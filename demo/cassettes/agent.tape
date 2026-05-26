# Leavitt's view of a headless Hermes/Nemotron/Crusoe agent driving the enforced
# FSM, rendered live off Theodosia's audit trail. Full-screen, no split.
Output demo/media/leavitt-agent.gif
Output demo/media/leavitt-agent.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1300
Set Height 800
Set Padding 10
Set Theme { "background": "#040A12", "foreground": "#DBD7CF", "cursor": "#F6B755", "selection": "#252F39", "black": "#09121C", "red": "#5D8BB4", "green": "#F6B755", "yellow": "#CB9A5B", "blue": "#5D8BB4", "magenta": "#CB9A5B", "cyan": "#5D8BB4", "white": "#DBD7CF", "brightBlack": "#4A545D", "brightRed": "#5D8BB4", "brightGreen": "#F6B755", "brightYellow": "#F6B755", "brightBlue": "#5D8BB4", "brightMagenta": "#CB9A5B", "brightCyan": "#5D8BB4", "brightWhite": "#F2EEE6" }
Hide
Type "cd ~/leavitt && uv run leavitt agent 'An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible.'" Enter
Sleep 14s
Show
Sleep 72s
