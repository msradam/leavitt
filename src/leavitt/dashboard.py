"""Live on-call dashboard over the audit trail.

Reads Theodosia's tracker (``~/.theodosia/leavitt``) and shows recent
investigations and their dispositions, refreshing in place. Operators leave it
open on the CLI; scheduled and alert-triggered runs land here as they happen. No
web server, the same ledger `leavitt sessions` reads, as a live board.
"""

from __future__ import annotations

import time

from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.text import Text

from leavitt.sessions import _runs, _store

STAR, MARGIN, MOON, TEXT, DIM, FAINT = (
    "#F6B755",
    "#CB9A5B",
    "#5D8BB4",
    "#DBD7CF",
    "#78746D",
    "#4A545D",
)
DISP_STYLE = {"resolved": STAR, "degraded": MARGIN, "inconclusive": MOON}


def _disp(run: dict) -> str:
    if not run["complete"]:
        return f"incomplete @ {run['last']}"
    rep = run["report"]
    if rep["disposition"]:
        return rep["disposition"]
    if rep["usable"] == 0:
        return "inconclusive"
    return "resolved" if rep["confidence"] == "full" else "degraded"


def render(limit: int = 16) -> Group:
    runs = _runs()
    head = Text.assemble(
        ("✦ Leavitt", f"bold {STAR}"),
        ("  on-call dashboard", DIM),
        (f"   {len(runs)} investigations · {_store()}", DIM),
    )

    counts: dict[str, int] = {}
    for r in runs:
        d = _disp(r)
        key = d.split(" @ ")[0] if d.startswith("incomplete") else d
        counts[key] = counts.get(key, 0) + 1
    order = [
        ("resolved", STAR),
        ("degraded", MARGIN),
        ("inconclusive", MOON),
        ("incomplete", DIM),
    ]
    stats = Text("  ")
    for name, color in order:
        n = counts.get(name, 0)
        stats.append(f"{name} ", style=DIM)
        stats.append(f"{n}   ", style=f"bold {color}" if n else FAINT)

    t = Table.grid(padding=(0, 3))
    t.add_column(style=DIM, no_wrap=True)  # when
    t.add_column(style=TEXT, no_wrap=True)  # incident
    t.add_column(no_wrap=True)  # disposition
    t.add_column(style=DIM, no_wrap=True)  # cause
    t.add_column(justify="right", style=DIM, no_wrap=True)  # steps
    t.add_row(
        Text("when", style=FAINT),
        Text("incident", style=FAINT),
        Text("disposition", style=FAINT),
        Text("cause", style=FAINT),
        Text("steps", style=FAINT),
    )
    for r in runs[:limit]:
        when = r["started"][11:19] if len(r["started"]) >= 19 else r["started"][:8]
        d = _disp(r)
        base = d.split(" @ ")[0] if d.startswith("incomplete") else d
        style = DISP_STYLE.get(base, MARGIN if base == "incomplete" else DIM)
        cause = (r["report"]["root_cause"] or "")[:46] if r["complete"] else ""
        t.add_row(
            when,
            (r["query"] or "")[:40],
            Text(d[:24], style=f"bold {style}"),
            cause,
            str(len(r["actions"])),
        )
    return Group(head, Text(""), stats, Text(""), t)


def run(once: bool = False) -> int:
    console = Console()
    if once:
        console.print(render())
        return 0
    try:
        with Live(render(), console=console, refresh_per_second=4, screen=True) as live:
            while True:
                time.sleep(2.0)
                live.update(render())
    except KeyboardInterrupt:
        pass
    return 0
