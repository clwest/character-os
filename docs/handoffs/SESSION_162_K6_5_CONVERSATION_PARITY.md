---
title: "Session 162 — K6.5 conversation verifier parity"
date: 2026-05-15
status: complete
session: 162
previous_handoff: ./SESSION_161_K6_4_1_STRICT_DOGFOOD.md
---

# Session 162 — K6.5 conversation verifier parity

## TL;DR

K6.5 ships verifier parity onto `conversation_synthesis.py`.
The same hallucination class K6.4/K6.4.1 catches on render
scripts now applies to `/api/conversations/<id>/messages/`
replies. Strict mode returns 422 with the rejected
synthesis + flagged claims; Warn mode persists warnings on
the SPOKESPERSON `ConversationMessage`.

**Live dogfood surfaced an unexpected failure class:** the
verifier was rejecting *honest refusals*. When K6 says "I
don't know which library — the docs don't say," the words
`Short`, `Which`, `HTML` (used in clarification) aren't in
chunks → the verifier flagged them → the operator never saw
the honest answer. Punishing honesty is the **opposite** of
the verifier's purpose. Fixed inline by widening the
stoplist with refusal-pattern words.

Tests: Django **684 → 691** (+7). Migrations: **53 → 54**.

## What shipped

### `shell/apps/conversations/models.py` — two new fields

`ConversationMessage.verification_warnings: JSONField` +
`ConversationMessage.rejected_synthesis: TextField`. Same
shape as `Composition.verification_warnings` /
`Composition.rejected_synthesis` from K6.4 / K6.4.1.
Empty on USER messages (user input is trusted by
definition). Populated on SPOKESPERSON messages in Warn
mode (`verification_warnings`) and on strict-mode
rejection placeholders (`rejected_synthesis` carries what
the LLM said).

Migration: `apps/conversations/migrations/0003_k6_5_verification_warnings.py`.

### `shell/character_os/conversation_synthesis.py` — verifier hook

`ReplyResult.verification_warnings: list[dict]` added.
After `_call_responses_api` returns, the synthesis runs
through `claim_verifier.run_verifier`. Strict mode raises
`ClaimVerifierError` (same exception type K6.4 uses);
Warn mode returns the list. Corpus built via
`build_corpus(docs, spokesperson=..., operator_prompt=user_content,
extras=[h.chunk_text for h in history])` — thread history
chunks legitimately introduce terms via prior turns so
they belong in the allow-list.

### `shell/apps/conversations/views.py` — API contract

`POST /api/conversations/<id>/messages/`:

* **Warn / Off / clean** → **201** with the standard
  payload. `spokesperson_message.verification_warnings`
  is populated in Warn mode.
* **Strict + rejection** → **422** with:
  ```json
  {
    "user_message": {...},
    "spokesperson_message": <placeholder msg>,
    "knowledge_chunk_ids": [],
    "verifier_rejection": {
      "mode": "strict",
      "rejected_synthesis": "<what the LLM said>",
      "unsupported_claims": [{"claim": "...", "kind": "...", "position": ...}]
    }
  }
  ```

The placeholder SPOKESPERSON message captures the rejection
in `content` so thread continuity is maintained even when
the real reply was withheld; the operator can audit the
rejection via the persisted `rejected_synthesis` field.
The user's original message is always persisted regardless.

### `shell/apps/conversations/serializers.py` — SPA surface

`ConversationMessageSerializer` exposes
`verification_warnings` + `rejected_synthesis` so the
SPA's K6.4 v1.1 SPA toggle slice (queued) can render
them without a separate fetch.

### `shell/character_os/claim_verifier.py` — refusal-pattern stoplist

K6.5 dogfood discovery (see §Calibration moments).
Stoplist widened with: `short, long, brief, quick, which,
what, where, whose, whom, either, neither, both, many,
lots, rather, instead, otherwise, frankly, honestly,
actually, really, straight, plain, plainly, simply, fine,
ok, okay`. Same pattern as K6.4's `Cleanest`/`Welcome` and
K6.4.1's `Modern`/`Digital` additions: hand-curated
stoplist, anchored by a regression test.

### `shell/apps/conversations/tests/test_k6_5_verifier.py` — 6 new tests

Coverage:

* Warn-mode `synthesize_spokesperson_reply` populates
  `ReplyResult.verification_warnings`.
* Strict-mode raises `ClaimVerifierError` carrying the
  synthesized text.
