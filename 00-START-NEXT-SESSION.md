---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — 9 contract rules, V0-V15 slice breakdown).
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0 done; W11.6.1 next.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_171_DOGFOOD_W11_3_STABILITY_PROMPT_FIXES.md`.

---

## SESSION 171 outcome — W11.2 dogfood + Tier 1 fixes + Stability port

Wide-ranging session driven by operator dogfood of W11.2.
Multiple bugs surfaced, multiple slices shipped:

* **W11.2 dogfood validated** end-to-end against real Runway.
  Voice swap + rebake actions fire cleanly from the SPA.
* **Tier 1 visual_template fix** — `Spokesperson` now persists
  the wizard's template choice (CharField + migration 0004 +
  backfill of all 5 cast rows to `mascot`). Rebake action
  defaults from row instead of hardcoded `coach`. SPA rebake
  modal shows the template in the confirm-spend grid.
* **K6.6.1 leak fix** — Marcus's first real render leaked
  `business_brief` into the script ("I'm Marcus, your AP
  history teacher..."). Fixed three ways in `_system_prompt`:
  fenced the brief as tone-only guidance, dropped "grounds
  them in who you are" framing, added anti-recitation rule.
* **gpt-5 family migration** — K6 / K9 / R6 promoted from
  `gpt-5-mini` to `gpt-5` (full); `script_splitter` +
  transcription stayed on mini. K6's `MAX_OUTPUT_TOKENS`
  raised 500 → 2000.
* **W11.3 Stability port (reframed)** — ported
  `stability_ai_service.py` + `style_library.py` (42 presets)
  + new `stability_portrait.py` from u-d-b. Calibration
  finding: Stability portraits bake but mis-lip-sync (Runway
  rig is tuned for gen4_image geometry). **Reframed for
  W11.6**: Stability is the right provider for non-avatar
  image generation (scenes, b-roll, products). Avatars stay
  on Runway gen4_image.
* **Mascot auto-inject (Tier 1, shipped)** — when
  `template=="mascot"` and the operator's subject lacks
  `"anthropomorphic"`, the composer silently injects a
  creature-anatomy clause. Operators don't have to know the
  magic word.
* **Tier 2 attempt + revert** — tried changing the mascot
  opening + dropping "Professional advertising character
  design" line. Operator visual judgment: still plasticy.
  Diffed runway-hackathon's prompts → bit-identical to
  character-os. Plastic-vs-natural is variance + subject
  complexity, not the template. Reverted Tier 2; Tier 1
  stays.

Tests: Django **727** (+9). Media-engine **111** (+3). SPA
vitest **53** (unchanged).

### Final state at session close

Cast roster after the SESSION 171 re-bakes:

  - Riggs the Donkey — natural-looking bake (cast seed)
  - **Sasha the Raccoon** — re-baked, voice `clara`, operator
    verdict "nailed it"
  - Donny the Sloth — natural-looking bake (cast seed)
  - Maya the Panda — natural-looking bake (cast seed)
  - **Marcus the Battle Unicorn** — re-baked, voice `marcus`,
    visual_subject reset to clean operator-intent form,
    Tier 1 auto-inject anchoring creature-anatomy

### FIRST THING (SESSION 172): W11.6 scope-lock + image gen registry

The Stability port is in-tree and tested but not yet wired
through the production paths. W11.6 should formalize the
multi-purpose image generation surface:

1. **Purpose registry** — `purpose=avatar` → Runway gen4_image
   (current path), `purpose=scene` / `broll` / `product` →
   Stability with style preset selection.
2. **New Django endpoints** — `POST /api/images/` for
   non-avatar image gen (subject + purpose + style_preset +
   negative_prompt).
3. **SPA picker** — surface the 42 preset library somewhere
   useful (probably recipe-launch or a dedicated "Images"
   tab in the workspace fabric).
4. **Cost telemetry** — `cost_micros` (Stability) tracked
   alongside Runway credits in the cost ledger.

Scope-lock the slice properly before writing code — this is
a real surface that touches multiple subsystems.

### Other queued work (in priority-ish order)

1. **F8.1 — K10 seed corpus** — blocked on operator-authored
   markdown.
2. **K6.4 v3 — embedding-similarity fallback** — holds until
   a real paraphrase miss surfaces.
3. **K7.x — YouTube ingest fix** — silent-failure mode noted
   in MEMORY.
4. **K6.3 — Brief length cap** — likely moot now that K6
   produces clean briefs.
5. **K7.1 — Cost telemetry surface in SPA**.
6. **W11.x — surface voice_patch.status in edit modal**
   (calibration finding from this session).

---

## SESSION 170 outcome — W11.2 voice swap + avatar re-bake

The last operator-facing gap on spokesperson editing
closes. Voice + avatar are no longer read-only after
creation:

* **Voice swap** — the existing edit modal gains a Runway
  voice-preset `<select>`. Save fires two requests in
  sequence: PATCH for the W11.1 persona fields, then the
  new `change-voice` action if the voice changed. DB
  persistence + live Runway PATCH are reported
  separately (`voice_patch: {status, error}`) so partial
  success is visible.
* **Avatar re-bake** — dedicated confirm modal on the
  spokesperson detail page, mounted from a new "Re-bake"
  ghost button in the Masthead. Surfaces the cost
  ($5-10 Runway credits, 30-180s wall-clock) before
  spending. New `rebake-avatar` Django action fires
  portrait gen + avatar create against the media-engine
  and swaps `runway_avatar_id` + `portrait_path` on the
  row.

Implementation surfaces:

* `media-engine/app/services/voice_clone_client.py`
  gains `voice_kind="preset"` so
  `PATCH /v1/avatars/<id>` can target Runway voice
  presets (block type `runway-live-preset`) as well as
  custom-clone IDs.
* `media-engine/app/routers/internal.py` —
  `POST /internal/avatars/<id>/change-voice/`.
* `shell/apps/spokespeople/views.py` — two new actions
  (`change-voice`, `rebake-avatar`). Both serialize the
  full spokesperson on response; rebake additionally
  returns 502 with `runway_avatar_status="failed"`
  persisted on bake failure.
* `shell/character_os/clients/media_engine.py` —
  `change_avatar_voice` wrapper.
* `web/src/lib/api/spokespeople.ts` — `useChangeVoice` +
  `useRebakeAvatar` hooks.
* `web/src/components/spokesperson-edit-modal.tsx` — voice
  picker; two-request save.
* `web/src/components/spokesperson-rebake-modal.tsx` —
  new.
* `web/src/routes/spokespeople/$id.tsx` — Re-bake button;
  `rebaking` state above early returns.

**Tests**: SPA vitest **52 → 53** (+1). Django **718**
(unchanged — actions live-exercised SESSION 171 pending).
Media-engine **108** (unchanged). All routes auto-loaded
via runserver / uvicorn `--reload`; no service restart
needed.

### FIRST THING (SESSION 171): live W11.2 dogfood

The natural follow-up is operator-driven. The endpoint
contract has been exercised in tests; the production
side-effect (Runway PATCH on avatar voice; full avatar
re-bake) hasn't been fired against real keys yet.

1. **Voice swap dogfood** — open the SPA edit modal on
   Marcus, change voice from `marcus` to `clara` (or
   `roman` — Latin-flavored), save. Confirm
   `voice_patch.status === "ok"`. Fire a `talking_head`
   render against the same brief used SESSION 169 and
   compare lip-sync quality + tonal feel. ~$0.25 spend.
2. **Re-bake dogfood (optional)** — open the Re-bake
   modal on Marcus or any cast member with a stale-feeling
   avatar. Confirm the spend warning text + the 30-180s
   blocking wait. Avatar id + portrait should swap;
   previous renders' `final_asset` URLs should still work
   (they reference the old asset, not the avatar). ~$5-10
   spend.

Both flows have unit-test coverage on the SPA side; the
dogfood is to validate Runway's real response shapes
match the optimistic implementation.

**Recommendation — after dogfood, pick by mood:**

* **More real-Runway exposure** — `talking_head_polished`
  Sasha retake (V9 — captions + intro/outro);
  `long_form_ad` end-to-end smoke (V5 launch
  differentiator).
* **F8.1 — K10 seed corpus** if operator-authored markdown
  is ready. 30-60 minutes once the markdown lands.
* **K6.4 v3 — embedding-similarity fallback.** Holds
  until a real paraphrase miss surfaces during
  real-Runway work.
* **K7.x — YouTube ingest fix** if the silent-failure mode
  surfaces. ~1 session.
* **K6.3 — Brief length cap (~15 min)** — cheapest cleanup;
  might be moot now that K6 produces clean briefs.
* **K7.1 — Cost telemetry surface** in the SPA. ~1 session.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11; W11.1 + W11.2
ship operator-facing edit + voice + re-bake). Cast went
live in real-mode (SESSION 136). **First marketing video
shipped against real Runway** (SESSION 158).

**Phase 4 (four arcs, three complete; R-arc complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped.
- **Video composition arc (V0-V15). COMPLETE.**
- **Workspace fabric arc (F0-F10). COMPLETE.**
- **Realtime avatar arc (R0-R10). COMPLETE.**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| **First marketing video** | **DONE** (SESSION 158) |
| **Drift-prevention items 2+3** | **DONE** (SESSION 159; context-kit) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| **K6.4 (claim verifier)** | **DONE (SESSION 160)** |
| **K6.4.1 (stoplist widen + strict forensics)** | **DONE (SESSION 161)** |
| **K6.5 (conversation verifier parity)** | **DONE (SESSION 162)** |
| **K6.4 v1.1 (SPA toggle + warning surface)** | **DONE (SESSION 163)** |
| **K6.4 v1.2 (verification_status + recipe rollout)** | **DONE (SESSION 164)** |
| **K6.4 stoplist watchdog** | **DONE (SESSION 165)** |
| **K6.4 v2 (semantic-match surgical fixes)** | **DONE (SESSION 166)** |
| **K6.4 v2.1 (real-Runway dogfood + CTA verbs)** | **DONE (SESSION 167)** |
| **K6.6 (script structure + opener + brief persist)** | **DONE (SESSION 168)** |
| **Marcus end-to-end + W11.1 edit modal** | **DONE (SESSION 169)** |
| **Portrait JWT refresh + hook-order fix** | **DONE (SESSION 169 close, commit `2cdcd26`)** |
| **W11.2 voice swap + avatar re-bake** | **DONE (SESSION 170)** |
| **W11.2 dogfood + Tier 1 visual_template fix** | **DONE (SESSION 171)** |
| **K6.6.1 system prompt leak fix** | **DONE (SESSION 171)** |
| **gpt-5 family migration (K6 / K9 / R6)** | **DONE (SESSION 171)** |
| **W11.3 — Stability port (reframed for W11.6)** | **DONE — Stability is non-avatar image gen (SESSION 171)** |
| **Mascot anthropomorphic auto-inject (Tier 1)** | **DONE (SESSION 171)** |
| K7.x (YouTube ingest fix) | Queued |
| K6.3 / K7.1 | Queued |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - **Sasha the Raccoon** (sales) — id `79d48883-...` — known-good real-render voice (`clara`)
  - Donny the Sloth (user stories) — id `f30b2980-...` — dental artifacts on `drew` voice; eligible for SESSION 171 voice swap or re-bake
  - Maya the Panda (educator) — id `9410f23f-...` — untested in real-mode
  - **Marcus the Battle Unicorn** (AP history tutor) — id `b6a00dd8-...` — `marcus` voice; Nerva–Antonine doc attached; 2 verified strict-mode renders shipped; SESSION 171 voice-swap dogfood target

---

## Queued investigations (priority-ordered)

1. **SESSION 171 dogfood** — voice swap + optional re-bake
   against Marcus. ~$0.25 + ~$5-10.
2. **More real-Runway exposure on other recipes** —
   `talking_head_polished` Sasha retake;
   `long_form_ad` smoke. Real-Runway renders so far this
   thread: **3 renders at $0.75** (SESSION 167 + 168
   probes) + **2 renders at $0.50** (SESSION 169 Marcus
   end-to-end + dogfood loop) + **1 first marketing
   video at $0.50** (SESSION 158).
3. **K6.4 v3 — embedding-similarity fallback.** Holds
   until a real paraphrase miss surfaces in operator
   dogfood.
4. **Run the watchdog periodically.** `python manage.py
   stoplist_watchdog --days=14` weekly.
5. **Older backlog**: F8.1 (blocked on operator
   markdown), K7.x (YouTube ingest silent failure), K6.3
   (brief length cap — likely moot), K7.1 (cost
   telemetry surface).
6. **Voice preset audit** — smoke-test other voices
   beyond `marcus` / `clara` / `drew`. W11.2 makes this
   cheap (no re-bake required for preset swaps).
7. **E2e detritus cleanup.**
8. **OpenAI client factory port.**
9. **Cast sync command.**
10. **Stuck-row janitor.**
11. **Act-Two performance capture.**
12. **`lesson` video kind.**
13. **Real Google OAuth + dj-stripe.**
14. **Allauth legacy-settings cleanup.**
15. **smoke_voice / smoke_avatar transaction discipline.**
16. **INVENTORY working-tree-dirty flag fix.**
17. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 173 stack-up requirement (carried from SESSION 172
close)**: the Celery worker process running locally (`pid 62107`
from 2026-05-15 23:52) has stale module imports — it loaded
before SESSION 171's gpt-5 migration + prompt-composer
auto-inject + before SESSION 172's W11.6.0 scope-lock. **Restart
the worker before firing any composition** so K6 synthesis +
the prompt composer use the current code:

```bash
# Kill the stale worker (matches the SESSION 172 close pid; adjust if respawned)
pkill -f "celery -A character_os worker" || true

