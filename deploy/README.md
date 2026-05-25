# Substrate

Leavitt reads from the OpenTelemetry Demo (the Astronomy Shop) through MCP
servers. This directory brings up the demo, the Grafana MCP server Leavitt
queries, and a small feature-flag context server.

## 1. OpenTelemetry Demo

The demo runs 15+ instrumented microservices plus Prometheus, Grafana, Jaeger,
OpenSearch, a load generator, and flagd. flagd injects failures on demand.

```bash
make demo-up        # pulls and starts the demo via docker compose
```

Endpoints once healthy:

- Frontend / store: http://localhost:8080
- Grafana: http://localhost:8080/grafana
- flagd UI (chaos toggles): http://localhost:8080/feature
- Prometheus: http://localhost:9090 (internal to the compose network by default)

flagd flags used as chaos primitives: `productCatalogFailure`,
`paymentServiceFailure`, `recommendationServiceCacheFailure`, `adServiceFailure`,
`adServiceManualGc`, `adServiceHighCpu`, `cartServiceFailure`,
`kafkaQueueProblems`, `loadgeneratorFloodHomepage`, `imageSlowLoad`.

## 2. Grafana MCP server

Leavitt talks to the official Grafana MCP server (`mcp-grafana`), pointed at the
demo's Grafana. It exposes `query_prometheus` and `query_loki_logs`, the tools
Leavitt's metric and log actions call.

```bash
make mcp-up         # starts mcp-grafana on http://localhost:8000/mcp
```

`mcp-grafana` reads `GRAFANA_URL` and `GRAFANA_API_KEY` from the environment.
See `mcp-servers.yml` for the wiring.

## 3. Feature-flag context server

The third source reports the current flagd configuration as deployment context.
It answers "what changed" without touching the system. It is a thin MCP server
in `flagctx_server.py`.

```bash
make flagctx-up
```

## Pointing Leavitt at the stack

```bash
export LEAVITT_GRAFANA_MCP=http://localhost:8000/mcp
export LEAVITT_FLAGCTX_MCP=...        # stdio or http transport for flagctx
export LEAVITT_PROM_UID=webstore-metrics
export LEAVITT_LOKI_UID=webstore-logs
```

Then drive Leavitt against it (see the repository README).
