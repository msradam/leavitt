# Leavitt, demo video script

Target ~2:00, hard cap 3:00. Voiceover is punchy and brisk; it does NOT read the
slides or narrate the obvious. On-screen text carries names and numbers; the VO
carries the idea. Cut fast. `[ ]` = on screen. `>` = voiceover.

---

## 0:00 to 0:12, hook

[ Dark terminal. An alert fires: "webstore error rate spiking." ]
> It's 3am. Something's broken. You want an AI agent to triage it.
> But would you let one loose on your production systems?

[ Title card: leavitt-masthead.gif, the alert-fired -> resolved beat ending on
  "Leave it to Leavitt." ]

## 0:12 to 0:35, what it is

[ leavitt-console.gif: live k6 load on top, the agent walking its steps below. ]
> Leavitt reads your dashboards the way an on-call engineer does. Metrics, logs,
> client load, what just deployed. It correlates them and tells you what broke.
> And it physically cannot touch the thing it's watching.

[ Cut to the FSM diagram / leavitt-enforcement.gif refusing an invalid step. ]
> It's a state machine. Every step is checked against the graph before it runs,
> and the graph only knows how to read. Diagnosis with no off-switch to flip.

## 0:35 to 1:00, the run

[ Console hero ends: disposition resolved, root cause = llmRateLimitError on
  product-reviews, 4/4 sources usable, eight steps. ]
> Here it is on a real incident. It finds the rate-limited service, names it, and
> backs it with evidence, in eight steps, start to finish.

[ leavitt-discord.gif: the live message filling in per step, then the report
  card lands. ]
> It runs headless. Nemotron on Crusoe drives it through the Hermes harness; the
> model layer routes through TrueFoundry's gateway, so when a provider browns
> out, the investigation fails over and keeps going.

## 1:00 to 1:30, on call

[ leavitt-oncall.gif: webhook alerts arriving, triages starting, reports posting,
  audit footer "25 runs / 24h, 22 resolved, 3 degraded, 0 confident-wrong." ]
> Wire it to your alerts and this is what a shift looks like. Webhook in, agent
> runs, report out. Every step on the record. Twenty-five runs a day, zero
> confident-wrong.

## 1:30 to 1:50, the proof

[ demo/results_table.md / chaos benchmark: clean / source-down / multi-fail. ]
> Here is what happens when the data lies. Kill a source, feed it garbage. A bare
> agent gets confident and wrong. Leavitt degrades, or says inconclusive, and it
> never once invents a cause it can't support.

## 1:50 to 2:00, close

[ leavitt-dashboard.gif: the audit-trail dashboard, recent runs scrolling. ]
> Every investigation is on the record. Nothing it did is a mystery.
> It only reads, so you can point it at production and walk away.

[ Title card: leavitt-thumbnail.png. "Leavitt. On-Call AI Agent. Turns Alerts
  Into Answers." with "Leave it to Leavitt." kicker. ]
> Leave it to Leavitt.

---

## Delivery notes
- Pace ~150 wpm. Leave a beat after "no off-switch to flip" and after "invents a
  cause it can't support." Those two lines are the payoff; land them.
- The "Leave it to Leavitt." outro lands clean, no rush. Let the title card sit.
- Never say a number the viewer can't read in time. Show it, move on.
- Asset order: leavitt-masthead.gif, leavitt-console.gif, FSM diagram or
  leavitt-enforcement.gif, leavitt-discord.gif, leavitt-oncall.gif,
  demo/results_table.md, leavitt-dashboard.gif, leavitt-thumbnail.png.

## What's deliberately not in this video
- **No AIOpsLab on camera.** We built the harness (in `bench/aiopslab/`) and ran
  it honestly, but the cross-model accuracy numbers are mid-iteration. The video
  leads with what we own: read-only architecture, the chaos benchmark, the
  on-call loop. Adding it back is a one-paragraph edit when numbers are final.
- No raw model-name dropping beyond Nemotron / Crusoe / TrueFoundry / Hermes /
  Theodosia. The tagline carries the rest.
