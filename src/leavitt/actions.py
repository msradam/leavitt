"""READ-class action bodies for the Leavitt FSM.

Every action reads from upstream MCP servers via ``theodosia.call_upstream`` and
writes to Burr state. None of them mutate the observed system. There is no
write action and no unlock action in this module; the read-only guarantee is
the graph having nothing else.

Upstream tool names and queries live in ``SOURCES`` so pointing at a real
``mcp-grafana`` instance is one edit. The default mapping targets the official
Grafana MCP server (``query_prometheus``, ``query_loki_logs``) and a feature-flag
context server.
"""

from __future__ import annotations

import json
import os
from typing import Any

from burr.core import State, action

from leavitt import reports
from leavitt.chaos_handler import (
    OK,
    SourceResult,
    confidence_label,
    coverage,
    safe_upstream,
)

# Default datasource UIDs in the OpenTelemetry Demo Grafana. Overridable via env.
PROM_DS = os.getenv("LEAVITT_PROM_UID", "webstore-metrics")
LOKI_DS = os.getenv("LEAVITT_LOKI_UID", "webstore-logs-loki")

# Broad incident-surfacing queries. Not scenario-specific: Leavitt reads what is
# wrong, it is not told what to look for.
PROM_ERROR_RATE = (
    "sum by (service_name) "
    '(rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m]))'
)
LOKI_WARN_ERROR = '{service_name=~".+"} |~ "(?i)error|warn|exception|timeout"'

# k6 client-side: failed request rate per endpoint (expected_response="false").
# This is the user-facing symptom, separate from server-side span errors.
K6_CLIENT_FAILS = (
    'sum by (name) (rate(k6_http_reqs_total{expected_response="false"}[5m]))'
)

SOURCES: dict[str, dict[str, Any]] = {
    "grafana_metrics": {
        "server": "grafana",
        "tool": "query_prometheus",
        "args": {
            "datasourceUid": PROM_DS,
            "expr": PROM_ERROR_RATE,
            "queryType": "instant",
            "endTime": "now",
        },
        "expect": "any",
    },
    "grafana_logs": {
        "server": "grafana",
        "tool": "query_loki_logs",
        "args": {"datasourceUid": LOKI_DS, "logql": LOKI_WARN_ERROR, "limit": 50},
        "expect": "any",
    },
    "client_load": {
        "server": "grafana",
        "tool": "query_prometheus",
        "args": {
            "datasourceUid": PROM_DS,
            "expr": K6_CLIENT_FAILS,
            "queryType": "instant",
            "endTime": "now",
        },
        "expect": "any",
    },
    "deployment_context": {
        "server": "flagctx",
        "tool": "get_flag_state",
        "args": {},
        "expect": "any",
    },
}


def _source_call(name: str):
    spec = SOURCES[name]
    return safe_upstream(
        name, spec["server"], spec["tool"], dict(spec["args"]), expect=spec["expect"]
    )


@action(
    reads=[], writes=["query", "max_retries", "retry_count", "recovery_events", "mode"]
)
def receive_query(
    state: State, query: str = "", max_retries: int = 1
) -> tuple[dict, State]:
    return {"query": query}, state.update(
        query=query,
        max_retries=int(max_retries),
        retry_count=0,
        recovery_events=[],
        mode="readonly",
    )


@action(reads=[], writes=["sources"])
def enumerate_sources(state: State) -> tuple[dict, State]:
    sources = list(SOURCES.keys())
    return {"sources": sources}, state.update(sources=sources)


@action(reads=["query"], writes=["metrics_result"])
async def query_grafana_metrics(state: State) -> tuple[dict, State]:
    res = await _source_call("grafana_metrics")
    return {"status": res.status}, state.update(metrics_result=res.to_dict())


@action(reads=["query"], writes=["logs_result"])
async def query_grafana_logs(state: State) -> tuple[dict, State]:
    res = await _source_call("grafana_logs")
    return {"status": res.status}, state.update(logs_result=res.to_dict())


