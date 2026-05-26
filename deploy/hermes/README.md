# Leavitt as a Hermes agent (Nemotron on Crusoe)

Leavitt ships as a [Hermes Agent](https://github.com/NousResearch/hermes-agent)
profile: a read-only incident-triage agent running NVIDIA Nemotron on Crusoe
Cloud managed inference, driving the Leavitt MCP server (a Theodosia-enforced
state machine). The agent is Leavitt; Hermes is the outer harness, Theodosia the
inner one. Two governance layers on one Nemotron agent: Hermes sandboxes what the
agent can touch, Theodosia enforces the workflow it must follow.

## Files
- `leavitt-profile.config.yaml` — the Hermes profile config (model = Nemotron via
  Crusoe, the Leavitt MCP server, skin = leavitt). Secrets and paths are placeholders.
- `skins/leavitt.yaml` — the Leavitt skin (amber-on-charcoal, Cepheid star motif).

## Install
```bash
# 1. install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. create a profile and drop in the Leavitt config + skin
hermes profile create leavitt --no-alias
cp deploy/hermes/leavitt-profile.config.yaml ~/.hermes/profiles/leavitt/config.yaml
cp deploy/hermes/skins/leavitt.yaml ~/.hermes/skins/leavitt.yaml
#    then edit the config: replace /path/to/leavitt and set ${CRUSOE_API_KEY}

# 3. run it
hermes profile use leavitt
hermes
# branded as Leavitt, Nemotron drives the Leavitt MCP to a triage report
```

The Leavitt MCP it drives is started by the profile (`leavitt serve`), which reads
Grafana metrics/logs and flagd deployment context through mcp-grafana. Bring the
substrate up first with `deploy/setup_demo.sh up`.
