# Demo video script (~2 minutes)

Two terminal panes side by side. Left: `k6top` showing the live load test against
the OpenTelemetry Demo. Right: `leavitt investigate`. A browser tab on the flagd
UI (http://localhost:8080/feature) for the chaos toggle.

Setup before recording:
- Demo up: `cd deploy && ./setup_demo.sh up`
- Left pane: `k6top --url http://localhost:5665`
- Right pane ready to run `leavitt investigate`
- Env: `LEAVITT_GRAFANA_MCP=http://localhost:8000/sse`,
  `LEAVITT_FLAGCTX_CONFIG=.../demo.flagd.json`, `TOGETHER_API_KEY` set.

---

## 0:00 – 0:15 — What it is

Narration: "Leavitt reads observability dashboards and tells you what broke,
without touching anything. It's built on Theodosia, a state machine an LLM
drives one validated step at a time."

Screen: title, then the two panes. k6top on the left shows steady traffic, low
error rate. The system is healthy.

## 0:15 – 0:35 — Inject a real incident

Screen: flagd UI, flip `productCatalogFailure` to on.

Narration: "I'll inject a real failure with flagd. The product-catalog service
starts erroring."

Screen: on the left, k6top's error rate and the product endpoint failures climb.
This is real telemetry, not a mock.

## 0:35 – 1:15 — Leavitt triages it

Screen: right pane, run:
`leavitt investigate "Users report product pages erroring. Root cause?"`

Narration: "Leavitt walks its state machine. It reads four sources through MCP
servers, server metrics, logs, the k6 client-side failures, and the deployment
flags, correlates them, distills the evidence, and reasons."

Screen: the TUI phases light up in order, the four sources resolve to ok, the
report resolves: disposition resolved, root cause productCatalogFailure cascading
to frontend and frontend-proxy. The amber report card.

Narration: "It found the flag and the cascade, from the telemetry."

## 1:15 – 1:35 — The guarantee

Narration: "It can't cut corners. Theodosia enforces the graph."

Screen: a quick clip of an MCP client calling `step` with `produce_report` from
the start. The response: `invalid_transition`, refused, with the valid next
action. "The agent literally cannot skip correlation or reach a conclusion early.
And there is no write action in the graph, so it cannot act on what it observes."

## 1:35 – 1:50 — Resilient under chaos

Narration: "When a source goes down mid-investigation, it degrades instead of
guessing. When the data is unusable, it returns inconclusive rather than
hallucinating a cause. It never claims a resolution it can't support."

Screen: a run with a source killed, the report marked degraded, a recovery event
logged, still no false positive.

## 1:50 – 2:00 — It composes

Narration: "The same agent runs as a Nemotron agent on Crusoe, driven by a Hermes
harness over MCP, with the model layer routable through TrueFoundry's gateway.
One artifact. Read-only, auditable, resilient. Built on Theodosia."

Screen: the Hermes one-shot output naming the same root cause, then the Theodosia
GitHub link.

---

## Notes
- Keep it honest: the benchmark shows parity with a strong model plus the
  structural guarantees and safe-failure behavior. Do not claim a numeric win.
- The cascade detail in the report is the proof it read real telemetry, call it
  out.