@action(reads=["query"], writes=["client_result"])
async def query_client_load(state: State) -> tuple[dict, State]:
    res = await _source_call("client_load")
    return {"status": res.status}, state.update(client_result=res.to_dict())


@action(reads=["query"], writes=["deployment_result"])
async def query_deployment_context(state: State) -> tuple[dict, State]:
    res = await _source_call("deployment_context")
    return {"status": res.status}, state.update(deployment_result=res.to_dict())


def _gather(state: State) -> list[SourceResult]:
    out = []
    for key in ("metrics_result", "logs_result", "client_result", "deployment_result"):
        raw = state.get(key)
        if raw:
            out.append(SourceResult(**raw))
    return out


@action(
    reads=[
        "metrics_result",
        "logs_result",
        "client_result",
        "deployment_result",
        "retry_count",
        "max_retries",
        "recovery_events",
    ],
    writes=[
        "evidence",
        "usable_count",
        "source_count",
        "confidence",
        "should_retry",
        "retry_count",
        "recovery_events",
    ],
)
def correlate_evidence(state: State) -> tuple[dict, State]:
    results = _gather(state)
    usable, total = coverage(results)
    conf = confidence_label(usable, total)

    evidence = []
    for r in results:
        if r.usable:
            evidence.append(
                {
                    "source": r.name,
                    "status": r.status,
                    "summary": _summarize(r),
                    "data": r.data,
                }
            )
        else:
            evidence.append(
                {
                    "source": r.name,
                    "status": r.status,
                    "summary": f"unavailable: {r.detail}",
                }
            )

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 0)
    recovery = list(state.get("recovery_events", []))
    should_retry = usable == 0 and retry_count < max_retries

    if should_retry:
        retry_count += 1
        recovery.append(
            f"total source failure on attempt {retry_count}; re-querying upstream sources"
        )
    elif usable < total:
        recovery.append(
            f"continued with {usable}/{total} sources after partial failure (confidence: {conf})"
        )

    return {
        "usable": usable,
        "total": total,
        "confidence": conf,
        "should_retry": should_retry,
    }, state.update(
        evidence=evidence,
        usable_count=usable,
        source_count=total,
        confidence=conf,
        should_retry=should_retry,
        retry_count=retry_count,
        recovery_events=recovery,
    )


def _unwrap(data: Any) -> Any:
    """FastMCP wraps a tool's non-object return (e.g. a list) under a single
    ``result`` key, since MCP structured content must be an object. Peel that
    envelope so list-returning tools (query_prometheus, query_loki_logs) read
    the same whether or not they were wrapped."""
    if isinstance(data, dict) and set(data.keys()) == {"result"}:
        return data["result"]
    return data


def _summarize(r: SourceResult) -> str:
    data = _unwrap(r.data)
    if isinstance(data, list):
        return f"{len(data)} records"
    if isinstance(data, dict):
        keys = list(data.keys())[:6]
        return f"{len(data)} fields ({', '.join(map(str, keys))})"
    return str(data)[:160]


@action(reads=["evidence", "usable_count"], writes=["digest"])
def distill_evidence(state: State) -> tuple[dict, State]:
    """Reduce raw telemetry to a high-signal digest before the reasoning step.

    A distinct action so the exact text the reasoner sees is a recorded entry in
    the Theodosia ledger, separate from the raw evidence. Deterministic: it
    extracts known fields from mcp-grafana's stable response shapes, so it cannot
    drop or paraphrase the signal the way a generative summarizer might.
    """
    usable_ev = [e for e in state.get("evidence", []) if e.get("status") == OK]
    digest = _digest_for_llm(usable_ev) if usable_ev else ""
    return {"digest": digest}, state.update(digest=digest)


@action(
    reads=["query", "digest", "evidence", "usable_count", "confidence"],
    writes=["root_cause", "affected_services", "hypothesis"],
)
async def form_hypothesis(state: State) -> tuple[dict, State]:
    usable = state.get("usable_count", 0)
    if usable == 0:
        out = {
            "root_cause": "undetermined: no usable telemetry",
            "affected_services": [],
            "hypothesis": "All sources failed. Insufficient evidence to name a cause.",
        }
        return out, state.update(**out)

    if os.getenv("LEAVITT_LLM_STUB") == "1":
        usable_ev = [e for e in state.get("evidence", []) if e.get("status") == OK]
        out = _stub_reason(usable_ev)
        return out, state.update(**out)

    out = await _reason(
        state["query"], state.get("digest", ""), state.get("confidence", "full")
    )
    return out, state.update(**out)