# Restart in a new terminal
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Runserver auto-reloads on file changes so it's fine; only
Celery needs the manual reboot.

**Session-end anchor re-stamp + calibration audit** (new in SESSION 159):

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py \
    handoff write <NNN> --project .
```

**Six force-mocks** (RUNWAY on media-engine;
EMBEDDING + RENDER_SCRIPT + CONVERSATION_REPLY + SERPER
+ REALTIME_MEMORY on Django). With `RUNWAY_API_KEY` set
in `.env`, media-engine runs in real mode by default.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 718 tests

# Media-engine (from media-engine/)
python -m pytest                              # 108 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 53 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 170 — W11.2 voice swap +
  avatar re-bake.** Operator-facing edits on
  spokespeople are no longer read-only-after-creation.
  Two new endpoints (`change-voice`, `rebake-avatar`)
  + voice picker in the edit modal + dedicated re-bake
  confirm modal on the detail page. Test counts:
  SPA **52 → 53**; Django **718**; media-engine **108**.
- **Calibration carried forward:**
  - **Distinct request boundaries for distinct
    side-effects** — when an SPA save spans a DB write
    + an external-system call, model them as two
    requests, not one bundled PATCH. The action endpoint
    surfaces the side-effect result explicitly.
  - **Mock-fetch should route-switch from day one**
    once a component hits more than one endpoint. The
    failure mode (schema parse → mutation throws → far
    expectation fails) is hard to diagnose.
  - **Hook order across early returns** (SESSION 169) —
    pattern held; new state hooks live above the
    loading/error/not-found returns. Caught preemptively
    on the `rebaking` state add.
  - **AI's "shipped" framing belongs to the operator
    after review** for any model-output deliverable.
  - **Avatar voice × lip-sync quality is a real
    operational axis.** W11.2 makes the smoke-test loop
    cheap; SESSION 171 should exercise it.
  - **R9 placeholder accurate to ~5x** — stub-and-refine
    validated.
  - **Drift verifiers belong as early scaffolding**
    (SESSION 157).
  - **Milestone-level doc refresh has its own cadence**
    (SESSION 156).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151). **Now
    paired with `handoff write` at session-end**
    (SESSION 159).
  - **OpenAI gpt-5 family uses the Responses API.**
- **Realtime arc complete; W-arc operator-facing
  gaps closed.** Phase 4's four arcs all shipped;
  W11.1 + W11.2 close the spokesperson edit loop.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
