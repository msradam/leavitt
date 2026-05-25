"""Smoke test: FSM flow, chaos recovery, and Theodosia transition enforcement.

Run with a stubbed LLM and stubbed upstream servers so it needs no network:

    LEAVITT_LLM_STUB=1 uv run python tests/smoke_test.py
"""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("LEAVITT_LLM_STUB", "1")

from fastmcp import Client

import theodosia
from theodosia.upstream import reset_upstream
from leavitt.app import build_application, mount_server


class StubUpstream:
    """Implements the async ``call(server, tool, args)`` contract Theodosia binds."""

    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    async def call(self, server, tool, args):
        self.calls.append((server, tool))
        return self.behavior(server, tool, args)


def healthy(server, tool, args):
    if tool == "query_prometheus":
        return [
            {"service_name": "product-catalog", "value": 4.2},
            {"service_name": "checkout", "value": 1.1},
        ]
    if tool == "query_loki_logs":
        return [{"service_name": "product-catalog", "line": "error: product not found"}]
    return {"productCatalogFailure": "on", "paymentServiceFailure": "off"}


def all_down(server, tool, args):
    raise RuntimeError("connection refused")


async def drive(behavior, query, max_retries=1):
    app = build_application(track=False)
    token = theodosia.bind_upstream(StubUpstream(behavior))
    try:
        action, _, state = await app.astep(
            inputs={"query": query, "max_retries": max_retries}
        )
        steps = [action.name]
        while action.name != "produce_report":
            action, _, state = await app.astep()
            steps.append(action.name)
        return state, steps
    finally:
        reset_upstream(token)


def check(label, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    return cond


async def main():
    ok = True

    print("clean run (all sources healthy):")
    state, steps = await drive(healthy, "why are checkouts failing?")
    report = state["report"]
    ok &= check("reached produce_report", steps[-1] == "produce_report")
    ok &= check("full confidence", report["confidence"] == "full")
    ok &= check("disposition not inconclusive", report["disposition"] != "inconclusive")
    ok &= check("identified affected services", len(report["affected_services"]) > 0)
    ok &= check("correlate ran before report", "correlate_evidence" in steps)

    print("total source failure (all upstream down, 1 retry):")
    state, steps = await drive(all_down, "checkout latency spike?", max_retries=1)
    report = state["report"]
    ok &= check("disposition inconclusive", report["disposition"] == "inconclusive")
    ok &= check("no usable sources", len(report["sources_usable"]) == 0)
    ok &= check(
        "recovery event recorded",
        any("re-querying" in e for e in report["recovery_events"]),
    )
    ok &= check("retry re-queried metrics", steps.count("query_grafana_metrics") == 2)
    ok &= check("did not claim resolved", report["disposition"] != "resolved")

    print("Theodosia transition enforcement (in-memory MCP client):")
    server = mount_server(upstream={})
    async with Client(server) as client:
        res = await client.call_tool("step", {"action": "produce_report"})
        payload = res.structured_content or {}
        err = payload.get("error") or {}
        ok &= check(
            "skipping to produce_report refused",
            (err.get("type") if isinstance(err, dict) else "") == "invalid_transition"
            or "invalid_transition" in str(payload),
        )
        ok &= check("refusal lists valid next actions", "receive_query" in str(payload))

    print()
    print("SMOKE: " + ("ALL PASS" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
