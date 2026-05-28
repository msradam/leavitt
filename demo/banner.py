"""Leavitt README banner: a 4-second diagnosis-in-motion ticker.

Title up top, then the story plays underneath: an alert fires, the four sources
tick on, the evidence correlates, the root cause lands. Observatory palette.
Loops. Recorded by demo/cassettes/banner.tape.
"""

from __future__ import annotations

import time

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

STAR = "#F6B755"
MARGIN = "#CB9A5B"
MOON = "#5D8BB4"
TEXT = "#DBD7CF"
DIM = "#78746D"
FAINT = "#4A545D"


def title() -> Group:
    return Group(
        Text(""),
        Align.center(Text("✦  L E A V I T T", style=f"bold {TEXT}")),
        Align.center(Text("on-call AI agent  ·  turns alerts into answers", style=DIM)),
        Text(""),
    )


def beat(line1: Text, line2: Text | None = None) -> Group:
    pad = Text("")
    parts: list = [title(), pad, Align.center(line1)]
    if line2 is not None:
        parts.append(Align.center(line2))
    else:
        parts.append(pad)
    parts.append(pad)
    return Group(*parts)


def alert(intensity: str) -> Group:
    return beat(Text(f"▶  alert fired  ·  webstore", style=f"bold {intensity}"))


def reading(n: int) -> Group:
    sources = ["metrics", "logs", "client load", "deploys"]
    parts = []
    for i, s in enumerate(sources):
        mark = "✓" if i < n else "·"
        parts.append((f"  {mark} {s}  ", STAR if i < n else FAINT))
    return beat(
        Text("  reading the dashboards…  ", style=DIM),
        Text.assemble(*parts),
    )


def correlating() -> Group:
    return beat(
        Text("correlate evidence  ·  4/4 sources usable", style=MOON),
        Text("…", style=DIM),
    )


def resolved() -> Group:
    return beat(
        Text("✦  root cause  ·  product-reviews  ·  LLM rate-limit (429s)", style=f"bold {STAR}"),
        Text("resolved  ·  evidence-grounded  ·  read-only", style=MARGIN),
    )


def main() -> None:
    console = Console()
    # One designed pass that fits the VHS capture window, with the verdict held
    # as the dominant frame. Loops afterward so any overrun is more verdict, not
    # confusion. Recording start (after uv warm-up) drops into the pass cleanly.
    with Live(title(), console=console, refresh_per_second=24, screen=True) as live:
        for _ in range(6):
            live.update(title()); time.sleep(0.20)
            for c in (FAINT, MARGIN, STAR):
                live.update(alert(c)); time.sleep(0.10)
            time.sleep(0.10)
            for n in range(5):
                live.update(reading(n)); time.sleep(0.14)
            live.update(correlating()); time.sleep(0.30)
            live.update(resolved()); time.sleep(2.20)  # the payoff, held


if __name__ == "__main__":
    main()
