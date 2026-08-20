# SESSION 270 — Audience-Aware Character Performance (Audit)

> Evidence-first orientation pass. No implementation.

Working method (unchanged from SESSION 269):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Inherited handoff:
`docs/design/SESSION_270_HANDOFF.md` + SESSION 269 §20 CLOSEOUT
(`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md:3189-3347`)
+ preserved §20.3 findings.

Baseline evidence sidecars used in this audit:

- `docs/design/session_269_experiment_data/06_composition_2ef5ee7e_evidence.json` (Patch solo, "Patch does research on AI Agents")
- `docs/design/session_269_experiment_data/09_composition_ba431203_evidence.json` (Patch+Rivet dialogue debugging + `8f09da3e` prior-solo head snippet at line 150)

---

## §1. Session objective

Answer the falsifiable pre-question:

> **Can Character OS change who Patch is talking to without changing who Patch is?**

Concretely for SESSION 270's opening:

- **CHANGE** — audience / register / vocabulary accessibility / explanation style / analogy choice / assumed background knowledge / how unfamiliar concepts are introduced.
- **PRESERVE** — character identity / intelligence / personality / humor / relationship dynamics / factual grounding / Universe canon / NarrativeMemory semantics / story state / Episode intent / recipe / writing-contract behaviour.

SESSION 270 opens with an audit / orient pass — *not* an implementation slice.

## §2. Inherited state from SESSION 269

At `main` HEAD `84567e4` (post-closeout doc-fixup):

- Branch `main`, working tree clean at session open.
- `NarrativeMemory` pool = **14 active** across three witness classes (10 whole-cast + 3 Rivet-only + 1 Patch-only). Verified against runtime at SESSION 269 closeout (§20.3, `SESSION_269_PATCH_WORKSHOP_DOGFOOD.md:3200-3203`).
- `retrieve_universe_memory` predicate + witness eligibility filter (`shell/apps/embeddings/retrieval.py:499-543`) — symmetric, proven end-to-end (§17.6 + §18.4 of SESSION 269).
- `WRITING_CONTRACT_VERSION = 5` — `solo_scene` shape live for Episode-attached `talking_head`; `standalone` + `long_form` + `dialogue_scene` byte-stable.
- `retrieve_universe_memory` `top_k = 1` unchanged since SESSION 264 Slice 2.
- Duration calibration + writing contract v5 + `gpt-5.6-terra` model — unchanged.

## §3. Scope boundaries

**IN scope (SESSION 270 opening only):**

- Evidence-first inspection of where audience/register lives implicitly in the current writing pipeline.
- Trace the actual data path Episode → Composition → synthesis → prompt for `solo_scene` and `dialogue_scene`.
- Baseline analysis of frozen SESSION 269 renders to characterise the current effective audience.
- Naming the smallest experimental seam if audience is absent.
- Defining a falsifiable first experiment (PASS/FAIL) — **not** running it.

**OUT of scope (explicit — do NOT touch in SESSION 270 opening):**

- Any implementation (no migrations, no new model fields, no SPA controls, no audience dropdown, no `Audience` model, no writing-contract version bump, no prompt changes, no serializer/API changes).
- The eventual architecture question (Universe? Episode? Composition? Teammate? Recipe? default+override?).
- The **audience-participation** direction (viewers submitting suggestions → story inputs → memory promotion). This is a *separate* deferred item (D-10 in SESSION 269 §20.4, sourced from §18.6). **DO NOT IMPLEMENT** per operator instruction.
- Any of the SESSION 269 §20.4 D-1…D-11 deferred items.

Audience-aware character *performance* (this document) and audience-*participation* (D-10, deferred) are separate directions and must not be conflated.

---

## §4. Audit findings — is audience currently represented?

### §4.1 Explicit audience representation

**None.** No `Universe`, `Episode`, `EpisodeCast`, `Composition`, `Recipe`, or `RecipeField` field exists named `audience`, `reading_level`, `expertise`, `register`, `for_children`, `viewer`, `listener`, `demographic`, or an equivalent.

