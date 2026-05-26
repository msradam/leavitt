# Leavitt README banner: wordmark + a slowly pulsing Cepheid star.
Output demo/media/leavitt-banner.gif
Set Shell "zsh"
Set FontSize 22
Set Width 1200
Set Height 360
Set Padding 24
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#040A12", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && uv run python demo/banner.py" Enter
Sleep 1500ms
Show
Sleep 3200ms
