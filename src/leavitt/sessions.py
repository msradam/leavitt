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

AMBER = "dark_orange"
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
                query = (e.get("inputs") or {}).get("query")
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
        c.print("[grey70]No sessions yet. Run `leavitt investigate \"...\"`.[/]")
        return 0
    t = Table(title=Text("leavitt sessions", style=f"bold {AMBER}"), title_justify="left", border_style="grey42")
    t.add_column("when", style="grey70", no_wrap=True)
    t.add_column("query", style="white")
    t.add_column("outcome")
    t.add_column("steps", justify="right", style="grey70")
    for r in runs[:limit]:
        when = r["started"][:19].replace("T", " ")
        if r["complete"]:
            disp = (r["report"].get("disposition") or "").lower()
            style = {"resolved": "green", "degraded": AMBER, "inconclusive": "red"}.get(disp, "white")
            cause = (r["report"].get("root_cause") or "")[:46]
            outcome = Text.assemble((disp or "reported", f"bold {style}"), ("  " + cause, "grey70"))
        else:
            outcome = Text(f"incomplete @ {r['last']}", style="yellow")
        t.add_row(when, (r["query"] or "")[:44], outcome, str(len(r["actions"])))
    c.print(t)
    c.print(f"[grey50]{len(runs)} sessions in {_store()}. `leavitt sessions <id>` for the full trail.[/]")
    return 0


def show_session(prefix: str) -> int:
    c = Console()
    runs = _runs()
    match = next((r for r in runs if r["id"].startswith(prefix)), None)
    if not match:
        c.print(f"[red]No session matching '{prefix}'.[/]")
        return 1
    head = Text.assemble(
        ("leavitt session ", f"bold {AMBER}"), (match["id"][:8], "grey70"),
        (f"   {match['started'][:19].replace('T', ' ')}\n", "grey50"),
        (match["query"], "white"),
    )
    steps = Table.grid(padding=(0, 1))
    for a in match["actions"]:
        steps.add_row(Text("✓", style="green"), Text(a, style="grey80"))
    if not match["complete"]:
        steps.add_row(Text("✗", style="yellow"), Text(f"stopped here (never reached {TERMINAL})", style="yellow"))
    r = match["report"]
    report_t = Table.grid(padding=(0, 2))
    if match["complete"]:
        disp = (r.get("disposition") or "").lower()
        style = {"resolved": "green", "degraded": AMBER, "inconclusive": "red"}.get(disp, "white")
        report_t.add_row(Text("disposition", style="grey70"), Text(disp or "reported", style=f"bold {style}"))
        report_t.add_row(Text("confidence", style="grey70"), Text(r.get("confidence", ""), style="white"))
        report_t.add_row(Text("root cause", style="grey70"), Text((r.get("root_cause") or "")[:90], style="white"))
        report_t.add_row(Text("affected", style="grey70"), Text(", ".join(r.get("affected_services", [])) or "-", style="white"))
        report_t.add_row(Text("sources", style="grey70"), Text(f"{r.get('usable', 0)}/{r.get('total', 0)} usable", style="white"))
        for ev in r.get("recovery_events", []):
            report_t.add_row(Text("recovery", style="grey70"), Text(ev[:80], style="yellow"))
    else:
        report_t.add_row(Text("report", style="grey70"), Text("none (session did not complete)", style="yellow"))
    c.print(Group(
        Panel(head, border_style="grey42"),
        Panel(steps, title="steps run", border_style="grey42", title_align="left"),
        Panel(report_t, title="report", border_style=AMBER, title_align="left"),
    ))
    return 0
