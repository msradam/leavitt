# Progress

## Phase 1: substrate + FSM scaffold (Mon May 25)

### Done
- `~/leavitt` initialized: uv project, Python 3.11, src layout, `.env` (gitignored) holds `TOGETHER_API_KEY` and `LEAVITT_LLM`.
- Dependencies: theodosia 0.1.0, burr, fastmcp, litellm, mcp, pyyaml.
- Studied Theodosia's API directly from the installed package. Relevant pieces:
  - `theodosia.mount(application_or_factory, upstream={name: transport})` returns a FastMCP server with the `step(action, inputs)` surface. The server enforces valid Burr transitions.
  - Action bodies call `theodosia.call_upstream(server, tool, args)`; the upstream MCP servers are never exposed to the agent.
  - There is no built-in read/write "mode" primitive. The read-only guarantee is structural: the FSM graph has only READ actions and no unlock edge.
- Leavitt FSM built (`src/leavitt/app.py`): receive_query → enumerate_sources → query_grafana_metrics → query_grafana_logs → query_deployment_context → correlate_evidence → form_hypothesis → produce_report, with a recovery edge `correlate_evidence → query_grafana_metrics` when `should_retry` (total source failure, retries left).
- Action bodies (`src/leavitt/actions.py`): READ-class. Queries centralized in `SOURCES` so wiring real `mcp-grafana` is one edit. PromQL surfaces error rate by service; LogQL pulls warn/error lines; flagctx reports deployment context.
- Chaos handling (`src/leavitt/chaos_handler.py`): `safe_upstream` never raises; classifies each response ok / error / malformed. `correlate_evidence` computes coverage and confidence (full / degraded / none).
- Report (`src/leavitt/reports.py`): disposition constrained by evidence. `produce_report` forces `inconclusive` when no source is usable and downgrades `resolved` to `degraded` under partial coverage.
- CLI (`src/leavitt/cli.py`): `leavitt graph`, `leavitt serve`.
- Deploy scaffold (`deploy/`): Makefile fetches the official OTel Demo compose; `docker-compose.mcp.yml` runs `mcp-grafana`; `flagctx_server.py` is the third source (feature-flag context), verified against a sample flagd config.

### Smoke test (`tests/smoke_test.py`, runs with no network)
All pass:
- Clean run with healthy stub upstreams: reaches produce_report, full confidence, names affected services, correlate runs before report.
- Total source failure with 1 retry: recovery event recorded, metrics re-queried twice, disposition `inconclusive`, never claims `resolved`.
- Theodosia transition enforcement via in-memory FastMCP client: `step(produce_report)` from the start is refused with `invalid_transition` and lists valid next actions.

### Decisions
- Substrate: full OpenTelemetry Demo via docker-compose, per spec. Not yet started (heavy; 7.8 GB Docker RAM, sibling `o11y-bench` containers already running).
- LLM: Kimi K2 via litellm (`together_ai/moonshotai/Kimi-K2-Instruct-0905`), `LEAVITT_LLM` configurable. `LEAVITT_LLM_STUB=1` for offline dev.
- Three sources: grafana_metrics, grafana_logs, deployment_context (flagctx). Two physical MCP servers (grafana, flagctx).

### Real Theodosia upstream path verified (`tests/integration_upstream.py`)
- `theodosia.mount(upstream={grafana, flagctx})` opens real fastmcp.Client stdio sessions; the full FSM is driven through the `step` tool; `call_upstream` hits each server live. All 7 checks pass.
- Caught a real-MCP detail: FastMCP wraps a tool's list return under `{"result": [...]}`. Added `_unwrap`.

### Real mcp-grafana tool surface confirmed (`mcp/grafana:latest`, SSE on :8000)
- 56 tools. The two Leavitt uses: `query_prometheus`, `query_loki_logs` (names correct).
- `query_prometheus` range query **requires** `expr`, `datasourceUid`, `startTime`, `endTime`, `stepSeconds`. My config had only the first two; fixed. Times accept relative form (`now-1h`, `now`).
- `query_loki_logs` requires `datasourceUid` + `logql`; defaults to last hour, limit, backward. My args valid.
- Called the real server with Leavitt's exact args: both accepted (failed only on the unreachable placeholder Grafana backend, not on arg validation). Confirms the contract.
- Discovery path for real datasource UIDs: `list_datasources` (use once a real Grafana is up, instead of guessing `webstore-metrics`/`webstore-logs`).

