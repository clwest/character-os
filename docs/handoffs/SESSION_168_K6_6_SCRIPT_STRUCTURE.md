---
title: "Session 168 — K6.6 script structure + opener override + brief persistence"
date: 2026-05-15
status: complete
session: 168
previous_handoff: ./SESSION_167_REAL_RUNWAY_DOGFOOD.md
---

# Session 168 — K6.6 script structure

## TL;DR

Operator-mediated feedback on the SESSION 167 Donny render:
*"Those look really good, but they still need some tweaking,
or clean up on how the conversation is flowing. A couple of
them feel like it's picking up mid conversation and you
don't really know what's going on."*

Diagnosis: K6's system prompt enforced "one clear claim,
one call to action" but had no structural opener guidance.
The model dove in mid-thought — SESSION 167's brief opened
*"I sit with customers and watch the knowledge layer do
its work…"* with no setup.

K6.6 fix, three changes:
1. **Tightened K6 system prompt** with standalone-video
   framing — opener → claim → CTA, "first sentence must
   stand alone, do NOT begin mid-thought."
2. **Opener override** — `talking_head(opener="...")` +
   the 3 sibling recipes. Lets the operator pin the
   first sentence verbatim; K6 writes the rest to follow.
3. **`Composition.synthesized_brief` field** — persists
   what K6 actually said on *successful* renders. Closes
   the SESSION 167 audit gap where operator feedback on
   rendered video quality had no place to land
   (only `rejected_synthesis` survived for strict-mode
   failures).

Live dogfood: 2 real Runway renders at $0.25 each, both
`verification_status=verified`, both with clear
standalone openers — exactly the structural fix the
operator asked for.

Tests: Django **714 → 718** (+4 K6.6 tests).
Migrations: **56 → 57**. SPA build clean.

## What shipped

### Backend — `character_os/script_synthesis.py`

* `_system_prompt` now includes:
  > This is a SHORT STANDALONE VIDEO (60-100 words,
  > about 30-60 seconds). The viewer has not seen
  > anything else from you — there is no prior context.
  > Open with a brief setup that grounds them in who
  > you are and what this video is about (one or two
  > short sentences). Then make your one clear claim
  > or insight from the knowledge chunks. Then one
  > call to action. Do NOT begin mid-thought as if
  > continuing a conversation. The first sentence
  > must stand alone.
* `build_render_brief(..., opener: str | None = None)` —
  new kwarg threads into `_call_responses_api(opener=...)`
  which adds an "Operator-supplied opening line" clause
  to the user prompt when set.

### Backend — `apps/compositions/`

* `Composition.synthesized_brief: TextField` — populated
  by the avatar_speech primitive on `verification_status
  ∈ {verified, skipped}`. Empty on
  `trusted_passthrough` (degraded path; operator's
  prompt flowed through verbatim, nothing to capture).
  Migration `0005_k6_6_synthesized_brief`.
* `_maybe_synthesize_script` reads
  `step.params["opener"]` and threads it into
  `build_render_brief`.
* `talking_head` + `talking_head_with_backdrop` +
  `talking_head_polished` + `long_form_ad` starters all
  grew `opener: str | None = None` kwarg. For
  `long_form_ad` the opener applies only to the FIRST
  chunk (later chunks continue the same script;
  re-opening would be redundant).
* `_OPENER_FIELD` recipe template — text input,
  optional, max 240 chars. Added to all 4 K6-aware
  recipes. Auto-renders in the metadata-driven form;
  `resolve_kwargs` routes it straight to the starter.
* `CompositionSerializer` exposes `synthesized_brief`.

### SPA

* `web/src/lib/api/recipes.ts` — composition schema
  parses `synthesized_brief` with default empty.
* `web/src/routes/compositions/$id.tsx` — new
  `SynthesizedBriefPanel` section renders the persisted
  brief + word count when non-empty. Sits between the
  verifier panel and the citations panel.

### Tests (+4)

* `test_system_prompt_includes_standalone_video_framing_k6_6`
  — locks the structural-guidance phrasing.
* `test_opener_override_appears_in_user_prompt_k6_6`
  — patches the OpenAI client + verifies the operator
  opening line lands in the user prompt verbatim.
* `test_opener_blank_does_not_appear_in_user_prompt_k6_6`
  — None / whitespace opener doesn't add the clause.
* `test_synthesized_brief_persists_on_successful_warn_render_k6_6`
  — composition.synthesized_brief is set after a
  Warn-mode successful render.

## Live dogfood — side-by-side comparison

Two real Runway renders, $0.25 each, both strict-mode:

### PROBE 1 (no opener, new framing)

**K6 synthesized brief:**
> I'm Donny, and today I'll quickly explain how the
> knowledge layer ingests pages. Pages are broken into
> chunks—fixed-length with overlap, syntax-based, or by
> file-format—then converted into embeddings and stored
> in a vector database. A retriever finds the most
> relevant documents, sometimes using hybrid text plus
> vector search; those results are fed into the LLM via
> prompt engineering so the model can augment its
> answer. Systems may add re-ranking or context
> selection, but can still misinterpret retrieved data.
> Want your pages ingested? Get in touch and we'll walk
> it through.

Compare to SESSION 167's cold opener (same prompt):
> I sit with customers and watch the knowledge layer
> do its work: pages get converted into embeddings…

