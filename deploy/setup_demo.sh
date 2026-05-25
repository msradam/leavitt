#!/usr/bin/env bash
# Bring up the OpenTelemetry Demo as Leavitt's substrate, with Loki added so the
# logs source is queryable through mcp-grafana (the demo ships logs to OpenSearch,
# which mcp-grafana cannot query).
#
#   ./setup_demo.sh up      clone demo, apply overlay, start everything
#   ./setup_demo.sh down    stop the demo and mcp-grafana
set -euo pipefail
cd "$(dirname "$0")"

DEMO_DIR=opentelemetry-demo
OVERLAY=otel-demo-overlay
COMPOSE=(-f compose.yaml -f compose.observability.yaml -f compose.leavitt-loki.yaml -f compose.leavitt-k6.yaml)

apply_overlay() {
  cp "$OVERLAY/compose.leavitt-loki.yaml" "$DEMO_DIR/"
  cp "$OVERLAY/compose.leavitt-k6.yaml" "$DEMO_DIR/"
  cp "$OVERLAY/grafana-datasources/loki.yaml" "$DEMO_DIR/src/grafana/provisioning/datasources/"
  cp "$OVERLAY/otel-collector/otelcol-config-extras.yml" "$DEMO_DIR/src/otel-collector/"
  mkdir -p "$DEMO_DIR/k6-scripts"
  cp "$OVERLAY/k6-scripts/loadtest.js" "$DEMO_DIR/k6-scripts/"
}

case "${1:-up}" in
  up)
    [ -d "$DEMO_DIR" ] || git clone --depth 1 https://github.com/open-telemetry/opentelemetry-demo "$DEMO_DIR"
    apply_overlay
    ( cd "$DEMO_DIR" && docker compose "${COMPOSE[@]}" pull && docker compose "${COMPOSE[@]}" up -d )
    # mcp-grafana on the demo network, anonymous (demo Grafana enables anonymous Admin)
    docker rm -f leavitt-mcp-grafana >/dev/null 2>&1 || true
    docker run -d --name leavitt-mcp-grafana --network opentelemetry-demo -p 8000:8000 \
      -e GRAFANA_URL=http://grafana:3000 mcp/grafana:latest
    echo "demo up. flagd UI: http://localhost:8080/feature  mcp-grafana: http://localhost:8000/sse"
    echo "datasource UIDs: webstore-metrics (Prometheus), webstore-logs-loki (Loki)"
    echo "load: k6 (replaces Locust), client metrics remote-written to Prometheus as k6_*"
    ;;
  down)
    ( cd "$DEMO_DIR" && docker compose "${COMPOSE[@]}" down )
    docker rm -f leavitt-mcp-grafana >/dev/null 2>&1 || true
    ;;
  *) echo "usage: $0 {up|down}"; exit 1 ;;
esac
