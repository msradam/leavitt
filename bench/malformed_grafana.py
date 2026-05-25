"""A Grafana-surface MCP server that returns malformed data, for the multi_fail
chaos condition. Same tool names as mcp-grafana (query_prometheus,
query_loki_logs) so the agent calls it unchanged, but the responses are garbage:
wrong shapes and error-ish strings. Tests whether the agent rejects unusable
evidence instead of hallucinating a root cause from it.
"""

from __future__ import annotations

import random

from fastmcp import FastMCP

mcp = FastMCP("malformed-grafana")

GARBAGE = [
    "ERR_CONNECTION_RESET while scraping",
    "<html>502 Bad Gateway</html>",
    {"unexpected": "shape", "nan": float("nan").__repr__()},
    "\x00\x01 binary noise \xff",
    "null",
]


@mcp.tool
def query_prometheus(datasourceUid: str, expr: str, **kwargs) -> str:  # noqa: N803
    return str(random.choice(GARBAGE))


@mcp.tool
def query_loki_logs(datasourceUid: str, logql: str, **kwargs) -> str:  # noqa: N803
    return str(random.choice(GARBAGE))


if __name__ == "__main__":
    mcp.run()
