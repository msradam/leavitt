# Leavitt's view of a headless Hermes/Nemotron/Crusoe agent driving the enforced
# FSM, rendered live off Theodosia's audit trail. Full-screen, no split.
Output demo/media/leavitt-agent.gif
Output demo/media/leavitt-agent.mp4
Set Shell "zsh"
Set FontSize 18
Set Width 1300
Set Height 800
Set Padding 10
Set Theme "Catppuccin Mocha"
Hide
Type "cd ~/leavitt && uv run leavitt agent 'An alert fired for the webstore. Investigate the current state and report what is wrong and which service is responsible.'" Enter
Sleep 14s
Show
Sleep 72s
