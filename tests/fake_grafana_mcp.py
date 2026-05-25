"""A Grafana-surface MCP server for integration testing the Theodosia upstream path.

This is a test double. It exposes the same tool names and argument shapes as the
official mcp-grafana (`query_prometheus`, `query_loki_logs`) so Leavitt's actions
call it unchanged, but it returns fixed sample telemetry instead of querying a
real Grafana. Use it to verify the wiring (Theodosia opens a client session,
call_upstream hits the right tool with the right args). Real numbers come from
mcp-grafana against the OpenTelemetry Demo, not from here.
"""

from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP("fake-grafana")


@mcp.tool
def query_prometheus(  # noqa: N803 - match mcp-grafana arg names
    datasourceUid: str,
    expr: str,
    endTime: str,
    queryType: str = "range",
    startTime: str = "now-1h",
    stepSeconds: int = 60,
) -> list:
    return [
        {"service_name": "product-catalog", "value": 5.4},
        {"service_name": "frontend", "value": 1.2},
        {"service_name": "checkout", "value": 0.9},
    ]


@mcp.tool
def query_loki_logs(datasourceUid: str, logql: str, limit: int = 50) -> list:  # noqa: N803
    return [
        {
            "service_name": "product-catalog",
            "line": "error: failed to get product: rpc error",
        },
        {
            "service_name": "product-catalog",
            "line": "error: GetProduct returned code Internal",
        },
    ]


if __name__ == "__main__":
    mcp.run()
