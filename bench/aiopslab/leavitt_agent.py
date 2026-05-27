"""Leavitt agent for AIOpsLab.

The machinery: Leavitt deterministically gathers the service's telemetry, server
metrics, distributed traces (distilled to per-service latency and errors), and
error logs across all pods, before it concludes. This is Theodosia's contract,
you traverse the query phases before you reach the report, in bounded form. A
free-form agent can skip telemetry, loop, and never conclude; this cannot.

Everything the model reads to *reason and submit* is 1:1 with the baseline (AIOps
Lab's stock agent): the same problem description, the same task instructions, the
same submit format. The only difference is the machinery, the gather happened for
it, so the prompt says so. Model is read from OPENAI_COMPATIBLE_* env.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from aiopslab.orchestrator import Orchestrator
from clients.utils.llm import GenericOpenAIClient
from dotenv import load_dotenv

load_dotenv()

# The necessary machinery delta over the baseline prompt: the telemetry was
# gathered for the model rather than fetched by it. Everything else is shared.
MACHINERY = (
    "The service's telemetry has been collected for you and is included below: "
    "server metrics, distributed traces (summarized as per-service latency and "
    "error counts), and recent error logs across all pods, plus pod status and "
    "events. Diagnose from this evidence. Do not claim a fault you cannot ground "
    "in it; if nothing is anomalous, say so rather than inventing a fault."
)
FORMAT = (
    "Respond with exactly one action inside a single triple-backtick block and "
    "nothing else."
)


def parse_path(text: str) -> str | None:
    m = re.search(r"(/[^\s'\"]+\.(?:csv|json|txt))", str(text))
    if m:
        return m.group(1)
    m = re.search(r"(/[^\s'\"]+/[^\s'\"]+)", str(text))
    return m.group(1) if m else None


def distill_traces(path: str) -> str | None:
    """Per-service latency and error counts from the trace CSV, so a slowdown
    (network delay, GC pause) shows in p95 even when nothing errors."""
    try:
        import pandas as pd

        df = pd.read_csv(path)
        if "duration" not in df or "service_name" not in df:
            return None
        df = df.assign(_ms=df["duration"] / 1000.0)  # Jaeger duration is microseconds
        rows = []
        for svc, sub in df.groupby("service_name"):
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
        rows.sort(key=lambda r: r[3], reverse=True)
        out = ["service: count mean_ms p95_ms max_ms errors"]
        out += [
            f"{s}: {n} {m:.0f} {p:.0f} {mx:.0f} {e}" for s, n, m, p, mx, e in rows[:25]
        ]
        return "\n".join(out)
    except Exception:
        return None


class LeavittAgent:
    def __init__(self):
        self.llm = GenericOpenAIClient()
        self.ns = "default"
        self.problem_desc = ""
        self.instructions = ""
        self.submit_doc = ""
        self.evidence: list[tuple[str, str]] = []
        self.phase = "m_get"
        self.history: list[dict] = []

    def init_context(self, problem_desc, instructions, apis):
        self.problem_desc = problem_desc
        self.instructions = instructions
        self.submit_doc = apis.get("submit", "")
        m = re.search(r"Namespace:\s*(\S+)", problem_desc + "\n" + instructions)
        if m:
            self.ns = m.group(1)

    def _block(self, call: str) -> str:
        return f"```\n{call}\n```"

    def _record(self, label, content):
        self.evidence.append((label, str(content)[:3500]))

    def _status_cmd(self) -> str:
        return self._block(
            f'exec_shell("kubectl get pods -n {self.ns} -o wide; echo ===EVENTS===; '
            f'kubectl get events -n {self.ns} --sort-by=.lastTimestamp | tail -40")'
        )

    def _logs_cmd(self) -> str:
        # Cross-service error logs (what real Leavitt reads from Loki), so a
        # network fault's connection errors surface on the affected service.
        # sh-safe: single quotes only, grep -e patterns avoid inner double quotes.
        return self._block(
            f'exec_shell("kubectl get pods -n {self.ns} -o name | xargs -r -I% sh -c '
            f"'echo ==%==; kubectl logs -n {self.ns} % --tail=30 2>/dev/null | "
            f"grep -i -e error -e fail -e refused -e timeout -e unavailable -e exception | head -8'\")"
        )

    async def get_action(self, input) -> str:
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
                self.phase = "status"
                return self._status_cmd()
            if p:
                self.phase = "t_read"
                return self._block(f'read_traces(file_path="{p}")')
            self._record("traces", input)
            self.phase = "status"
            return self._status_cmd()
        if self.phase == "t_read":
            self._record("traces", input)
            self.phase = "status"
            return self._status_cmd()
        if self.phase == "status":
            self._record("pod status + events", input)
            self.phase = "logs"
            return self._logs_cmd()
        if self.phase == "logs":
            self._record("error logs across pods", input)
            self.phase = "reason"
            return await self._reason(first=True)
        return await self._reason(first=False, last_input=input)

    async def _reason(self, first: bool, last_input: str = "") -> str:
        if first:
            ev = "\n\n".join(
                f"=== {label} ===\n{content}" for label, content in self.evidence
            )[:16000]
            if os.getenv("LEAVITT_DIAG") == "1":
                print(
                    "===DIAG EVIDENCE START===\n" + ev + "\n===DIAG EVIDENCE END===",
                    flush=True,
                )
            # 1:1 with the baseline: same problem_desc, instructions, submit doc.
            # MACHINERY is the only added line, the necessary delta.
            system = "\n\n".join([self.problem_desc, self.submit_doc, FORMAT])
            user = "\n\n".join(
                [
                    self.instructions,
                    MACHINERY,
                    "Gathered telemetry:\n\n" + ev,
                    "Diagnose and submit.",
                ]
            )
            self.history = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        else:
            self.history.append({"role": "user", "content": str(last_input)[:2000]})
        out = self.llm.run(self.history)[0]
        self.history.append({"role": "assistant", "content": out})
        print(f"\n===== leavitt ({self.llm.model}) =====\n{out[:400]}", flush=True)
        return out


async def main():
    pids = sys.argv[1:]
    rdir = Path.home() / "AIOpsLab" / "runs" / "leavitt"
    for pid in pids:
        print(f"\n###PROBLEM {pid}###", flush=True)
        agent = LeavittAgent()
        orch = Orchestrator(results_dir=rdir)
        orch.register_agent(agent, name="leavitt")
        try:
            desc, instr, apis = orch.init_problem(pid)
            agent.init_context(desc, instr, apis)
            await orch.start_problem(max_steps=30)
        except Exception as e:  # keep the batch going
            print(f"###ERROR {pid}: {type(e).__name__}: {e}###", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
