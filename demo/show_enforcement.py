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

AMBER = "dark_orange"
c = Console()


async def main():
    c.print(
        Panel(
            Text.assemble(
                ("leavitt", f"bold {AMBER}"),
                ("  Theodosia transition enforcement", "grey70"),
            ),
            border_style="grey42",
        )
    )

    async def _quiet(_message):  # swallow the server's per-step log notifications
        pass

    async with Client(mount_server(upstream={}), log_handler=_quiet) as client:
        await asyncio.sleep(1.2)
        c.print("\n[white]An agent tries to skip straight to the conclusion:[/]")
        c.print("[grey70]  step(action=[/][bold]produce_report[/][grey70])[/]")
        await asyncio.sleep(1.6)
        res = await client.call_tool("step", {"action": "produce_report"})
        sc = res.structured_content or {}
        c.print(
            Panel(
                Text.assemble(
                    ("✗ refused  ", "bold red"),
                    (f"{sc.get('error')}\n", "red"),
                    (f"{sc.get('message', '')}", "grey70"),
                ),
                title="Theodosia",
                border_style="red",
                title_align="left",
            )
        )
        await asyncio.sleep(2.2)
        c.print(
            "[white]It cannot reach a conclusion without first reading and correlating evidence.[/]"
        )
        c.print(
            "[white]There is no write action in the graph, so it cannot act on what it observes.[/]"
        )
        await asyncio.sleep(2.5)


if __name__ == "__main__":
    asyncio.run(main())
