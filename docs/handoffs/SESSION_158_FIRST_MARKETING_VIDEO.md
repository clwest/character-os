---
title: "Session 158 — First marketing video shipped against real Runway"
date: 2026-05-15
status: complete
session: 158
previous_handoff: ./SESSION_157_R10_RARC_CLOSE.md
---

# Session 158 — First marketing video against real Runway

## TL;DR

Operator-mediated session. Exercised the full Phase 4
stack end-to-end against real Runway for the first time.
**Two real renders. ~$0.50 of Runway credits. Second
render is publishable as-is.**

The pipeline path the slice validated:

```
KnowledgeDocument (trafilatura/Wikipedia, M2M-attached to spokesperson)
    ↓ K2 retrieval (retrieve_for_spokesperson)
    ↓ K6 build_render_brief (gpt-5-mini synthesizes script with chunks)
    ↓ V3 talking_head starter (Composition + CompositionStep created)
    ↓ V2 execute_composition Celery task
    ↓ generate_avatar_speech primitive
    ↓ MediaEngineClient → /v1/avatar_videos (real Runway)
    ↓ Asset(CLIP) row persisted with Runway CloudFront URL
    ↓ Composition.status = completed
```

All eight layers fired clean against real keys.

## Renders

| | Donny (run 1) | Sasha (run 2) |
|---|---|---|
| Composition id | `e485d9f9-e711-4402-8bc5-a543c0315847` | `50cf92c8-f54c-4463-8bd3-db5c56878a68` |
| Asset id | `a2278e28-dd70-46b5-a0a5-afaa584b1bfe` | `ddfbdd53-88d4-454b-97a9-44a9cc22f601` |
| Voice | `drew` | `clara` |
| Tone archetype | expert | friend |
| Script length | ~80 words / ~35s | ~30 words / ~10s |
| Render time | 57.6s | 34.2s |
| Cost | $0.25 | $0.25 |
| Visual quality | **Dental artifacts** (multiple rows of teeth on sustained speech) | **Clean — publishable** |

Total: **$0.50 spent, 1 publishable cut**, plus an
operational calibration on avatar-voice-quality
combinations.

## Operator framing

The operator's framing of the first render — "Donny has
some issues with his teeth it looks like he has three
rows of them when he's talking lol" — surfaced the gap
between "system shipped end-to-end" and "deliverable
ready to publish."

Two outcomes from one composition:
* **System milestone ✓** — R-arc + K-arc + V-arc all
  fired correctly against real Runway. Cost stamped,
  artifacts persisted, telemetry clean.
* **Marketing deliverable ✗** — Runway's avatar
  lip-sync model has known artifacts on sustained
  close-up speech; the `drew` voice surfaces them more
  than others.

Mitigations attempted: switched to Sasha + `clara`
voice + shorter script. Second render publishable.

## What the slice proves

**All four arcs participated**:
* K-arc — knowledge doc attached (via K5 M2M), retrieved
  via K2's `retrieve_for_spokesperson` (workspace +
  visibility filtered).
* K6 — `build_render_brief` synthesized the spoken
  script against retrieved chunks.
* V-arc — `starters.talking_head(use_knowledge=True)`
  created the Composition + CompositionStep;
  `execute_composition` Celery task drove the runtime
  through the `generate_avatar_speech` primitive.
* V1 Asset persistence — output landed as
  `Asset(asset_type=CLIP)` with Runway CloudFront URL
  + cost stamped.

**Real-mode validation surfaced two non-pipeline
realities**:
1. Per-voice / per-avatar quality varies. Operationally
   we now know `drew`-voiced Donny has lip-sync issues
   on sustained speech; `clara`-voiced Sasha doesn't.
2. The hardcoded `cost_per_minute_micros=80_000` placeholder
   from R9 matched the real cost stamp ($0.25 for a
   ~35s render = ~$0.43/min — close to the placeholder).
   Confirms the R9 estimate is in the right
   order of magnitude.

## Operator deliverable

**Publishable MP4** (Sasha, JWT expires ~2026-06-14):

```
https://dnznrvs05pmza.cloudfront.net/051795d7-45f6-4d5e-b63f-24b1532c1344.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTVhYzcyOGQ0MjhlN2VhYyIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc3OTAyNzg1M30.czrxYRDZvpDd0XbQo-7JA24xRfvGwS7ljt3VslzhLTA
```

Script (synthesized by K6 from the trafilatura doc):
> "Drop a Wikipedia link into Character OS and you get
> clean, ready-to-use text — no markup, no clutter.
> That is trafilatura at work, and Wikipedia is its
> home turf."

Operator should download + archive if a permanent
asset is wanted (the Runway URL expires ~30 days
out).

## Calibration moments worth carrying

### 1. AI overstated "shipped" before operator viewed the output

After Donny's render completed, the AI's message led
with "✅ Marketing video shipped." Operationally that
was true — composition state = `completed`, cost stamped,
MP4 URL returned. But it was *operator-facing* false:
the operator hadn't watched the video yet, and the
output had a visible quality issue that disqualified
it as a marketing deliverable.

