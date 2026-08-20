# SESSION 271 — Handoff

Concise starting point for the next Character OS session. Full SESSION 270 audience-aware character-performance research + evidence + corrections + synthesis live in `docs/design/SESSION_270_AUDIENCE_AWARE_PERFORMANCE_AUDIT.md` (§1–§14), with frozen evidence sidecars under `docs/design/session_270_experiment_data/` (four SESSION 270 renders) and `docs/design/session_269_experiment_data/06_composition_2ef5ee7e_evidence.json` (baseline reference).

Read the linked SESSION 270 doc before starting SESSION 271. This handoff is orientation, not a substitute.

---

## §A. WHERE WE ARE

- **SESSION 270 is CLOSED** (per §14 of the audit doc). Central audience-aware character-performance question answered **YES** with a bounded end-to-end pipeline caveat about at-risk technical vocabulary.
- **Repository checkpoint at handoff creation:** `main` at the SESSION 270 CLOSEOUT commit (SHA recorded in `SESSION_270_AUDIENCE_AWARE_PERFORMANCE_AUDIT.md` §14.6). Local `main == origin/main`. Working tree clean.
- **Local-real runtime expected state** (per §14.4 of the audit doc):
  - Celery worker running canonical `start-local-real.sh` invocation with **NO** `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` set.
  - `_resolve_solo_audience_hint(step={})` → `None`.
  - Django `http=302` at `/admin/`; media-engine `http=200` at `/health` with `any_mock=false`, `llm_provider=openai`, `llm_model=gpt-4o-mini`; Vite `http=200` at `/`.
  - Celery `inspect ping` → `pong / 1 node online`.
- **NarrativeMemory pool** in Patch' Workshop Universe: **14 active + 1 archived**. Unchanged across the entire SESSION 270 five-composition sequence.
- **Writing Contract version:** **5**. Unchanged.
- **Audience experiment env var:** **OFF**. Any SESSION 271 audience work must explicitly re-activate per the procedure documented in SESSION 270 §13.13 / §13.18 / §13.21 / §13.24.
- **Transient solo audience_hint research plumbing** (`shell/apps/compositions/primitives/avatar_speech.py::_resolve_solo_audience_hint` + `audience_hint` kwarg on `build_render_brief` / `synthesize_with_duration_gate` / `_assemble_task_message`): **still present, status remains "experimental research plumbing"**. Backwards-compatible (default `None` preserves all prior behaviour). Any decision to remove or productise must be a deliberate future slice.

---

## §B. WHAT SESSION 270 PROVED

**Central answer:** Character OS CAN change who Patch is addressing (register / metaphor family / explanation strategy / listener context) without changing who Patch is (identity / intelligence / humor / story / memory / factual grounding). Proven across four audience-conditioned real-mode renders on tightly-controlled substrate.

**Compositions inspected (all real-mode, all on Episode `2b6087d2-cbe3-47c4-a7ef-7d7625231472` "Patch does research on AI Agents", Universe "Patch' Workshop", Patch spokesperson `7fad8172-cd39-4bbe-85e0-ed705d900645`, solo_scene / talking_head, 90 s target, use_knowledge=on, opener blank, verifier=warn, writing contract v5):

| Role | Composition ID | Directive | Sidecar |
|---|---|---|---|
| Baseline (adult/general) | `2ef5ee7e-7a55-4083-a587-1b5799bbaa47` | (none — implicit adult/general) | `docs/design/session_269_experiment_data/06_composition_2ef5ee7e_evidence.json` |
| Verbose child (Experiment 1) | `f0e0a7bf-28db-4c18-b5c5-550737cfa4af` | 372-char CHANGE/PRESERVE contract | `docs/design/session_270_experiment_data/01_composition_f0e0a7bf_evidence.json` |
| Minimal child (Q-270-9) | `9880eb93-cbfc-48bf-ab19-9ff16a67fa3b` | 41-char `AUDIENCE: children around 8-10 years old.` | `docs/design/session_270_experiment_data/02_composition_9880eb93_evidence.json` |
| Broad adult beginner (Q-270-8 REVISED) | `0b3c1fc1-d6cc-4ce9-9647-264fc23b2cb9` | 42-char `AUDIENCE: adults who are new to AI agents.` | `docs/design/session_270_experiment_data/03_composition_0b3c1fc1_evidence.json` |
| Nontechnical adult beginner (Q-270-13) | `c3ff972d-a7a0-4882-960a-60084485cc02` | 79-char `AUDIENCE: general adults with no technical background who are new to AI agents.` | `docs/design/session_270_experiment_data/04_composition_c3ff972d_evidence.json` |

**Strong findings (per §14.2):**

