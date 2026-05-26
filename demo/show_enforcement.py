"""Short clip: Theodosia refuses an invalid transition.

An MCP client tries to jump straight to a conclusion. The server refuses,
structurally, and points at the only reachable next action. There is no prompt
that talks past this; the transition simply is not allowed.
"""

from __future__ import annotations

# ruff: noqa: E402 - logging must be muted before fastmcp/mcp import
import asyncio
import logging
import os

# Keep the MCP server's step logging out of the clip.
os.environ["FASTMCP_LOG_LEVEL"] = "CRITICAL"
logging.disable(logging.WARNING)

from fastmcp import Client
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from leavitt.app import mount_server

# Leavitt observatory palette (brand handoff).
STAR = "#F6B755"  # sodium-amber star
MOON = "#5D8BB4"  # cool counter-tone: the boundary, the refusal
TEXT = "#DBD7CF"  # bone ink
DIM = "#78746D"
FAINT = "#4A545D"
c = Console()


async def main():
    c.print(
        Panel(
            Text.assemble(
                ("leavitt", f"bold {STAR}"),
                ("  Theodosia transition enforcement", DIM),
            ),
            border_style=FAINT,
        )
    )

    async def _quiet(_message):  # swallow the server's per-step log notifications
        pass

    async with Client(mount_server(upstream={}), log_handler=_quiet) as client:
        await asyncio.sleep(1.2)
        c.print("\n[#DBD7CF]An agent tries to skip straight to the conclusion:[/]")
        c.print("[#78746D]  step(action=[/][bold]produce_report[/][#78746D])[/]")
        await asyncio.sleep(1.6)
        res = await client.call_tool("step", {"action": "produce_report"})
        sc = res.structured_content or {}
        c.print(
            Panel(
                Text.assemble(
                    ("✗ refused  ", f"bold {MOON}"),
                    (f"{sc.get('error')}\n", MOON),
                    (f"{sc.get('message', '')}", DIM),
                ),
                title="Theodosia",
                border_style=MOON,
                title_align="left",
            )
        )
        await asyncio.sleep(2.2)
        c.print(
            "[#DBD7CF]It cannot reach a conclusion without first reading and correlating the evidence.[/]"
        )
        c.print("[#DBD7CF]Every diagnosis it gives is one it did the reading for.[/]")
        await asyncio.sleep(2.5)


if __name__ == "__main__":
    asyncio.run(main())
