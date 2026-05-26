#!/usr/bin/env python3
"""Make Hermes render Leavitt's MCP step calls as readable one-liners.

Hermes shows a per-call line for each tool, but for an MCP tool the preview is
built from a fixed set of argument keys (query/text/command/path/...). Leavitt's
step tool is keyed `action`/`inputs`, so the preview comes back empty and every
call renders as a bare `step` with no detail. This applies two edits to Hermes's
`agent/display.py`:

1. add `action` to the preview-key fallback, so the line shows the action name;
2. strip the `mcp_<server>_` prefix from the tool label, so it reads `step`
   instead of `mcp_leavi`.

Result: `│ ⚡ step  query_grafana_metrics  1.2s`. Pair with `display.tool_progress: all`
so every step prints (the `new` mode collapses repeats of the same tool name).

Idempotent. Usage:
    python deploy/hermes/patch-tool-display.py [path/to/agent/display.py]
Default path: ~/.hermes/hermes-agent/agent/display.py
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT = Path.home() / ".hermes" / "hermes-agent" / "agent" / "display.py"

EDITS = [
    (
        'for fallback_key in ("query", "text", "command", "path", "name", "prompt", "code", "goal"):',
        'for fallback_key in ("action", "query", "text", "command", "path", "name", "prompt", "code", "goal"):',
    ),
    (
        '    preview = build_tool_preview(tool_name, args) or ""\n'
        '    return _wrap(f"┊ ⚡ {tool_name[:9]:9} {_trunc(preview, 35)}  {dur}")',
        "    # MCP tools register as mcp_<server>_<tool>; show the bare tool name.\n"
        '    display_name = tool_name.split("_", 2)[-1] if tool_name.startswith("mcp_") else tool_name\n'
        '    preview = build_tool_preview(tool_name, args) or ""\n'
        '    return _wrap(f"┊ ⚡ {display_name[:12]:12} {_trunc(preview, 40)}  {dur}")',
    ),
]


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 1
    text = target.read_text()
    changed = 0
    for old, new in EDITS:
        if new in text:
            continue
        if old not in text:
            print(
                f"anchor not found (Hermes version drift?): {old[:60]}...",
                file=sys.stderr,
            )
            return 1
        text = text.replace(old, new, 1)
        changed += 1
    if changed:
        target.write_text(text)
    print(
        f"{target}: {changed} edit(s) applied"
        + (" (already patched)" if not changed else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
