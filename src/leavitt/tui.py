"""Live terminal view of an investigation.

Drives the FSM and renders, in real time, the current phase, each source as it
returns (ok / degraded / down / malformed), and the triage report as it
resolves. The palette is Leavitt's observatory theme: a plate-black ground, bone
ink, and a single sodium-amber star as the accent, with a cool moon-blue for the
counter-tone (a source down, an inconclusive finding).
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

# Leavitt observatory palette (brand handoff): a single sodium-amber star on a
# plate-black ground, with a cool "moon" blue as the counter-tone. Observatories
# light their domes amber to preserve dark adaptation; the accent is that light.
ACCENT = "#F6B755"  # star, sodium amber, the one accent: brand, borders, active
OK = "#F6B755"  # source ok / phase done (lit)
WARN = "#CB9A5B"  # marginalia amber, degraded / recovery
CRIT = "#5D8BB4"  # moon blue, the cool counter-tone: source down / inconclusive
YELLOW = "#CB9A5B"  # malformed source
TEXT = "#DBD7CF"  # bone ink
DIM = "#78746D"  # labels / secondary
FAINT = "#4A545D"  # pending / idle
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
        self.driver: str | None = None

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
        show_conf = conf and conf != "none"
        sub = Text(f"\nconfidence: {conf}", style=DIM) if show_conf else Text("")
        return Panel(
            Group(t, sub), title="sources", border_style=FAINT, title_align="left"
        )

    def _report_from_state(self) -> dict | None:
        """The tracker serializes report fields at the top level (the nested
        ``report`` dict is not always persisted), so rebuild the report view from
        them when driving an external agent off the audit trail."""
        s = self.state
        if not (
            s.get("root_cause") or s.get("affected_services") or s.get("confidence")
        ):
            return None
        usable, total = int(s.get("usable_count") or 0), int(s.get("source_count") or 0)
        return {
            "disposition": s.get("disposition") or _disposition(s),
            "confidence": s.get("confidence", ""),
            "root_cause": s.get("root_cause", ""),
            "affected_services": s.get("affected_services", []),
            "sources_usable": [None] * usable,
            "sources_queried": [None] * total,
            "recovery_events": s.get("recovery_events", []),
        }

    def _report(self) -> Panel:
        r = self.state.get("report")
        # form_hypothesis fills the report fields; produce_report adds the
        # grounding guard. Show the report once either has run so a driver that
        # stops after the hypothesis still surfaces a conclusion.
        if not r and self.done & {"form_hypothesis", "produce_report"}:
            r = self._report_from_state()
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
        parts = [("leavitt", f"bold {ACCENT}"), ("  on-call incident triage", DIM)]
        if self.driver:
            parts += [("   driver: ", DIM), (self.driver, f"bold {ACCENT}")]
        parts += [("\n", DIM), (self.query, TEXT)]
        header = Text.assemble(*parts)
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


def _tracker_dir():
    from pathlib import Path

    base = os.getenv("LEAVITT_TRACKER_DIR") or str(Path.home() / ".theodosia")
    return Path(base) / "leavitt"


def _read_run(log) -> tuple[set[str], str | None, dict]:
    """Parse a Theodosia run log into (completed actions, in-flight action, state)."""
    import json

    done: set[str] = set()
    current: str | None = None
    state: dict = {}
    for line in log.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "begin_entry":
            current = e.get("action")
        elif e.get("type") == "end_entry":
            done.add(e.get("action"))
            current = None
            if e.get("state"):
                state = e["state"]
    return done, current, state


async def investigate_via_hermes(query: str, with_load: bool = False) -> dict:
    """Drive a headless Hermes (Nemotron on Crusoe) run against the Leavitt MCP and
    render the enforced FSM live off Theodosia's audit trail. Hermes is the agent;
    this is its front-end. We read the tracker, not Hermes stdout, so the agent's
    own banner/skills never reach the view. With ``with_load``, a live k6 load pane
    sits above the investigation, one console for the system and the agent reading
    it."""
    import shutil
    import time
    from pathlib import Path

    from rich.layout import Layout

    from leavitt.loadview import LoadView

    store = _tracker_dir()
    before = {p.name for p in store.iterdir()} if store.exists() else set()
    hermes = shutil.which("hermes") or str(Path.home() / ".local" / "bin" / "hermes")

    view = View(query)
    view.driver = "Hermes · Nemotron · Crusoe"
    console = Console()
    load = LoadView() if with_load else None
    last_load = 0.0

    def render_all():
        if load is None:
            return view.render()
        root = Layout()
        root.split_column(
            Layout(load.render(endpoints=True), name="load", size=16),
            Layout(view.render(), name="agent"),
        )
        return root

    proc = await asyncio.create_subprocess_exec(
        hermes,
        "-t",
        "leavitt",
        "-z",
        query,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    run_dir: Path | None = None

    def refresh() -> None:
        nonlocal run_dir
        if store.exists():
            # Hermes also creates an empty session dir, so don't latch onto the
            # first new dir; each tick pick the new run with the most logged data.
            best, best_size = None, 0
            for p in store.iterdir():
                if not p.is_dir() or p.name in before:
                    continue
                log = p / "log.jsonl"
                size = log.stat().st_size if log.exists() else 0
                if size > best_size:
                    best, best_size = p, size
            if best is not None:
                run_dir = best
        if run_dir is not None:
            done, current, state = _read_run(run_dir / "log.jsonl")
            view.done, view.current = done, current
            if state:
                view.state = state

    with Live(
        render_all(), refresh_per_second=12, screen=True, console=console
    ) as live:
        while proc.returncode is None:
            if load is not None and time.monotonic() - last_load >= 0.9:
                load.poll()
                last_load = time.monotonic()
            refresh()
            live.update(render_all())
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.4)
            except asyncio.TimeoutError:
                pass
        if load is not None:
            load.poll()
        refresh()
        view.current = None
        live.update(render_all())
    console.print(render_all())
    return view.state.get("report") or {}


def run_agent(query: str, with_load: bool = False) -> int:
    asyncio.run(investigate_via_hermes(query, with_load=with_load))
    return 0
