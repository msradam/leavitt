"""Leavitt README banner: the wordmark and a slowly pulsing Cepheid star.

The one permitted motion (period = luminosity). Rendered in the observatory
palette and recorded to a small gif by demo/cassettes/banner.tape.
"""

from __future__ import annotations

import time

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

STAR = "#F6B755"
MOON = "#5D8BB4"
TEXT = "#DBD7CF"
DIM = "#78746D"
FAINT = "#4A545D"

# A pulse, dim to bright and back. Period = luminosity.
PULSE = [
    "#4A545D",
    "#6E6347",
    "#937340",
    "#BC9248",
    "#E2AC52",
    "#F6B755",
    "#E2AC52",
    "#BC9248",
    "#937340",
    "#6E6347",
]


def frame(star_color: str) -> Group:
    return Group(
        Text(""),
        Align.center(Text("✦", style=f"bold {star_color}")),
        Text(""),
        Align.center(Text("L E A V I T T", style=f"bold {TEXT}")),
        Align.center(
            Text("on-call AI agent that turns alerts into answers", style=DIM)
        ),
        Text(""),
        Align.center(
            Text.assemble(
                ("incident triage · built on Theodosia", DIM),
                ("      ", DIM),
                ("“Leave it running.”", f"italic {STAR}"),
            )
        ),
    )


def main() -> None:
    console = Console()
    with Live(
        frame(PULSE[0]), console=console, refresh_per_second=20, screen=True
    ) as live:
        for _ in range(8):  # run long enough to outlast `uv run` cold start
            for color in PULSE:
                live.update(frame(color))
                time.sleep(0.16)


if __name__ == "__main__":
    main()
