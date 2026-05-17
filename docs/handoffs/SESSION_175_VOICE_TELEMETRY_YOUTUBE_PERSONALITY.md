---
title: "Session 175 — voice telemetry follow-up, YouTube extractor, personality split"
date: 2026-05-17
status: complete
session: 175
previous_handoff: ./SESSION_174_OPERATOR_FACING_POLISH.md
---

# Session 175 — voice telemetry follow-up + YouTube extractor + personality split

## TL;DR

Five feature commits. Two natural dogfood-driven fixes
following from SESSION 174's voice-telemetry slice. One full
arc-close on the K7.x YouTube ingest backlog item. One
operator-insight slice — the personality / business_brief
split.

* **W11.x.1** (`edff9f2`) — voice swap success/skipped banners
  now stay visible. SESSION 174's auto-close-on-success
  unmounted the banner in the same React tick the state was
  set; operators saw nothing.
* **K6.4 v2.2** (`1577ce4`) — sentence-opener stoplist
  expansion. Donny K6 dogfood ("Walk me through what makes
  Wikipedia such a strong source…") returned a clean brief
  with one false-positive `"Respect HTML"` — same shape as
  v2.1's "Think Antoninus" case, just missing `respect` from
  the CTA-verb set.
* **K7.x v2** (`6f9d5b4`) — proper YouTube transcript
  extractor. Replaces v1's up-front rejection (SESSION 174)
  with actual ingestion via `youtube-transcript-api`.
  YouTube URLs are now ingestable, not just deflectable.
* **W11.x.2** (`0b56bd9`) — voice preview surface in the
  wizard. Runway's `clone-voice` returns a hosted preview
  URL we were throwing away; now plays inline in the
  wizard's final step so operators hear the cloned voice
  before committing.
* **W11.y** (`47f5166`) — personality / business_brief split.
  Operator insight: "they should be treated differently —
  not every personality matches the same business brief."
  Splits HOW (personality) from WHAT (business_brief)
  across the entire stack: model + K6 prompt + K6.5 prompt
  + Runway avatar create + R-arc realtime document + wizard
  + edit modal. Backfill preserves existing K6 output.

Plus the SESSION 174 close commit (`462a3d2`) carried over.

**Tests**: Django **782 → 814** (+32). Media-engine **133**
unchanged. SPA vitest **91 → 95** (+4). Migrations **54 →
55**.

**Real-mode spend this session**: ~$0.06 OpenAI (K6.6
multi-cast dogfood across Donny + Maya). $0 Runway / $0
Stability — all SESSION 175 slices were dogfood-validated
via shell scripts or unit tests; W11.x.1 banner fix was
operator-visual; W11.y to-be-dogfooded post-session by the
operator splitting Marcus's content.

## What shipped — commit by commit

### `462a3d2` — SESSION 174 close (carried)

Already documented in `SESSION_174_OPERATOR_FACING_POLISH.md`.
Anchor restamps + 4 TRUST_CALIBRATION + handoff. Doctor
green.

### `edff9f2` — W11.x.1 voice swap never auto-closes

Operator drove the voice swap dogfood (#2 from the
SESSION 174 close menu). DB confirmed the swap landed
(Marcus → vincent, Sasha → felix). Operator reported "I
switched to Vincent's voice and saved it but I didn't see
anything to verify it's saved." The W11.x banner code from
SESSION 174 fired correctly — `setVoicePatch` then
immediately `onClose()` in the same handler tick, so the
banner rendered for ~10ms and unmounted before the human
eye could register it.

* `web/src/components/spokesperson-edit-modal.tsx` —
  removed auto-close on voice change. Modal stays open for
  ALL voice-patch outcomes (ok / skipped / failed).
  Operator clicks Close themselves after seeing the
  banner. Persona-only edits (no voice change) still
  auto-close because they carry no telemetry to surface.
* Cancel button relabels to "Close" for any set
  `voicePatch` (was: only on `failed`).
* 3 tests updated to assert stay-open on ok/skipped; 1
  pre-W11.x.1 test updated from "auto-closes after voice
  change" to "stays open after voice change".

**Calibration moment carried forward** (in TRUST_CALIBRATION
appended this session): vitest assertions that fire
atomically pass for behavior that's invisible in real
time. When render → unmount runs in a single React tick,
jsdom asserts both ends true; the human eye sees only the
second. Pattern to watch: any test that asserts both "X
exists" AND "onClose called" without a timing gate.

### `1577ce4` — K6.4 v2.2 sentence-opener stoplist expansion

SESSION 175 K6.6 multi-cast dogfood (#4 from the menu):

* **Marcus** (Nerva-Antonine doc) — clean brief, zero
  warnings (validates SESSION 174's v2.1 fix).
* **Donny** (trafilatura doc) — clean brief, one
  false-positive `"Respect HTML"` flagged.
* **Maya** (no knowledge) — `trusted_passthrough`
  (degraded path correct).
* **Maya + trafilatura attached** — clean brief, zero
  warnings.

Pattern: every K6 dogfood since v2 (SESSION 166) has
surfaced 1-2 new sentence-opener gaps the stoplist needed
to cover. `respect` slipped through v2.1's CTA-verb sweep.

Added to stoplist: respect / protect / prepare / maintain
/ include / ensure / verify / verified / focus / avoid /
prioritize / prefer / proceed / treat / handle / choose /
pick (full conjugations). One new parametrized test
covers 10 verb+entity pairs.

**Calibration moment**: K6.4 v3 (architectural fix —
generalize sentence-position-aware imperative-verb
detection beyond stoplist curation) sits queued. The
curation pattern remains cheap (1-line + small test) but
the trickle suggests v3 would amortize. Worth scoping
when operators ship more verb-heavy K6 prose.

### `6f9d5b4` — K7.x v2 YouTube transcript extractor

Replaces v1's up-front rejection (SESSION 174's
`e4d5761`) with actual ingestion. `youtube-transcript-api`
was already installed in pyenv global but not in the
project venv — installed + declared in pyproject.toml
this slice.

* `shell/apps/embeddings/youtube_extractor.py` — NEW.
  `_extract_video_id` parses every reasonable YouTube URL
  shape (watch?v= / youtu.be / embed / shorts / live / v
  / music.youtube.com / youtube-nocookie.com) with a tight
  11-char regex + host allow-list defense.
  `_clean_transcript_text` joins snippets, collapses
  whitespace, drops pure music / applause / inaudible
  markers (`[♪♪♪]`, `[Music]`, `(Applause)`).
  `extract_youtube_transcript` orchestrates: video_id →
  YouTubeTranscriptApi.fetch → cleanup → ExtractedUrl.
  Operator-actionable errors for every documented
  failure mode (TranscriptsDisabled / NoTranscriptFound /
  VideoUnavailable / VideoUnplayable / AgeRestricted /
  IpBlocked / RequestBlocked / PoTokenRequired /
  CouldNotRetrieveTranscript / empty transcript /
  too-short after cleanup).
* `shell/apps/embeddings/url_fetch.py` — fetch_url
  routes YouTube URLs to the new extractor instead of
  rejecting. The host-detection helper (`_is_youtube_url`)
  from v1 stays as the routing gate.
* 29 new extractor tests + 3 updated url_fetch tests.

Real-mode dogfood: 2,083 chars extracted from
`https://www.youtube.com/watch?v=dQw4w9WgXcQ`, 61
snippets, music markers correctly dropped, ~$0 cost.

K7.x v3 queued: YouTube oEmbed call alongside transcript
fetch to populate the doc title with the real video title
instead of the v2 placeholder `"YouTube · {video_id}"`.

### `0b56bd9` — W11.x.2 voice preview surface in wizard

The SESSION 174 inventory question ("what does Runway
return that we ignore?") surfaced the unsurfaced
`preview_url` from clone-voice. Operators had to commit
a spokesperson + render a $0.25-0.50 talking-head to
hear what their voice clone actually sounded like.

* `web/src/components/spokesperson-wizard.tsx` — new
  `clonedPreview` state captures `voice_id` + `preview_url`
  on successful clone. Wizard skips auto-navigate +
  renders a new `VoicePreviewPanel` in place of
  Step4Confirm. Operator hears the cloned voice via inline
  `<audio controls>` + clicks "Continue to detail page"
  to navigate. Mock-mode clones (preview_url=null) +
  clone failures fall through to original immediate-nav.
* `VoicePreviewPanel` exported for testability. 4 tests
  cover audio src binding, voice_id reference label,
  onContinue callback, fallback link for browsers
  without audio support.

Preset voice previews + detail-page "test voice" button
queued — both would close the same anxiety loop for
preset-mode operators + post-create operators.

### `47f5166` — W11.y personality / business_brief split

Operator insight that crystallised during the SESSION 175
"what does the Runway API actually return?" inventory
discussion: a Spokesperson has two independently-swappable
attributes that the pre-split `business_brief` field jammed
together.

* `business_brief` is **WHAT** the business does (facts,
  product, audience, pricing). The K6 prompt now treats
  this as authoritative factual context alongside
  knowledge chunks; the model is encouraged to paraphrase.
* `personality` is **HOW** the spokesperson speaks (voice,
  character, mannerisms). The K6 prompt fences this as
  tone-only with the K6.6.1 anti-recitation guard. Runway
  avatar create + realtime document map their
  `personality` field to this.

Why it matters: operators can now compose "Sasha's
personality" + "AcmeCorp's business_brief" to clone a
sales rep for a new business without re-writing the voice
description.

* `shell/apps/spokespeople/models.py` — new
  `personality` TextField. business_brief help_text rewritten
  to clarify it now holds facts only.
* `shell/apps/spokespeople/migrations/0005_w11_y_personality_split.py`
  — additive + RunPython backfill (Option B): copy
  business_brief → personality for every existing row so
  K6 + Runway produce identical output until the operator
  splits content per-spokesperson.
* `shell/apps/spokespeople/serializers.py` — exposes
  personality.
* `shell/apps/spokespeople/views.py` — rebake_avatar
  sends personality (not business_brief) to Runway.
* `shell/character_os/script_synthesis.py` —
  `_system_prompt` restructure. Personality is the TONE
  fence; business_brief is the new FACT fence
  ("paraphrase as needed; treat as authoritative
  alongside the knowledge chunks"). Anti-recitation rule
  narrows from "recite your background" to "recite the
  speaker voice + character block".
* `shell/character_os/conversation_synthesis.py` — same
  split for K6.5 conversation replies.
* `shell/character_os/realtime_document.py` — Runway
  realtime session document gains "## Voice" section
  (personality) before "## About" (business_brief).
  Retrieval query stays business_brief-anchored
  (facts make better retrieval queries than voice
  descriptions).
* `shell/character_os/claim_verifier.py` — `build_corpus`
  allow-lists both fields.
* `web/src/components/spokesperson-wizard.tsx` — Step 1
  gains a Personality textarea. Step 4 review surfaces
  the new field.
* `web/src/components/spokesperson-edit-modal.tsx` —
  Personality field with WHAT/HOW labels for
  disambiguation.

Backfill verified against `Admin's workspace`: all 5
cast spokespeople have personality populated identically
to their business_brief. K6 + Runway produce the same
output as pre-W11.y until the operator splits.

Operator dogfood post-session:
1. Edit Marcus's modal → Personality auto-populated.
2. Split: drop facts from personality, drop voice from
   business_brief.
3. Re-fire K6 against Marcus to verify the new tone +
   fact balance.

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended this session:

1. **Vitest atomic assertions mask render → unmount flashes.**
   When a component's state-update + parent-callback fire
   in the same React tick, jsdom asserts both sides true
   even though the human eye sees only the final state.
   The W11.x voice telemetry slice's success banner
   technically rendered + the test passed — but operators
   saw nothing because onClose unmounted the banner before
   the next paint. Pattern: any test that asserts both
   "X exists in document" AND "onClose called" without a
   timing gate between them is suspect for visible-UX
   regressions.

2. **Browser-cache verification during real-mode dogfood.**
   Operator reported "Voice applied" text appearing in the
   modal — grep across SPA source returned zero matches.
   Root cause: stale browser bundle showing pre-W11.x.1
   code. The operator's `:8000` (Django serving `dist/`)
   was up-to-date because pnpm build had rebuilt; the
   browser tab held an older bundle in memory. Pattern:
   when source greps don't match operator-reported UI
   text, suspect stale browser before suspecting the code.
   Hard refresh (Cmd+Shift+R) is the first move.

3. **K6.4 stoplist curation has a trickle that suggests v3.**
   Every K6 dogfood since v2 (SESSION 166) — operator
   thread + Marcus + Sasha + Donny + Maya — has surfaced
   1-2 new sentence-opener verb gaps. v2 added 30+ verbs;
   v2.1 added 11 more (time adverbs + prepositions +
   think); v2.2 added 17 more this session. The
   curation pattern stays cheap (~1-line + small test per
   addition) but the trickle suggests v3 (architectural
   fix — sentence-position-aware imperative-verb
   detection beyond stoplist curation) would amortize the
   ongoing maintenance. Scope when operator ships more
   verb-heavy K6 prose.

## Cast roster + workspace state

Cast unchanged (Riggs / Sasha / Donny / Maya / Marcus). 5
voice swaps fired this session (operator-driven dogfood),
all landed in DB. Current voice_id values:

* Riggs: `vincent` (default)
* Sasha: `felix` (operator-swapped during W11.x.1 dogfood)
* Donny: `vincent` (operator-swapped during W11.x.1 dogfood)
* Maya: `victoria`
* Marcus: `david` (operator-swapped during W11.x.1 dogfood)

Knowledge corpus updated this session: Maya gained the
trafilatura test doc as a temporary attachment for K6.6
multi-cast dogfood. **Operator may want to detach** if
Maya's intended use case doesn't include trafilatura
content. (`spokesperson.knowledge_documents.remove(doc)`
via shell or detach button in SPA.)

All 5 cast spokespeople have `personality` populated
identically to `business_brief` post-W11.y backfill.
Operator splits per-spokesperson over time by editing.

## Final state — tests + routes

* **Django**: **814** (782 → 814, +32 across 5 slices)
* **Media-engine**: **133** (unchanged)
* **SPA vitest**: **95** (91 → 95, +4 for VoicePreviewPanel)
* **Migrations**: **55** (54 → 55; W11.y's personality field)
* **Real-mode spend**: ~$0.06 OpenAI total this session
  (3 gpt-5 K6 brief synthesis calls for Donny + Maya
  dogfood). $0 Runway / $0 Stability.

## Operational notes carried forward

1. **Celery worker restart REQUIRED for model-extending
   sessions.** W11.y restarted the worker (pid 74011) when
   the `personality` field landed. SESSION 174 calibration
   reinforced again this session.
2. **SPA gates need both `pnpm test` AND `pnpm build`** —
   reinforced when the W11.y `personality` field broke the
   `spokesperson-edit-modal.test.tsx` fixture typing. Caught
   at build, not test.
3. **Real-mode dogfood after operator-facing slices** —
   pattern carried forward from SESSION 174 memory entry.
   W11.x.1 + K6.4 v2.2 both surfaced from operator dogfood
   that unit tests couldn't catch.
4. **Browser-cache verification** — new pattern from this
   session. When operator-reported UI text doesn't exist
   in source, hard-refresh first.

## FIRST THING (SESSION 176): pick by mood

1. **W11.y operator dogfood** — edit Marcus's modal, split
   his backfilled personality from business_brief, re-fire
   K6 to verify the new tone + fact balance. ~10 min,
   ~$0.05 OpenAI for the brief re-fire. **High-value
   first move** because it validates the W11.y split
   against real operator content.
2. **Voice preview dogfood** — W11.x.2 ships but operator
   hasn't yet driven a clone-voice through it to see the
   preview panel. Requires upload/record path (not preset).
   ~$0.05.
3. **Cost panel polish** — credit ↔ dollar mode toggle for
   Stability, per-day chart, per-recipe breakdown.
   ~1 session.
4. **K6.4 v3 architectural fix** — generalize sentence-
   position-aware imperative-verb detection beyond
   stoplist curation. ~1 session. Amortizes the trickle.
5. **K7.x v3 — YouTube oEmbed** — populate the doc title
   with the real YouTube video title instead of the v2
   `"YouTube · {video_id}"` placeholder. ~30 min.
6. **Multi-step composition title disambiguation** —
   v1 leaves the same title across all step outputs in a
   long_form_ad / storyboard_voiced composition. ~30 min.
7. **F8.1 — K10 seed corpus** — still blocked on
   operator-authored markdown.
8. **TRANSCRIPT + VOICE asset titles** — verify the
   W11.6.5.3 runtime change covers all asset types.
   ~15 min.

Operator preference: pick at session start.

## Stack-up boilerplate

```bash
cd infra && docker compose up -d

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 176 stack-up note**: Celery worker was restarted
once this session (W11.y model change, pid 74011). Fresh
worker holds the W11.y runtime. If SESSION 176 touches
`apps/spokespeople/` models OR
`apps/compositions/{models,tasks,primitives}/`, restart
again. SESSION 174's broader rule still applies:
**ANY model-extending session needs a worker restart**.

**Smoke checks**:

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 814 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```
