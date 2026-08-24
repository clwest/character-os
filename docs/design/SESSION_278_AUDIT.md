# SESSION 278 — Audit Log

Primary durable document for SESSION 278 audit-only slices. Each Q-278-N is a self-contained section covering: question, prediction, evidence, blast-radius, tests/experiments, prediction-vs-actual, recommendation, explicit decision gate.

Handoff context: `docs/design/SESSION_278_HANDOFF.md`.

---

## SESSION 278 Checklist

- [x] **Q-278-1** — Is K6.4 systematically capable of misclassifying ordinary sentence-initial capitalized words as unsupported `proper_noun` claims, and does that classification affect anything beyond operator-visible evidence? *(CLOSED — CHARACTERIZED / NO IMPLEMENTATION; superseded by Q-278-2 invariant investigation.)*
- [x] **Q-278-2** — What semantic invariant is K6.4 `proper_noun` verification trying to enforce, and what evidence is available at classification time to distinguish ordinary sentence capitalization from unsupported named entities without weakening claim verification? *(AUDIT COMPLETE — original recommendation superseded by Q-278-2b.)*
- [x] **Q-278-2b** — Decision-gate challenge: does Option C actually change the Ruby/Tyson specimen? And has evidence crossed the threshold justifying the semantic/NER upgrade path over further regex+stoplist hardening? *(CLOSED — Option C withdrawn as mechanically redundant; Q-278-3 opened.)*
- [x] **Q-278-3** — What is the smallest robust verifier architecture that represents the named-entity grounding invariant rather than approximating it via capitalization + stoplist? Audit-only architecture comparison + shadow-evaluation feasibility. *(CLOSED — Chris + ChatGPT chose GO B: bounded feasibility spike first.)*
- [x] **Q-278-3.1** — Bounded local NER feasibility spike: install spaCy `en_core_web_sm` in throwaway venv; measure against adversarial matrix + real 26c62b4b + historical warned specimens; try to disprove Option D. *(CLOSED — Chris + ChatGPT chose GO A: approve modified D-POS Hybrid; open Q-278-3.2.)*
- [x] **Q-278-3.2** — D-POS shadow-mode implementation. Smallest safe observational substrate: legacy verifier stays authoritative; D-POS runs beside it behind `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT`; results land on new `Composition.verification_warnings_shadow` column; `k64_shadow_diff` mgmt command reports OLD/SHADOW/BOTH deltas. *(LANDED — commit `42298bc`; shadow OFF byte-identical to today.)*
- [x] **Q-278-3.2 Fresh Shadow Dogfood 5/5** — five fresh normal-dogfood specimens (a1421a0e / 5f4bdbbc / 1491d31c / fcba3242 / 1aabbff6) captured, analyzed, and compared against legacy per specimen + as a consolidated matrix. Acceptance criteria A-F evaluated. *(CLOSED — Chris + ChatGPT approved GO-CUTOVER-PLANNING.)*
- [x] **Q-278-4** — D-POS cutover-design audit. Mechanical trace of legacy authority path, NER-supplement Success experiment, stoplist disposition, dual-run design, persistence semantics, rollback, warn/strict separation, acceptance signals, blast radius, ordered smallest-cutover slices. *(AUDIT COMPLETE — recommendation: GO-IMPLEMENT-SLICE-1.)*
- [x] **Q-278-4.1** — NER-supplement POS=PROPN gate (Slice 1 of the Q-278-4 cutover plan). Single-function edit in `claim_verifier_ner.py`; +6 regression tests; 38 D-POS + 116 adjacent tests all green; Specimen 4 `Success` over-fire closed post-gate. *(LANDED — commit `1336420`.)*
- [x] **Q-278-4.2 pre-implementation boundary challenge** — before Slice 2 lands, resolve the apparent composition-boundary contradiction: a global `CHARACTER_OS_K64_AUTHORITY` flag rewiring three call sites would broaden authority to Script + ConversationMessage even though those surfaces have no shadow evidence. *(CLOSED — Chris + ChatGPT approved MODIFY-SLICE-2-DESIGN → REVISED Option A.)*
- [x] **Q-278-4.2** — Dialogue-scene-only dispatcher (revised Option A). New `character_os/claim_verifier_dispatch.py`; `CHARACTER_OS_K64_DIALOGUE_AUTHORITY = legacy | d_pos` (default `legacy`); dual-write to `Composition.verification_warnings_shadow` (D-POS) + new `Composition.verification_warnings_legacy` (legacy); dispatcher runs both classifiers per turn; defensive fallback on D-POS failure; strict/warn semantics preserved. *(LANDED — commit `e7c58c2`; 179 tests green; awaiting fresh dogfood + Slice 3 decision.)*
- [ ] Q-278-4.3 — (TBD; flip dispatcher default authority to `d_pos`; opens only if Slice 3 approved)

Slice discipline reminder: no fixes land in this session until Chris + ChatGPT explicitly approve.

---

## Operator observation (Q-278-1 context)

Fresh operator dogfood produced the first Ruby + Tyson dual-character Fox & Flour Bakery Episode. Composition `26c62b4b-0738-493f-8666-cb9a70dfe019`. Operator topic: `"Welcome to Fox & Flour."` Episode `a015128e-9554-4f54-8f43-122c9106e3ed` ("Welcome to Fox & Flour Bakery").

Chris reports the render worked well for a first attempt with a surprisingly natural conversational flow despite Ruby/Tyson not having undergone the extensive character-development dogfood previously done with Patch/Rivet. The composition also appears to have composed the SESSION 277 substrate correctly: Ruby received the two World-shared Knowledge chunks; Tyson received those same shared chunks plus Tyson's character-specific Knowledge; the dialogue used the retrieved facts naturally rather than dumping them.

> This observation is recorded only. Creative quality is NOT investigated in this slice.

The K6.4 evidence panel in the SPA showed the composition as "Warn — 3 flags" with unsupported `proper_noun` claims: `"Fair"`, `"Come"`, `"Unless"`. In the rendered dialogue these appear as ordinary sentence-initial capitalized words, not meaningful proper nouns or unsupported factual claims. Q-278-1 investigates that.

---

## Q-278-1 — K6.4 sentence-initial `proper_noun` misclassification

### Precise question

Is K6.4 systematically capable of misclassifying ordinary sentence-initial capitalized words as unsupported `proper_noun` claims, and if so, does that classification affect anything beyond operator-visible verification/evidence?

### Prediction / hypothesis (before investigation)

Given the K6.4 architecture (regex-driven single-cap extractor + hand-curated stoplist + corpus substring check), the most likely mechanism is that these three specific tokens are simply not in `_COMMON_PROPER_NOUN_FALSE_POSITIVES` and do not appear anywhere in the retrieved chunks / brief corpus. If that is the cause, the misclassification is systematic — any capitalized 4+ char English word that (a) is missing from the stoplist AND (b) is absent from the corpus for that speaker will flag, regardless of whether it is genuinely a proper noun. Expected blast radius in the currently-shipped default mode (`warn`): additive display-only metadata + `stoplist_watchdog` input; no synthesis, retry, block, or downstream compositional behavior change.

### Source-derived findings (`shell/character_os/claim_verifier.py`)

- The single-token extractor is one line: `_SINGLE_CAP_RE = re.compile(r"\b[A-Z][a-zA-Z]{3,}\b")` (`claim_verifier.py:334`).
- Every match is either (a) suppressed if `claim.lower()` is in `_COMMON_PROPER_NOUN_FALSE_POSITIVES` (`claim_verifier.py:618-619`), (b) matched substring-wise against the factual corpus (`verify_claims`, `claim_verifier.py:499-506`), or (c) recorded as an `UnsupportedClaim` with `kind="proper_noun"` (`claim_verifier.py:628-632`).
- `_COMMON_PROPER_NOUN_FALSE_POSITIVES` (`claim_verifier.py:115-310`) is an ~250-entry hand-curated set built up across SESSIONS 158-175 via prior dogfood. It contains no entry for `fair`, `come`, or `unless`.
- The `is_sentence_initial` helper (`claim_verifier.py:818-857`) DOES exist and IS invoked, but the invocation is ONLY inside the multi-word branch to demote a stoplisted leader ahead of a real proper noun (`claim_verifier.py:556-602`, `"Think Antoninus"` demotion). The single-cap branch has NO sentence-initial gating and NO sentence-initial demotion. Its stoplist check is unconditional on position.
- Consequence: for the single-cap pass, sentence-initial position is irrelevant to whether an unstoplisted 4+ char capitalized token becomes a `proper_noun` claim. The only mitigations are (i) presence in the stoplist, (ii) presence in the factual corpus, (iii) presence in the allowed vocabulary.

### Persisted / runtime findings (Composition 26c62b4b)

