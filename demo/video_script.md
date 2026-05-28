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

[ leavitt-video-run.gif EARLY: load panel + the FSM phases ticking through
  metrics -> logs -> client load -> deployment, sources panel filling. ]
> Leavitt reads your dashboards the way an on-call engineer does. Metrics, logs,
> client load, what just deployed. It correlates them and tells you what broke.
> And it physically cannot touch the thing it's watching.

[ Cut to the FSM diagram or leavitt-enforcement.gif: Theodosia refusing an
  invalid transition with valid next actions listed. ]
> It's a state machine. Every step is checked against the graph before it runs,
> and the graph only knows how to read. Diagnosis with no off-switch to flip.

## 0:35 to 1:00, the run

[ leavitt-video-run.gif LATE: disposition resolved, root cause =
  productCatalogFailure flag causing product-catalog degradation, cascade
  through frontend/checkout/recommendations, 4/4 sources, ten steps. ]
> Here it is on a real incident. It finds the failing service, names the flag
> that caused it, traces the cascade through frontend and checkout, and backs
> it all with evidence.

[ Live screen-capture of your Discord channel as the report card lands (record
  this LIVE during your session with `bash demo/incident.sh catalog --load
  --discord`, so the channel shows a fresh productCatalogFailure post). ]
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
- Asset order: leavitt-masthead.gif, leavitt-video-run.gif (early),
  leavitt-enforcement.gif (or FSM diagram), leavitt-video-run.gif (late, the
  verdict), live Discord screen-capture, leavitt-oncall.gif,
  demo/results_table.md, leavitt-dashboard.gif, leavitt-thumbnail.png.
- The README's leavitt-console.gif / leavitt-discord.gif are deliberately NOT
  used in the video, the README and the video tell DIFFERENT incidents (the
  video is productCatalogFailure; README stays product-reviews / LLM 429).

## What's deliberately not in this video
- **No AIOpsLab on camera.** We built the harness (in `bench/aiopslab/`) and ran
  it honestly, but the cross-model accuracy numbers are mid-iteration. The video
  leads with what we own: read-only architecture, the chaos benchmark, the
  on-call loop. Adding it back is a one-paragraph edit when numbers are final.
- No raw model-name dropping beyond Nemotron / Crusoe / TrueFoundry / Hermes /
  Theodosia. The tagline carries the rest.
