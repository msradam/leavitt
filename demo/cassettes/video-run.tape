# Video B-roll: a productCatalogFailure incident, Hermes / Nemotron / Crusoe,
# distinct from the README's product-reviews / llmRateLimitError run. Flag is
# pre-set by the wrapper script before this tape runs, and reset after.
Output demo/media/leavitt-video-run.gif
Output demo/media/leavitt-video-run.mp4
Set Shell "zsh"
Set FontSize 17
Set Width 1340
Set Height 1120
Set Padding 10
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#F6B755", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && uv run leavitt agent --load 'Users report product pages erroring. Investigate the current state and report the root cause and responsible service.'" Enter
Sleep 14s
Show
Sleep 90s