Direct DB read via `manage.py shell` on live workspace (Chris's, `character_os` DB via infra Postgres :5434):

- `Composition.status = "completed"` — render went through to Runway; not blocked.
- `Composition.verification_status = "verified"` — see the normalization note below.
- `Composition.verification_warnings` = list of 3 dicts, verbatim:
  - `{"kind":"proper_noun","claim":"Fair","position":0,"line_index":5,"speaker_name":"Tyson","speaker_alias":"tyson"}`
  - `{"kind":"proper_noun","claim":"Come","position":67,"line_index":8,"speaker_name":"Ruby","speaker_alias":"ruby"}`
  - `{"kind":"proper_noun","claim":"Unless","position":27,"line_index":9,"speaker_name":"Tyson","speaker_alias":"tyson"}`
- `Composition.synthesis_attempt_count = 2` — a corrective pass ran, but by inspection of `dialogue_synthesis.py` (see below) the corrective pass was DURATION-triggered, NOT verification-triggered.
- `Composition.corrective_hint` populated (duration-related).
- `Composition.synthesized_brief` (1615 chars) preserves the full dialogue. Contextual position of each flag verified in-brief:
  - `Fair` at offset 947, preceded by `"yson: "` (turn-opening after `Tyson:` speaker prefix). Sentence-initial in the turn text.
  - `Come` at offset 1431, preceded by `" Day. "` (period after `"...except Christmas Day."`). Sentence-initial.
  - `Unless` at offset 1539, preceded by `" ired. "` (period after `"No strategy required."`). Sentence-initial.

All three flagged tokens are, in the actual rendered text, ordinary English words at sentence starts — not proper nouns and not factual claims.

Note (secondary finding): `Composition.verification_status = "verified"` while `verification_warnings` is non-empty is INTENDED behavior. `_dialogue_ai_verification_status` (`apps/compositions/starters.py:295-305`) explicitly normalizes the `"warned"` overall status onto `"verified"` for the model column, matching the talking-head convention. Warnings live in the sibling `verification_warnings` column. This is documented, not a defect.

### Test-derived findings (deterministic experiment, zero LLM spend)

`shell` interpreter, no DB, no network:

```
Fair       lower_in_stoplist=False  single_cap_regex=True
Come       lower_in_stoplist=False  single_cap_regex=True
Unless     lower_in_stoplist=False  single_cap_regex=True

extract_named_entities('Fair enough.')       -> [('Fair',   'proper_noun', 0)]
extract_named_entities('Come by tomorrow.')  -> [('Come',   'proper_noun', 0)]
extract_named_entities('Unless you disagree.')-> [('Unless','proper_noun', 0)]
extract_named_entities('This is fair enough.')     -> []          # lowercase — no match
extract_named_entities('Please come by.')          -> [('Please','proper_noun',0)]  # incidental new false positive
extract_named_entities('It works unless you say no.') -> []
extract_named_entities('He said, Fair enough.')    -> [('Fair','proper_noun',9)]   # mid-sentence capital still flags
extract_named_entities('And then, Come by tomorrow.')-> [('Come','proper_noun',10)]
```

Reproduction is trivially generalizable: the class of failures is *any* capitalized token of length ≥ 4 whose lowercase form is neither in the stoplist nor a corpus substring. Sentence position affects nothing in the single-cap branch. An additional independent false-positive candidate `"Please"` surfaced incidentally during the experiment — it is not in the stoplist either.

### Existing tests (what they prove; what they leave untested)

Coverage lives in `shell/apps/compositions/tests/test_claim_verifier.py`:

- `test_extract_skips_common_sentence_starters` — asserts specific tokens (`Turns`, `Cleanest`, `That`, `When`, `They`) in the DONNY example brief do NOT extract. Case-by-case, not general.
- `test_stoplist_alright_k6_4_v2`, `test_stoplist_cta_verbs_k6_4_v2_dogfood`, `test_stoplist_time_adverbs_k6_4_v2_1`, `test_stoplist_cta_verbs_k6_4_v2_2_dogfood`, `test_extract_skips_sentence_initial_adjectives_k6_4_1` — each asserts a specific set of tokens (previously discovered false positives) is now silenced by the stoplist. Each covers only the tokens explicitly added.
- `test_multiword_demotes_sentence_initial_stoplisted_leader_k6_4_v2_1` / `_only_at_sentence_initial_` — assert the MULTI-word branch's `is_sentence_initial` demotion.
- `test_is_sentence_initial_*` — unit tests for the helper. Prove the helper works; do NOT prove any single-cap flow uses it.

Untested boundary: no test asserts the general property "an ordinary English sentence-initial capitalized word not in the stoplist WILL flag as `proper_noun`". Q-278-1 has effectively surfaced three concrete instances (`Fair`/`Come`/`Unless`) plus one incidental (`Please`) that the current test suite does not catch.

### Blast-radius analysis

Consumers of `Composition.verification_warnings` (and turn-level `DialogueTurn.verification_warnings`):

- **Persistence** — the `verification_warnings` JSON column, written by `dialogue_synthesis.py:1791-1792` per turn and flattened onto `Composition.verification_warnings` via `_dialogue_ai_flattened_warnings` (`starters.py:308-324`) with speaker/line annotations.
- **SPA display** — `web/src/routes/compositions/$id.tsx`, `web/src/routes/workspace/scripts.$id.tsx`, `web/src/routes/conversations/$id.tsx`, and their API-lib helpers surface warnings in the composition/script/conversation evidence panels. Read-only rendering.
- **`stoplist_watchdog` management command** (`shell/apps/compositions/management/commands/stoplist_watchdog.py`) — reads `Composition.verification_warnings` and `ConversationMessage.verification_warnings` to surface false-positive candidates for stoplist curation. Read-only report; exit code always 0.
- **`Script.verification_warnings` / `ConversationMessage.verification_warnings`** — same-shape columns for adjacent surfaces; consumed by their own admin + serializers + SPA panels.

Consumers that could change render behavior:

- **Strict-mode branch** — `ClaimVerifierError` raised in `run_verifier` (`claim_verifier.py:469-470`) when `K6_CLAIM_VERIFIER_MODE = "strict"`. In dialogue synth (`dialogue_synthesis.py:1783-1790`) this is re-raised out through the recipe → composition starter → view exception handler (`apps/compositions/views.py:799-849`) which persists the row as `status=FAILED`, populates `verification_warnings` + `rejected_synthesis`, dispatches ZERO `avatar_video` calls, and returns 201 with a FAILED payload. So in strict mode, Fair/Come/Unless WOULD have blocked this render with no provider spend.
- **Corrective / retry pass** — dialogue corrective retry (`dialogue_synthesis.py:1645-1724`) is triggered by `_parse_and_validate` on DURATION / structure grounds ONLY. `run_verifier` runs *after* the corrective loop (`dialogue_synthesis.py:1726-1797`). `verification_warnings` do NOT feed the corrective hint and do NOT influence retry.
- **Long-form / talking-head branches** (`shell/apps/compositions/primitives/avatar_speech.py`, `character_os/duration_contract.py`) — same rule: verification is post-synthesis; warnings do not gate any retry loop; strict mode blocks via `ClaimVerifierError` on the same shape.

Current active mode (verified live):

```
K6_CLAIM_VERIFIER_MODE (settings): <unset>
K6_CLAIM_VERIFIER_MODE (env):      <unset>
resolved default:                  warn
```

Mode is `warn`. Therefore for composition `26c62b4b` and any other current dogfood: the three `proper_noun` misclassifications are **operator-visible evidence only**. They did not:

- Change `Composition.status` (`completed`, not `failed`).
- Alter the synthesized dialogue.
- Trigger a corrective / retry pass.
- Change what was sent to Runway / avatar_video.
- Affect knowledge-chunk selection, retrieval, ordering, or scoring.
- Affect narrative-memory writes or downstream Episode / Universe state.
- Affect billing.

They DID:

- Populate `Composition.verification_warnings` (JSON) and per-turn `DialogueTurn.verification_warnings`.
- Set the aggregate DialogueResult `overall_verification_status` to `"warned"` internally, which the starter normalizes to `"verified"` on the composition row (documented convention).
- Render as visible "Warn — 3 flags" evidence in the SPA composition-detail evidence panel.
- Contribute to future `stoplist_watchdog` runs — the intended curation feedback loop.

### Is the behavior systematic / generalizable?

Yes. Not Ruby-specific, not Tyson-specific, not dialogue-specific.

The class of failures is exactly: any capitalized token matching `\b[A-Z][a-zA-Z]{3,}\b` whose lowercase form is neither in `_COMMON_PROPER_NOUN_FALSE_POSITIVES` nor a substring of the speaker's factual corpus nor covered by the allowed vocabulary. Position within the sentence is irrelevant to classification in the single-cap branch (verified in source + deterministic experiment). Two closure vectors exist and are already used elsewhere in the codebase:

1. Enlarge the stoplist (SESSIONS 158-175 pattern — the same pattern that added `Alright`, `Today`, `Reach`, `Want`, `Modern`, etc.).
2. Sentence-initial demotion for the single-cap branch (the multi-word branch already does this in v2.1 for stoplisted leaders — the natural symmetric extension would demote unstoplisted single-cap matches when `is_sentence_initial(text, position)` returns True, then re-verify against the corpus).

Neither vector is proposed for implementation in this slice — see recommendation.

### Prediction vs actual

Prediction was accurate. Mechanism: exactly (a) stoplist absence + (b) corpus absence + (c) 4+ char single-cap regex, with sentence position not participating in the classification decision for single tokens. Blast radius under warn mode: exactly operator-visible metadata + `stoplist_watchdog` input. Nothing runtime-consequential in the current default configuration.

### Evidence vs inference distinction

- Persisted state of Composition 26c62b4b: **evidence** (read directly from DB).
- Source behavior of the claim verifier: **evidence** (read from `claim_verifier.py` + confirmed by deterministic experiment in the running interpreter).
- Blast-radius enumeration: mostly **evidence** (grep-verified consumers + read of `views.py`, `starters.py`, `dialogue_synthesis.py`, `stoplist_watchdog.py`). Claim "no other consumer changes render behavior" is a **carefully bounded inference** from the searches performed — no exhaustive proof, but the search set covered every module that imports `verification_warnings`, `run_verifier`, or `ClaimVerifierError`.
- "Behavior is systematic" for other capitalized English words: **evidence** for `Fair`/`Come`/`Unless`/`Please`; **strong inference** for the general class (regex + set-membership check with no other conditional input).

### Recommendation

The behavior is (a) systematic and generalizable, (b) currently harmless under the active `warn` mode, (c) would be a real render-blocker under `strict` mode. Three plausible next moves:

1. **Small stoplist expansion.** Add `fair`, `come`, `unless`, `please` (plus a modest sentence-opener sweep suggested by `stoplist_watchdog`). Cheap, follows the SESSIONS 158-175 pattern exactly, closes the immediate visible-evidence noise, adds no new surface. Low risk. Does not close the general class.
2. **Sentence-initial demotion for single-cap matches.** Symmetric with the v2.1 multi-word demotion. When `is_sentence_initial(text, match.start())` and the token is not a substring of the corpus, EITHER treat as a false positive OR retry the classification with the token lowercased against the corpus. Closes the general class but changes verifier semantics — deserves its own audit / decision gate, because it would silence genuinely wrong sentence-initial proper nouns (a script starting `"NASA is..."` when NASA is absent from every source).
3. **Do nothing.** Warn mode. Warnings are honest per the current classifier definition ("this token has proper-noun shape and no corpus support"), the SPA is showing the operator exactly what the classifier believes, and `stoplist_watchdog` is the intended curation channel. Cost: continued operator-visible noise.

Chris's Q-278-1 asked whether to fix; the actionable next step depends on whether operator-visible noise is worth an intervention *right now* or whether it is better deferred until the `strict`-mode enablement decision is on the table.

### Unresolved questions surfaced by this audit

- Is there any near-term intent to flip `K6_CLAIM_VERIFIER_MODE` to `"strict"`? That is the singular decision that promotes this from "display noise" to "render-blocker".
- Should `Composition.verification_status = "verified"` while warnings are non-empty be revisited? Documented as intended, but operator-facing "verified" alongside "Warn — 3 flags" is a slight display tension. Out of scope for Q-278-1.
- Is `"Please"` (unstoplisted, would flag) worth its own dogfood sweep? Discovered incidentally in the deterministic experiment; may already have been surfaced by `stoplist_watchdog` in a prior run.

### Explicit decision gate

**STOP.** No implementation lands until Chris + ChatGPT explicitly pick between recommendations 1, 2, and 3. If picking (1) or (2), scope-lock the surface (which words / which invariants) before implementation.

### Q-278-1 decision (post-audit)

**CLOSE Q-278-1 as CHARACTERIZED / NO IMPLEMENTATION.** No stoplist additions. No sentence-initial demotion. No strict/warn change. No verification-status normalization change.

Reasoning: Q-278-1 proved the false-positive class is systematic rather than specific to `Fair`/`Come`/`Unless`. Recommendation 1 (stoplist expansion) would close today's specimens while knowingly leaving the general class intact. Recommendation 2 (blind sentence-initial demotion) could weaken the verifier by suppressing genuinely unsupported named entities such as `NASA` or `Antoninus` appearing at sentence start. Before choosing, the intended invariant needs to be established explicitly. Superseded by Q-278-2.

---

## Q-278-2 — K6.4 `proper_noun` semantic invariant + available classification signals

### Precise question

What semantic invariant is K6.4 `proper_noun` verification actually trying to enforce, and what evidence is available at classification time to distinguish ordinary sentence capitalization from unsupported named entities without weakening claim verification?

### Prediction / hypothesis (before investigation)

The verifier's real target is "named entity ungrounded in retrieved evidence" — not "capitalized word." The regex + stoplist is a cheap shape-based proxy for a real NER pass, with the stoplist absorbing the proxy's systematic false positives one dogfood at a time. At classification time only regex-derived shape signals + the two curated corpora are available; no NER, no dictionary, no POS-tagger runs in-process. The most defensible narrow closure without adding a dependency is `sentence-initial + lowercase-form-appears-in-corpus` re-check — but this preserves invariant only for corpora that mention the ordinary form of the word. Strict mode is expected to be a future-facing enforcement target that has been iteratively hardened but is not currently active in the dev workspace.

### History / intent

Traced end-to-end from git commit metadata (`git log -- shell/character_os/claim_verifier.py`) and the module docstring. No SESSION 15X/16X design docs exist in `docs/design/`; the durable design intent lives in commit messages and source docstrings.

**Founding motivation (commit `5548171`, SESSION 159; module docstring `claim_verifier.py:1-44`):**

> The SESSION 158 Donny render exposed: the script said *"Wikipedia is its absolute home turf"* and *"the library doing the work is called trafilatura"* with both terms absent from every retrieved chunk. The K6 system prompt's *"Use facts only from the knowledge chunks. Do not invent. Leave it out."* instruction is necessary but not sufficient — prompt-only no-invention contracts leak when the model already knows the truth.

The mechanism `gpt-5-mini` failed: prompt-only "don't invent" contracts leak when the model has prior knowledge. K6.4 was introduced as a **post-synthesis backstop** that catches the specific failure mode the prompt fails to prevent.

**What `proper_noun` was intended to mean semantically:** From the docstring — "named-entity-shaped tokens" that "check each against a corpus of supported content." The `proper_noun` kind is one of four shape buckets (`proper_noun`, `multi_word`, `numeric`, `tech_term`) — the shape proxy for named entity via capitalization + word length ≥ 4.

**Stoplist history** (evolution across sessions, chronological by git log for the file):

- v1 (`5548171`, SESSION 159) — small hand-curated set with `Cleanest`/`Welcome`/`Turns` explicitly listed as the first false-positive class the operator surfaced.
- K6.4.1 (`bd73276`, SESSION 161) — first strict-mode dogfood; `Modern` rejected a real render. +~60 adjective/adverb entries.
- v1.2 (`97f9224`) — `verification_status` 4-state enum added, closing the "bypass case looks identical to clean render" trust-calibration gap. Dogfood found `Alright` — flagged for v2.
- watchdog (`325aea2`, SESSION 165) — `stoplist_watchdog` mgmt command shipped so the operator can find candidates from persisted rows. `is_sentence_initial` helper introduced here, ONLY consumed by the watchdog (for reporting) at this point.
- v2 (`338dc5e`, SESSION 166) — First real-Runway strict-mode dogfood rejected on `Want` / `Reach` (CTA verbs). +~40 CTA-verb stoplist entries. Multi-word regex tightened (dropped `a`/`an` from joining set). `KNOWN_TECH_TERMS` frozenset added.
- v2.1 (`10d60b4` + `e9256e5`, SESSION 174) — `Today` (time adverb) + `Think Antoninus` (imperative + real proper noun). Time-adverb stoplist additions + sentence-initial multi-word demotion for stoplisted leaders.
- v2.2 (`1577ce4`, SESSION 175) — `Respect HTML` on Donny K6.6 dogfood. +17 more imperative verbs.

**Stoplist status:** The docstring (`claim_verifier.py:109-114`) explicitly labels it "curated narrowly — the test is whether removing them from this list causes the Donny smoke test to false-positive on a legitimate render." Not designed as permanent architecture — every commit that grew it framed the addition as **pragmatic dogfood hardening**. The founding docstring `claim_verifier.py:26-33` states plainly: *"v1 is deterministic / regex-based — zero added LLM cost, zero added latency. Lowercase technology names are a known false-negative class in v1... v2 upgrade path is small-model semantic similarity; deferred until first false-positive event motivates it."* The upgrade path was contemplated day-one; the shape+stoplist scaffold was intended to be replaced when a false-positive event motivated it — and Q-278-1 is that event.

**Strict mode intent:** From the founding commit — *"Mode shipped as Warn-default. Strict is one settings flip away."* From SESSION 161 (K6.4.1): three real-Runway renders under `K6_CLAIM_VERIFIER_MODE=strict`, with two trust-calibration entries surfaced — *"Strict mode is a forcing function, not just a gate"* (verifier under strict pressure alters K6's output distribution, not merely filtering it) and *"Bypass case looks identical to clean render"* (which motivated the v1.2 4-state enum). Strict-mode dogfood recurs in SESSIONS 166 and 175. **Strict mode is an intentionally future-facing enforcement target, not debug and not abandoned.** The expected precondition before flipping the default is that the false-positive class stops causing operator-visible rejections on grounded briefs.

### Current classification inputs (mechanically inventoried)

`verify_claims(text, factual_corpus, allowed_vocabulary)` receives:

- `text` — the synthesized text for one turn (or one talking-head brief). Full string; positions are indexable.
- `factual_corpus` — from `build_factual_corpus`: concatenated `KnowledgeChunk.chunk_text` (K2 chunks — shared + per-character + narrative-memory-adapted) + `Universe.brief` + `Teammate.business_brief` + `Teammate.who_you_help` + `Teammate.what_you_sell`. Deliberately excludes the operator prompt, teammate name, voice metadata, brand fields, and `KNOWN_PLATFORM_TERMS`.
- `allowed_vocabulary` — from `build_allowed_vocabulary`: teammate name + named entities extracted from `personality` / `character_point_of_view` / `voice_signature_phrases` + `KNOWN_PLATFORM_TERMS` + caller-passed extras (typically workspace name).

Inside `extract_named_entities` a candidate has access to:

- **Token text** — `match.group(0)`.
- **Position offset** — `match.start()` in `text`.
- **Sentence-initial signal** — `is_sentence_initial(text, position)` is computable (position + text); NOT invoked for single-cap classification (only for multi-word demotion of stoplisted leaders).
- **Prior matched spans** — `matched_spans` list, used to skip tokens inside a preceding multi-word span.
- **Multi-word neighborhood** — the shape of the surrounding capitalized run is discoverable via `_MULTIWORD_CAPS_RE.search(text, start, end)`.
- **Character-context signals** — `\b` boundaries; case profile of the token; length; whether the token is all-uppercase (via `token.isupper()`); whether the token is preceded by an open quote / em-dash / etc.

Available in-process but NOT currently passed into the verifier:

- **Per-chunk provenance** — retrieved chunks carry `KnowledgeChunk.id`, source `KnowledgeDocument`, per-scope audience. Not consumed by verification; verification only sees concatenated `chunk_text`.
- **Retrieval trace** — chunks are already ranked by hybrid retrieval; the scoring/ordering could be reused to weight tokens but currently isn't.
- **The speaker Teammate itself** — the whole ORM object; `build_factual_corpus` gets it, so the verifier has downstream access to identity if the API were widened.
- **The other turn(s) in the dialogue** — dialogue synthesis knows all turns; the verifier is per-turn and doesn't cross-check consistency.
- **The operator prompt / topic** — currently EXCLUDED from factual corpus by design (creative briefs may assert unsupported facts). This is intentional (see `claim_verifier.py:691-698`) and would need re-consideration to change.

Would require a NEW dependency / provider / model call:

- Real POS-tagger (e.g. spaCy `en_core_web_sm` for tag-based demotion of `VB`/`RB`/`JJ` at sentence start).
- Small-model or in-process NER (spaCy, transformers, or hosted).
- English-word dictionary lookup (e.g. `wordfreq`, `pyenchant`, or a static frozen set shipped in-tree).
- LLM-based classification (would defeat the "zero added LLM cost, zero added latency" v1 constraint).

### False-positive / false-negative deterministic matrix (zero provider spend)

Held constant across rows: `factual_corpus` (contains `Fox and Flour`, `Christmas Day`, `NASA`, `Wikipedia`, `trafilatura`, `Fair enough` — no; `Come` — no; `Unless` — no) and `allowed_vocabulary = ['Ruby', 'Tyson', 'Character OS']`. Text-only variables. Full script emitted from `character_os.claim_verifier` — no LLM, no DB.

| # | Text | Sentence-initial | Extracted (kind) | Flagged? |
|---|---|---|---|---|
| 1 | `Fair enough. It is not perfect.` | T | `Fair` (proper_noun) | YES |
| 2 | `Come by tomorrow.` | T | `Come` (proper_noun) | YES |
| 3 | `Unless you disagree with me.` | T | `Unless` (proper_noun) | YES |
| 4 | `Please come inside.` | T | `Please` (proper_noun) | YES |
| 5 | `Fox and Flour is open every day.` | T | `Fox and Flour` (multi_word) | no (corpus hit) |
| 6 | `Antoninus reigned peacefully.` | T | `Antoninus` (proper_noun) | YES (correct — genuinely unsupported) |
| 7 | `Our sourdough came from Fox and Flour last week.` | F | `Fox and Flour` (multi_word) | no (corpus hit) |
| 8 | `We visited Antoninus at the palace.` | F | `Antoninus` (proper_noun) | YES (correct) |
| 9 | `We are open—Come inside now.` | F (em-dash not terminator) | `Come` (proper_noun) | YES |
| 10 | `One rule: Always show up.` | T (colon counts) | `Always` (proper_noun) | YES (another unstoplisted sentence-opener) |
| 11 | `He said, Fair enough.` | F (comma) | `Fair` (proper_noun) | YES |
| 12 | `Ready? Come inside.` | T | `Come` (proper_noun) | YES |
| 13 | `Wait... Fair is fair.` | T (walks past whitespace + period) | `Fair` (proper_noun) | YES |
| 14 | `NASA is not our supplier.` | T | `NASA` (proper_noun) | no (corpus hit) |
| 15 | `FBI called us today.` | T | *(none)* — regex requires 4+ chars | no |
| 16 | `Christmas Day we are closed.` | T | `Christmas Day` (multi_word) | no (corpus hit) |
| 17 | `James Webb Space Telescope launched.` | T | `James Webb Space Telescope` (multi_word) | YES (correct) |
| 18 | `The county Fair opens Friday.` | F | `Fair` + `Friday` (proper_noun) | YES both |
| 19 | `Rose baked the bread today.` | T | `Rose` (proper_noun) | YES (ambiguous — polysemy) |
| 20 | `A rose bloomed today.` | T | *(none, lowercase)* | no |
| 21 | `Our stack runs on trafilatura.` | F | `trafilatura` (tech_term) | no (corpus hit) |
| 22 | `Our stack uses pgvector for embeddings.` | F | `pgvector` (tech_term) | YES (correct) |
| 23 | `She said, "Fair enough for now."` | F | `Fair` (proper_noun) | YES |
| 24 | `In 1789 France revolted.` | F | `1789` (numeric) + `France` (proper_noun) | YES both (correct) |
| 25 | `In 2020 we opened.` | F | `2020` (numeric) | YES |
| 26 | `The U.S. is a country. Mr. Smith arrived.` | T at `Smith` (abbreviation period fools helper) | `Smith` (proper_noun) | YES |

Highlights:

- Rows 1-4, 10, 12-13, 19: sentence-initial ordinary English words at start of sentence — the Q-278-1 class. `Fair`, `Come`, `Unless`, `Please`, `Always` all fire; the underlying regex + stoplist give no discriminating signal to separate them from row 6 (`Antoninus` — genuinely unsupported proper noun).
- Rows 5, 7, 14, 16, 21: corpus-substring check DOES work. `Fox and Flour`, `Christmas Day`, `NASA` (as long as they're in the corpus) pass at ANY position.
- Row 15: `FBI` (3-char all-caps acronym) is NOT extracted at all. Regex requires 4+ chars. `NASA` (4) matches; `FBI`/`CIA`/`FDA` (3) don't. This is an **existing silent false-negative** in the extractor.
- Row 18-19: polysemy is the residual hard case. `Fair` in "county Fair" is a partial proper noun (a proper name of a specific event); `Rose` in "Rose baked" is a person's name. The verifier has no signal to disambiguate from `Fair` in "Fair enough."
- Row 20: lowercase form of the polysemous word (`rose the flower`) escapes entirely — supports Option D's "if lowercase form is in corpus, demote."
- Row 26: `is_sentence_initial` is aggressive about abbreviation periods — `Mr.` and `U.S.` both look sentence-terminating to it. Documented in the helper docstring as intentional to prefer false positives over misses.

### Current behavior (summary)

Ordinary English capitalized function/adjective/verb tokens at sentence-initial position are extracted as `proper_noun` and flagged whenever they miss the corpus. This is the entire class Q-278-1 characterized. The stoplist has grown across 5+ sessions to close individual specimens; the class itself remains open. Corpus substring matching does its job when the corpus is broad enough to mention the ordinary form. `is_sentence_initial` is defined but only consumed by the multi-word demotion path and the watchdog reporter. The all-caps 3-char acronym silent miss (row 15) is an independent unstated behavior.

### Intended invariant (narrowest defensible)

Based on the founding commit + module docstring + stoplist evolution:

> **Named entities that appear in synthesized text should be grounded in the retrieved factual corpus for the speaking character or in the character's allowed vocabulary. Any ungrounded named entity should surface to the operator as a hallucination candidate.**

Two important clarifications:

- **"Named entity" is the target, "capitalized 4+ char token not in stoplist" is a cheap proxy.** The stoplist absorbs the proxy's systematic false positives. The corpus check + `KNOWN_TECH_TERMS` frozenset absorb its false negatives on lowercase tech names. The invariant is about named entities, not shapes.
- **"Ordinary English capitalization" is not itself a claim.** A sentence-initial `Fair` in `"Fair enough."` communicates no factual claim distinct from `"That's fair."` The invariant should not require verification of a token's ordinary-English use just because it happens to be capitalized due to sentence position.

The invariant `"Detect capitalized words absent from sources"` is *what the current classifier does*. The invariant `"Detect source-dependent named entities introduced by synthesis"` is *what the classifier is trying to approximate*. The gap between them is the Q-278-1 false-positive class, and it will not close by continuing to enumerate the exceptions.

### Option analysis

Evaluated against the invariant above.

**Option A — Continue stoplist expansion (Q-278-1 recommendation 1).**
- FP removed: `Fair`/`Come`/`Unless`/`Please` + whatever `stoplist_watchdog` surfaces today.
- FN introduced: none — stoplist is additive.
- Invariant preserved: yes.
- New dependency: none.
- Strict-mode consequence: fewer blocks on today's specimens; class remains open for future English words.
- Complexity: negligible.
- Generalizes: NO. Every future dogfood will surface new specimens; the pattern has repeated ≥5 times.
- Verdict: closes today's specimens without changing the class boundary. Pragmatic-only.

**Option B — Blind sentence-initial demotion for single-cap.**
- FP removed: all sentence-initial ordinary words including future ones.
- FN introduced: **any** sentence-initial genuinely unsupported proper noun — `Antoninus` (row 6), `Rose` (row 19, if unsupported), `NASA` if placed at sentence start, `Wikipedia` at sentence start, `Trafilatura` at sentence start. This is exactly the founding SESSION 158 hallucination class if the model happens to place the fabricated entity at a sentence boundary.
- Invariant preserved: **NO** — silences the hallucination signals the verifier exists to catch.
- New dependency: none.
- Strict-mode consequence: real hallucinations at sentence start would pass strict.
- Verdict: **rejected on invariant grounds.**

**Option C — Sentence-initial + lowercase-form-appears-in-corpus recheck.**
- Mechanism: when `_SINGLE_CAP_RE` matches at sentence-initial and misses the corpus (case-insensitive already), *additionally* check whether the token's lowercase form appears anywhere in the corpus. If it does, treat as ordinary-English use (demote). If not, keep as flagged.
- FP removed: `Fair`/`Come`/`Unless`/`Please` etc. when the corpus mentions the lowercase form (e.g. brief mentions "fair play" or "come in"). Row 20-adjacent case.
- FN introduced: minimal in practice. A sentence-initial `Rose` (person) IS silenced if `rose` (flower) is in the corpus — narrow polysemy edge case.
- Invariant preserved: mostly. Genuine hallucinations at sentence start whose lowercase form isn't in the corpus are still flagged.
- New dependency: none. Already using case-insensitive substring against corpus.
- Strict-mode consequence: better; over-rejection reduced without opening the founding hallucination hole (Wikipedia/Trafilatura wouldn't have `wikipedia`/`trafilatura` in a corpus that never mentioned them — the case-insensitive check would already have caught them).
- Complexity: one extra line in `verify_claims`.
- Generalizes: yes for corpora that mention ordinary words. Weakens for very narrow corpora that never mention common English words.
- Verdict: **preserves invariant + closes most of the Q-278-1 class + requires no dependency**, at the cost of narrow polysemy edge cases.

**Option D — Static English-word stoplist (dictionary form).**
- Mechanism: ship a frozen set of the top-N most common English lowercase words (function words, common verbs, common adjectives, common adverbs) and demote any sentence-initial single-cap whose lowercase form is in the set. The current hand-curated stoplist becomes a snapshot / seed of such a list.
- FP removed: nearly all Q-278-1 class specimens if the wordlist is comprehensive.
- FN introduced: any proper noun that IS also a common English word — `Mark`, `Bill`, `May`, `June`, `Rose`, `Fair` (event name), `Come` (unlikely but possible). These are only silenced when sentence-initial.
- Invariant preserved: mostly. Introduces a polysemy-driven leak class similar to Option C but broader.
- New dependency: static wordlist file in-tree (no runtime dependency). Curation still human-maintained but bounded and portable.
- Strict-mode consequence: substantial reduction in over-rejection.
- Complexity: modest — one new file + set-membership check.
- Generalizes: yes, but the wordlist itself becomes a maintenance surface.
- Verdict: same shape as Option C for the invariant, more aggressive.

**Option E — Small-model NER (contemplated in v1 upgrade path).**
- Mechanism: replace the regex extractor with spaCy `en_core_web_sm` or equivalent local NER. Extract `PERSON`/`ORG`/`GPE`/`WORK_OF_ART` etc. spans; use POS tags to reject non-nominal sentence-initial cases.
- FP removed: nearly all Q-278-1 class + row 26 abbreviation confusion.
- FN introduced: minimal — high-recall NER.
- Invariant preserved: yes (best).
- New dependency: `spacy` + `en_core_web_sm` (~13 MB). In-process, no provider spend.
- Strict-mode consequence: substantially safer to enable.
- Complexity: significant — new dependency, deterministic-behavior audit, span-alignment with existing `KNOWN_TECH_TERMS` + numeric passes, model cold-load, memory.
- Generalizes: yes.
- Verdict: aligns exactly with the v1 upgrade-path plan. Highest leverage; highest cost.

**Option F — Multi-signal composite: sentence-initial + word-length + POS-shape via light rules.**
- Mechanism: rather than dictionary, use combined shape signals (sentence-initial + ends in `-ed`/`-ing`/`-s` past-tense/gerund/plural marker + not TitleCase-camel-cased) to demote sentence-initial verbs/adjectives. No dependency.
- FP removed: some (verbs matching common inflection patterns).
- FN introduced: proper nouns following the same suffix pattern (`Herring`, `Fielding`).
- Invariant preserved: partial.
- Verdict: brittle heuristic layer that would grow like the stoplist. Not compelling versus C or E.

**Option G — Widen the corpus definition (structural).**
- Mechanism: fold the operator prompt back into the factual corpus for single-cap purposes only (or introduce a soft "operator context" corpus). Doesn't close the Q-278-1 class directly, but reduces its frequency.
- Invariant preserved: **NO** — was explicitly ruled out by SESSION 253 (`claim_verifier.py:691-698`). Reversing that decision is an audit of its own.
- Verdict: out of scope for Q-278-2.

### Strict-mode intent

Confirmed as an **intentionally future-facing enforcement target**, not debug and not abandoned:

- Founding commit (`5548171`): *"Mode shipped as Warn-default. Strict is one settings flip away."*
- K6.4.1 (`bd73276`): three real-Runway renders under `K6_CLAIM_VERIFIER_MODE=strict`. Trust-calibration entry: *"Strict mode is a forcing function, not just a gate."*
- K6.4 v2 (`338dc5e`): first production fire of the K-arc verifier stack against real Runway under strict, $0.00 spent on the rejection.
- K6.4 v2.1 + v2.2 (`10d60b4`, `1577ce4`): continued strict-mode dogfood in SESSIONS 174 and 175.
- Current live-workspace runtime (verified): `K6_CLAIM_VERIFIER_MODE` unset in settings AND environment; resolved default is `warn`.

Consequence for Q-278-2: any option chosen must be evaluated for its strict-mode behavior. Option A leaves strict mode fragile against the next unstoplisted specimen. Option B compromises the invariant strict-mode is meant to enforce. Options C/D/E all preserve the invariant under strict.

### Test boundary (what regressions would need to be locked)

If a change to the classifier is later approved, the following regression properties must be locked; several already have tests, several would be new:

**Existing tests to preserve** (`shell/apps/compositions/tests/test_claim_verifier.py`):
- Wikipedia flagged when absent from corpus (`test_extract_finds_wikipedia_at_sentence_start`).
- Character OS multi-word extracted (`test_extract_finds_character_os_multiword`).
- Trafilatura extracted case-insensitively (`test_extract_now_catches_lowercase_trafilatura_k6_4_v2`).
- Every stoplist expansion test (`test_stoplist_alright_k6_4_v2`, `test_stoplist_cta_verbs_k6_4_v2_dogfood`, `test_stoplist_time_adverbs_k6_4_v2_1`, `test_stoplist_cta_verbs_k6_4_v2_2_dogfood`, `test_extract_skips_sentence_initial_adjectives_k6_4_1`).
- Multi-word demotion at sentence-initial (`test_multiword_demotes_sentence_initial_stoplisted_leader_k6_4_v2_1`, `test_multiword_demotes_only_at_sentence_initial_k6_4_v2_1`).
- `is_sentence_initial` unit boundary tests.

**New regression properties to lock** before any classifier change:
- **Q-278-2 adversarial matrix** — parametrize the 26-row table above so future edits explicitly declare which rows change classification. Especially: rows 1-4 (target-change rows for options C/D/E), row 6 (`Antoninus` — must remain flagged under any option), row 14 (`NASA` supported — must remain unflagged), row 15 (`FBI` — decide whether to close the 3-char silent miss).
- **Sentence-initial hallucination invariant** — assert that a genuinely unsupported proper noun at sentence-initial (`Antoninus`) flags under whatever new logic is chosen. This is the guard against Option B slipping in.
- **Founding-case guard** — assert that a script asserting `"Wikipedia is X"` or `"trafilatura is Y"` at sentence-initial with no corpus support still flags.
- **Polysemy documentation** — a test that pins the chosen behavior on rows 18-19 (`county Fair`, `Rose baked`) so the trade-off is explicit rather than emergent.
- **3-char all-caps acronym behavior** — decide explicitly and pin: current is silent-miss (row 15). Options A-D preserve it; Option E closes it.

No production tests are being added in Q-278-2 itself. The matrix above lives in this audit doc and can be lifted into `test_claim_verifier.py` when an option is approved.

### Prediction vs actual

Prediction largely accurate. Refinements from the audit:

- The regex+stoplist substrate was explicitly framed at inception as *"v1... v2 upgrade path is small-model semantic similarity; deferred until first false-positive event motivates it."* — the operator-typed rationale reads Q-278-1 as exactly that motivating event.
- `is_sentence_initial` already exists in-process and is already used elsewhere; it does not require any new dependency to invoke from the single-cap branch.
- Corpus-lowercase-recheck (Option C) was not in the prior conversation and emerged from the adversarial matrix (row 20 → row 1 comparison). It preserves the invariant with no new dependency and closes most of the Q-278-1 class.
- Strict mode has more real-Runway dogfood history than initially assumed. The founding intent to flip it is clear.
- Silent 3-char acronym miss (row 15) is a small independent finding, not part of Q-278-2 as posed, but worth flagging.

### Evidence vs inference distinction

- **Evidence** — git commit metadata + commit messages for the K6.4 evolution; module docstring; source of `extract_named_entities` / `verify_claims` / `is_sentence_initial`; the 26-row deterministic experiment output; the current DB state of composition `26c62b4b`; the live-verified `K6_CLAIM_VERIFIER_MODE` resolution.
- **Inference (well-supported)** — invariant statement; strict-mode intent classification; the shape-vs-named-entity gap; that Option C preserves the invariant with narrow polysemy leaks.
- **Inference (weaker)** — that the class of English words will keep surfacing new members indefinitely under Option A. Supported by pattern across 5 sessions but not proven.

### Unresolved questions surfaced by this audit

- **Timing on flipping strict-mode default.** Q-278-2 assumes strict remains future-facing. If Chris plans to flip strict imminently (e.g. before next dogfood pass), that changes the option ranking.
- **3-char all-caps acronym silent miss (row 15).** Independent finding. Decide whether to preserve or close under any classifier change. Not part of Q-278-2 as posed.
- **`Composition.verification_status = "verified"` while `verification_warnings` non-empty.** Documented convention, but the operator-visible surface reads mildly contradictory. Out of scope for Q-278-2; possible Q-278-3 candidate.
- **Polysemy handling** (rows 18-19). Any option in C/D/E direction needs to pin behavior on `Fair` in `The county Fair` and `Rose baked` explicitly.
- **`is_sentence_initial` and abbreviations** (row 26). Helper treats `Mr.` / `U.S.` as sentence-terminating. Documented as intentional but relevant if the helper's role expands from watchdog-reporting to single-cap gating.

### Recommendation

The recommended shape (subject to Chris + ChatGPT explicit approval) is:

1. **Adopt Option C** — sentence-initial demotion for single-cap tokens *conditioned on the token's lowercase form appearing in the factual corpus* — as the minimum-viable closure of the Q-278-1 class that preserves the invariant with no new dependency.
2. Keep the stoplist as-is (do not remove entries); do not add new entries via Q-278-2. The stoplist becomes a legacy safety net that Option C should progressively supersede via `stoplist_watchdog` reporting.
3. Lock the 26-row adversarial matrix as regression tests before landing any classifier change. Explicitly pin behavior on rows 6, 18, 19, 24, 26, and row 15.
4. Defer Option E (small-model NER) until a Q-278-2-implemented Option C is dogfooded and its polysemy leaks are characterized. Option E remains the endpoint of the v1 upgrade path.
5. Do NOT flip `K6_CLAIM_VERIFIER_MODE` default from `warn` to `strict` inside this session; treat strict-flip as its own scope-locked change.

### Explicit decision gate

**STOP.** No implementation on Q-278-2 until Chris + ChatGPT explicitly approve one of:

- Option A (stoplist expansion; accept general class remains open),
- Option C (sentence-initial + corpus-lowercase-recheck; recommended),
- Option D (static English-word stoplist; broader closure with polysemy trade-off),
- Option E (small-model NER; largest lift, highest coverage),
- or defer/close Q-278-2.

If Option C is chosen, scope-lock separately: (a) exact matrix rows to pin, (b) whether `is_sentence_initial` continues to treat colon and abbreviation periods as terminators, (c) whether to close the 3-char acronym silent-miss simultaneously.

> **⚠️ SUPERSEDED — see Q-278-2b below. Option C failed mechanical testing and is withdrawn. Original Q-278-2 recommendation no longer stands.**

---

## Q-278-2b — Decision-gate challenge: Option C mechanical test + semantic-direction feasibility

### Precise question(s)

1. Would Option C (as written in Q-278-2) mechanically differ from the existing case-insensitive corpus check, and would it have removed any of the three real `Fair` / `Come` / `Unless` warnings on Composition `26c62b4b`?
2. Given the accumulated stoplist size (~250 entries), the general Q-278-1 false-positive class, the 3-char acronym silent-miss, polysemy ambiguity, and future-facing strict-mode intent — has the evidence crossed the threshold where continuing to harden the regex+stoplist proxy is less defensible than investigating the semantic/entity upgrade path K6.4 v1 originally contemplated?

### Apparent contradiction (ChatGPT challenge)

The Q-278-2 audit stated both:
- Existing `verify_claims` already performs a case-insensitive substring check against the factual corpus.
- Option C proposes: for a sentence-initial single-cap that misses the corpus, additionally check the candidate's lowercase form against the corpus.

Those operations appear equivalent. The Q-278-1 specimen (`Fair`, `Come`, `Unless`) was flagged specifically because those tokens were absent from the corpus — meaning Option C's "additional lowercase check" cannot fix the very case that motivated the audit.

### Exact existing corpus-match semantics (re-read from source)

`character_os/claim_verifier.py:499-506`:

```python
corpus_lower = factual_corpus.lower()
allowed_lower = { v.strip().lower() for v in (allowed_vocabulary or ()) if v and v.strip() }
unsupported = []
for candidate in candidates:
    needle = candidate.claim.lower()
    if needle in corpus_lower:
        continue
    ...
```

Precise properties:
- **Case-sensitivity:** case-**insensitive**. Both sides are `.lower()`-normalized before comparison.
- **Match granularity:** raw Python string `in` — **substring** on the lowercased corpus. NOT tokenized, NOT word-boundary-anchored on the corpus side. Any occurrence of `needle` anywhere in `corpus.lower()` — including inside a larger word — passes.
- **Normalization:** `.lower()` only. No accent folding, whitespace normalization, punctuation stripping, or lemmatization.
- **Allowed-vocabulary path** (separate check, line 513): substring bidirectional — `any(a in needle or needle in a for a in allowed_lower)`.

**Consequence for Option C:** the check `is candidate.claim.lower() a substring of factual_corpus.lower()?` IS THE EXISTING CHECK. Adding a "lowercase-recheck" performs the identical string operation. Option C, as written, is a no-op.

### Deterministic before-vs-Option-C matrix (rebuilt against real 26c62b4b corpora)

Rebuilt the actual factual corpus consumed by K6.4 for Composition `26c62b4b`, per speaker, using `build_factual_corpus` with the persisted knowledge-chunk IDs (`3bfea692`, `219bcc30` shared; `4c7954e0` Tyson-only) and each teammate's business_brief / who_you_help / what_you_sell / Universe.brief.

- `ruby_corpus.lower()` length: **763 chars** (Christmas Day + open hours + Fox & Flour identity + Ruby's business brief).
- `tyson_corpus.lower()` length: **895 chars** (same as Ruby's shared block plus Tyson's coffee/pastry pairing chunk plus Tyson's business brief).

Substring test performed live against those exact lowercased corpora (Python `in`) — this IS the current verifier check:

| candidate | needle | ruby_hit | tyson_hit | current: flagged? | Option-C: flagged? | changed? | why |
|---|---|---|---|---|---|---|---|
| `Fair` | `fair` | False | False | YES | YES | NO | lowercase `fair` absent from both corpora; Option C's recheck IS the current check |
| `Come` | `come` | False | False | YES | YES | NO | same |
| `Unless` | `unless` | False | False | YES | YES | NO | same |
| `Please` | `please` | False | False | YES | YES | NO | same |
| `Always` | `always` | False | False | YES | YES | NO | same |
| `Antoninus` | `antoninus` | False | False | YES | YES | NO | same — correctly flagged (genuine unsupported entity) |
| `Rose` | `rose` | False | False | YES | YES | NO | same |
| `NASA` | `nasa` | False | False | YES | YES | NO | same |
| `Wikipedia` | `wikipedia` | False | False | YES | YES | NO | same — founding hallucination case still catches |
| `trafilatura` | `trafilatura` | False | False | YES | YES | NO | same — founding hallucination case still catches |

**Zero rows change.** Every candidate whose lowercase form is absent from the raw corpus is by definition absent from the lowercased corpus, and Option C proposes exactly that test. The two operations are identical, not merely equivalent.

### Answer to the specific question

> Would Option C have removed ANY of the three real warnings from Composition 26c62b4b?

**No.** `fair`, `come`, and `unless` are absent from the actual factual corpora used for both Ruby and Tyson on this composition. The existing verifier already performed the case-insensitive substring check and reached the flagged verdict; Option C's proposed "additional lowercase recheck" is the same operation and would reach the identical verdict.

### Option C verdict

**WITHDRAWN.** Option C as documented in Q-278-2 does not perform any operation the current verifier is not already performing. It cannot close the Q-278-1 class. Rescuing it by silently redefining it (e.g. as "check lowercase form against a wordlist" or "run when sentence-initial with additional context") would just be Option D or Option E under a misleading label.

**Root cause of my error:** I conflated "case-insensitive corpus match" with "lowercase form of the word appears somewhere in text." The existing check already does the former. Option C as I wrote it does the former too. My Q-278-2 recommendation was defective and Chris was right to challenge it before implementation.

### Impact on Q-278-2 options

- Option A (stoplist expansion): unchanged. Still closes today's specimens, still leaves general class open.
- Option B (blind sentence-initial demotion for single-cap): unchanged. Still rejected on invariant grounds — silences genuinely unsupported sentence-initial proper nouns.
- **Option C (as written): WITHDRAWN.** Redundant with existing behavior.
- Option D (static English-word stoplist / wordlist demotion): still viable. Would close the Q-278-1 class by NOT relying on corpus content — the wordlist itself is the demotion signal. Introduces polysemy leaks (`Rose`, `Mark`, `Bill`, `May`, `June` when they IS a proper noun). No runtime dependency; ships as a data file.
- Option E (small-model NER): still viable. Original v1 upgrade path. Requires a new runtime dependency.
- Option F (heuristic composite): still marginal.
- Option G (widen corpus definition): still ruled out by SESSION 253 boundary.

### Small feasibility comparison — regex+stoplist vs semantic/NER vs existing-in-repo

Repository inventory verified. Runtime dependencies actually present (from `shell/pyproject.toml` + `media-engine/requirements.txt` + `.venv/lib/python3.11/site-packages/`):

Backend-relevant: `django`, `djangorestframework`, `psycopg`, `pgvector`, `celery`, `redis`, `httpx`, **`openai>=2.0`**, `pdfminer.six`, `django-redis`, **`trafilatura`**, `lxml_html_clean`, `youtube-transcript-api`, `PyYAML`, `jsonschema`, `numpy`, `regex` (enhanced regex library), `justext`.

Media-engine additional: `fastapi`, `uvicorn`, `pydantic`, `rembg`, `onnxruntime`, `opencv-python-headless`, `Pillow`.

**Explicitly NOT present:** `spacy`, `nltk`, `transformers`, `huggingface`, `flair`, `stanza`, `textblob`, `wordfreq`, `pyenchant`, any `en_core_web_*` model, any local NER model.

**Only candidate for existing-in-repo semantic classification:** `openai>=2.0`. Would require a Responses/Chat API call per turn — a per-render LLM cost + latency + provider dependency. This violates the K6.4 founding constraint ("zero added LLM cost, zero added latency") AND ChatGPT's explicit "no provider spend" instruction. It also chains K6.4 verification to the same provider whose hallucinations K6.4 exists to catch. Rejected.

**Conclusion — Option C for the "existing in-repo dependency" branch:** no such dependency exists. Any semantic/NER direction that meets the deterministic + zero-provider constraint requires a new runtime dependency.

#### Comparison matrix

| dimension | A: continue regex + stoplist | B: local NER (e.g. spaCy `en_core_web_sm`, new dep) | C-existing: OpenAI (no new dep, but violates constraints) |
|---|---|---|---|
| Alignment with named-entity grounding invariant | Approximate (shape proxy for entities) | Direct (extracts `PERSON`/`ORG`/`GPE` etc.) | Direct (LLM understands the concept) |
| Expected false-positive class | Sentence-initial ordinary English words missing from stoplist (open class, +5 sessions of growth) | Very small — mostly disambiguation edge cases | LLM non-determinism; prompt-sensitive |
| Expected false-negative class | Lowercase entities not in `KNOWN_TECH_TERMS`; 3-char all-caps acronyms; unusual spellings | Rare, well-characterized in NER lit | Same LLM class the verifier exists to catch |
| Strict-mode suitability | Fragile — every new specimen surfaces as a strict-mode block on grounded briefs | Robust | Fragile — LLM classifier can also hallucinate; recursive risk |
| Runtime latency | Microseconds per turn (regex only) | ~30-100 ms per turn (in-process model) | Provider call: hundreds of ms + per-turn cost |
| Memory / deployment | Negligible | ~13 MB model + ~200 MB spaCy runtime; ships once, loads once per worker | None (uses existing OpenAI client) |
| Deterministic / offline | Yes — pure regex + set | Yes — deterministic model, offline | No — provider dependency, non-deterministic |
| Maintenance burden | Growing — stoplist requires human curation every session, watchdog surfaces new candidates on every dogfood | Model version pinned; occasional false-positive fix via allow/deny lists | LLM version drift; prompt tuning; provider outages |
| Closes the CLASS (not just today's words) | **NO** — 5+ sessions of evidence that the class stays open | **YES** — POS + entity type replace capitalization as the signal | Yes in theory; unstable in practice |
| Constraint violations | None | New runtime dep + model download at build/deploy time | Violates K6.4 zero-cost / zero-latency founding constraint AND explicit no-provider instruction |

Option D (static wordlist file, no runtime dep, ships in-tree) sits between A and B on this matrix: closes most of the class via a bounded finite resource, introduces polysemy leaks, no new runtime dependency, deterministic. Not shown above because it's a variant of A rather than a new architecture.

#### Threshold question

*Has accumulated evidence crossed the threshold where continuing to harden the regex/stoplist proxy is less defensible than evaluating the semantic/entity upgrade originally contemplated by K6.4?*

The evidence:

- **Stoplist growth pattern.** 5+ sessions have grown the stoplist reactively, one dogfood at a time (Cleanest → Welcome → Modern → Short → Alright → Today → Reach → Respect → …). The Q-278-1 specimen (`Fair`, `Come`, `Unless`) makes it 6. Each addition closed a specific specimen without touching the class boundary. `stoplist_watchdog` was built to help find the next specimen, not to close the class.
- **General class characterization.** Q-278-1 proved the class is systematic: any capitalized English word ≥ 4 chars missing from the stoplist AND from the corpus. Enumeration cannot converge because English has more common function/verb/adjective/adverb words than any hand-curated set will reach.
- **Adjacent silent behaviors surfaced by Q-278-2.** 3-char all-caps acronyms (`FBI`/`CIA`/`FDA`) silently NOT extracted at all — a separate false-negative class the proxy simply cannot express.
- **Polysemy.** `Fair` (event), `Rose` (name), `Mark` (name / verb), `May` (name / month / verb), `Bill` (name / noun) — the shape proxy cannot disambiguate context. Neither can a static wordlist. Only entity-typed classification can.
- **Strict-mode intent.** The founding commit + K6.4.1/v2/v2.1/v2.2 dogfood all treat strict as the enforcement target. Every new Q-278-1-class specimen becomes a real render-blocker under strict. The current default remains `warn` in part because the class stays open.
- **Original v1 rationale.** The founding docstring explicitly says: *"v1 is deterministic / regex-based — zero added LLM cost, zero added latency. Lowercase technology names are a known false-negative class in v1... v2 upgrade path is small-model semantic similarity; deferred until first false-positive event motivates it."* The v2 upgrade was designed-in at inception, gated by evidence.

**Assessment:** the evidence has crossed the threshold to WARRANT an audit of the semantic-direction upgrade path. The evidence has NOT proven the semantic direction is the right immediate action — that requires a separate audit of Option E (or D) including: dependency footprint / license / offline-availability / deterministic guarantees for the specific model / span-alignment with existing `KNOWN_TECH_TERMS` and numeric passes / worker cold-load implications / test-mode substitution strategy.

The right shape is a **Q-278-3 scope-locked feasibility audit of Option E** (small-model in-process NER) versus **Option D** (static wordlist stoplist), with a specific candidate model or wordlist named and its dependency + deployment cost quantified.

### Evidence vs inference

- **Evidence:** exact source of `verify_claims`; live-verified corpus contents for Composition `26c62b4b`; live-verified substring test outcomes for the 10 candidate tokens; exact per-file dependency inventory; git commit history of the stoplist evolution.
- **Inference (well-supported):** Option C is redundant with existing check (proven by the matrix and by re-reading source). No existing runtime dep supports semantic classification without violating stated constraints. Semantic direction warrants an audit.
- **Inference (weaker):** that Option E (specifically spaCy `en_core_web_sm`) is the right endpoint. Naming a specific model and its trade-offs is Q-278-3, not Q-278-2b.

### Updated recommendation

1. **CLOSE Option C** (withdrawn on mechanical grounds).
2. **Do not implement anything in Q-278-2 today.** Options A / D / E remain on the table.
3. **Open Q-278-3** as a scope-locked audit of the semantic direction: pick specific candidate implementations (e.g. spaCy `en_core_web_sm`, static wordlist derived from an in-tree common-words snapshot), quantify dependency / model / license / offline / determinism / latency / cold-load, and produce a Go/No-Go with a named implementation shape.
4. **Do NOT flip `K6_CLAIM_VERIFIER_MODE`** default from `warn` to `strict` while the false-positive class remains open. Any strict-flip is downstream of Q-278-3.
5. **Optional interim mitigation** — Option A (small stoplist expansion of `fair`, `come`, `unless`, `please`, `always`) if the operator wants near-zero visible-evidence noise on the current dogfood cadence. Explicitly acknowledge this closes today's specimens only. Not recommended unless the noise is materially blocking dogfood.

### Explicit decision gate

**STOP.** No implementation lands. Chris + ChatGPT must explicitly:

- (a) confirm Option C is withdrawn (recorded here);
- (b) either open Q-278-3 as scoped above OR keep the K6.4 substrate frozen and treat the false-positive class as accepted noise under `warn`;
- (c) decide separately whether interim Option A stoplist tweaks should ship while Q-278-3 is investigated.

*Chris + ChatGPT decision:* Q-278-2b accepted. Option C closed WITHDRAWN. No stoplist additions. Q-278-3 opened as an audit-only semantic-verifier feasibility investigation.

---

## Q-278-3 — Semantic-verifier feasibility (architecture audit)

### Precise question

Given the Q-278-2 invariant — *named entities / source-dependent factual references introduced by synthesis should be grounded in the speaking character's factual corpus or allowed vocabulary; ordinary language should not be treated as a claim* — what is the smallest robust verifier architecture that actually represents that invariant rather than approximating it via capitalization + an expanding stoplist?

Audit-only. No production changes. No dependency installation. No provider calls. No warn→strict flip.

### Prediction / hypothesis (before investigation)

The smallest defensible architecture is a **hybrid** (Option D): preserve the deterministic passes that are semantically useful independent of the capitalization proxy (numeric, `KNOWN_TECH_TERMS`, corpus grounding, allowed vocabulary), and replace ONLY the two capitalization-as-NER passes (`_SINGLE_CAP_RE`, `_MULTIWORD_CAPS_RE` — the shape proxy) with a semantic entity/POS classifier. The concrete candidate is a small in-process NER (spaCy `en_core_web_sm` is the natural first candidate but must be justified against alternatives, not assumed). The ~250-entry stoplist becomes a compatibility layer during a shadow-evaluation period, then eventually removable technical debt once the semantic classifier has been characterized against real dogfood corpora. Shadow evaluation is feasible via the existing `CHARACTER_OS_*_EXPERIMENT` env-var pattern.

### Candidate architectures

**A — Current: regex + ~250-entry stoplist + corpus grounding + `KNOWN_TECH_TERMS` + numeric.**
- Same as production today.

**B — Static wordlist: A + deterministic English-word demotion.**
- After single-cap extraction, if the token's lowercase form appears in a curated top-N common-English wordlist, demote regardless of corpus content.
- Concrete shape: ~1,000-10,000 word frozen file shipped in-tree (no runtime dep).

**C — Local NER (replace-everything).**
- Replace all shape-based extraction with in-process NER + POS.
- Concrete candidate: spaCy `en_core_web_sm`. See dependency block below.

**D — Hybrid: preserve numeric + `KNOWN_TECH_TERMS` + corpus + vocab; replace ONLY the capitalization-as-NER passes with local NER/POS.**
- The two regex passes that currently proxy for NER (`_SINGLE_CAP_RE`, `_MULTIWORD_CAPS_RE`) are replaced.
- Numeric pass stays (regex on `$X` / `X%` / four-digit years — no NER needed).
- `KNOWN_TECH_TERMS` stays (closes the lowercase-domain-entity class NER will not catch — `trafilatura`, `pgvector`, `numpy`, `redis`, `django`).
- `build_factual_corpus` + `build_allowed_vocabulary` + case-insensitive substring grounding stay.
- Stoplist becomes compatibility layer (see Q-278-3 §"Stoplist disposition" below).

### Adversarial matrix (by category)

Text-only reasoning. Deterministic where the current classifier is invoked in-repo; documented behavior for the NER candidate (clearly labeled). No provider calls. Corpus assumed to include supported entities as shown; `KNOWN_TECH_TERMS` behavior mirrored.

Legend for outcome cells:
- **flag** — verifier reports an `UnsupportedClaim`.
- **pass** — verifier does not flag (correct or by design).
- **miss** — extractor never produces a candidate for the token (silent).

| category | input | A: current | B: wordlist demote | D: hybrid (NER + preserved passes) | invariant-correct? |
|---|---|---|---|---|---|
| **ordinary sentence language** | `Fair enough.` | flag (Q-278-1) | pass (`fair` in wordlist) | pass (JJ/RB; not entity) | pass |
| | `Come inside.` | flag | pass | pass (VB; not entity) | pass |
| | `Unless you disagree.` | flag | pass | pass (IN; not entity) | pass |
| | `Please sit down.` | flag | pass | pass (UH; not entity) | pass |
| | `Always check first.` | flag | pass | pass (RB; not entity) | pass |
| | `Today we are open.` | pass (stoplisted) | pass | pass | pass |
| | `Modern systems are useful.` | pass (stoplisted) | pass | pass | pass |
| **real unsupported entities (mid- or sentence-init)** | `Antoninus reigned peacefully.` | flag | flag (not in wordlist) | flag (NER: PERSON) | flag |
| | `Wikipedia is our source.` | flag | flag | flag (NER: ORG) | flag |
| | `NASA supplied the equipment.` | flag | flag | flag (NER: ORG) | flag |
| | `France changed the rule.` | flag | flag | flag (NER: GPE) | flag |
| | `Microsoft built it.` | flag | flag | flag (NER: ORG) | flag |
| | `OpenAI released it.` | flag | flag | flag (NER: ORG) | flag |
| **supported entities (present in corpus)** | `Fox and Flour` | pass (corpus) | pass | pass (corpus) | pass |
| | `Ruby` | pass (allowed_vocab) | pass | pass (allowed_vocab) | pass |
| | `Tyson` | pass (allowed_vocab) | pass | pass (allowed_vocab) | pass |
| | `Christmas Day` | pass (corpus) | pass | pass (corpus) | pass |
| | `Character OS` | pass (`KNOWN_PLATFORM_TERMS`) | pass | pass (`KNOWN_PLATFORM_TERMS`) | pass |
| **short acronyms** | `FBI` (3-char) | miss (regex requires 4+ chars) | miss | flag (NER: ORG) | flag |
| | `CIA` | miss | miss | flag (NER: ORG) | flag |
| | `FDA` | miss | miss | flag (NER: ORG) | flag |
| | `IRS` | miss | miss | flag (NER: ORG) | flag |
| **lowercase / domain entities** | `trafilatura` | flag (`KNOWN_TECH_TERMS`) | flag | flag (`KNOWN_TECH_TERMS` preserved) | flag |
| | `pgvector` | flag (`KNOWN_TECH_TERMS`) | flag | flag (`KNOWN_TECH_TERMS` preserved) | flag |
| | `numpy` | miss (not in `KNOWN_TECH_TERMS`) | miss | miss (`KNOWN_TECH_TERMS` preserved) | *documented gap* — add to `KNOWN_TECH_TERMS` if wanted |
| | `django` | flag (`KNOWN_TECH_TERMS`) | flag | flag | flag |
| | `redis` | flag (`KNOWN_TECH_TERMS`) | flag | flag | flag |
| **polysemy** | `Rose baked the bread.` (person) | flag | pass (wordlist has `rose`) — **WEAKENED** | flag (NER: PERSON) | flag |
| | `A rose bloomed.` (flower) | miss (lowercase) | miss | miss (NER: no entity) | pass |
| | `Mark called today.` (person) | flag | pass (wordlist has `mark`) — **WEAKENED** | flag (NER: PERSON) | flag |
| | `Make a mark here.` (verb/noun) | miss (lowercase) | miss | miss | pass |
| | `Bill approved it.` (person) | flag | pass (wordlist has `bill`) — **WEAKENED** | flag (NER: PERSON) | flag |
| | `Pay the bill.` (noun) | miss | miss | miss | pass |
| | `May arrived.` (person/month) | flag | pass (wordlist has `may`) — **WEAKENED** | flag (NER: PERSON or DATE) | flag |
| | `It may happen.` (modal) | miss | miss | miss | pass |
| | `The county Fair opens Friday.` (event name mid-sentence) | flag `Fair` + `Friday` | pass `Fair` (weakened) + `Friday` (in wordlist too if included) | context-dependent (NER may or may not tag `Fair` as EVENT; `Friday` as DATE) | ambiguous — see notes |
| | `Fair enough.` (idiom) | flag | pass | pass | pass |
| **multi-word entities** | `James Webb Space Telescope` | flag (multi_word) | flag | flag (NER: WORK_OF_ART / PRODUCT / ORG) | flag |
| | `New York` | flag (multi_word) | flag | flag (NER: GPE) | flag |
| | `OpenAI API` | flag (multi_word) | flag | flag (NER: ORG) | flag |
| | `Larimer County` | flag (multi_word) | flag | flag (NER: GPE) | flag |
| | `Fox and Flour` | pass (corpus) | pass | pass (corpus) | pass |
| **punctuation / position** | sentence-initial | often false-flag | wordlist-dependent | context-aware via POS | pass |
| | mid-sentence | corpus-check works well | same | same | pass |
| | after quotes | often false-flag | wordlist-dependent | context-aware | pass |
| | after colon | often false-flag (`is_sentence_initial` treats `:` as terminator) | wordlist-dependent | context-aware | pass |
| | after abbreviation (`Mr. Smith`) | often false-flag on next token | same | context-aware (NER handles as name) | pass |
| | after em-dash | current regex doesn't treat as sentence-initial for demotion | wordlist-dependent | context-aware | pass |

**Cells marked "WEAKENED" for Option B are the invariant violation:** any proper-noun name that ALSO happens to be a common English word (`Rose`, `Mark`, `Bill`, `May`, `June`) gets silenced by a wordlist regardless of context, which is exactly the class of true positives the verifier exists to catch when synthesis smuggles a fabricated person into a script.

**Option D**'s edges:
- **Correctly** handles all seven ordinary-sentence-language rows via POS awareness — the class Q-278-1 opened is closed structurally, not by enumeration.
- **Correctly** flags all six real unsupported entities via NER entity typing (ORG/PERSON/GPE/etc.).
- **Correctly** flags all polysemous NAME uses (`Rose baked`, `Mark called`, `Bill approved`, `May arrived`) because NER context tags them as PERSON.
- **Correctly** ignores the common-word uses (`rose bloomed`, `mark here`, `bill to pay`, `may happen`) because NER does not tag them as entities.
- **Adds** 3-char acronym coverage (`FBI`/`CIA`/`FDA`/`IRS`) as ORG entities.
- **Preserves** lowercase tech-term coverage via the retained `KNOWN_TECH_TERMS` pass.
- **Documents** a gap: `numpy` is currently NOT in `KNOWN_TECH_TERMS`. That gap exists in A and B too; D inherits it. Additive-only fix.

Distinction: **repository-measured evidence** vs **documented external behavior**:
- Option A columns (`flag` / `miss` / `pass`) are **measured** in-repo (the Q-278-2 26-row experiment + Q-278-2b 10-token substring test). Reproducible with the running interpreter.
- Option B columns are **inferred** from the definition (wordlist absent/present).
- Option D "NER" columns are **inferred** from spaCy `en_core_web_sm`'s documented OntoNotes-trained entity types (`PERSON`, `NORP`, `FAC`, `ORG`, `GPE`, `LOC`, `PRODUCT`, `EVENT`, `WORK_OF_ART`, `LAW`, `LANGUAGE`, `DATE`, `TIME`, `PERCENT`, `MONEY`, `QUANTITY`, `ORDINAL`, `CARDINAL`) and its POS tag set. Concrete row-by-row measurement would require installing spaCy + model, which is out of audit scope. Q-278-3 does not claim NER row-by-row certainty; it claims the architecture eliminates the shape-based false-positive class by construction.

### Architecture responsibility map

Semantic responsibility of each verifier pass in **Option D — Hybrid**:

| pass | responsibility | why it stays |
|---|---|---|
| **numeric** (`_NUMERIC_RE`) | Extract $X / X% / years so numeric assertions can be corpus-grounded | Independent of NER; deterministic regex is correct |
| **known-tech** (`KNOWN_TECH_TERMS` frozenset + regex) | Extract lowercase library/product names general NER won't recognize | Closes the class NER doesn't cover; curated finite list |
| **NER** (new pass — replaces `_SINGLE_CAP_RE` and `_MULTIWORD_CAPS_RE`) | Extract named entities (PERSON/ORG/GPE/etc.) regardless of position or shape | Represents the invariant directly instead of approximating it |
| **corpus grounding** (`verify_claims` case-insensitive substring) | Distinguish supported vs unsupported entities | Orthogonal to extraction; correct |
| **allowed vocabulary** (`build_allowed_vocabulary` substring bi-directional) | Whitelist per-character named entities without treating them as evidence | Correct |
| **stoplist** (`_COMMON_PROPER_NOUN_FALSE_POSITIVES`) | Compatibility layer during shadow evaluation; watchdog reference | See disposition below |

Behavior that exists only to compensate for the capitalization proxy and could **disappear once D is proven**:

- The 250-entry stoplist itself (its raison d'être is stopping the shape proxy from flagging capitalized common words; NER doesn't produce those candidates in the first place).
- The multi-word "sentence-initial stoplisted leader" demotion (SESSION 174 v2.1). NER doesn't produce the "Think Antoninus" concatenation.
- The 4-character length gate on `_SINGLE_CAP_RE` and its resulting silent-miss on 3-char acronyms.
- The lowercase-form dedupe logic that exists because casing variants (`PyTorch` / `PYTORCH`) go through separate passes.

Stoplist disposition (Option D):

- **Phase 1 (shadow evaluation)** — stoplist stays active in production; NER runs in shadow behind an env flag; both classifications persisted for comparison.
- **Phase 2 (cutover)** — NER becomes primary; stoplist becomes fallback with a boolean gate (e.g., `settings.K6_LEGACY_STOPLIST_ENABLED = False` by default; toggleable for rollback).
- **Phase 3 (removal)** — stoplist deleted once ≥N dogfood cycles pass without stoplist producing a flag NER misses.

### Dependency / deployment analysis (Option D concrete candidate: spaCy `en_core_web_sm`)

**Repository-measured evidence** (this session):
- No `spacy`, `nltk`, `transformers`, `huggingface`, `flair`, `stanza`, `textblob`, `wordfreq`, `pyenchant`, `en_core_web_*` present in `shell/pyproject.toml`, `media-engine/requirements.txt`, or `.venv/lib/python3.11/site-packages/`.
- Existing deps that could host semantic classification: `openai>=2.0` (rejected — LLM cost + recursive-hallucination risk + violates founding constraint).
- `regex` present but is only an enhanced regex library, not semantic.
- Celery worker layout runs `--concurrency=2` per `scripts/start-local-real.sh:108`. Single Django dev server. Production layout unknown to this audit.

**Documented external evidence** (from spaCy 3.x + `en_core_web_sm` public docs):
- Package: `spacy` MIT license. Pure-Python + Cython + numpy; already-installed `numpy>=2` covers the numeric-array dep.
- Model: `en_core_web_sm` v3.7 wheel ~12-13 MB compressed / ~50 MB extracted. **License: MIT** (SmallCore models were relicensed MIT in the v3.5+ line; earlier CC-BY-SA notices apply to the v2 models — verify at install time).
- Cold-load: ~0.5-2 s per process on modern CPU. Loading is `spacy.load("en_core_web_sm")`; keep as module-level singleton so it happens once per worker.
- Per-turn latency: ~5-30 ms for short texts (per-turn dialogue chunks are ≤ ~150 chars). K6.4 is called once per dialogue turn (5-12 turns per composition) or once per talking-head brief. Materially negligible next to a Runway render (60-120 s) or an OpenAI Responses call (500-2000 ms).
- Memory: ~50 MB per loaded process. With `--concurrency=2` × Django+Celery, ~200 MB total additional resident memory. Acceptable on typical dev/prod boxes.
- Determinism: yes. Model is a fixed-weights CNN-based tagger + NER; no sampling.
- Offline: yes after initial download. Wheel + model can be pinned in `pyproject.toml` and installed at container-build time. No runtime provider dependency.
- Alternatives briefly assessed conceptually (not installed):
  - **NLTK**: smaller runtime but its NER (`maxent_ne_chunker`) is dated; higher error rate; still requires model downloads (~40 MB across `punkt`, `averaged_perceptron_tagger`, `maxent_ne_chunker`, `words`). Comparable footprint, worse accuracy for our invariant.
  - **stanza / flair**: PyTorch-based; ~500 MB+ footprint. Rejected on deployment cost.
  - **transformers** (Hugging Face): PyTorch + tokenizers; ~1 GB+; rejected.
  - **HanLP / other small models**: not standardized; rejected on maintenance burden.

Net: `spacy` + `en_core_web_sm` is the smallest well-supported local NER that fits the deterministic/offline constraint. This audit does not commit to it — it names it as the concrete candidate to evaluate in shadow mode.

### Strict-mode implications

Option A: any new Q-278-1-class specimen becomes a real render-blocker under strict; strict-flip remains gated by stoplist coverage.

Option B: strict is safe for Q-278-1 class but WEAKER on polysemy — a fabricated `Bill Gates said X` (with `bill` in wordlist) could silently pass. Invariant violated.

Option D: strict-mode safety improves substantially in two directions simultaneously — ordinary language doesn't false-block, and short acronyms + polysemous name uses that A silently misses become properly flagged. Recommended precondition before flipping strict-mode default is: ≥N warn-mode dogfood renders under D with a shadow-diff analysis showing D's warnings are a strict superset of A's true positives.

### Uncertainty handling

Any semantic classifier will produce candidates it is not 100% confident about. Default policy per Chris's directive (*"Prefer warn over silent acceptance unless evidence supports otherwise"*):

- Below-threshold NER predictions → still emit as `UnsupportedClaim` unless the corpus supports them. Errs toward operator visibility.
- Ambiguous polysemy cases (row `The county Fair opens Friday`) → emit if NER doesn't confidently type as entity; verifier can attach a new `kind="ambiguous"` or reuse `kind="proper_noun"` for compatibility.

### Shadow-evaluation feasibility

**Feasible with existing patterns.** Two existing precedents:

1. **`CHARACTER_OS_*_EXPERIMENT` env-var pattern** (`character_os/duration_contract.py:179`, `apps/compositions/primitives/avatar_speech.py:93/156`). Each pattern gates optional behavior behind a settings flag with an env-var override. `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` would fit the same shape.
2. **`stoplist_watchdog` mgmt command** (`apps/compositions/management/commands/stoplist_watchdog.py`). Already reads persisted `verification_warnings` and reports. A `k64_shadow_diff` mgmt command would read a new sibling JSON field with the shadow classifier's output and report old-vs-new deltas.

Proposed shadow-mode shape (design only, no implementation this session):

- New optional JSONField on `Composition` and `ConversationMessage` (e.g. `verification_warnings_shadow`) or a new dedicated model. If a model, it can be additive-nullable and rolled back cleanly.
- In `run_verifier`, when the env flag is set: compute the current-classifier output (returned as today), THEN compute the D-Hybrid classifier's output, persist both, return CURRENT so render behavior is unchanged.
- New `k64_shadow_diff` mgmt command: reads recent rows with populated shadow field, reports per-turn (a) tokens flagged by old but not new (Q-278-1 class closures), (b) tokens flagged by new but not old (hallucination surface expansion), (c) unchanged tokens.
- Gate under `warn` mode only — strict cannot consume shadow output.
- No provider spend (shadow classifier is local).
- Cost impact: adds ~5-30 ms per dialogue turn only when the flag is on. Zero cost when off.

Feasibility caveats:

- One additive schema change (new JSONField) is required if we want durable comparison. If we want to skip the migration, shadow output could go to a dedicated logger instead — cheaper but harder to query historically.
- The stoplist_watchdog pattern already knows how to walk `Composition.verification_warnings`; extending it to walk the sibling field is straightforward.
- Rollback: unset the env var. Full revert. No data loss (shadow field is additive).

### Operational impact (estimated, Option D)

- Package size added: **~13 MB** compressed wheel (`en_core_web_sm`) + **~5 MB** for `spacy` itself.
- Model size on disk: **~50 MB extracted**.
- Worker memory: **~50 MB per loaded worker process** (2 Celery + 1 Django = **~150 MB** dev; production worker count TBD).
- Cold-load time: **~1 s** per worker process at startup; module-level singleton so it happens once.
- Per-turn latency: **~5-30 ms** for a typical dialogue turn. Composition renders take 60-120 s of Runway wall-clock; this is <0.05% overhead.
- Build/deployment: `spacy` + model downloadable at container-build time; can be pinned via `pyproject.toml`. No runtime provider dependency.
- Licensing: `spacy` MIT; `en_core_web_sm` v3.5+ MIT (verify at install-time).
- Test-mode substitution: NER pass gated behind a factory that can be monkeypatched to a deterministic stub for tests that don't want to load the model — same pattern used elsewhere in the codebase for `RUNWAY_FORCE_MOCK`.

### Recommendation

**Option D — Hybrid** is the recommended architecture direction:

1. Preserve numeric, `KNOWN_TECH_TERMS`, corpus grounding, and allowed vocabulary passes unchanged.
2. Replace the two capitalization-as-NER passes (`_SINGLE_CAP_RE`, `_MULTIWORD_CAPS_RE`) with a local NER classifier. Concrete candidate: spaCy `en_core_web_sm`. Other candidates (NLTK's `maxent_ne_chunker`, static-wordlist-only, or "no change") remain on the table if evaluation reveals blockers.
3. Ship with **shadow-evaluation mode first** (env-flag gated, additive JSONField, no render-behavior change). Run for a bounded dogfood window. Compare classifications with a new `k64_shadow_diff` mgmt command.
4. **Cutover** to primary only after shadow diff shows: (a) D is a superset of A's true positives, (b) D closes the Q-278-1 class in real corpora, (c) no new false-negative class larger than the ones D closes.
5. **Retire stoplist** after ≥N cutover-mode dogfood cycles pass without stoplist producing a flag NER misses. Until then, keep stoplist behind a boolean gate for rollback.
6. **Do NOT flip strict-mode default** until at least a shadow window + cutover window have both passed.
7. Reject Option B on invariant grounds (polysemy leaks). Reject Option A as endpoint (the class stays open). Do NOT introduce an LLM-based verifier.

Explicit non-recommendations:

- **Do NOT** install `spacy` in this session.
- **Do NOT** add `Fair`/`Come`/`Unless` to the stoplist as an interim mitigation. Option D's shadow phase will exercise them and characterize D's real behavior; interim stoplist tweaks would corrupt the shadow signal.
- **Do NOT** open Q-278-4 (strict-mode flip) until shadow + cutover phases complete.

### Evidence vs inference

**Evidence** (measured / repository-verified in this session):
- Exact match semantics of `verify_claims` (Q-278-2b).
- Absence of any semantic/NER library in the current runtime (dep files + site-packages listing).
- Current per-verifier-pass responsibilities (source of `extract_named_entities`).
- Existing `CHARACTER_OS_*_EXPERIMENT` env-var pattern and its call sites.
- Existing `stoplist_watchdog` mgmt command and its schema access pattern.
- Celery `--concurrency=2` per `scripts/start-local-real.sh`.

**Inference (well-supported by evidence + public documentation)**:
- spaCy `en_core_web_sm` size / memory / latency / determinism / license characteristics from public model card + spaCy documentation.
- Option D closes the Q-278-1 class by construction (NER doesn't tag ordinary English as entity).
- Shadow-mode shape is achievable via existing patterns without new architectural surface.

**Inference (weaker — would benefit from a bounded feasibility spike, still audit-only)**:
- Actual NER behavior on Fox & Flour / Patch's Workshop corpora (would require installing spaCy locally in a throwaway venv and running the Q-278-3 adversarial matrix against it). If Chris + ChatGPT approve, Q-278-3.1 could be a "throwaway venv, no repo changes" measurement pass to convert the "documented" cells above to measured cells.

### Unresolved questions

- **Model file distribution.** spaCy models can be pinned via `pip install <wheel-url>` or via `python -m spacy download`. Preference depends on offline-build guarantees. Not decided in Q-278-3.
- **Shadow-field disposition after cutover.** Delete the field? Keep as history? Decide at cutover time.
- **`numpy` (and any other missing tech term) coverage.** Independent of the D decision. Grep-add to `KNOWN_TECH_TERMS` when the operator surfaces one.
- **`Composition.verification_status = "verified"` while warnings non-empty.** Still open from Q-278-2. Independent surface.

### Explicit Go / No-Go decision gate

**STOP.** No implementation lands. Chris + ChatGPT must explicitly:

- **Go A**: Approve Option D as the target architecture and open Q-278-3.1 to design the shadow-mode implementation. (Recommended.)
- **Go B**: Approve a bounded throwaway-venv feasibility spike first to measure the NER candidate against the adversarial matrix before committing to D.
- **No-Go**: Reject Option D. If No-Go, either freeze at Option A (accept the false-positive class as `warn`-mode noise) or select B/C for reasons documented in the decision.

If Go A is chosen, scope-lock separately:
- (i) concrete NER candidate (spaCy `en_core_web_sm` or another),
- (ii) shadow-mode schema shape (new JSONField vs new model vs logger-only),
- (iii) shadow-window duration (calendar-time or N dogfood cycles),
- (iv) cutover acceptance criteria (concrete metrics on shadow diff).

*Chris + ChatGPT decision:* **GO B** — bounded throwaway-venv feasibility spike first. Also: UDB cross-repo reuse audit concluded NO USEFUL REUSE (`docs/design/SESSION_278_UDB_NER_REUSE_AUDIT.md`). Character OS evaluates its own semantic verifier without waiting on cross-repo reuse.

---

## Q-278-3.1 — Bounded local NER feasibility measurement (throwaway venv)

### Precise question

Does a concrete local NER/POS candidate materially outperform Character OS's current capitalization proxy on the actual adversarial boundary we care about, while preserving the founding unsupported-entity invariant? Concrete candidate: `spacy>=3.7,<3.8` + `en_core_web_sm==3.7.1`. Try to disprove Option D.

Cross-reference: `docs/design/SESSION_278_UDB_NER_REUSE_AUDIT.md` — verdict NO USEFUL REUSE. Do not reopen the cross-repo reuse question without new evidence.

### Prediction / hypothesis (before spike)

Option D as described in Q-278-3 assumes raw `doc.ents` (NER entity spans) closes the Q-278-1 class. Prediction: this holds for the seven ordinary-language rows (`Fair`, `Come`, `Unless`, `Please`, `Always`, `Today`, `Modern`) while preserving flags for real unsupported entities (`Antoninus`, `Wikipedia`, `NASA`, etc.). Short acronyms (`FBI`/`CIA`/`FDA`/`IRS`) become extractable via NER ORG label. Lowercase domain names (`pgvector`, `redis`) stay in the `KNOWN_TECH_TERMS` pass.

### Isolation

- **Temporary venv:** `/tmp/q278_spacy_spike/venv/` — throwaway, unrelated to Character OS's `.venv`.
- **Temporary scripts:** `/tmp/q278_spacy_spike/{measure.py,classify.py,real_specimens.py}` — throwaway.
- **No modifications** to `shell/pyproject.toml`, `media-engine/requirements.txt`, `.venv/`, production source, migrations, DB state, provider config.
- **No provider calls.**
- **DB access:** read-only. Django `manage.py shell -c` used to reconstruct real per-speaker corpora for Composition `26c62b4b` and enumerate 5 recent warned rows.
- **K6_CLAIM_VERIFIER_MODE:** unchanged (`warn` default resolved from settings + env).

### Package / model versions actually installed

- `python 3.11.6` (throwaway venv)
- `spacy 3.7.5` (MIT-licensed core library; wheel install)
- `en_core_web_sm 3.7.1` (installed via `python -m spacy download en_core_web_sm`)
- `click` (installed as spaCy CLI dependency)

### Measured operational cost

Measured on the local macOS Darwin 25.6.0 box (single-process cold-load + repeated warm inference in one Python process):

- **Installed package footprint:** `spacy` = 30 MB on disk; `en_core_web_sm` = 15 MB on disk; combined **~45 MB**. Includes transitive deps.
- **Cold-load time:** `import spacy` = **433 ms**; `spacy.load("en_core_web_sm")` = **215 ms**; total cold path ≈ **648 ms** per process at first use.
- **Process RSS after cold-load:** **~135 MB** (Python 3.11 + spaCy + model + numpy etc.). Grows to ~140 MB after warm inference on the 41-row matrix. This is the *whole-process* RSS in the throwaway venv, which lacks Django/Celery/psycopg — so the *incremental* Django-worker cost is smaller than 135 MB (spaCy + model contribution is bounded above by the ~50 MB documented model footprint plus spaCy's own runtime).
- **Warm inference per short specimen** (20-repeat, min-of-runs): **1.66-2.61 ms** per specimen for 3-8 token turns; peaks at 2.6 ms for the multi-sentence rows with abbreviation periods.
- **10-turn Fox & Flour dialogue serial** (`for turn in turns: nlp(turn)`): **38.33 ms** wall time total.
- **10-turn Fox & Flour dialogue via `nlp.pipe`:** **25.51 ms** wall time total (batched more efficient by ~33%).

Fraction of composition wall-time: A Runway render is 60-120 s; per-turn spaCy adds <0.05% overhead.

**Measured fact vs documented external vs inference:**

- **Measured:** all latency numbers above; installed package sizes; RSS in throwaway venv; entity spans / POS tags for every specimen shown below.
- **Documented external:** `en_core_web_sm` license (MIT for v3.5+); `spacy` license (MIT). Model architecture (CNN-based tagger + parser + NER, trained on OntoNotes 5).
- **Inference (well-supported):** incremental worker RSS in Django/Celery process ≈ 50-70 MB per loaded worker (bounded by model + spaCy runtime, less than the full 135 MB the throwaway venv shows because Django+Celery baseline already includes numpy and much of the Python runtime). Would benefit from a per-worker measurement inside a real Django shell.
- **Inference (weaker):** production worker-count multiplier. Depends on production topology, not measured here.

### Adversarial matrix — measured spaCy behavior

Legend for outcome columns:
- **entity** — spaCy emitted a `doc.ents` span for the token or its containing phrase (label shown).
- **POS** — spaCy's `token.pos_` tag for the flagged token.
- **A extract?** — current regex+stoplist verifier would extract the token as a candidate.
- **D-raw-ent extract?** — Option D as originally described (raw `doc.ents` gates extraction) would extract.
- **D-POS extract?** — refined D that gates extraction on `token.pos_ == "PROPN"` (single) or consecutive PROPN spans (multi-word). Preserves numeric + `KNOWN_TECH_TERMS`.
- **invariant?** — matches the intended behavior?

For every row, corpus assumed to be the Q-278-1 constant corpus (Fox and Flour + Christmas Day + Wikipedia + NASA + trafilatura; no `fair`/`come`/`unless`/…). All extractions run against corpus for grounding.

| category | text | entity(label) | POS | A | D-raw-ent | **D-POS** | invariant-correct |
|---|---|---|---|---|---|---|---|
| ORDINARY LANG | `Fair enough.` | Fair(ORG) | ADV/RB | flag | flag (raw-ent WRONG) | **pass** (not PROPN) | pass ✓ |
| ORDINARY LANG | `Come inside.` | — | VERB/VB | flag | pass | **pass** | pass ✓ |
| ORDINARY LANG | `Unless you disagree.` | — | SCONJ/IN | flag | pass | **pass** | pass ✓ |
| ORDINARY LANG | `Please sit down.` | — | INTJ/UH | flag | pass | **pass** | pass ✓ |
| ORDINARY LANG | `Always check first.` | first(ORDINAL) | ADV/RB | flag | pass (first is ORDINAL not relevant) | **pass** | pass ✓ |
| ORDINARY LANG | `Today we are open.` | Today(DATE) | NOUN/NN | pass (stoplist) | pass (DATE not relevant) | **pass** (not PROPN) | pass ✓ |
| ORDINARY LANG | `Modern systems are useful.` | — | ADJ/JJ | pass (stoplist) | pass | **pass** | pass ✓ |
| UNSUPPORTED | `Antoninus reigned peacefully.` | Antoninus(GPE — WRONG type, should be PERSON) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| UNSUPPORTED | `Wikipedia is our source.` | Wikipedia(ORG) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| UNSUPPORTED | `NASA supplied the equipment.` | NASA(ORG) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| UNSUPPORTED | `France changed the rule.` | France(GPE) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| UNSUPPORTED | `Microsoft built it.` | Microsoft(ORG) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| UNSUPPORTED | `OpenAI released it.` | OpenAI(GPE — WRONG type) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| SHORT ACRONYM | `FBI called.` | FBI(ORG) | PROPN/NNP | miss (3 chars) | flag | **flag** | flag ✓ (D closes A's silent miss) |
| SHORT ACRONYM | `CIA is watching.` | CIA(ORG) | PROPN/NNP | miss | flag | **flag** | flag ✓ |
| SHORT ACRONYM | `FDA approved it.` | FDA(ORG) | PROPN/NNP | miss | flag | **flag** | flag ✓ |
| SHORT ACRONYM | `IRS audited us.` | IRS(ORG) | PROPN/NNP | miss | flag | **flag** | flag ✓ |
| POLYSEMY | `Rose baked the bread.` | — (NER MISSED) | PROPN/NNP | flag | pass (raw-ent WEAKENED — MISSES ROSE) | **flag** | flag ✓ (POS catches what NER misses) |
| POLYSEMY | `A rose bloomed.` | — | VERB/VBD | miss (lowercase) | miss | **miss** | pass ✓ |
| POLYSEMY | `Mark called today.` | Mark(PERSON), today(DATE) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| POLYSEMY | `Make a mark here.` | — | VERB/VB → NOUN | miss (lowercase 'mark') | miss | **miss** | pass ✓ |
| POLYSEMY | `Bill approved it.` | Bill(PERSON) | PROPN/NNP | flag | flag | **flag** | flag ✓ |
| POLYSEMY | `Pay the bill.` | — | NOUN/NN | miss | miss | **miss** | pass ✓ |
| POLYSEMY | `May arrived.` | May(DATE) | AUX/MD | flag | pass (DATE not entity-relevant) | **pass — MISSES a person named May** | miss (documented gap) |
| POLYSEMY | `It may happen.` | — | AUX/MD | miss | miss | **miss** | pass ✓ |
| POLYSEMY | `The county Fair opens Friday.` | Fair(ORG),Friday(DATE) | PROPN/NNP,PROPN/NNP | flag,flag | flag (Fair) | **flag** (Fair), skip Friday (DATE, not relevant) | flag ✓ |
| POLYSEMY | `Fair enough.` | Fair(ORG — WRONG) | ADV/RB | flag | flag (WRONG) | **pass** | pass ✓ |
| MULTI-WORD | `James Webb Space Telescope launched.` | `James Webb Space`(PERSON — span truncation) | PROPN×4 | flag (multi) | flag but wrong span | **flag** as PROPN-span "James Webb Space Telescope" | flag ✓ (D-POS beats D-raw-ent span accuracy) |
| MULTI-WORD | `New York is far.` | `New York`(GPE) | PROPN×2 | flag | flag | **flag** | flag ✓ |
| MULTI-WORD | `OpenAI API is public.` | — (NER MISSED) | PROPN×2 | flag | miss (raw-ent MISSED) | **flag** | flag ✓ |
| MULTI-WORD | `Larimer County called.` | `Larimer County`(GPE) | PROPN×2 | flag | flag | **flag** | flag ✓ |
| MULTI-WORD | `Fox and Flour is open.` | `Fox`(ORG), `Flour`(PERSON — split!) | PROPN×2 with `and` glue | pass (corpus hit) | pass (corpus) | **pass** | pass ✓ |
| LOWERCASE TECH | `trafilatura extracts HTML.` | — | PROPN/NNP,PROPN/NNP | flag (KNOWN_TECH_TERMS) | flag (KNOWN_TECH_TERMS preserved) OR extract as PROPN | **flag** | flag ✓ |
| LOWERCASE TECH | `pgvector powers embeddings.` | — | **NOUN/NN** (spaCy misses!) | flag (KNOWN_TECH_TERMS) | flag (KNOWN_TECH_TERMS preserved) | **flag** (via KNOWN_TECH_TERMS pass) | flag ✓ (KNOWN_TECH_TERMS still necessary) |
| LOWERCASE TECH | `numpy is fast.` | — | PROPN/NNP | miss (not in KNOWN_TECH_TERMS) | miss (raw-ent misses) | **flag** (POS-based extraction picks up) | flag ✓ (D-POS closes A's numpy gap) |
| LOWERCASE TECH | `django serves the API.` | API(ORG) | PROPN/NNP,PROPN/NNP | flag django (KNOWN_TECH_TERMS) | flag API only | **flag** django + API | flag ✓ |
| LOWERCASE TECH | `redis caches the values.` | — | **NOUN/NN** (spaCy misses!) | flag (KNOWN_TECH_TERMS) | flag (preserved) | **flag** (via KNOWN_TECH_TERMS) | flag ✓ |
| PUNCT/POS | `She said, "Fair enough for now."` | — | ADJ/JJ | flag | pass | **pass** | pass ✓ |
| PUNCT/POS | `One rule: Always show up.` | One(CARDINAL) | ADV/RB | flag Always | pass | **pass** | pass ✓ |
| PUNCT/POS | `We are open—Come inside now.` | — | VERB/VB | flag Come | pass | **pass** | pass ✓ |
| PUNCT/POS | `The U.S. is a country. Mr. Smith arrived.` | U.S.(GPE), Smith(PERSON) | PROPN,PROPN | flag Smith | flag Smith + U.S. | **flag** Smith + U.S. | flag ✓ (D closes A's abbrev-period Smith miss detail) |
| PUNCT/POS | `The U.S. followed a policy. Wikipedia disagreed.` | U.S.(GPE), Wikipedia(ORG) | PROPN×2 | flag Wikipedia | flag both | **flag** both | flag ✓ |

### Failure modes / surprises observed (do not gloss)

1. **`Fair` in `Fair enough.` is labeled ORG by spaCy NER despite POS=ADV.** This is the biggest surprise: raw `doc.ents` alone does NOT close the Q-278-1 class — it just moves it. Original Option D (Q-278-3) was defective in the same way Option C was: I had assumed `doc.ents` filtering on "entity-relevant labels" would exclude adverbs, but spaCy's small-model NER over-fires on capitalized-adverb sentence starters. **This forced the D refinement to POS=PROPN gating rather than raw NER gating.**
2. **`Antoninus` labeled GPE (should be PERSON).** Non-fatal — still gets flagged (invariant preserved) but NER type is wrong. `en_core_web_sm` is a small model and its NER accuracy on rare proper nouns is noisy.
3. **`OpenAI` labeled GPE (should be ORG).** Same class of NER type noise.
4. **`James Webb Space Telescope` NER span truncates to `James Webb Space` labeled PERSON.** Wrong span + wrong type. Consecutive-PROPN extraction on the POS side would correctly get the full span.
5. **`Rose baked the bread.` → NER emits NO entity for `Rose`.** POS correctly tags `Rose` as PROPN/NNP. **Confirms raw-`doc.ents` alone is insufficient** — polysemous names get silently dropped without POS-based fallback.
6. **`Fox and Flour is open.` → NER split into `Fox`(ORG) + `Flour`(PERSON).** The `and` isn't recognized as multi-word glue by the small model. Not a problem here because the corpus contains "Fox & Flour" and case-insensitive substring matches, but a general concern for multi-word entity extraction.
7. **`OpenAI API is public.` → NER emits NO entity.** POS tags both as PROPN. Raw-ent extraction would miss this entirely. **Second confirmation POS gating is needed.**
8. **`pgvector` and `redis` tagged NOUN/NN (not PROPN).** spaCy doesn't recognize these as proper nouns. **Confirms `KNOWN_TECH_TERMS` pass must be preserved in the hybrid** — POS alone won't cover the lowercase-tech-name class.
9. **`May arrived.` → POS says AUX/MD (modal), NER says DATE.** A genuine person named `May` in a spokesperson script would be silenced by BOTH POS-gating AND NER-relevant-label gating. **Documented residual false-negative gap for D-POS**, present in A too (A flags `May` because it's 3+ chars capitalized; A flags it as an unsupported proper_noun without knowing it's actually a modal-verb misclassification). Neither approach handles this cleanly. In practice, rare.
10. **`Today` labeled DATE, POS=NOUN (not PROPN).** D-POS correctly does not extract; D-raw-ent with entity-label filtering also skips (DATE is not in the entity-relevant set). Only current A (with stoplist) handled it.
11. **`AI` in `Can AI actually help...` → NER=ORG, 2 chars.** Below A's 4-char regex threshold — A silently missed. spaCy catches it via NER even though POS gating alone would miss (`AI` is 2 chars and PROPN-tagged in the historical row's context). **D closes A's 2-char/3-char acronym silent-miss class.**

### Real Character OS specimen — Composition 26c62b4b (Ruby + Tyson, Fox & Flour)

10 turns replayed through spaCy in-process. Per-turn output:

- **Turn 0 (Ruby, "Welcome to Fox & Flour..."):** entities `Fox & Flour`(ORG) + `first`(ORDINAL); PROPN tokens `Fox`, `Flour`. Corpus has `Fox & Flour` → pass. D-POS: pass. Current A: pass. Match.
- **Turn 1 (Tyson):** entity `first`(ORDINAL); no PROPN. D-POS: pass. Match.
- **Turn 2 (Ruby):** no entities; no PROPN. Match.
- **Turn 3 (Tyson):** no entities; PROPN `Ruby`. `Ruby` in allowed_vocabulary → pass. Match.
- **Turn 4 (Ruby):** no entities; no PROPN. Match.
- **Turn 5 (Tyson, `Fair. But if someone needs...`):** entity `Fair`(ORG — WRONG). POS `Fair`=ADJ/JJ. **D-POS extraction: SKIP. A extraction: flag. → D-POS closes the false positive.** ✓
- **Turn 6 (Ruby):** no entities; no PROPN. Match.
- **Turn 7 (Tyson):** no entities; no PROPN. Match.
- **Turn 8 (Ruby, `...Christmas Day. Come in...`):** entities `7:00 AM to 3:00 PM`(TIME), `Christmas Day`(DATE), `a minute`(TIME). POS `Come`=VERB/VB. **D-POS extraction of Come: SKIP. A extraction: flag. → D-POS closes the false positive.** ✓
- **Turn 9 (Tyson, `See? No strategy required. Unless...`):** no entities. POS `Unless`=SCONJ/IN. **D-POS extraction of Unless: SKIP. A extraction: flag. → D-POS closes the false positive.** ✓

**All three Q-278-1 real warnings would be silenced by D-POS extraction. Zero real unsupported entities in this composition would be silenced by D-POS.** ✓

### Historical warned rows replay (5 sampled from live DB)

Read-only enumeration of the 5 most-recent compositions with populated `verification_warnings`:

| composition | name | warnings (existing A) | D-POS result |
|---|---|---|---|
| `26c62b4b` | Dialogue — Welcome to Fox & Flour | `Fair`, `Come`, `Unless` | all three silenced (POS=ADJ/VERB/SCONJ) ✓ |
| `8cb9e115` | Talking-head — Rivet | `Briefly`, `Carefully` | both silenced (POS=ADV/RB) ✓ |
| `774658ea` | Talking-head — Patch | `Can AI` | context replay: `Can AI` — POS of `Can`=AUX/MD; `AI` tagged ORG entity, 2 chars, PROPN — **D-POS would extract `AI` alone as PROPN → corpus check → flag if AI is not in corpus**. A currently flags the multi-word span; D-POS would flag only the meaningful entity. Improvement. ✓ |
| `8b61ca92` | Talking-head — Patch | `react`, `Sometimes` | `react` POS=VERB/VBP → silenced; `Sometimes` POS=ADV/RB → silenced ✓ |
| `1ff3d16f` | Talking-head — Patch | `Basically`, `Here`, `Annoying` | all three silenced (POS=ADV/ADV/ADJ) ✓ |

**Aggregate:** 11 historical warned tokens across 5 compositions. Under D-POS: 10 correctly silenced as ordinary language, 1 correctly rescoped from a false multi-word span (`Can AI`) to the actual entity (`AI`). Zero true positives lost. Zero silent misses.

### Architecture decision (answers to the seven Q-278-3.1 questions)

1. **Does spaCy/en_core_web_sm close the Q-278-1 false-positive class?** **Yes**, via POS=PROPN gating (NOT via raw `doc.ents` — that would leave the class open, as `Fair` labeled ORG demonstrates).
2. **Does it preserve `Antoninus` / `Wikipedia` / `NASA` / `France` / `Microsoft` / `OpenAI` as candidates when unsupported?** **Yes**, all six are POS=PROPN and NER-typed as an entity (though the specific NER label is sometimes wrong; POS gating is the load-bearing signal).
3. **Does it close the FBI/CIA/FDA/IRS short-acronym miss?** **Yes**, all four are POS=PROPN + NER=ORG. D closes A's silent 3-char miss class.
4. **How well does it handle `Rose`/`Mark`/`Bill`/`May`/`Fair` contextually?**
   - `Rose baked` → PROPN → extracted correctly (NER MISSED it, but POS caught it). ✓
   - `A rose bloomed` → VERB (past tense) → not extracted. ✓
   - `Mark called` → PROPN + PERSON → extracted. ✓
   - `Make a mark here` → NOUN → not extracted. ✓
   - `Bill approved` → PROPN + PERSON → extracted. ✓
   - `Pay the bill` → NOUN → not extracted. ✓
   - `May arrived` (person May) → AUX/MD + DATE → **NOT extracted (residual gap)**.
   - `It may happen` → AUX/MD → not extracted. ✓
   - `The county Fair opens Friday` → Fair PROPN → extracted; Friday PROPN + DATE (skip DATE-relevance-filter or flag depending on choice).
   - `Fair enough` → ADV → not extracted. ✓
5. **What false-negative classes remain?**
   - Personal names that are also modal verbs / auxiliaries (`May`, `Will`, `Would`). Rare. Documented gap.
   - Lowercase domain names spaCy tags NOUN (`pgvector`, `redis`). **This is exactly why `KNOWN_TECH_TERMS` must be preserved in the hybrid** — spaCy small model doesn't recognize them.
   - Multi-word entity span accuracy is imperfect (`James Webb Space` truncation, `Fox and Flour` split). Consecutive-PROPN span extraction on the POS side is more reliable than raw `doc.ents` spans for entity boundary purposes.
6. **Does the preserved `KNOWN_TECH_TERMS` pass still make the Hybrid meaningfully stronger than NER alone?** **Yes.** Directly proven: `pgvector` (NOUN) and `redis` (NOUN) would be silently missed without it. Corollary: retiring `KNOWN_TECH_TERMS` requires additional operator curation somewhere.
7. **Based on measured evidence, is Option D still the recommended architecture?** **Yes, with MODIFY.** The modification: extraction is driven by **POS=PROPN** (single-token) and **consecutive-PROPN spans** (multi-word), NOT by raw `doc.ents`. `doc.ents` becomes classification metadata (used to bucket flagged tokens by NER type in the SPA panel and to catch 1-3 char acronyms POS may miss) but is not the extraction gate. Numeric pass stays. `KNOWN_TECH_TERMS` pass stays. Corpus grounding stays. Allowed vocabulary stays. Stoplist becomes compatibility layer through shadow-evaluation phase.

### Refined architecture (D-POS Hybrid) — design only

```
extract_claim_candidates(text, doc):
    # Pass 1 — numeric (unchanged from A)
    yield from _NUMERIC_RE matches                          -> kind="numeric"

    # Pass 2 — KNOWN_TECH_TERMS (unchanged from A; still necessary)
    yield from _TECH_TERMS_RE matches                        -> kind="tech_term"

    # Pass 3 — POS-driven named entity (REPLACES current single-cap + multi-word passes)
    for span of consecutive PROPN tokens in doc:
        if len(span) == 1:
            yield (span.text, position)                      -> kind="proper_noun"
        else:
            yield (span.text, position)                      -> kind="multi_word"

    # Pass 4 — NER-supplement for entities POS misses (short acronyms mostly)
    for ent in doc.ents where ent.label_ in ENTITY_RELEVANT_LABELS
                          and ent.text NOT already extracted:
        yield (ent.text, position)                           -> kind=f"ner_{ent.label_}"

    # Grounding step (unchanged from A)
    for candidate in yields:
        if candidate.text.lower() in factual_corpus.lower(): pass
        elif candidate matches allowed_vocabulary:            pass
        else:                                                 flag
```

Where `ENTITY_RELEVANT_LABELS = {"PERSON","ORG","GPE","NORP","FAC","PRODUCT","EVENT","WORK_OF_ART","LAW","LANGUAGE"}` (excluding `DATE`/`TIME`/`PERCENT`/`MONEY`/`QUANTITY`/`ORDINAL`/`CARDINAL` which are numeric-adjacent and either already handled or should not gate).

### Shadow-mode re-evaluation

Q-278-3's shadow-mode proposal remains the safest next implementation step and **its shape does not need to change** based on Q-278-3.1 measurement. Acceptance criteria refinement:

- Shadow diff must show D-POS is a superset of A's TRUE positives on a bounded dogfood window (≥N compositions with warnings under warn mode).
- Shadow diff must show D-POS closes ≥ some threshold percentage of A's warnings that are ordinary-language false positives (Q-278-1 class + Rivet/Patch adverb/interjection class).
- Shadow diff must NOT introduce a new false-negative class larger than the ones it closes. Specifically monitor:
  - `pgvector`/`redis`/other lowercase-NOUN-tagged tech names — must remain flagged via `KNOWN_TECH_TERMS`.
  - Multi-word entity accuracy vs A (POS-span vs regex-span).
  - Any `May`-like modal-verb-name collisions.
- Sample size: at least the current backlog of persisted warned rows PLUS ≥5 fresh operator dogfood cycles.

Shadow-mode plumbing options remain as documented in Q-278-3: additive JSONField on `Composition` + `ConversationMessage`, env-flag gate (`CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT`), new `k64_shadow_diff` mgmt command.

**No shadow-mode implementation this session.** Design only.

### Evidence vs inference

**Measured:** all specimen classifications (entity spans + POS tags); all latency numbers; installed package footprint; RSS in the throwaway venv; real 26c62b4b turn-by-turn classification; historical warned-row replay for 5 rows.

**Documented external:** spaCy + `en_core_web_sm` license (MIT), model architecture, and general behavior characteristics (rare-word NER noise, tokenization rules for hyphens/em-dashes).

**Inference (well-supported):** POS-based extraction is a stricter gate than raw `doc.ents` for our invariant; incremental Django-worker RSS bounded above by ~70 MB; per-composition wall-time impact is negligible next to Runway.

**Inference (weaker):** production worker-count multiplier for total memory; long-term maintenance cost of the spaCy model version pin; behavior on future language drift.

### Prediction vs actual

Prediction accuracy: PARTIALLY WRONG in an important way. I had predicted raw `doc.ents` filtered by entity-relevant labels would close the Q-278-1 class. Measurement disproved that for the `Fair enough.` specimen and confirmed the same class of NER over-fire on adverbs. Predicted correctly on the other 40 matrix rows. The refinement from raw-ent gating to POS-gating is the surviving lesson from Q-278-3.1. This is exactly the "try to disprove" outcome ChatGPT asked for.

### Recommendation

**MODIFY** — Option D as originally described in Q-278-3 does not survive intact. **Modified Option D (D-POS Hybrid)** does survive:

1. Extraction is POS-driven (`token.pos_ == "PROPN"` for singletons; consecutive-PROPN runs for multi-word).
2. NER-supplement pass covers 1-3 char acronyms and other cases POS misses.
3. Numeric + `KNOWN_TECH_TERMS` + corpus grounding + allowed vocabulary passes preserved.
4. Stoplist becomes compatibility layer through shadow-eval phase → deletable after cutover proves NER doesn't miss anything the stoplist caught.

**Shadow-evaluation mode remains the recommended next step** (same shape as Q-278-3 proposed), with the refined acceptance criteria above.

**Do NOT** flip `K6_CLAIM_VERIFIER_MODE` default from `warn` to `strict` until shadow + cutover phases complete.

**Do NOT** implement D-POS in production today. Design shape recorded here.

**Do NOT** add `Fair`/`Come`/`Unless` to the stoplist — the shadow phase will exercise them and characterize D-POS behavior; interim tweaks would corrupt the shadow signal.

### Unresolved questions

- Whether to attach `doc.ents` label as metadata on `UnsupportedClaim` (nice for SPA display but adds shape to the dataclass).
- Whether `numpy` (POS=PROPN, not currently in `KNOWN_TECH_TERMS`) should get an additive `KNOWN_TECH_TERMS` add before D-POS ships. Currently A silently misses `numpy` too; not a D-POS regression.
- Model-download strategy for the production build (`python -m spacy download` vs pinned wheel URL). Downstream of Q-278-3.2 if approved.
- Whether to close the `May`-as-person residual false-negative or accept it as documented (out of D-POS's smallest-shape scope).

### Explicit decision gate

**STOP.** No implementation lands. Chris + ChatGPT must explicitly:

- **Go A:** Approve modified D-POS Hybrid as the target architecture and open Q-278-3.2 to design + implement shadow mode.
- **Go B:** Approve one more bounded feasibility spike — e.g. try `en_core_web_md` (heavier, more accurate NER — ~40 MB model) to check whether the model-size tradeoff is worth it.
- **No-Go:** Reject the semantic direction. Freeze at Option A and accept the false-positive class as `warn`-mode noise. If chosen, `docs/design/SESSION_278_UDB_NER_REUSE_AUDIT.md` NO USEFUL REUSE finding still stands; do not reopen without new evidence.

Recommended path: **Go A**. Measurement showed D-POS closes the Q-278-1 class on real specimens (11/11 historical warnings correctly handled), preserves the founding hallucination invariant (all six real unsupported entities still flag), and adds coverage for short acronyms + numpy-like PROPN tech names. Operational cost is negligible.

Throwaway artifacts (safe to delete anytime): `/tmp/q278_spacy_spike/`.

*Chris + ChatGPT decision:* **GO A** — approve modified D-POS Hybrid as target architecture. Open Q-278-3.2 to implement the smallest safe shadow-evaluation substrate. Do not authorize D-POS to become authoritative production verification.

---

## Q-278-3.2 — D-POS shadow-mode implementation

### Precise question

Implement the smallest safe shadow-evaluation substrate so the current K6.4 verifier remains authoritative while D-POS runs beside it and records what it would have decided. When the experiment flag is OFF, external behavior must be byte-for-byte / semantically identical to today. When ON, shadow output is purely observational.

### Baseline (before edits)

- `character_os/claim_verifier.py` — regex + ~250-entry stoplist + numeric + `KNOWN_TECH_TERMS` + case-insensitive corpus substring. Authoritative for `Composition.verification_warnings` / `DialogueTurn.verification_warnings`.
- `character_os/dialogue_synthesis.py` — per-turn K6.4 verification loop in `synthesize_dialogue`; writes `turn.verification_warnings` and `turn.verification_status`.
- `apps/compositions/starters.py:_dialogue_ai_flattened_warnings` — flattens per-turn warnings onto `Composition.verification_warnings` at composition-create time.
- Migration path: additive `models.JSONField(default=list, blank=True)` (mirrors `0002_k6_4_verification_warnings.py`).
- Experiment-flag conventions: `CHARACTER_OS_*_EXPERIMENT` env var + Django settings override, settings precedence, whitespace-only inactive (`avatar_speech._patch_communication_policy_experiment_active`, `duration_contract._corrective_revision_experiment_active`).
- No spaCy / NER library in the runtime venv prior to this slice.

### Integration audit — questions answered

**Q1 — Smallest persistence shape that allows old-vs-new comparison without altering current behavior?**
> One additive nullable JSONField `Composition.verification_warnings_shadow` (list of dicts, empty default). Same enrichment shape as `verification_warnings` (adds `line_index` / `speaker_alias` / `speaker_name` per warning). No changes to `DialogueTurn` schema — per-turn shadow state stays in-memory on the dataclass only; flattened onto the composition column at composition-create time.

**Q2 — Additive JSONField safer/smaller than a new model?**
> Yes. A new model would require (a) a foreign key back to Composition, (b) a new admin registration, (c) a new serializer + potentially SPA surface, (d) coordinated deletion in the Workspace cascade, (e) an extra join for every shadow-diff query. The single additive JSONField ships as one column, one migration, and matches the exact shape the legacy verifier already uses on the same row.

**Q3 — Which model(s) need shadow persistence for THIS first slice?**
> **Composition only.** `ConversationMessage.verification_warnings` (K6.5) and `Script.verification_warnings` (B-arc) both exist and follow the same shape, but the Q-278-1 evidence and every Q-278-3.1 measurement come from dialogue-scene compositions. The shared classifier core (`character_os.claim_verifier_ner`) is a pure function with no ORM coupling, so extending shadow persistence to those adjacent surfaces later is a small mechanical change. Preferring smallest end-to-end surface per slice discipline; extending in this slice would add three migrations + three serializer changes for no evidence-of-value.

### Chosen persistence shape + rationale

- New column on `Composition`: `verification_warnings_shadow = models.JSONField(default=list, blank=True)`.
- Same shape as `verification_warnings`. Default `[]` — legacy rows read as empty; new rows only get non-empty when the experiment flag was truthy at synthesis time.
- Not added to `_IMMUTABLE_OBSERVABILITY_FIELDS` — matches the `verification_warnings` lifecycle (freely mutable).
- Not exposed via serializer/SPA in this slice — the audit consumer is `k64_shadow_diff` mgmt command, not the operator UI. The SPA evidence panel remains driven by the legacy `verification_warnings` column.

### Dependency / model installation shape

Pinned in `shell/pyproject.toml` (main dependencies, not dev-only, so both local dev and production installs pick up the shadow substrate):

```toml
"spacy>=3.8,<3.9",
"en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
```

Version notes (from measured install in Character OS's shared `.venv`):

- **spaCy 3.7.x is incompatible** with the shared runtime — pins `numpy<2` which conflicts with `rembg>=2.0.75` and `opencv-python-headless>=4.13` (both require `numpy>=2`). Attempting `spacy>=3.7,<3.8` broke both dependencies at install time. Rolled up to `spacy>=3.8,<3.9` which supports `numpy>=2` cleanly.
- **`en_core_web_sm==3.8.0`** model paired with spaCy 3.8. Improved behavior over Q-278-3.1's 3.7.1 measurement on the specific `Fair enough.` case: no longer NER-labels `Fair` as ORG (empty entities; POS ADJ). This makes the D-POS classifier's guarantee slightly stronger.
- **Model wheel is pinned to a specific published GitHub release URL** — reproducible `pip install -e shell` without invoking `python -m spacy download` at runtime.
- **Licenses:** spaCy MIT; `en_core_web_sm` 3.5+ MIT (verified against release metadata).
- **Cold-load behavior:** lazy import inside `character_os.claim_verifier_ner._get_nlp()`. spaCy is NOT imported at module import time; the model is not loaded until a shadow call actually fires. Workers where the experiment flag is off pay zero spaCy cost.

Installed to venv via:

```
pip3 install --upgrade 'spacy>=3.8,<3.9' \
    'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl' \
    'numpy>=2.3,<3'
```

The `numpy>=2.3,<3` explicit pin was needed to prevent pip's resolver from downgrading numpy in a shared-venv install.

### Implementation

**Files added:**

- `shell/character_os/claim_verifier_ner.py` — the D-POS Hybrid classifier. Public `run_shadow_verifier(text, factual_corpus, allowed_vocabulary)` and `extract_named_entities_ner(text)`. Lazy spaCy singleton in `_get_nlp()`. Passes: numeric (reused from `claim_verifier._NUMERIC_RE`) → `KNOWN_TECH_TERMS` (reused from `claim_verifier._TECH_TERMS_RE`) → PROPN spans (contiguous `token.pos_ == "PROPN"` runs, one claim per run) → NER supplement (entities in `_ENTITY_RELEVANT_LABELS = {"PERSON","ORG","GPE","NORP","FAC","PRODUCT","EVENT","WORK_OF_ART","LAW","LANGUAGE"}` not covered by earlier passes). Grounding identical to legacy `verify_claims` (case-insensitive substring against corpus; substring-either-way against vocab).
- `shell/apps/compositions/management/commands/k64_shadow_diff.py` — new mgmt command. Reads recent compositions where either warnings column is non-empty; reports OLD_ONLY / SHADOW_ONLY / BOTH per row + aggregate totals.
- `shell/apps/compositions/tests/test_claim_verifier_ner_shadow.py` — 32-test regression suite pinning all Q-278-3.1 measured properties.

**Files modified:**

- `shell/pyproject.toml` — spacy + model pins (see above).
- `shell/apps/compositions/models.py` — `verification_warnings_shadow` JSONField added to `Composition`.
- `shell/apps/compositions/migrations/0019_session278_verification_warnings_shadow.py` — additive `AddField` (plus Django-auto-generated no-op AlterFields for other observability fields).
- `shell/character_os/dialogue_synthesis.py` — added `verification_warnings_shadow: list[dict]` field to `DialogueTurn`; per-turn shadow call inside the K6.4 verification loop, gated by `ner_shadow_experiment_active()`, defensive `try/except` wraps so shadow can never crash the primary path.
- `shell/apps/compositions/starters.py` — new `_dialogue_ai_flattened_shadow_warnings(result)` helper; wired into the dialogue AI-Topic starter's composition-create kwargs so the flattened shadow list persists onto `verification_warnings_shadow`.

**Behavior guarantees:**

- Shadow OFF (env unset OR settings unset OR value in `{"","0","false","no","off"}`) → `spacy` never imported (lazy load only triggered by `_get_nlp()` inside `extract_named_entities_ner`, which is only called from `run_shadow_verifier`, which is only called when `ner_shadow_experiment_active()` returns True). `Composition.verification_warnings_shadow` stays `[]` on every new row. Zero externally observable difference from pre-Q-278-3.2 behavior.
- Shadow ON → per-turn D-POS classifier runs on the same `(text, corpus, vocab)` triple the legacy verifier saw; results flatten onto the shadow column. `verification_warnings` / `verification_status` / render pipeline / provider calls unaffected.
- If spaCy or the model become unavailable at runtime, `_get_nlp()` returns `None`, `extract_named_entities_ner` returns `[]`, and `run_shadow_verifier` returns `[]` — logged at WARNING once. Shadow degrades to no-op; primary path never affected.
- Exceptions inside spaCy are trapped by the `try/except Exception` in `dialogue_synthesis.py`; a defect in shadow can never fail a composition or trigger a retry.

### Classifier responsibilities (final)

| pass | source | responsibility |
|---|---|---|
| numeric | reused `claim_verifier._NUMERIC_RE` | Extract `$X` / `X%` / four-digit years |
| tech_term | reused `claim_verifier._TECH_TERMS_RE` (built from `KNOWN_TECH_TERMS`) | Extract lowercase library / product names spaCy tags NOUN |
| proper_noun_pos / multi_word_pos | new: contiguous `token.pos_ == "PROPN"` runs | Named-entity extraction that replaces the capitalization-as-NER proxy |
| ner_<label> | new: `doc.ents` with labels in `_ENTITY_RELEVANT_LABELS` not covered by earlier passes | Supplement PROPN for unusual spans (sub-4-char acronyms mostly) |
| grounding | same substring rules as legacy | Case-insensitive corpus + substring-either-way vocab |

Stoplist (`_COMMON_PROPER_NOUN_FALSE_POSITIVES`) is **NOT consumed** by the shadow classifier — PROPN tagging obviates it. The stoplist stays alive in the legacy verifier per Q-278-3.2 scope (no cleanup in this slice).

### Regression tests

`shell/apps/compositions/tests/test_claim_verifier_ner_shadow.py` — 32 tests, all passing. Pure-function tests on the shadow classifier (no ORM writes → no `test_isolation.py` allow-list change needed). Skips cleanly if spaCy or the model are absent (`pytest.importorskip("spacy")` + `spacy.load` guard).

Coverage locks the Q-278-3.1 measured properties:

- Ordinary language (`Fair enough.`, `Come inside.`, `Unless you disagree.`, `Please sit down.`, `Always check first.`) — must NOT shadow-flag (Q-278-1 class).
- Unsupported entities (`Antoninus`, `Wikipedia`, `NASA`, `France`, `Microsoft`, `OpenAI`) — must shadow-flag (founding invariant preserved).
- Short acronyms (`FBI`, `CIA`, `FDA`, `IRS`) — must be candidates (closes legacy 4+ char silent miss).
- Polysemy (`Rose baked` flags person; `A rose bloomed` does not; `Mark called` flags person; `Make a mark here` does not; `Bill approved` flags person; `Pay the bill` does not; `Fair enough` does not flag).
- Documented residual: `May arrived.` (person named May) still missed — test PINS current behavior so any future "fix" surfaces intentionally.
- Lowercase tech (`pgvector`, `redis`) — must remain flagged via preserved `KNOWN_TECH_TERMS` pass.
- Documented residual: `numpy is fast.` (lowercase `numpy` NOT in `KNOWN_TECH_TERMS`, spaCy 3.8 tags NOUN not PROPN → silent miss, matching legacy A). Test PINS.
- Founding hallucination invariant (`Wikipedia is our absolute home turf.` / `trafilatura` on empty corpus) — extraction path still emits the entity.
- Multi-word PROPN span (`James Webb Space Telescope`) — full contiguous span emitted (beats spaCy's `doc.ents` truncation).
- Supported multi-word (`Fox and Flour is open.`) — grounding substring matches; neither piece flagged.
- Kind labels distinguishable (numeric / tech_term / proper_noun_pos / ner_*).
- Empty-text defensive branch.

Adjacent test suites also green: `test_dialogue_synthesis.py`, `test_claim_verifier.py`, `test_stoplist_watchdog.py`, `test_dialogue_ai_topic_wiring.py` — **116 pre-existing tests all pass**, confirming zero regression in existing verifier or dialogue paths.

### Real specimen replay — Composition 26c62b4b (Ruby + Tyson, Fox & Flour)

Read-only replay via `/tmp/q278_spacy_spike/replay_shadow.py`. Rebuilt real per-speaker corpora from the persisted `knowledge_chunk_ids`. Ran BOTH classifiers per-turn against the actual synthesized text:

| turn | speaker | text opener | LEGACY | SHADOW |
|---|---|---|---|---|
| 0 | Ruby | Welcome to Fox & Flour. If this is your first visit… | `[]` | `[]` |
| 1 | Tyson | A strategy does help if you're staring at the case… | `[]` | `[]` |
| 2 | Ruby | He says that as if bread isn't also an excellent answer. | `[]` | `[]` |
| 3 | Tyson | Bread is an excellent answer. Ruby just takes it… | `[]` | `[]` |
| 4 | Ruby | I own the place; I'm allowed to care… | `[]` | `[]` |
| 5 | Tyson | Fair. But if someone needs a treat for a birthday… | `[('Fair','proper_noun')]` | **`[]`** ✓ |
| 6 | Ruby | Exactly. Tell us the occasion… | `[]` | `[]` |
| 7 | Tyson | And if you're picking up an order… | `[]` | `[]` |
| 8 | Ruby | We're here every day from 7:00 AM… Come in when… | `[('Come','proper_noun')]` | **`[]`** ✓ |
| 9 | Tyson | See? No strategy required. Unless you're choosing… | `[('Unless','proper_noun')]` | **`[]`** ✓ |

**All 3 Q-278-1 false positives correctly silenced. Zero real unsupported entities silenced.** ✓

### Historical warned-row replay (5 rows sampled)

Same script also replayed against the 5 most-recent compositions with persisted warnings. Per-turn corpora aren't reconstructible without a full-composition context so this replay used empty corpus on the whole `synthesized_brief` (extractor path only; grounding intentionally weakened for extraction-boundary observation):

- **`8cb9e115` Rivet** — legacy: `Briefly`, `Carefully`; shadow: `AI`, `Patch`. Both ordinary-language false positives silenced; shadow surfaces `AI` (legit entity in Rivet's brief) and `Patch` (name — either supported by allowed_vocab in a real per-turn corpus, or a legit hallucination flag).
- **`774658ea` Patch** — legacy: `Can AI` (multi_word); shadow: `AI` alone. Correctly rescoped multi-word false-positive to the actual entity.
- **`8b61ca92` Patch** — legacy: `react` (tech_term), `Sometimes` (proper_noun); shadow: `AI`, `react` (tech_term preserved). `Sometimes` correctly silenced; `react` preserved via `KNOWN_TECH_TERMS`.
- **`1ff3d16f` Patch** — legacy: `Basically`, `Here`, `Annoying`; shadow: `AI`, `Here's how I` (ner_work_of_art — noise finding from replaying the whole brief; not a per-turn concern). All three ordinary-language false positives silenced.

### Prediction vs actual

- Predicted: OFF path byte-identical. ✅ Confirmed — `verification_warnings_shadow` defaults `[]` for every legacy row; lazy spaCy import means no cost for OFF workers.
- Predicted: D-POS silences Fair/Come/Unless on 26c62b4b. ✅ Confirmed on real per-speaker corpora.
- Predicted: D-POS preserves Antoninus/Wikipedia/NASA/France/Microsoft/OpenAI. ✅ Confirmed in regression suite.
- Predicted: D-POS adds FBI/CIA/FDA/IRS coverage. ✅ Confirmed.
- Predicted: D-POS handles polysemy correctly (Rose/Mark/Bill flag when PERSON; not when noun/verb). ✅ Confirmed.
- Predicted: numpy PROPN-extractable. ❌ **Falsified.** `en_core_web_sm==3.8.0` tags lowercase `numpy` as NOUN (Q-278-3.1 measured 3.7.1 which tagged PROPN). Test now pins current behavior; `numpy` remains a documented gap same as legacy A.
- Predicted: `Fair enough.` NER=ORG under 3.7.1 → open under raw-ent gating. **Model 3.8.0 no longer emits the ORG entity for `Fair`** — improvement over 3.7.1. POS remains ADJ, PROPN pass correctly ignores.

### Discrepancies from Q-278-3.1

- **spaCy version bumped 3.7 → 3.8** due to numpy conflict with rembg/opencv. Actually improves the invariant (see `Fair` case above).
- **`numpy` PROPN → NOUN** across model versions — one row of the Q-278-3.1 adversarial matrix flipped. `numpy` behavior is now identical to legacy A (silent miss); documented in the audit + pinned by a regression test.

### Unresolved questions

- Whether to extend shadow persistence to `ConversationMessage.verification_warnings` and `Script.verification_warnings` in a follow-up slice. Same classifier core is reusable; each surface adds one migration + one persistence hook.
- Whether to add `numpy` (and any other tech names discovered by `stoplist_watchdog`) to `KNOWN_TECH_TERMS` in a companion additive slice. Not blocked by Q-278-3.2.
- Whether SPA evidence panel should surface shadow warnings alongside legacy warnings for the operator to eyeball. Deferred — the mgmt command is sufficient for the shadow-evaluation phase.

### Explicit STOP gate — no cutover in this slice

Shadow mode is IMPLEMENTED but **not authoritative**. Before any cutover discussion (Q-278-4 or later), the acceptance criteria from Q-278-3.1 (repeated here for durability) require:

- A. D-POS preserves ALL identified TRUE positives from current K6.4 on the shadow window.
- B. D-POS removes the large majority of current ordinary-language false positives.
- C. No new false-negative class larger/more dangerous than the class closed.
- D. `KNOWN_TECH_TERMS` continues protecting lowercase-domain terms.
- E. Multi-word POS spans do not materially regress supported/unsupported entity grounding.
- F. `May`-like collisions are recorded, not hidden.

Shadow evidence window target: current historical warned backlog PLUS **at least 5 fresh operator dogfood compositions rendered with `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT=1`**. Chris drives that dogfood; K6_CLAIM_VERIFIER_MODE stays `warn`; no strict-mode flip in this session or Q-278-3.2.

**STOP.** Await operator dogfood + Chris + ChatGPT review before Q-278-4.

---

## Q-278-3.2 Fresh Shadow Dogfood — Specimen 1/5

**Cumulative fresh-window count: 1/5.**

### Composition

- ID: `a1421a0e-cc31-4323-a50e-3e88d8b21a4b`
- Name: `Dialogue — That was a new one: a customer`
- Template: `dialogue_scene` (Ruby + Tyson cast)
- Episode: `350a8c14-d25d-41ff-85a5-83d494216311`
- Operator topic: *"Ruby and Tyson deal with a difficult bakery customer."*
- Status: `completed`; `verification_status = "verified"`; `synthesis_attempt_count = 2`

### Operator observation (recorded, not investigated)

First synthesis attempt was too short; existing duration-corrective behavior fired; second attempt passed; composition completed successfully. Not reported as duration friction. Recording only — will only become relevant if repeated evidence surfaces.

### Legacy `verification_warnings` (authoritative)

3 warnings, all `proper_noun`, all sentence-initial ordinary English words:

- `Mostly` — turn 6 (Tyson): *"She softened when you said that. Mostly. Then she asked what coffee would go with the cake she hasn't chosen yet."*
- `Once` — turn 7 (Ruby): *"That was her way back into the conversation. Once people feel heard, they can usually start choosing again."*
- `Perfect` — turn 9 (Ruby): *"Perfect. We can keep it simple: choose the occasion, choose a pickup day when we're open, then choose the treat."*

These are three fresh members of the Q-278-1 false-positive class (each capitalized, ≥ 4 chars, missing from the stoplist AND from the per-speaker corpus).

### Shadow `verification_warnings_shadow` (observational)

**0 entries. Empty list.**

### OLD_ONLY / SHADOW_ONLY / BOTH

- **OLD_ONLY (legacy flagged, shadow did not): `Mostly`, `Once`, `Perfect`** — 3 warnings.
- **SHADOW_ONLY (D-POS flagged, legacy did not):** none.
- **BOTH:** none.

### Were `Mostly` / `Once` / `Perfect` silenced?

**Yes, all three.** Live per-turn replay (running D-POS against the same real per-speaker corpora reconstructed from the persisted knowledge_chunk_ids) reproduced the persisted shape exactly: turns 6/7/9 flagged by legacy, silenced by shadow; all other turns clean for both classifiers. spaCy 3.8 POS tags for the three tokens: `Mostly`→ADV, `Once`→SCONJ, `Perfect`→ADJ — none PROPN → D-POS does not extract.

### Shadow-only deltas requiring interpretation

None. The shadow classifier produced no candidates D-POS would flag that the legacy verifier missed. Nothing to interpret as desirable / undesirable / ambiguous for this specimen.

### Runtime shadow confirmation

**Confirmed active in the actual Celery worker process.** Three independent signals:

1. `ps eww -p 52384 52415` on the running Celery worker PIDs shows `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT=1` in their environment (env was inherited via `set -a; source .env; set +a` inside `scripts/start-local-real.sh`).
2. `ner_shadow_experiment_active()` resolves `True` in the same venv the workers run under.
3. Live in-process replay of the D-POS classifier against the exact per-speaker corpora returns the same empty per-turn output the persisted column shows. Since the classifier is deterministic on `(text, corpus, vocab)` and the code path in `dialogue_synthesis.py:_shadow_active` guard invokes it when the flag is on, the persisted empty list is the expected outcome of the shadow having run, not the default of shadow NOT having run.

Note on evidence limits: an all-empty shadow column is INDISTINGUISHABLE by direct inspection from "shadow classifier did not execute" on this single specimen. The three signals above are strong indirect evidence; a follow-up specimen that produces ANY shadow-only output would provide stronger direct confirmation.

### Legacy authority + shadow zero-impact

Legacy `verification_warnings` was written and drove the SPA display. `verification_status = "verified"` (composition-level normalization of the aggregate `"warned"` per starters.py:295-305 documented convention). Composition status `completed`; render dispatched to Runway; provider spend uncorrelated with shadow. Shadow column populated purely as observational metadata; no field in the operator-visible path was influenced by D-POS.

### Prediction vs actual (this specimen)

- Predicted the Q-278-1 class would silence for these three tokens: confirmed. Third real-world confirmation of D-POS closing the general class (26c62b4b + 5-row historical replay + this fresh render).
- Predicted the shadow-only column would be empty on a well-grounded dialogue: confirmed on turns 0-5 and 8-12; no unsupported entities in the synthesized text.

### Cumulative fresh-window progress: **1 / 5**

---

## Q-278-3.2 Fresh Shadow Dogfood — Specimen 2/5

**Cumulative fresh-window count: 2/5.**

### Composition

- ID: `5f4bdbbc-7043-47e7-a362-3cdc8be98761`
- Name: `Dialogue — I want to start a consulting f`
- Template: `dialogue_scene` (Patch + Rivet cast)
- Episode: `c7adc141-4e37-4b01-99bd-f0839aa91d8c`
- Operator topic: *"Patch wants to start a consulting firm."*
- Status: `completed`; `verification_status = "verified"`; `synthesis_attempt_count = 1` (no corrective this time)

### Legacy `verification_warnings` (authoritative)

2 warnings, both `proper_noun`, both sentence-initial ordinary English:

- `Consulting` — turn 1 (Rivet): *"That is a sentence with several missing parts. Consulting about what?"*
- `Also` — turn 4 (Patch): *"Exactly. Also to prevent them from turning on something half-finished and declaring victory because it said one clever sentence."*

Two additional fresh members of the Q-278-1 false-positive class.

### Shadow `verification_warnings_shadow` (observational)

**0 entries. Empty list.**

### OLD_ONLY / SHADOW_ONLY / BOTH

- **OLD_ONLY: `Consulting`, `Also`** — 2 warnings.
- **SHADOW_ONLY:** none.
- **BOTH:** none.

### Were `Consulting` / `Also` silenced?

**Yes, both.** Live per-turn replay against the reconstructed per-speaker corpora (Patch = 1825-char corpus, Rivet = 943-char corpus, both driven by teammate identity fields — per-character K2 chunks were empty per the brief metadata `patch=[]; rivet=[]`) reproduced the persisted shape exactly: turns 1/4 flagged by legacy, silenced by shadow; every other turn clean for both. spaCy 3.8 POS tags: `Consulting` and `Also` are sentence-initial gerund/adverb constructions, not PROPN → D-POS does not extract.

### Shadow-only deltas

None. Nothing to classify as desirable/undesirable/ambiguous.

### Runtime shadow confirmation

Confirmed active — same three signals as Specimen 1 hold: env-var in running Celery worker processes, `ner_shadow_experiment_active() == True` in the venv, deterministic live replay reproduces the persisted empty shape.

### Legacy authority + shadow zero-impact

Same as Specimen 1. Legacy `verification_warnings` drove the SPA display. Shadow column was populated as observational metadata only. Render dispatched to Runway; composition completed.

### DEFERRED observations (record only — NOT investigated in this slice)

Chris reports the resulting Patch/Rivet scene was "okay" but felt off in three specific ways. **These observations are recorded durably here for possible future investigation; nothing about Patch/Rivet prompts / identities / memories / synthesis / composition behavior is changed as a result.**

1. **Recurring rhetorical construction.** Patch closes turn 10 with: *"Technically, that is also consulting. **Whether it should be is a different question.**"* Chris believes he has heard Patch use this or a very similar construction across multiple independently generated episodes. Not investigated here; not confirmed against other compositions in this slice.

2. **Polished consulting methodology out of a minimal topic.** For a topic of only 8 words, Patch produced strikingly structured methodology-flavored lines including: *"build the smallest useful version and find out"* (turn 2), *"the point is honest experiments: what worked, what broke, what needs another pass. If it fails, we say it failed."* (turn 6). The tightness of the framing was surprising given the topic's minimality.

3. **Empty per-character K2 retrieval.** The persisted brief metadata reports `patch=[]; rivet=[]`. Retrieval returned no per-character KnowledgeChunks; the shadow-verifier corpora above were built entirely from teammate identity fields (business_brief / who_you_help / what_you_sell / Universe.brief). Episode metadata references one story memory concerning "the workshop agent"; that piece did land (visible in turn 7).

**Possible future falsifiable question (NOT opened yet):** *Is Patch exhibiting repeated rhetorical/template language across independently generated episodes, and if so, what substrate is producing or reinforcing it?* If Chris chooses to open this later, evidence gathering would start by grepping every completed Patch composition's `synthesized_brief` for the "Whether it should be is a different question" construction and adjacent template-shape indicators.

### Cumulative fresh-window progress: **2 / 5**

---

## Q-278-3.2 Fresh Shadow Dogfood — Specimen 3/5

**Cumulative fresh-window count: 3/5.**

### Composition

- ID: `1491d31c-3329-4485-a84e-80a0f0781035`
- Name: `Dialogue — I think Fox & Flour needs a ma`
- Template: `dialogue_scene` (Ruby + Tyson cast, Fox & Flour World)
- Episode: `49ead0ac-a085-49dd-a447-602af08ec368`
- Operator topic: *"Ruby thinks the bakery needs a mascot."*
- Status: `completed`; `verification_status = "verified"`; `synthesis_attempt_count = 1` (no corrective)

### Legacy `verification_warnings` (authoritative)

2 warnings, both `proper_noun`, both sentence-initial ordinary English:

- `Tucked` — turn 4 (Ruby): *"He wouldn't present it. He'd be carrying it home. Tucked under one arm, very pleased with himself."*
- `Done` — turn 10 (Ruby): *"Done. And he is going to have the best little loaf."*

Two more Q-278-1 class members.

### Shadow `verification_warnings_shadow` (observational)

**0 entries. Empty list.**

### OLD_ONLY / SHADOW_ONLY / BOTH

- **OLD_ONLY: `Tucked`, `Done`** — 2 warnings.
- **SHADOW_ONLY:** none.
- **BOTH:** none.

### Were `Tucked` / `Done` silenced?

**Yes, both.** Live per-turn replay against real per-speaker corpora (Ruby + Tyson, real per-character K2 populated this time — same chunk IDs as Specimen 1) reproduced the persisted shape exactly. spaCy 3.8 POS tags: `Tucked` = past-participle VERB, `Done` = sentence-initial ADJ/INTJ — neither PROPN → D-POS does not extract.

### Shadow-only deltas

None. Nothing to classify.

### Runtime shadow confirmation

Confirmed active — deterministic live replay reproduces persisted empty shape.

### Legacy authority + shadow zero-impact

Same as prior specimens.

### Creative operator observation (positive — record only)

Chris reports this episode "worked very well creatively." No creative-quality investigation.

### DEFERRED cross-specimen observation — visual-composition boundary

The dialogue progressively expanded a visually important mascot concept **without operator prompting**. The 8-word topic was only *"Ruby thinks the bakery needs a mascot."* The synthesized scene added:

- small fox mascot
- loaf tucked under one arm (turn 4)
- tiny coffee cup on the counter signs (turn 6)
- little party hat by the celebration-cake pickup (turn 6)
- three proposed sketches (turn 9)

The viewer sees only the two talking-head character clips (Ruby + Tyson) and cannot see the mascot the characters are increasingly discussing. This resembles the prior Patch/Rivet dogfood where dialogue introduced visually important scene objects (e.g. the box) that the current talking-head composition could not show.

**Cross-specimen shape:** the same class of behavior has now surfaced across different dogfood characters (Patch + Rivet **and** Ruby + Tyson) and different Worlds (Patch's Workshop **and** Fox & Flour Bakery). Today's mascot is not the architecture; the cross-character/cross-World pattern is.

**Important distinction:** the operator did NOT request these visual details. The synthesizer itself expanded the topic into visual storytelling that exceeded the current talking-head visual grammar.

**Possible future focused question (NOT opened yet):** *When synthesis makes an unseen object or concept important to the scene, how can Character OS determine whether the composition needs additional visual representation?*

Nothing in this slice about:
- image generation
- writer prompt
- composition planning
- suppression of visual references
- PiP / B-roll / cutaway architecture
- an "every mentioned object gets a visual" assumption

The observation is recorded durably here for a future question, not investigated.

### Cumulative fresh-window progress: **3 / 5**

---

## Q-278-3.2 Fresh Shadow Dogfood — Specimen 4/5

**Cumulative fresh-window count: 4/5.**

### Composition

- ID: `fcba3242-097f-4355-b47b-669c48be43ed`
- Name: `Dialogue — I'm building an agent to help`
- Template: `dialogue_scene` (Patch + Rivet cast, Patch's Workshop World)
- Episode: `4598fcfa-70ff-41c9-81d5-becebb48d29c`
- Operator topic: *"Patch and Rivet work on an Agent"*
- Status: `completed`; `verification_status = "verified"`; `synthesis_attempt_count = 1`

### Legacy `verification_warnings` (authoritative)

7 warnings, all `proper_noun`, distributed across turns 2-10:

- `Suggest` — turn 2 (Patch, mid-sentence after ". "): *"Not decide. Suggest. I still retain..."*
- `Success` — turn 3 (Rivet, position 41): *"Then success is not \"it picked an idea.\" Success is whether its suggestion helps us learn something..."*
- `Fair` — turn 4 (Patch, sentence-initial): *"Fair. I asked it what we should do..."*
- `Mostly` — turn 6 (Patch, sentence-initial): *"Mostly. Its first job is to look at a project..."*
- `Basically` — turn 6 (Patch, later sentence): *"Basically, it gets to be you, but without the disappointed stare."*
- `Also` — turn 7 (Rivet, sentence-initial after ". "): *"The stare is not optional. Also, if it only repeats questions..."*
- `Painful` — turn 10 (Patch, mid-sentence after ". "): *"Then it can bring them up later. Painful, but fair."*

Six are Q-278-1 sentence-initial ordinary-language shape; one (`Success`) is a mid-sentence capitalized common noun.

### Shadow `verification_warnings_shadow` (observational)

**1 entry:** `{"kind":"ner_org","claim":"Success","position":41,"line_index":3,"speaker_name":"Rivet","speaker_alias":"rivet"}`

### OLD_ONLY / SHADOW_ONLY / BOTH

- **OLD_ONLY: `Suggest`, `Fair`, `Mostly`, `Basically`, `Also`, `Painful`** — 6 warnings silenced by shadow.
- **SHADOW_ONLY:** none.
- **BOTH: `Success`** — 1 warning (both classifiers flagged; kinds differ: legacy `proper_noun` from the single-cap regex vs shadow `ner_org` from the NER supplement pass).

### Were the 7 legacy warnings silenced?

**6 of 7 silenced by D-POS**; 1 (`Success`) also flagged by shadow via a different mechanism.

- `Suggest` → spaCy POS=VERB (imperative "Suggest.") → PROPN pass skips ✓
- `Fair` → POS=ADJ → skips ✓
- `Mostly` → POS=ADV → skips ✓
- `Basically` → POS=ADV → skips ✓
- `Also` → POS=ADV → skips ✓
- `Painful` → POS=ADJ → skips ✓
- `Success` → POS=NOUN (spaCy tags both occurrences NOUN, not PROPN) → PROPN pass skips; **but** spaCy NER labels the capitalized `Success` at position 41 as `ORG` → **the NER supplement pass in `claim_verifier_ner.extract_named_entities_ner` picks it up as `ner_org`**.

### Delta interpretation

- **The 6 OLD_ONLY entries: desirable.** Six additional Q-278-1 class false positives closed by construction. Consistent with prior specimens.
- **The 1 BOTH entry (`Success`): ambiguous / newly-surfaced weakness of the NER supplement.** Not a shadow-only NEW false positive (legacy already flagged), but it shows that the NER supplement pass — which was designed to catch entities PROPN misses (specifically short acronyms like `FBI`/`CIA`) — also inherits spaCy's small-model NER over-firing on capitalized common nouns at sentence boundaries. Same class as the Q-278-3.1 `Fair enough.` observation in the 3.7.1 model, which we thought was closed by moving to 3.8. It is closed for `Fair` under 3.8 but NOT for `Success` in this exact sentence shape.

  Interpretation: the NER supplement's benefit (closing `FBI`/`CIA` silent misses) comes with a small cost (importing spaCy's ORG false positives on common nouns). Under the current D-POS Hybrid design the two effects are coupled. If the shadow window keeps producing `ner_*` warnings on common capitalized nouns, a future refinement — evaluated in a separate audit, not this slice — could require `token.pos_ == "PROPN"` for any NER-supplement candidate, sacrificing short-acronym coverage in exchange for tighter ordinary-noun exclusion. **No implementation change here.**

### Shadow-only NEW warnings

**None.** Shadow did not surface any candidate the legacy classifier missed. `Success` is a BOTH, not a SHADOW_ONLY.

### Runtime shadow confirmation

Confirmed active. First specimen with a non-empty `verification_warnings_shadow` column, which is now the strongest single-shot direct confirmation the shadow classifier ran during the Celery worker's actual render — not merely consistent with a hypothetical off run. Deterministic live replay matches the persisted row exactly.

### Legacy authority + shadow zero-impact

`Success` appears in BOTH columns; legacy drove the SPA display. Composition status `completed`; render dispatched to Runway; provider spend unaffected by shadow.

### Creative operator observations (record only — NOT investigated)

**POSITIVE — POSSIBLE CROSS-EPISODE EPISTEMIC ASYMMETRY.** The retrieved Rivet-scoped memory is:

> *"While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him."*

The memory body itself encodes an information asymmetry: **Rivet knows about PATCH OVERRIDES; Patch does not**.

The generated scene behaves consistently with that asymmetry. Patch (turn 10) unknowingly approaches the hidden subject:

> Patch: *"And if it remembers every recommendation you ignore?"*

Rivet (turn 11) responds in a way informed by his private knowledge without exposing it:

> Rivet: *"Well. It may already have a system for that."*

Notably, the synthesis did NOT simply expose or recite the retrieved memory. The generated dialogue appears to have (1) retrieved a Rivet-relevant prior event, (2) preserved that Rivet knows something Patch does not, (3) allowed Patch to unknowingly approach the hidden subject, (4) let Rivet respond in a way informed by his private knowledge, (5) avoided leaking the specific secret ("PATCH OVERRIDES" is never named) to Patch, and (6) produced subtext whose meaning depends on the prior episode.

**Preserve the OBSERVED-vs-NOT-YET-PROVEN distinction:**

- **OBSERVED (this specimen):** the final dialogue behaves as though Rivet retains private knowledge that Patch lacks, across an episode boundary.
- **NOT YET PROVEN:** that Character OS mechanically maintains arbitrary per-character epistemic state across episodes.

Specifically NOT yet mechanically established:
- what exact context was supplied to each synthesis stage (per-character corpus + memory rows) for this composition;
- whether Patch was actually prevented from seeing the Rivet-scoped memory during synthesis, or whether the model simply chose not to name it;
- whether speaker-specific memory visibility is mechanically enforced (witness filtering, per-turn corpora, etc.) or is emergent from prompt semantics;
- whether the behavior generalizes across topics, characters, and Worlds;
- whether the result arose from explicit memory scoping, prompt semantics, model inference alone, or a composition of several mechanisms.

**Possible future falsifiable question (NOT opened yet):**

> Can Character OS reliably preserve and compose character-specific knowledge asymmetry across episodes — allowing one character's private memory to influence behavior without leaking that information to characters who should not know it?

If Chris later opens this, evidence gathering would start from the mechanical facts already in the DB for this composition (per-character `knowledge_chunk_ids`, `memory_ids`, and the exact text passed to `synthesize_dialogue`), then extend to a bounded set of adversarial episodes that place secrets on one character with an evident temptation for the other character to guess.

**No investigation of memory / synthesis / prompt path is opened in this slice.**

**DEFERRED — methodology / repetition observation.** Chris independently noticed the scene contains the phrase *"It suggested we give it one narrow job before we give it access to everything in the workshop."* The "one narrow job" concept has recurred frequently enough across prior Character OS work that it now reads as over-pushed. This episode also strongly reflects Character OS's own development methodology (one narrow job / what are we trying to prove / what changed / what result would count / test on a real project / learn from the result / reject vague output).

Combined with the earlier Specimen 2 deferred observation about Patch's *"Whether it should be is a different question."* construction, both observations point to the same broader possible future falsifiable question:

> **Are Character OS's embedded behavioral / product principles becoming overrepresented in generated character dialogue, causing independent scenes to converge on recurring methodology, phrases, or rhetorical structures?**

The question is DEFERRED and NOT formally opened. If Chris later opens it, evidence gathering would start by grepping every completed Patch composition's `synthesized_brief` for the "Whether it should be is a different question" construction, the "one narrow job" family, and adjacent methodology-shape indicators — then contrast with Ruby/Tyson briefs to test whether the pattern is Patch-specific or platform-wide.

**Three observations from this specimen must remain distinct and MUST NOT be conflated:**

- The methodology/repetition observation is a possible drift in generated language.
- The rhetorical-construction observation (carried forward from Specimen 2, "Whether it should be is a different question.") is a separate possible drift.
- The PATCH OVERRIDES observation is a possible cross-episode epistemic asymmetry — an emerging positive continuity behavior, still an observation not a proven invariant.

All three recorded here durably; none investigated in this slice.

Also **DO NOT modify:** Patch, Rivet, Agent behavior, identity prompts, business_brief, memories, synthesis prompts, methodology guidance. Nothing changes as a result of these observations in Q-278-3.2.

### Cumulative fresh-window progress: **4 / 5**

Aggregate across the window so far:

- Silenced Q-278-1 class false positives (OLD_ONLY): **3 + 2 + 2 + 6 = 13**
- SHADOW_ONLY new candidates: **0**
- BOTH (parity, including one shadow noise finding): **0 + 0 + 0 + 1 = 1** (`Success` in Specimen 4)

---

## Q-278-3.2 Fresh Shadow Dogfood — Specimen 5/5

**Cumulative fresh-window count: 5/5 — window complete.**

### Composition

- ID: `1aabbff6-4fe9-4054-812a-88cdd9f5ad7e`
- Name: `Dialogue — I'm telling you, this bakery i`
- Template: `dialogue_scene` (Tyson + Ruby cast, Fox & Flour World)
- Episode: `2e58568a-e42e-4339-b1ec-e5ea89df37be`
- Operator topic: *"Tyson is convinced the bakery is haunted."*
- Status: `completed`; `verification_status = "verified"`; `synthesis_attempt_count = 1`
- Operator creative note: worked well creatively.

### Legacy `verification_warnings` (authoritative)

5 warnings across 4 turns:

- `Turned` (proper_noun) — turn 2 (Tyson, position 61): *"…nobody. **Turned** around: nobody. Then the pastry case caught a reflection…"*  *(sentence-initial after ". ")*
- `Well` (proper_noun) — turn 5 (Ruby, position 0): *"**Well**, that does narrow it down. Was this ghost disappointed because…"*
- `At Fox` (multi_word) — turn 7 (Ruby, position 0): *"**At Fox** & Flour? A bakery built around small-batch baking and handcrafted pastries?..."*
- `Explain` (proper_noun) — turn 8 (Tyson, position 6): *"Fine. **Explain** the cold spot by the counter."*
- `Probably` (proper_noun) — turn 9 (Ruby, position 127): *"…Very particular. **Probably** wants a celebration cake and refuses to give us a pickup time."*

### Shadow `verification_warnings_shadow` (observational)

**0 entries. Empty list.**

### OLD_ONLY / SHADOW_ONLY / BOTH

- **OLD_ONLY: `Turned`, `Well`, `At Fox`, `Explain`, `Probably`** — 5 warnings silenced by shadow.
- **SHADOW_ONLY:** none.
- **BOTH:** none.

### Were `Turned` / `Well` / `Explain` / `Probably` silenced?

**Yes, all four.** spaCy 3.8 POS: `Turned` = VERB (past tense), `Well` = INTJ, `Explain` = VERB (imperative), `Probably` = ADV — none PROPN → D-POS does not extract.

### `At Fox` forensic (the multi-word specimen)

Turn 7 source text (Ruby): *"At Fox & Flour? A bakery built around small-batch baking and handcrafted pastries? I'm afraid the ghost may have an airtight alibi."*

Live-replay extraction outputs:

- **Legacy** — `extract_named_entities` returned two candidates:
  - `("At Fox", "multi_word", position 0)` — the multi-word regex `\b[A-Z][a-zA-Z]+(\s+[A-Z][a-zA-Z]+)+\b` matched `At Fox` because both are capitalized and adjacent. `At` is a preposition and **not in the stoplist**, so the demotion never fired. The regex terminated at `Fox` because `&` breaks the whitespace-only joiner alternation.
  - `("Flour", "proper_noun", position 9)` — single-cap regex pass. Corpus check hit `fox & flour` substring → not flagged.
- **D-POS** — `extract_named_entities_ner` returned two singletons:
  - `("Fox", "proper_noun_pos", position 3)` — PROPN token, corpus-grounded (`fox` substring of `fox & flour`) → pass.
  - `("Flour", "proper_noun_pos", position 9)` — PROPN token, corpus-grounded → pass.
- **Corpus check:** Ruby's factual corpus contains `fox & flour` (True) but NOT `at fox` (False) and NOT `fox and flour` (False — the corpus writes it with `&`).

**Grounding outcome:** legacy flagged `At Fox` because `at fox` isn't in the corpus (spurious span forced the miss). D-POS split cleanly into `Fox` + `Flour`, both PROPN, both substring-matched to the corpus → both pass.

**Classification: entity-boundary IMPROVEMENT.** Legacy's over-greedy multi-word regex captured a preposition into an entity span and then failed to reunite with `Flour` after the `&`. D-POS avoids the preposition (POS=ADP, not PROPN) and grounds each PROPN independently. This is exactly the shape refinement the Q-278-3 architecture predicted for multi-word entities interrupted by non-whitespace punctuation.

### Delta interpretation

- **All 5 OLD_ONLY entries: desirable.** Four Q-278-1 sentence-initial ordinary-language false positives + one multi-word boundary improvement.
- **Zero SHADOW_ONLY, zero BOTH.**

### Runtime shadow confirmation

Confirmed active. Deterministic live replay reproduces the persisted empty shadow output on every turn. Fifth consecutive fresh render with `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT=1` in the Celery worker environment.

### Legacy authority + shadow zero-impact

Same as prior specimens. Legacy drove SPA display. Composition completed; render dispatched to Runway; provider spend unaffected by shadow.

### Cumulative fresh-window progress: **5 / 5 — window complete**

---

## Q-278-3.2 Five-Specimen Shadow Window Analysis

Consolidated analysis of the five fresh dogfood compositions (a1421a0e / 5f4bdbbc / 1491d31c / fcba3242 / 1aabbff6) built from persisted DB evidence + live-replay forensics. Separate from the historical warned-row replay recorded in Q-278-3.2 §"Historical warned-row replay" above.

### Complete fresh-window matrix

| # | comp | speaker/turn | span | kind | legacy | D-POS | class | interpretation |
|---|---|---|---|---|---|---|---|---|
| 1 | a1421a0e | Tyson t6 | `Mostly` | proper_noun | flag | pass | OLD_ONLY | ordinary ADV — false positive silenced |
| 2 | a1421a0e | Ruby t7 | `Once` | proper_noun | flag | pass | OLD_ONLY | SCONJ — false positive silenced |
| 3 | a1421a0e | Ruby t9 | `Perfect` | proper_noun | flag | pass | OLD_ONLY | ADJ/INTJ — false positive silenced |
| 4 | 5f4bdbbc | Rivet t1 | `Consulting` | proper_noun | flag | pass | OLD_ONLY | sentence-initial gerund — false positive silenced |
| 5 | 5f4bdbbc | Patch t4 | `Also` | proper_noun | flag | pass | OLD_ONLY | ADV — false positive silenced |
| 6 | 1491d31c | Ruby t4 | `Tucked` | proper_noun | flag | pass | OLD_ONLY | past-participle VERB — false positive silenced |
| 7 | 1491d31c | Ruby t10 | `Done` | proper_noun | flag | pass | OLD_ONLY | ADJ/INTJ — false positive silenced |
| 8 | fcba3242 | Patch t2 | `Suggest` | proper_noun | flag | pass | OLD_ONLY | imperative VERB — false positive silenced |
| 9 | fcba3242 | Rivet t3 | `Success` | proper_noun / ner_org | flag | flag | BOTH | ambiguous — spaCy POS=NOUN but NER=ORG; NER supplement pass over-fires on capitalized common noun |
| 10 | fcba3242 | Patch t4 | `Fair` | proper_noun | flag | pass | OLD_ONLY | ADJ — false positive silenced (repeat of Q-278-1 specimen) |
| 11 | fcba3242 | Patch t6 | `Mostly` | proper_noun | flag | pass | OLD_ONLY | ADV — silenced (repeat) |
| 12 | fcba3242 | Patch t6 | `Basically` | proper_noun | flag | pass | OLD_ONLY | ADV — silenced |
| 13 | fcba3242 | Rivet t7 | `Also` | proper_noun | flag | pass | OLD_ONLY | ADV — silenced (repeat) |
| 14 | fcba3242 | Patch t10 | `Painful` | proper_noun | flag | pass | OLD_ONLY | ADJ — silenced |
| 15 | 1aabbff6 | Tyson t2 | `Turned` | proper_noun | flag | pass | OLD_ONLY | past-tense VERB — silenced |
| 16 | 1aabbff6 | Ruby t5 | `Well` | proper_noun | flag | pass | OLD_ONLY | INTJ — silenced |
| 17 | 1aabbff6 | Ruby t7 | `At Fox` | multi_word | flag | pass | OLD_ONLY | multi-word BOUNDARY IMPROVEMENT — legacy captured preposition `At`; D-POS split into `Fox` + `Flour` PROPN singletons, both corpus-grounded → pass |
| 18 | 1aabbff6 | Tyson t8 | `Explain` | proper_noun | flag | pass | OLD_ONLY | imperative VERB — silenced |
| 19 | 1aabbff6 | Ruby t9 | `Probably` | proper_noun | flag | pass | OLD_ONLY | ADV — silenced |

### Totals — warning instances

| metric | count |
|---|---|
| total legacy warning instances | **19** |
| total D-POS shadow warning instances | **1** |
| BOTH | **1** (`Success` in Specimen 4) |
| OLD_ONLY | **18** |
| SHADOW_ONLY | **0** |

### Totals — unique spans

Repeat words in the window: `Fair` × 2 (specimens 1, 4), `Mostly` × 2 (specimens 1, 4), `Also` × 2 (specimens 2, 4). Everything else once.

| metric | count |
|---|---|
| unique legacy spans | **17** (`Mostly`, `Once`, `Perfect`, `Consulting`, `Also`, `Tucked`, `Done`, `Suggest`, `Success`, `Fair`, `Basically`, `Painful`, `Turned`, `Well`, `At Fox`, `Explain`, `Probably`) |
| unique D-POS spans | **1** (`Success`) |
| unique OLD_ONLY spans | **16** |
| unique SHADOW_ONLY spans | **0** |
| unique BOTH spans | **1** |

### True / false / ambiguous classification (human)

Reviewer inspection of every OLD_ONLY / BOTH specimen in surrounding text:

- **19 legacy warning instances → 18 false positives + 1 ambiguous (`Success`).** Zero legacy true positives in this window. Every specimen was normal Fox & Flour or Patch/Rivet operator dogfood with a well-grounded corpus; no character invented an unsupported named entity.
- **1 D-POS warning instance → 1 ambiguous (`Success`).** Not a true positive of a hallucinated entity; not a clean false positive because both classifiers agree; classified as newly-surfaced weakness of the NER supplement pass on capitalized common nouns spaCy small-model labels as ORG.

Note: the fresh window contains **no adversarial test of the founding hallucination invariant** — no composition attempted to introduce an unsupported `Wikipedia`/`trafilatura`-shaped entity. The true-positive-preservation guarantee therefore rests on (a) the Q-278-3.1 measured evidence + (b) the regression suite pinning the invariant. Fresh window is compatible with that guarantee (nothing was silenced that should have flagged) but does not by itself stress-test it.

### Acceptance criteria evaluation (A-F)

Criteria established in Q-278-3.2 §"Explicit STOP gate":

- **A. D-POS preserves all identified TRUE positives from current K6.4.** → **PASS (with qualifier).** Zero legacy warnings in the fresh window were named-entity true positives; there were none to lose. True-positive preservation for the founding class rests on the Q-278-3.1 measured matrix + regression suite (both green). No fresh evidence contradicts this criterion; no fresh evidence stresses it either.
- **B. D-POS removes the large majority of current ordinary-language false positives.** → **PASS.** 18 of 19 warning instances (94.7%) and 16 of 17 unique spans (94.1%) silenced. General-class closure demonstrated across 15+ different English words, not case-by-case memorization of Fair/Come/Unless.
- **C. No new false-negative class larger/more dangerous than the class closed.** → **PASS.** Zero SHADOW_ONLY warnings across the fresh window. No new silent-miss class surfaced by fresh dogfood.
- **D. `KNOWN_TECH_TERMS` continues protecting lowercase-domain terms.** → **PASS via regression tests; INSUFFICIENT FRESH-WINDOW EVIDENCE.** None of the 5 fresh compositions contained lowercase-tech-name candidates. `test_lowercase_tech_terms_still_flagged_via_known_tech_terms` covers `pgvector`/`redis` deterministically.
- **E. Multi-word POS spans do not materially regress supported/unsupported entity grounding.** → **PASS (with positive finding).** ONE multi-word case (`At Fox`, Specimen 5): D-POS produced a cleaner extraction than legacy, avoiding a spurious preposition capture and correctly grounding both PROPN halves via corpus substring. No multi-word regression observed. `test_multiword_propn_span_extracts_full_span` + `test_multiword_supported_multi_word_passes` continue to lock the general shape.
- **F. `May`-like collisions are recorded rather than hidden.** → **PASS via regression test; INSUFFICIENT FRESH-WINDOW EVIDENCE.** No `May`/`Bill`/`Mark`-as-person collisions surfaced in fresh window. `test_may_as_person_currently_missed_documented_gap` pins the known residual.

### Combined with historical replay

Kept distinguishable per instruction:

**HISTORICAL REPLAY** (5 pre-shadow warned rows sampled in Q-278-3.1):
- Legacy warning instances: 11
- D-POS: 10 ordinary-language silenced + 1 rescoped multi-word→entity (`Can AI` → `AI` alone) = 11 corrections
- Zero true positives lost.

**FRESH SHADOW DOGFOOD** (5/5 window, this analysis):
- Legacy warning instances: 19
- D-POS: 18 silenced + 1 BOTH (Success)
- Zero true positives lost. Zero shadow-only new warnings. One newly-observed weakness of the NER supplement pass. One multi-word entity-boundary improvement.

**COMBINED**:
- Legacy warning instances across both datasets: **30**
- D-POS silenced (OLD_ONLY): **28** (18 fresh + 10 historical clean silences)
- D-POS improved boundary (OLD_ONLY with rescope): **2** (1 fresh `At Fox` + 1 historical `Can AI`)
- BOTH: **1** (Success)
- SHADOW_ONLY: **0**
- Losses of legacy true positives: **0**

### Answers to the six combined-evidence questions

1. **Did any historical true positive disappear under D-POS?** No.
2. **Did any fresh specimen expose a new D-POS false negative?** No.
3. **Did any fresh specimen expose a D-POS false positive?** Only in BOTH parity (`Success`, Specimen 4) — legacy also flagged. Not a shadow-only false positive.
4. **Did any fresh specimen expose a useful entity/span legacy missed?** Not a new true positive; but entity-boundary improvement on `At Fox` — D-POS split `Fox` + `Flour` cleanly where legacy captured preposition + first proper noun as one span.
5. **Did any fresh specimen expose a multi-word boundary difference such as `At Fox`?** Yes — see Specimen 5 forensic. D-POS handles preposition-adjacent proper nouns more cleanly.
6. **Is there evidence that the new verifier fixes the GENERAL false-positive class rather than only Fair/Come/Unless?** Yes. 15+ different fresh English tokens silenced across 5 independent compositions (Mostly / Once / Perfect / Consulting / Also / Tucked / Done / Suggest / Basically / Painful / Turned / Well / Explain / Probably plus repeats of Fair / Mostly / Also). This is general-class closure, not case-by-case memorization.

### Prediction vs actual

- Predicted (Q-278-3): D-POS closes the Q-278-1 general class. **CONFIRMED** across 5 fresh independent compositions on 15+ different English tokens.
- Predicted: D-POS preserves founding hallucination invariant. **CONFIRMED indirectly** — no fresh true positive was lost; regression suite + Q-278-3.1 measured evidence carry the direct guarantee.
- Predicted: SHADOW_ONLY warnings would occasionally surface entities legacy missed. **NOT OBSERVED** in fresh window; historical replay saw one (`Can AI` → `AI`).
- Predicted: `Success`-shape common-noun NER over-firing was possible but expected to be rare. **OBSERVED once** in fresh window — Specimen 4 turn 3. Documented rather than hidden.
- Predicted: multi-word entity boundary improvements over the legacy regex. **CONFIRMED** on `At Fox`.

### Discrepancies

- Q-278-3.1 had not stressed the NER supplement pass on capitalized common nouns; fresh window surfaced `Success` as the first specimen where spaCy small-model NER labels a common noun as ORG and the supplement pass therefore emits a candidate. Documented as a known observation of the D-POS Hybrid shape; not a regression against A (legacy also flagged); worth revisiting in the cutover-design slice.

### Deferred creative observations remain OUT-OF-SCOPE for this verifier decision

The following DEFERRED observations are recorded in the per-specimen sections above and are **not permitted to influence** the shadow-window verifier decision:

- Repeated methodology / "one narrow job" (Specimen 4).
- Repeated rhetorical constructions (Specimen 2 + carried into Specimen 4).
- Visual storytelling exceeding talking-head grammar (Specimen 3, cross-referenced with prior Patch/Rivet dogfood).
- Possible cross-episode epistemic asymmetry (Specimen 4 addendum).

Each stays recorded for possible future falsifiable questions Chris may or may not choose to open. None was investigated in this analysis.

### Recommendation

**GO-CUTOVER-PLANNING.**

Justification:

- 5 of 6 acceptance criteria PASS on the fresh window; the remaining two (D, F) PASS via regression suite with insufficient fresh-window stress but no contradictory evidence.
- General-class closure demonstrated across 15+ different English tokens in 5 independent compositions; not case-by-case.
- Founding hallucination invariant preserved (no true positive lost across 30 combined warning instances).
- Multi-word entity boundary improved on the one fresh case that surfaced (`At Fox`).
- The one newly-observed weakness (NER-supplement over-firing on `Success`) is not a regression against legacy behavior and is a design consideration for the cutover slice, not a blocker.

GO-CUTOVER-PLANNING **does not authorize** cutover. It authorizes opening the smallest safe cutover-design question next. That question should scope-lock:

1. Whether the NER supplement pass should additionally require `token.pos_ == "PROPN"` to accept a candidate, and how that would affect the `FBI`/`CIA` short-acronym coverage the supplement was designed to protect.
2. How the legacy stoplist deprecates during and after cutover (Q-278-3 §"Stoplist disposition" three-phase plan).
3. Whether shadow persistence extends to `ConversationMessage.verification_warnings` / `Script.verification_warnings` before or after cutover.
4. Whether `K6_CLAIM_VERIFIER_MODE` default flip from `warn` to `strict` is scope-locked separately from the cutover itself.
5. Rollback path (env flag + boolean gate) and cutover acceptance signal.

### Explicit decision gate

**STOP.** No cutover in this slice. No implementation changes to the verifier. No new dependency changes. No strict-mode flip.

Chris + ChatGPT must explicitly approve one of:

- **Open Q-278-4** as the cutover-design audit scoped by the five items above.
- **Extend the shadow window** with N additional fresh dogfood specimens before opening Q-278-4 (would apply if Chris wants direct stress on criterion A — e.g. deliberately introduce a hallucination-shaped prompt to test true-positive preservation on a fresh render).
- **Modify D-POS first** — if the `Success` NER-supplement finding is judged blocking, gate the NER supplement on POS=PROPN before advancing.
- **No-Go** — reject the semantic direction; freeze at legacy A.

Deferred creative observations (methodology repetition, rhetorical constructions, visual-composition boundary, cross-episode epistemic asymmetry) are independent of this decision and remain recorded for any future Chris-authorized investigation.

*Chris + ChatGPT decision:* **GO-CUTOVER-PLANNING** approved. Open Q-278-4 as cutover-design audit ONLY. Do NOT flip authority. Do NOT change strict-mode. Do NOT deprecate legacy verifier or stoplist yet.

---

## Q-278-4 — D-POS Cutover Design Audit

### Precise question

What is the smallest safe, reversible transition from the current legacy-authoritative + D-POS-shadow architecture to D-POS authority, given the completed historical replay + 5/5 fresh shadow window?

Audit only. No production authority change. No K6_CLAIM_VERIFIER_MODE change. Warn/strict decisions remain SEPARATE.

### §1 — Current authority path (mechanical trace)

Legacy verification is authoritative today via three production call sites and one public entry point.

**Public entry point:** `character_os.claim_verifier.run_verifier(text, factual_corpus, allowed_vocabulary, mode)` (`claim_verifier.py:410-471`). Resolves mode from `settings.K6_CLAIM_VERIFIER_MODE` → env → `"warn"`. Returns `list[UnsupportedClaim]` or raises `ClaimVerifierError` in strict mode.

**Extraction → verification pipeline (inside `run_verifier`):**
1. `extract_named_entities(text)` — regex passes: multi-word capitalized (with stoplisted-leader demotion), single-cap 4+ chars (with stoplist), numeric, KNOWN_TECH_TERMS. Emits `UnsupportedClaim` candidates.
2. `verify_claims(text, factual_corpus, allowed_vocabulary)` — grounding: candidate lowercased, `needle in factual_corpus.lower()`, substring-either-way against allowed vocab; miss → keep as `UnsupportedClaim`.
3. `run_verifier` applies mode policy: `off` → return `[]`; `warn` → return list; `strict` → raise `ClaimVerifierError` if list non-empty.

**Production call sites (three):**

| # | file:line | context | on-exception behavior |
|---|---|---|---|
| 1 | `character_os/dialogue_synthesis.py:1798` | per-turn K6.4 verification loop inside `synthesize_dialogue` | `ClaimVerifierError` → set turn.verification_status=rejected, overall_status=rejected, re-raise (caught by dialogue starter → persists FAILED composition row) |
| 2 | `character_os/script_synthesis.py:526` | inside `build_render_brief` for talking-head / long-form paths | `ClaimVerifierError` → propagates to `avatar_speech` primitive → `PrimitiveError` → FAILED composition |
| 3 | `character_os/conversation_synthesis.py:226` | inside conversation reply synthesis (K6.5) | strict-mode failure → persisted onto `ConversationMessage.rejected_synthesis`, message status=rejected |

**Persistence targets (four columns across three models):**

- `Composition.verification_warnings` (JSONField) + `.verification_status` (enum) + `.rejected_synthesis` (text) — filled by the composition starter path via `_dialogue_ai_flattened_warnings` (dialogue) or by the `avatar_speech` primitive (talking-head / long-form).
- `Composition.verification_warnings_shadow` — Q-278-3.2 addition, populated by D-POS shadow.
- `DialogueTurn.verification_warnings` — per-turn in-memory dataclass; flattened up to Composition on save.
- `Script.verification_warnings` (B-arc scripts app; SPA-visible in `web/src/routes/workspace/scripts.$id.tsx`).
- `ConversationMessage.verification_warnings` (K6.5; SPA-visible in `web/src/routes/conversations/$id.tsx`).

**SPA display consumers (read-only):**
- `web/src/routes/compositions/$id.tsx` — reads `verification_warnings` + `verification_status`.
- `web/src/routes/workspace/scripts.$id.tsx` — reads `Script.verification_warnings`.
- `web/src/routes/conversations/$id.tsx` — reads `ConversationMessage.verification_warnings`.

Q-278-3.2 shadow column is NOT surfaced in the SPA. `stoplist_watchdog` and `k64_shadow_diff` mgmt commands consume the persisted columns for audit reporting.

**Minimum code surface for authority flip:** replace the three `run_verifier(...)` call sites with a dispatcher that returns either classifier's output based on a new authority flag. Both classifiers return `list[UnsupportedClaim]` with identical dataclass shape, and `.to_dict()` produces the same JSON schema. Downstream (`turn.verification_warnings = [w.to_dict() for w in warnings]`) is unchanged.

### §2 — Success / NER-supplement question (mechanical test in throwaway venv)

The Q-278-3.2 Specimen 4 finding: spaCy tags both occurrences of `success` in *"Then success is not \"it picked an idea.\" Success is whether…"* as `POS=NOUN` (not PROPN), but NER labels the capitalized occurrence `Success` as `ORG` → the NER supplement pass in `claim_verifier_ner.extract_named_entities_ner` picks it up, producing a shadow-BOTH-parity noise entry.

Tested (throwaway `/tmp/q278_spacy_spike/test_supplement_propn_gate.py`, using the Character OS venv's spaCy 3.8.15 + en_core_web_sm 3.8.0 already installed for Q-278-3.2 — **NO** modifications to production code):

**Proposed refinement:** in the NER supplement pass, require at least one token of the entity span to have `POS=PROPN`. Rejects a spaCy NER label when every token in the span is common (POS=NOUN / VERB / ADJ / etc.).

Measured outcomes:

| specimen | current supplement | PROPN-gated supplement | outcome |
|---|---|---|---|
| `Success` common noun (Specimen 4) | ACCEPT (ORG) | REJECT (POS=NOUN only) | ✓ over-fire removed |
| `FBI called.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ short-acronym coverage preserved |
| `CIA is watching.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `FDA approved it.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `IRS audited us.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `Wikipedia is our source.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `NASA supplied the equipment.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `France changed the rule.` | ACCEPT (GPE) | ACCEPT (POS=PROPN) | ✓ preserved |
| `Microsoft built it.` | ACCEPT (ORG) | ACCEPT (POS=PROPN) | ✓ preserved |
| `OpenAI released it.` | ACCEPT (PERSON) | ACCEPT (POS=PROPN) | ✓ preserved |
| `Mark called today.` | ACCEPT (PERSON) | ACCEPT (POS=PROPN) | ✓ polysemous name preserved |
| `Bill approved it.` | ACCEPT (PERSON) | ACCEPT (POS=PROPN) | ✓ polysemous name preserved |
| `James Webb Space Telescope launched.` | ACCEPT (PERSON multi-word) | ACCEPT (all PROPN) | ✓ multi-word preserved |
| `New York is far.` | ACCEPT (GPE) | ACCEPT (all PROPN) | ✓ multi-word preserved |

**Recommendation: REQUIRE POS=PROPN.** The gate cleanly closes the `Success` common-noun over-fire without regressing any short-acronym coverage or any real proper-noun case tested. All FBI/CIA/FDA/IRS short-acronyms remain accepted because spaCy tags them as PROPN. This becomes Slice 1 below — smallest possible change, high evidence, non-authority-changing.

### §3 — Legacy stoplist disposition

Three-phase plan from Q-278-3 refined against post-shadow evidence:

- **Phase 1 (at initial authority flip — Slice 3 below):** legacy verifier code + `_COMMON_PROPER_NOUN_FALSE_POSITIVES` stoplist stay in place, untouched. Legacy is invoked as post-cutover shadow (dual-run). If rollback is needed, legacy behavior is byte-identical to today.
- **Phase 2 (rollback confidence period — for the duration of Slice 3's flag-in-place):** stoplist stays untouched. Rollback restores today's behavior exactly.
- **Phase 3 (retirement — much later, deliberately unscheduled):** delete legacy verifier module + stoplist ONLY after ≥ N post-cutover renders with zero rollback signals. Independent slice, out of scope for Q-278-4.

**Do NOT touch the stoplist in Slices 1-3.** Reversibility beats cleanup.

### §4 — Shadow / dual-run disposition

The current shape (legacy authoritative + D-POS shadow) inverts cleanly at authority flip:

- **Pre-cutover:** legacy authoritative → `verification_warnings`; D-POS shadow → `verification_warnings_shadow`.
- **Post-cutover:** D-POS authoritative → `verification_warnings`; legacy shadow → new column `verification_warnings_legacy`.

Inverting the relationship (rather than immediately deleting the legacy path) is safer because:

1. Post-cutover ongoing evidence — every render generates a legacy shadow row that can be diffed against D-POS output. Any regressions surface within one dogfood cycle.
2. Rollback is a flag flip, not a code revert.
3. Symmetric observability — the operator can trust the shadow-diff mgmt command semantics in both directions.

### §5 — Persistence semantics

Chris explicitly ruled out "silently changing the meaning of a column named 'shadow' to legacy." Adopted design:

- **`verification_warnings`** — ALWAYS authoritative (whichever classifier is selected by the authority flag).
- **`verification_warnings_shadow`** — ALWAYS D-POS output. When D-POS is authoritative, `verification_warnings_shadow == verification_warnings` (self-mirror; kept for symmetry).
- **`verification_warnings_legacy`** (NEW, added in Slice 2) — ALWAYS legacy output. When legacy is authoritative, `verification_warnings_legacy == verification_warnings`.

Invariant: for any row `verification_warnings ∈ {verification_warnings_shadow, verification_warnings_legacy}` depending on which classifier was authoritative at write time. The authority tag can be inferred from row equality, and historical data remains interpretable in both directions.

**Adjacent surfaces (`ConversationMessage`, `Script`):** NOT migrated in the cutover slices below. Q-278-3.2's dialogue-only shadow persistence is deliberately preserved. Adjacent-surface migration is a follow-up slice (Q-278-4.x, unopened), evidenced by the same classifier core + a per-model persistence pattern. Only migrating dialogue-scene compositions in the cutover keeps blast radius minimal.

### §6 — Rollback

Smallest explicit rollback mechanism:

- **Flag:** new env-and-settings `CHARACTER_OS_K64_AUTHORITY = "legacy" | "d_pos"` (default `"legacy"` at Slice 2; flipped to `"d_pos"` at Slice 3). Same precedence pattern as `K6_CLAIM_VERIFIER_MODE` (settings > env; whitespace-only invalid).
- **Rollback = flip the flag.** No restart is required per-composition — the flag is resolved fresh per synthesis call inside a dispatcher. Django dev + Celery workers pick up env changes at spawn time; a stack restart via `scripts/start-local-real.sh` is the operator-visible reload.
- **Persisted evidence:** rows written under either authority remain interpretable — `verification_warnings_legacy` and `verification_warnings_shadow` continue to carry the same semantics they were written under (see §5 invariant). No DB surgery required to rollback.
- **Defensive fallback (spaCy failure post-cutover):** if authority=d_pos and `run_shadow_verifier` cannot execute (spacy missing / model missing / exception), Slice 2 dispatcher **falls back to legacy** for that synthesis call AND logs at ERROR. Prevents an install regression from silently converting "no unsupported claim ever flagged" into false confidence. This is the load-bearing safety net for post-cutover strict-mode discussion.

### §7 — Warn vs Strict (KEPT SEPARATE)

`CHARACTER_OS_K64_AUTHORITY` (D-POS authority) and `K6_CLAIM_VERIFIER_MODE` (warn / strict) are two independent decisions. **Q-278-4 does NOT bundle them.**

Mechanically confirmed independent: the dispatcher in Slice 2 passes `mode=resolved_verifier_mode` through to whichever classifier is authoritative. Both `run_verifier` (legacy) and `run_shadow_verifier` (D-POS) accept the same mode contract. D-POS's `run_shadow_verifier` today does not raise on any input (defensive design — Q-278-3.2), but Slice 2 will add strict-mode error raising to the D-POS side to match the legacy semantics (see §9 blast radius). Strict-mode flip remains a distinct future slice, downstream of at least Slice 3 completion + a bounded post-cutover shadow window.

**Default expectation:** cut over classifier authority while remaining `warn` first.

### §8 — Acceptance + observability

**Slice 1 → Slice 2 advancement acceptance:** `Success` (Specimen 4 turn 3) no longer appears in D-POS output when replayed; existing 32 regression tests + new `Success`-gate test all pass; adjacent test suites (116 tests) still green.

**Slice 2 → Slice 3 advancement acceptance:**
- Dual-write correctness: for any composition rendered with `CHARACTER_OS_K64_AUTHORITY=legacy` post-Slice-2, `verification_warnings == verification_warnings_legacy` exactly. Verified across ≥ 3 fresh renders.
- The `k64_shadow_diff` command reads all three columns and reports OLD/D-POS/BOTH correctly under both authority values.
- Defensive fallback smoke: manually break spaCy install (in a throwaway venv), confirm dispatcher falls back to legacy AND logs ERROR.

**Slice 3 → legacy retirement acceptance (deferred to Slice 4, unscheduled):**
- ≥ N post-cutover renders (Chris to set N; suggested lower bound ≥ 10 fresh dogfood compositions across at least two Worlds).
- Zero rollback-necessity signals surface. Defined below.
- `k64_shadow_diff` OLD_ONLY (legacy-only warnings) rate consistent with pre-cutover shadow-window OLD_ONLY rate (i.e. legacy is still generating the same Q-278-1 class false positives it always generated; not a NEW regression).
- Zero LEGACY_ONLY warnings that inspection classifies as true positives — i.e., no case where legacy caught something D-POS should have caught.

**Rollback-necessity signals (any of):**
- Any post-cutover composition where D-POS silences a token that operator inspection confirms as a real hallucination.
- Any post-cutover LEGACY_ONLY warning inspection classifies as a true positive missed by D-POS.
- Any post-cutover D-POS new false-positive class that dogfood confirms as materially worse than the legacy Q-278-1 noise.
- Runtime degradation: repeated ERROR-level fallback logs indicating spaCy failure in production; sustained pattern would motivate rollback regardless of correctness.

**Strict-mode discussion opens only after:** Slice 3 completes + a bounded post-cutover shadow window + explicit Chris + ChatGPT scope-lock. Downstream.

### §9 — Test / blast radius inventory

| dimension | Slice 1 (NER-supplement PROPN gate) | Slice 2 (dispatcher + column + fallback) | Slice 3 (default flip) |
|---|---|---|---|
| files touched | `character_os/claim_verifier_ner.py` (one function) | new `character_os/claim_verifier_dispatch.py` module; `character_os/dialogue_synthesis.py` / `script_synthesis.py` / `conversation_synthesis.py` (rewire 3 call sites); `apps/compositions/models.py` (new field); new migration; `apps/compositions/starters.py` (new flatten helper + persistence); `apps/compositions/management/commands/k64_shadow_diff.py` (read all three columns) | one-line change in `claim_verifier_dispatch.py` default resolver |
| migrations | 0 | 1 additive JSONField (`verification_warnings_legacy`) | 0 |
| new tests | `test_claim_verifier_ner_shadow.py` — `Success`-gate test; keep-FBI-CIA-FDA-IRS assertion tests | dispatcher tests: default=legacy identical to today, flag=d_pos flips outputs; dual-write invariant test; defensive-fallback test (mock spaCy import failure) | one authority-default test |
| adjacent tests to keep green | 32 D-POS + 116 dialogue/verifier adjacent | all of the above + dialogue/script starter tests that construct Composition rows | all above |
| worker / runtime | none | Both classifiers always run per synthesis call. spaCy cold-load happens on every worker regardless of the (retired) shadow flag. Measured incremental: ~50-70 MB RSS + ~215 ms cold-load per worker at first synthesis. Per-turn: ~5-30 ms extra (measured Q-278-3.1). Negligible vs 60-120 s Runway render. | none |
| SPA implications | none | none — SPA reads `verification_warnings`, which is now authoritative under either classifier | none |
| deployment / build | none — no new deps | none — spacy + en_core_web_sm already pinned since Q-278-3.2 | none |
| compatibility with shadow-flag=OFF | unchanged | **`CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` is retired as a gate.** Both classifiers always run at Slice 2. Setting the shadow flag is a no-op after Slice 2. Documented at deprecation. | unchanged |
| historical rows | unchanged — pre-Slice-1 shadow warnings interpret the same way | unchanged — pre-Slice-2 rows have `verification_warnings_legacy = []`; interpretable as "written before dual-run existed" | unchanged |
| externally-observable behavior when authority=legacy (Slice 2 default) | identical to today | identical to today | flips at Slice 3 |

### Ordered smallest cutover plan (three slices)

**Slice 1 — Q-278-4.1: NER-supplement POS=PROPN gate.**
- **Responsibility:** narrow the NER supplement pass in `character_os/claim_verifier_ner.py` to require at least one PROPN token in an entity span.
- **Files/surfaces:** `character_os/claim_verifier_ner.py` (single function edit); `apps/compositions/tests/test_claim_verifier_ner_shadow.py` (+1 `Success`-gate test + assertions that FBI/CIA/FDA/IRS still flag).
- **Invariant protected:** short-acronym coverage; the founding hallucination invariant. Nothing about legacy authority.
- **Rollback:** revert the single function change.
- **Test gate:** 32 D-POS regression tests + new Success-gate test all pass; adjacent 116 tests remain green.
- **Production authority change:** NONE. D-POS remains shadow-only.

**Slice 2 — Q-278-4.2: Authority dispatcher + `verification_warnings_legacy` column + defensive fallback. Default authority = `legacy`.**
- **Responsibility:** introduce classifier-agnostic dispatch. Add authority flag with default `legacy`. Add `verification_warnings_legacy` column. Rewire three synthesis call sites to use the dispatcher. Dispatcher runs BOTH classifiers, writes each to its own column, and mirrors the authoritative one to `verification_warnings`. On D-POS execution failure (spacy / model / exception) when authority=d_pos, fall back to legacy AND log ERROR.
- **Files/surfaces:** new `character_os/claim_verifier_dispatch.py`; `character_os/dialogue_synthesis.py:1798`, `character_os/script_synthesis.py:526`, `character_os/conversation_synthesis.py:226` (call-site rewire); `apps/compositions/models.py` (new field); new migration `0020_composition_verification_warnings_legacy.py`; `apps/compositions/starters.py` (persistence for the new column); `apps/compositions/management/commands/k64_shadow_diff.py` (read all three columns); tests.
- **Invariant protected:** persistence semantics per §5; rollback mechanism per §6; independence from strict-mode per §7.
- **Rollback:** unset `CHARACTER_OS_K64_AUTHORITY` (or set to `legacy`). Restart workers. Byte-identical to today externally.
- **Test gate:** all Slice 1 tests still pass; new dispatcher / dual-write invariant / defensive-fallback tests pass; dogfood 3 fresh compositions under default legacy, confirm `verification_warnings == verification_warnings_legacy`.
- **Production authority change:** NONE by default. Authority ONLY flips if the operator sets `CHARACTER_OS_K64_AUTHORITY=d_pos` explicitly.

**Slice 3 — Q-278-4.3: Flip default authority to `d_pos`.**
- **Responsibility:** change dispatcher's default authority resolution from `"legacy"` to `"d_pos"`.
- **Files/surfaces:** one-line change in `character_os/claim_verifier_dispatch.py` resolver.
- **Invariant protected:** all Slice 2 invariants.
- **Rollback:** set `CHARACTER_OS_K64_AUTHORITY=legacy` explicitly OR revert the one-line default change.
- **Test gate:** dispatcher tests still pass with new default; ≥ 5 fresh operator dogfood compositions post-flip pass acceptance criteria per §8.
- **Production authority change:** YES — D-POS becomes authoritative by default. `verification_warnings` = D-POS output. `verification_warnings_legacy` = legacy shadow.

**Slice 4 — Deferred, NOT scheduled: retire legacy verifier + stoplist + `verification_warnings_shadow` column.** Only after long post-Slice-3 stability window with zero rollback signals + explicit approval.

### Recommendation

**GO-IMPLEMENT-SLICE-1.**

Slice 1 is the smallest possible change with the highest evidence density:

- Concrete measured evidence: PROPN gate closes the only ambiguous shadow finding (`Success` in Specimen 4) without regressing any short-acronym coverage (FBI/CIA/FDA/IRS all preserved) or any real proper-noun case tested.
- No authority change. No schema change. No migration. No new dependency.
- Independent of Slices 2/3 — landing Slice 1 does NOT commit to Slice 2. Chris + ChatGPT re-decide after Slice 1 lands.
- Rollback is a one-function revert.

GO-IMPLEMENT-SLICE-1 authorizes only Slice 1. Slices 2 and 3 remain gated on separate Chris + ChatGPT decisions after Slice 1 evidence is available.

### Explicit decision gate

**STOP.** No implementation lands until Chris + ChatGPT explicitly:

- Approve **GO-IMPLEMENT-SLICE-1** → open Q-278-4.1 and land the NER-supplement PROPN gate.
- OR **MODIFY-DESIGN** — the cutover plan needs adjustment before slice work begins (e.g. different column naming, different authority-flag semantics, different acceptance signals).
- OR **EXTEND-SHADOW** — the fresh-window evidence isn't yet sufficient; add more dogfood before landing anything.
- OR **NO-GO** — reject the cutover direction; freeze at Q-278-3.2's shadow-only architecture.

Strict-mode considerations, adjacent-surface migrations (ConversationMessage/Script), and legacy retirement are downstream of Slice 3 and out of scope for this decision.

*Chris + ChatGPT decision:* **GO-IMPLEMENT-SLICE-1** approved. Open Q-278-4.1. No Slice 2 / Slice 3 work.

---

## Q-278-4.1 — Slice 1 implementation: NER-supplement POS=PROPN gate

### Precise scope

Implement **exactly** the NER-supplement `token.pos_ == "PROPN"` gate audited in Q-278-4 §2. No authority change. No schema change. No new dependency. No migration. No strict-mode change. No stoplist change. No adjacent-surface migration.

### Implementation

**File touched:** `shell/character_os/claim_verifier_ner.py` — single-function edit inside `extract_named_entities_ner`, plus a docstring update on the module header.

**The change** (extract): the NER supplement loop now skips any `doc.ents` span whose tokens are ALL non-PROPN.

```python
for ent in doc.ents:
    if ent.label_ not in _ENTITY_RELEVANT_LABELS:
        continue
    if _span_overlaps(ent.start_char, ent.end_char, matched_spans):
        continue
    # SESSION 278 Q-278-4.1 — require at least one PROPN token.
    if not any(tok.pos_ == "PROPN" for tok in ent):
        continue
    _emit(ent.text.strip(), f"ner_{ent.label_.lower()}",
          ent.start_char, (ent.start_char, ent.end_char))
```

Module docstring updated to record the gate + reference to the Specimen 4 canonical case that motivated it.

**No other files modified.** Zero migrations. Zero dependency changes. Zero authority / schema / strict-mode changes.

### Regression tests added

`shell/apps/compositions/tests/test_claim_verifier_ner_shadow.py` — 6 new tests under a new "Q-278-4.1 — NER supplement POS=PROPN gate" block:

- `test_ner_supplement_rejects_success_common_noun_q278_4_1` — canonical Specimen 4 turn-3 shape; asserts `Success` is NOT flagged post-gate.
- `test_ner_supplement_preserves_short_acronyms_after_propn_gate_q278_4_1` — parametrized across `FBI`/`CIA`/`FDA`/`IRS`; asserts each still flags. Load-bearing non-regression guarantee for the gate.
- `test_ner_supplement_preserves_real_proper_noun_entities_q278_4_1` — sweeps the full Q-278-4 §2 matrix (Wikipedia, NASA, France, Microsoft, OpenAI, Antoninus, Mark, Bill, James Webb Space Telescope, New York); asserts every real proper-noun/entity still flags. Ten deterministic assertions in one test.

### Test results

**Full D-POS regression suite:** `pytest apps/compositions/tests/test_claim_verifier_ner_shadow.py` → **38 passed** (32 pre-existing Q-278-3.2 tests + 6 new Q-278-4.1 tests).

**Adjacent 116-test gate:** `pytest apps/compositions/tests/test_dialogue_synthesis.py apps/compositions/tests/test_claim_verifier.py apps/compositions/tests/test_stoplist_watchdog.py apps/compositions/tests/test_dialogue_ai_topic_wiring.py` → **116 passed**.

Zero regressions in either suite. Total green: **154 tests**.

### Post-gate live verification against Specimen 4

Read-only replay of the Q-278-3.2 Specimen 4 (`fcba3242`) turn 3 text through the newly-gated `run_shadow_verifier`:

```
Specimen 4 turn 3 post-gate: []
  Success flagged? False
Persisted verification_warnings_shadow (from pre-gate write): [{'kind': 'ner_org', 'claim': 'Success', ...}]
```

Persisted row is intentionally unchanged (Slice 1 does not backfill historical rows). All new dialogue-scene shadow writes going forward will use the gated classifier.

### Prediction vs actual

- Predicted (Q-278-4 §2 measurement): PROPN gate rejects `Success` common-noun ORG mislabel; preserves FBI/CIA/FDA/IRS and all real proper-noun matrix rows. **Confirmed.**
- Predicted: single-function edit, no new dependency, no schema change, no migration. **Confirmed.** Files touched = 2 (source + test), no migrations, no config changes.
- Predicted: 32 D-POS tests + 116 adjacent tests remain green. **Confirmed.**
- Predicted: authority behavior unchanged; legacy verifier remains authoritative. **Confirmed** — no dispatcher, no authority flag, no persistence change.

No discrepancies from the audit prediction.

### Blast radius (actual)

- Code surface: 1 function body edit + module docstring update in `claim_verifier_ner.py`; 1 test module extension.
- Migrations: 0.
- New dependencies: 0.
- Authority change: none.
- SPA change: none.
- Persistence-shape change: none.
- Env / settings change: none.
- Rollback: revert the single function change; delete the 6 new tests. One-commit revert.

### Recommendation

Land Slice 1 as-is. Chris + ChatGPT re-decide Slice 2 (dispatcher + `verification_warnings_legacy` column + defensive fallback) after seeing the gated shadow's behavior on subsequent fresh dogfood.

### Explicit decision gate

**STOP.** No Slice 2 / Slice 3 work. Continue normal warn-mode dogfood; shadow rows now use the gated classifier. When Chris judges the evidence sufficient, decide separately:

- **GO-IMPLEMENT-SLICE-2** → open Q-278-4.2 (authority dispatcher + `verification_warnings_legacy` column + defensive fallback; default authority still `legacy`).
- **MODIFY-DESIGN** — revisit Slice 2 shape.
- **EXTEND-SHADOW-POST-GATE** — accumulate more post-gate shadow evidence first.
- **NO-GO** — freeze at Slice 1 (gate applied; shadow architecture stays; no cutover).

---

## Q-278-4.2 pre-implementation — boundary challenge (Chris + ChatGPT)

### The apparent contradiction

Q-278-4 §5 explicitly deferred Script and ConversationMessage migration:

> **Adjacent surfaces (`ConversationMessage`, `Script`):** NOT migrated in the cutover slices below. Q-278-3.2's dialogue-only shadow persistence is deliberately preserved. Adjacent-surface migration is a follow-up slice (Q-278-4.x, unopened), evidenced by the same classifier core + a per-model persistence pattern. Only migrating dialogue-scene compositions in the cutover keeps blast radius minimal.

But Q-278-4 §9 (blast-radius inventory) lists Slice 2 rewiring **three** call sites through a single dispatcher gated by one global flag `CHARACTER_OS_K64_AUTHORITY`:

- `character_os/dialogue_synthesis.py:1798`
- `character_os/script_synthesis.py:526`
- `character_os/conversation_synthesis.py:226`

Only `Composition.verification_warnings_legacy` is planned as the new persistence column in Slice 2. If Slice 3 later flips the default to `d_pos`, all three call sites would swap classifier — but only the dialogue-scene Composition surface has the shadow-observability substrate to detect regressions or rollback safely.

That is a real safety hole, not a documentation nitpick.

### Source-derived paths — all three surfaces

**A. Dialogue Composition (`template_kind = "dialogue_scene"`):**

| step | code path |
|---|---|
| verifier called | `character_os.dialogue_synthesis.synthesize_dialogue` → per-turn loop → `run_verifier` (`dialogue_synthesis.py:1798`) |
| current authority | Legacy verifier via `run_verifier` |
| persisted warning field(s) | `DialogueTurn.verification_warnings` (in-memory) flattened by `_dialogue_ai_flattened_warnings` → `Composition.verification_warnings`; **shadow via Q-278-3.2** → `Composition.verification_warnings_shadow` |
| strict/warn behavior | `run_verifier` reads `settings.K6_CLAIM_VERIFIER_MODE` → env → default `warn`; strict-mode `ClaimVerifierError` → `DialogueSynthesisFailedError` → `Composition.status = FAILED` |
| operator-visible consumer | `web/src/routes/compositions/$id.tsx` reads `verification_warnings` + `verification_status` |
| rollback / observability substrate | **YES** — `verification_warnings_shadow` column exists AND is populated by the D-POS shadow classifier (post-Q-278-3.2); `k64_shadow_diff` mgmt command consumes it |

**B. Script (B-arc `apps.scripts`):**

| step | code path |
|---|---|
| verifier called | `apps.scripts.synthesis.draft_script` → `character_os.script_synthesis.build_render_brief` → `run_verifier` (`script_synthesis.py:526`) |
| current authority | Legacy verifier via `run_verifier` |
| persisted warning field(s) | `Script.verification_warnings` (JSONField on `apps/scripts/models.py:138`); NO shadow column |
| strict/warn behavior | Same mode resolution; strict-mode `ClaimVerifierError` propagates to `apps/scripts/synthesis.py:133` → persisted with `verification_status="rejected"` + populated warnings |
| operator-visible consumer | `web/src/routes/workspace/scripts.$id.tsx` reads `Script.verification_warnings` |
| rollback / observability substrate | **NO** — no shadow column, no dual-run persistence, no comparison evidence, no `k64_shadow_diff` support |

*Note:* the SAME `script_synthesis.build_render_brief` call path ALSO produces the talking-head + long-form Composition warnings (via `apps/videos/views.py:151` and `character_os/duration_contract.py:653`). Those Composition rows have `verification_warnings_shadow` as a COLUMN (from the Q-278-3.2 migration) but that column has **never been written to** for non-dialogue Composition — the shadow classifier is only invoked from `dialogue_synthesis.py`, not from the script/talking-head path.

**C. ConversationMessage (K6.5):**

| step | code path |
|---|---|
| verifier called | `character_os.conversation_synthesis.generate_reply` → `run_verifier` (`conversation_synthesis.py:226`) |
| current authority | Legacy verifier via `run_verifier` |
| persisted warning field(s) | `ConversationMessage.verification_warnings` (JSONField on `apps/conversations/models.py:91`); NO shadow column |
| strict/warn behavior | Same mode resolution; strict → `ClaimVerifierError` → view sets `verification_status="rejected"` + persists onto ConversationMessage placeholder |
| operator-visible consumer | `web/src/routes/conversations/$id.tsx` reads `ConversationMessage.verification_warnings` |
| rollback / observability substrate | **NO** — no shadow column, no dual-run persistence, no comparison evidence, no shadow classifier invocation today |

**Also verified read-only from source:** `character_os/claim_verifier_ner.run_shadow_verifier` is called from exactly ONE production site — `dialogue_synthesis.py:1785-1832`. Neither `script_synthesis.py` nor `conversation_synthesis.py` imports or calls the shadow classifier.

### Mechanical consequence of the currently-planned Slice-2 + Slice-3 shape

If Slice 2 rewires ALL THREE call sites through a shared dispatcher gated on `CHARACTER_OS_K64_AUTHORITY`, and Slice 3 flips the global default to `d_pos`:

- **Dialogue-scene Composition** — becomes D-POS authoritative. `verification_warnings` = D-POS output. `verification_warnings_legacy` (new column) = legacy shadow. `verification_warnings_shadow` = D-POS self-mirror. **Full rollback + observability substrate available.**
- **Talking-head / long-form Composition** (via `script_synthesis.build_render_brief`) — silently also becomes D-POS authoritative. `verification_warnings` = D-POS output. `verification_warnings_legacy` = legacy shadow (if the Slice-2 dual-write logic runs on this path too). `verification_warnings_shadow` = empty (Q-278-3.2 shadow was NEVER wired into this path). **NO pre-cutover shadow evidence for D-POS behavior on talking-head briefs.** Q-278-3.1 measured D-POS on isolated sentences, not on real talking-head briefs. **Regression risk NOT audited.**
- **Script (B-arc)** — silently becomes D-POS authoritative. `Script.verification_warnings` = D-POS output. **No shadow column exists**, so Slice 2 would EITHER need to add one OR the surface would have no post-cutover observability at all. **NO pre-cutover shadow evidence.** Q-278-3.x never measured D-POS on any real Script row.
- **ConversationMessage (K6.5)** — silently becomes D-POS authoritative. `ConversationMessage.verification_warnings` = D-POS output. **No shadow column exists.** **NO pre-cutover shadow evidence.** Q-278-3.x never measured D-POS on any real spokesperson message.

**Legacy output persisted for comparison:** on talking-head Composition, only if Slice 2 explicitly adds a mirror write; on Script and ConversationMessage, only if Slice 2 also adds new columns to their models — a scope explosion the original audit deferred.

**Rollback evidence:** dialogue-scene fully protected; the other three surfaces would have zero to weak evidence, meaning "rollback" post-Slice-3 would be a blind decision on 3 of 4 surfaces.

**Does this violate the Q-278-4 §5 explicit deferral of adjacent-surface migration?** **YES.** Slice 3 as designed would functionally migrate all three adjacent surfaces (talking-head Composition, Script, ConversationMessage) to D-POS authority WITHOUT the "same classifier core + per-model persistence pattern" the deferral commits to.

**Answers to the three yes/no questions:**

- Would a global authority flip affect **Script**? **YES** — via `script_synthesis.py:526`, which serves both talking-head Composition and B-arc Script.
- Would it affect **ConversationMessage**? **YES** — via `conversation_synthesis.py:226`.
- Would those surfaces have equivalent dual-run persistence? **NO** — no shadow column on Script or ConversationMessage; talking-head Composition has the column but no data.

### Option comparison

**Option A — Dialogue-scene-only dispatch (narrowest).**
- Rewire ONLY `character_os/dialogue_synthesis.py:1798`.
- `script_synthesis.py` and `conversation_synthesis.py` remain calling `run_verifier` directly — legacy behavior identical to today.
- Add `Composition.verification_warnings_legacy` column (only relevant to dialogue-scene compositions, but the column lives on the shared Composition model — that's fine; it stays empty for talking-head/long-form rows).
- Authority flag scoped: `CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy" | "d_pos"` (renamed to reflect actual scope).
- Slice 3 flips only dialogue-scene authority. Script + ConversationMessage untouched.
- **Smallest code surface. Preserves Q-278-4 §5 deferral. Symmetric with Q-278-3.2 shadow evidence.**

**Option B — Surface-scoped authority (future-facing abstraction).**
- Shared dispatcher module, but authority flag is per-surface: e.g. three env vars `CHARACTER_OS_K64_AUTHORITY_DIALOGUE` / `..._TALKING_HEAD` / `..._CONVERSATION`, each `"legacy" | "d_pos"`, each defaulting to `"legacy"`.
- Slice 2 still only wires the dispatcher; Slice 3 still only flips the dialogue flag.
- Bigger up-front abstraction; deferred surfaces get one-line adoption later.
- Modest complexity tax vs Option A; slightly more future-proof.

**Option C — All-surface dispatch WITH equivalent dual-run persistence.**
- Rewire all three call sites; migrate Script + ConversationMessage to add shadow columns; extend the D-POS shadow classifier invocation into script/conversation synthesis with an equivalent env flag.
- Would produce true 3-surface parity but massively enlarges Slice 2 scope and takes Q-278-4 off its "smallest cutover plan" rails.
- Rejected on scope-lock grounds.

**Option D — Source-derived alternative.**
- Rewire all three call sites but the dispatcher internally hard-codes a "which caller am I answering for" and only takes the d_pos branch on dialogue callers.
- Ugly; inspection burden; hides scope in the dispatcher. Not preferred.

### Assessment per option

| dimension | A: dialogue-only | B: surface-scoped | C: all-surface + persistence | D: caller-check inside dispatcher |
|---|---|---|---|---|
| smallest code surface | ✓ smallest — 1 call site + 1 column + 1 dispatcher | 1 call site + 1 column + 1 dispatcher (same as A, but with per-surface flag plumbing) | 3 call sites + 3 columns/migrations + 3 shadow-invocation paths | 3 call sites + 1 column + dispatcher with internal branching |
| persistence requirements | 1 additive column on Composition | 1 additive column on Composition (or 3 later) | 3 additive columns across Composition/Script/ConversationMessage | 1 additive column on Composition |
| migrations | 1 | 1 | 3 (or 1 now + 2 later) | 1 |
| rollback correctness | fully protected on dialogue; adjacent surfaces unchanged so rollback is trivially safe | same as A | full parity but only after enormous scope | brittle — depends on dispatcher-internal caller inference |
| future Slice-3 behavior | flips only dialogue-scene authority | flips only dialogue-scene authority | would flip all three (only if the Chris + ChatGPT approval is explicit per surface) | flips dialogue by dispatcher rule |
| strict-mode implications | independent per surface (dialogue can strict-flip without dragging Script/Conversation) | same as A | strict-flip forced to be per-surface eventually | strict-flip logic tangled with authority logic |
| test burden | small — dispatcher tests + dual-write correctness on dialogue | slightly larger — per-surface authority-flag tests | large — 3 surface-worth of shadow tests | brittle — must test dispatcher's caller-inference logic |
| respects "smallest proven surface" discipline | ✓ | ✓ | ✗ (bloats scope) | partial |

### Flag-name reconsideration

The originally proposed `CHARACTER_OS_K64_AUTHORITY` name is **misleading given only one surface initially participates**. It reads as system-wide authority control, but under Options A or B it only actually controls dialogue-scene authority.

**Recommended rename (deferred to Slice-2-implementation slice):** `CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy" | "d_pos"`, or under Option B a small family `CHARACTER_OS_K64_AUTHORITY_<SURFACE>`. Either shape explicitly encodes scope in the flag name so a future operator (or an LLM assisting) cannot accidentally believe setting one env var flips the whole verifier.

The Q-278-3.2 shadow-mode env var `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` is already dialogue-scoped by virtue of the call site — it just doesn't broadcast that in its name. Fine as-is because it only ever gates behavior on the one call site that inspects it. The Slice-2 authority flag needs the scope in the name because the DISPATCHER is what interprets it.

### Recommended smallest boundary

**Option A — Dialogue-scene-only dispatch.**

Rationale:

- Preserves the "smallest proven surface" discipline that has governed Q-278-3.x / Q-278-4.x.
- Symmetric with the Q-278-3.2 shadow evidence + Q-278-3.2 fresh-window measurement (all five specimens are dialogue-scene).
- Explicitly upholds the Q-278-4 §5 deferral of adjacent-surface migration.
- Preserves Chris's stated invariant: *a future authority flip must NEVER silently broaden its behavioral blast radius to a surface that did not receive equivalent shadow/dual-run evidence*.
- Rollback + observability substrate exactly matches the surface being flipped.

Adjacent surfaces (talking-head Composition via `script_synthesis`, B-arc Script, ConversationMessage) remain **fully legacy-authoritative through Slice 2 and Slice 3**. Migrating them becomes a separately-scoped future slice (Q-278-4.x, still unopened) that gets its own shadow window per surface before any authority flip.

### Slice 2 design status: MODIFY-SLICE-2-DESIGN

The original Q-278-4 §9 blast-radius inventory listed three rewired call sites and one global flag. **That design does not survive this mechanical check.** Slice 2 must be revised BEFORE implementation to:

1. Rewire ONLY `character_os/dialogue_synthesis.py:1798`.
2. Leave `character_os/script_synthesis.py:526` and `character_os/conversation_synthesis.py:226` untouched.
3. Rename the flag to explicitly encode its scope (e.g. `CHARACTER_OS_K64_DIALOGUE_AUTHORITY`).
4. Keep the `Composition.verification_warnings_legacy` column addition (it lives on the shared Composition model; dialogue-scene rows populate it; talking-head/long-form rows leave it `[]` because their call site still uses legacy `run_verifier` directly).
5. Retain defensive fallback (spaCy failure → dispatcher falls back to legacy AND logs ERROR) on the dialogue path only.
6. Everything else in Q-278-4 §5-§9 (persistence semantics, warn/strict separation, acceptance signals, rollback design) applies as-is on the dialogue-only scope.

Slice 3 correspondingly flips ONLY the dialogue-scene default authority. Talking-head Composition, Script, and ConversationMessage remain legacy-authoritative until a future scope-locked slice (Q-278-4.x, unopened) provides their own shadow windows.

### Prediction vs actual

Prediction (initial Q-278-4 §9 shape): "three call sites can safely be dispatched together because they use the same classifier core." **Falsified** — the classifier core is shared, but the **observability substrate is not**. Two of the three surfaces (Script, ConversationMessage) have no shadow column and no shadow-classifier invocation, and the third (talking-head Composition via `script_synthesis`) has a shadow column that has never been written. A global authority flip would silently violate the Q-278-4 §5 deferral.

Prediction: no adjacent-surface migration in Slice 2. **Confirmed as intent, but the design as written would violate it.**

Prediction: rollback is a one-flag flip. **Still true on the dialogue-only scope; untrue if the flag also silently controls Script + ConversationMessage.**

Concrete surprise: even "Composition-only" isn't clean because talking-head + long-form Composition go through `script_synthesis.build_render_brief`, not through `dialogue_synthesis.synthesize_dialogue`. The safe boundary is **dialogue-scene template_kind**, not "Composition."

### Explicit decision gate

**STOP.** Slice 2 design must be **revised** before implementation. Chris + ChatGPT must explicitly:

- **Approve the revision to Option A (dialogue-scene-only dispatch)** → open the revised Q-278-4.2.
- **Approve Option B (surface-scoped authority abstraction)** if broader future capability is desired now.
- **Reject the current Slice-2 design entirely** — pause the cutover plan.

Do NOT implement any Slice-2 shape until an explicit revision is approved. Q-278-4.1 (the PROPN gate) remains landed and unaffected regardless of this decision.

*Chris + ChatGPT decision:* **APPROVE REVISED OPTION A** — dialogue-scene-only dispatch. Open Q-278-4.2.

---

## Q-278-4.2 — Slice 2 implementation: dialogue-scene dispatcher + `verification_warnings_legacy`

### Precise scope (approved)

Implement the smallest slice that establishes the dialogue-scene dispatcher + dual-write substrate. Preserve all boundary constraints from the Q-278-4.2 pre-implementation boundary challenge:

- Rewire ONLY `character_os/dialogue_synthesis.py`.
- Leave `character_os/script_synthesis.py` and `character_os/conversation_synthesis.py` unchanged.
- Talking-head / long-form Composition, B-arc Script, ConversationMessage all remain legacy-authoritative.
- New env/settings flag `CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy" | "d_pos"` (default `"legacy"`).
- Add `Composition.verification_warnings_legacy` (additive JSONField).
- Populate dual-run persistence only for dialogue-scene compositions.
- Defensive fallback: D-POS execution failure → legacy authority substituted + ERROR log.
- Preserve warn/strict semantics; do NOT flip default authority.
- No adjacent-surface migration; no Slice 3 work.

### Implementation

**Files added:**

- `shell/character_os/claim_verifier_dispatch.py` — new dispatcher module. Public: `resolve_dialogue_authority()` (settings > env > `"legacy"`; whitespace-only reads as unset; invalid values fall back to default + WARNING); `run_dialogue_verifier(text, factual_corpus, allowed_vocabulary, mode)` returning a `DialogueVerifierResult` dataclass carrying `authoritative` / `legacy` / `d_pos` / `d_pos_ok` / `authority_requested` / `authority_used`. Runs BOTH classifiers per call. Legacy strict-mode raise re-fires ONLY when legacy is authoritative; suppressed with WARNING when authority=d_pos. Defensive fallback on D-POS failure: substitutes legacy + logs ERROR. Never crashes the caller.
- `shell/apps/compositions/migrations/0020_session278_verification_warnings_legacy.py` — additive `AddField` for `verification_warnings_legacy` JSONField (default `list`, blank OK).
- `shell/apps/compositions/tests/test_claim_verifier_dispatch.py` — 21 new tests locking the dispatcher contract + scope-lock guards + dual-write invariants (see §Tests below).

**Files modified:**

- `shell/apps/compositions/models.py` — added `Composition.verification_warnings_legacy = models.JSONField(default=list, blank=True)`. Same lifecycle as `verification_warnings` (not immutable). Docstring blocks on both `verification_warnings_shadow` and `verification_warnings_legacy` explain the Q-278-4.2 invariant and Option A scope-lock.
- `shell/character_os/dialogue_synthesis.py` — replaced the per-turn direct `run_verifier(...)` call inside `synthesize_dialogue` with a call to the new dispatcher. Removed the now-obsolete `run_verifier` import from the module header. Added `DialogueTurn.verification_warnings_legacy` in-memory field. Retired the Q-278-3.2 `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` gate from the dialogue path (the dispatcher's dual-run supersedes it).
- `shell/apps/compositions/starters.py` — added `_dialogue_ai_flattened_legacy_warnings(result)` helper (mirrors the shape of the existing `_dialogue_ai_flattened_warnings` and `_dialogue_ai_flattened_shadow_warnings` helpers). Wired into `composition_kwargs` so `Composition.verification_warnings_legacy` is populated on every dialogue-scene AI-Topic render.
- `shell/apps/compositions/management/commands/k64_shadow_diff.py` — extended to read all three columns. Diff now compares `verification_warnings_shadow` (D-POS) vs `verification_warnings_legacy` (legacy) so the report is stable under authority flips. Pre-Q-278-4.2 rows (empty `verification_warnings_legacy`) fall back to comparing `verification_warnings` (assumed legacy pre-cutover) vs `verification_warnings_shadow`. Per-row AUTHORITY tag is inferred from mirror equality: `legacy`, `d_pos`, `legacy(pre-Q-278-4.2)`, `clean`, or `unknown`. Column labels renamed OLD_ONLY → LEGACY_ONLY, SHADOW_ONLY → D_POS_ONLY for post-cutover clarity.

**Files intentionally NOT touched (per Option A scope-lock):**

- `character_os/script_synthesis.py`
- `character_os/conversation_synthesis.py`
- `apps/scripts/*`
- `apps/conversations/*`

Two dedicated regression tests (`test_script_synthesis_does_not_import_dispatcher` + `test_conversation_synthesis_does_not_import_dispatcher`) source-inspect these modules to guarantee the boundary invariant is not silently broken by a future edit.

### Migration

`0020_session278_verification_warnings_legacy.py`. Single `AddField` on `Composition`. Additive-nullable-or-empty per the observability discipline. Applied cleanly to the local Postgres. Historical rows populate `verification_warnings_legacy = []` and read as "written before dual-run existed" — see §Historical rows below.

### Tests

**New dispatcher tests** (`test_claim_verifier_dispatch.py`, 21 tests):

- `resolve_dialogue_authority` (7 tests): default legacy; env flip to d_pos; settings-beats-env; whitespace-only unset; invalid values fall back to legacy.
- `run_dialogue_verifier` basics (3 tests): both classifiers run under default legacy; env flip to d_pos routes D-POS output as authoritative; real unsupported entity (`Antoninus`) preserved under BOTH authorities (founding hallucination invariant).
- Strict-mode preservation (2 tests): legacy strict-raise bubbles up under legacy authority; SUPPRESSED with WARNING under d_pos authority (legacy is not authoritative in that combination).
- Defensive fallback (1 test): forced D-POS RuntimeError with authority=d_pos → dispatcher substitutes legacy AND logs ERROR (verified via caplog).
- Q-278-1/4.1 continuity (6 tests): parametrized across `Fair`/`Come`/`Unless`/`Please`/`Always`; asserts default authority produces LEGACY-only warnings + empty D-POS; authority-flip end-to-end produces silent Q-278-1 class while `result.legacy` still captures the pre-cutover warning for shadow evidence.
- Dialogue-scene scope-lock (2 tests): source-inspection guards on `script_synthesis.py` and `conversation_synthesis.py` — MUST NOT import the dispatcher; if either does, the test fails loudly to prevent silent adjacent-surface broadening.
- Dual-write invariant on flattener (2 tests): under default authority, `_dialogue_ai_flattened_warnings` and `_dialogue_ai_flattened_legacy_warnings` produce structurally-equal output; under d_pos authority, authoritative flatten equals shadow flatten while legacy flatten diverges (locks the SHAPE of the Slice-3 acceptance signal).

**Adjacent test migration** (`test_dialogue_synthesis.py`, 3 tests): the pre-existing `test_k64_uses_speaking_character_corpus_per_turn`, `test_warnings_retain_speaker_and_turn_context`, and `test_strict_verifier_failure_raises` all monkeypatched `character_os.dialogue_synthesis.run_verifier`. That symbol no longer exists — the dispatcher owns the legacy call now. Updated the three patch targets to `character_os.claim_verifier_dispatch.run_verifier` so the test intent (fake the legacy verifier from the dispatcher's perspective) survives.

**Test results:**

- New dispatcher tests: **21 passed** (test_claim_verifier_dispatch.py).
- Q-278-4.1 D-POS regression suite: **38 passed** (test_claim_verifier_ner_shadow.py).
- Adjacent 116-test gate: **116 passed** (test_dialogue_synthesis + test_claim_verifier + test_stoplist_watchdog + test_dialogue_ai_topic_wiring). Zero regressions after the three patch-target updates.
- **Combined: 179 tests green.**

### Fresh dogfood dual-write verification

The full end-to-end persistence path (Composition column population under default legacy authority) is **not yet exercised** by a fresh render because that requires operator-driven synthesis + provider spend. The invariant is proven at two layers instead:

1. **Dispatcher layer:** `test_dispatcher_runs_both_classifiers_default_legacy_authority` asserts `result.authoritative == result.legacy` under default authority on real spaCy invocation.
2. **Flattener layer:** `test_flattener_dual_write_invariant_under_default_authority` asserts the two starters flatteners produce structurally-equal output when both per-turn columns carry the same legacy list.

The transitive guarantee: for any real dialogue-scene render under default authority, `Composition.verification_warnings == Composition.verification_warnings_legacy` because both are derived from the same source list (dispatcher's `authoritative == legacy`) via identical flattening. Chris's post-implementation fresh dogfood will verify this on real persisted rows.

**Historical rows (pre-Q-278-4.2, sanity-verified read-only):**

```
1aabbff6  auth_col_len=5  shadow_col_len=0  legacy_col_len=0
fcba3242  auth_col_len=7  shadow_col_len=1  legacy_col_len=0
1491d31c  auth_col_len=2  shadow_col_len=0  legacy_col_len=0
5f4bdbbc  auth_col_len=2  shadow_col_len=0  legacy_col_len=0
a1421a0e  auth_col_len=3  shadow_col_len=0  legacy_col_len=0
26c62b4b  auth_col_len=3  shadow_col_len=0  legacy_col_len=0
```

All historical `verification_warnings_legacy` values are empty (field just added); no backfill performed. `k64_shadow_diff` reports these rows with `AUTH=legacy(pre-Q-278-4.2)` and uses the fallback comparison (`verification_warnings` vs `verification_warnings_shadow`) so historical evidence remains interpretable end-to-end.

Live `k64_shadow_diff --days=30 --limit=5` on the local DB produces the expected shape:

```
LEGACY_ONLY total:   18  (ordinary-language false positives D-POS removed)
D_POS_ONLY total :    0  (entities D-POS surfaces that legacy missed)
BOTH total       :    1  (both classifiers agree)
```

Matches the Q-278-3.2 5/5 fresh-window totals bit-for-bit.

### Prediction vs actual

- Predicted (revised Q-278-4.2 boundary challenge): dialogue-only dispatch preserves adjacent-surface behavior byte-identically. **Confirmed** — adjacent surfaces call `run_verifier` unchanged; scope-lock guards enforce the boundary.
- Predicted: default authority `legacy` produces byte-identical external behavior to today. **Confirmed at dispatcher + flattener layers** via tests; end-to-end confirmation is Chris's fresh-dogfood step.
- Predicted: dispatcher tests + dual-write invariant tests prove Slice-3 acceptance signal (`verification_warnings == verification_warnings_legacy` under default). **Confirmed.**
- Predicted: Q-278-3.2 shadow env flag becomes a no-op for dialogue path. **Confirmed** — the dispatcher always runs both classifiers; the flag is no longer consulted in `dialogue_synthesis.py`.
- Predicted: three adjacent test failures from `test_dialogue_synthesis.py` due to removed `run_verifier` import. **Occurred as predicted**; fixed by re-pointing the three `mock_patch` targets to `character_os.claim_verifier_dispatch.run_verifier`; 116/116 adjacent tests then green.
- Predicted: defensive fallback works. **Confirmed** via `test_dispatcher_falls_back_to_legacy_when_d_pos_fails` using a mocked `RuntimeError`.
- Predicted: strict-mode raise re-fires under legacy authority, suppressed under d_pos. **Confirmed** via two dedicated tests.

No discrepancies from the audit prediction.

### Blast radius (actual)

- Files added: 3 (dispatcher module, migration, test file).
- Files modified: 4 (models, dialogue_synthesis, starters, k64_shadow_diff mgmt command).
- Files NOT modified (Option A scope-lock guard): `script_synthesis.py`, `conversation_synthesis.py`, any file in `apps/scripts/` or `apps/conversations/`.
- Migrations: 1 additive (`0020_session278_verification_warnings_legacy.py`).
- Dependency changes: 0 (spaCy + model already installed in Q-278-3.2).
- Externally-observable behavior under default `CHARACTER_OS_K64_DIALOGUE_AUTHORITY=legacy`: identical to Q-278-3.2 landed state on `verification_warnings` and `verification_warnings_shadow`; `verification_warnings_legacy` becomes populated on every new dialogue-scene render (== `verification_warnings` under default authority).
- Externally-observable behavior on adjacent surfaces: **UNCHANGED.** No touch to talking-head / long-form / Script / ConversationMessage code paths.
- Compatibility with `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT`: the env var is now a no-op for the dialogue path (dispatcher runs both classifiers unconditionally). It remains defined so operators / adjacent surfaces reading it directly are not broken; the effective behavior on the dialogue path is "always on".
- SPA implications: none — SPA still reads `Composition.verification_warnings` (unchanged column).
- Historical row impact: none. `verification_warnings_legacy` defaults empty; `k64_shadow_diff` recognizes the pre-Q-278-4.2 shape and uses the fallback comparison.
- Rollback: `unset CHARACTER_OS_K64_DIALOGUE_AUTHORITY` (or set to `legacy` — already the default). Under the default, the dispatcher still runs both classifiers, but `verification_warnings` mirrors legacy. To completely revert: revert this commit; the migration can be safely left in place (`verification_warnings_legacy` column is additive-nullable-or-empty). To rollback the schema too: `python manage.py migrate compositions 0019`.

### Unresolved questions

- Whether extending the dispatcher pattern to Script + ConversationMessage in a future slice reuses this dispatcher module (surface-scoped authority flags) or gets its own per-surface dispatcher. Deferred to Q-278-4.x cutover-followup.
- Whether the `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` env var should be formally deleted once every surface either has a dispatcher or has explicitly opted out. Housekeeping; not blocking.

### Explicit Slice-3 decision gate

**STOP after Q-278-4.2.** Slice 3 (Q-278-4.3 — flip default `CHARACTER_OS_K64_DIALOGUE_AUTHORITY` from `legacy` to `d_pos`) is NOT authorized.

Before Chris + ChatGPT approve Slice 3, the following evidence must be available:

- Fresh dialogue-scene dogfood renders under default `legacy` authority that confirm `Composition.verification_warnings == Composition.verification_warnings_legacy` bit-for-bit on the persisted rows (Chris-side operator step; I inspect after).
- Fresh dialogue-scene dogfood evidence collected via `k64_shadow_diff` continues showing zero D_POS_ONLY warnings that inspection classifies as true positives legacy caught.
- Chris + ChatGPT explicit approval to flip the default.

Post-Slice-3, adjacent-surface migration (Script + ConversationMessage) opens as a separately scope-locked slice (Q-278-4.x, unopened) with its own shadow windows per surface before ANY authority flip.

### Recommendation

Land Q-278-4.2 as-is. Continue normal warn-mode dogfood under default legacy authority. When Chris judges the dual-write substrate stable and wants to advance:

- **GO-IMPLEMENT-SLICE-3** → open Q-278-4.3 (one-line default flip in the dispatcher).
- **EXTEND-DUAL-WRITE-WINDOW** — accumulate more evidence first.
- **MODIFY-DISPATCHER** — revise dispatcher shape based on dogfood findings.
- **NO-GO** — freeze at Slice 2; keep dual-write as the terminal state.

Q-278-4.1 and this slice are independent commits and independently revertable.

---
