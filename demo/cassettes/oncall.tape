# Leavitt on-call feed: alerts arrive, the agent runs, reports go out.
Output demo/media/leavitt-oncall.gif
Set Shell "zsh"
Set FontSize 17
Set Width 1320
Set Height 720
Set Padding 24
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#040A12", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && uv run python demo/oncall.py" Enter
Sleep 4s
Show
Sleep 14s
