---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`
> (locked SESSION 178 — 10 contract rules, B0-B10 slice
> breakdown). **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`
> (locked SESSION 178 — supersedes V1). Premium enterprise
> dark + gold; Geist + JetBrains Mono.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — **13 contract rules** total: V1's 9 + V17's
> 4 merged as rules 10-13; V0-V15 + V16 slice breakdown).
> **V16 POST-CLOSE SHIPPED (SESSION 179) — remove_avatar_background.**
> **V17 LOCKED (SESSION 182) — extend + keyframes.**
> V17.0 + V17.1 SHIPPED SESSION 182. V17.2 (cinematic_visual_extended
> recipe) is next.
> See `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE + REAL-MODE HARDENED
> (SESSION 176).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5.1-3 COMPLETE.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_182_V17_SCOPE_LOCK_PLUS_V17_0_AND_V17_1.md`.

---

## SESSION 182 outcome — V17 scope-lock + V17.0 + V17.1

Two feature commits. V17 went from `status: proposed` to
`status: locked`; four contract rules merged into V1 as rules
10-13; first two slices shipped.

* **V17 scope-lock.** SESSION 181's V17 proposal reviewed in
  full, 8 edits applied (pricing-as-estimate, rules
  numbering, rule 1 rewrite, rule 5 folded into rule 2,
  endpoint design committed to single endpoint, slice
  breakdown + parallelization note, in-scope clarifications,
  open-questions resolution). Status flipped to `locked`.
  Rules 10-13 appended to V1; §"Post-close additions" updated
  to name V17 as the second post-close addition (after V16).
* **`933d4e7` — feat(V17.0):** media-engine
  `POST /internal/clips/extend/` endpoint + 13 tests. New
  primitive helpers: `_extract_last_frame` (ffmpeg `-sseof`
  tail-seek), `_extend_poll_task`, `_extend_download`,
  `_extend_concat` (re-encoding filter graph). Reuses
  existing infra (`runway_create_task`, `runway_get_task`,
  `_download_concat_input`, `_probe_duration`). Cached by
  hash(source_clip_url + prompt + duration + ratio + seed).
* **`cfc2854` — feat(V17.1):** Django `extend_visual_clip`
  primitive + cost estimator + 19 tests. New
  `ExtendClipResult` dataclass + `MediaEngineClient.extend_clip()`
  method. Cost = new-segment seconds × $0.05/sec (floor 5s) —
  charges only the new segment, source isn't re-rendered.

**Q-v17-1 surfaced + resolved mid-slice.** Live Runway API
check during V17.0 slice-open found that `/v1/video_to_video`
only accepts `gen4_aleph` (the V11 style-remix model). The
V17 proposal's original framing (`gen4_turbo` / `gen4.5`
extend mode at that endpoint) was wrong. Pivoted to
**last-frame extraction + `/v1/image_to_video` (gen4_turbo) +
ffmpeg concat**, all on the media-engine side. Operator-facing
capability unchanged; endpoint became synchronous (mirrors V11
style_remix) instead of async (the original proposal mirrored
V4 visual_clip).

Tests: Django **871** (+19 from V17.1 in compositions, +9
unrelated growth between SESSIONS 181-182); compositions **440**
(421 → 440). Media-engine **190** (177 → 190, +13 from V17.0).
SPA vitest **95** unchanged.

Real-mode spend this session: **$0**. Q-v17-1 surfaced before
any Runway calls fired; remaining work was mock-mode + unit
tests.

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **A confident API claim in a design doc is a hypothesis,
   not a fact, until live-doc verified.** The V17 proposal
   had been reviewed, edited, scope-locked, and had rules
   merged into V1 with the wrong API shape baked in.
   Slice-open verification surfaced the gap — but by then,
   four upstream artifacts had to be amended. **Before
   scope-lock of any slice that references a third-party
   API capability, live-doc check the specific
   endpoint+model+param combination.** Third recurrence
   of this pattern (SESSIONS 175, 181, 182); deserves a
   slice-open checklist item.

2. **Pre-implementation pause when a finding shifts scope.**
   When Q-v17-1 surfaced, I stopped before writing endpoint
   code, surfaced three options (A — pivot / B — try aleph
   / C — defer V17) to the operator, waited for direction.
   Operator confirmed A explicitly. The pause was ~5
   minutes; the alternative (commit wrong-shape code, rip
   it out, re-litigate) would have been far costlier.
   Pattern: **"finding shifts scope" + "still implementing"
   is the failure mode**; pause + surface + operator
   confirms is the right shape.

