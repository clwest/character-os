---
title: "Content Format Backlog — gaps beyond the 18 starter recipes"
status: backlog
generated: 2026-05-19 (SESSION 184+ research pass)
parent_doc: "VIDEO_COMPOSITION_V1.md"
phase: 4
---

# Content Format Backlog

> **Read first:** `docs/design/VIDEO_COMPOSITION_V1.md` (the
> V-arc scope lock — 18 shipped recipes + 14 primitives),
> `docs/design/REALTIME_AVATAR_V1.md` (the R-arc — transcripts
> as Assets), and `docs/design/KNOWLEDGE_LAYER.md` (K-arc —
> retrieval surface). This doc references but does not modify
> any of them.

---

## Purpose

The V-arc scope-locked SESSION 142 at 18 starter recipes
selected for breadth across known video genres. After the
V-arc closed and operator dogfood ran (SESSION 158
real-Runway bake; SESSION 173-174 calibration; SESSION
181-184 V17 integration), a research pass against the
broader marketing/content-video genre space surfaced a
set of formats and pipelines that are **not covered by
the 18 recipes** and where **every primitive needed
already ships**.

This doc is a brainstorm anchor, not a scope lock. It
exists so a future session can pick any item, write a
proper scope-lock doc for it (in the style of
`VIDEO_COMPOSITION_V17_PROPOSAL.md`), and ship it as a
post-close slice.

**Scope:** content the platform could produce with its
existing data and primitives that it currently doesn't.
**Out of scope:** entirely new providers, entirely new
persistence layers, or anything that would require
violating the V-arc contract rules.

---

## What we already ship (anchor)

For grounding — the 18 starter recipes from the V-arc are:

* **V3** `talking_head`
* **V4** `cinematic_visual`
* **V5** `long_form_ad`
* **V7** `pip_layout`, `backdrop_layout`, `cohost_layout`,
  `broll_splice`, `music_bed_pass`
* **V8** `talking_head_with_backdrop`
* **V9** `talking_head_polished`, `reels_format`
* **V10** `voice_design`, `multi_lang_dub`
* **V11** `style_remix_pass`
* **V12** `recut_teaser`
* **V13** `storyboard_ad`
* **V14** `dialogue_scene`
* **V15.4** `storyboard_voiced`

And the 14 primitives (+ V16 post-close
`remove_avatar_background` = 15):

`generate_avatar_speech`, `generate_visual_clip`,
`split_script`, `concat_clips`, `composite_video`,
`mix_audio`, `add_captions`, `add_intro_outro`,
`trim_clip`, `reformat_clip`, `design_voice`,
`dub_audio`, `style_remix`, `transcribe`,
`generate_image`, `audio_extract`,
`remove_avatar_background`.

The R-arc additionally produces
`Asset(TRANSCRIPT)` per realtime session — a
data source the V-arc has never consumed.

---

## The backlog

Items are grouped by leverage given the existing
primitives and data. Each item lists the genre, the
operator value, the primitives it would compose, and
known risks/open questions.

### Tier 1 — high leverage, unique to this stack

These three exploit data or primitives nobody else
in the LLM-video market has the same way.

---

#### B-1. Realtime transcript → highlight clip miner

**Genre:** repurposed long-form → social clips.

**What it is:** R-arc lands `Asset(TRANSCRIPT)` for
every realtime session (R5; R6.1 widened the query so
mid-session transcripts also flow). Nothing currently
mines them. A recipe (LLM picks 3–5 punchy moments from
the transcript → re-renders each as a `talking_head` or
audiogram) turns every live conversation into multiple
shareable assets at near-zero marginal cost — the
realtime spend already happened.

**Primitives:** read `Asset(TRANSCRIPT)` →
gpt-5-mini segment selection → for each segment:
`generate_avatar_speech` (re-bake with the same avatar
+ voice) → `add_captions` → `reformat_clip` for the
target platform.

**Cost shape:** the avatar/voice re-bake is the same
cost as `talking_head`; gpt-5-mini segment selection is
~$0.001. ~$0.05–$0.10 per highlight clip if re-baked,
or $0 if rendered as audiogram only.

