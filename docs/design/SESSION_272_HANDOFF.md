# SESSION 272 — Handoff

Concise starting point for the next Character OS session.

**Full SESSION 271 record** — including all nine slices, the v6 implementation slice, and the §191 canonical v6 verification verdict — lives in `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md`. Seven frozen evidence sidecars under `docs/design/session_271_experiment_data/` (Trials 1–6 + the canonical v6 verification `07_composition_994e7b1b`).

**Full SESSION 270 record** — audience-aware character-performance research — lives in `docs/design/SESSION_270_AUDIENCE_AWARE_PERFORMANCE_AUDIT.md` with sidecars under `docs/design/session_270_experiment_data/`.

Read both audit docs (or at least their §14 / §191 closing sections) before starting SESSION 272. This handoff is orientation, not a substitute.

---

## §A. WHERE WE ARE

- **SESSION 271 is CLOSED.** Audience-aware communication architecture for `solo_scene` is RATIFIED (v6) with a documented known limitation.
- **Repository checkpoint:** `main` at the SESSION 271 CLOSEOUT commit (SHA recorded in `SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` §192). Local `main == origin/main`. Working tree clean.
- **Local-real runtime expected state** (verified at SESSION 271 close):
  - Django `:8010/admin/` → `http=302`.
  - Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`.
  - Vite `:5174/` → `http=200`.
  - Celery `inspect ping` → `pong / 1 node online`.
  - Fresh worker PIDs (post-`start-local-real.sh` restart on 2026-08-20 12:18): zero `SOLO_AUDIENCE_HINT` / `COMMUNICATION_POLICY_HINT` / any `CHARACTER_OS_*_HINT` / `_POLICY` / `_EXPERIMENT` env vars.
- **Writing Contract version:** **6** (bumped from 5 in SESSION 271 §187 to add the universal `AUDIENCE-AWARE COMMUNICATION` invariant to `_solo_scene_contract`; standalone / long_form / dialogue_scene contract text remains byte-stable).
- **NarrativeMemory pool** in Patch' Workshop Universe: **17 active memories** (unchanged across the entire SESSION 271 render sequence — 8 dogfood + verification renders, zero promotions).
- **All audience/policy/revision experiment env vars:** OFF.

---

## §B. WHAT SESSION 270 ESTABLISHED (unchanged from SESSION 271 open)

Character OS CAN change *who Patch is addressing* (register / metaphor family / explanation strategy / listener context) without changing *who Patch is* (identity / intelligence / humor / story / memory / factual grounding). Proven across four audience-conditioned real-mode renders on tightly-controlled substrate. Bounded caveat at close: at-risk technical vocabulary (`API`, `language model`, `state`) sometimes survives corrective expansion into the final accepted script. SESSION 271 refined that caveat's causal model — see §D.

---

## §C. WHAT SESSION 271 ESTABLISHED

### §C.1 Audience-aware communication as a general Character OS concern (Slice 7)

**E-KNOWLEDGE-1** (experimental `communication_policy_hint` kwarg / env plumbing in `avatar_speech`) proved that character-agnostic communication policy could be plumbed into the §5 Task HARD CONSTRAINTS block WITHOUT touching the Writing Contract. Trials 4 + 6 confirmed reproducible behavioral effect. Bounded caveats: activation-gap failures (3 of 5 trials failed when the operator had to set env vars across a session boundary; 2 of 5 succeeded via the Claude-inline activation pattern discovered mid-session).

### §C.2 Character-agnostic architecture for arbitrary future characters (Slice 8)

Fox-first thought experiment (would this design work for a fresh workspace whose first character is *"a fox who owns a bakery"* with no Patch/Rivet knowledge assumptions?) drove the architectural design. Outcome: the audience-aware invariant MUST live in the Writing Contract (universal, retrieval-independent, character-agnostic), not in the knowledge document or the persona. Per-render listener descriptor is a separate optional signal.

### §C.3 Final design ratification (Slice 9)

- Universal `AUDIENCE-AWARE COMMUNICATION` invariant wording ratified clause-by-clause against fox-baker / bear-coffee-shop / Patch / Rivet / unrelated-domain thought experiments. Seven identity dimensions preserved (identity, intelligence, expertise, humor, personality, factual grounding, confidence). Four adaptation levers allowed (technical depth, vocabulary, examples, analogies).
- `Composition.audience_hint` chosen as the persisted per-render listener descriptor. **Option C hybrid:** Composition field is source of truth; `talking_head` starter copies to `step.params["audience_hint"]` so the SESSION 270 `_resolve_solo_audience_hint` resolver picks it up first in its `step.params > settings > env` precedence chain — no primitive-layer changes required.
- Empty `Composition.audience_hint` ⇒ v6 invariant reads `Teammate.who_you_help` from §1 AUDIENCE as the character's baseline listener. Non-empty ⇒ §5 HARD CONSTRAINTS AUDIENCE DIRECTIVE block emitted in addition to the §4 universal invariant; both compose.

### §C.4 v6 shipped (Slice 9 §187 implementation)

Commit **`c16814d`** landed:

| Surface | Change |
| --- | --- |
| `character_os/writing_contract.py` | `WRITING_CONTRACT_VERSION` 5→6; `_AUDIENCE_AWARE_COMMUNICATION_BLOCK` inserted into `_solo_scene_contract` between INVARIANTS and SHAPES |
| `apps/compositions/models.py` | `Composition.audience_hint = TextField(blank=True, default="")`; added to `_IMMUTABLE_OBSERVABILITY_FIELDS` |
| `apps/compositions/migrations/0018_composition_audience_hint.py` | Single `AddField` op, additive-nullable per SESSION 262 discipline; zero backfill |
| `apps/compositions/starters.py` | `talking_head` accepts `audience_hint` kwarg → coerces (strip) → persists → copies non-empty to `step.params` |
| `apps/compositions/views.py` | `CompositionRecipeViewSet.create` reads body top-level `audience_hint`; `inspect.signature` gate injects into starter kwargs only when the starter accepts it |
| `apps/compositions/serializers.py` | `CompositionSerializer` exposes `audience_hint` on GET |
| Tests | New `test_session271_slice9_audience_hint_field.py` (10 tests); 10 version-pin bumps; universal-invariant assertions in `test_writing_contract_solo_scene.py`; Slice 7 leak-fragment narrowing; isolation whitelist updated |

**1327 tests pass** in `apps/compositions/ + apps/universe/` post-slice. One pre-existing unrelated failure (`MediaEngineClient.image_overlay` in `test_media_engine_timeouts.py`) confirmed present on `main` before this slice; belongs to a separate media-engine cleanup slice.

### §C.5 v6 verification verdict (Slice 9 §191 forensics)

**Verdict B — RATIFY V6 WITH KNOWN LIMITATION.**

Canonical v6 verification render: Composition **`994e7b1b-e95a-4b9b-b17e-1b25611fcd8e`** on Episode `Patch does research on AI Agents`. Persisted `audience_hint=""` AND `Patch.who_you_help=""` — the hardest possible v6 test (no audience information anywhere except the universal invariant text itself). Universal invariant still fired. Accepted script contains ALL six accessible expressions Chris flagged as behavioral success (`A language model can give you one answer` / `handle a task with more than one step` / `information, state, tools` / `remember what matters` / `respond when the situation changes` / `can we check its work`) AND all three Patch identity signature markers (`More context sounds harmless. Like giving somebody a bigger desk.` / `pursuing the completely wrong objective with tremendous enthusiasm` / `before it causes administrative weather`).

**Residual jargon causal ranking (§191.9):**

1. **C — Retrieved KnowledgeDocument lexical gravity (dominant).** Chunk `505acbba` in `PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE` packs `call APIs, perform multi-step tasks, maintain state` into a dense enumeration. Every same-topic specimen pulls `call APIs` raw (5/5 renders across v6 + E-K1 + 3 canonical historical).
2. **D — Corrective-pass expansion reintroduces terminology (co-dominant).** Draft A of the v6 render was clean (no `call APIs`, no raw `state`). Draft B, forced to expand by ~500 chars under a corrective hint that explicitly said *"Expand secondary detail from the knowledge chunks"*, pulled the raw enumeration back in.
3. A (v6 too weak) — **rejected**; Draft A proves the invariant works on this substrate.
4. B (persona insufficient) — **rejected**; Patch's `character_point_of_view` is directionally aligned.

The operative combination is **C + D**. Redesigning v6 would not address it; redesigning the corrective-hint wording OR the knowledge-doc shape would.

---

## §D. UNRESOLVED — KNOWLEDGE-DOCUMENT SHAPE QUESTION (recommended SESSION 272 opener)

**Question (§191.11):**

*"How should Character OS factual knowledge represent technically precise concepts while also giving synthesis accessible semantic formulations, without duplicating facts, dumbing down expert knowledge, or baking audience-specific prose into retrieval documents?"*

Explicit distinctions:

| Not the next question | Why |
| --- | --- |
| Audience-architecture | CLOSED — v6 ratified per §191.10 |
| Character persona | Not the bottleneck — Patch's `character_point_of_view` is directionally aligned |
| Retrieval ranking | Same 5 chunks across every same-topic specimen; ranking is stable |
| Chunking | Chunks are ~200-word semantic paragraphs; sizing is not the pathology |
| Corrective synthesis | *Related* (co-dominant cause) but separately owned by Q-270-15c. The knowledge-shape question is *upstream*: even without corrective expansion, a chunk that encodes a concept only through a dense enumeration has no material for the model to accessibilize |

**Do not implement a knowledge rewrite in the first SESSION 272 slice.** Start with audit + architectural exploration; a knowledge-authoring convention should be *designed against arbitrary future characters* (fox baker, bear coffee-shop, expert-technical, child-facing), not authored for Patch first.

---

## §E. OTHER OPEN FINDINGS (priority-ordered)

| Priority | # | Status |
| --- | --- | --- |
| **HIGH** (SESSION 272 opener) | **Knowledge-authoring / knowledge shape** | See §D. |
| MEDIUM | **Q-270-15c** (corrective revision semantics) | Slice 3 evidence collected. Corrective-pass reintroduction of terminology is now understood to be a co-dominant cause of residual jargon in solo_scene renders (§191.9 rank 2). Any SESSION 272 slice touching corrective-hint wording should coordinate with the knowledge-shape work. |
| MEDIUM | Q-270-16 (K6.4 `proper_noun` false-positive) | Reproducible verifier defect. NOT audience-related. Untouched by SESSION 271. Standalone verifier-quality slice. |
| OPEN | Q-270-6 (`dialogue_scene` audience semantics) | Not explored. `dialogue_synthesis` was deliberately kept out of every SESSION 271 slice's scope. If dialogue needs audience-aware treatment, a separate v6→v7 slice would add the invariant to `_dialogue_scene_contract` and thread `audience_hint` through `synthesize_dialogue`. |
| OPEN | Q-270-7 (`AUDIENCE:` label rename in `who_you_help` prompt) | Untouched. |
| OPEN | Q-270-2 (§5 Task Hard-Constraint seam ownership) | Effectively resolved by v6 landing the universal invariant in §4 Writing Contract; the §5 seam is now for per-render directives ON TOP of the invariant. Consider closing at SESSION 272 open. |

---

## §F. WRITING CONTRACT V6 ARCHITECTURE (quick reference)

Location: `shell/character_os/writing_contract.py`.

```
_solo_scene_contract insert order:
  SHAPE
  LENGTH
  INVARIANTS  (SESSION 269 §15 scene-physics)
  AUDIENCE-AWARE COMMUNICATION  ← SESSION 271 §187 v6 addition (universal, character-agnostic)
  NARRATIVE SHAPES
  CTA POLICY
  ANTI_SELF_DESCRIPTION
  ANTI_GENERIC_REGISTER