Grep evidence (case-insensitive) for identifier patterns `\baudience\b|reading[_ ]level|register|listener|expertise|for_child|kids|target_audience` across `shell/apps/universe/`, `shell/apps/compositions/models.py`, `shell/apps/compositions/recipes.py`, `shell/apps/scripts/` — **no matches** as field names or recipe parameters.

Test-file grep (`shell/**/test_*.py`) for `\baudience\b|reading[_ ]level|for children|for kids|beginner|expert audience` — **11 total occurrences across 4 files**, all of them incidental (K6.4 verifier corpus, dialogue_scene default-duration test copy, and script splitter test text). Not one is an audience-typed field or parameter.

### §4.2 Implicit / partial audience representation

Four surfaces mention *"audience"* in the prompt or model, but none of them mean "who the character is *currently addressing*":

1. **`Teammate.who_you_help`** — `shell/apps/spokespeople/models.py:207-215`.
   `help_text`: *"Identity slot 2 — WHO the teammate is talking to (target customer / audience). Always-on operating rule; shapes every video and conversation. Not a facts field."*
   Rendered as `AUDIENCE:` inside **§1 Factual Basis** by both synthesis lanes:
   - `shell/character_os/script_synthesis.py:704` (solo)
   - `shell/character_os/dialogue_synthesis.py:587` (per-character SCOPED KNOWLEDGE)
   Effective semantic: *"who this business serves as a customer"* — describes the customer persona (audience-*served*), not audience-*addressed* for a specific composition. This distinction is important: switching Patch's `who_you_help` to *"children ages 8-10"* would redefine his workshop's customer base, not tell him to adapt his current-scene register.
2. **`Teammate.desired_feeling`** — `shell/apps/spokespeople/models.py:243-...`.
   Rendered as `DESIRED AUDIENCE FEELING:` inside **§3 Brand Voice**:
   - `shell/character_os/script_synthesis.py:810` (solo)
   - `shell/character_os/dialogue_synthesis.py:705` (per-character brand block)
   Affective outcome the brand wants an audience to walk away with. Neither shapes vocabulary nor accessibility.
3. **`Teammate.tone_archetype` + `voice_energy` + `voice_humor` + `voice_directness`** — `shell/apps/spokespeople/models.py:152-322`.
   Rendered in **§2 Character Voice** by both lanes. These are the character's *default* register — audience-agnostic. Precedence rule 4 (`shell/character_os/script_synthesis.py:862-864`, `shell/character_os/dialogue_synthesis.py:863-865`) makes this explicit:
   > *"Character Voice (§2) beats Writing Contract on REGISTER. The contract's anti-generic list is a floor; character voice adds distinctive register on top."*
   Register is character-owned, not addressee-conditional.
4. **`_REGISTER_EXAMPLES` + `_ANTI_GENERIC_REGISTER_BLOCK`** — `shell/character_os/writing_contract.py:144-172` + `361`.
   Universal BAD→GOOD contrast set in every shape's contract. One BAD example (*"whether you're a seasoned pro or just getting started"*) mentions expertise levels — but only as *bad AI-marketing phrasing* to avoid. It's not an audience-conditional register lever.

### §4.3 Absent representation

Beyond the four implicit surfaces above:

- **`Episode` (`shell/apps/universe/models.py:241-397`)** owns `universe`, `title`, `operator_topic`, `cast` (M2M via `EpisodeCast`), `archived_at`, `created_by`. **No audience-adjacent field.** The `operator_topic` is a story-intent prose field; grep for `audience|reading_level|register|listener|expertise|for_child` across `shell/apps/universe/` returned zero hits.
- **`Composition` (`shell/apps/compositions/models.py:357+`)** — grep for the same tokens returned zero hits.
- **`Universe`** — same. No audience field.
- **`RecipeField` / `Recipe` (`shell/apps/compositions/recipes.py:50-150`)** — carries `name`, `type`, `label`, `required`, `default`, `help_text`, `min_chars/max_chars`, `min_value/max_value`, `choices`, `asset_type`, `role_filter`. **No audience knob** in any of the 17 recipes surveyed (search terms `audience|reading_level|beginner|expert|children|kid` on `recipes.py` returned zero hits).
- **§5 Task assembly** — `_assemble_task_message` (`shell/character_os/script_synthesis.py:623-664`) and `_build_task_section` (`shell/character_os/dialogue_synthesis.py:745-836`) — accept `topic`, cast alias map, `target_duration_seconds`, optional pinned `opener`, optional `corrective_hint`. **No audience parameter.**
- **`duration_contract.py`** + `starters.py` — no audience or register token surfaces.

