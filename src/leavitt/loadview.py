"""Live k6 client-load view, polling Prometheus.

Shared by the standalone monitor (``demo/loadmon.py``) and the agent console
(``leavitt agent --load``). The same k6 metrics Leavitt reads as its client_load
source, rendered in the observatory palette.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import deque

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ACCENT, OK, PURPLE, TEXT, DIM = "#F6B755", "#CB9A5B", "#5D8BB4", "#DBD7CF", "#78746D"
BLOCKS = " ▁▂▃▄▅▆▇█"
WINDOW = 70


def _get(prom: str, expr: str):
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(url, timeout=2) as r:
        return json.load(r)["data"]["result"]


def _q(prom: str, expr: str) -> float:
    try:
        res = _get(prom, expr)
        return sum(float(s["value"][1]) for s in res) if res else 0.0
    except Exception:
        return float("nan")


def _series(prom: str, expr: str) -> list[tuple[str, float]]:
    try:
        res = _get(prom, expr)
        out = [(s["metric"].get("name", "?"), float(s["value"][1])) for s in res]
        return sorted(out, key=lambda x: x[1], reverse=True)
    except Exception:
        return []


def _spark(vals: deque[float], color: str) -> Text:
    nums = [v for v in vals if v == v]
    hi = (max(nums) if nums else 1.0) or 1.0
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


class LoadView:
    """Polls Prometheus for k6 client-load metrics and renders a live panel."""

    def __init__(self, prom: str | None = None):
        self.prom = prom or os.environ.get("PROM", "http://localhost:9090")
        self.reqs: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
        self.iters: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
        self.data_in: deque[float] = deque([float("nan")] * WINDOW, maxlen=WINDOW)
        self.total = 0.0
        self.vus = 0.0
        self.endpoints: list[tuple[str, float]] = []

    def poll(self) -> None:
        p = self.prom
        self.reqs.append(_q(p, "sum(rate(k6_http_reqs_total[15s]))"))
        self.iters.append(_q(p, "sum(rate(k6_iterations_total[15s]))"))
        self.data_in.append(_q(p, "sum(rate(k6_data_received_total[15s]))"))
        self.total = _q(p, "sum(k6_http_reqs_total)")
        self.vus = _q(p, "sum(k6_vus)")
        self.endpoints = _series(p, "sum by (name)(rate(k6_http_reqs_total[20s]))")

    def render(self, endpoints: bool = True) -> Panel:
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="right", style=DIM, no_wrap=True)
        t.add_column(justify="right", no_wrap=True)
        t.add_column(no_wrap=True)
        t.add_row(
            "requests/s",
            Text(f"{_last(self.reqs):5.1f}", style=f"bold {ACCENT}"),
            _spark(self.reqs, ACCENT),
        )
        t.add_row(
            "iterations/s",
            Text(f"{_last(self.iters):5.1f}", style=f"bold {OK}"),
            _spark(self.iters, OK),
        )
        t.add_row(
            "data in/s",
            Text(_bytes(_last(self.data_in)), style=f"bold {PURPLE}"),
            _spark(self.data_in, PURPLE),
        )

        body = [
            Text.assemble(
                ("k6 client load", f"bold {ACCENT}"),
                ("   live · Prometheus · OpenTelemetry demo", DIM),
            ),
            Text(""),
            t,
        ]
        if endpoints:
            ep = Table.grid(padding=(0, 2))
            ep.add_column(justify="right", style=DIM, no_wrap=True)
            ep.add_column(no_wrap=True)
            ep.add_column(justify="right", style=TEXT, no_wrap=True)
            hi = max((v for _, v in self.endpoints), default=1.0) or 1.0
            for name, val in self.endpoints[:5]:
                ep.add_row(
                    name,
                    Text("█" * max(1, round(val / hi * 22)), style=ACCENT),
                    f"{val:4.1f}/s",
                )
            body += [Text(""), Text("busiest endpoints", style=DIM), ep]

        # NaN can land here when a service fully errors and Prometheus has no
        # series for the k6 totals; int(nan) raises, so guard.
        def _i(x: float) -> int:
            return int(x) if x == x else 0  # x != x is True only for NaN

        body += [
            Text(""),
            Text.assemble(
                (f"{_i(self.total):,} requests", f"bold {TEXT}"),
                (" total · ", DIM),
                (f"{_i(self.vus)} ", f"bold {TEXT}"),
                ("virtual users", DIM),
            ),
        ]
        return Panel(
            Group(*body), border_style=ACCENT, title="load", title_align="left"
        )
