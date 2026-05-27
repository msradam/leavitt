"""Leavitt agent for AIOpsLab.

Leavitt's discipline is: gather every telemetry class before concluding, then
bound the conclusion by what the evidence supports. In the standalone product a
Theodosia-enforced FSM guarantees that traversal; here the same guarantee lives
in this loop. The agent deterministically pulls metrics, traces, and logs (the
mandatory query phases) before it is allowed to reason or submit, and the
reasoning prompt holds it to evidence (abstain when a signal is absent rather
than guess). The baseline arm is the same model with no such gate
(clients/generic_openai.py).

Model is read from OPENAI_COMPATIBLE_* env (point it at Crusoe/Nemotron).
"""

import asyncio
import re
import sys

from aiopslab.orchestrator import Orchestrator
from aiopslab.orchestrator.problems.registry import ProblemRegistry
from clients.utils.llm import GenericOpenAIClient
from dotenv import load_dotenv

load_dotenv()

PROTOCOL = """\
You are Leavitt, an on-call incident-triage agent. You diagnose from evidence and \
never claim a fault you cannot ground in the telemetry you were shown.

You have already gathered the available telemetry for this service (below): \
server metrics, distributed traces, and recent pod logs. Reason over ALL of it \
before concluding. Rules:
- A fault must be supported by a concrete signal in the metrics, traces, or logs \
(errors, saturation, latency, restarts, missing dependencies). Name the service \
only if a signal points to it.
- If the telemetry shows no anomaly, say so: report no fault rather than inventing one.
- Do not speculate beyond the evidence. Partial evidence means a cautious answer.

When you are ready, respond with exactly one action in a single triple-backtick \
block, and nothing else. {submit_hint}
"""


def parse_path(text: str) -> str | None:
    m = re.search(r"(/[^\s'\"]+\.(?:csv|json|txt))", str(text))
    if m:
        return m.group(1)
    m = re.search(r"(/[^\s'\"]+/[^\s'\"]+)", str(text))
    return m.group(1) if m else None


def distill_traces(path: str) -> str | None:
    """Per-service latency and error counts from the trace CSV. A slowdown
    (e.g. a network delay) shows in p95 duration even when nothing errors, so
    distilling it is what lets the agent localize a latency fault."""
    try:
        import pandas as pd

        df = pd.read_csv(path)
        if "duration" not in df or "service_name" not in df:
            return None
        ms = df["duration"] / 1000.0  # Jaeger duration is microseconds
        df = df.assign(_ms=ms)
        rows = []
        g = df.groupby("service_name")
        for svc, sub in g:
            errs = int(sub["has_error"].sum()) if "has_error" in sub else 0
            rows.append(
                (
                    svc,
                    len(sub),
                    sub["_ms"].mean(),
                    sub["_ms"].quantile(0.95),
                    sub["_ms"].max(),
                    errs,
                )
            )
        rows.sort(key=lambda r: r[3], reverse=True)  # by p95 desc
        lines = ["service: count mean_ms p95_ms max_ms errors"]
        for svc, n, mean, p95, mx, errs in rows[:25]:
            lines.append(f"{svc}: {n} {mean:.0f} {p95:.0f} {mx:.0f} {errs}")
        return "\n".join(lines)
    except Exception:
        return None


