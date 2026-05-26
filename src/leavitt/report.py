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
        "title": "✦ Leavitt — incident triage",
        "description": run["query"] or "(no query)",
        "color": color,
        "fields": fields,
        "footer": {
            "text": "on-call · Hermes / Nemotron / Crusoe · reads, never touches"
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
    payload = json.dumps({"embeds": [_embed(run)]}).encode()
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