3. **Sync vs async endpoint contract is a design-time
   decision.** V17.0 originally proposed mirroring V4
   visual_clip's async fire-and-poll. The pivot to V11
   style_remix's synchronous shape was forced by the
   actual implementation flow: ffmpeg + Runway + ffmpeg
   doesn't fit async semantics. **Mirror the nearest
   existing endpoint with the same architectural shape**,
   not the nearest endpoint in the same conceptual family.
   V11 style_remix (download + ffmpeg + provider + concat
   wrapped sync) was the contract twin, even though
   conceptually V4 visual_clip is closer to extend.

### Final state at session close

* V17 **scope-locked with 13 contract rules total** (V1's
  9 + V17's 4 = 13). V17.0 + V17.1 shipped; V17.2-V17.5
  pending.
* Q-v17-x resolution: Q-v17-1 RESOLVED SESSION 182;
  Q-v17-2/3/4 RESOLVED at lock; Q-v17-5 open (cost
  estimator with unknown source duration, resolves at
  V17.5 slice-open).
* No workspace artifacts (compositions / assets) created
  this session — all work was scope + mock-mode + unit
  tests.

### FIRST THING (SESSION 183): V17.2 — cinematic_visual_extended recipe

Operator-recommended direction from V17.1 close: V17.2 is the
natural next slice. Most operator-facing of the remaining
five.

1. **Read** `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`
   §"Slice breakdown" V17.2 row + the dependency tree.
   V17.2 chains V17.1's `extend_visual_clip` primitive
   off V4's `generate_visual_clip` output.

2. **Read** the existing V4 `cinematic_visual` starter +
   recipe form to understand the V4 shape we're chaining
   from. The new `cinematic_visual_extended` recipe takes
   a target duration > 10s and lays down 1
   `generate_visual_clip` + N `extend_visual_clip` steps
   where N = ceil((target - 10) / 5).

3. **Ship V17.2** — recipe starter + recipe form + tests +
   real-mode dogfood. ~1 session. Real-mode dogfood at
   this slice is the **first time V17.0's actual
   `/v1/image_to_video` flow fires in anger** — Q-v17-1's
   pivot lives or dies here.

After V17.2 closes, V17.3 (keyframes track) is independent
of V17.0-V17.2 + V17.5. Could parallelize if the operator
wants two fronts open simultaneously; default per the locked
doc is linear.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete +
R-arc real-mode validated (SESSION 176); V-arc real-mode
validation **near-complete** (16 of 18 recipes, SESSIONS
158 + 179 + 180 + 181). V16 post-close shipped (SESSION
179); **V17 scope-locked SESSION 182 with V17.0 + V17.1
shipped**. V17.2-V17.5 pending.
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent
(SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); **16/18 real-mode validated** |
| **V17 (extend + keyframes)** | **LOCKED (SESSION 182); V17.0 + V17.1 SHIPPED; V17.2-V17.5 pending** |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| B0-B5 brand ecosystem pivot | DONE (SESSION 178) |
| V16 remove_avatar_background | DONE (SESSION 179) |
| V9 polish form shorthands + intro_outro fixes | DONE (SESSION 180) |
| V7/V11/V13 dogfood fixes + 11 recipes validated | DONE (SESSION 181) |
| **V17.0 (extend endpoint) + V17.1 (extend primitive)** | **DONE (SESSION 182)** |
| B6-B10 brand arc | Deferred (product #2 reality) |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI (AUDIO / IMAGE) | NEW QUEUED (SESSION 181) — operator-facing gap |
| 2 of 18 V-arc recipes unvalidated | storyboard_voiced + dialogue_scene; deferred until V17 lands |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179-181 hero — most-validated avatar)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (stale "Thruman" record at same prefix queued for cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most-dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**SESSION 182 workspace artifacts:** none. All work was
scope-lock + mock-mode + unit tests; no compositions /
assets / VOICE / AUDIO rows persisted.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174 — V2 dark navy + gold
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 183 stack-up notes:**

* **Celery worker restart required** if working V17.2 — the
  V17.1 primitive registration in
  `apps/compositions/primitives/__init__.py` is new since
  SESSION 181's worker pid 24687. Restart so the worker
  picks up `extend_visual_clip`.
* Uvicorn `--reload` window can serve requests with stale
  module code mid-swap — when iterating on
  `media-engine/app/` files with rapid edits + immediate
  re-fires, wait for the "Application startup complete"
  log line between iterations (per SESSION 180
  TRUST_CALIBRATION entry).
* First-call deps cached: ~176MB `u2net_human_seg.onnx`
  for V16 matting at `~/.u2net/`.

**Smoke checks** (counts as of SESSION 182 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 871 tests (compositions: 440)

# Media-engine (from media-engine/)
python -m pytest                              # 190 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 182**:

* `POST /internal/clips/extend/` — media-engine. Last-frame
  + image_to_video + concat. Mirrors V11 style_remix's
  sync shape.
* `extend_visual_clip` Django primitive — registered as
  the 15th primitive (12th real + 3 mock).
* `MediaEngineClient.extend_clip()` — Python client.
  Returns `ExtendClipResult` with source + new-segment
  + total durations split out.

---

## AI / assistant context

- **Last session: SESSION 182 — V17 scope-lock + V17.0 +
  V17.1.** Two feature commits. V17 went `proposed → locked`
  with rules 10-13 merged into V1. V17.0 (media-engine
  endpoint) + V17.1 (Django primitive) shipped. Q-v17-1
  surfaced + resolved at slice-open with a clean pivot. No
  Runway spend.

- **Calibration carried forward (NEW SESSION 182)**:
  - **API claim in design doc = hypothesis until live-doc
    verified.** Third recurrence of this pattern (SESSIONS
    175 / 181 / 182). Worth a slice-open checklist item:
    live-doc check before any code.
  - **Pre-implementation pause when a finding shifts
    scope.** Stop + surface + operator confirms is the
    right shape; "still implementing" is the failure mode.
  - **Sync vs async endpoint contract is a design-time
    decision.** Mirror the nearest endpoint with the same
    architectural shape, not the same conceptual family.

- **Calibration carried forward (from earlier sessions)**:
  - Operator "are we using X?" framing surfaces capability
    gaps (SESSION 181).
  - Asset upload UI is a recurring gap (SESSION 181).
  - External API validation tightens over time —
    re-dogfood periodically (SESSION 181).
  - "200 OK + plausible byte count" doesn't mean correct
    output (SESSION 180).
  - Uvicorn `--reload` has stale-during-restart window
    (SESSION 180).
  - drawtext `text=` footgun once `fontfile=` joins
    (SESSION 180).
  - Celery worker doesn't auto-reload (SESSION 179).
  - ffmpeg can't infer muxer from double-extension
    tempfile names (SESSION 179).
  - Real-mode dogfood finds bugs in every recipe
    (SESSIONS 179-181 — 15+ bugs across 16 recipes).
  - PostCSS `@import` order (SESSION 178).
  - Operator catches premature extraction (SESSION 178).
  - DevTools computed-style snippet for visual bugs
    (SESSION 178).
  - Lossy paraphrase of scope locks (SESSION 177).
  - Handoff "swapped/edited" claims need verification
    (SESSION 177).
  - Runway DELETE poisons conversation (SESSION 176).
  - Mock-only test coverage hides upstream drift
    (SESSION 176).
  - Operator framing unlocks AI blockers (SESSION 176).
  - gpt-5 reasoning eats output budget silently
    (SESSION 176).
  - Tool descriptions need narration scaffolding
    (SESSION 176).
  - Real-mode dogfood after operator-facing slices.
  - SPA gates need both `pnpm test` AND `pnpm build`.
  - Distinct request boundaries for distinct side-effects.
  - Hook order across early returns (SESSION 169).
  - AI's "shipped" framing belongs to operator after
    review.
  - Doctor is the drift tool + handoff write at
    session-end.
  - OpenAI gpt-5 family uses Responses API.
  - lru_cached `get_settings()` bypasses FastAPI
    dependency_overrides.
  - Radix UI primitives need `userEvent` under jsdom.
  - Scope-lock reviews should distinguish operator
    input from LLM input.
  - Don't rationalise "somewhat readable" — look at
    operator-facing surface.
  - Vitest atomic assertions can mask real UX bugs.
  - Stale browser before stale code.
  - K6.4 stoplist curation trickle.

- **V-arc growth template (SESSION 179-182)**: V16 +
  V17 follow the same shape. Narrow scope, opt-in
  defaults, one primitive + one knob + one endpoint per
  slice, real-mode validated before handoff. SESSION
  182's V17.0+V17.1 fit the template; V17.2's recipe
  layer is the first real-mode validation point for V17.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Both deferred until V17 closes per
  operator-locked direction.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
