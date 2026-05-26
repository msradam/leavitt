# Theodosia enforcement: refusing an invalid transition. gif + mp4.
Output demo/media/leavitt-enforcement.gif
Output demo/media/leavitt-enforcement.mp4
Set Shell "zsh"
Set FontSize 16
Set Width 1180
Set Height 560
Set Padding 16
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#F6B755", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && clear" Enter
Sleep 1s
Show
Type "uv run python demo/show_enforcement.py"
Sleep 800ms
Enter
Sleep 12s
