# Hero demo: Leavitt triages a live incident. gif + mp4.
Output demo/media/leavitt-investigate.gif
Output demo/media/leavitt-investigate.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1080
Set Height 840
Set Padding 14
Set Theme "Catppuccin Mocha"
Hide
Type "cd ~/leavitt && set -a && source .env && set +a" Enter
Type "export LEAVITT_GRAFANA_MCP=http://localhost:8000/sse" Enter
Type "export LEAVITT_FLAGCTX_CONFIG=$PWD/deploy/opentelemetry-demo/src/flagd/demo.flagd.json" Enter
Type "export LEAVITT_LLM=together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo" Enter
Type "clear" Enter
Sleep 1s
Show
Type "uv run leavitt investigate 'Users report product pages are erroring. What is the root cause?'"
Sleep 1s
Enter
Sleep 20s
Sleep 3s
