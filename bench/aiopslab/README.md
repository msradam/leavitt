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

Twelve HotelReservation read-only problems (misconfig, pod-failure, pod-kill,
network-delay, network-loss, plus a no-fault control), across detection,
localization, and one root-cause-analysis task. Run on two models, Kimi K2.6 and
DeepSeek-V4-Pro, both arms, 30-step budget.

| metric | Kimi: Leavitt | Kimi: baseline | DeepSeek: Leavitt | DeepSeek: baseline |
|---|---|---|---|---|
| detection correct | 4/6 | 4/6 | 5/6 | 6/6 |
| localization exact | 3/5 | 4/5 | 3/5 | 5/5 |
| RCA (1) | partial | full | partial | full |
| median steps | 6 | 19 | 6 | 6 |
| non-terminations | 0 | 2 (1 invalid, 1 error) | 0 | 0 |

Honest reading:

- **The free-form baseline is ahead on accuracy.** Combined exact scores across
  both models: Leavitt 15/24, baseline 21/24. An unconstrained agent can drill
  into the suspect service adaptively; Leavitt's fixed-breadth gather cannot, and
  it abstains rather than guess.
- **Network-fault localization is Leavitt's weak spot** (0/4). The faulted service
  does not stand out in a single fixed gather, so the disciplined agent submits
  nothing. Free exploration finds it.
- **What enforcement does buy, and AIOpsLab does not score:** Leavitt concludes in
  a bounded ~6 steps on every problem and always terminates with a valid answer
  (the Kimi baseline sprawled to 19 steps median and twice failed to produce one).
  Every step is read-only and on the audit trail.

The takeaway is a trade, not a win. Enforcement costs some diagnostic accuracy
against an unconstrained agent on adaptive tasks, and buys bounded, terminating,
read-only, auditable behavior. AIOpsLab measures the accuracy; production cares
about the rest. For Leavitt's safety-under-chaos behavior (degrade or decline
rather than conclude wrongly), see the chaos benchmark in
[`demo/results_table.md`](../../demo/results_table.md).
