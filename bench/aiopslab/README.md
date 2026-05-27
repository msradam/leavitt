# Leavitt on AIOpsLab

Leavitt evaluated on [AIOpsLab](https://github.com/microsoft/AIOpsLab)
([arXiv:2501.06706](https://arxiv.org/abs/2501.06706)), Microsoft Research's
framework for incident-management agents. AIOpsLab deploys microservices, injects
faults, and scores an agent on detection, localization, and root-cause analysis
through a fixed telemetry API (metrics via Prometheus, traces via Jaeger, logs via
kubectl).

`leavitt_agent.py` is Leavitt as an AIOpsLab agent. The enforcement machinery
lives in the agent loop: Leavitt deterministically gathers metrics, traces
(distilled to per-service latency and errors), and error logs across all pods,
then reasons once and submits, bounded, and read-only. The baseline is AIOpsLab's
stock agent (`clients/generic_openai.py`), the same model exploring freely.

The comparison is 1:1 except for that machinery. Both arms get the same problem
description, the same task instructions, and the same submit format. The only
difference Leavitt adds is the enforced gather (and one sentence telling the model
the telemetry was collected for it). This isolates what the enforcement does, not
prompt wording.

## Reproduce

```bash
# 1. clone AIOpsLab and bring up a kind cluster (see its TutorialSetup.md)
git clone --recurse-submodules https://github.com/microsoft/AIOpsLab
cd AIOpsLab && poetry install
cp aiopslab/config.yml.example aiopslab/config.yml   # set k8s_host: kind
kind create cluster --config kind/kind-config-arm.yaml   # or -x86

# 2. drop in the Leavitt agent
cp /path/to/leavitt/bench/aiopslab/leavitt_agent.py clients/

# 3. point the OpenAI-compatible client at your model
export OPENAI_COMPATIBLE_BASE_URL=https://api.together.xyz/v1
export OPENAI_COMPATIBLE_MODEL=moonshotai/Kimi-K2.6   # or deepseek-ai/DeepSeek-V4-Pro
export OPENAI_COMPATIBLE_API_KEY=...    # keep the real key out of git

# 4. run problems
poetry run python clients/leavitt_agent.py <problem_id> ...   # Leavitt (gated)
poetry run python clients/baseline_run.py <problem_id> ...    # baseline
```

Results write to `runs/leavitt/` and `runs/baseline/` (problem id, scores, steps).

## Results

Runs cover twelve HotelReservation read-only problems (misconfig, pod-failure,
pod-kill, network-delay, network-loss, plus a no-fault control) across detection,
localization, and root-cause analysis, on two models (Kimi K2.6, DeepSeek-V4-Pro).

We are still iterating on the enforced agent's investigation loop, in particular
giving it bounded, step-by-step adaptive drill-down after the mandatory gather, so
slow-manifesting faults (network delay) get the observation time they need. Final
numbers will land here once that loop is settled. The reproduction above runs the
current agent and the baseline so anyone can regenerate the tables.

For Leavitt's safety-under-chaos result (degrade or decline rather than conclude
wrongly when sources fail), which is its core property, see the chaos benchmark in
[`demo/results_table.md`](../../demo/results_table.md).
