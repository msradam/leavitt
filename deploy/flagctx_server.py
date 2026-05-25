"""Feature-flag context MCP server.

Reports the OpenTelemetry Demo's current flagd configuration as deployment
context: which chaos flags are on, and the default variant of every flag. This
answers "what changed in the deployment" without touching the system. One tool,
``get_flag_state``. Read-only.

Source resolution:
  FLAGCTX_CONFIG_URL  HTTP(S) URL to the flagd flag JSON (the demo serves the
                      file the flagd-ui edits), or
  FLAGCTX_CONFIG_PATH local path to a flagd flag definition JSON.

Run:
  uv run python deploy/flagctx_server.py            # stdio
  uv run python deploy/flagctx_server.py --http      # streamable-http on :8001
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

from fastmcp import FastMCP

mcp = FastMCP("flagctx")


def _load_config() -> dict:
    url = os.getenv("FLAGCTX_CONFIG_URL")
    path = os.getenv("FLAGCTX_CONFIG_PATH")
    if url:
        with urllib.request.urlopen(url, timeout=5) as r:  # noqa: S310 - operator-supplied internal URL
            return json.loads(r.read().decode())
    if path:
        with open(path) as f:
            return json.load(f)
    raise RuntimeError("set FLAGCTX_CONFIG_URL or FLAGCTX_CONFIG_PATH")


@mcp.tool
def get_flag_state() -> dict:
    """Return current flagd flag states: each flag's default variant and whether
    it is in a non-baseline (chaos) state."""
    cfg = _load_config()
    flags = cfg.get("flags", cfg)
    out = {}
    chaos = []
    for name, spec in flags.items():
        if not isinstance(spec, dict):
            continue
        default_variant = spec.get("defaultVariant")
        variants = spec.get("variants", {})
        value = variants.get(default_variant, default_variant)
        out[name] = {"defaultVariant": default_variant, "value": value}
        if value not in (0, False, "off", None, "") and default_variant not in (
            "off",
            "false",
        ):
            chaos.append(name)
    return {"flags": out, "active_chaos_flags": chaos}


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)  # noqa: S104
    else:
        mcp.run()