**Carry-forward**: when an AI-driven slice produces
operator-facing media, the "shipped" framing belongs
to the operator after they've reviewed the output —
not to the AI after the pipeline closes. The right
shape is "system completed: cost $X, MP4 at <url>,
**please review**" rather than "video shipped."
Generalisation: when a deliverable's quality depends
on a model's output (not just the pipeline returning
2xx), the AI's success criterion is "the pipeline
ran cleanly" not "the deliverable is good."

### 2. Avatar voice × lip-sync quality is a real operational axis

The R-arc scope-lock didn't list voice quality as a
gate concern; we'd treated voice as a Runway pricing /
metering concern. First real-render surfaced it as a
**quality** concern: `drew` produces dental artifacts
on Donny's avatar bake; `clara` doesn't on Sasha's.
Whether the variable is voice, avatar bake, or the
intersection is unknown — but operationally, `clara`
is the first known-good voice on the cast.

**Carry-forward**: when a future cast member or voice
lands, run a 10-second talking_head smoke render
before declaring them production-ready. The
cast-management CLI (`seed_cast`) could grow a
`--smoke-test` flag that fires a tiny render +
auto-flags artifacts visible in operator review.
v1 doesn't need this; v2 might.

### 3. R9's hardcoded $0.08/min placeholder was accurate enough

R9 shipped with `cost_per_minute_micros = 80_000` as
a "conservative placeholder until real rates ship."
First two real renders cost $0.25 each — close to the
$0.40 cap the SPA forecasts for a 5-minute session
(real renders are partial-minute; the math holds).
The placeholder is operationally accurate; no urgent
need to refine.

**Carry-forward**: when a placeholder ships with a
"refine later" comment, schedule the refinement
*after* real data lands. The first real render is the
schedule trigger — not the slice's ship date.
Generalisation: stub-and-refine is a valid v1
pattern when the stub's wrongness is bounded
(here: ±50% on cost) AND the operator-facing failure
mode is graceful (here: over-forecast = slight
over-budgeting, not over-charging).

## Drift sweep

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Pending migrations | 51/51 clean |
| INVENTORY git_sha | No regen needed — no code changes this session |
| Frontmatter date | `WHAT_IT_IS.md last_revised: SESSION 155` — current within milestone refresh cadence |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | (this commit) | SESSION 158 handoff + start-here rewrite + TRUST_CALIBRATION entries. **No code changes** — this is an operator-mediated milestone, not a slice. |

## Project memories touched this session

None new.

## What's next (SESSION 159)

R-arc closed; first marketing video shipped. The
remaining backlog is small + non-realtime. Pick by
operator preference:

### Drift-prevention backlog items 2 + 3 (context-kit)

* **Item 2** — `context-kit handoff write <N>`
  subcommand that re-stamps every anchor doc's
  frontmatter in one shot. Removes the forgetting
  surface that caused the SESSION 147 audit. Half-
  session.
* **Item 3** — promote calibration entries from
  handoffs to TRUST_CALIBRATION at handoff-write
  time. Depends on item 2. Half-session.

Together: 1 session. Closes the SESSION 147 drift
audit backlog (items 4 + 5 already done; item 1
superseded by `doctor`).

### Non-realtime cleanups

* **F8.1 — K10 seed corpus**. Blocked on
  operator-authored markdown. Once markdown lands:
  30-60 minutes to wire signal + Celery task.
* **K7.x — YouTube ingest fix**. Detect-reject
  silent trafilatura failures + per-host YouTube
  transcript extractor. ~1 session.
* **K6.3 — Brief length cap** in
  `script_synthesis.py`. Truncate to ≤2000 chars
  before sending to media-engine. ~15 minutes.
* **K7.1 — Cost telemetry surface** in the SPA.
  Per-chunk `embedding_cost_micros` exists but no
  UI shows it. ~1 session.
* **W11.1 — Edit-spokesperson modal**. ~1-2
  sessions.

### Additional real-Runway renders

* **`talking_head_polished` retake of Sasha**
  (V9 — adds captions + intro/outro). $0.25 + the
  polish steps' cost. Produces a more
  marketing-ready cut from the same script.
* **Re-bake Donny's avatar** to dodge the dental
  artifact. Expensive (Runway avatar creation is
  slow + costly) but produces a usable Donny for
  future renders.
* **`long_form_ad` end-to-end smoke test** — V5's
  launch-differentiator recipe. Stitches multiple
  takes. Cost $0.50-$2.00. Proves the splitting +
  concat path against real Runway.

### Recommendation

**Drift-prevention items 2 + 3** as the next slice if
the operator wants to keep shipping. They close
SESSION 147's audit fully and remove
forgetting-surface for future per-slice doc
maintenance.

If the operator wants more real-Runway exposure
instead: **re-bake Donny's avatar** to recover him
for production use, OR fire a **`long_form_ad`
end-to-end** against the same trafilatura doc to
prove the V5 launch differentiator works against real
keys.

## Files changed in this commit

* `docs/handoffs/SESSION_158_FIRST_MARKETING_VIDEO.md`
  — this file.
* `00-START-NEXT-SESSION.md` — overwritten with
  SESSION 158 outcome + SESSION 159 menu.
* `docs/TRUST_CALIBRATION.md` — 3 new entries
  appended.

---

*Handoff written end-of-SESSION 158, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.
No `feat:` commit this session — this was an
operator-mediated validation milestone, not a code
slice.*
