# Sponsor integrations

Leavitt is an MCP server (Theodosia mount) that also drives upstream MCP servers.
That gives two integration directions: other agents drive Leavitt, and Leavitt's
LLM calls route through gateways. Both are config, not code changes.

## Crusoe: a Hermes agent (Nemotron) driving Leavitt over MCP

Hermes Agent (NousResearch) runs Nemotron on Crusoe Cloud managed inference and
connects to Leavitt as an MCP server. The agent is Leavitt; Hermes is the outer
harness, Theodosia the inner one. Verified: Hermes/Nemotron drove the full FSM
(`receive_query` to `produce_report`) and returned the correct root cause with
the affected-service cascade, which is only derivable from Leavitt's telemetry,
not from the prompt.

`~/.hermes/config.yaml`:

```yaml
model:
  default: "hack-crusoe/Nemotron-3-Nano-30B-A3B-FP8"
  provider: "custom"
  base_url: "https://api.inference.crusoecloud.com/v1"
  api_key: "<CRUSOE_KEY>"

mcp_servers:
  leavitt:
    command: "/opt/homebrew/bin/uv"
    args: ["run", "--directory", "/path/to/leavitt", "leavitt", "serve"]
    timeout: 180
    env:
      LEAVITT_GRAFANA_MCP: "http://localhost:8000/sse"
      LEAVITT_FLAGCTX_CONFIG: "/path/to/leavitt/deploy/opentelemetry-demo/src/flagd/demo.flagd.json"
      LEAVITT_LLM: "openai/hack-crusoe/Nemotron-3-Nano-30B-A3B-FP8"
      LEAVITT_LLM_API_BASE: "https://api.inference.crusoecloud.com/v1"
      LEAVITT_LLM_API_KEY: "<CRUSOE_KEY>"
```

Run a triage:

```bash
hermes --yolo -z "Investigate: users report product pages are erroring. Use the \
leavitt MCP tools, start with step action 'receive_query', follow valid_next_actions \
to produce_report, then report the root cause."
```

Nemotron runs the whole thing: it drives Leavitt's `step` tool, and Leavitt's
`form_hypothesis` also calls Nemotron via `LEAVITT_LLM`.

## TrueFoundry: route Leavitt's LLM through the AI Gateway

Set Leavitt's model to an `openai/<gateway-model-id>` and point it at the gateway.
Provider failover, retries, and load balancing then happen at the gateway; Theodosia
handles data-layer resilience. Verified end to end through litellm.

```bash
export LEAVITT_LLM="openai/together-ai/moonshotai-kimi-k2.6"   # a model configured in the gateway
export LEAVITT_LLM_API_BASE="https://<tenant>.truefoundry.cloud/api/llm/api/inference/openai"
export LEAVITT_LLM_API_KEY="<TRUEFOUNDRY_PAT>"
```

`_llm_kwargs()` in `leavitt/actions.py` passes `api_base`/`api_key` to every LLM
call, so the same two env vars route either the TrueFoundry gateway or Crusoe.

## Crusoe direct (Leavitt on Nemotron, no Hermes)

```bash
export LEAVITT_LLM="openai/hack-crusoe/Nemotron-3-Nano-30B-A3B-FP8"
export LEAVITT_LLM_API_BASE="https://api.inference.crusoecloud.com/v1"
export LEAVITT_LLM_API_KEY="<CRUSOE_KEY>"
```
