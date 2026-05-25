"""Shared benchmark engine.

Both arms are the same model (Kimi via litellm) driving via tool calls. Only the
Theodosia layer differs:

  Leavitt arm  (runner.py):        Kimi calls one `step` tool; Theodosia enforces
                                   the FSM, classifies upstream failures, and
                                   constrains the report's disposition by evidence.
  Baseline arm (baseline_agent.py): Kimi calls the raw query tools and a
                                   submit_report tool directly. No FSM, no
                                   enforcement, no evidence-constrained disposition.

Chaos is injected by the upstream config for a run:
  clean       all servers real
  single_down flagctx (deployment context) omitted -> that source errors
  multi_fail  flagctx omitted AND grafana points at the malformed server
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

import litellm

from leavitt.actions import _digest_for_llm

REPO = Path(__file__).resolve().parent.parent
MODEL = os.getenv("LEAVITT_LLM", "together_ai/moonshotai/Kimi-K2.6")
GRAFANA_SSE = os.getenv("LEAVITT_GRAFANA_MCP", "http://localhost:8000/sse")
FLAGD_CONFIG = str(REPO / "deploy/opentelemetry-demo/src/flagd/demo.flagd.json")


def flagctx_stdio() -> dict[str, Any]:
    return {
        "command": sys.executable,
        "args": [str(REPO / "deploy/flagctx_server.py")],
        "env": {**os.environ, "FLAGCTX_CONFIG_PATH": FLAGD_CONFIG},
    }


def malformed_grafana_stdio() -> dict[str, Any]:
    return {
        "command": sys.executable,
        "args": [str(REPO / "bench/malformed_grafana.py")],
    }


def upstream_for(condition: str) -> dict[str, Any]:
    """Upstream MCP server config per chaos condition."""
    if condition == "clean":
        return {"grafana": GRAFANA_SSE, "flagctx": flagctx_stdio()}
    if condition == "single_down":
        return {"grafana": GRAFANA_SSE}  # flagctx omitted -> deployment source errors
    if condition == "multi_fail":
        return {"grafana": malformed_grafana_stdio()}  # garbage + flagctx omitted
    raise ValueError(condition)


# ----- Kimi tool-calling loop -------------------------------------------------

Dispatch = Callable[[str, dict], Awaitable[dict]]


async def kimi_loop(
    system: str,
    user_msg: str,
    tools: list[dict],
    dispatch: Dispatch,
    max_turns: int = 18,
) -> tuple[dict | None, dict]:
    """Run a tool-calling conversation. dispatch(name, args) returns a dict with
    keys: result (fed back to the model), optional report (dict), stop (bool),
    refusal (bool). Returns (report, trace)."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]
    trace = {"turns": 0, "tool_calls": [], "refusals": 0}
    report = None
    for _ in range(max_turns):
        trace["turns"] += 1
        try:
            resp = await litellm.acompletion(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=8000,
                allowed_openai_params=["tools", "tool_choice"],
            )
        except Exception as exc:  # noqa: BLE001
            trace["error"] = f"{type(exc).__name__}: {exc}"[:300]
            break
        msg = resp["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if not tcs:
            trace["final_text"] = (msg.get("content") or "")[:500]
            break
        messages.append(
            {
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in tcs
                ],
            }
        )
        for tc in tcs:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            out = await dispatch(name, args)
            trace["tool_calls"].append({"name": name, "args": args})
            if out.get("refusal"):
                trace["refusals"] += 1
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": json.dumps(out.get("result"), default=str)[:3500],
                }
            )
            if out.get("report"):
                report = out["report"]
            if out.get("stop"):
                return report, trace
    return report, trace


def digest_one(source: str, payload: Any) -> str:
    """Same digest Leavitt's distill step uses, applied to one source payload, so
    both arms reason over equivalently-reduced evidence."""
    return _digest_for_llm([{"source": source, "status": "ok", "data": payload}])


# ----- scoring ----------------------------------------------------------------


def score(report: dict | None, expect_services: list[str]) -> dict:
    """Score one run against a scenario's ground truth.

    A run "found the root cause" only if it reached an actual conclusion (a
    disposition other than inconclusive) and named the expected service in the
    root_cause statement. Listing a service among affected_services while
    declining (inconclusive) does not count, that is naming candidates, not
    identifying the cause.
    """
    produced = report is not None
    rc = ((report or {}).get("root_cause", "") or "").lower()
    disposition = (report or {}).get("disposition", "") or ""
    concluded = disposition not in ("", "inconclusive")
    found = concluded and any(s.lower() in rc for s in expect_services)
    false_positive = disposition == "resolved" and not found
    return {
        "produced_report": produced,
        "found_root_cause": found,
        "disposition": disposition,
        "false_positive": false_positive,
    }
