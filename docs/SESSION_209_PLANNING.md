---
title: "SESSION 209 — Working Plan + Backlog Snapshot"
status: working
generated: 2026-05-20
purpose: "Scratch doc for SESSION 209 — captures everything mid-discussion before BC5 dogfood opens. Distilled into the handoff at session close."
---

# SESSION 209 — Working Plan

> **Scratch doc.** This is the working surface while we
> map SESSION 209's scope before opening BC5. It captures
> every thread we've pulled today so we don't lose them
> when fatigue or context-switching kicks in. Distill
> what's load-bearing into `docs/handoffs/SESSION_209_*.md`
> at session close and delete the rest.

---

## Original FIRST THING

**BC5 — composition arc dogfood + close.** Marcus × Five
Good Emperors Script × 2 recipients × ~$0.50. See
`00-START-NEXT-SESSION.md` for the full plan.

**Status:** queued. Stack is up and verified
(commit-cleanly post-BC3 Celery + Django). The dogfood
hasn't fired yet — we sidebared into UI cleanup first.

---

## What shipped in SESSION 209 so far

### 1. Nav rail expansion (`bab6b93`)

Rail expanded from 5 → 11 entries. Five post-F-arc
surfaces had been shipping for sessions without nav
entries — operators were typing URLs to reach them.
Each surface is already scope-locked by its own design
doc (F0 contract rule 7 satisfied). Hard-count
regression net updated.

### 2. Videos library (`bab6b93`)

`/workspace/videos` — paginated composition browse view.
Backend: `CompositionPagination` (25/page default, 100
max), light `CompositionListSerializer`, status +
spokesperson filters, `-created_at` order. Spokesperson
detail's Renders panel surfaces "View all in library →"
pre-filtered.

### 3. Scripts list Zod fix (`86f002f`)

Drift between `ScriptListSerializer` (omits
`knowledge_chunk_ids` for perf) and SPA's
`scriptListItemSchema` (required it). Fix:
`knowledge_chunk_count` SerializerMethodField on the
shared base; SPA Zod schema updated; BC4 picker
consumer updated.

### 4. Runtime cleanup (uncommitted — data only)

| Sweep | Rows | Disk |
|---|---|---|
| Failed/partial/draft compositions | 13 + 45 steps | — |
| Orphan asset DB rows | 20 | — |
| Orphan local files | — | 14 MiB |
| `https_expired` asset rows | 56 | — |
| **Total** | **89 + 45 steps** | **~14 MiB** |

Path B (soft-delete via `archived_at` + DELETE endpoint)
still queued.

### 5. TRUST_CALIBRATION entry appended

*Expired-asset accumulation has no purge mechanism.*
The V1 "no destroy" design implicitly assumed manual
hygiene. SPA doesn't surface the rot. Three follow-up
candidates documented in the calibration entry.

---

## Findings the operator surfaced mid-session

### Finding A — Voiceover flows (two distinct shapes)

**A1. Add spokesperson voiceover to a storyboard ad.**

**Status: ALREADY SHIPPED as `storyboard_voiced` (V15.4).**
Composition shape: 3 storyboard frames → 3 visual clips
→ silent concat → spokesperson narration as
talking-head → audio_extract → mix_audio under the
silent storyboard. Workspace already has one
(`05-20 01:31 | storyboard_voiced | Riggs`).

**The actual gap is discoverability.** When operator
opens the recipe gallery looking to "make an ad with
voiceover," they hit `storyboard_ad` (no voiceover, no
spokesperson) instead of `storyboard_voiced`. Recipe
gallery labels need a copy pass.

**Proposed fix:** ½-session slice. Audit the recipe
gallery's `display_name` + `description` strings.
Group related recipes visually (e.g. *Storyboard ads*
section pairs `storyboard_ad` with `storyboard_voiced`
side-by-side, with the difference called out).

---

