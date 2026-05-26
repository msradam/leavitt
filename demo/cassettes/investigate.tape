# Hero demo: Leavitt triages a live incident. Exports gif + mp4.
Output demo/media/leavitt-investigate.gif
Output demo/media/leavitt-investigate.mp4

Set Shell "zsh"
Set FontSize 14
Set Width 1280
Set Height 900
Set Padding 16
Set Theme "Catppuccin Mocha"

# --- hidden setup ---
Hide
Type "cd ~/leavitt && set -a && source .env && set +a" Enter
Type "export LEAVITT_GRAFANA_MCP=http://localhost:8000/sse" Enter
Type "export LEAVITT_FLAGCTX_CONFIG=$PWD/deploy/opentelemetry-demo/src/flagd/demo.flagd.json" Enter
Type "clear" Enter
Sleep 1s
Show

# --- the demo ---
Type "uv run leavitt investigate 'Users report product pages are erroring. What is the root cause?'"
Sleep 1s
Enter
Sleep 48s
Sleep 3s