**Why it's high-leverage:** the LLM-video market is
crowded but nobody else has a per-workspace realtime
avatar producing transcripts they can mine. Unique
to this stack.

**Risks / open questions:**
* Does the operator want the re-baked clip
  (operator's avatar speaking the highlight, clean
  audio) or the original session audio (more
  authentic, voice may be noisy)?
* Highlight selection is an LLM judgement — needs
  approval UX so operator can veto bad picks.

---

#### B-2. Knowledge-driven auto-scripting (zero-typing) — **LOCKED → AUTO_SCRIPTING_V1.md (SESSION 206)**

**Genre:** removes the blank-page problem.

**What it is:** K-arc retrieves but the operator still
writes the script for every recipe. A recipe like
`auto_script_short` accepts a single prompt ("30s about
our new pricing") → K2 retrieves relevant chunks → LLM
drafts a script grounded in those chunks → renders as
`talking_head`. The operator approves the script before
the render fires (use the R7.0 approval-threshold
pattern).

**Primitives:** K2 retrieve (existing) → LLM draft
(new, but trivially a `responses.create` call) →
`generate_avatar_speech` + `concat_clips`.

**Cost shape:** ~$0.001 for the draft + standard
`talking_head` cost.

**Why it's high-leverage:** the "grounded in your
knowledge" UX is the most defensible product story
the platform has. Right now operators have to
manually write the script that uses that knowledge —
the friction defeats the differentiator.

**Risks / open questions:**
* Hallucination risk — must cite K2 chunk_ids in
  the draft so operator can audit.
* How long does the operator wait at the
  approval gate? Auto-renders feel magical but
  approve-then-render keeps trust.

---

#### B-3. Personalized variable-substitution videos

**Genre:** B2B sales / lifecycle email at scale.

**What it is:** one template ("Hi {firstName}, saw
{company} just {triggerEvent}…") + a CSV / contact list
→ N rendered videos, each personalized. Massive
revenue category in B2B (Vidyard, Loom, Tavus all
sell this) and the only one where per-workspace
avatars are structurally necessary — generic LLM
video can't do it.

**Primitives:** script template (new, but trivial)
+ batch dispatch of `talking_head` + per-recipient
asset naming.

**Cost shape:** N × `talking_head` cost. Tier-gate
hard (Agency only?) or per-render charge.

**Why it's high-leverage:** different SKU than one-off
videos. Sticky in a way one-off video isn't (CSV
integration, CRM webhook integration, recipient
analytics).

**Risks / open questions:**
* Need a CRM/CSV ingest UX, or accept
  copy-paste rows initially.
* Per-recipient cost cap — runaway batch could
  cost thousands. Tier the batch size.
* Privacy: recipient PII in the workspace.

---

### Tier 2 — format gaps in the 18 recipes

These are genres the 18 recipes don't address but
the primitives all exist for.

---

#### B-4. Audiogram / podcast clip

**Genre:** voice-only consumption (LinkedIn, X, Spotify
clips).

**What it is:** waveform animation + animated captions +
optional avatar in a corner + voice. Voice-only is a
huge content category and the 18 recipes never address
"no full-body video."

**Primitives:** `generate_avatar_speech` (voice only),
`add_captions`, `generate_image` (for static
background), `composite_video` (for waveform overlay).
Waveform rendering itself isn't a primitive — would
either need ffmpeg `showwaves` filter or a new
primitive.

**Risks / open questions:**
* Waveform — ffmpeg filter (cheap, ugly) vs custom
  renderer (better, work).

---

#### B-5. Kinetic typography / quote card video

**Genre:** text-driven, no avatar.

**What it is:** punchy quote or stat displayed as
animated text over a still or generated background,
optionally with voice. Top-of-funnel social hooks. The
"no avatar at all" genre is missing entirely from the
18 recipes.

**Primitives:** `generate_image` for background +
`composite_video` with text overlay (new — would need
either ffmpeg `drawtext` orchestration or a new
text-animation primitive) + optional `generate_avatar_speech`
voice-only.

**Risks / open questions:**
* Text animation quality — ffmpeg `drawtext` is
  ugly. Investigate Remotion, FFmpeg + ASS
  subtitles, or a JS-rendered overlay.

---

#### B-6. Tutorial with numbered step overlay

**Genre:** how-to / educational. Largest content
category on YouTube.

**What it is:** avatar narrates steps; numbered step
cards appear as overlays; optionally a screen recording
plays in a PIP. The 18 recipes have `pip_layout` but no
step-overlay or screen-capture ingest.

**Primitives:** `pip_layout` (existing) + step-overlay
composite (new) + screen-recording ingest (new — accept
operator-uploaded `.mp4`).

**Risks / open questions:**
* Does the operator upload the screen recording, or
  do we attempt to record from a browser session?
  v1 = uploaded.

---

#### B-7. Reaction / commentary overlay

**Genre:** UGC commentary, news reaction, competitor
ad teardown.

**What it is:** avatar in a corner reacting to an
embedded clip that takes the main frame. Different
from `pip_layout` (which puts the avatar in the main
frame).

**Primitives:** `composite_video` with avatar
PIP in a corner + uploaded source clip in main frame +
`generate_avatar_speech` over the muted source audio.

**Risks / open questions:**
* Copyright posture — operator-uploaded only, no
  scraping. Make explicit in UI.

---

#### B-8. Data / chart overlay on avatar

**Genre:** finance, analytics, SaaS metrics videos.

**What it is:** avatar narrates while animated chart
cards appear beside them. Niche but high-value for
vertical operators (finance creators, SaaS founders
posting metrics, analysts).

**Primitives:** `composite_video` + chart rendering
(new — Plotly / Chart.js → PNG → animate-in).

**Risks / open questions:**
* Data input — CSV upload or JSON paste? v1 = paste.

---

#### B-9. Lower-thirds + citation graphics

**Genre:** newscaster credibility cues.

**What it is:** name tags ("Riggs, Co-host"),
on-screen citations ("Source: <K-arc chunk>"), call-out
boxes. Not in any of the 18 recipes — and citations
specifically would massively reinforce the K-arc
grounding story.

**Primitives:** `composite_video` with text-overlay
layer (new — same gap as B-5).

**Risks / open questions:**
* Auto-cite from `knowledge_chunk_ids` (the R4
  bridge already plumbs these for realtime; same
  pattern for video would be straightforward).

---

#### B-10. Multi-shot single-avatar cuts

**Genre:** high-energy YouTube editing style
(MrBeast-cadence cuts).

**What it is:** the avatar reads one script but the
camera "cuts" between zooms/angles every 2–4 seconds,
synthesizing the high-energy editing pace social
viewers expect. `broll_splice` does cuts but with
B-roll inserts; this is cuts of the avatar itself.

**Primitives:** `generate_avatar_speech` (one bake) +
multiple `reformat_clip` calls at different
crops/zooms + `concat_clips` with cut timing driven
by an LLM "cut points" call.

**Risks / open questions:**
* Real motion would require multiple bakes from
  different camera angles — expensive. v1 fakes
  it with crop/zoom on a single bake.

---

### Tier 3 — audio / soundtrack gaps

---

#### B-11. Generative music (not music_bed_pass reuse)

**What it is:** `music_bed_pass` reuses existing audio
files. A generative-music primitive (Suno, Udio,
ElevenLabs Music API) would let recipes produce
custom soundtracks per clip.

**Primitives:** new `generate_music` primitive.

---

#### B-12. SFX / Foley

**What it is:** whooshes, stings, ambient layers.
Lifts perceived production quality enormously and
none of the 18 recipes touch it.

**Primitives:** new `generate_sfx` primitive
(ElevenLabs Sound Effects API), or curated SFX
library + `mix_audio`.

---

#### B-13. Operator's own voice clone

**What it is:** `design_voice` builds designed
personas (V10). A different flow — operator records
3–5 minutes of their own voice, the platform clones
it, and any spokesperson can speak in the operator's
voice. Strong personalization story; different
trust/consent surface (must be the operator's voice,
not a third party's).

**Primitives:** ElevenLabs Instant Voice Cloning API
+ consent capture UX.

**Risks / open questions:**
* Consent is non-trivial — explicit on-record
  agreement; voice fingerprint verification.

---

### Tier 4 — distribution / output gaps

---

#### B-14. One render → many platform variants

**What it is:** same source video clipped/reformatted
to Reels 60s, Shorts 60s, TikTok 90s, X 2:20,
LinkedIn 30s, with platform-appropriate captions /
safe zones. Currently `reformat_clip` exists but
isn't orchestrated as a single "publish bundle"
operation.

**Primitives:** existing `reformat_clip` +
`trim_clip` + `add_captions` wrapped in a publish
recipe.

**Cost shape:** all ffmpeg, ~$0 incremental per
variant.

---

#### B-15. Auto thumbnails + titles + descriptions

**What it is:** every render also produces a
thumbnail (gen4_image of a reaction shot or extracted
frame), 3 title variants, and a description.
Thumbnails drive CTR more than the video itself —
this is one of the highest-leverage post-render
additions possible.

**Primitives:** ffmpeg frame extraction OR
`generate_image` + gpt-5-mini for titles/descriptions.

---

#### B-16. Subtitle-only multi-language

**What it is:** `multi_lang_dub` re-voices into N
languages — expensive. A cheaper variant burns
translated subtitles without re-dubbing the audio.
Covers the 80% of "international reach" cases at 10%
of the cost.

**Primitives:** existing `transcribe` + LLM
translation + `add_captions`.

---

### Tier 5 — strategic / structural gaps

---

#### B-17. Trend-responsive auto-content

**What it is:** RSS / news feed / X-trends ingest →
"react in your voice" recipe. Content engines that
ride trends massively outperform evergreen.

**Primitives:** external feed ingest (new) + B-2's
auto-scripting + `talking_head`.

**Risks / open questions:**
* Latency target — trends decay in hours. Needs
  a fast lane (operator approves, fires
  immediately) vs the normal approval flow.

---

#### B-18. A/B variant render

**What it is:** same script rendered through two
recipes (e.g. `talking_head` vs `cinematic_visual`),
tagged as a pair, operator picks the winner.
Calibration loop for the platform.

**Primitives:** existing recipes + new
`composition_pair` metadata on Composition rows.

---

#### B-19. Episodic / serialized memory for video

**What it is:** Episode 7 references Episode 6's hook.
R6/R6.1 has cross-session memory for realtime;
nothing equivalent exists for the video-composition
arc. A "series" container would let an operator
build serialized content (podcast episodes, course
modules) that remembers prior episodes.

**Primitives:** new `Series` model (or repurpose
workspace fabric metadata) + cross-episode prompt
context.

---

#### B-20. Course-in-a-box / series generator

**What it is:** one knowledge corpus → a 10-video
sequence with consistent hook/CTA structure (intro,
8 lessons, recap). Different SKU than one-off
videos.

**Primitives:** B-2 (auto-scripting) × N + B-19
(series memory) + tier-gate (Pro/Agency).

---

## Strategic recommendation

If only three of these were ever built, prioritize:

1. **B-1 — Realtime transcript clip miner.** Unique
   to this stack. The data is being thrown away.
2. **B-3 — Personalized variable-substitution
   videos.** Largest single revenue unlock; only
   format where per-workspace avatars are
   structurally necessary.
3. **B-14 — One render → many platform variants.**
   Every customer ships to ≥3 platforms; right now
   they reformat manually. Owning publish-bundle is
   sticky.

B-2 (auto-scripting) is a close fourth — it is the
single biggest reduction in "blank page" friction
and reinforces the K-arc grounding story more than
any other slice could.

---

## How to use this doc

This is a **backlog**, not a scope lock. To pick up
any item:

1. Read the item + linked anchor docs
   (`VIDEO_COMPOSITION_V1.md`, the relevant arc
   scope lock).
2. Write a proper proposal in the style of
   `VIDEO_COMPOSITION_V17_PROPOSAL.md` — purpose,
   the capability description, contract-rule
   alignment, sub-slice breakdown if needed, open
   questions.
3. Lock the proposal with operator sign-off
   following the V-arc lock pattern.
4. Update this backlog by marking the item
   `LOCKED → <slice id>` so the backlog stays
   honest about what has graduated.

---

## Change log

* 2026-05-19 (SESSION 184+) — initial brainstorm
  doc; 20 items captured across 5 tiers; no items
  locked yet.
