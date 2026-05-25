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
    "Start by calling step with action='receive_query' and inputs={\"query\": <the "
    'user\'s question>, "max_retries": 1}. After each step the response gives '
    "valid_next_actions; call step with one of them. Walk the machine to its end. "
    'The terminal action is produce_report: call it with inputs={"disposition": '
    "<one of 'resolved','degraded','inconclusive'>} chosen from the evidence. Use "
    "'resolved' only when confidence is full and a clear root cause was found, "
    "'degraded' when some sources failed, 'inconclusive' when no usable evidence. "
    "If a step is refused, read valid_next_actions and pick a valid one. Do not "
    "invent evidence."
)


def make_leavitt_dispatch(client: Client) -> tuple[Callable, Callable]:
    holder: dict = {}

    async def dispatch(name: str, args: dict) -> dict:
        action = args.get("action", "")
        inputs = args.get("inputs") or {}
        res = await client.call_tool("step", {"action": action, "inputs": inputs})
        sc = res.structured_content or {}
        if sc.get("error"):
            return {
                "result": {
                    "error": sc["error"],
                    "valid_next_actions": sc.get("valid_next_actions"),
                },
                "refusal": True,
            }
        st = sc.get("state", {}) or {}
        out = {
            "executed": sc.get("action"),
            "valid_next_actions": sc.get("valid_next_actions"),
            "next_hint": sc.get("next_hint"),
        }
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