**A2. Post-hoc voiceover injection at specific
timestamps.**

**Status: NOT SHIPPED. Genuinely new flow.**

What it means: take an already-rendered video, inject a
voiceover at a specific time window (e.g. "at 0:05–0:08,
overlay spokesperson saying X"). Different shape from
A1 because:

- A1 is a **single-shot recipe** — operator picks the
  recipe, fills the form, fires once, gets the final
  composition.
- A2 is a **post-production edit** — operator picks an
  existing composition + a voiceover script + a time
  range, and produces a NEW composition that's the
  original + voice overlay at the right offset.

**Primitives needed:** already have `generate_avatar_speech`
(or `dub_audio` for voice-only), `audio_extract`,
`mix_audio` (currently mixes full-length, would need
an offset arg).

**Primitives missing:** time-offset audio mixing.
`mix_audio` today assumes the voice/music starts at
t=0. Need either:
- Extend `mix_audio` with `start_offset_ms` (cleanest)
- New primitive `insert_audio_at` (more explicit)

**SPA gap:** a timeline-aware editor. Even minimal:
duration slider over the composition's final clip
+ start time picker for the voiceover. Probably
~1 session for backend (offset arg + new recipe like
`voiceover_insert`) + ~1 session for the SPA editor.
Could be MVP'd with numeric inputs (no visual
timeline) for ½ session.

**Scope-lock candidate.** This is its own arc —
**VO0** through whatever. New design doc should land
before any code.

---

### Finding B — Spokesperson missing from "ads"

**Root cause: operator was hitting `storyboard_ad`
thinking it was the equivalent of the hackathon's
long-ad service.** Today's `long_form_ad` IS the
hackathon's `long_ad_service.py` equivalent — both
are avatar-speech-only chunked + concatenated.
`storyboard_ad` (V13) is a different shape — it
generates AI-imagined storyboard frames from a prompt
and has no `generate_avatar_speech` step. The
"random people or things" in the output are exactly
what the prompt described — Runway imagined them.

**The fix is the same as A1's fix** — recipe gallery
copy / grouping pass so operators don't conflate
`storyboard_ad` with their intended "ad" recipe.

Riggs's avatar setup is fine
(`runway_avatar_id=ee1ccd6e-...`). All four cast
spokespeople (Riggs, Sasha, Donny, Marcus) have
valid avatars + portraits.

---

### Finding C — Runtime hygiene gap

Captured in the TRUST_CALIBRATION entry. Short
version: 19 `expiring_soon` Runway URLs will graduate
to `expired` within ~24h. No automated purge. Three
follow-up candidates:

1. Celery Beat sweep (½ session)
2. Storage-health filter on Videos library (small)
3. "Bake to local" preserve-before-expire (medium —
   different shape; preserves media instead of
   accepting loss)

---

## Full backlog (composite from start-here + this session)

### Path A — Slices ready to go (effort tagged)

| | Slice | Effort | Source |
|---|---|---|---|
| 1 | **BC5 — composition arc dogfood + close** | ½ session | start-here FIRST THING |
| 2 | Composition-detail verifier panel polish | ½ slice | SESSION 207 finding |
| 3 | B-2 v2 polish slice | ½ session | SESSION 207 findings |
| 4 | B-14 v2 `offset_x` knob | ½ session | SESSION 205 finding |
| 5 | **Recipe gallery copy + grouping pass** | ½ session | **NEW SESSION 209 — finding A1 + B** |
| 6 | Marcus rig re-bake | quick | SESSION 207 finding |
| 7 | Storage-health filter on Videos library | small | **NEW SESSION 209 — finding C** |
| 8 | Asset upload UI | 1-2 sessions | start-here queue |
| 9 | F8.1 — K10 seed corpus | blocked | start-here queue |
| 10 | K7.x v3 YouTube oEmbed | queued | memory |
| 11 | K6.4 v3 architectural fix | queued | start-here queue |
| 12 | W12 legacy form retirement | queued | start-here queue |
| 13 | B-2 v2 `auto_script_polished` + `auto_script_cinematic` | queued | start-here queue |

