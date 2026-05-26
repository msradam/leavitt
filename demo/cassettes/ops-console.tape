# Ops console: live load (xk6-top) beside the branded Leavitt agent (Hermes/Nemotron/Crusoe).
Output demo/media/leavitt-ops-console.gif
Output demo/media/leavitt-ops-console.mp4
Set Shell "zsh"
Set FontSize 13
Set Width 1500
Set Height 820
Set Padding 8
Set Theme "Catppuccin Mocha"
Hide
Type "tmux kill-server 2>/dev/null; clear" Enter
Sleep 1s
Type "tmux new-session -d -s ops -x 232 -y 60" Enter
Type "tmux split-window -h -t ops" Enter
Type "tmux send-keys -t ops.0 'k6top --url http://localhost:5665' Enter" Enter
Sleep 3s
Type "tmux send-keys -t ops.1 'hermes -t leavitt' Enter" Enter
Sleep 7s
Type "tmux send-keys -t ops.1 'An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible.' Enter" Enter
Type "tmux attach -t ops" Enter
Show
Sleep 78s
