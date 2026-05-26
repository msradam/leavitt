"""Deliver a triage report from the audit trail to a notification channel.

Leavitt's investigation is read-only; this is a separate harness-side step that
reads a recorded run from Theodosia's tracker and posts the report. The FSM never
calls it. Today it delivers to a Discord channel webhook
(``LEAVITT_DISCORD_WEBHOOK``); without ``--discord`` it prints the report.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone

from leavitt.sessions import _runs

AMBER, MARGIN, MOON = 0xF6B755, 0xCB9A5B, 0x5D8BB4
ICON = (
    "https://raw.githubusercontent.com/msradam/leavitt/main/demo/media/leavitt-icon.png"
)


def _disposition(rep: dict) -> str:
    if rep["usable"] == 0:
        return "inconclusive"
    return "resolved" if rep["confidence"] == "full" else "degraded"


def _pick(prefix: str | None):
    runs = _runs()
    if not runs:
        return None
    if prefix:
        return next((r for r in runs if r["id"].startswith(prefix)), None)
    return runs[0]


def _embed(run: dict) -> dict:
    rep = run["report"]
    disp = rep["disposition"] or _disposition(rep)
    color = {"resolved": AMBER, "degraded": MARGIN, "inconclusive": MOON}.get(
        disp, AMBER
    )
    fields = [
        {"name": "disposition", "value": disp or "—", "inline": True},
        {"name": "confidence", "value": rep["confidence"] or "—", "inline": True},
        {
            "name": "sources",
            "value": f"{rep['usable']}/{rep['total']} usable",
            "inline": True,
        },
        {"name": "root cause", "value": (rep["root_cause"] or "undetermined")[:1000]},
        {
            "name": "affected services",
            "value": ", ".join(rep["affected_services"]) or "—",
        },
    ]
    for ev in rep.get("recovery_events", [])[:2]:
        fields.append({"name": "recovery", "value": ev[:300]})
    return {
        "author": {"name": "Leavitt · on-call incident triage", "icon_url": ICON},
        "title": "Triage report",
        "description": run["query"] or "(no query)",
        "color": color,
        "fields": fields,
        "thumbnail": {"url": ICON},
        "footer": {
            "text": "Hermes / Nemotron / Crusoe · reads, never touches",
            "icon_url": ICON,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _text(run: dict) -> str:
    rep = run["report"]
    disp = rep["disposition"] or _disposition(rep)
    lines = [
        "✦ Leavitt — incident triage",
        f"  query:       {run['query']}",
        f"  disposition: {disp}",
        f"  confidence:  {rep['confidence']}",
        f"  root cause:  {rep['root_cause'] or 'undetermined'}",
        f"  affected:    {', '.join(rep['affected_services']) or '-'}",
        f"  sources:     {rep['usable']}/{rep['total']} usable",
    ]
    return "\n".join(lines)


def deliver(prefix: str | None = None, discord: bool = False) -> int:
    run = _pick(prefix)
    if run is None:
        print(
            "No matching session in the audit trail." if prefix else "No sessions yet."
        )
        return 1
    if not run["complete"]:
        print(
            f"Session {run['id'][:8]} is incomplete (stopped at {run['last']}); not delivering."
        )
        return 1
    if not discord:
        print(_text(run))
        return 0
    webhook = os.getenv("LEAVITT_DISCORD_WEBHOOK")
    if not webhook:
        print("Set LEAVITT_DISCORD_WEBHOOK to deliver to Discord.")
        return 1
    payload = json.dumps(
        {"username": "Leavitt", "avatar_url": ICON, "embeds": [_embed(run)]}
    ).encode()
    req = urllib.request.Request(
        webhook,
        data=payload,
        # Discord rejects the default urllib User-Agent with 403; set our own.
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Leavitt/1.0 (+https://github.com/msradam/leavitt)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            code = r.status
    except Exception as e:
        print(f"Delivery failed: {e}")
        return 1
    print(f"Delivered run {run['id'][:8]} to Discord (HTTP {code}).")
    return 0


# Discord rejects the default urllib User-Agent with 403; set our own.
_HDRS = {
    "Content-Type": "application/json",
    "User-Agent": "Leavitt/1.0 (+https://github.com/msradam/leavitt)",
}


def report_from_state(query: str, state: dict) -> dict:
    """A run dict in the audit-trail shape, built from live FSM state."""
    return {
        "query": query,
        "complete": True,
        "report": {
            "disposition": state.get("disposition") or "",
            "root_cause": state.get("root_cause") or "",
            "affected_services": state.get("affected_services") or [],
            "confidence": state.get("confidence") or "",
            "usable": int(state.get("usable_count") or 0),
            "total": int(state.get("source_count") or 0),
            "recovery_events": state.get("recovery_events") or [],
        },
    }


class LiveDiscord:
    """A live, per-step progress message during an investigation, then the final
    report as a separate message. The agent never posts; this runs harness-side
    alongside the run, editing one Discord message as the FSM advances."""

    def __init__(self):
        self.webhook = os.getenv("LEAVITT_DISCORD_WEBHOOK")
        self.msg_id: str | None = None
        self.ok = bool(self.webhook)

    def _send(self, url: str, payload: dict, method: str) -> bytes:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=_HDRS, method=method
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read()

    def _progress_embed(self, query: str, checklist: str, done: bool) -> dict:
        return {
            "author": {"name": "Leavitt · on-call incident triage", "icon_url": ICON},
            "title": "Investigation complete" if done else "Investigating",
            "description": ((query or "")[:200] + "\n```\n" + checklist + "\n```")[
                :4000
            ],
            "color": AMBER,
            "footer": {"text": "report below" if done else "reading the dashboards…"},
        }

    def start(self, query: str) -> None:
        if not self.ok:
            return
        try:
            body = self._send(
                self.webhook + "?wait=true",
                {
                    "username": "Leavitt",
                    "avatar_url": ICON,
                    "embeds": [
                        self._progress_embed(query, "receiving the alert…", False)
                    ],
                },
                "POST",
            )
            self.msg_id = json.loads(body).get("id")
        except Exception:
            self.ok = False

    def progress(self, query: str, checklist: str, done: bool = False) -> None:
        if not self.ok or not self.msg_id:
            return
        try:
            self._send(
                f"{self.webhook}/messages/{self.msg_id}",
                {"embeds": [self._progress_embed(query, checklist, done)]},
                "PATCH",
            )
        except Exception:
            pass

    def final(self, run: dict) -> None:
        if not self.ok:
            return
        try:
            self._send(
                self.webhook + "?wait=true",
                {"username": "Leavitt", "avatar_url": ICON, "embeds": [_embed(run)]},
                "POST",
            )
        except Exception:
            pass
