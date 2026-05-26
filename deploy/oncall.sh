#!/usr/bin/env bash
# Leavitt on-call loop: investigate (read-only), then deliver the report.
#
# This is what a schedule or an alert invokes. The investigation is a headless
# Hermes/Nemotron run that drives the read-only Leavitt MCP; delivery is a
# separate step that reads the audit trail and posts to Discord. The agent never
# writes; the harness does.
#
#   ./deploy/oncall.sh "An alert fired for the webstore. Root cause?"
#
# Wire it to a schedule with `hermes cron`, or to an alert with `hermes webhook`.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }

INCIDENT="${1:-An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible.}"

hermes -t leavitt -z "$INCIDENT"     # Nemotron drives the enforced FSM, recorded
uv run leavitt report --discord      # post the latest triage report to Discord
