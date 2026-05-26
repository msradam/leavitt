---
marp: true
size: 16:9
paginate: false
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Sans:wght@300;400&family=IBM+Plex+Mono:wght@400&display=swap');

:root {
  --plate: #040A12;
  --panel: #09121C;
  --ink: #DBD7CF;
  --ink-dim: #78746D;
  --star: #F6B755;
  --moon: #5D8BB4;
  --hair: #252F39;
}
section {
  background: var(--plate);
  color: var(--ink);
  font-family: "IBM Plex Sans", sans-serif;
  font-weight: 300;
  padding: 80px 110px;
  letter-spacing: 0.01em;
  position: relative;
}
h1 { font-family: "Instrument Serif", serif; font-weight: 400; font-size: 92px; color: var(--ink); margin: 0; letter-spacing: 0.04em; }
h2 { font-family: "Instrument Serif", serif; font-style: italic; font-weight: 400; font-size: 50px; color: var(--ink); margin: 0 0 40px; line-height: 1.15; }
p  { font-size: 27px; line-height: 1.5; max-width: 22em; color: var(--ink); }
em { color: var(--moon); font-style: italic; }
strong { color: var(--star); font-weight: 400; }
.cat { font-family: "IBM Plex Mono", monospace; font-size: 16px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--ink-dim); }
.star { color: var(--star); }
.colophon { position: absolute; bottom: 44px; left: 110px; font-size: 12.5px; letter-spacing: 0.08em; line-height: 2.1; white-space: nowrap; }
hr { border: 0; border-top: 1px solid var(--hair); margin: 26px 0; }
.big-star { font-size: 64px; color: var(--star); line-height: 1; }
</style>

<!-- Slide 1: title -->

<div class="big-star">✦</div>

# LEAVITT

<h2 style="font-size:38px; margin-top:24px;">It reads your dashboards and tells you what broke.</h2>

<p class="cat">On-call incident triage &nbsp;·&nbsp; built on Theodosia</p>

<p class="colophon cat">
Adam Munawar Rahman &nbsp;·&nbsp; SWE @ IBM &nbsp;·&nbsp; M.S. Computer Engineering, NYU Tandon<br>
DevNetwork [AI + ML] Hackathon 2026 &nbsp;·&nbsp; AI DevSummit
</p>

---

<!-- Slide 2: the method -->

<p class="cat">§ I &nbsp; Method</p>

## Read the plate. Find the pattern.<br>Never touch the sky.

<p>
Henrietta Swan Leavitt found the period–luminosity law by reading thousands of
glass plates by hand. Leavitt reads your dashboards the same way:
<strong>metrics, logs, client load, deployment</strong>, one source at a time, and
reports the cause, with a confidence <em>bounded by the evidence</em>.
</p>

<p>
It does the reading; it never acts. That is why you can leave it pointed at
production.
</p>

---

<!-- Slide 3: leave it running -->

<p class="cat">§ II &nbsp; On call</p>

## Leave it running.

<p>
A <strong>Hermes agent running NVIDIA Nemotron on Crusoe</strong> drives the
enforced FSM, on demand or on a schedule. It wakes, reads the dashboards, and
reports the cause.
</p>

<p>
Its worst case under chaos is a <em>visible incomplete trace</em>, not a
confident wrong page.
</p>

<p style="margin-top:52px;" class="cat"><span class="star">✦</span> &nbsp; Watch it read.</p>
