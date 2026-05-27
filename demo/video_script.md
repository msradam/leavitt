# Leavitt, demo video script

Target ~2:00, hard cap 3:00. Voiceover is punchy and brisk; it does NOT read the
slides or narrate the obvious. On-screen text carries names and numbers; the VO
carries the idea. Cut fast. `[ ]` = on screen. `>` = voiceover.

---

## 0:00 to 0:12, hook

[ Dark terminal. An alert fires: "webstore error rate spiking." ]
> It's 3am. Something's broken. You want an AI agent to triage it.
> But would you let one loose on your production systems?

[ Title card: Leavitt, on-call AI agent. Turns alerts into answers. ]

## 0:12 to 0:35, what it is

[ The ops console: live k6 load on top, the agent walking its steps below. ]
> Leavitt reads your dashboards the way an on-call engineer does. Metrics, logs,
> client load, what just deployed. It correlates them and tells you what broke.
> And it physically cannot touch the thing it's watching.

[ Highlight: the FSM graph, all read actions, no write edge. ]
> It's a state machine. Every step is checked against the graph before it runs,
> and the graph only knows how to read. Diagnosis with no off-switch to flip.

## 0:35 to 1:05, the run

[ Console finishing: disposition resolved, root cause = llmRateLimitError on
  product-reviews, 4/4 sources. ]
> Here it is on a real incident. It finds the rate-limited service, names it, and
> backs it with evidence, in eight steps, start to finish.

[ Discord: the live message filling in per step, then the report card lands. ]
> It runs headless. Nemotron on Crusoe drives it through the Hermes harness, and
> it files the report to your on-call channel as it works. Alert in, answer out.

[ Quick cuts: cron schedule, webhook trigger, fallback Crusoe to Together. ]
> Schedule it, trigger it from an alert, and when the model provider browns out,
> it fails over and keeps going.

## 1:05 to 1:40, the proof

[ Chaos benchmark table: clean / source-down / malformed. ]
> The interesting part is what happens when the data lies. Kill a source, feed it
> garbage. A bare agent gets confident and wrong. Leavitt degrades, or says
> inconclusive, and it never once invents a cause it can't support.

[ AIOpsLab logo + the FSM running a problem; steps counter staying bounded. ]
> And it's not just our benchmark. It runs on Microsoft Research's AIOpsLab too,
> the same harness used to evaluate cloud-incident agents, where it diagnoses in a
> bounded handful of steps, always terminates, and keeps every step on the record.

# NOTE: AIOpsLab accuracy numbers are mid-iteration (adaptive drill-down). Do not
# claim an accuracy win on camera until the final numbers are in. The line above
# is true and safe as written. Finalize once the adaptive loop lands.

## 1:40 to 2:00, close

[ leavitt sessions / dashboard: the audit trail of past runs. ]
> Every investigation is on the record. Nothing it did is a mystery.
> It only reads, so you can point it at production and walk away.

[ Title: Leavitt. Built on Theodosia. Nemotron on Crusoe. ]
> Leavitt. On call, so you don't have to be.

---

## Delivery notes
- Pace ~150 wpm. Leave a beat after "no off-switch to flip" and after "invents a
  cause it can't support." Those two lines are the payoff; land them.
- Never say a number the viewer can't read in time. Show it, gesture at it
  ("matches on accuracy"), move on.
- Cut the cron/webhook/fallback triad fast. It's a montage, not a tour.
- Assets in order of appearance: leavitt-console.gif, the FSM diagram (README/
  slides), leavitt-discord.gif, leavitt-enforcement.gif, results_table.md +
  bench/aiopslab, leavitt-dashboard.gif, masthead.
