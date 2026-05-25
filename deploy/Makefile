DEMO_REF ?= main
DEMO_DIR := opentelemetry-demo
DEMO_COMPOSE_URL := https://raw.githubusercontent.com/open-telemetry/opentelemetry-demo/$(DEMO_REF)/docker-compose.yml

.PHONY: demo-fetch demo-up demo-down mcp-up mcp-down flag-list

demo-fetch:
	mkdir -p $(DEMO_DIR)
	curl -fsSL $(DEMO_COMPOSE_URL) -o $(DEMO_DIR)/docker-compose.yml
	@echo "fetched demo compose at ref $(DEMO_REF)"

demo-up: demo-fetch
	docker compose -f $(DEMO_DIR)/docker-compose.yml up -d
	@echo "demo starting; frontend at http://localhost:8080  flagd UI at http://localhost:8080/feature"

demo-down:
	docker compose -f $(DEMO_DIR)/docker-compose.yml down

mcp-up:
	docker compose -f docker-compose.mcp.yml up -d
	@echo "mcp-grafana at http://localhost:8000/mcp"

mcp-down:
	docker compose -f docker-compose.mcp.yml down

# Toggle a flagd chaos flag. Usage: make flag-set FLAG=productCatalogFailure STATE=on
flag-set:
	@echo "set $(FLAG)=$(STATE) via the flagd UI at http://localhost:8080/feature"