1. Character preservation robust under minimal audience directives — never a FAIL on preservation dimensions across 4 audience-conditioned specimens.
2. Audience labels produce distinct communication strategies per audience — child concrete-physical vs adult conversational vs adult workshop-native are demonstrably different metaphor families.
3. NarrativeMemory promotion discipline held across five consecutive renders (zero promotions; pool unchanged 14+1).
4. Same-knowledge + same-memory substrate stayed controlled (identical `knowledge_chunk_ids` + identical `memory_ids=[8d4fdfec-...]` across all 5 compositions — retrieval is deterministic under identical query).
5. Final-output technical-vocabulary reliability is imperfect under minimal directives; explicit vocabulary/technical-accessibility guidance in the verbose specimen `f0e0a7bf` **appears reliability-enhancing** for final-output vocabulary handling (only tested condition whose accepted output consistently closed the *"call APIs"* gap).
6. K6.4 `proper_noun` heuristic reproducibly false-positives on sentence-initial capitalised tokens — bounded verifier-quality defect (Q-270-16), NOT audience-related.

**Bounded caveat (refined post-close per §13.28 re-audit):**

For at-risk technical vocabulary (`API`, `language model`, `state`), the CURRENT END-TO-END SYNTHESIS PIPELINE does not, under minimal audience directives, guarantee that every such term will remain audience-accessible in the FINAL ACCEPTED output. **Whether that weakness originates in the audience directive itself, the corrective-pass expansion mechanism, or their interaction is NOT yet resolved.** §13.28 evidence: in 2 of 3 minimal-directive audience-conditioned specimens, the FIRST PASS was clean on at-risk terms and the CORRECTIVE EXPANSION pass reintroduced them from the Factual Basis. The verbose specimen `f0e0a7bf` was the exception — its CHANGE clause persisted through corrective expansion.

---

## §C. IMPORTANT OPEN FINDINGS (priority-ordered per §13.25.3)

| Priority | # | Question |
|---|---|---|
| **HIGH** | **Q-270-15** | When a solo_scene audience-conditioned first pass is rejected only for duration, does the corrective retry preserve the same audience-specific vocabulary/knowledge-boundary transformation while expanding content? **Audit-first — no paid render required for the initial audit step.** Compare first-pass vs corrective-pass prompt assembly + frozen outputs across existing five specimens before any code change. |
| **MEDIUM** | Q-270-12 | Would a minimal audience label + a targeted vocabulary-translation directive (2-clause hybrid) match the verbose contract at lower token cost? **Reordered below Q-270-15** — premise is potentially wrong if Q-270-15 confirms a corrective-pass mechanical cause. Do NOT execute before Q-270-15 audit is at least attempted. |
| LOW | Q-270-10 | Repeat minimal-child render to test whether the API miss is stochastic vs systematic — largely subsumed by §13.28 cross-specimen evidence. |
| LOW | Q-270-11 | Register-vs-knowledge-boundary systematic-vs-stochastic across multiple renders per audience — would need substantial n to fully resolve. |
| OPEN | Q-270-2 | Is the §5 Task Hard-Constraint seam the RIGHT eventual home for audience signal? |
| OPEN | Q-270-6 | Does `dialogue_scene` need identical audience semantics? — untested. |
| OPEN | Q-270-7 | Rename `who_you_help`'s `AUDIENCE:` prompt label to reduce confusability with a future audience-addressee field? |
| OPEN | **Q-270-16** | K6.4 `proper_noun` heuristic false-positive on sentence-initial capitalised tokens (reproducible defect). **NOT audience-related.** Do NOT fix in any SESSION 271 audience-experiment slice. |

None of these are implementation-blocking.

---

## §D. RECOMMENDED SESSION 271 START — TWO CLEAN WORKSTREAMS

Chris + ChatGPT + Claude choose which. **Do not mix them in a single render.**

### §D.1 Workstream 1 — Patch story-progression dogfood (return to normal Universe development)

SESSION 270 intentionally froze story state by reusing the same Episode across five audience-conditioned renders. If Chris wants to return to organic Universe development, the next Episode should finally permit Patch to act on the idea he has been researching.

**Candidate Episode seed** (Chris may pick different wording):

> *"Patch gives the workshop agent one small job to see what it actually does."*

Principle: the new Episode intent should authorise actual action or a bounded outcome, not another research/planning scene. Then:

- Dogfood through real UI (existing solo_scene machinery).
- Inspect actual persisted Composition/runtime evidence.
- Evaluate whether a durable state change occurred.
- Apply SESSION 269 §16.8 promotion discipline — *good content ≠ memory-worthy event*. Promote to `NarrativeMemory` **only** if runtime evidence reveals an actual bounded durable outcome.

**Do NOT mix audience experiment variables into this story-progression render** unless explicitly authorised. Ensure `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` is unset before the render.

### §D.2 Workstream 2 — Q-270-15 corrective-pass audience-invariance audit

If Chris wants to stay on audience mechanics, **begin with AUDIT only. No paid render required for the first step.**

