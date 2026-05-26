# Leavitt as a Hermes agent (Nemotron on Crusoe)

Leavitt ships as a [Hermes Agent](https://github.com/NousResearch/hermes-agent)
profile: an on-call incident-triage agent that reads observability dashboards and
reports the cause, running NVIDIA Nemotron on Crusoe Cloud managed inference and
driving the Leavitt MCP server (a Theodosia-enforced state machine). The agent is Leavitt; Hermes is the outer harness, Theodosia the
inner one. Two governance layers on one Nemotron agent: Hermes sandboxes what the
agent can touch, Theodosia enforces the workflow it must follow.

## Files
- `leavitt-profile.config.yaml`: the Hermes profile config (model = Nemotron via
  Crusoe, the Leavitt MCP server, skin = leavitt). Secrets and paths are placeholders.
- `SOUL.md`: the system prompt: investigate only through the Leavitt MCP tools, never answer from memory.
- `skins/leavitt.yaml`: the Leavitt skin (observatory palette: sodium-amber star on plate-black).
- `patch-tool-display.py`: makes Hermes render each MCP step as a readable one-liner (see "Readable tool calls").

## Install
```bash
# 1. install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. create a profile and drop in the Leavitt config + skin
hermes profile create leavitt --no-alias
cp deploy/hermes/leavitt-profile.config.yaml ~/.hermes/profiles/leavitt/config.yaml
cp deploy/hermes/skins/leavitt.yaml ~/.hermes/skins/leavitt.yaml
cp deploy/hermes/SOUL.md ~/.hermes/profiles/leavitt/SOUL.md   # forces tool use, no answering from memory
#    then edit the config: replace /path/to/leavitt and set ${CRUSOE_API_KEY}

# 3. run it
hermes profile use leavitt
hermes -t leavitt          # scope to the Leavitt MCP only
# branded as Leavitt, Nemotron drives the Leavitt MCP to a triage report
```

The Leavitt MCP it drives is started by the profile (`leavitt serve`), which reads
Grafana metrics/logs and flagd deployment context through mcp-grafana. Bring the
substrate up first with `deploy/setup_demo.sh up`.

## Clean branding

The Leavitt skin (`skins/leavitt.yaml`, `display.skin: leavitt`) sets the banner
welcome, the `✦ Leavitt` response label, the observatory palette, and the spinner
verbs. A few notes for a clean look:

- The skin applies from the **default profile** cleanly. A non-default profile
  hits a Hermes `HERMES_HOME` fallback in subprocesses (issue #18594) where the
  skin/display config may not load; if you use a named profile, launch with
  `HERMES_HOME=~/.hermes/profiles/<name>` and keep the skin in that profile's
  `skins/` dir.
- Scope the agent to the Leavitt MCP with `hermes -t leavitt` so its only tools
  are Leavitt's, and the `SOUL.md` keeps it investigating through the tools
  rather than answering from memory.

## Readable tool calls

By default Hermes shows each step as a bare `step` with no detail: it builds the
per-call preview from a fixed set of argument keys (`query`/`text`/`path`/...),
and Leavitt's step tool is keyed `action`/`inputs`, so the preview comes back
empty. `patch-tool-display.py` applies two edits to Hermes's `agent/display.py` so
each call renders the action it ran:

```bash
python deploy/hermes/patch-tool-display.py    # idempotent; defaults to ~/.hermes/hermes-agent
```

Then set `display.tool_progress: all` in the profile config (the `new` mode
collapses repeated calls to the same tool, and every Leavitt call is `step`). The
result:

```
│ ⚡ step  query_grafana_metrics  1.2s
│ ⚡ step  query_grafana_logs     0.9s
│ ⚡ step  correlate_evidence     0.3s
│ ⚡ step  produce_report         0.8s
```

## On-call: scheduled runs

The agent is headless and only ever reads, so it runs unattended on a schedule. Scope
the cron platform to the Leavitt toolset so the scheduled worker can only call
`step` (no terminal, file, or web tools):

```yaml
# ~/.hermes/config.yaml
platform_toolsets:
  cron: [leavitt]
```

```bash
hermes cron create '0 * * * *' "An alert fired for the webstore. Investigate and report." \
  --profile default --name leavitt-oncall
hermes cron run leavitt-oncall && hermes cron tick   # fire once now
# or run the gateway to fire on schedule: hermes gateway install
```

Each run drives the full FSM to a report in Theodosia's tracker; `leavitt
sessions` lists them, completed or `incomplete @ <action>`.

## On-call: deliver the report

The investigation is read-only; delivery is a separate harness step. `leavitt
report` reads the latest completed run from the audit trail and posts a formatted
incident report. Today it targets a Discord channel webhook:

```bash
export LEAVITT_DISCORD_WEBHOOK=https://discord.com/api/webhooks/...   # keep in .env
leavitt report --discord          # post the latest triage report
leavitt report <id> --discord     # a specific run
leavitt report                    # print it instead of posting
```

`deploy/oncall.sh` is the loop a schedule or an alert invokes: it runs the
headless investigation, then delivers the report.

```bash
hermes cron create '0 * * * *' --name leavitt-oncall --no-agent \
  --script oncall.sh             # scheduled on-call: investigate + deliver
```

## On-call: fire on an alert

Hermes can trigger a run from an inbound webhook, so an alert (Alertmanager,
Grafana, PagerDuty) becomes a Leavitt investigation. Enable the webhook platform,
scope it to the Leavitt toolset, and subscribe a route:

```yaml
# ~/.hermes/config.yaml
platform_toolsets:
  webhook: [leavitt]
platforms:
  webhook: { enabled: true, extra: { host: "127.0.0.1", port: 8644, secret: "..." } }
```

```bash
hermes webhook subscribe leavitt-alert --events alert \
  --prompt "An alert fired: {summary}. Investigate the current state and report what is wrong and which service is responsible."
hermes gateway run                # listen on /webhooks/leavitt-alert
# your alerting system POSTs {"summary": "..."} (HMAC-signed) to the route
```

The triggered run is scoped to the Leavitt toolset, so even an alert-driven
investigation can only read. Pair it with `leavitt report --discord` to close the
loop: alert in, triage report out.

## Model fallback

A third resilience layer for unattended runs: when the primary model (Nemotron on
Crusoe) rate-limits, 5xxs, or drops the connection, Hermes retries on the next
provider in the chain. Add a `fallback_providers` list to `~/.hermes/config.yaml`:

```yaml
fallback_providers:
  - provider: custom
    model: moonshotai/Kimi-K2.6
    base_url: https://api.together.xyz/v1
    api_key: ${TOGETHER_API_KEY}     # keep the real key in .env
```

`hermes fallback list` shows the chain. This sits beside Theodosia's data-layer
resilience and the TrueFoundry gateway's routing-layer failover.