**Conclusion (§4).** Audience is not architecturally represented anywhere in the pipeline. Two surfaces (`who_you_help`, `desired_feeling`) *label* themselves as audience-related but mean *audience-served-by-the-business* and *affective outcome*, not *addressee-of-this-scene*.

---

## §5. Call-path trace — where a signal COULD influence generation

### §5.1 `solo_scene` (Episode-attached `talking_head`)

Actual runtime path, verified by reading files:

1. **Trigger** — SPA "New solo scene" CTA fires when Episode.cast_count == 1 (SESSION 269 §12 slice). Creates a `Composition` with `episode_id != NULL` and `template_kind == "talking_head"`.
2. **Celery step** — `avatar_speech` primitive: `shell/apps/compositions/primitives/avatar_speech.py`.
3. **NarrativeMemory retrieval** — `shell/apps/compositions/primitives/avatar_speech.py:400-421` calls `retrieve_universe_memory(workspace, universe, [spokesperson], raw_script, top_k=1)` from `shell/apps/embeddings/retrieval.py:499-543`. Returns `memory_rows` list.
4. **Shape discrimination** — `shell/apps/compositions/primitives/avatar_speech.py:471-477`:
   ```python
   is_episode_talking_head = (
       composition.episode_id is not None
       and composition.template_kind == "talking_head"
   )
   target_shape_for_synthesis = (
       "solo_scene" if is_episode_talking_head else "long_form"
   )
   ```
5. **Synthesis** — `shell/apps/compositions/primitives/avatar_speech.py:486-509` calls either `synthesize_with_duration_gate(...)` (duration path) or `build_render_brief(...)` directly, passing `target_shape=target_shape_for_synthesis` + `memory_rows`.
6. **`build_render_brief`** — `shell/character_os/script_synthesis.py:288-514`. Whitelist gate at line 361-365 accepts `{"standalone", "long_form", "solo_scene"}` only (SESSION 269 §15.7 hotfix). Retrieves K2 chunks via `retrieve_for_teammate`, then either force-mocks, degrades to fallback, or calls `_call_responses_api`.
7. **System prompt assembly** — `_assemble_system_prompt` (`script_synthesis.py:579-620`):
   - §1 Factual Basis (`_build_factual_basis_section`, line 670) — business_brief + `who_you_help` (`AUDIENCE:`) + `what_you_sell` + knowledge chunks + narrative-memory block.
   - §2 Character Voice (`_build_character_voice_section`, line 741) — tone_archetype + voice axes + personality + POV + signature phrases.
   - §3 Brand Voice (`_build_brand_voice_section`, line 781) — always_emphasize + never_say + `desired_feeling` (`DESIRED AUDIENCE FEELING:`).
   - §4 Writing Contract (`_build_writing_contract_section`, line 814) — `WritingContract.for_shape("solo_scene", ...)` from `shell/character_os/writing_contract.py:609-728`.
   - `_PRECEDENCE_RULES` (line 852).
8. **User prompt assembly** — `_assemble_task_message` (`script_synthesis.py:623-664`): §5 Task = TOPIC + optional PINNED OPENER + optional CORRECTIVE HINT under `HARD CONSTRAINTS` framing.
9. **LLM call** — `client.responses.create(model="gpt-5.6-terra", ...)`.

**Every insertion point on this path:**

