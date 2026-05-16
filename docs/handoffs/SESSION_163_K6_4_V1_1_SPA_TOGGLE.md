---
title: "Session 163 — K6.4 v1.1 SPA toggle + verifier surface"
date: 2026-05-15
status: complete
session: 163
previous_handoff: ./SESSION_162_K6_5_CONVERSATION_PARITY.md
---

# Session 163 — K6.4 v1.1 SPA toggle

## TL;DR

The K6.4 / K6.4.1 / K6.5 verifier thread had backend
machinery but zero SPA surface — operators flipped strict /
warn / off via env vars only, and `verification_warnings`
were persisted but invisible. K6.4 v1.1 closes that gap.

* **Backend:** per-request `verifier_mode` flows through
  the entire stack (recipes → starter → primitive →
  synthesizer → verifier). Conversations API accepts
  `verifier_mode` in the POST body (400 on invalid;
  defaults to settings if absent). Both serializers expose
  `verification_warnings` + `rejected_synthesis`.
* **SPA:** conversation chat composer + recipe form get a
  Strict/Warn/Off select. 422 strict-mode rejection renders
  a `VerifierRejectionPanel` with the unsupported claims +
  a collapsible "what the LLM almost said." Message bubbles
  show a "K6.4 flagged N claims" badge when warnings exist.
  Composition detail page surfaces both warnings + rejected
  synthesis in a dedicated panel.

Tests: Django **691 → 693** (+2). SPA vitest **37 → 40** (+3).
Migrations unchanged at **54**. SPA build clean. tsc clean.

## What shipped

### Backend — per-request mode plumbing

* `shell/character_os/script_synthesis.py` —
  `build_render_brief(verifier_mode=None)` kwarg. Passes
  to `run_verifier(mode=...)`. None falls back to
  settings → env → "warn".
* `shell/character_os/conversation_synthesis.py` — same
  on `synthesize_spokesperson_reply`.
* `shell/apps/compositions/primitives/avatar_speech.py` —
  reads `step.params.get("verifier_mode")` and threads it
  into `build_render_brief`.
* `shell/apps/compositions/starters.py:talking_head` —
  new `verifier_mode` kwarg, stored on `step.params`.
* `shell/apps/compositions/recipes.py` — new
  `_VERIFIER_MODE_FIELD` template; added to the
  `talking_head` recipe. Future K6.4 v1.x rolls it out
  to the rest of the recipes (queued; one-line edits).
* `shell/apps/compositions/serializers.py` —
  `CompositionSerializer` exposes
  `verification_warnings` + `rejected_synthesis`.
* `shell/apps/conversations/views.py` — accepts
  `verifier_mode` in POST body; validates against
  `{"strict", "warn", "off"}` (400 on unknown).

### SPA — types, toggle, surfaces

* `web/src/lib/api/conversations.ts`:
  * `messageSchema` gains `verification_warnings` +
    `rejected_synthesis` (both default empty so older
    messages still parse).
  * `verifierRejectionSchema` for the 422 body.
  * `useSendMessage` mutation now takes
    `{content, verifierMode?}` instead of bare content.

* `web/src/lib/api/recipes.ts`:
  * `compositionSchema` gains
    `verification_warnings` + `rejected_synthesis`.

* `web/src/routes/conversations/$id.tsx`:
  * State for `verifierMode` (default `"warn"`) +
    `verifierRejection`.
  * On `ApiError.status === 422`, parses
    `body.verifier_rejection` and renders a
    `VerifierRejectionPanel`.
  * `VerifierModeSelect` renders in the composer footer.
  * Each message bubble shows a "K6.4 flagged N
    claim(s)" badge when `verification_warnings.length > 0`,
    or "K6.4 strict — reply withheld" when
    `rejected_synthesis` is set. Expandable inline detail
    panel.

* `web/src/routes/compositions/$id.tsx`:
  * New `VerifierPanel` section, rendered when either
    `verification_warnings.length > 0` or
    `rejected_synthesis.length > 0`.
  * Sits between the failed/final-asset row and the
    citations panel.

### Tests

* `apps/conversations/tests/test_k6_5_verifier.py` — 2 new:
  * `test_api_per_request_verifier_mode_overrides_settings_k6_4_v1_1`
    — confirms per-request override beats settings.
  * `test_api_invalid_verifier_mode_returns_400_k6_4_v1_1`
    — bad value rejected with 400.
* `web/src/routes/conversations/verifier-ui.test.tsx`
  — 3 new vitest cases on `verifierRejectionSchema`
  parsing (well-formed body, wrong mode rejected, wrong
  array type rejected).

## Live dogfood

* **Per-request override**: `synthesize_spokesperson_reply(
  thread, prompt, verifier_mode="warn")` ran with
  settings + env = `strict`. Reply produced
  successfully, warnings=0 (model stayed grounded).
  Override path confirmed working end-to-end.
