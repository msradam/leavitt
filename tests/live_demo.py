"""Leavitt end to end against the live OpenTelemetry Demo with real Kimi.

Three real upstream sources, all via real MCP servers:
  - grafana  : mcp-grafana (SSE :8000) -> Prometheus (webstore-metrics) + Loki (webstore-logs-loki)
  - flagctx  : deploy/flagctx_server.py reading the demo's flagd config

The FSM is driven through Theodosia's step tool. form_hypothesis calls Kimi via
litellm (no stub). Run with a flagd flag enabled to give it a real incident.

  set -a; source .env; set +a
  uv run python tests/live_demo.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("LEAVITT_PROM_UID", "webstore-metrics")
os.environ.setdefault("LEAVITT_LOKI_UID", "webstore-logs-loki")

from fastmcp import Client

from leavitt.app import mount_server

REPO = Path(__file__).resolve().parent.parent
FLAGD_CONFIG = str(REPO / "deploy/opentelemetry-demo/src/flagd/demo.flagd.json")


async def drive(client: Client, query: str) -> dict:
    resp = await client.call_tool(
        "step",
        {"action": "receive_query", "inputs": {"query": query, "max_retries": 1}},
    )
    while True:
        sc = resp.structured_content or {}
        if sc.get("error"):
            raise RuntimeError(f"refusal: {sc['error']}")
        if sc.get("action") == "produce_report":
            return sc.get("state", {})
        nxt = (sc.get("valid_next_actions") or [None])[0]
        if not nxt:
            return sc.get("state", {})
        resp = await client.call_tool("step", {"action": nxt})


async def main() -> int:
    upstream = {
        "grafana": "http://localhost:8000/sse",
        "flagctx": {
            "command": sys.executable,
            "args": [str(REPO / "deploy/flagctx_server.py")],
            "env": {**os.environ, "FLAGCTX_CONFIG_PATH": FLAGD_CONFIG},
        },
    }
    server = mount_server(upstream=upstream)
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Checkouts are failing for some users. What is the root cause?"
    )
    print(f"query: {query}\nmodel: {os.getenv('LEAVITT_LLM')}\n")

    async with Client(server) as client:
        state = await drive(client, query)

    report = state.get("report") or {}
    print("=" * 70)
    print(f"disposition:       {report.get('disposition')}")
    print(f"confidence:        {report.get('confidence')}")
    print(f"root cause:        {report.get('root_cause')}")
    print(f"affected services: {report.get('affected_services')}")
    print(f"sources usable:    {report.get('sources_usable')}")
    for f in report.get("sources_failed", []):
        print(f"source failed:     {f['name']} -> {f['detail'][:80]}")
    for ev in report.get("recovery_events", []):
        print(f"recovery:          {ev}")
    print("\nhypothesis:\n" + (state.get("hypothesis", "")[:800]))
    print(
        "\nactive chaos flags (deployment context):",
        ((state.get("deployment_result") or {}).get("data") or {}).get(
            "active_chaos_flags"
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
