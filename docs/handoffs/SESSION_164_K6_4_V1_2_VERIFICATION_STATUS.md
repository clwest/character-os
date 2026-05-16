---
title: "Session 164 — K6.4 v1.2 verification_status + recipe rollout"
date: 2026-05-15
status: complete
session: 164
previous_handoff: ./SESSION_163_K6_4_V1_1_SPA_TOGGLE.md
---

# Session 164 — K6.4 v1.2 verification_status

## TL;DR

K6.4 v1.2 closes the SESSION 161 bypass-case audit gap: an
empty `verification_warnings` list used to be ambiguous
between "verified clean" and "verifier didn't run." v1.2
adds an explicit four-state field on both `Composition` and
`ConversationMessage`, plus a colored SPA badge keyed off
the state. Same commit rolls `_VERIFIER_MODE_FIELD` to the
three remaining K6-aware recipes
(`talking_head_with_backdrop`, `talking_head_polished`,
`long_form_ad`) so the strict/warn/off control surfaces
everywhere.

Tests: Django **693 → 697** (+4). SPA vitest **40 → 46** (+6).
Migrations **54 → 56**. SPA build clean. tsc clean.

## What shipped

### Backend — `verification_status` field

New `VerificationStatus` TextChoices in
`apps.compositions.models`. Four states:

* `VERIFIED` — synthesis ran AND verifier ran in
  strict/warn mode. `verification_warnings` may be empty
  (clean) OR populated (Warn flags). Either way, the
  contract held.
* `TRUSTED_PASSTHROUGH` — synthesis path degraded (no
  chunks, no OpenAI key, retrieval failure, mock mode).
  Operator's prompt flowed through verbatim; trusted by
  definition.
* `SKIPPED` — verifier mode was `"off"`. LLM ran but no
  verification occurred; operator may have invented.
* `REJECTED` — strict mode caught unsupported claims and
  blocked the render. `rejected_synthesis` carries what
  the LLM produced. Composition `status` will be `FAILED`.

Both `Composition` and `ConversationMessage` grew the
field (migrations `0004_composition_verification_status`
+ `0004_conversationmessage_verification_status`). Default
empty string for pre-v1.2 rows.

### Backend — wiring

* `ScriptResult.verification_status: str` populated at
  every return path in `build_render_brief`. Three of the
  five paths return `trusted_passthrough`; the post-
  synthesis path resolves `verified` vs `skipped` based
  on `_get_default_mode()`-resolved mode.
* `ReplyResult.verification_status: str` same pattern in
  `conversation_synthesis.py`.
* `_maybe_synthesize_script` in the avatar_speech
  primitive now returns a 4-tuple
  (`brief, chunk_ids, verification_warnings,
  verification_status`). The strict-rejection catch sets
  `composition.verification_status = "rejected"`
  alongside warnings + rejected_synthesis.
* `apps/conversations/views.py` persists
  `ConversationMessage.verification_status` on every
  spokesperson message (rejected on 422, otherwise
  whatever the synthesizer returned).
* Both serializers expose the new field.

### SPA — `VerificationStatusBadge` component

New `web/src/components/verification-status-badge.tsx`.
Renders a colored badge keyed off the four states. Empty
status renders nothing (pre-v1.2 row or USER message).

Dropped into two places:

* Composition detail page header (next to mock-mode
  badge / composition id).
* Each SPOKESPERSON `MessageBubble` in the conversation
  thread view (next to spokesperson name).

Zod schemas in both `conversations.ts` + `recipes.ts`
parse the field with a default of empty string so older
rows still load.

### Recipe rollout

`_VERIFIER_MODE_FIELD` added to:

* `talking_head` ← already from v1.1
* `talking_head_with_backdrop` ← v1.2
* `talking_head_polished` ← v1.2
* `long_form_ad` ← v1.2 (sets the mode on every
  per-chunk speech step)

Corresponding starter signatures grew a `verifier_mode:
str | None = None` kwarg. For `long_form_ad`, the mode is
copied into every per-chunk `generate_avatar_speech`
step's `params["verifier_mode"]`.

### Backend tests (+4)

* `test_verification_status_verified_on_clean_warn_k6_4_v1_2`
* `test_verification_status_skipped_on_off_mode_k6_4_v1_2`
* `test_verification_status_trusted_passthrough_when_no_openai_key_k6_4_v1_2`
* `test_api_strict_rejection_persists_status_rejected_k6_4_v1_2`

### SPA tests (+6)

`verification-status-badge.test.tsx`: 6 cases covering
each of the four explicit states + empty status + unknown
status (defensive null-render).

## Live dogfood

Direct synthesizer probe (bypassing HTTP) confirmed the
two interesting state transitions in real-mode:

* **Warn mode** against Donny's RAG-attached thread:
  prompt "Summarize the chunking section." →
  `verification_status="verified"`, 1 Warn flag
  (`'Alright'` — sentence-initial false positive; a
  future stoplist widening candidate). The flag didn't
  block the reply; the badge will render "Verified" in
  emerald.

* **Off mode** explicit override: prompt "Why use a
  vector DB?" with `verifier_mode="off"` →
  `verification_status="skipped"`, warnings empty.
  Bypass case audit-distinguishable from
  `verified+empty`. Closes the SESSION 161 gap.