* Off-mode bypasses the verifier (no warnings).
* User-introduced terms in the prompt are allow-listed
  (parity with K6.4's operator-prompt allow-list).
* API view warn mode → 201 + persisted
  `verification_warnings`.
* API view strict mode → 422 with `verifier_rejection`
  payload, placeholder `spokesperson_message` persisted
  with `rejected_synthesis`, USER message preserved.

### `shell/apps/compositions/tests/test_claim_verifier.py` — +1 test

`test_extract_skips_refusal_pattern_starters_k6_5` anchors
the SESSION 162 stoplist widening with a synthetic refusal
text containing the full new false-positive set.

## Live dogfood (strict mode, real Runway, real OpenAI)

Donny + his attached Wikipedia-RAG doc + a fresh
ConversationThread:

| Prompt | First-run result | After stoplist fix |
|---|---|---|
| "Tell me how your knowledge layer ingests pages." | **PASSED** — 1144-char chunk-grounded reply about embeddings, vector databases, retrieval | Same |
| "What companies have written about RAG?" | **PASSED** — correctly cited Ars Technica (which is in the corpus) | Same |
| "What's the library you use under the hood for parsing pages?" | **REJECTED** on `Short`, `HTML`, `Which` — but the synthesis was an *honest refusal*, not a hallucination | **PASSED** — honest refusal flows through |
| "Tell me about famous AI projects that use RAG." | **PASSED** — model says "I don't have names of specific famous AI projects" + sticks to RAG concepts in the chunks | Same |

The acid test was the third prompt. The model's honest
"I don't know which library" got punished by the strict
verifier because honest meta-language uses meta-terms not
present in the source. After widening the stoplist, the
same prompt passes.

## Calibration moments worth carrying

### 1. The verifier was punishing honest refusals — opposite of its purpose

K6.4 / K6.4.1 framed the verifier as a hallucination
filter. SESSION 162's live dogfood revealed a class the
scope-lock didn't anticipate: **honest refusals**. When the
model correctly says "the docs don't say which library
we use," it produces refusal-meta-language ("Short
answer", "Which library", "HTML") that lives outside the
source doc's vocabulary. The verifier's substring matcher
can't distinguish "the model invented HTML as a fact" from
"the model named HTML while clarifying the question."

**Carry-forward**: when shipping a hallucination filter,
write *honest refusal* test cases alongside the
hallucination test cases. The two outcomes look identical
to a substring matcher — both produce text that the
matcher labels "unsupported." The filter is supposed to
penalize the first and pass the second; failing to
distinguish them inverts the slice's purpose. **For this
operator specifically**: maintain a curated set of
honest-refusal prompts that should always pass the
verifier; treat any change to the verifier stack as
gated on those staying green.

### 2. Live dogfood found what unit tests couldn't

The K6.5 unit tests use a hand-crafted hallucination
payload (Donny's exact SESSION 158 script) as the
LLM-output fixture. They never see what the model
actually produces under real load. The live dogfood —
real OpenAI key, real `gpt-5-mini` Responses call, real
chunks — surfaced the honest-refusal class within three
prompts. Unit tests would have shipped K6.5 with the
bug latent. SESSION 158 had already taught this lesson
once; the slice's test design didn't yet incorporate it
because the K6.4 path under test always assumed the LLM
hallucinates (which is what the test fixture forces).

**Carry-forward**: when a slice's risk surface is "the
model behaves unexpectedly," at least one live-system
dogfood probe is part of ship gate. Unit tests confirm
the slice handles the *anticipated* inputs; the live
probe confirms it handles the inputs the operator + model
actually produce. For verifiers / classifiers /
guardrails specifically: the **third or fourth real
prompt** is the calibration event the test fixture
can't anticipate.

## Files changed in this commit

* `shell/character_os/conversation_synthesis.py` — verifier hook.
* `shell/character_os/claim_verifier.py` — refusal stoplist.
* `shell/apps/conversations/models.py` — two new fields.
* `shell/apps/conversations/migrations/0003_k6_5_verification_warnings.py` — new.
* `shell/apps/conversations/serializers.py` — exposes new fields.
* `shell/apps/conversations/views.py` — Strict-mode 422 + warn persistence.
* `shell/apps/conversations/tests/test_k6_5_verifier.py` — new (6 tests).
* `shell/apps/compositions/tests/test_claim_verifier.py` — +1 refusal-pattern test.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.5 ship notes.
* `docs/TRUST_CALIBRATION.md` — two new entries (refusal-rejection + live-dogfood-found-it).
* `00-START-NEXT-SESSION.md` — overwritten for SESSION 163.
* `docs/handoffs/SESSION_162_K6_5_CONVERSATION_PARITY.md` —
  this file.

## What's next (SESSION 163)

K6.4 / K6.4.1 / K6.5 close the K-arc's verifier thread.
The remaining queued slices are mostly SPA-facing:

* **K6.4 v1.1 — SPA toggle + warning surface.** Surface
  `verification_warnings` + `rejected_synthesis` on the
  composition detail page; render warnings inline on
  conversation messages; expose Strict/Warn/Off toggle.
  ~1 session.
* **K6.4 v1.2 — `verification_status` field.** Captured
  SESSION 161 as a calibration. Distinguish verified /
  trusted_passthrough / skipped. ~30 minutes.

If neither appeals: more real-Runway exposure, K7.x
YouTube ingest fix, K6.3 brief length cap, K7.1 cost
telemetry, W11.1 edit-spokesperson modal, or anything
else in `00-START-NEXT-SESSION.md`.

---

*Handoff written end-of-SESSION 162. Anchor frontmatter
re-stamped via `context-kit handoff write 162 --project .`.
Strict mode left active in the running Django + Celery for
ongoing operator dogfooding.*