def _digest_for_llm(usable_ev: list[dict]) -> str:
    """Compact each source to high-signal lines. Reasoning models burn their
    token budget on raw Prometheus matrices and log dumps, so send a digest:
    service -> value for metrics, distinct lines for logs, active flags for
    deployment context."""
    parts = []
    for e in usable_ev:
        name = e.get("source")
        data = _unwrap(e.get("data"))
        rows = data.get("data") if isinstance(data, dict) and "data" in data else data
        if name == "grafana_metrics" and isinstance(rows, list):
            pairs = []
            for r in rows:
                if isinstance(r, dict):
                    svc = (r.get("metric") or {}).get("service_name") or r.get(
                        "service_name", "?"
                    )
                    val = r.get("value")
                    if (
                        val is None
                        and isinstance(r.get("values"), list)
                        and r["values"]
                    ):
                        val = r["values"][-1]  # range matrix: last [ts, v] point
                    if isinstance(val, (list, tuple)):
                        val = val[-1]
                    try:
                        val = round(float(val), 4)
                    except (TypeError, ValueError):
                        pass
                    pairs.append(f"{svc}={val}")
            parts.append(
                f"[metrics] error/call rate by service: {', '.join(pairs[:20]) or 'no series'}"
            )
        elif name == "client_load" and isinstance(rows, list):
            pairs = []
            for r in rows:
                if isinstance(r, dict):
                    ep = (r.get("metric") or {}).get("name") or r.get("name", "?")
                    val = r.get("value")
                    if isinstance(val, (list, tuple)):
                        val = val[-1]
                    try:
                        val = round(float(val), 4)
                    except (TypeError, ValueError):
                        pass
                    pairs.append(f"{ep}={val}")
            parts.append(
                "[client load (k6)] failed request rate by endpoint: "
                + (", ".join(pairs[:20]) or "no client-side failures")
            )
        elif name == "grafana_logs" and isinstance(rows, list):
            lines = []
            for r in rows:
                if isinstance(r, dict):
                    svc = (r.get("labels") or {}).get("service_name", "?")
                    line = (r.get("line") or "").strip()[:160]
                    if line:
                        lines.append(f"{svc}: {line}")
            seen, distinct = set(), []
            for ln in lines:
                if ln not in seen:
                    seen.add(ln)
                    distinct.append(ln)
            parts.append(
                "[logs] sample warning/error lines:\n  "
                + "\n  ".join(distinct[:15] or ["(none)"])
            )
        elif name == "deployment_context" and isinstance(data, dict):
            active = data.get("active_chaos_flags") or []
            parts.append(
                f"[deployment] active feature flags (non-baseline): {active or 'none'}"
            )
        else:
            parts.append(f"[{name}] {json.dumps(data)[:600]}")
    return "\n\n".join(parts)


async def _reason(query: str, digest: str, confidence: str) -> dict[str, Any]:
    import litellm

    model = os.getenv("LEAVITT_LLM", "together_ai/moonshotai/Kimi-K2.6")
    prompt = (
        "You are an incident triage analyst reading observability telemetry. "
        "You only read dashboards; you cannot run commands. "
        f"Investigation question:\n{query}\n\n"
        f"Evidence collected (confidence: {confidence}):\n"
        f"{digest}\n\n"
        "Identify the most likely root cause and the affected services strictly "
        "from this evidence. If the evidence does not support a conclusion, say so. "
        'Reply with JSON only: {"root_cause": str, "affected_services": [str], "reasoning": str}'
    )
    try:
        resp = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            # Kimi K2.6 is a reasoning model: tokens are spent on reasoning_content
            # before the JSON answer lands in content, so the budget must be generous.
            max_tokens=8000,
        )
        text = resp["choices"][0]["message"]["content"]
        parsed = _parse_json(text)
        return {
            "root_cause": parsed.get("root_cause", "undetermined"),
            "affected_services": parsed.get("affected_services", []),
            "hypothesis": parsed.get("reasoning", text)[:1200],
        }
    except Exception as exc:  # noqa: BLE001 - LLM failure degrades, it does not crash the FSM
        return {
            "root_cause": "undetermined: reasoning step unavailable",
            "affected_services": [],
            "hypothesis": f"LLM call failed ({type(exc).__name__}: {exc}); evidence preserved for review.",
        }