```

The invariant is a module-level constant `_AUDIENCE_AWARE_COMMUNICATION_BLOCK`. Every wording change is a v6→v7 bump — deliberate slice, fresh fox-first re-test, snapshot updates.

`standalone` / `long_form` / `dialogue_scene` contract text remains **byte-stable** across the 5→6 bump. Only `_solo_scene_contract` changed.

---

## §G. `Composition.audience_hint` OWNERSHIP + LIFECYCLE

**Location:** `shell/apps/compositions/models.py`. Field: `audience_hint = TextField(blank=True, default="")`. Immutable-after-first-write via `_IMMUTABLE_OBSERVABILITY_FIELDS` (SESSION 262 provenance guard).

**Lifecycle:**

- **Write path:** `POST /api/compositions/` body top-level key. `views.CompositionRecipeViewSet.create` reads → strips → `inspect.signature` gate injects into starter kwargs only when the starter's signature accepts it. Currently only `talking_head` accepts. Blank / whitespace-only silently drops.
- **Starter path:** `talking_head` coerces (strip), persists on `Composition.objects.create(audience_hint=…)`, then `if composition.audience_hint:` copies to `step.params["audience_hint"]`.
- **Runtime path:** `_resolve_solo_audience_hint(step)` reads `step.params["audience_hint"]` first (SESSION 270 precedence: `step.params > settings > env`). If empty everywhere, returns `None`; synthesis then relies on the v6 universal invariant's baseline (which reads `Teammate.who_you_help` from §1 AUDIENCE).
- **Immutability:** first write on the empty-string default is always accepted; subsequent divergent writes raise `ValidationError`. No-op saves of the same value pass.
- **Rerender semantics:** a rerender creates a new Composition row with its own `audience_hint` field; the immutable guard prevents any mutation on the original.

**SPA UI:** *not shipped in §187.* The write path is API-only until a future slice adds a form field. The `audience_hint` is exposed on `CompositionSerializer` for GET responses (observability).

**Other solo_scene starters** (`talking_head_with_backdrop`, `talking_head_polished`): do NOT yet accept `audience_hint`. Adding them is a future bounded slice — behavior falls back to the v6 universal invariant + `Teammate.who_you_help` fallback until then.

---

## §H. EXPERIMENTAL PLUMBING STATUS

| Machinery | Status | Location | Recommendation |
| --- | --- | --- | --- |
| `_SOLO_AUDIENCE_HINT_ENV` / `_SOLO_AUDIENCE_HINT_SETTING` + `_resolve_solo_audience_hint` | **Kept.** Load-bearing infrastructure for `Composition.audience_hint` runtime plumbing. | `apps/compositions/primitives/avatar_speech.py` | Retain. The step.params leg now carries production traffic; the settings + env legs remain safety nets. |
| `audience_hint` kwarg on `build_render_brief`, `synthesize_with_duration_gate`, `_assemble_task_message` | **Kept.** Load-bearing runtime plumbing. | `character_os/script_synthesis.py`, `character_os/duration_contract.py` | Retain. Now driven by the canonical `Composition.audience_hint` chain. |
| `communication_policy_hint` (E-KNOWLEDGE-1 experimental kwarg) | **Kept transitional.** Not wired to `Composition`. Not used in production traffic. Still referenced by `test_session271_patch_communication_policy.py` (26 tests). | `apps/compositions/primitives/avatar_speech.py` + adjacent | The v6 universal invariant now supersedes the *purpose* this experiment served. A cleanup slice can remove the kwarg + suite once §191.10 verdict B is comfortable in production. Not urgent. |
| `previous_draft` (Q-270-15c corrective-revision experiment) | **Kept transitional.** | `character_os/script_synthesis.py` | Related to the Q-270-15c open question. Do not remove until knowledge-shape + corrective-hint interaction is resolved. |

---

## §I. NARRATIVE MEMORY STATE

| Metric | Value |
| --- | --- |
| Total memories in Patch' Workshop Universe | **17** |
| Newest memory | `36c21641-1495-4236-8632-86aa774e5e7b` (created 2026-08-19T20:06:08 UTC, source `ba431203-…`) |
| Memories created during entire SESSION 271 (2026-08-19 23:23 → 2026-08-20 close) | **0** |
| Memory retrieved by canonical v6 render `994e7b1b` | `8d4fdfec-add4-4505-8ade-b0f9e6d8aea6` — "Patch found the old workshop-agent project and notes" (created 2026-08-19T14:04:59, pre-SESSION 271) |
| Promotion discipline (SESSION 269 §16.8) | Held. Zero promotions in SESSION 271. |

Do not promote NarrativeMemory in the SESSION 272 opener unless a bounded durable outcome mechanically requires it.

---

## §J. RELEVANT COMPOSITION IDs (SESSION 271 sequence)

Frozen sidecars in `docs/design/session_271_experiment_data/`.

| Trial | Full UUID | Slice / Purpose | Sidecar |
| --- | --- | --- | --- |
| 1 (invalid — activation gap) | `25467733-…` | Q-270-15c Trial 1 | `01_composition_25467733_q270_15c_trial1_evidence.json` |
| 2 (valid) | `1ff3d16f-a428-4bcb-8413-f3ad91290724` | Q-270-15c Trial 2 | `02_composition_1ff3d16f_q270_15c_trial2_evidence.json` |
| 3 (invalid — activation gap) | `8b61ca92-1642-49b7-9f68-4d6786e331bc` | Q-270-15c Trial 3 | `03_composition_8b61ca92_q270_15c_trial3_evidence.json` |
| 4 (valid E-K1) | `774658ea-2f2c-4b15-b330-c1c4ada221d7` | E-KNOWLEDGE-1 Trial 4 (Patch/AI-Agents) | `04_composition_774658ea_e_knowledge_1_trial4_evidence.json` |
| 5 (invalid — activation gap) | `62d68b17-261c-45fb-978c-06bef966715f` | E-K1 Trial 5 attempt | `05_composition_62d68b17_e_knowledge_1_trial5_evidence.json` |
| 6 (valid E-K1) | `abafba24-c44c-4aa9-8a9a-9de1a6286b2f` | E-K1 Trial 6 (Patch/image-gen; media dispatch failed orthogonally, synthesis fully succeeded) | `06_composition_abafba24_e_knowledge_1_trial6_evidence.json` |
| **7 (canonical v6 verification)** | **`994e7b1b-e95a-4b9b-b17e-1b25611fcd8e`** | **§191 v6 verdict specimen** | **`07_composition_994e7b1b_v6_verification_evidence.json`** |
| Historical control | `c3ff972d-a7a0-4882-960a-60084485cc02` | SESSION 270 Q-270-13 same-topic nontechnical-adult canonical | (SESSION 270 sidecars) |
| Historical control | `2ef5ee7e-7a55-4083-a587-1b5799bbaa47` | SESSION 269 baseline | `docs/design/session_269_experiment_data/…` |

---

## §K. ACTIVATION-GAP LESSONS (do not re-learn)

- **Only Claude-inline env-var activation reliably injects experiment flags into a running Celery worker.** Handing an env-var + restart instruction to Chris across a session boundary fails ~60% of the time (Trials 1, 3, 5).
- **After every restart, `ps eww <pid>` verify env vars.** Do not trust `.env` layering to reach worker child processes.
- **`Composition.audience_hint` completely obviates this class of failure for audience information.** The persistable field IS the activation. This is one of v6's structural wins.

---

## §L. CANONICAL RUNTIME STATE (at SESSION 271 close)

- **Django** (`:8010`): running, `/admin/` returns 302.
- **Media-engine** (`:8001`): running, `/health` returns `{status:ok, all mocks false, llm_provider:openai, llm_model:gpt-4o-mini}`.
- **Vite** (`:5174`): running, `/` returns 200.
- **Celery**: 1 node, 3 processes, `inspect ping` → `pong`.
- **Experiment env vars**: none set (verified via `ps eww` on live worker PIDs post-restart).
- **Postgres + Redis (docker-compose)**: up.
- **Repository**: `main == origin/main`; working tree clean.

---

## §M. EXPLICIT NON-DECISIONS (SESSION 271 did NOT settle these)

- **SPA UI for `audience_hint`.** Not shipped. Currently API-only. A future slice can add a form field on the composition-create surface, guided by the F0 rule 7 discipline recorded in memory (`feedback_navrail_gated_by_f0_rule_7`).
- **`audience_hint` on other solo_scene starters** (`talking_head_with_backdrop`, `talking_head_polished`). Not added. Behavior falls back to v6 universal invariant + `who_you_help` fallback.
- **`audience_hint` on `dialogue_scene`.** Not added. Q-270-6 remains open.
- **Cleanup of E-KNOWLEDGE-1 experimental machinery** (`communication_policy_hint`). Kept transitional. See §H.
- **Q-270-15c corrective-revision experiment resolution.** Kept transitional. Its causal role in residual jargon is now understood (§191.9 rank 2), but the mechanism belongs to the knowledge-shape research question (§D).
- **Knowledge-document rewrite.** Explicitly not touched. The knowledge-shape question is SESSION 272's opener — do it in a bounded audit + design slice first.
- **NarrativeMemory promotion.** Zero promotions in SESSION 271.

---

## §N. REMINDERS FOR SESSION 272

- **Design for arbitrary future characters, not just Patch/Rivet.** Every architectural decision made in SESSION 271 was validated against the fox-first thought experiment (fox baker / bear coffee-shop / expert-technical / child-facing) and passed. Continue the discipline. If a proposed knowledge-authoring convention only "works" because Patch has a certain persona shape or a certain knowledge doc structure, it fails the fox-first test and needs redesign.
- **Patch has researched AI Agents enough.** Five behaviorally-equivalent same-topic renders (994e7b1b, 774658ea, c3ff972d, 1ff3d16f, 8b61ca92) have saturated the substrate. Future story dogfood should let Patch **actually begin the agent experiment** — his own scripts have been repeatedly asking to. 😂 Suggested candidate Episode: *"Patch gives the workshop agent one small job to see what it actually does."* (or Chris's alternative wording).
- **Do not require another same-topic Patch render to answer any remaining architectural question.** If a SESSION 272 render is needed, use a DIFFERENT substrate — either a different Episode, a different topic, or a different character altogether. The fox-first discipline extends to substrate variety.
- **Do not commit a knowledge rewrite in the first SESSION 272 slice.** Start with audit + design.

---

## §O. RECOMMENDED SESSION 272 START

Single question:

> **KNOWLEDGE AUTHORING / KNOWLEDGE SHAPE** — *How should Character OS factual knowledge represent technically precise concepts while also giving synthesis accessible semantic formulations, without duplicating facts, dumbing down expert knowledge, or baking audience-specific prose into retrieval documents?*

**Start with audit, not implementation.** Suggested first-slice steps:

1. Read three Character OS knowledge documents (Patch, Rivet, at least one other if available) and characterize how each represents technical concepts — dense enumeration vs prose vs mixed.
2. Cross-reference SESSION 271 §191.9 causal ranking against the actual shape of the load-bearing chunk (`505acbba` in Patch's doc). Confirm the "dense-enumeration → raw-terminology-gravity" hypothesis on a second character's substrate.
3. Sketch 2–3 candidate authoring conventions (e.g. "technical enumeration MUST be paired with a plain-language reformulation in the same paragraph"; or "dedicated `# TERMS` glossary block per chunk that synthesis explicitly can-but-need-not draw from"; or others).
4. Fox-first each candidate.
5. Return a design recommendation. Do NOT rewrite Patch's doc in the first slice.

---

**End of SESSION 272 handoff. SESSION 271 CLOSED. Audience-architecture for `solo_scene` RATIFIED (v6). Next question: KNOWLEDGE AUTHORING / KNOWLEDGE SHAPE — audit first, no render, no rewrite in the first slice.**