The §13.28 cross-specimen re-audit already showed a directional pattern (2 of 3 minimal-directive audience specimens exhibit first→corrective technical-term reintroduction). Q-270-15's audit step deepens that:

- **Falsifiable question:** *"When a solo_scene audience-conditioned first pass is rejected only for duration, does the corrective retry preserve the same audience-specific vocabulary/knowledge-boundary transformation while expanding content?"*
- **Suggested first audit dimensions** (all doable from frozen evidence — no render cost):
  - Compare first-pass vs corrective-pass PROMPT ASSEMBLY (system + user text) — is the audience_hint present on both calls or only on the first?
  - Verify `audience_hint` presence on both first-pass and corrective-pass `_assemble_task_message` invocations in `synthesize_with_duration_gate._synthesize` closure (`shell/character_os/duration_contract.py:524-533` — the closure passes `audience_hint=audience_hint` on both invocations by design, but confirm by inspection / test).
  - Inspect corrective_hint wording + precedence — does the expansion instruction (`"Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied"`) directionally pull the writer back to raw Factual Basis vocabulary?
  - Catalogue which technical tokens are introduced on retry across the five specimens (extend the §13.28 table if useful).
  - Determine whether the Factual Basis chunks get copied more literally during expansion.
- **Only if the audit supports the mechanical-cause hypothesis, consider a controlled additional render** (single Composition, same substrate, one at-risk audience, capturing both prompt versions and both output versions) to confirm.
- **Do NOT change any prompt or code** during the audit step.

---

## §E. METHODOLOGY TO PRESERVE

**Evidence-first cycle** (unchanged from SESSION 269 + reinforced across SESSION 270):

> AUDIT / ORIENT → falsifiable question → smallest change only if evidence requires → real UI dogfood → inspect actual persisted runtime state → freeze Composition evidence → interpret → NarrativeMemory only for actual durable state changes → document under `docs/design/` → commit clean checkpoint.

**Verification hierarchy** (SESSION 269 §13.1):

> SOURCE IMPLEMENTED → TESTED → LIVE VISIBLE → OPERATOR REACHABLE. Never upgrade a claim without evidence at the claimed level.

**Non-promotion discipline:**

- **Good content ≠ memory-worthy event.** Only bounded, durable state change justifies a `NarrativeMemory` promotion.
- **Audience rerender ≠ story progression.** Reusing an Episode intent to control listener conditions is a research technique, NOT evidence that the character fails to act. Do not conflate.

**Causal precision** (added during SESSION 270 CLOSEOUT):

- Distinguish "final-output reliability" from "causal necessity." A specimen's accepted output failing on a criterion does not prove the source of the failure; earlier pipeline stages (first pass, corrective retry, prompt assembly) may localise the cause elsewhere. Prefer AUDIT of existing evidence over a new render whenever possible.

**Documentation discipline:**

Meaningful audits / runtime findings / comparisons / experiments MUST be persisted under `docs/design/`. Do not leave important findings only in terminal output. Chris uploads these Markdown files into ChatGPT for joint review — durable docs are the primary handoff surface between Claude and ChatGPT.

---

## §F. DO NOT DO AUTOMATICALLY

All of the following require a NEW evidence-backed decision. Do not roll them in without explicit authorisation:

- Build `Audience` model / `AudienceProfile` / schema.
- Add `age_group` / `expertise_level` / `technical_background` / `knowledge_boundary` enums or fields.
- Add SPA UI (audience dropdown, listener-model form, etc).
- Move audience ownership to `Episode` / `Universe` / `Composition` / `Teammate` / `Recipe`.
- Add default+override hierarchy.
- Add `dialogue_scene` audience plumbing.
- Bump `WRITING_CONTRACT_VERSION` to 6.
- Add a vocabulary-accessibility clause to the writing contract or to the audience-hint plumbing.
- Fix the corrective-pass audience-invariance behaviour (Q-270-15) — audit first.
- Fix the K6.4 `proper_noun` heuristic (Q-270-16) — bounded follow-up, not urgent, not audience-related.
- Promote any NarrativeMemory row.
- Remove the transient audience-hint research plumbing.

---

## §G. DURABLE DOC WORKFLOW REMINDER

Meaningful findings live under `docs/design/`. Chris uploads them into ChatGPT for joint review, so:

- Every SESSION should produce or update at least one durable Markdown document under `docs/design/`.
- Frozen experiment evidence goes in `docs/design/session_<N>_experiment_data/` as JSON sidecars.
- Historical wording is preserved with addenda rather than overwritten. When a re-audit changes a causal interpretation, add a correction section rather than rewriting the original.
- Commits should carry a clear subject that names the section(s) touched.
- Do not batch unrelated work into a single "session close" commit.

---

**End of SESSION 271 handoff. Do NOT start SESSION 271 work in the SESSION 270 CLOSEOUT slice.**
