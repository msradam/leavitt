# Leavitt on AIOpsLab

Leavitt evaluated on [AIOpsLab](https://github.com/microsoft/AIOpsLab)
([arXiv:2501.06706](https://arxiv.org/abs/2501.06706)), Microsoft Research's
framework for incident-management agents. AIOpsLab deploys microservices, injects
faults, and scores an agent on detection, localization, and root-cause analysis
through a fixed telemetry API (metrics via Prometheus, traces via Jaeger, logs via
kubectl).

`leavitt_agent.py` is Leavitt as an AIOpsLab agent. Leavitt's enforced workflow
lives in the agent loop: it deterministically gathers metrics, traces, and logs
(the mandatory query traversal) before it may reason or submit, distills
per-service latency and errors from the trace data, and bounds its conclusion to
the evidence. The baseline is AIOpsLab's stock free-form agent
(`clients/generic_openai.py`). Both arms use the same model, the same telemetry
APIs, and the same step budget; the only difference is the enforced traversal.

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
export OPENAI_COMPATIBLE_MODEL=moonshotai/Kimi-K2.6
export OPENAI_COMPATIBLE_API_KEY=...    # keep the real key out of git

# 4. run a problem (or several)
poetry run python clients/leavitt_agent.py misconfig_app_hotel_res-localization-1
# baseline arm: poetry run python clients/generic_openai.py
```

Results write to `runs/leavitt/` (problem id, scores, steps, tokens).

## Results

A 7-problem HotelReservation slice (misconfig, pod-failure, network-delay;
detection, localization, and one RCA). Same model (Kimi K2.6), same 30-step
budget, both arms.

| task | Leavitt | Baseline |
|---|---|---|
| detection | 3/3 | 3/3 |
| localization | 2/3 | 1/3 |
| RCA (1 problem) | partial (level right, type wrong) | partial (level right, type wrong) |
| median steps | 8 | 21 |

What it shows: the enforced workflow matches the free-form agent on accuracy
(tie on detection and RCA, an edge on localization) while concluding in 7-8 steps
every problem against the baseline's 21-30 with high variance. One case,
network-delay localization, neither arm solved; a per-service latency
distillation we added did not crack it.

Caveats: a small slice (n=1 per cell), and a same-model ablation, not a comparison
to AIOpsLab's published baselines. It measures what the enforcement layer costs,
nothing in accuracy here, while the workflow stays bounded, auditable, and
replayable.
