# Live k6 client-load dashboard (demo/loadmon.py), the client_load source Leavitt
# reads, shown on its own. Polls Prometheus once a second.
Output demo/media/leavitt-loadmon.gif
Output demo/media/leavitt-loadmon.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1300
Set Height 410
Set Padding 10
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#F6B755", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && uv run python demo/loadmon.py" Enter
Sleep 10s
Show
Sleep 38s
