#!/usr/bin/env bash
# Drive one incident end to end: enable its flagd flag, run Leavitt against it,
# reset the flag on exit. Each incident has a different root cause and symptom
# shape, so the demo shows more than one failure mode.
#
#   ./demo/incident.sh catalog            # console
#   ./demo/incident.sh ad-latency --load --discord
#
# Incidents (flag -> what Leavitt should find):
#   catalog      productCatalogFailure   product-catalog erroring
#   cart         cartFailure             cart erroring
#   reviews      llmRateLimitError       product-reviews LLM rate-limited (429s)
#   ad-latency   adManualGc              ad service slow, no errors (GC pauses)
set -euo pipefail

cd "$(dirname "$0")/.."
FLAGD="deploy/opentelemetry-demo/src/flagd/demo.flagd.json"

case "${1:-}" in
  catalog)    FLAG=productCatalogFailure; Q="Users report product pages erroring. Investigate and report the root cause and responsible service." ;;
  cart)       FLAG=cartFailure;           Q="Users cannot view or update their cart. Investigate and report the root cause and responsible service." ;;
  reviews)    FLAG=llmRateLimitError;     Q="An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible." ;;
  ad-latency) FLAG=adManualGc;            Q="The ad service feels sluggish but nothing is erroring. Investigate and report what is going on." ;;
  *) echo "usage: $0 {catalog|cart|reviews|ad-latency} [--load] [--discord]"; exit 2 ;;
esac
shift

set_flag() { python3 - "$FLAGD" "$FLAG" "$1" <<'PY'
import json, sys
path, flag, variant = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(path))
d["flags"][flag]["defaultVariant"] = variant
json.dump(d, open(path, "w"), indent=2)
PY
}

reset() { set_flag off; echo "reset $FLAG -> off"; }
trap reset EXIT

echo "enabling $FLAG, waiting for signal to build..."
set_flag on
sleep 45
uv run leavitt agent "$@" "$Q"
