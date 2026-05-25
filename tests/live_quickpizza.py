"""Live smoke against real telemetry: mcp-grafana -> QuickPizza's Grafana.

Not a benchmark. Confirms the full real pipeline end to end: Theodosia opens a
client session to the running mcp-grafana (SSE), the query actions run real
PromQL/LogQL against QuickPizza's Prometheus and Loki, correlate and report run.

flagctx is intentionally left unconfigured (QuickPizza has no flagd), so
deployment_context degrades. A 2/3-source degraded report against real data is
the expected, correct outcome.

Prereqs:
  - QuickPizza monolithic stack up (Grafana :3000, Prometheus, Loki)
  - mcp-grafana up on http://localhost:8000/sse, GRAFANA_URL=http://host.docker.internal:3000

Run:
  LEAVITT_LLM_STUB=1 LEAVITT_PROM_UID=prometheus LEAVITT_LOKI_UID=loki \
    uv run python tests/live_quickpizza.py
"""

from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("LEAVITT_PROM_UID", "prometheus")
os.environ.setdefault("LEAVITT_LOKI_UID", "loki")
os.environ.setdefault("LEAVITT_LLM_STUB", "1")

from fastmcp import Client

from leavitt.app import mount_server

GRAFANA_MCP = os.getenv("LEAVITT_GRAFANA_MCP", "http://localhost:8000/sse")


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
    upstream = {"grafana": GRAFANA_MCP}  # flagctx deliberately omitted
    server = mount_server(upstream=upstream)

    print(f"driving Leavitt against real mcp-grafana at {GRAFANA_MCP}")
    async with Client(server) as client:
        state = await drive(client, "are any services erroring or slow right now?")

    report = state.get("report") or {}
    print(json.dumps(report, indent=2)[:1800])

    metrics = state.get("metrics_result") or {}
    logs = state.get("logs_result") or {}
    print(
        "\nraw metrics status:",
        metrics.get("status"),
        "-",
        (metrics.get("detail") or "")[:200],
    )
    print(
        "raw logs status:   ", logs.get("status"), "-", (logs.get("detail") or "")[:200]
    )

    reached = report.get("disposition") is not None
    print("\nLIVE: reached a report =", reached)
    return 0 if reached else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
