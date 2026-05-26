"""Past FSM sessions, the audit trail.

Every tracked run writes a Burr log under Theodosia's tracker store
(``~/.theodosia/leavitt`` by default). This reads those logs and shows what each
session did: the steps that ran, where it stopped, and the report it produced. A
session that stalled mid-FSM shows up as incomplete rather than as a wrong
answer, the failure is visible, not silent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Leavitt observatory palette (brand handoff).
ACCENT = "#F6B755"  # sodium-amber star
OK = "#F6B755"
WARN = "#CB9A5B"
CRIT = "#5D8BB4"  # moon blue
TEXT = "#DBD7CF"
DIM = "#78746D"
FAINT = "#4A545D"
TERMINAL = "produce_report"


def _store() -> Path:
    base = os.getenv("LEAVITT_TRACKER_DIR") or str(Path.home() / ".theodosia")
    return Path(base) / "leavitt"


def _parse(run_dir: Path) -> dict | None:
    log = run_dir / "log.jsonl"
    if not log.exists() or log.stat().st_size == 0:
        return None
    actions: list[str] = []
    query, started, ended, state = None, None, None, {}
    for line in log.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "begin_entry":
            actions.append(e.get("action"))
            started = started or e.get("start_time")
            if e.get("action") == "receive_query":
                ins = e.get("inputs") or {}
                query = ins.get("query") or ins.get("question")
        elif e.get("type") == "end_entry":
            state = e.get("state") or state
            ended = e.get("end_time")
    if not actions:
        return None
    # Derive the report view from top-level state fields; the nested ``report``
    # dict is not always serialized into the tracked state, but these are.
    report = {
        "disposition": state.get("disposition") or "",
        "root_cause": state.get("root_cause") or "",
        "affected_services": state.get("affected_services") or [],
        "confidence": state.get("confidence") or "",
        "usable": int(state.get("usable_count") or 0),
        "total": int(state.get("source_count") or 0),
        "recovery_events": state.get("recovery_events") or [],
    }
    return {
        "id": run_dir.name,
        "started": started or "",
        "ended": ended or "",
        "query": query or "",
        "actions": actions,
        "last": actions[-1],
        "complete": actions[-1] == TERMINAL,
        "state": state,
        "report": report,
    }


def _runs() -> list[dict]:
    store = _store()
    if not store.exists():
        return []
    runs = [r for d in store.iterdir() if d.is_dir() and (r := _parse(d))]
    return sorted(runs, key=lambda r: r["started"], reverse=True)


def list_sessions(limit: int = 20) -> int:
    c = Console()
    runs = _runs()
    if not runs:
        c.print('[#8E8E8E]No sessions yet. Run `leavitt investigate "..."`.[/]')
        return 0
    t = Table(
        title=Text("leavitt sessions", style=f"bold {ACCENT}"),
        title_justify="left",
        border_style=FAINT,
    )
    t.add_column("when", style=DIM, no_wrap=True)
    t.add_column("query", style=TEXT)
    t.add_column("outcome")
    t.add_column("steps", justify="right", style=DIM)
    for r in runs[:limit]:
        when = r["started"][:19].replace("T", " ")
        if r["complete"]:
            disp = (r["report"].get("disposition") or "").lower()
            style = {"resolved": OK, "degraded": WARN, "inconclusive": CRIT}.get(
                disp, TEXT
            )
            cause = (r["report"].get("root_cause") or "")[:46]
            outcome = Text.assemble(
                (disp or "reported", f"bold {style}"), ("  " + cause, DIM)
            )
        else:
            outcome = Text(f"incomplete @ {r['last']}", style=WARN)
        t.add_row(when, (r["query"] or "")[:44], outcome, str(len(r["actions"])))
    c.print(t)
    c.print(
        f"[#8E8E8E]{len(runs)} sessions in {_store()}. `leavitt sessions <id>` for the full trail.[/]"
    )
    return 0


def show_session(prefix: str) -> int:
    c = Console()
    runs = _runs()
    match = next((r for r in runs if r["id"].startswith(prefix)), None)
    if not match:
        c.print(f"[red]No session matching '{prefix}'.[/]")
        return 1
    head = Text.assemble(
        ("leavitt session ", f"bold {ACCENT}"),
        (match["id"][:8], DIM),
        (f"   {match['started'][:19].replace('T', ' ')}\n", DIM),
        (match["query"], TEXT),
    )
    steps = Table.grid(padding=(0, 1))
    for a in match["actions"]:
        steps.add_row(Text("✓", style=OK), Text(a, style=TEXT))
    if not match["complete"]:
        steps.add_row(
            Text("✗", style=WARN),
            Text(f"stopped here (never reached {TERMINAL})", style=WARN),
        )
    r = match["report"]
    report_t = Table.grid(padding=(0, 2))
    if match["complete"]:
        disp = (r.get("disposition") or "").lower()
        style = {"resolved": OK, "degraded": WARN, "inconclusive": CRIT}.get(disp, TEXT)
        report_t.add_row(
            Text("disposition", style=DIM),
            Text(disp or "reported", style=f"bold {style}"),
        )
        report_t.add_row(
            Text("confidence", style=DIM), Text(r.get("confidence", ""), style=TEXT)
        )
        report_t.add_row(
            Text("root cause", style=DIM),
            Text((r.get("root_cause") or "")[:90], style=TEXT),
        )
        report_t.add_row(
            Text("affected", style=DIM),
            Text(", ".join(r.get("affected_services", [])) or "-", style=TEXT),
        )
        report_t.add_row(
            Text("sources", style=DIM),
            Text(f"{r.get('usable', 0)}/{r.get('total', 0)} usable", style=TEXT),
        )
        for ev in r.get("recovery_events", []):
            report_t.add_row(Text("recovery", style=DIM), Text(ev[:80], style=WARN))
    else:
        report_t.add_row(
            Text("report", style=DIM),
            Text("none (session did not complete)", style=WARN),
        )
    c.print(
        Group(
            Panel(head, border_style=FAINT),
            Panel(steps, title="steps run", border_style=FAINT, title_align="left"),
            Panel(report_t, title="report", border_style=ACCENT, title_align="left"),
        )
    )
    return 0
