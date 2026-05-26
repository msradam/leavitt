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
ACCENT, OK, PURPLE, TEXT, DIM = (
    "#5794F2",
    "#73BF69",
    "#B877D9",
    "#CCCCDC",
    "#8E8E8E",
)
BLOCKS = " ▁▂▃▄▅▆▇█"
WINDOW = 70


def _get(expr: str):
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    import json

    with urllib.request.urlopen(url, timeout=2) as r:
        return json.load(r)["data"]["result"]


def _q(expr: str) -> float:
    try:
        res = _get(expr)
        return sum(float(s["value"][1]) for s in res) if res else 0.0
    except Exception:
        return float("nan")


def _series(expr: str) -> list[tuple[str, float]]:
    try:
        res = _get(expr)
        out = [(s["metric"].get("name", "?"), float(s["value"][1])) for s in res]
        return sorted(out, key=lambda x: x[1], reverse=True)
    except Exception:
        return []


def _spark(vals: deque[float], color: str) -> Text:
    nums = [v for v in vals if v == v]  # drop NaN
    hi = max(nums) if nums else 1.0
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


def _bytes(n: float) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:4.0f} {unit}" if unit == "B" else f"{n:4.1f} {unit}"
        n /= 1024
    return f"{n:.1f} MB"


def render(reqs, iters, data_in, total, vus, endpoints) -> Panel:
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
    t.add_row(
        "data in/s",
        Text(_bytes(_last(data_in)), style=f"bold {PURPLE}"),
        _spark(data_in, PURPLE),
    )

    ep = Table.grid(padding=(0, 2))
    ep.add_column(justify="right", style=DIM, no_wrap=True)
    ep.add_column(no_wrap=True)
    ep.add_column(justify="right", style=TEXT, no_wrap=True)
    hi = max((v for _, v in endpoints), default=1.0) or 1.0
    for name, val in endpoints[:5]:
        bar = "█" * max(1, round(val / hi * 22))
        ep.add_row(name, Text(bar, style=ACCENT), f"{val:4.1f}/s")

    foot = Text.assemble(
        (f"{int(total):,} requests", f"bold {TEXT}"),
        (" total · ", DIM),
        (f"{int(vus)} ", f"bold {TEXT}"),
        ("virtual users", DIM),
    )
    head = Text.assemble(
        ("k6 client load", f"bold {ACCENT}"),
        ("   live · Prometheus · OpenTelemetry demo", DIM),
    )
    return Panel(
        Group(
            head,
            Text(""),
            t,
            Text(""),
            Text("busiest endpoints", style=DIM),
            ep,
            Text(""),
            foot,
        ),
        border_style=ACCENT,
        title="load",
        title_align="left",
    )


def main() -> int:
    reqs: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
    iters: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
    data_in: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
    total = vus = 0.0
    endpoints: list[tuple[str, float]] = []
    console = Console()
    with Live(
        render(reqs, iters, data_in, total, vus, endpoints),
        console=console,
        refresh_per_second=8,
        screen=True,
    ) as live:
        while True:
            reqs.append(_q("sum(rate(k6_http_reqs_total[15s]))"))
            iters.append(_q("sum(rate(k6_iterations_total[15s]))"))
            data_in.append(_q("sum(rate(k6_data_received_total[15s]))"))
            total = _q("sum(k6_http_reqs_total)")
            vus = _q("sum(k6_vus)")
            endpoints = _series("sum by (name)(rate(k6_http_reqs_total[20s]))")
            live.update(render(reqs, iters, data_in, total, vus, endpoints))
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