### Next (Phase 2)
- Bring up the OTel Demo (Grafana + Prometheus + Loki + flagd); point `mcp-grafana` at it; discover real datasource UIDs via `list_datasources`.
- Enable a flagd flag, confirm the failure shows in Prometheus, run Leavitt end-to-end against real telemetry.
- Verify Kimi over litellm end-to-end (real key).

### Blockers
- None. Tool names and arg contracts confirmed against the real `mcp-grafana`. Only the demo's datasource UIDs remain to be read from a live Grafana (one `list_datasources` call), isolated to `SOURCES`/env.

## Live-pipeline smoke against QuickPizza (Mon May 25)
- Brought up QuickPizza's monolithic Grafana stack (Grafana/Prometheus/Loki/Tempo) as a fast, light real-Grafana substrate. Pointed `mcp-grafana` at it, drove the full Leavitt FSM through `step`. Reached a report; metrics + logs sources returned `ok` against real Prometheus/Loki; deployment_context degraded (no flagd). Confirms the full real path end to end.
- Real-MCP detail: `mcp-grafana` returns payloads as MCP **text content**, not `structured_content`. Theodosia's `call_upstream._extract` already parses the text JSON, so Leavitt receives real data. (My first diagnostic read the wrong field.)
- QuickPizza Grafana enables anonymous Admin and disables basic auth; pass `mcp-grafana` **no** API key (a bogus key is rejected and returns empty).
- QuickPizza torn down after (OOM under contention).

## Infra decision: RunPod ruled out, run locally (Mon May 25)
- Tried RunPod for the heavy bench. Provisioned a CPU pod via `runpodctl`, SSHed in, probed it: `CapEff` is the default unprivileged Docker set (no `CAP_SYS_ADMIN`/`CAP_NET_ADMIN`), `ip netns add` denied, no sysbox. **RunPod standard pods cannot run a Docker daemon (no DinD)**, so the OTel Demo's docker-compose can't run there regardless of instance size. Pod deleted.
- Pivoted to local. The laptop was CPU-strangled by sibling projects (`circe-bench-control-plane` kind cluster at ~700% CPU, the `o11y-bench`/`harbor` eval harness respawning compose stacks), not RAM-strangled. With explicit go-ahead, stopped circe and killed the `harbor` orchestrator. Machine now clean: ~7.1 GB free, load dropped from ~21 to ~5.
- OTel Demo (main/v2) structure: `compose.yaml` (22 app services incl. flagd) + `compose.observability.yaml` (jaeger, grafana, prometheus, opensearch). **Logs go to OpenSearch, not Loki.** `otel-collector` hard-depends on jaeger + opensearch. No Kafka in v2. Cloned the repo for its `src/` config mounts; pulling published ghcr images (no local build).

## Phase 2 complete: live end-to-end against the OTel Demo with Kimi (Mon May 25)

### Substrate up
- OTel Demo running locally (26 services), ~4 GB free. `deploy/setup_demo.sh up` reproduces it: clones the demo, applies the overlay, starts everything + `mcp-grafana` + Loki.
- Logs: `mcp-grafana` only queries Loki (no OpenSearch tool), so the overlay adds Loki (`compose.leavitt-loki.yaml`), exports collector logs to it (`otelcol-config-extras.yml`), and provisions a Grafana Loki datasource. Overlay files preserved under `deploy/otel-demo-overlay/` (the demo clone is gitignored).
- Real datasource UIDs: `webstore-metrics` (Prometheus), `webstore-logs-loki` (Loki). `mcp-grafana` runs anonymous (demo Grafana enables anonymous Admin); pass no API key.
- `mcp-grafana` attached to the demo's `opentelemetry-demo` network, `GRAFANA_URL=http://grafana:3000`.