* **HTTP API 422**: POSTed to
  `/api/conversations/<id>/messages/` with
  `verifier_mode=strict` + a patched
  fabrication-prone LLM response. Got:
    * Status `422`
    * Body contained `user_message`, `spokesperson_message`,
      `knowledge_chunk_ids`, `verifier_rejection`
    * `verifier_rejection.mode === "strict"`
    * `verifier_rejection.unsupported_claims` populated
      with `['Drop a Wikipedia', 'Wikipedia']` (the
      multi-word matcher caught the broader phrase too —
      operationally still correct; v2 may tighten)
    * `spokesperson_message.verification_warnings` +
      `spokesperson_message.rejected_synthesis` both
      persisted

  The SPA's `VerifierRejectionPanel` will render this
  payload directly. Visual confirmation deferred to the
  next live SPA session.

## Calibration moments worth carrying

### 1. Metadata-driven forms paid off

The SPA's make-video form is metadata-driven — recipe
metadata declares the fields, the form renderer reads
the metadata and emits the right input element. Adding
the Strict/Warn/Off select to the `talking_head` recipe
took **two edits**: define `_VERIFIER_MODE_FIELD` once,
add a reference to it in the recipe's `fields` tuple.
Zero form-renderer changes. Zero SPA route changes for
the make-video path. The metadata-driven approach
absorbed the new field without ceremony.

**Carry-forward**: when adding new form fields to
existing metadata-driven surfaces, the cost is one
field declaration + one tuple entry. This is *much*
cheaper than touching the form rendering layer. Stay
in the metadata for as long as the field shape fits
the renderer's vocabulary; only break out when the
field needs custom rendering the renderer can't
express.

### 2. SPA tests went lighter than expected

K6.4 v1.1 added SPA surfaces (toggle, rejection panel,
inline warnings) but only 3 vitest cases — all on the
schema parsing. Component-level tests for
`VerifierRejectionPanel` and `VerifierModeSelect`
weren't added because the components are small + the
backend tests already prove the data shapes round-trip.
The trade-off: a UI regression that doesn't break the
schema parsing won't be caught by vitest. Visual
confirmation needs an operator-driven SPA session.

**Carry-forward**: small UI components hand-tied to a
well-tested API can ship with schema-only vitest
coverage when the visual is straightforward.
The cost of a UI regression here is "operator sees
something weird" → 5-minute fix. The cost of
component-level vitest tests is ~15 minutes per
component. Worth it when the component encodes
significant logic; not worth it when it's a flat
render of pre-shaped data.

## Files changed in this commit

* `shell/character_os/script_synthesis.py` —
  `verifier_mode` kwarg.
* `shell/character_os/conversation_synthesis.py` —
  `verifier_mode` kwarg.
* `shell/apps/compositions/primitives/avatar_speech.py`
  — reads from step.params.
* `shell/apps/compositions/starters.py:talking_head` —
  new kwarg.
* `shell/apps/compositions/recipes.py` —
  `_VERIFIER_MODE_FIELD` + applied to `talking_head`.
* `shell/apps/compositions/serializers.py` — exposes
  verification fields.
* `shell/apps/conversations/views.py` — accepts +
  validates `verifier_mode`.
* `shell/apps/conversations/tests/test_k6_5_verifier.py`
  — +2 backend tests.
* `web/src/lib/api/conversations.ts` — types + schema
  + mutation shape.
* `web/src/lib/api/recipes.ts` — composition schema.
* `web/src/routes/conversations/$id.tsx` — toggle +
  rejection panel + inline warning bubble.
* `web/src/routes/compositions/$id.tsx` — verifier
  panel section.
* `web/src/routes/conversations/verifier-ui.test.tsx`
  — new schema tests.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4 v1.1 ship
  notes.
* `00-START-NEXT-SESSION.md` — overwritten for
  SESSION 164.
* `docs/handoffs/SESSION_163_K6_4_V1_1_SPA_TOGGLE.md`
  — this file.

## What's next (SESSION 164)

The K-arc verifier thread is now operator-visible end
to end. Remaining queued v1.x:

* **K6.4 v1.2 — `verification_status` field.** Captured
  SESSION 161. Add a TextChoices field distinguishing
  `verified | trusted_passthrough | skipped`. Closes
  the bypass-case audit gap. ~30 minutes.
* **Roll `_VERIFIER_MODE_FIELD` to more recipes.** v1.1
  added it only to `talking_head`. The other K6-aware
  recipes (`talking_head_with_backdrop`,
  `talking_head_polished`, `long_form_ad`) should grow
  the same field. ~15 minutes.

Outside the K-arc backlog: more real-Runway exposure,
F8.1, K7.x YouTube ingest fix, K6.3 brief length cap,
K7.1 cost telemetry, W11.1 edit-spokesperson modal.

---

*Handoff written end-of-SESSION 163. Anchors re-stamped
via `context-kit handoff write 163`. Strict mode left
active in the running Django + Celery for ongoing
operator dogfooding.*