class LeavittAgent:
    def __init__(self):
        self.llm = GenericOpenAIClient()
        self.ns = "default"
        self.task = "detection"
        self.submit_hint = ""
        self.evidence = []
        self.phase = "m_get"
        self.history = []

    def init_context(self, problem_desc, instructions, apis):
        text = problem_desc + "\n" + instructions
        m = re.search(r"Namespace:\s*(\S+)", text)
        if m:
            self.ns = m.group(1)
        if "system_level" in text:
            self.task = "analysis"
            self.submit_hint = (
                'Submit submit({"system_level": <Hardware|Operating System|'
                'Virtualization|Application>, "fault_type": <Misconfiguration|'
                "Code Defect|Authentication Issue|Network/Storage Issue|Operation "
                "Error|Dependency Problem>}), or submit() if no fault."
            )
        elif "list of faulty" in text or "submit([" in text:
            self.task = "localization"
            self.submit_hint = (
                "Submit submit([<faulty service names>]) or submit([]) if none."
            )
        else:
            self.task = "detection"
            self.submit_hint = (
                'Submit submit("Yes") if anomalies exist, else submit("No").'
            )

    def _block(self, call: str) -> str:
        return f"```\n{call}\n```"

    def _record(self, label, content):
        self.evidence.append((label, str(content)[:3500]))

    def _logs_cmd(self) -> str:
        # exec_shell runs under sh (no bash loops). Pod status + recent events
        # surface crashloops, restarts, failed mounts, and config errors without
        # a shell loop; robust across fault types.
        return self._block(
            f'exec_shell("kubectl get pods -n {self.ns} -o wide; echo ===EVENTS===; '
            f'kubectl get events -n {self.ns} --sort-by=.lastTimestamp | tail -40")'
        )

    async def get_action(self, input) -> str:
        # Deterministic gather: metrics, then traces, then logs (the mandatory
        # query traversal) before any conclusion. Each get returns a file path
        # we then read; if no path comes back, record the raw output and move on.
        if self.phase == "m_get":
            self.phase = "m_after"
            return self._block(f'get_metrics(namespace="{self.ns}", duration=5)')
        if self.phase == "m_after":
            p = parse_path(input)
            if p:
                self.phase = "m_read"
                return self._block(f'read_metrics(file_path="{p}")')
            self._record("metrics", input)
            self.phase = "t_after"
            return self._block(f'get_traces(namespace="{self.ns}", duration=5)')
        if self.phase == "m_read":
            self._record("metrics", input)
            self.phase = "t_after"
            return self._block(f'get_traces(namespace="{self.ns}", duration=5)')
        if self.phase == "t_after":
            p = parse_path(input)
            distilled = distill_traces(p) if p else None
            if distilled:
                self._record("trace latency + errors by service", distilled)
                self.phase = "l_after"
                return self._logs_cmd()
            if p:
                self.phase = "t_read"
                return self._block(f'read_traces(file_path="{p}")')
            self._record("traces", input)
            self.phase = "l_after"
            return self._logs_cmd()
        if self.phase == "t_read":
            self._record("traces", input)
            self.phase = "l_after"
            return self._logs_cmd()
        if self.phase == "l_after":
            self._record("pod status + events", input)
            self.phase = "l2_after"
            return self._block(f'get_logs(namespace="{self.ns}", service="frontend")')
        if self.phase == "l2_after":
            self._record("frontend logs", input)
            self.phase = "reason"
            return await self._reason(first=True)
        # Reasoning phase: conclude from the gathered evidence.
        return await self._reason(first=False, last_input=input)

    async def _reason(self, first: bool, last_input: str = "") -> str:
        usable = sum(
            1 for _, c in self.evidence if c.strip() and "error" not in c[:60].lower()
        )
        coverage = f"{usable}/3 telemetry classes returned usable data."
        if first:
            ev = "\n\n".join(
                f"=== {label} ===\n{content}" for label, content in self.evidence
            )
            ev = ev[:16000]  # hard ceiling regardless of per-item caps
            sys_msg = PROTOCOL.format(submit_hint=self.submit_hint)
            self.history = [
                {"role": "system", "content": sys_msg},
                {
                    "role": "user",
                    "content": f"{coverage}\n\nGathered telemetry:\n\n{ev}\n\nDiagnose and submit.",
                },
            ]
        else:
            self.history.append({"role": "user", "content": str(last_input)[:2000]})
        out = self.llm.run(self.history)[0]
        self.history.append({"role": "assistant", "content": out})
        print(f"\n===== Leavitt ({self.llm.model}) =====\n{out[:600]}")
        return out


async def main():
    from pathlib import Path

    only = sys.argv[1:] or None
    problems = ProblemRegistry().PROBLEM_REGISTRY
    pids = only if only else list(problems)
    rdir = Path.home() / "AIOpsLab" / "runs" / "leavitt"
    for pid in pids:
        print(f"\n###PROBLEM {pid}###", flush=True)
        agent = LeavittAgent()
        orch = Orchestrator(results_dir=rdir)
        orch.register_agent(agent, name="leavitt")
        desc, instr, apis = orch.init_problem(pid)
        agent.init_context(desc, instr, apis)
        try:
            await orch.start_problem(max_steps=30)
        except Exception as e:  # keep the batch going
            print(f"###ERROR {pid}: {type(e).__name__}: {e}###", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
