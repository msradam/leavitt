"""Leavitt arm: the single `step` tool Kimi uses to drive the Theodosia FSM, and
the dispatch that executes each step against the mounted server. Theodosia
validates every transition; the dispatch feeds back the executed action, the
valid next actions, a hint, and decision-relevant state so Kimi can choose the
disposition at produce_report.
"""

from __future__ import annotations

from typing import Callable

from fastmcp import Client

STEP_TOOL = {
    "type": "function",
    "function": {
        "name": "step",
        "description": (
            "Advance the read-only triage FSM by one action. Pass the action name "
            "and any inputs. The response lists valid_next_actions to pick from."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "the action to run"},
                "inputs": {"type": "object", "description": "inputs for the action"},
            },
            "required": ["action"],
        },
    },
}

LEAVITT_SYSTEM = (
    "You drive a read-only incident triage state machine using the `step` tool. "
    "You cannot run commands or change anything; you only read dashboards.\n"
    "RULES:\n"
    "1. Only ever use an action name that appears in the latest response's "
    "valid_next_actions. Never invent or guess an action name.\n"
    "2. You almost always have exactly one valid next action. When the response "
    "includes do_this_next, call step exactly as it says.\n"
    "3. Start by calling step with action='receive_query' and inputs={\"query\": "
    '<the user\'s question>, "max_retries": 1}.\n'
    "4. Keep calling step, one valid action at a time, until you reach "
    "produce_report. Do not stop early and do not repeat an action you already ran.\n"
    '5. produce_report is terminal: call it with inputs={"disposition": <one of '
    "'resolved','degraded','inconclusive'>} chosen from the evidence. Use 'resolved' "
    "only when confidence is full and a clear root cause was found, 'degraded' when "
    "some sources failed, 'inconclusive' when no usable evidence.\n"
    "6. If a step is refused, read valid_next_actions and call step with one of "
    "those exact names. Do not invent evidence."
)


def make_leavitt_dispatch(client: Client) -> tuple[Callable, Callable]:
    holder: dict = {}

    async def dispatch(name: str, args: dict) -> dict:
        action = args.get("action", "")
        inputs = args.get("inputs") or {}
        res = await client.call_tool("step", {"action": action, "inputs": inputs})
        sc = res.structured_content or {}
        if sc.get("error"):
            vna = sc.get("valid_next_actions") or []
            directive = (
                f"REFUSED. Call step with action='{vna[0]}'."
                if len(vna) == 1
                else f"REFUSED. action must be exactly one of {vna}."
            )
            return {
                "result": {
                    "error": sc["error"],
                    "valid_next_actions": vna,
                    "do_this_next": directive,
                },
                "refusal": True,
            }
        st = sc.get("state", {}) or {}
        vna = sc.get("valid_next_actions") or []
        out = {
            "executed": sc.get("action"),
            "valid_next_actions": vna,
            "next_hint": sc.get("next_hint"),
        }
        if len(vna) == 1:
            hint = (
                'with inputs {"disposition": ...}' if vna[0] == "produce_report" else ""
            )
            out["do_this_next"] = f"call step with action='{vna[0]}' {hint}".strip()
        for k in (
            "confidence",
            "usable_count",
            "source_count",
            "root_cause",
            "hypothesis",
        ):
            v = st.get(k)
            if v not in (None, "", "undetermined", 0):
                out[k] = v
        if sc.get("action") == "produce_report":
            holder["report"] = st.get("report")
            return {"result": out, "report": st.get("report"), "stop": True}
        return {"result": out}

    return dispatch, lambda: holder.get("report")
