"""Baseline arm: AIOpsLab's stock generic agent (its canonical free-form agent),
over a given problem list. Same model as Leavitt; same problem description, task
instructions, and submit format. The difference is the machinery: this agent
fetches telemetry itself and may conclude whenever it likes; Leavitt's gather is
enforced and bounded.
"""

import asyncio
import sys
from pathlib import Path

from aiopslab.orchestrator import Orchestrator
from clients.generic_openai import GenericOpenAIAgent


async def main():
    pids = sys.argv[1:]
    rdir = Path.home() / "AIOpsLab" / "runs" / "baseline"
    for pid in pids:
        print(f"\n###PROBLEM {pid}###", flush=True)
        agent = GenericOpenAIAgent()
        orch = Orchestrator(results_dir=rdir)
        orch.register_agent(agent, name="baseline")
        try:
            desc, instr, apis = orch.init_problem(pid)
            agent.init_context(desc, instr, apis)
            await orch.start_problem(max_steps=30)
        except Exception as e:
            print(f"###ERROR {pid}: {type(e).__name__}: {e}###", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
