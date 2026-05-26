"""Live k6 client-load monitor for the demo.

Polls Prometheus (where k6 remote-writes its client-side metrics) once a second
and renders request, iteration, and transfer rates as scrolling sparklines with
the busiest endpoints. The same k6_* metrics Leavitt reads as its client_load
source. Observatory palette.

    uv run python demo/loadmon.py            # defaults to http://localhost:9090
    PROM=http://host:9090 uv run python demo/loadmon.py
"""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live

from leavitt.loadview import LoadView


def main() -> int:
    view = LoadView()
    with Live(
        view.render(), console=Console(), refresh_per_second=8, screen=True
    ) as live:
        while True:
            view.poll()
            live.update(view.render())
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