def _stub_reason(usable_ev: list[dict]) -> dict[str, Any]:
    services = sorted({s for e in usable_ev for s in _services_in(e)})
    return {
        "root_cause": "stubbed: derived from highest-signal source"
        if usable_ev
        else "undetermined",
        "affected_services": services[:5],
        "hypothesis": f"stub reasoning over {len(usable_ev)} usable source(s)",
    }


def _services_in(evidence_item: dict) -> list[str]:
    data = _unwrap(evidence_item.get("data"))
    found = []
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                for k in ("service_name", "service", "serviceName"):
                    if k in row:
                        found.append(str(row[k]))
    return found


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _observed_entities(evidence: list[dict]) -> str:
    """A lowercased blob of entities actually seen in collected signal: service
    names from metrics and logs, k6 endpoint names, and active feature flags.
    Used to check a claimed root cause is grounded in observed telemetry."""
    tokens: list[str] = []
    for e in evidence:
        if e.get("status") != OK:
            continue
        data = _unwrap(e.get("data"))
        rows = data.get("data") if isinstance(data, dict) and "data" in data else data
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    m = r.get("metric") or {}
                    tokens += [str(m.get("service_name", "")), str(m.get("name", ""))]
                    labels = r.get("labels") or {}
                    tokens.append(str(labels.get("service_name", "")))
        if isinstance(data, dict):
            tokens += [str(f) for f in (data.get("active_chaos_flags") or [])]
    return " ".join(t for t in tokens if t).lower()


def _grounded(affected: list[str], evidence: list[dict]) -> bool:
    if not affected:
        return False
    blob = _observed_entities(evidence)
    return any(s.lower() in blob for s in affected if s)


@action(
    reads=[
        "query",
        "evidence",
        "root_cause",
        "affected_services",
        "confidence",
        "usable_count",
        "sources",
        "recovery_events",
    ],
    writes=["report", "disposition"],
)
def produce_report(
    state: State, disposition: str = reports.DEGRADED
) -> tuple[dict, State]:
    usable = state.get("usable_count", 0)
    conf = state.get("confidence", "none")

    affected = list(state.get("affected_services", []))

    # Disposition is constrained by evidence, not by the caller's wish.
    # resolved requires: no source lost (full confidence) AND the named cause
    # actually appears in the collected signal. A confident hypothesis that
    # isn't grounded in observed telemetry is downgraded, not trusted.
    if usable == 0:
        disposition = reports.INCONCLUSIVE
    elif disposition == reports.RESOLVED and (
        conf != "full" or not _grounded(affected, state.get("evidence", []))
    ):
        disposition = reports.DEGRADED

    evidence = state.get("evidence", [])
    usable_names = [e["source"] for e in evidence if e.get("status") == OK]
    failed = [
        {"name": e["source"], "detail": e.get("summary", "")}
        for e in evidence
        if e.get("status") != OK
    ]

    report = reports.TriageReport(
        query=state.get("query", ""),
        disposition=disposition,
        confidence=conf,
        root_cause=state.get("root_cause", "undetermined"),
        affected_services=affected,
        evidence=[
            {"source": e["source"], "summary": e.get("summary", "")} for e in evidence
        ],
        sources_queried=list(state.get("sources", [])),
        sources_usable=usable_names,
        sources_failed=failed,
        recovery_events=list(state.get("recovery_events", [])),
    )
    return {"report": report.to_dict()}, state.update(
        report=report.to_dict(), disposition=disposition
    )