### Path B — New surfaces / arcs

| | Item | Effort | Status |
|---|---|---|---|
| 14 | Path B — soft-delete via `archived_at` | 1 session | scope-locked in start-here |
| 15 | Expired-asset Celery Beat sweep | ½ session | **NEW SESSION 209 — finding C** |
| 16 | **VO-arc — post-hoc voiceover insertion** | ~2 sessions (scope-lock + impl) | **NEW SESSION 209 — finding A2** |
| 17 | "Bake to local" preserve-before-expire | medium | **NEW SESSION 209 — finding C alt** |

### Path C — Composition arc candidates (after BC closes)

| | Arc | Effort | Notes |
|---|---|---|---|
| 18 | B-2 ↔ B-14 | ~½ regular arc | Script-grounded publish bundles |
| 19 | B-1 ↔ B-3 | ~½ regular arc | Transcript-mined → personalized batch |
| 20 | B-3 ↔ B-14 | ~½ regular arc | Per-recipient platform fan-out |

---

## Open questions for the operator

1. **BC5 ordering**: do we BC5 first as planned, or
   address one of the new findings (recipe gallery copy,
   expired-asset sweep, VO-arc scope-lock) before
   firing real-mode renders?
2. **Recipe gallery copy pass** (item 5): is this ½
   session you'd want before BC5? It directly affects
   discoverability for the ongoing dogfood pattern.
3. **VO-arc**: scope-lock doc as a next-session FIRST
   THING, or queue and prioritize after BC5 + a couple
   polish slices?
4. **Anything else the operator wanted to surface** —
   the prompt mentioned "there's a few things I want to
   address as well" — list outstanding.

---

## Out-of-session things to remember

* Asset upload UI unblocks Marcus rig re-bake + B-1 v2
  + transcript ingestion. Bottleneck for several v2
  slices.
* The 19 `expiring_soon` Assets will become expired
  within ~24h. If BC5 dogfood runs, the new
  `talking_head_polished` outputs will hit
  `expiring_soon` themselves in 12h.
* Celery worker doesn't auto-reload (3rd hit per
  calibration). The new pre-fire path now includes
  `apps/campaigns/views.py` + `signals.py` +
  `models.py` + `apps/compositions/starters.py`.
* `gpt-5` reasoning eats output budget (calibration).
  Auto-script slices use `gpt-5-mini` per memory.

---

# Pivot — second half of SESSION 209

Everything above this line describes the original
session shape. What follows describes the strategic
pivot that started mid-session.

## What changed

Operator decided to **start completely fresh** with a
new spokesperson representing the parent company
(24/7 Global AI). This obsoletes the original BC5
plan entirely and turns the next several sessions into
a different shape of work.

## What shipped (post-pivot)

### 6. New keeper spokesperson created

- **Name:** 24/7 Global AI (rename pending — operator
  considering "24/7 Donkey" placeholder)
- **ID:** `d3d0fb14-193e-4c4c-88d1-acae9af25bb5`
- **Runway avatar:** `f1e5cec2-...` (real-mode bake from
  `~/Desktop/24:7-Global-AI.png`, 1254×1254 PNG)