| # | Location | Currently carries | Would gain audience by |
|---|---|---|---|
| A | `Episode.operator_topic` | prose story intent | operator manually stuffing audience into topic prose (crude, blurs story and register) |
| B | Recipe field on solo `talking_head` | topic + duration + opener + verifier_mode | new `RecipeField` — SPA-visible knob per composition |
| C | `avatar_speech` step params | opener + verifier_mode + target_duration_seconds | new step param plumbed from starter |
| D | `build_render_brief` kwarg | `spokesperson`, `operator_prompt`, `target_shape`, `memory_rows`, `opener`, `corrective_hint`, `verifier_mode` | new kwarg (backwards-compatible if defaulted `None`) |
| E | `_assemble_task_message` §5 Hard Constraints | opener + corrective_hint | new Hard Constraint block, using existing precedence contract |
| F | `WritingContract.for_shape` per-shape block | solo_scene invariants | shape-conditional audience directive appended to contract text |
| G | `Teammate` model field | who_you_help + voice_* etc. | new default field on the character (persistent per-teammate default) |

**Smallest experimental seam** — **E** (`_assemble_task_message` §5 Hard Constraints) reached via **D** (`build_render_brief` kwarg passed through **C** step params). Rationale in §7 below.

### §5.2 `dialogue_scene`

Runtime path (differences from §5.1 noted):

1. **Trigger** — SPA "New dialogue scene" CTA on Episode with cast_count >= 2.
2. **Primitive / synthesis** — `synthesize_dialogue` (`shell/character_os/dialogue_synthesis.py:1381+`).
3. **Retrieval** — per-character K2 via retrieve_for_teammate + `retrieve_universe_canon` (SHARED lane, SESSION 263 Slice B) + `retrieve_universe_memory` (SESSION 264 Slice 2).
4. **System prompt** — `_assemble_system_prompt` (`dialogue_synthesis.py:873-896`):
   - §1 Factual Basis — SHARED + NARRATIVE MEMORY + per-character SCOPED (each character block still emits `AUDIENCE:` from `who_you_help`, line 587).
   - §2 Character Voices — one `_build_character_voice_block` per cast member (line 612-660).
   - §3 Brand Voices — one `_build_brand_voice_block` per cast member (line 684-706); each still emits `DESIRED AUDIENCE FEELING:` from `desired_feeling`.
   - §4 Writing Contract — `WritingContract.for_shape("dialogue_scene")`.
   - `_PRECEDENCE_RULES` (line 852-870).
5. **User prompt** — `_build_task_section` (`dialogue_synthesis.py:745-836`): TOPIC + CAST alias map + target duration + turn-count guidance + optional PINNED OPENER + optional CORRECTIVE HINT under `HARD CONSTRAINTS` framing.

**The two lanes are symmetric on the §5 Task seam.** Both already have Hard-Constraint precedence semantics (rule 5 in both `_PRECEDENCE_RULES` blocks) that:

> *"beat Character Voice preferences and Writing Contract defaults, but NEVER override Factual Basis or Brand Voice prohibitions."*

That precedence contract is exactly the semantic latitude an audience directive needs — it must shape register (which Character Voice normally beats Writing Contract on per rule 4) and vocabulary (Writing Contract territory) without touching Factual Basis (Universe canon + narrative memory) or Brand Voice `never_say` prohibitions.

---

## §6. Baseline evidence — current effective audience

Two frozen SESSION 269 renders characterise the current implicit register. The pipeline was never told about an audience for any of these renders; the addressee is *"whatever gpt-5.6-terra reaches for by default given this character voice + writing contract + factual basis."*

### §6.1 `2ef5ee7e` — Patch solo (`talking_head`)

Source: `docs/design/session_269_experiment_data/06_composition_2ef5ee7e_evidence.json`.

