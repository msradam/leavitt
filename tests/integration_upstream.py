"""End-to-end test of the Theodosia upstream path with real MCP servers.

Unlike the smoke test (which binds a stub via bind_upstream), this exercises the
real machinery: theodosia.mount(upstream={...}) opens fastmcp.Client sessions to
two MCP servers running as stdio subprocesses, and the FSM is driven entirely
through the `step` tool. call_upstream inside each query action hits the real
server.

  - grafana: tests/fake_grafana_mcp.py (Grafana tool surface, sample telemetry)
  - flagctx: deploy/flagctx_server.py (real flagd config parsing)

Run:
    LEAVITT_LLM_STUB=1 uv run python tests/integration_upstream.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("LEAVITT_LLM_STUB", "1")

from fastmcp import Client

from leavitt.app import mount_server

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

SAMPLE_FLAGS = {
    "flags": {
        "productCatalogFailure": {
            "defaultVariant": "on",
            "variants": {"on": True, "off": False},
        },
        "paymentServiceFailure": {
            "defaultVariant": "off",
            "variants": {"on": True, "off": False},
        },
        "adServiceHighCpu": {
            "defaultVariant": "off",
            "variants": {"on": True, "off": False},
        },
    }
}


def check(label, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    return bool(cond)


async def drive_full_run(client: Client, query: str) -> dict:
    """Step the FSM to completion via the step tool, following valid_next_actions."""
    resp = await client.call_tool(
        "step",
        {"action": "receive_query", "inputs": {"query": query, "max_retries": 1}},
    )
    while True:
        sc = resp.structured_content or {}
        if sc.get("error"):
            raise RuntimeError(f"unexpected refusal: {sc['error']}")
        last = sc.get("action")
        if last == "produce_report":
            return sc.get("state", {})
        nxt = (sc.get("valid_next_actions") or [None])[0]
        if not nxt:
            return sc.get("state", {})
        resp = await client.call_tool("step", {"action": nxt})


async def main() -> int:
    ok = True
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE_FLAGS, f)
        flags_path = f.name

    upstream = {
        "grafana": {
            "command": PY,
            "args": [str(REPO / "tests" / "fake_grafana_mcp.py")],
        },
        "flagctx": {
            "command": PY,
            "args": [str(REPO / "deploy" / "flagctx_server.py")],
            "env": {**os.environ, "FLAGCTX_CONFIG_PATH": flags_path},
        },
    }

    server = mount_server(upstream=upstream)
    print("driving full FSM through step tool against two real stdio MCP servers:")
    async with Client(server) as client:
        state = await drive_full_run(client, "why are product pages erroring?")

    report = state.get("report") or {}
    print(json.dumps(report, indent=2)[:1200])
    print()

    usable = report.get("sources_usable", [])
    ok &= check("all four sources usable (real upstream calls)", len(usable) == 4)
    ok &= check("grafana_metrics usable", "grafana_metrics" in usable)
    ok &= check("grafana_logs usable", "grafana_logs" in usable)
    ok &= check("client_load usable", "client_load" in usable)
    ok &= check("deployment_context usable", "deployment_context" in usable)
    ok &= check("full confidence", report.get("confidence") == "full")
    ok &= check(
        "deployment context surfaced the active chaos flag",
        _flag_seen(state, "productCatalogFailure"),
    )
    ok &= check(
        "report names product-catalog from metrics/logs",
        any("product-catalog" in s for s in report.get("affected_services", [])),
    )

    os.unlink(flags_path)
    print()
    print("INTEGRATION: " + ("ALL PASS" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


def _flag_seen(state: dict, flag: str) -> bool:
    dep = state.get("deployment_result") or {}
    data = dep.get("data") or {}
    return flag in (data.get("active_chaos_flags") or []) or flag in (
        data.get("flags") or {}
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
