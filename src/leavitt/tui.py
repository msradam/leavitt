"""Live terminal view of an investigation.

Drives the FSM and renders, in real time, the current phase, each source as it
returns (ok / degraded / down / malformed), and the triage report as it
resolves. The palette is Grafana's dark dashboard theme: slate panels, a blue
accent, and Grafana's semantic threshold colors (green/orange/red) on the
disposition, the same colors a Grafana panel uses for ok/warning/critical.
"""

from __future__ import annotations

import asyncio
import os

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import theodosia
from theodosia import UpstreamManager
from theodosia.upstream import reset_upstream
from leavitt.app import build_application, default_upstream

# Grafana dark dashboard palette.
ACCENT = "#5794F2"  # Grafana blue, brand + borders + active phase
OK = "#73BF69"  # Grafana green, resolved / source ok
WARN = "#FF9830"  # Grafana orange, degraded / recovery
CRIT = "#F2495C"  # Grafana red, inconclusive / source down
YELLOW = "#FADE2A"  # Grafana yellow, malformed source
TEXT = "#CCCCDC"  # primary text
DIM = "#8E8E8E"  # labels / secondary
FAINT = "#4B4B52"  # pending / idle
PHASES = [
    "receive_query",
    "enumerate_sources",
    "query_grafana_metrics",
    "query_grafana_logs",
    "query_client_load",
    "query_deployment_context",
    "correlate_evidence",
    "distill_evidence",
    "form_hypothesis",
    "produce_report",
]
PHASE_LABEL = {
    "receive_query": "receive query",
    "enumerate_sources": "enumerate sources",
    "query_grafana_metrics": "read metrics (Prometheus)",
    "query_grafana_logs": "read logs (Loki)",
    "query_client_load": "read client load (k6)",
    "query_deployment_context": "read deployment (flagd)",
    "correlate_evidence": "correlate evidence",
    "distill_evidence": "distill evidence",
    "form_hypothesis": "form hypothesis (LLM)",
    "produce_report": "produce report",
}
SOURCES = [
    ("metrics_result", "metrics (Prometheus)"),
    ("logs_result", "logs (Loki)"),
    ("client_result", "client load (k6)"),
    ("deployment_result", "deployment (flagd)"),
]
STATUS_STYLE = {"ok": OK, "error": CRIT, "malformed": YELLOW}