K6.6's framing produced a clean standalone opener that
establishes who's speaking + what the video is about
before diving in.

### PROBE 2 (operator-supplied opener)

**Operator opener:** "Hey, I'm Donny — I've been
sitting with the Character OS team this week."

**K6 synthesized brief:**
> Hey, I'm Donny — I've been sitting with the
> Character OS team this week. The knowledge layer
> ingests pages by converting content into
> embeddings — numerical vectors — often after
> chunking (fixed-length with overlap, syntax- or
> file-aware chunks like whole functions or HTML
> elements). Those vectors live in a vector database;
> a retriever pulls the most relevant documents,
> sometimes combined with traditional text search,
> and feeds that augmented prompt into the LLM to
> generate grounded answers. Want to see your pages
> ingested this way? Reach out and we'll walk
> through it.

Operator opener used verbatim; K6 wrote the rest in
the same voice.

### Strict mode still held

Both renders ended with CTAs (`Want your pages
ingested? Get in touch...` / `Want to see your pages
ingested this way? Reach out...`). The K6.4 v2.1 CTA
stoplist correctly recognized these as
not-real-named-entities. Strict mode passed,
verification_status=verified, both real Runway
clips shipped.

## Calibration moments worth carrying

### 1. Operator feedback on rendered output ≠ feedback on the pipeline

The SESSION 167 dogfood landed a green pipeline: strict
mode worked, verification_status=verified, real Runway
render shipped. By system metrics, success. The operator
watched the actual video and said it sounded like
"picking up mid conversation." That's a *quality* gap
the verifier doesn't see — the rendered text was
factually grounded but rhetorically jarring.

Two distinct failure modes:
* **System failure**: pipeline returns non-2xx, or the
  verifier rejects, or the model hallucinates.
* **Quality failure**: pipeline is green but the
  rendered output doesn't read well.

The K-arc verifier work catches system + hallucination
failures. K6.6 introduces *prompt engineering* for
quality. They live in different layers and need
different feedback loops.

**Carry-forward**: distinguish "the pipeline worked" from
"the output was good." For any AI-output deliverable,
treat them as separate review gates — operator-facing
preview > system metrics. **Generalisation**: ML system
correctness and ML system quality decouple. A green
correctness signal can hide a real quality regression.
The fix is structural (build the quality-review surface
explicitly) not aspirational (just expect operators to
notice).

### 2. Persistence enables retroactive feedback

The SESSION 167 render that motivated this work isn't
recoverable — `synthesized_brief` didn't exist yet, so
when the operator said "picking up mid conversation" we
couldn't go back and look at the specific text. We only
knew it from the rejection paths (`rejected_synthesis`)
where K6 had been blocked, not from the rendered text
that actually shipped.

K6.6's `synthesized_brief` field closes that gap going
forward. Every future composition's actual rendered text
is on the row. Operator can review at any time, give
specific feedback, and the agent can quote the actual
text in calibration entries.

**Carry-forward**: persist the artifact that the
operator might review later, even when "the system
worked." Audit trails are operator-facing, not just
debugging-facing. **Generalisation**: ML pipelines
should persist their generated content alongside their
state transitions. The state alone is necessary but not
sufficient for retroactive operator review.

## Files changed in this commit

* `shell/character_os/script_synthesis.py` — system
  prompt + opener kwarg.
* `shell/apps/compositions/models.py` —
  `synthesized_brief` field.
* `shell/apps/compositions/migrations/0005_k6_6_synthesized_brief.py`
  — new.
* `shell/apps/compositions/primitives/avatar_speech.py`
  — reads opener from step.params; persists brief on
  success.
* `shell/apps/compositions/starters.py` — opener kwarg
  on 4 starters.
* `shell/apps/compositions/recipes.py` — `_OPENER_FIELD`
  template + applied to 4 recipes.
* `shell/apps/compositions/serializers.py` — exposes
  synthesized_brief.
* `shell/apps/compositions/tests/test_claim_verifier.py`
  — +4 K6.6 tests.
* `web/src/lib/api/recipes.ts` — schema.
* `web/src/routes/compositions/$id.tsx` —
  `SynthesizedBriefPanel`.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.6 ship notes.
* `docs/TRUST_CALIBRATION.md` — two new entries.
* `00-START-NEXT-SESSION.md` — overwritten for
  SESSION 169.
* `docs/handoffs/SESSION_168_K6_6_SCRIPT_STRUCTURE.md`
  — this file.

## What's next (SESSION 169)

K-arc verifier + K6 synthesis quality both validated
end-to-end. Open paths:

1. **More real-Runway exposure** —
   `talking_head_polished` (V9 captions + intro/outro)
   for Sasha, or `long_form_ad` smoke. The full v2 +
   K6.6 stack has been proven on `talking_head`; time
   to stress more recipes.
2. **K6.4 v3 — embedding-similarity fallback** for
   paraphrases. Holds until a real paraphrase miss
   surfaces in operator dogfood.
3. **Older backlog** — F8.1 (blocked), K7.x YouTube
   ingest fix, K6.3 brief length cap (15 min), K7.1
   cost telemetry, W11.1 edit-spokesperson modal.

---

*Handoff written end-of-SESSION 168. Anchors re-stamped
via `context-kit handoff write 168`. Two new real
Runway assets shipped at verification_status=verified.
Total cumulative Runway spend across SESSIONS 167-168:
$0.75 (3 verified renders).*
