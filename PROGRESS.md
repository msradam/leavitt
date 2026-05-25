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

### Next (Phase 2)
- Bring up the OTel Demo and `mcp-grafana`; confirm `query_prometheus` / `query_loki_logs` tool names and datasource UIDs against the real instance.
- Run one scenario end-to-end against real telemetry with a flagd flag enabled; confirm the injected failure shows up in Prometheus and Leavitt finds it.
- Verify Kimi over litellm end-to-end (real key).

### Blockers
- None yet. `mcp-grafana` tool names and Grafana datasource UIDs are assumed; verify against the running instance in Phase 2.
