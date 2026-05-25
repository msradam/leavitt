"""Baseline arm: the same model (Kimi) with raw query tools and a submit_report
tool, calling the upstream MCP servers directly. No Theodosia, no FSM, no forced
correlation, no evidence-constrained disposition. This is the comparison point
for what the Theodosia layer buys under chaos.
"""

from __future__ import annotations

from theodosia import UpstreamError, UpstreamManager

from bench.common import digest_one, kimi_loop, upstream_for
from leavitt.actions import SOURCES

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_server_metrics",
            "description": "Server-side error rate by service (PromQL over span metrics).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_logs",
            "description": "Recent warning/error log lines across services (LogQL).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_client_metrics",
            "description": "Client-side failed request rate by endpoint (k6 load test metrics).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_deployment",
            "description": "Current feature-flag / deployment state.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "Submit the final triage report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "root_cause": {"type": "string"},
                    "affected_services": {"type": "array", "items": {"type": "string"}},
                    "disposition": {
                        "type": "string",
                        "enum": ["resolved", "degraded", "inconclusive"],
                    },
                },
                "required": ["root_cause", "affected_services", "disposition"],
            },
        },
    },
]

SYSTEM = (
    "You are an incident triage analyst. You read observability dashboards through "
    "the query tools; you cannot run commands or change anything. Investigate the "
    "incident, then call submit_report. Base the root cause strictly on the evidence "
    "you gathered. Use disposition 'resolved' only if the evidence clearly supports a "
    "root cause, 'degraded' if some sources were unavailable or weak, 'inconclusive' if "
    "the evidence does not support a conclusion. Do not invent evidence."
)

_QUERY_MAP = {
    "query_server_metrics": ("grafana", "query_prometheus", "grafana_metrics"),
    "query_logs": ("grafana", "query_loki_logs", "grafana_logs"),
    "query_client_metrics": ("grafana", "query_prometheus", "client_load"),
    "query_deployment": ("flagctx", "get_flag_state", "deployment_context"),
}


async def run_baseline(scenario: dict, condition: str) -> tuple[dict | None, dict]:
    mgr = UpstreamManager(upstream_for(condition))

    async def dispatch(name: str, args: dict) -> dict:
        if name == "submit_report":
            return {
                "result": "report submitted",
                "report": {
                    "root_cause": args.get("root_cause", ""),
                    "affected_services": args.get("affected_services", []),
                    "disposition": args.get("disposition", ""),
                },
                "stop": True,
            }
        if name not in _QUERY_MAP:
            return {"result": {"error": f"unknown tool {name}"}}
        server, tool, src = _QUERY_MAP[name]
        call_args = dict(SOURCES[src]["args"]) if src in SOURCES else {}
        try:
            payload = await mgr.call(server, tool, call_args)
        except UpstreamError as exc:
            return {"result": {"error": f"source unavailable: {exc}"[:200]}}
        except Exception as exc:  # noqa: BLE001
            return {"result": {"error": f"{type(exc).__name__}: {exc}"[:200]}}
        return {"result": digest_one(src, payload)}

    try:
        report, trace = await kimi_loop(SYSTEM, scenario["query"], TOOLS, dispatch)
    finally:
        await mgr.aclose()
    trace["arm"] = "baseline"
    return report, trace
