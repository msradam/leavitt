"""Live k6 client-load monitor for the ops-console demo.

Polls Prometheus (where k6 remote-writes its client-side metrics) once a second
and renders request rate and iteration rate as scrolling sparklines, with a
running request total. This is a demo prop: the same k6_* metrics Leavitt reads
as its client_load source, shown as a live dashboard beside the agent.
Grafana-dark palette to match the Leavitt skin.

    uv run python demo/loadmon.py            # defaults to http://localhost:9090
    PROM=http://host:9090 uv run python demo/loadmon.py
"""

from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

PROM = os.environ.get("PROM", "http://localhost:9090")
ACCENT, OK, WARN, CRIT, TEXT, DIM = (
    "#5794F2",
    "#73BF69",
    "#FF9830",
    "#F2495C",
    "#CCCCDC",
    "#8E8E8E",
)
BLOCKS = " ▁▂▃▄▅▆▇█"
WINDOW = 70


def _q(expr: str) -> float:
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            import json

            res = json.load(r)["data"]["result"]
            return sum(float(s["value"][1]) for s in res) if res else 0.0
    except Exception:
        return float("nan")


def _spark(vals: deque[float], color: str, peak: float | None = None) -> Text:
    nums = [v for v in vals if v == v]  # drop NaN
    hi = peak if peak else (max(nums) if nums else 1.0)
    hi = hi or 1.0
    t = Text()
    for v in vals:
        if v != v:
            t.append(" ", style=DIM)
        else:
            idx = min(len(BLOCKS) - 1, int(v / hi * (len(BLOCKS) - 1)))
            t.append(BLOCKS[idx], style=color)
    return t


def _last(vals: deque[float]) -> float:
    return next((v for v in reversed(vals) if v == v), 0.0)


def render(reqs: deque[float], iters: deque[float], total: float, vus: float) -> Panel:
    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style=DIM, no_wrap=True)
    t.add_column(justify="right", no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_row(
        "requests/s",
        Text(f"{_last(reqs):5.1f}", style=f"bold {ACCENT}"),
        _spark(reqs, ACCENT),
    )
    t.add_row(
        "iterations/s",
        Text(f"{_last(iters):5.1f}", style=f"bold {OK}"),
        _spark(iters, OK),
    )
    t.add_row("total reqs", Text(f"{int(total):,}", style=f"bold {TEXT}"), Text(""))
    t.add_row("active VUs", Text(f"{int(vus)}", style=f"bold {TEXT}"), Text(""))
    head = Text.assemble(
        ("k6 client load", f"bold {ACCENT}"),
        ("   live · Prometheus · OpenTelemetry demo", DIM),
    )
    return Panel(
        Group(head, Text(""), t),
        border_style=ACCENT,
        title="load",
        title_align="left",
    )


def main() -> int:
    reqs: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
    iters: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
    total = vus = 0.0
    console = Console()
    with Live(
        render(reqs, iters, total, vus),
        console=console,
        refresh_per_second=8,
        screen=True,
    ) as live:
        while True:
            reqs.append(_q("sum(rate(k6_http_reqs_total[15s]))"))
            iters.append(_q("sum(rate(k6_iterations_total[15s]))"))
            total = _q("sum(k6_http_reqs_total)")
            vus = _q("sum(k6_vus)")
            live.update(render(reqs, iters, total, vus))
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