class View:
    def __init__(self, query: str):
        self.query = query
        self.current: str | None = None
        self.done: set[str] = set()
        self.state: dict = {}

    def update(self, current: str | None, done: str | None, state: dict):
        if current:
            self.current = current
        if done:
            self.done.add(done)
        if state:
            self.state = state

    def _pipeline(self) -> Panel:
        t = Table.grid(padding=(0, 1))
        for p in PHASES:
            if p in self.done:
                icon, style = "✓", OK
            elif p == self.current:
                icon, style = "▶", f"bold {ACCENT}"
            else:
                icon, style = "·", FAINT
            t.add_row(Text(icon, style=style), Text(PHASE_LABEL[p], style=style))
        return Panel(t, title="state machine", border_style=FAINT, title_align="left")

    def _evidence(self) -> Panel:
        t = Table.grid(padding=(0, 2))
        for key, label in SOURCES:
            raw = self.state.get(key)
            if not raw:
                t.add_row(Text("·", style=FAINT), Text(label, style=FAINT), Text(""))
                continue
            status = raw.get("status", "?")
            mark = {"ok": "✓", "error": "✗", "malformed": "⚠"}.get(status, "?")
            style = STATUS_STYLE.get(status, FAINT)
            detail = raw.get("detail") or f"{status}"
            t.add_row(
                Text(mark, style=style),
                Text(label, style=style),
                Text(detail[:54], style=DIM),
            )
        conf = self.state.get("confidence", "")
        sub = Text(f"\nconfidence: {conf}", style=DIM) if conf else Text("")
        return Panel(
            Group(t, sub), title="sources", border_style=FAINT, title_align="left"
        )

    def _report(self) -> Panel:
        r = self.state.get("report")
        if not r:
            hint = (
                "reasoning…" if self.current == "form_hypothesis" else "investigating…"
            )
            return Panel(
                Text(hint, style=FAINT),
                title="report",
                border_style=FAINT,
                title_align="left",
            )
        disp = r.get("disposition", "")
        disp_style = {
            "resolved": f"bold {OK}",
            "degraded": f"bold {WARN}",
            "inconclusive": f"bold {CRIT}",
        }.get(disp, "bold")
        t = Table.grid(padding=(0, 2))
        t.add_row(Text("disposition", style=DIM), Text(disp, style=disp_style))
        t.add_row(
            Text("confidence", style=DIM),
            Text(r.get("confidence", ""), style=TEXT),
        )
        t.add_row(
            Text("root cause", style=DIM),
            Text(r.get("root_cause", "")[:90], style=TEXT),
        )
        t.add_row(
            Text("affected", style=DIM),
            Text(", ".join(r.get("affected_services", [])) or "-", style=TEXT),
        )
        usable, queried = r.get("sources_usable", []), r.get("sources_queried", [])
        t.add_row(
            Text("sources", style=DIM),
            Text(f"{len(usable)}/{len(queried)} usable", style=TEXT),
        )
        for ev in r.get("recovery_events", []):
            t.add_row(Text("recovery", style=DIM), Text(ev[:80], style=WARN))
        return Panel(t, title="triage report", border_style=ACCENT, title_align="left")

    def render(self) -> Group:
        header = Text.assemble(
            ("leavitt", f"bold {ACCENT}"),
            ("  read-only incident triage\n", DIM),
            (self.query, TEXT),
        )
        return Group(
            Panel(header, border_style=FAINT),
            self._pipeline(),
            self._evidence(),
            self._report(),
        )


def _disposition(state: dict) -> str:
    """Propose a disposition from coverage. produce_report's grounding guard has
    the final say: it downgrades 'resolved' if the cause is not in observed signal."""
    if state.get("usable_count", 0) == 0:
        return "inconclusive"
    return "resolved" if state.get("confidence") == "full" else "degraded"


async def investigate(query: str, upstream: dict | None = None) -> dict:
    app = build_application(track=True)  # record the run to the audit trail
    mgr = UpstreamManager(upstream if upstream is not None else default_upstream())
    token = theodosia.bind_upstream(mgr)
    view = View(query)
    console = Console()
    try:
        # screen=True renders in place on the alternate buffer (no scroll
        # duplication while the report panel grows); the final view is printed
        # to the main screen after, so it persists.
        with Live(
            view.render(), refresh_per_second=12, screen=True, console=console
        ) as live:
            action, _, state = await app.astep(
                inputs={"query": query, "max_retries": 1}
            )
            view.update(None, action.name, state)
            live.update(view.render())
            while action.name != "produce_report":
                nxt = app.get_next_action()
                view.update(nxt.name if nxt else None, None, state)
                live.update(view.render())
                if nxt and nxt.name == "produce_report":
                    action, _, state = await app.astep(
                        inputs={"disposition": _disposition(state)}
                    )
                else:
                    action, _, state = await app.astep()
                view.update(None, action.name, state)
                live.update(view.render())
    finally:
        await mgr.aclose()
        reset_upstream(token)
    console.print(view.render())
    return state.get("report", {})


def run(query: str) -> int:
    import logging

    # Mute litellm's import-time AWS pre-load warnings (we don't use Bedrock),
    # so the live view stays clean.
    os.environ.setdefault("LITELLM_LOG", "ERROR")
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    os.environ.setdefault("LEAVITT_PROM_UID", "webstore-metrics")
    os.environ.setdefault("LEAVITT_LOKI_UID", "webstore-logs-loki")
    asyncio.run(investigate(query))
    return 0
