---
title: "Session 193 — Asset Library v1 dogfood pass + Celery hard-rule calibration"
date: 2026-05-19
status: complete
session: 193
previous_handoff: ./SESSION_192_A8_ARC_CLOSE.md
arc_validation: ASSET_LIBRARY_V1
---

# Session 193 — A-arc dogfood + Celery hard-rule promotion

## TL;DR

**No code changes this session.** Real-mode dogfood pass
validated Asset Library v1 end-to-end against the dev DB.
Operator browsed (A5), drilled into detail (A6 via row links),
exercised the role-filtered picker (A7 narrowed 119 CLIPs →
42 BACKDROP), and fired a `talking_head_with_backdrop`
composition that completed with the A8 produced_assets panel
rendering exactly as designed.

**One real calibration catch**: the SESSION 192 stack-up
notes claimed mock-mode doesn't need Celery. Wrong — the
composition hung silent at DRAFT for 104s with 65 messages
backed up in the Redis queue. **Promoting the SESSION 184
#5 calibration to a hard stack-up rule** at the SESSION 194
start-here.

Two new TRUST_CALIBRATION entries.

## Dogfood walkthrough

### Step 1 — Browse (A5) ✓

Pre-flight DB state confirmed 136 assets in `Admin's workspace`
across 9 role buckets (49 talking_head + 42 backdrop + 15
composite_output + 11 polish_output + 8 raw_upload legacy + 4
transcript + 3 reference_image + 2 experiment + 2 audio_track).

Operator reaction: *"I didn't know we had hundreds lol"* —
the inventory was completely invisible pre-A0 (lived in the
Asset table without role tags, no SPA surface). **First
operator-visible payoff of the arc — the table-of-contents
moment that motivated A0 ships through to A5.**

### Step 2 — Detail (A6) ✓ (implicit via row links)

Operator skipped clicking individual rows but A8's produced
asset rows wire into the same `/workspace/assets/<id>` route
that A6 ships. Verified by row → link consistency at the
composition page (step 4).

### Step 3 — Role-filtered picker (A7) ✓

Operator opened the V18 `talking_head_with_backdrop` recipe
form. Initial reaction: *"the pre-recorded one still looks
like its listing almost everything"* — followed by
*"Wait its probably 42"*. **It was exactly 42** — A7
narrowing 119 total CLIPs down to the BACKDROP-tagged subset.
Validated.

Calibration moment: **A7's narrowing is mathematically
correct but visually still a long dropdown** because the
workspace has accumulated 42 BACKDROPs over the V-arc
real-mode validation runs. The role filter works; the
operator's perception flipped after counting.

### Step 4 — Fire composition + A8 (the dogfood catch)

Operator submitted `Avatar over backdrop — Talking about
random shit` (talking_head_with_backdrop, mock_mode=true)
with a picked backdrop_clip from the dropdown. **Composition
sat at DRAFT for 104s** with both steps `pending`, no error
message, no Celery worker in `ps`.

Diagnostic check from AI tail:

```
Status: draft (104.7s age)
Error: ''
Produced assets: 0
  step 0: generate_avatar_speech status=pending elapsed_ms=None
  step 1: composite_video status=pending elapsed_ms=None
Redis celery queue depth: 65 (backed up envelopes)
ps aux | grep celery → no worker
```

**Diagnosis: SESSION 184 calibration #5 "Celery worker
stop-state is silent" hit for the second time** — and the
SESSION 192 start-here `stack-up notes` were structurally
wrong in claiming mock-mode is "Celery-free."

#### Resolution

Started Celery worker in background:

```bash
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Within 8 seconds:
- Composition advanced `draft` → `completed`
- Step 0 (`generate_avatar_speech`): succeeded, elapsed_ms=3
- Step 1 (`composite_video`): succeeded, elapsed_ms=2
- 2 produced assets attached
- Redis queue depth: 65 → 0 (drained 64 stale envelopes from
  prior sessions + the 1 live task)
- Workspace asset count: 136 → 138 (+2 from the new composition)

#### A8 rendering verified

Operator refreshed `/compositions/26e783a4-…` and shared a
screenshot. The page shows everything as designed:

* **STATUS: COMPLETED** badge
* **DERIVED FROM** panel (F5 lineage from SESSION 144) —
  "Sunset coastline (calm, easy mode)" PARTIAL — the picked
  backdrop's source composition
* **Steps** — `#1 generate_avatar_speech clip 5.0s` +
  `#2 composite_video clip 7.5s` both green
