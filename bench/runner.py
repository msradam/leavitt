"""Chaos benchmark runner.

Leavitt arm: Kimi drives Theodosia's `step` tool; the FSM is enforced and the
report disposition is evidence-constrained. Baseline arm in baseline_agent.py.

For each scenario, enable its flagd flag, wait for signal, run every
(condition x arm), score against the demo's flag ground truth, reset the flag.

  set -a; source .env; set +a
  uv run python -m bench.runner                 # full matrix
  BENCH_SCENARIOS=product_catalog_failure BENCH_CONDITIONS=clean uv run python -m bench.runner
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone

import yaml
from fastmcp import Client

from bench.baseline_agent import run_baseline
from bench.common import GRAFANA_SSE, REPO, score, upstream_for
from bench.kimi_step import LEAVITT_SYSTEM, STEP_TOOL, make_leavitt_dispatch
from leavitt.app import mount_server

FLAGD = REPO / "deploy/opentelemetry-demo/src/flagd/demo.flagd.json"
# BENCH_TAG namespaces output per model so a weak-model run doesn't overwrite a
# frontier-model run.
BENCH_TAG = os.getenv("BENCH_TAG", "")
RESULTS = REPO / "bench/results" / BENCH_TAG if BENCH_TAG else REPO / "bench/results"


def set_flag(name: str, on: bool) -> None:
    d = json.loads(FLAGD.read_text())
    d["flags"][name]["defaultVariant"] = "on" if on else "off"
    FLAGD.write_text(json.dumps(d, indent=2))


async def wait_for_signal(service: str, timeout: float = 90.0) -> bool:
    """Poll server-side error rate until the expected service shows errors."""
    expr = f'sum(rate(traces_span_metrics_calls_total{{service_name="{service}",status_code="STATUS_CODE_ERROR"}}[1m]))'
    deadline = time.time() + timeout
    async with Client(GRAFANA_SSE) as c:
        while time.time() < deadline:
            try:
                r = await c.call_tool(
                    "query_prometheus",
                    {
                        "datasourceUid": "webstore-metrics",
                        "expr": expr,
                        "queryType": "instant",
                        "endTime": "now",
                    },
                )
                txt = "".join(getattr(b, "text", "") for b in (r.content or []))
                data = json.loads(txt).get("data", []) if txt else []
                if data and float(data[0]["value"][1]) > 0:
                    return True
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(6)
    return False


async def run_leavitt(scenario: dict, condition: str) -> tuple[dict | None, dict]:
    server = mount_server(upstream=upstream_for(condition))
    async with Client(server) as client:
        dispatch, get_report = make_leavitt_dispatch(client)
        from bench.common import kimi_loop

        report, trace = await kimi_loop(
            LEAVITT_SYSTEM, scenario["query"], [STEP_TOOL], dispatch
        )
    report = report or get_report()
    trace["arm"] = "leavitt"
    if report:
        trace["sources_usable"] = report.get("sources_usable", [])
        trace["recovery_events"] = report.get("recovery_events", [])
    return report, trace


async def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    spec = yaml.safe_load((REPO / "examples/scenarios.yaml").read_text())
    scenarios = spec["scenarios"]
    conditions = spec["conditions"]
    only_s = set(filter(None, os.getenv("BENCH_SCENARIOS", "").split(",")))
    only_c = set(filter(None, os.getenv("BENCH_CONDITIONS", "").split(",")))
    if only_s:
        scenarios = [s for s in scenarios if s["id"] in only_s]
    if only_c:
        conditions = [c for c in conditions if c in only_c]

    rows = []
    for sc in scenarios:
        print(f"\n=== scenario {sc['id']} (flag {sc['flag']}) ===")
        set_flag(sc["flag"], True)
        signal = await wait_for_signal(sc["expect_services"][0])
        print(f"  signal present: {signal}")
        try:
            for cond in conditions:
                for arm, runner in (
                    ("leavitt", run_leavitt),
                    ("baseline", run_baseline),
                ):
                    t0 = time.time()
                    try:
                        report, trace = await runner(sc, cond)
                    except Exception as exc:  # noqa: BLE001
                        report, trace = (
                            None,
                            {"arm": arm, "error": f"{type(exc).__name__}: {exc}"[:300]},
                        )
                    sc_score = score(report, sc["expect_services"])
                    rec = {
                        "scenario": sc["id"],
                        "flag": sc["flag"],
                        "condition": cond,
                        "arm": arm,
                        "elapsed_s": round(time.time() - t0, 1),
                        "expect_services": sc["expect_services"],
                        **sc_score,
                        "recovery_events": len(trace.get("recovery_events", [])),
                        "refusals": trace.get("refusals", 0),
                        "tool_calls": len(trace.get("tool_calls", [])),
                        "report": report,
                        "trace_error": trace.get("error"),
                    }
                    rows.append(rec)
                    fn = RESULTS / f"{sc['id']}__{cond}__{arm}.json"
                    fn.write_text(json.dumps(rec, indent=2, default=str))
                    mark = (
                        "OK"
                        if sc_score["found_root_cause"]
                        else ("FP" if sc_score["false_positive"] else "--")
                    )
                    print(
                        f"  {cond:11s} {arm:8s} found={sc_score['found_root_cause']!s:5s} "
                        f"disp={sc_score['disposition'] or '-':12s} {mark} ({rec['elapsed_s']}s)"
                    )
        finally:
            set_flag(sc["flag"], False)
            await asyncio.sleep(3)

    _write_table(rows)
    (RESULTS / "all_runs.json").write_text(json.dumps(rows, indent=2, default=str))
    print(f"\nwrote {len(rows)} runs to {RESULTS}")
    return 0


def _write_table(rows: list[dict]) -> None:
    suffix = f"_{BENCH_TAG}" if BENCH_TAG else ""
    out = REPO / f"demo/results_table{suffix}.md"
    out.parent.mkdir(exist_ok=True)
    lines = [
        f"# Leavitt chaos benchmark ({datetime.now(timezone.utc).date()})",
        "",
        "Real runs against the OpenTelemetry Demo. Ground truth: the demo's flagd flag descriptions.",
        "Leavitt = Kimi driving a Theodosia-enforced FSM. Baseline = same model, raw MCP tool calls, no FSM.",
        "",
        "| scenario | condition | arm | report | found cause | disposition | false positive | recoveries |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario']} | {r['condition']} | {r['arm']} | "
            f"{'Y' if r['produced_report'] else 'N'} | {'Y' if r['found_root_cause'] else 'N'} | "
            f"{r['disposition'] or '-'} | {'YES' if r['false_positive'] else 'no'} | {r['recovery_events']} |"
        )

    # aggregate
    def agg(arm, cond):
        sub = [r for r in rows if r["arm"] == arm and r["condition"] == cond]
        if not sub:
            return None
        n = len(sub)
        return {
            "found": sum(r["found_root_cause"] for r in sub),
            "fp": sum(r["false_positive"] for r in sub),
            "report": sum(r["produced_report"] for r in sub),
            "n": n,
        }

    conds = sorted({r["condition"] for r in rows})
    lines += [
        "",
        "## Summary (found root cause / produced report / false positives)",
        "",
        "| condition | Leavitt | Baseline |",
        "|---|---|---|",
    ]
    for cond in conds:
        lv, bl = agg("leavitt", cond), agg("baseline", cond)

        def fmt(a):
            return f"{a['found']}/{a['n']} found, {a['fp']} FP" if a else "-"

        lines.append(f"| {cond} | {fmt(lv)} | {fmt(bl)} |")
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