- **Voice preset:** `david` (Marcus's voice)
- **Workspace:** Admin's workspace
- **Portrait:** persisted locally at
  `_internal/avatar_portraits/f1e5cec2-...jpg`
- **First test render:** `talking_head` fired and
  completed in 33.9s at **$0.25** real-mode spend
  (deleted in the subsequent wipe — sunk cost).

### 7. Full data wipe

| Stage | Rows deleted |
|---|---|
| Failed/partial/draft compositions earlier in session | 13 + 45 steps |
| Orphan asset sweep (intermediate) | 20 |
| Expired asset sweep | 56 |
| **Full wipe** | 64 comps + 155 steps + 13 RT sessions + 324 spokespeople + 119 Assets + 74 misc (Videos, Conv*, Campaign, Script, Bundle, etc.) |
| **Session total** | **~700 rows + 328 MiB disk** |

Surviving content: 1 spokesperson (the keeper),
0 compositions, 0 RT sessions, 0 assets initially.

### 8. Tier 1 knowledge corpus seeded

7 KnowledgeDocuments seeded from the catalogue at
`/Users/donkeyking/development/24-7-ai-global/src/lib/products.ts`:

| KD ID | Title |
|---|---|
| `85da0660` | 24/7 Global AI — The Charter & Four Pillars |
| `37f146ac` | PitchDeckForge |
| `953c6060` | DealFlowTracker |
| `df8da613` | Contract Concierge |
| `2001b8c3` | MentorForge |
| `e417b347` | context-kit |
| `eada3f46` | Character OS |

All attached to keeper via M2M. 13 chunks embedded
total, **$0.00005 spend**. `ingested_via=seed`.
Idempotent via content_hash.

### 9. Tier 1 validation — RAG probes + real-mode render

Closed the "validate before building more" loop the
same session Tier 1 shipped. Three sub-steps:

**A. Stale KD sweep.** 16 leftover docs from earlier
SPA testing (test fixtures + Marcus's Nerva–Antonine
Wikipedia research) deleted before re-probing. Kept
the trafilatura research doc (general RAG knowledge).
Surviving corpus: 8 KDs (7 seeded + 1 trafilatura).

**B. RAG retrieval probes.** Seven probes across
brand-thesis / cross-product / per-product questions.
All seeded docs were retrieved correctly for their
domains:

| Probe | Top hit | Distance |
|---|---|---|
| Brand thesis | Charter | 0.30 |
| Cross-product PD↔DF | DealFlowTracker → PitchDeckForge | 0.37/0.40 |
| The Lab | Charter (Lab section) | 0.55 |
| Character OS realtime | Character OS doc | 0.59 |
| context-kit | context-kit | 0.35 |
| MentorForge | MentorForge | 0.34 |
| Operating cadence | Charter | 0.65 |

Trafilatura doc surfaced tangentially on probe 1
(distance 0.64, distant 3rd) — acceptable noise.

**C. Real-mode validation render.**

| Field | Value |
|---|---|
| Composition | `7722b3fc-...` |
| Script (120 chars) | "Decisions on autopilot. Judgment reserved for what only a human can do. That is the twenty-four seven operating thesis." |
| `use_knowledge` | True (K6 brief grounding) |
| Wall time | 75.0s |
| Cost | $0.25 |
| Status | completed, verified |
| Duration | **50.6s** (557-char synthesized brief) |

**Subjective:** operator approved — logo-as-avatar +
Marcus's `david` voice over 50s of brand-thesis
content rendered well.

**Two findings filed in TRUST_CALIBRATION:**

1. **`talking_head` chunk_ids propagation bug.**
   Chunks land on `final_asset.source_spec` but never
   aggregate to `Composition.knowledge_chunk_ids`.
   Asymmetric with `talking_head_polished`. SPA
   citation surfaces fail for single-step renders.
   Fix queued for SESSION 210 (~10-20 LOC).

2. **K6 brief replaces operator script.** 120-char
   input became 557-char rendered output (~6× longer
   than naive duration estimate). Operator-facing
   "Script" label misleads — should read "Topic" on
   grounded variants. SPA copy pass queued.

**"Real-mode finds bugs in every arc" pattern is
now 8-for-8.** Tier 1 validation surfaced two
findings on first fire.

## The corrected understanding of `/24-7-ai-global/`

**Not a doc consolidator** — it's the marketing
website itself (Next.js 16 + React 19 + Tailwind 4
+ Vercel). The second CC is cataloguing six finished/
near-finished projects as **products on the marketing
site**, not consolidating their docs.

The catalogue (`src/lib/products.ts`) is a structured
summary per product. It's now the seed corpus for the
keeper. Full doc walks of each project repo are
deferred (Tier 2).

## Brand language discovered

Major Character OS design pivot the start-here
hadn't anticipated:

| Token | Value |
|---|---|
| Palette | **ink** (#050a14), **gold** (#c9a961), cream/mist/fog, night/midnight/deep/steel |
| Fonts | Bodoni Moda · DM Sans · JetBrains Mono |
| Patterns | Editorial section numbering (`§ 01 — The Charter`), italic-display contrast, hairline gold dividers, orbit/sweep animations |
| Voice | "Plate 01 · The proprietor", "Pocket watch by appointment", "Reply · By morning", "The 24/7 Doctrine · 2026 Edition" |
| Stance | Agentic operating partner. Editorial luxury. NOT generic SaaS. |

Current `BRAND_IDENTITY_V2` is editorial-warm. New
direction is **editorial-dark-luxe**. That's a
re-skin arc, not a slice.

## What's dead vs queued vs new

**Dead** (deleted from data, references should be
purged from docs):

- BC5 dogfood (Marcus + Five Good Emperors gone)
- "Cast is example data" memory still applies in
  concept — but the named cast (Riggs/Sasha/Donny/Maya/
  Marcus) is gone.
- B-2 v2 polish slice (no scripts to polish against)
- Composition-detail verifier panel polish (no
  compositions to verify)
- Marcus rig re-bake (Marcus gone)

**Still queued** (unchanged by pivot):

- Asset upload UI
- Storage-health filter on Videos library
- Expired-asset Celery Beat sweep
- VO-arc (post-hoc voiceover insertion)
- F8.1 K10 seed corpus
- K7.x v3 YouTube oEmbed
- K6.4 v3 architectural fix
- W12 legacy form retirement

**New** (added this session):

- **Knowledge Ingest v1** — Tier 1 SHIPPED. Tier 2
  (deep per-project corpus walks of all 6 projects'
  `docs/` directories) ~1-2 sessions.
- **Brand Identity v3** — Character OS re-skin to
  match `/24-7-ai-global/` editorial-dark-luxe
  language. ~1-2 sessions.
- **Keeper profile** — operator-driven via SPA.
- **End-to-end keeper validation** — talk to the
  keeper via realtime or fire a content render with
  Tier 1 knowledge attached. ~½ session.
  Calibration test: does logo-as-avatar work? Does
  Marcus voice fit the brand? Is RAG retrieval
  hitting the right chunks?

## AI recommendation on next-session FIRST THING

**My vote: validate the keeper end-to-end first
(~½ session), then Tier 2 ingest.**

Reasoning:

- Tier 1 just shipped. The "real-mode finds bugs in
  every arc" pattern is 7-for-7 going in. We should
  test before building more.
- Cheap (~$0.10 for a realtime session or another
  talking_head with `use_knowledge=True`).
- Reveals what's actually broken: RAG retrieval
  quality on the seeded chunks, Marcus voice fit on
  the brand persona, logo-as-portrait behavior on
  longer scripts, brand-voice consistency.
- Sets up Tier 2's chunking strategy with real data
  (we'll know what kind of questions miss).

Brand v3 is meaty but doesn't block the keeper's
functionality. Can sit at SESSION 211+.

## When to retire this doc

At SESSION 209 close. Pull what's load-bearing into:
- `docs/handoffs/SESSION_209_*.md` (narrative)
- `00-START-NEXT-SESSION.md` (next session priorities)
- `docs/design/KNOWLEDGE_INGEST_V1.md` (when Tier 2
  scope-locks)
- `docs/design/BRAND_IDENTITY_V3.md` (when re-skin
  scope-locks)
Then delete this file.