* **FINAL OUTPUT** — `mock://compositions/3e23b43c0f98-composite-backdrop.mp4`
* **PRODUCED 2 ASSETS** panel (A8):
  * Row 1: `step 1/2 (generate_avatar_speech)` — `CLIP` +
    `TALKING HEAD` + `UPLOAD PENDING`, no Final pill
  * Row 2: `step 2/2 (composite_video)` — `CLIP` +
    `COMPOSITE OUTPUT` + `UPLOAD PENDING`, **`FINAL` pill**

Asset Library v1 end-to-end working in real-mode against
the dev DB.

#### Minor mock-mode quirk (not a bug)

Both produced assets show `UPLOAD PENDING` storage health
in mock-mode because `mock://` URLs don't match any A3
classifier branch (HTTPS / local / data) and fall through
to `UPLOAD_PENDING`. In real-mode renders these would show
`HTTPS_LIVE` (green). Worth noting in start-here for
future mock-mode dogfooders so they don't chase it as a
bug.

## Calibration moments worth carrying

Two new TRUST_CALIBRATION entries appended:

1. **Celery worker is NOT optional for mock_mode — promote
   to hard stack-up rule.** Mock_mode controls primitive
   behavior (skips Runway/Stability API calls); it does
   NOT bypass the Celery task wrapper. Any session that
   fires compositions — mock_mode or real-mode — requires
   a running Celery worker. The `celery worker` line moves
   from "optional helper" to "required step" in the
   start-here stack-up checklist. SESSION 192's
   "Celery-free" wording was wrong and is scrubbed at
   SESSION 193 close.

2. **Arc-close dogfood is high-yield even after every slice
   was test-validated.** Asset Library v1 closed with 134
   SPA vitest + 995 Django pytest tests passing — full
   automated coverage. The dogfood pass still caught a real
   start-up error within 2 minutes. Tests use
   `CELERY_TASK_ALWAYS_EAGER=True` and bypass the broker;
   the "is the dev stack usable" question is structurally
   outside the test surface. **Generalizes: test passing
   ≠ dev stack usable.** Same shape as SESSION 173's
   real-mode-dogfood calibration but for local-dev drift
   instead of provider drift.

## State at session close

* **Django dev server** still running (PID 74864, started
  before this session by operator).
* **SPA dev server** still running (PID 62796, ditto).
* **Celery worker** started by AI in background during this
  session — still running. Will keep consuming the queue.
  If the operator wants to stop it cleanly, find the PID
  via `ps aux | grep "celery.*worker"` and `kill <PID>`.
  Otherwise it'll sit idle (empty queue) until manually
  stopped or the machine reboots.
* **No real-mode spend** — mock_mode throughout.
* **Workspace inventory grew**: 136 → 138 assets (+2 from
  the dogfood composition).

## Tests at session close

No code changes; suites unchanged from SESSION 192:

| Suite | Count |
|---|---|
| Django | 995 |
| - compositions | 564 |
| Media-engine | 194 |
| SPA vitest | 134 |

## Operational notes for SESSION 194

### Hard stack-up rule changes

* **Celery worker is required for ANY composition fire.**
  Mock_mode does not change this. The start-here stack-up
  block at SESSION 194 boot lists it as a required step,
  not optional.
* **Workers exit silently when killed.** No reconnect
  banner, no error log, the composition just sits at DRAFT
  with `error_message=''`. If you submit a composition
  and the status doesn't advance within 5 seconds in
  mock-mode, check `ps aux | grep celery` first.
* **The Redis broker accumulates stale envelopes across
  sessions.** Pre-dogfood the queue had 65 backed-up
  messages. The worker drains them on boot but logs
  warnings/errors for terminated-composition envelopes
  (harmless; no-op semantics). If queue depth gets
  uncomfortable, `redis-cli -p 6381 -n 0 del celery`
  drops the lot — but only do this when no live work is
  pending.

### Next session opens with operator picking direction

No arc in flight. Same options as SESSION 192 close-out:

* **Real-mode validation** for the 2 unvalidated V-arc
  recipes (`storyboard_voiced` + `dialogue_scene`).
* **V18 polish slice** (duration-mismatch starter warning).
* **F8.1 K10 seed corpus** (blocked on operator-authored
  markdown).
* **New-arc candidates from `CONTENT_FORMAT_BACKLOG.md`**:
  B-1 (transcript miner — closest to shipped infra), B-3
  (personalized variable-substitution video), B-14
  (multi-platform variants).
* **Backlog items**: V17.3 keyframes re-open criteria,
  B6-B10 brand arc, K7.x v3 YouTube oEmbed, K6.4 v3, asset
  upload UI, smoke `--save-assets` opt-in, W12 legacy form
  retirement, Thruman cleanup.
