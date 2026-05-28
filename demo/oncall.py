"""Leavitt on-call feed: an alert arrives, the agent runs, the report goes out.

What an operator sees with Hermes's webhook gateway running. Recorded by
demo/cassettes/oncall.tape.
"""

from __future__ import annotations

import time

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

STAR = "#F6B755"
MARGIN = "#CB9A5B"
MOON = "#5D8BB4"
TEXT = "#DBD7CF"
DIM = "#78746D"
FAINT = "#4A545D"

# (delay before showing, icon, icon color, [(segment text, color)])
EVENTS = [
    (0.6, "◇", MOON,   [("03:14:02  ", DIM), ("webhook   ", DIM), ("alert_received  ", TEXT), ("webstore error rate spike", STAR)]),
    (0.4, "▶", STAR,   [("03:14:02  ", DIM), ("triage    ", DIM), ("started         ", TEXT), ("#7a3f  hermes / nemotron · 4 sources", DIM)]),
    (1.6, "✦", STAR,   [("03:14:14  ", DIM), ("triage    ", DIM), ("complete        ", TEXT), ("#7a3f  resolved  ", STAR), ("product-reviews · LLM rate-limit", TEXT)]),
    (0.3, "→", MARGIN, [("03:14:14  ", DIM), ("discord   ", DIM), ("posted to ", TEXT), ("#leavitt-reports", MOON)]),
    (1.0, "◇", MOON,   [("03:18:55  ", DIM), ("webhook   ", DIM), ("alert_received  ", TEXT), ("cart returning 502s", STAR)]),
    (0.4, "▶", STAR,   [("03:18:55  ", DIM), ("triage    ", DIM), ("started         ", TEXT), ("#b9c1  hermes / nemotron · 4 sources", DIM)]),
    (1.4, "✦", STAR,   [("03:19:08  ", DIM), ("triage    ", DIM), ("complete        ", TEXT), ("#b9c1  resolved  ", STAR), ("cart service · backend errors", TEXT)]),
    (0.3, "→", MARGIN, [("03:19:08  ", DIM), ("discord   ", DIM), ("posted to ", TEXT), ("#leavitt-reports", MOON)]),
    (1.0, "◇", MOON,   [("03:24:11  ", DIM), ("webhook   ", DIM), ("alert_received  ", TEXT), ("checkout p95 above threshold", STAR)]),
    (0.4, "▶", STAR,   [("03:24:11  ", DIM), ("triage    ", DIM), ("started         ", TEXT), ("#e3d2  hermes / nemotron · 4 sources", DIM)]),
    (1.5, "⚠", MARGIN, [("03:24:23  ", DIM), ("triage    ", DIM), ("complete        ", TEXT), ("#e3d2  degraded ", MARGIN), (" grafana unreachable · 3/4 usable", TEXT)]),
    (0.3, "→", MARGIN, [("03:24:23  ", DIM), ("discord   ", DIM), ("posted to ", TEXT), ("#leavitt-reports", MOON)]),
]

RULE = "  " + "─" * 80


def header() -> Group:
    return Group(
        Text(""),
        Text("  ✦  Leavitt  ·  On-Call", style=f"bold {TEXT}"),
        Text("  listening on /webhooks/leavitt-alert  ·  read-only  ·  unattended  ·  audited", style=DIM),
        Text(""),
        Text(RULE, style=FAINT),
        Text(""),
    )


def footer(resolved: int, degraded: int) -> Group:
    return Group(
        Text(""),
        Text(RULE, style=FAINT),
        Text(
            f"  audit  ·  past 24h:  {resolved + degraded} runs  ·  {resolved} resolved  ·  {degraded} degraded  ·  0 confident-wrong",
            style=MARGIN,
        ),
        Text("  Leave it to Leavitt.", style=f"italic {STAR}"),
        Text(""),
    )


def line(icon: str, icon_color: str, segs) -> Text:
    t = Text(f"  {icon}  ", style=f"bold {icon_color}")
    for s, c in segs:
        t.append(s, style=c)
    return t


def frame(lines, resolved: int, degraded: int) -> Group:
    return Group(header(), *lines, footer(resolved, degraded))


def main() -> None:
    console = Console()
    lines: list[Text] = []
    # Seed with prior 24h so the audit footer reflects a real on-call day; the
    # three visible runs increment it.
    resolved, degraded = 20, 2
    with Live(frame(lines, resolved, degraded), console=console, refresh_per_second=24, screen=True) as live:
        time.sleep(0.5)
        for delay, icon, color, segs in EVENTS:
            time.sleep(delay)
            lines.append(line(icon, color, segs))
            if icon == "✦":
                resolved += 1
            elif icon == "⚠":
                degraded += 1
            live.update(frame(lines, resolved, degraded))
        time.sleep(12.0)  # hold the final feed visible through the capture window


if __name__ == "__main__":
    main()