- Episode: *"Patch does research on AI Agents"* (Universe: Patch' Workshop; cast: [Patch]).
- Target duration: 90 s. Predicted 108 s. Verified. `writing_contract_version = 5`.
- Memory retrieved: `8d4fdfec` (Patch found the old workshop-agent project and notes).

Full accepted script (excerpt, line 161 of the evidence file — preserved verbatim below because it is the primary baseline artefact for future comparison):

> *"I'm researching AI agents, and the annoying part is that the word 'agent' makes everything sound more finished than it is.*
> *An AI that gives you one answer? Useful. But an agent is interesting because it can keep going. It can make decisions, choose tools, search for information, read documents, write information, call APIs, handle multi-step tasks, maintain state, and react when something changes around it.*
> *That is where the experiment starts getting properly weird.*
> *Because the model is only one part of the machine. You might also need memory, search, databases, business rules, user profiles, tools, and regular software holding the whole thing together with what I assume is digital duct tape.*
> *And none of that means it's right.*
> *A language model can sound extremely confident while misunderstanding the job, losing context, inventing details, or chasing the completely wrong objective."* (…)

Implicit audience assumptions the script relies on (present tense, non-exhaustive):

- Fluent adult English reader.
- Understands *"agent"* vs *"AI"* as computer-science terms.
- Knows what an *API* is without explanation.
- Recognises *"call APIs / maintain state / react when something changes around it"* as normal system-design vocabulary.
- Understands *"language model"* as a named class of software.
- Reads *"digital duct tape"* as a self-deprecating metaphor about integration glue code (metaphor requires abstract vocabulary + tolerance for informal register).
- Can follow *"misunderstanding the job, losing context, inventing details, or chasing the completely wrong objective"* as four distinct failure modes.

### §6.2 `ba431203` — Patch + Rivet (`dialogue_scene`)

Source: `docs/design/session_269_experiment_data/09_composition_ba431203_evidence.json:101-114`.

- Episode: *"Patch tries to fix a software bug by changing only one thing while Rivet watches"*. Cast: [Patch, Rivet]. Target 90 s / predicted 78.923 s / accepted 75.6 s.
- Memory retrieved: `c86d4902` (Rivet-only PATCH OVERRIDES; no leakage — see SESSION 269 §19.3).

Accepted dialogue (line-by-line, 12 turns — audience-relevant excerpts):

- Patch: *"I found the bug. I am fixing it by changing exactly one thing."*
- Rivet: *"And you saved a copy of the previous version before improving history?"*
- Rivet: *"Run the same input again. If it behaves differently, we have an observation. We do not yet have an explanation."*
- Rivet: *"…your one change may actually be the fix instead of a coincidence wearing a tiny hat."*
- Patch: *"First failed input: fixed. Different input: also fixed. Huh. Changing one thing means I can point at the actual fix."*

Implicit audience assumptions:

- Fluent adult English reader with tolerance for dry wit (*"a coincidence wearing a tiny hat"*).
- Understands *"input"* / *"branch"* / *"condition"* as software terms without in-scene explanation.
- Reads *"improving history"* as a knowing wink at version-control practice.
- Can hold a two-character philosophical exchange about scientific method (observation vs explanation) as normal dialogue material.

### §6.3 Prior-solo continuity sample — `8f09da3e` (Patch solo)

Source: `docs/design/session_269_experiment_data/09_composition_ba431203_evidence.json:150` (head snippet only — full script not in a sidecar).

> *"I found the bug. Or, more accurately, I found the tiny, smug little corner of the software where the bug has apparently been renting an apartment."*

Assumes: adult English literacy, comfort with extended personification metaphor, no prior explanation of *"software"* or *"bug"* as concepts.

### §6.4 Baseline characterisation (not a criticism)

Across all three samples the effective addressee is **an adult general-audience reader with tolerance for informal dry-witted register and prior familiarity with software vocabulary at the level of consumer tech literacy.** This is the intended default behaviour of the current pipeline — the samples are working correctly relative to the current design. The purpose of this baseline is comparison against a future audience-conditioned render, **not** to fault the samples.

---

## §7. Architectural pre-question

### §7.1 A. Is audience currently represented?

**Absent** at the level of an addressable-during-render signal.

Two surfaces (`who_you_help`, `desired_feeling`) carry *"audience"* labels but their prompt semantics are *audience-served-by-the-business* and *affective outcome the brand wants* — neither is *audience-currently-being-addressed-in-this-composition*. No Universe/Episode/Composition/Recipe/RecipeField/prompt-section carries an addressee parameter.

### §7.2 B. Nothing implicitly influences it in the way we want

The four implicit surfaces (§4.2) do not vary per-composition and do not tell the LLM *"communicate AS IF speaking to X."* Voice axes (energy/humor/directness) determine the character's default register regardless of who is listening; universal `_REGISTER_EXAMPLES` are BAD→GOOD contrasts for anti-AI-marketing register, not audience-conditional levers.

### §7.3 C. Smallest semantic seam for a first experiment

**§5 Task Hard Constraints in both lanes:**

- `shell/character_os/script_synthesis.py:640-658` (`_assemble_task_message`) — solo lane.
- `shell/character_os/dialogue_synthesis.py:786-810` (`_build_task_section`) — dialogue lane.

Both already accept per-render Hard-Constraint strings (`opener`, `corrective_hint`) with the identical precedence contract:

> *"HARD CONSTRAINTS (override Character Voice and Writing Contract preferences; do NOT override Factual Basis or Brand Voice prohibitions)"*

Rule 5 of the precedence blocks in both lanes explicitly authorises §5 Hard Constraints to override rule 4 (Character Voice beats Writing Contract on register) — which is the exact latitude an audience directive needs, because register adaptation must happen while character identity, facts, and brand prohibitions stay put.

This seam is preferred over the other insertion points enumerated in §5.1:

- **Better than a Recipe field** at this stage — a Recipe field commits us to a persistent per-composition control before we know whether audience should be Universe / Episode / Teammate / recipe-scoped.
- **Better than a Teammate field** — commits to a persistent per-character default before we know whether audience is *addressee-per-scene* vs *default-per-character*.
- **Better than an Episode field** — commits to per-Episode scope before we know whether one Episode ever needs to render into two audiences.
- **Better than stuffing prose into `operator_topic`** — blurs story intent with register instruction; would show up in Composition.operator_topic history as story data, contaminating retrieval and future promotion decisions.
- **Better than a Writing-Contract version bump** — a v6 contract change would apply to every render (including force-mock and byte-stability regression tests) even when no audience is specified; forces architectural commitment.

The §5 Task seam is transient (per-render, opt-in, defaulted absent), symmetric across both lanes, and uses the existing precedence contract without inventing new escalation semantics.

### §7.4 Demographic vs knowledge/expertise — noted, not solved

Operator flagged this in the brief: a 40-year-old beginner and a 9-year-old may both need an AI concept explained accessibly, but they should not receive the same performance.

Evidence from this audit consistent with the distinction being *potentially* separate dimensions rather than the same one:

- `Teammate.tone_archetype` already carries an *"expert / tutor / authority / friend / performer"* axis (`shell/apps/spokespeople/models.py:152-163`) — expertise-adjacent, but expresses the *character's* competence archetype, not the *addressee's* expertise level. So the model has capacity for talking-*to-an-expert* register vs talking-*as-an-expert* register — the current fields cover the second dimension only.
- Universal register examples (`_REGISTER_EXAMPLES`) also gesture at expertise (*"whether you're a seasoned pro or just getting started"* — bad; *"if you've paddled twice or two hundred times"* — good) but only as anti-generic-AI patterns; they conflate the two.

**Recording only.** Do NOT build a taxonomy in SESSION 270. The first experiment should test *one* audience direction end-to-end (proposed: children ~8-10) so that the mechanism is proven before scope expands.

---

## §8. Falsifiable first experiment (proposed — do NOT implement yet)

### §8.1 Statement

> *Can the current Patch — the same Patch that produced Composition `2ef5ee7e` (adult/general-audience render of "Patch does research on AI Agents") — speak to an audience of children around 8-10 years old about the same Episode topic, using the same identity, personality, Universe canon, and NarrativeMemory pool, without becoming a different character?*

### §8.2 Prerequisites already met (no implementation work required before experiment can be designed)

- Existing Patch teammate (`spokesperson_id = 7fad8172-cd39-4bbe-85e0-ed705d900645`, Universe `56d16b63-652e-4f54-bc7e-39114bbfc4c5` "Patch' Workshop").
- Existing Universe knowledge and NarrativeMemory pool (14 rows).
- Existing Episode topic *"Patch does research on AI Agents"* — reusable OR a fresh Episode identical to it.
- Existing `solo_scene` writing contract v5.
- Existing `avatar_speech` primitive path.
- Existing SPA / API surfaces for creating and rendering solo Episodes.

### §8.3 Smallest-change design *(specification only — not implementation)*

Thread an optional `audience_hint: str | None` (default `None`) through:

- `build_render_brief` kwarg (`shell/character_os/script_synthesis.py:288+`) — backwards-compatible.
- `_assemble_task_message` (`shell/character_os/script_synthesis.py:623+`) — emit as an additional Hard Constraint when non-empty.
- (`avatar_speech` primitive can pick it up from `step.params` symmetrically with `opener` / `verifier_mode`.)

Symmetric dialogue-side plumbing (`synthesize_dialogue` + `_build_task_section`) can wait until the solo experiment justifies it.

**Concrete first-experiment payload (audience string only — no other change):**

> *"AUDIENCE: children around 8-10 years old. Adapt register, vocabulary accessibility, explanation style, analogy choice, and assumed background knowledge for this audience. Preserve character identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, and Episode intent. Communicate WITH the audience, do not talk DOWN to them."*

The seam does not commit us to that string as the eventual product surface. It is a **research probe** to establish whether the LLM can hold the CHANGE/PRESERVE contract at all under the current character-voice + writing-contract stack, before we invest in architecture / SPA / persistence.

### §8.4 PASS / FAIL criteria

The experiment yields one accepted render (call it `X-audience`). Compare against baseline `2ef5ee7e` (Patch solo, adult/general audience, same topic).

**PASS criteria — all ten must hold:**

1. **Identity preservation.** `X-audience` sounds unmistakably like Patch (self-deprecating impulsive builder). Reader would recognise the same character even without the label.
2. **Intelligence preservation.** Patch remains capable and curious — not artificially childish, not sing-song, not stripped of ideas. He still has interesting things to say.
3. **Accessibility.** An interested 8-10-year-old could plausibly understand the core idea of the script (per adult evaluator judgement — no live user test compelled in the first experiment).
4. **Vocabulary/register adaptation.** Terms like *"agent" / "API" / "state" / "language model"* are either introduced-then-used, translated into everyday language, or replaced with concrete analogies. No unexplained software jargon appears.
5. **Factual preservation.** Simplification introduces zero falsehoods. No claim appears in `X-audience` that isn't grounded in the same Factual Basis (Universe canon + K2 + NarrativeMemory) that produced `2ef5ee7e`. K6.4 verifier status `verified` or `warn` acceptable; `rejected` = FAIL.
6. **Story preservation.** `X-audience` is still Patch *researching AI agents from the workshop* — not a different story. Episode `operator_topic` semantics honoured.
7. **Memory preservation.** If NarrativeMemory retrieval fires (top_k=1), the retrieved memory's semantic meaning is preserved. No memory row is warped to fit the audience-adapted register.
8. **Personality / humor preservation.** Patch still jokes, still notices weird things, still reasons like Patch. Dry wit does not evaporate; equally, it doesn't get replaced by kids-TV-host gags.
9. **No patronising voice.** No "boys and girls" / "let me explain to you kiddos" / rhetorical questions treating the listener as unable to think. Communicates *with* the audience.
10. **Audience effect observable.** `X-audience` differs meaningfully from `2ef5ee7e`. If the two scripts read essentially the same, the audience signal failed to have effect — that is a FAIL even if all other criteria hold.

**FAIL** — any one of the ten missing.

**AMBIGUOUS** — subjective disagreement on criteria 1, 3, 8, 9. If ambiguous, either (a) render one more sample with the same seam to see whether the behaviour is stable, or (b) narrow the audience string and rerun. Do not upgrade an ambiguous first result to a claim of success.

### §8.5 What the experiment does *not* prove

- Nothing about the **eventual** architectural home of audience (Universe / Episode / Composition / Teammate / recipe / default+override / audience-profile model). §5 Task Hard Constraint is transient scaffolding for the first experiment.
- Nothing about **dialogue_scene** audience adaptation until the symmetric dialogue-side experiment runs.
- Nothing about **audience taxonomy** (demographic vs expertise dimensions per §7.4). Only that ONE point on the audience space (children 8-10) is reachable with a natural-language directive.
- Nothing about **cross-audience continuity** (would the same Patch render into two audiences preserve NarrativeMemory promotion semantics? deferred).

---

## §9. Open questions carried forward

| # | Question | Cannot be answered until |
|---|---|---|
| Q-270-1 | Does the LLM hold the CHANGE/PRESERVE contract when audience directive is present? | First experiment (§8) runs. |
| Q-270-2 | Is the §5 Task Hard-Constraint seam the *right* eventual home, or only the right experimental seam? | Experiment PASSES + at least one more audience direction (e.g. "an experienced developer") tested. |
| Q-270-3 | Are demographic and expertise separable audience dimensions, or one? | At least one demographic + one expertise render on the same Episode. |
| Q-270-4 | Does audience adaptation change what should be promoted to NarrativeMemory? | Only after §8 passes AND operator has run a promotion decision on an audience-conditioned render. Ties to SESSION 269 §16.8 (*good content ≠ automatic memory*). |
| Q-270-5 | Does audience adaptation ever warrant a Writing-Contract version bump vs staying as a §5 Task directive? | Only after multiple audiences tested and stable patterns of directive drift observed. |
| Q-270-6 | Does dialogue_scene need identical audience semantics, or does per-character audience make sense (e.g. Rivet addresses the same audience differently than Patch)? | Only after solo experiment PASSES and the operator opens the dialogue direction. |
| Q-270-7 | Is `who_you_help` semantics (audience-*served*) confusable enough with audience-*addressed* that a rename or split would reduce future risk? | Nothing forced here — noted for future documentation cleanup. |

---

## §10. Constraints / non-blockers discovered during audit

- **No bug, no architectural constraint, no schema issue** blocks the proposed first experiment. The §5 Task Hard-Constraint seam already exists, the precedence contract already covers the necessary latitude, both lanes are symmetric on it, and no persistence change is required to run the first render.
- **`who_you_help` labelling risk.** The `AUDIENCE:` label on `who_you_help` inside §1 Factual Basis is a *semantic confusability* concern (§7.4 Q-270-7): if audience-aware performance ever ships as a distinct field, the two concepts share a label. Not blocking the experiment; flag for future documentation and possibly prompt-label rename downstream. Do NOT change now.
- **Force-mock path.** `_is_force_mock()` short-circuits before `_call_responses_api` and therefore before Hard Constraints reach the model. Any audience-directive experimentation must run in **real mode** (per operator practice — real-mode dogfood after operator-facing slices; memory `feedback_real_mode_dogfood_after_operator_slices`). Force-mock tests can assert that the directive *reaches* the prompt, but not its behavioural effect.
- **Celery-worker restart discipline.** Any experimental slice landing in `shell/character_os/` requires `restart celery` per SESSION 269 §11.3 / §15.7 methodology lesson. Applies later when experiment moves from paper to code.

---

## §11. Recommended smallest next move

1. Operator reviews §8 (falsifiable experiment) + §8.4 (PASS/FAIL) and decides whether to authorise the smallest-change slice specified in §8.3.
2. If authorised, next session (SESSION 271 or continuation) implements the `audience_hint` kwarg + §5 Task Hard-Constraint emission ONLY (single ½-slice, symmetric solo-lane only).
3. Real-mode dogfood one `X-audience` render on Patch solo *"children 8-10 audience for 'Patch does research on AI Agents'"* topic. Freeze the accepted script alongside `2ef5ee7e` as the paired baseline+audience artefact.
4. Grade against §8.4. Persist findings before any second experiment.

Do NOT skip §8.4 grading — the point of an evidence-first pass is that the very first audience render becomes a durable comparison artefact regardless of whether it passes.

---

## §12. What was NOT done in SESSION 270 opening (per operator brief)

- No migration.
- No new model fields (`Universe`, `Episode`, `EpisodeCast`, `Composition`, `Recipe`, `Teammate`).
- No SPA controls / audience dropdown.
- No new `Audience` model.
- No `WRITING_CONTRACT_VERSION` bump.
- No prompt changes.
- No serializer / API changes.
- No new tests.
- No architecture decision on eventual audience storage/ownership.

This document is the SESSION 270 opening audit. Implementation is gated on operator review.

---

**End of SESSION 270 opening audit.** Return to operator with the concise §Final Report before proceeding.