`trusted_passthrough` + `rejected` paths are exercised
by the new backend tests; live HTTP exercise of the
`rejected` 422 path lives in the prior K6.4 v1.1 dogfood
(SESSION 163 handoff).

## Calibration moments worth carrying

### 1. Recipe rollouts get cheaper as the metadata layer matures

K6.4 v1.1 added `_VERIFIER_MODE_FIELD` once + applied it
to 1 recipe (1 edit). K6.4 v1.2 applied the same field to
3 more recipes — total recipe edit was 3 one-line tuple
additions + 3 starter-signature-+ kwarg-passthrough
patches. The cost dropped to ~15 minutes total because
the metadata layer absorbed the field once; subsequent
applications are mechanical. Reinforces the SESSION 163
"Metadata-driven forms paid off" calibration:
investment compounds across recipes.

**Carry-forward**: when reusable field templates land,
roll them out to siblings while the muscle memory is
fresh. The first 1 rollout is design work; the rest is
mechanical and fast. Batching v1.x rollouts with the
field's debut is cheaper than coming back later when
the operator has flipped contexts.

### 2. Field defaults vs explicit values matter for tests

The `_maybe_synthesize_script` refactor from 3-tuple to
4-tuple broke one test that mocked `build_render_brief`
with `MagicMock()` (without setting the new
`verification_status` attr). MagicMock lazily-created
the attr as another MagicMock; assigning that to a
`CharField` via the Django ORM raised a FieldError
about "aggregate functions not allowed in this query"
— a confusing surface error for what was really
"MagicMock leaked into ORM assignment." The fix was
one line on the test fixture: set
`fake_script_result.verification_status = "verified"`
explicitly.

**Carry-forward**: when adding new attributes to a
dataclass that's mocked elsewhere, audit the mocks for
attrs the new code path will read. Pyright would catch
this on a real type, but MagicMock is structurally
typed; only running the test surfaces the leak.
**Generalisation**: dataclass evolution + mocks have a
sharp edge here. Either use real dataclass instances
in tests, or stamp every new attr on every mock that
gets read by the code under test.

## Files changed in this commit

* `shell/apps/compositions/models.py` —
  `VerificationStatus` enum + field on `Composition`.
* `shell/apps/compositions/migrations/0004_composition_verification_status.py`
  — new.
* `shell/apps/conversations/models.py` — field on
  `ConversationMessage`.
* `shell/apps/conversations/migrations/0004_conversationmessage_verification_status.py`
  — new.
* `shell/character_os/script_synthesis.py` —
  `verification_status` on `ScriptResult`; populated at
  every return path.
* `shell/character_os/conversation_synthesis.py` — same.
* `shell/apps/compositions/primitives/avatar_speech.py`
  — 4-tuple signature; persist status on strict
  rejection.
* `shell/apps/compositions/starters.py` —
  `verifier_mode` kwarg added to
  `talking_head_with_backdrop`, `talking_head_polished`,
  `long_form_ad`.
* `shell/apps/compositions/recipes.py` —
  `_VERIFIER_MODE_FIELD` added to the three additional
  recipes.
* `shell/apps/compositions/serializers.py` — exposes
  `verification_status`.
* `shell/apps/conversations/serializers.py` — same.
* `shell/apps/conversations/views.py` — persist status
  on every spokesperson message.
* `shell/apps/conversations/tests/test_k6_5_verifier.py`
  — +4 v1.2 tests.
* `shell/apps/compositions/tests/test_primitive_avatar_speech.py`
  — MagicMock attrs (1-line fix).
* `web/src/lib/api/conversations.ts` — schema +
  `verificationStatusSchema` export.
* `web/src/lib/api/recipes.ts` — schema.
* `web/src/components/verification-status-badge.tsx` —
  new.
* `web/src/components/verification-status-badge.test.tsx`
  — new (6 tests).
* `web/src/routes/compositions/$id.tsx` — badge in
  header.
* `web/src/routes/conversations/$id.tsx` — badge in
  message bubble.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4 v1.2 notes.
* `docs/TRUST_CALIBRATION.md` — two new entries.
* `00-START-NEXT-SESSION.md` — overwritten for
  SESSION 165.
* `docs/handoffs/SESSION_164_K6_4_V1_2_VERIFICATION_STATUS.md`
  — this file.

## What's next (SESSION 165)

The K-arc verifier thread is feature-complete and
operator-visible end to end. The remaining backlog
shifts back to real-Runway exposure and operator-facing
UX:

* **More real-Runway exposure.** Strict mode has been
  validated in mock-mode + via direct synthesizer
  probes. Time to fire some real renders under the new
  default Warn + Strict-per-recipe contract and see
  what the operator-facing experience feels like.
* **K6.4 v2 — semantic-match upgrade.** Lowercase tech
  names + short common adjectives still slip the
  substring matcher. A small-model NER pass or
  embedding-similarity check would close the gap.
* **Stoplist watchdog.** Every session has surfaced
  1-3 new false positives via dogfood. A scripted
  reporter that scans recent compositions for
  sentence-initial flagged words would generate
  stoplist candidates without live operator
  intervention.

Or anything else from the backlog (`F8.1`, `K7.x`,
`K6.3`, `K7.1`, `W11.1`).

---

*Handoff written end-of-SESSION 164. Anchors re-stamped
via `context-kit handoff write 164`. Strict mode left
active in the running services for ongoing dogfooding.*
