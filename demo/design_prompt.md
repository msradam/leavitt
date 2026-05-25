# Leavitt — design prompt

A prompt for generating Leavitt's visual identity and a landing page. Paste into
Claude Code (or a design tool) as the brief. The aesthetic target is enterprise
observability tooling, the world of Grafana, Prometheus, OpenTelemetry, and
developer-infrastructure labs. Not consumer-warm, not the rounded pastel
friendliness of consumer AI products.

## What Leavitt is (context for the designer)

Leavitt is a read-only observability triage agent. It reads metrics, logs, and
deployment context from dashboards through MCP servers, correlates them, and
produces an incident triage report. It is built on Theodosia, a state-machine
runtime that makes the agent structurally unable to act on the systems it
observes. The point of the product is trust: a report you can hand to an on-call
engineer at 3am, with an audit trail of every read.

## Aesthetic direction

Dark-first, data-dense, precise. The visual language of a control room and a
dashboard, not a chatbot. Think Grafana panels, terminal output, monospace
labels, thin rules, tabular numbers. Restraint over decoration. Every element
should look like it carries information.

- **Mood:** instrument, observatory, ops console. Calm, exact, legible under
  pressure.
- **Avoid:** gradients-as-decoration, blobs, rounded oversized cards, emoji,
  hand-drawn or playful marks, marketing hero illustrations, warm beige/cream.

## Palette

- Base: near-black charcoal (#0B0E14 to #11151C), panel surfaces one step
  lighter (#161B22).
- Text: cool off-white (#E6EDF3) primary, muted slate (#8B949E) secondary.
- Single accent: a signal amber/orange (#F2A93B to #FF8800), the observability-
  tooling accent. Use sparingly, for the active signal, the live value, the one
  thing that matters.
- State colors, muted and functional: green (healthy / full confidence), amber
  (degraded), red (failure / inconclusive). Desaturated, not candy.
- Optional secondary: a deep indigo for "deployment context" accents.

## Typography

- Display/headings: a precise grotesque (Inter, IBM Plex Sans, or similar).
  Tight, technical, not friendly.
- Data and labels: a monospace (JetBrains Mono, IBM Plex Mono, Berkeley Mono).
  Use monospace for service names, metric values, action names, dispositions.
- Numbers: tabular figures, aligned.

## The mark

Henrietta Swan Leavitt read photographic plates of the night sky one at a time
and found the period-luminosity relation of Cepheid variable stars, the relation
that became the cosmic distance ladder. The mark should nod to this without
being literal or cute-overboard:

- A Cepheid light curve (a periodic brightness-over-time line) reads as both a
  star's pulse and a latency/error time series on a dashboard. That double
  reading is the whole logo. A single amber light-curve stroke on charcoal.
- Alternative: a faint grid of plotted points evoking a photographic plate, with
  one point marked in amber (the variable star / the anomaly found).
- The wordmark "Leavitt" in the grotesque, lowercase or small-caps, with the
  light-curve mark to its left. One amber accent maximum.

Keep the astronomy reference to the mark and a single line of copy. Do not name
her more than once, and do not lean on the metaphor in UI labels.

## Deliverables

1. **Logo / wordmark** (light-curve mark + "Leavitt"), on dark and on light.
2. **Landing page**, single scroll, dark:
   - Hero: one sentence ("Leavitt reads your dashboards and tells you what
     broke, without touching anything."), the mark, a "Built on Theodosia" line,
     one call to action (GitHub).
   - A triage-report panel as the hero artifact: render an actual Leavitt report
     (disposition, confidence, root cause, affected services, sources used,
     recovery events) styled as a dashboard panel with monospace values and the
     amber accent on the disposition.
   - An architecture strip: the FSM as a horizontal pipeline of named steps
     (receive_query → … → produce_report), with the read-only sources feeding in.
   - A short benchmark table, styled as a data panel.
3. **Report card component**: the unit of the product, the triage report, as a
   reusable dashboard-panel component. This is the most important screen.

## Tone of copy

Plain, declarative, specific. Name the tools (Prometheus, Loki, k6, flagd,
mcp-grafana). No exclamation, no "powerful" or "seamless," no three-word
slogans. State what it does and what it will not do (act on the system).