### Three real sources confirmed
- metrics: `query_prometheus` (instant) -> 16 services. Switched from range to **instant** (range returns a matrix Leavitt doesn't need; instant gives current error rate per service and a simpler digest).
- logs: `query_loki_logs` -> real log lines with `service_name` labels.
- deployment: `flagctx` reads the demo's `src/flagd/demo.flagd.json` (flagd hot-reloads on edit -> the chaos primitive). Reports `active_chaos_flags`.

### Chaos primitive works
- Toggling `productCatalogFailure` to `on` (edit the flagd JSON) makes product-catalog emit `STATUS_CODE_ERROR` spans (~1.1/s), cascading to frontend (~4.4) and frontend-proxy (~2.2). flagd reloads on file write.
- Flag names in v2 differ from the spec: `paymentFailure`/`paymentUnreachable`, `adFailure`, `adHighCpu`, `recommendationCacheFailure`, `cartFailure`, plus `productCatalogFailure`, `kafkaQueueProblems`, `loadGeneratorFloodHomepage`, `imageSlowLoad`.

### LLM: Kimi K2.6 via litellm
- Together model string is `together_ai/moonshotai/Kimi-K2.6` (the `Kimi-K2-Instruct-0905` string is non-serverless on Together). Set in `.env`.
- Kimi K2.6 is a **reasoning model**: output is split into `reasoning_content` and `content`. The reasoning consumes the token budget, so `max_tokens` must be generous (8000) or `content` comes back empty (`finish_reason: length`).

### New FSM step: distill_evidence
- Added `distill_evidence` between `correlate_evidence` and `form_hypothesis`. Deterministically reduces raw telemetry to a high-signal digest (service->rate, distinct log lines, active flags) so the exact text the reasoner sees is a recorded ledger entry, and the reasoning model isn't drowned in raw Prometheus matrices. Chose deterministic over a local-model summarizer: auditable, reproducible, cannot drop the smoking-gun log line.

### End-to-end result (productCatalogFailure on)
- Leavitt, driven through Theodosia's `step`, with Kimi in `form_hypothesis`, correctly identified: root cause = `productCatalogFailure` feature flag, affected = product-catalog, frontend, frontend-proxy. All 3 real sources usable, full confidence. It used the metrics (error rates), the deployment flag, and dismissed otel-collector log noise as infrastructure. `tests/live_demo.py`.

## k6 integration: Grafana-native load + a 4th client-side source (Mon May 25)
- The demo's load generator was Locust (Python). Replaced it with **k6** so the whole stack is Grafana-native (k6 -> Prometheus/Loki/Tempo -> Grafana -> mcp-grafana -> Leavitt). `deploy/k6/loadtest.js` mirrors the Locust shopping journey (same endpoints and task weights) so the flagd scenarios still trigger; requests are tagged by endpoint name.
- `compose.leavitt-k6.yaml`: adds the k6 service (remote-writes to Prometheus), neuters Locust to an idle alpine stub (frontend-proxy depends_on it, so it can't be removed), and enables Prometheus's remote-write receiver.
- k6 metrics land in Prometheus as `k6_*` (e.g. `k6_http_reqs_total` by `name`, `k6_http_req_duration_p95`, `expected_response` label marks client failures), queryable via mcp-grafana.
- Added a **4th Leavitt source `client_load`** (`query_client_load` action): client-side failed request rate by endpoint (`k6_http_reqs_total{expected_response="false"}`). This is the user-facing symptom, distinct from server-side span errors. FSM is now metrics -> logs -> client_load -> deployment -> correlate -> distill -> hypothesis -> report.
- k6 2.0's AI features (`k6 x agent`, `mcp-k6` MCP server) are for *authoring/running* tests, which is a write action, so they stay out of Leavitt's read-only graph. Framing note: mcp-k6 writes load, Leavitt reads the resulting telemetry; two MCP agents either side of the system.
- End-to-end with chaos on: Kimi correctly used all four sources, citing "K6 client load tests confirm product endpoint failures at 4.07%" alongside server error rates and the active flag, and reasoned that checkout failures were downstream symptoms. Full confidence, correct root cause.

### Next (Phase 3): benchmark
- Build `examples/scenarios.yaml` (flagd scenarios with expected services), `bench/runner.py` (Kimi drives Theodosia `step`), `bench/baseline_agent.py` (same LLM, raw MCP, no FSM). Run clean / single-fail / multi-fail x Leavitt / baseline. Score per spec.
- Disposition in the deterministic driver is always `degraded` (default); the LLM-driven bench runner will let Kimi choose disposition (so a clean run can reach `resolved`).
