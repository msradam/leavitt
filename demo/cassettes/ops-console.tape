# Ops console: live k6 client load (top) above the branded Leavitt agent
# (Hermes / Nemotron / Crusoe, bottom). Vertical split so each pane is full
# width and the agent's Rich output renders without wrapping.
Output demo/media/leavitt-ops-console.gif
Output demo/media/leavitt-ops-console.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1320
Set Height 980
Set Padding 10
Set Theme "Catppuccin Mocha"
Hide
Type "tmux kill-server 2>/dev/null; clear" Enter
Sleep 1s
Type "tmux new-session -d -s ops" Enter
Type "tmux split-window -v -t ops" Enter
Type "tmux resize-pane -t ops.0 -y 16" Enter
Type "tmux send-keys -t ops.0 'cd ~/leavitt && uv run python demo/loadmon.py' Enter" Enter
Sleep 6s
Type "tmux send-keys -t ops.1 'hermes -t leavitt' Enter" Enter
Sleep 7s
Type "tmux send-keys -t ops.1 'An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible.' Enter" Enter
Type "tmux attach -t ops" Enter
Show
Sleep 60s
