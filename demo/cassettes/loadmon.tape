# Live k6 client-load dashboard (demo/loadmon.py), the client_load source Leavitt
# reads, shown on its own. Polls Prometheus once a second.
Output demo/media/leavitt-loadmon.gif
Output demo/media/leavitt-loadmon.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1300
Set Height 410
Set Padding 10
Set Theme "Catppuccin Mocha"
Hide
Type "cd ~/leavitt && uv run python demo/loadmon.py" Enter
Sleep 10s
Show
Sleep 38s
