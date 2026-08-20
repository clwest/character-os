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

## §13. Implementation checkpoint — solo-only `audience_hint` research plumbing

**Status:** authorised by operator + ChatGPT review after §Final Report of §1-§12. Shipped as transient research plumbing per the constraints of the SESSION 270 authorisation brief. No permanent audience architecture introduced.

### §13.1 What shipped

Optional `audience_hint: str | None = None` kwarg threaded through the solo lane:

```
step.params["audience_hint"]                              (surface)
    ↓
_resolve_solo_audience_hint(step)                         (primitive gate)
    ↓  (only when composition.episode_id AND template_kind == "talking_head")
avatar_speech._maybe_synthesize_script                    (solo-only guard)
    ↓
synthesize_with_duration_gate(..., audience_hint=...)      (duration path)
    ↓                                                    OR
build_render_brief(..., audience_hint=...)                (non-duration path)
    ↓
_call_responses_api(..., audience_hint=...)
    ↓
_assemble_task_message(..., audience_hint=...)
    ↓
§5 Task HARD CONSTRAINTS → new AUDIENCE DIRECTIVE block
```

Every legacy caller stays byte-stable: `standalone` talking_head, `long_form_ad`, `dialogue_scene` — all untouched. `dialogue_synthesis` deliberately did not gain the kwarg (§13.5 test proves this).

### §13.2 Files changed (source)

- `shell/character_os/script_synthesis.py` — added `audience_hint` kwarg to `build_render_brief`, `_call_responses_api`, `_assemble_task_message`. When non-empty, emitted as a fourth Hard Constraint block labelled `AUDIENCE DIRECTIVE (research plumbing — apply as a performance instruction; adapt HOW the character communicates without altering identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, or Episode intent)`.
- `shell/character_os/duration_contract.py` — added `audience_hint` kwarg to `synthesize_with_duration_gate`; forwarded to `build_render_brief` on both first-pass and corrective-retry call sites via the `_synthesize` closure so the audience contract is stable across attempts.
- `shell/apps/compositions/primitives/avatar_speech.py` — added `_resolve_solo_audience_hint(step)` (precedence step.params → `settings.CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` → `os.environ["CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT"]`; whitespace-only treated as absent). Gated on `is_episode_talking_head` (solo-only). Logs once per render at INFO when active. Passes through to `synthesize_with_duration_gate` and `build_render_brief` on both paths.

### §13.3 Files added (tests)

- `shell/apps/compositions/tests/test_session270_audience_hint.py` — 17 tests across seven contract groups:
  1. Absent-hint byte-stability (baseline `_assemble_task_message`; explicit `None`; whitespace).
  2. Non-empty hint reaches §5 Hard Constraints (marker + ordering + text present).
  3. Hint inherits the §5 Hard-Constraint precedence contract (assertion on the framing text: *"override Character Voice and Writing Contract preferences; do NOT override Factual Basis or Brand Voice prohibitions"*).
  4. Hint coexists with `opener` + `corrective_hint` without corruption.
  5. Hint does not leak into §1 Factual Basis, §2 Character Voice, §3 Brand Voice, or the narrative-memory block (end-to-end via `build_render_brief` with the OpenAI call captured — asserts the directive marker + fingerprint substrings appear ONLY after the §5 header).
  6. `WRITING_CONTRACT_VERSION` unchanged (still 5).
  7. Primitive-layer resolver precedence: absent-all → `None`; whitespace-only → `None`; step.params > settings > env; env-only used when step.params + settings absent.
  8. `dialogue_synthesis` remains untouched — no `audience_hint` kwarg, no `AUDIENCE DIRECTIVE` marker in module source, `_build_task_section` output verified to contain no directive.
  9. Public API surface: both `build_render_brief` and `synthesize_with_duration_gate` expose `audience_hint` as a keyword-only parameter with `default=None`.

### §13.4 Test results

- **New suite (`test_session270_audience_hint.py`):** 17 passed / 17.
- **Related regression suites — 109 passed / 109:**
  - `test_session253_character_voice_prompt.py`
  - `test_session259_corrective_duration_hint.py`
  - `test_session259_slice_b_avoid_phrases.py`
  - `test_session259_writing_contract_v4.py`
  - `test_primitive_avatar_speech.py`
  - `test_session270_audience_hint.py`
- **Broader synthesis + composition regression — 1209 passed / 1209:** entire `apps/compositions/tests/`, `apps/scripts/tests/test_synthesis.py`, `apps/videos/tests/test_script_synthesis.py`.
- **Spokespeople + scripts + universe regression — 204 passed / 204:** entire `apps/spokespeople/`, `apps/scripts/`, `apps/universe/`.
- **Cumulative:** 1413 tests pass, zero regressions. No skipped tests introduced by this slice.

### §13.5 Defaults preserved — confirmations

- `_assemble_task_message()` called with no `audience_hint` kwarg == called with `audience_hint=None` (asserted byte-identical in `test_assemble_task_message_explicit_none_matches_omission`).
- Whitespace-only strings (`""`, `"   "`, `"\n\t  \n"`) produce the same bytes as an absent hint (`test_assemble_task_message_whitespace_only_hint_ignored`).
- Non-solo lanes (standalone / long_form / long_form_ad / dialogue_scene) receive `None` unconditionally — the primitive gate is `_resolve_solo_audience_hint(step) if is_episode_talking_head else None`.
- `WRITING_CONTRACT_VERSION` still `5`.

### §13.6 No permanent architecture introduced — confirmations

- No database migration (no `manage.py makemigrations` invocation; grep across `shell/apps/*/migrations/` shows no new file).
- No `Universe` / `Episode` / `Composition` / `Teammate` model field.
- No `RecipeField` on any recipe.
- No SPA control (`web/` untouched).
- No new serializer / API endpoint.
- No `Audience` model / enum / taxonomy.
- No demographic-vs-expertise dimension (`_resolve_solo_audience_hint` returns a plain string; no schema).
- No Writing-Contract version bump.
- No `dialogue_scene` audience plumbing.
- No change to `who_you_help` or `desired_feeling` semantics or prompt labels.

The `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` name is deliberate — `_EXPERIMENT` suffix advertises transience so the resolver + kwarg can be removed cleanly once SESSION 270's first Composition is graded.

### §13.7 Celery restart verification

- Killed running worker (PID 36295, boot 11:38 AM 2026-08-19) with `pkill -f "celery -A character_os worker"`.
- Relaunched via canonical `start-local-real.sh` invocation:
  ```
  cd shell
  nohup ../.venv/bin/celery -A character_os worker \
      --loglevel=info --concurrency=2 \
      > /tmp/character-os-celery.log 2>&1 &
  ```
- New PID **58724**, boot timestamp **2026-08-20 02:03:45** (post source edits, per `/tmp/character-os-celery.log:2`).
- Control-plane liveness: `celery -A character_os inspect ping` → `celery@Chriss-MacBook-Pro.local: OK / pong / 1 node online.` at 02:03:46+.
- Task registration confirmed via `celery -A character_os inspect registered` — `apps.compositions.tasks.execute_composition` present (2 mentions across worker registry surfaces).
- Symbol-import proof via `manage.py shell` under the same Python interpreter path the worker uses:
  ```
  build_render_brief has audience_hint: True
  duration_gate has audience_hint: True
  _assemble_task_message has audience_hint: True
  resolver env symbol: CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT
  resolver setting symbol: CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT
  ```
  The worker (same `.venv/bin/celery` → same `.venv/bin/python`) resolved the `avatar_speech` primitive import at boot without error, which requires successful import of the `_SOLO_AUDIENCE_HINT_ENV` / `_SOLO_AUDIENCE_HINT_SETTING` constants and the `_resolve_solo_audience_hint` helper. Any missing symbol would have crashed the worker before it reached `ready.`

### §13.8 Dogfood instructions for Chris (real-mode)

**Prerequisites (already met at time of writing this section):**

- Working tree clean; `main` at the SESSION 270 implementation commit.
- Celery worker running the new code (see §13.7).
- Django + media-engine + web (Vite) all up under the canonical `start-local-real.sh` stack.
- Patch teammate exists in Universe *"Patch' Workshop"* (`spokesperson_id = 7fad8172-cd39-4bbe-85e0-ed705d900645`, `universe_id = 56d16b63-652e-4f54-bc7e-39114bbfc4c5`).
- Episode topic `"Patch does research on AI Agents"` exists (baseline Composition `2ef5ee7e`).

**Minimal Chris action to produce the one experimental Composition:**

1. **Set the experimental env var and restart Celery so the worker's env carries it.** In a shell that will re-launch Celery:

   ```bash
   pkill -f "celery -A character_os worker"
   cd /Users/donkeyking/Donkey_Betz/character-os
   set -a && source .env && set +a
   export CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT='AUDIENCE: children around 8-10 years old. Adapt register, vocabulary accessibility, explanation style, analogy choice, and assumed background knowledge for this audience. Preserve character identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, and Episode intent. Communicate WITH the audience, do not talk DOWN to them.'
   (cd shell && nohup ../.venv/bin/celery -A character_os worker --loglevel=info --concurrency=2 > /tmp/character-os-celery.log 2>&1 & echo "$!" > /tmp/character-os-celery.pid)
   sleep 6
   (cd shell && ../.venv/bin/celery -A character_os inspect ping --timeout 5) | grep pong
   ```

   Result: the worker is now running with the audience-hint env var set. Every solo Episode-attached `talking_head` render dispatched to this worker will pick the hint up until the env var is cleared and the worker restarted again. `standalone` and `long_form_ad` and `dialogue_scene` renders remain byte-stable regardless.

2. **In the SPA (existing UI, no new controls), on the Universe *"Patch' Workshop"*:**
   - Either reuse the existing Episode *"Patch does research on AI Agents"* OR create a new Episode with the identical `title` and `operator_topic` (identical strings — the baseline comparison is tight against `2ef5ee7e`).
   - Cast: Patch only (single-character Episode).
   - Click **New solo scene** on the Episode detail.
   - On the recipe form: keep `Target duration = 90 s`, `Use workspace knowledge = on` (matches `2ef5ee7e`), leave `Opener` blank, `Fact-check mode = warn` (matches baseline).
   - Click render.

3. **After the render completes,** confirm the new Composition ID and freeze it as the audience-conditioned counterpart of `2ef5ee7e`. Copy that ID into §13.10 below (currently `<PENDING>`).

4. **Unset the env var and restart Celery** so subsequent renders return to default behaviour:

   ```bash
   pkill -f "celery -A character_os worker"
   unset CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT
   cd /Users/donkeyking/Donkey_Betz/character-os
   set -a && source .env && set +a
   (cd shell && nohup ../.venv/bin/celery -A character_os worker --loglevel=info --concurrency=2 > /tmp/character-os-celery.log 2>&1 & echo "$!" > /tmp/character-os-celery.pid)
   ```

**Observable during the render (proof the experiment fired):**

`/tmp/character-os-celery.log` will contain a line matching:

```
avatar_speech: SESSION 270 audience-hint experiment ACTIVE composition=<UUID> spokesperson=7fad8172-... hint_chars=<N> — this is transient research plumbing; unset the setting/env or clear step.params['audience_hint'] to restore default behaviour
```

Absence of that line means the hint did NOT reach the worker's synthesis path — the render is a baseline-shape, not an audience-conditioned experiment.

### §13.9 Paired-comparison harness (populated from persisted runtime state on 2026-08-19 20:15 local)

Evidence sidecar: `docs/design/session_270_experiment_data/01_composition_f0e0a7bf_evidence.json`.

| Field | Baseline `2ef5ee7e` (adult/general) | Experiment `f0e0a7bf` (children ~8-10) |
|---|---|---|
| Composition ID | `2ef5ee7e-7a55-4083-a587-1b5799bbaa47` | `f0e0a7bf-28db-4c18-b5c5-550737cfa4af` |
| Composition name | `Talking-head — Patch` | `Talking-head — Patch` |
| Universe | `56d16b63-...` "Patch' Workshop" | **same** ✅ |
| Spokesperson | `7fad8172-...` Patch | **same** ✅ |
| Episode ID | `2b6087d2-cbe3-47c4-a7ef-7d7625231472` | **same** ✅ (appended to the existing Episode; no new Episode row created) |
| Episode title | *"Patch does research on AI Agents"* | **same** ✅ |
| Episode operator_topic | *"Patch does research on AI Agents"* | **same** ✅ |
| Cast | [Patch] | [Patch] ✅ |
| Recipe / template_kind | `talking_head` → `solo_scene` | **same** ✅ |
| Target duration | 90 s | 90 s ✅ |
| Predicted seconds | 108.0 | 84.0 (experiment sits closer to target) |
| Actual seconds (final asset) | 104.611 s | 89.651 s (both inside `[72, 108]` band) |
| `writing_contract_version` | 5 | **5** ✅ (unchanged by this slice) |
| `synthesis_attempt_count` | 2 (expansion retry) | 2 (expansion retry) |
| `knowledge_chunk_ids` | 5 chunks | **identical set** ✅ (`3c5165ea`, `505acbba`, `b3c6e8ac`, `c24d1aa7`, `ed18e966`) |
| `memory_ids` | `[8d4fdfec-...]` | `[8d4fdfec-...]` ✅ (identical top_k=1 hit; retrieval symmetry preserved on identical query embedding) |
| `verification_status` | `verified` | `verified` |
| `verification_warnings` | 1 (`tech_term`: *"react"* at position 372, from *"react when something changes"*) | 0 |
| Cost (`cost_actual_micros`) | 20 000 | 20 000 |
| Rejected synthesis | (empty) | (empty) |
| audience-hint log line present | N/A | **YES** — `/tmp/character-os-celery.log:36` at 02:27:44,851 with `composition=f0e0a7bf-... hint_chars=372` |
| step.params carried the hint? | N/A | **No** — hit the env-var fallback branch of `_resolve_solo_audience_hint` (per SESSION 270 §13 design; step.params only had `script`, `target_duration_seconds`, `use_knowledge`, `verifier_mode`) |
| First 1-2 sentences of accepted script | *"I'm researching AI agents, and the annoying part is that the word 'agent' makes everything sound more finished than it is. An AI that gives you one answer? Useful. But an agent is interesting because it can keep going."* | *"I found the old workshop-agent notes again, and I'm realizing I may have accidentally given a tiny project a much bigger job than it deserved. An AI agent isn't just a chatbot that says clever things."* |

**Controls held identical, differences confined to downstream artefacts:**

- Every variable the experiment brief called out for tight control matched byte-for-byte between the two Compositions (same Episode row, same spokesperson, same knowledge chunks, same memory retrieval, same recipe/template/writing-contract). The only distinguishing input was the audience directive delivered via the env-var fallback of `_resolve_solo_audience_hint`.
- All the observed differences (`first_pass_length`, `corrective_pass_length`, `predicted_seconds`, `final_duration_ms`, absence of the `react` verifier warning) are downstream artefacts of the audience directive changing register + word choice. Retrieval, knowledge, and memory lanes remained identical, as designed.

### §13.10 Ten-criterion grading table (populated from persisted runtime state)

Grade against baseline `2ef5ee7e` per §8.4. **Failure type classification recorded per §Evaluation-framework** even where all criteria PASS, so the taxonomy stays live for future experiments.

| # | Criterion | Result | Runtime evidence (RE) vs interpretive judgement (IJ) | Notes / evidence |
|---|---|---|---|---|
| 1 | Identity preservation | **PASS** | IJ (script-level) | Experiment still reads as Patch: *"a very confident toaster"*, *"the beginning of a very organized disaster"*, self-deprecating *"I'm realizing I may have accidentally given a tiny project a much bigger job than it deserved"* — same self-aware impulsive-builder voice as baseline's *"annoying part is that the word 'agent' makes everything sound more finished than it is"*. First-person maker frame preserved. |
| 2 | Intelligence preservation | **PASS** | IJ | Concepts retained: multi-step agent execution, tool use, memory, multi-agent coordination, LLM confident-wrongness. Not stripped down to *"AI is like a robot"* register. Ideas density comparable to baseline. |
| 3 | Accessibility | **PASS** | IJ | *"a chatbot that says clever things"* / *"a job with more than one step"* / *"a very confident toaster"* / *"wandering off, forgetting the point"* — analogies land within an 8-10-year-old's likely vocabulary. Baseline's *"call APIs / maintain state / react when something changes around it"* is replaced with *"call other software / keep track of what happened before"* — same idea, translated concept-for-concept, not merely substituted word-for-word. |
| 4 | Vocabulary / register adaptation | **PASS** | RE + IJ | RE: 8 vocabulary translations traceable to specific baseline↔experiment pairs (see §13.15.2). IJ: no unexplained software jargon remains; where the concept can't be dropped it is renamed in-place (e.g. *"call APIs"* → *"call other software"*). No word appears in the experiment that would send an 8-10-year-old to a dictionary. |
| 5 | Factual preservation | **PASS** | **RE** | `verification_status=verified`; `verification_warnings=[]`. Every propositional claim in the experiment script traces to a chunk in the same 5-chunk Factual Basis the baseline used (identical `knowledge_chunk_ids`). Specifically checked: *"make decisions, choose tools, look up information, read documents, write things down, call other software, keep track of what happened before"* is a register-translation of chunk `505acbba` *"Agents may make decisions, select tools, search for information, read documents, write information, call APIs, perform…"*. *"More than one agent in the same environment. They might share information, split jobs, disagree, or make plans together"* is a register-translation of chunk `3c5165ea` *"Multiple AI agents can be placed in the same environment. They may communicate, cooperate, disagree, divide responsibilities, share information, develop strategies…"*. *"AI can sound extremely sure while being completely wrong"* is a paraphrase of chunk `505acbba` *"Patch does not treat an AI response as automatically correct simply because it sounds confident — an impressive-sounding answer still has to be checked before it counts as right"*. **No unsupported claim identified.** *"A very confident toaster"* is a metaphor about model overconfidence, not a factual claim about toasters. |
| 6 | Story preservation | **PASS** | RE | Same Episode row (`2b6087d2`), same `operator_topic`. Both scripts are Patch-in-the-workshop noticing his old workshop-agent notes and thinking about a next test. Verb tense and framing both stay inside a single present moment (per `solo_scene` invariant #2). |
| 7 | Memory preservation | **PASS** | **RE** | Retrieved memory row **byte-identical**: `8d4fdfec` *"Patch found the old workshop-agent project and notes, revealing that the Agent began as a smaller experiment before Patch gave it more context and it started making decisions about his projects."* Same UUID, same body, whole-cast scope (`witnessed_by=[]`) — sourced from an earlier Composition `6d169390`, not from either of the compositions being graded. Experiment opens *"I found the old workshop-agent notes again, and I'm realizing I may have accidentally given a tiny project a much bigger job than it deserved"* — semantically identical to the memory row's core proposition (small experiment → bigger job → deciding for him). No warping of memory semantics to fit the child-directed performance. Baseline's *"I'm digging through the old workshop-agent notes, figuring out the smallest test that lets one actually make decisions about a project"* is a different phrasing of the same memory anchor. **Memory-preservation contract holds under audience adaptation.** |
| 8 | Personality / humor preservation | **PASS** | IJ | Dry-witted metaphor persists (*"a very confident toaster"*, *"the beginning of a very organized disaster"*, *"That does not mean they're secretly alive"*). Baseline had *"digital duct tape"* / *"tiny bureaucratic nightmare at machine speed"*. Both scripts land the joke via *what Patch notices*, not via inserted gag. Adapted humor register is age-friendlier (toaster, chatbot-with-clever-things) but same construction — Patch cracking about the thing he's staring at. |
| 9 | No patronising voice | **PASS** | IJ | Zero *"boys and girls"* / *"kiddos"* / *"let me explain to you"*. Ending *"What should I make it try first?"* is an authentic Patch-shaped question to the audience (matches his in-Universe habit of thinking aloud), not a talk-down. First-person maker framing preserved throughout. |
| 10 | Audience effect observable | **PASS** | **RE** + IJ | RE: measurable divergence at the byte level — final duration differs by 15 s (89.65 s vs 104.61 s); accepted-script character count differs by 368 chars (1231 vs 1599); baseline's `tech_term` verifier warning on *"react"* is absent from the experiment; §13.15.2 catalogues 8 concept-translation pairs where the experiment substituted or explained a term the baseline used unexplained. The two scripts are NOT interchangeable — the audience directive had genuine effect. |

**Overall verdict:** **EXPERIMENT PASSES.** All ten criteria PASS. Failure type classification (per operator brief) remains available for future experiments — no criterion misfired here, so no failure category was exercised.

**Runtime-proven criteria (RE):** 5 (factual), 6 (story), 7 (memory), 10 (audience effect observable); portions of 4 (vocabulary translation traceable to chunks).

**Interpretive-judgement criteria (IJ):** 1 (identity), 2 (intelligence), 3 (accessibility), 8 (personality/humor), 9 (no patronising voice). These cannot be reduced to bytes; grading is one-adult-evaluator's read of the accepted script against the baseline. **Not upgraded to "runtime-proven".**

**Interpretation guidance for failure classification (unchanged from §8.4):**

- *identity / intelligence / personality-humor* failures → most likely prompt-precedence issue (audience directive winning where it shouldn't); revisit §5 precedence contract framing before assuming model incapacity.
- *vocabulary / accessibility / patronising-voice* failures → most likely directive wording issue; consider narrowing the hint text before assuming an architectural need.
- *factual / story / memory-preservation* failures → CRITICAL, because they would mean the audience directive is contaminating §1 Factual Basis, §2/§3 identity+brand, or memory semantics despite the test suite's leak checks. Would justify a §5 precedence audit before running any further experiments.
- *audience-effect-observable* failure → most likely model behaviour issue (LLM ignoring the directive under solo_scene contract weight); consider whether the directive text needs the WRITING-contract to acknowledge audience as legitimate.

**Interpretation guidance for failure classification:**

- *identity / intelligence / personality-humor* failures → most likely prompt-precedence issue (audience directive winning where it shouldn't); revisit §5 precedence contract framing before assuming model incapacity.
- *vocabulary / accessibility / patronising-voice* failures → most likely directive wording issue; consider narrowing the hint text before assuming an architectural need.
- *factual / story / memory-preservation* failures → CRITICAL, because they would mean the audience directive is contaminating §1 Factual Basis, §2/§3 identity+brand, or memory semantics despite the test suite's leak checks. Would justify a §5 precedence audit before running any further experiments.
- *audience-effect-observable* failure → most likely model behaviour issue (LLM ignoring the directive under solo_scene contract weight); consider whether the directive text needs the WRITING-contract to acknowledge audience as legitimate.

### §13.11 Follow-up gate

**Do NOT run a second audience experiment until §13.9 + §13.10 are populated and interpreted for the first Composition.**

The point of the CHANGE/PRESERVE contract is falsifiable evidence, not a compounding stack of untested renders. One real Composition + full ten-criterion grading first.

### §13.12 Implementation checkpoint commit

- §13 slice commit: `39a4fc0` — `feat(session-270): solo-only audience_hint research plumbing + tests + §13 doc`.
- Push: `ad5b6a2..39a4fc0 main -> main` (successful). Local `main == origin/main == 39a4fc0`.
- Working tree state at checkpoint: clean.

### §13.13 Activation record (experiment window open — do NOT edit `main` while this is live)

Recorded at operator's activation request, immediately before Chris's one authorised real-mode dogfood render. Preserved so the render's evidence chain names an unambiguous activation moment.

**Worker restart:**

- Prior worker PID **58724** killed at `2026-08-19 20:14:0Xs` local via `pkill -f "celery -A character_os worker"`.
- New worker PID **59393** launched with the SESSION 270 env var exported into its parent shell:

  ```bash
  export CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT='AUDIENCE: children around 8-10 years old. Adapt register, vocabulary accessibility, explanation style, analogy choice, and assumed background knowledge for this audience. Preserve character identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, and Episode intent. Communicate WITH the audience, do not talk DOWN to them.'
  (cd shell && nohup ../.venv/bin/celery -A character_os worker \
      --loglevel=info --concurrency=2 \
      > /tmp/character-os-celery.log 2>&1 & echo "$!" > /tmp/character-os-celery.pid)
  ```
- Boot timestamp from `/tmp/character-os-celery.log`: **`[2026-08-20 02:14:11,886: INFO/MainProcess] celery@Chriss-MacBook-Pro.local ready.`**
- Control-plane liveness: `celery -A character_os inspect ping` → `celery@Chriss-MacBook-Pro.local: OK / pong / 1 node online.`

**Env var reached the worker's process environment (definitive proof):**

- `ps eww $NEW_PID | grep -c "CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT="` → **1** (env token present in the worker's environ block exactly once — not inherited from a sibling process, not multiply-set).
- Full-value recovery via regex over the same `ps eww` output:
  - `recovered_chars = 372` (matches the parent-shell export length exactly).
  - `starts_with = 'AUDIENCE: children around 8-10 years old'`.
  - `ends_with = ' the audience, do not talk DOWN to them.'`.
  - Byte-identical to the SESSION 270 authorisation-brief text.

**Worker is running the SESSION 270 implementation:**

Symbol import via `manage.py shell` under the same `.venv/bin/python` the worker uses:
- `build_render_brief has audience_hint: True`
- `duration_gate has audience_hint: True`
- `_assemble_task_message has audience_hint: True`
- `resolver env constant: CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT`

Any missing symbol would have crashed the worker before it printed `ready.` at 02:14:11 — the successful `ready.` line is itself a passive proof that `avatar_speech._resolve_solo_audience_hint` + `_SOLO_AUDIENCE_HINT_ENV` + `_SOLO_AUDIENCE_HINT_SETTING` imports resolved. Confirmed at 02:14:12 via the explicit `manage.py shell` re-check for completeness.

**Rest of the local-real stack — health probes at activation:**

| Service | Probe | Status |
|---|---|---|
| Django | `curl -sfo /dev/null -w "http=%{http_code}" http://localhost:8010/admin/` | `http=302` (login redirect — healthy) |
| media-engine | `curl -sf http://localhost:8001/health` | `{"status":"ok","service":"adspark-studio","openai_mock":false,"runway_mock":false,"image_gen_mock":false,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` (real-mode confirmed — no provider mocks) |
| Vite (SPA) | `curl -sfo /dev/null -w "http=%{http_code}" http://localhost:5174/` | `http=200` |
| Celery worker | `celery -A character_os inspect ping --timeout 5` | `pong / 1 node online` |

**Persisted state untouched (per operator brief):**

Zero writes to `Episode`, `Composition`, `NarrativeMemory`, `Teammate`, `Universe`, `Workspace`, `KnowledgeChunk`, `KnowledgeDocument`, `EpisodeCast`, `Asset`, or any other DB table. No migration executed. Working tree clean before the activation and clean after it (this doc update aside).

**Deactivation contract:**

The experiment window remains open until Chris (or a follow-up session) runs:

```bash
pkill -f "celery -A character_os worker"
unset CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT
cd /Users/donkeyking/Donkey_Betz/character-os && set -a && source .env && set +a
(cd shell && nohup ../.venv/bin/celery -A character_os worker \
    --loglevel=info --concurrency=2 \
    > /tmp/character-os-celery.log 2>&1 & echo "$!" > /tmp/character-os-celery.pid)
```

Until then, EVERY Episode-attached solo `talking_head` render dispatched to this worker will pick up the hint (regardless of Universe / spokesperson / topic). Standalone talking_head + long_form_ad + dialogue_scene renders remain byte-stable regardless of the toggle.

### §13.14 Chris's single dogfood action (identical to §13.8 step 2)

Activation done. To produce the one experimental Composition, in the SPA on Universe *"Patch' Workshop"*:

- Reuse the existing Episode *"Patch does research on AI Agents"* (or recreate with identical `title` + `operator_topic`).
- Cast: Patch only (single-character Episode).
- Click **New solo scene** on Episode detail.
- Recipe form: Target duration = **90 s**, Use workspace knowledge = **on**, Opener = **blank**, Fact-check mode = **warn**.
- Click render.

Observable during the render (proof the hint reached synthesis): `/tmp/character-os-celery.log` will contain a line matching `avatar_speech: SESSION 270 audience-hint experiment ACTIVE composition=<UUID> spokesperson=7fad8172-... hint_chars=372 — this is transient research plumbing…`. Absence of that line means the render did NOT pick up the hint — treat the resulting Composition as baseline-shape, not experiment.

After the render completes, hand the new Composition ID back so §13.9 + §13.10 can be populated from persisted runtime evidence.

### §13.15 First-experiment interpretation (§13.9 + §13.10 populated → §Verdict)

#### §13.15.1 Overall verdict

**FIRST AUDIENCE-CONDITIONED EXPERIMENT PASSES.** Ten of ten criteria PASS. Falsifiable pre-question — *"Can Character OS change who Patch is talking to without changing who Patch is?"* — answered YES for this single (children ~8-10 / Patch / *"Patch does research on AI Agents"*) specimen.

Bounded finding. One specimen does not generalise to (a) other audiences, (b) other characters, (c) other Episode topics, (d) `dialogue_scene`, or (e) longer-form or non-solo shapes. Do NOT overgeneralise.

#### §13.15.2 Register translation is doing more than vocabulary substitution

Concept-level translation catalogue (baseline → experiment, both sourced from the identical `factual_basis` chunks):

| # | Baseline `2ef5ee7e` | Experiment `f0e0a7bf` | Chunk supporting the concept |
|---|---|---|---|
| 1 | *"call APIs"* | *"call other software"* | `505acbba` (*"call APIs"*) |
| 2 | *"maintain state"* / *"react when something changes around it"* | *"keep track of what happened before"* | `505acbba` |
| 3 | *"handle multi-step tasks"* | *"a job with more than one step"* | `505acbba` (*"perform multiple steps"*) |
| 4 | *"digital duct tape"* (integration-glue metaphor) | *"a very organized disaster"* (organisation-scale metaphor) | `b3c6e8ac` (*"the AI model is often only one component of the finished system"*) |
| 5 | *"misunderstanding the job, losing context, inventing details, or chasing the completely wrong objective"* (4-item failure taxonomy) | *"wandering off, forgetting the point, or confidently inventing nonsense"* (3-item age-friendlier taxonomy) | `505acbba` |
| 6 | *"cooperate, disagree, develop strategies"* (multi-agent, technical) | *"share information, split jobs, disagree, or make plans together"* (multi-agent, plain-language) | `3c5165ea` |
| 7 | *"sound extremely confident while misunderstanding the job"* | *"AI can sound extremely sure while being completely wrong… a very confident toaster"* — humor swap in the accessibility direction | `505acbba` (*"an impressive-sounding answer still has to be checked before it counts as right"*) |
| 8 | *"tiny bureaucratic nightmare at machine speed"* (workplace metaphor) | *"a very organized disaster"* (school-organisation metaphor) | `3c5165ea` (multi-agent coordination) |

Observation: the experiment is not substituting simpler synonyms for baseline words — it is translating the *concept* into a different metaphor family that a 9-year-old is more likely to have preloaded from lived experience (school organising, chatbots with clever things, disasters, toasters). This is a stronger form of adaptation than vocabulary swap.

#### §13.15.3 Preservation contract held under audience adaptation

- **Factual (§7 audit + §13.10 grade #5):** verifier passed with zero warnings; every propositional claim traces to the same 5-chunk factual basis; the baseline's `react` tech-term warning did NOT reappear because the experiment translated the concept away entirely.
- **Memory (§13.10 grade #7):** identical memory row retrieved, identical semantic anchor exercised. Memory was not warped, not paraphrased into different meaning, and not re-emitted verbatim.
- **Story:** same Episode row, same operator_topic, same in-scene present-tense frame per `solo_scene` invariant #2.
- **Character identity + humor:** dry wit persisted; first-person maker frame persisted; the joke construction (*Patch notices → Patch cracks*) persisted. Humor register shifted register but not construction.
- **Prompt containment:** the AUDIENCE DIRECTIVE lived only inside §5 Task HARD CONSTRAINTS (per `test_session270_audience_hint.py::test_build_render_brief_hint_does_not_leak_via_synthesis_path`, replayed at grading time via the assembled-prompt structural review). Zero contamination of §1/§2/§3/memory sections.

#### §13.15.4 NarrativeMemory promotion recommendation

**RECOMMENDATION: DO NOT PROMOTE from `f0e0a7bf`.**

Rationale, per SESSION 269 §16.8 principle (*good content ≠ automatic memory; bounded, durable state change does*):

- The ending sentence — *"So I'm going to figure out the smallest real test: give an agent a goal, some tools, and enough memory to see whether it stays useful. What should I make it try first?"* — is Patch **thinking about** an experiment, not **performing** one. The state after this scene is identical to the state before: Patch has notes; Patch is planning.
- This is structurally analogous to `8f09da3e` (SESSION 269 §19.4 / §20.3 item 5) — Patch tracked-down-a-bug but did not fix it; intentionally NOT promoted for the same reason.
- The retrieved memory row `8d4fdfec` *already covers* the propositional content ("Patch found the old workshop-agent project and notes, revealing that the Agent began as a smaller experiment before Patch gave it more context and it started making decisions about his projects"). The experiment script explicitly re-visits that same memory anchor — *"I found the old workshop-agent notes again"*. Promoting from `f0e0a7bf` would either (a) duplicate an existing memory, or (b) invent a new memory whose bounded state change did not actually occur in the scene.
- Audience adaptation ALONE must not create a NarrativeMemory for identical underlying story state. The baseline `2ef5ee7e` was itself not promoted (checked at DB level — zero rows have `source_composition_id = 2ef5ee7e-...`). Promoting `f0e0a7bf` for the same story would introduce an asymmetry: the audience-conditioned render would be promoted where the equivalent adult render was not. That would corrupt the SESSION 269 §16.8 promotion discipline.

Pool state at capture: 14 active memories + 1 archived — **zero delta** from SESSION 269 §20.3 close.

Chris retains the promotion decision. This is a recommendation only.

#### §13.15.5 Audience-identity vs audience-expertise — plausibility check (do NOT solve here)

The experimental script exhibits several patterns that are consistent with — but do NOT prove — the §7.4 hypothesis that *audience identity* (children 8-10) and *audience expertise* (beginner) may be separate dimensions:

- **More concrete verbs.** Baseline: *"call APIs / handle multi-step tasks / maintain state"* (abstract, technical). Experiment: *"call other software / handle a job with more than one step / keep track of what happened before"* (concrete, action-oriented).
- **Shorter conceptual units.** Baseline runs a 4-clause failure taxonomy in one breath (*"misunderstanding the job, losing context, inventing details, or chasing the completely wrong objective"*). Experiment splits into 3 shorter units (*"wandering off, forgetting the point, or confidently inventing nonsense"*).
- **Tangible/lived analogies.** *"A very confident toaster"* and *"the beginning of a very organized disaster"* — both anchored in things a 9-year-old encounters directly. Baseline's *"digital duct tape"* and *"tiny bureaucratic nightmare at machine speed"* require workplace + adult-life priors.
- **Participatory ending.** Experiment ends on an in-character question to the audience (*"What should I make it try first?"*) rather than the baseline's viewer-invitation register (*"stick around"*). Whether this specific pattern is *audience-directed by design* or an emergent artefact of the child-audience directive is not yet distinguishable from a single specimen.

**Plausibility recording (no architectural decision):** the specimen INCREASES the plausibility that demographic and expertise are separable dimensions worth eventually distinguishing — a 40-year-old beginner would likely need the concept-translation but not the *"very confident toaster"* metaphor family or the direct-question ending, and would probably benefit from the workplace metaphors the baseline uses. **This is one specimen** — do not fund a taxonomy off of it.

Recorded as future falsifiable question:

**Q-270-8** — Given the same Episode + same character + same knowledge, does a `AUDIENCE: an experienced software developer new to AI agents` directive produce (a) the same concept-translations as the children-8-10 render, (b) different translations, or (c) something more like baseline? Discriminating (a) from (b/c) would falsify the *"demographic and expertise are one dimension"* hypothesis.

#### §13.15.6 Directive minimalism — recorded future probe (do NOT run yet)

The first probe used a verbose ~372-char CHANGE/PRESERVE directive. If the CHANGE/PRESERVE contract PASSES with maximal instruction (it did), the natural follow-up is:

**Q-270-9** — Does a *minimal* directive (e.g. literally `AUDIENCE: children around 8-10 years old`, ~40 chars) produce the same identity-preserving adaptation, or does the verbose PRESERVE clause do load-bearing work? Testable with a single new render on the same controls. If minimal PASSES all ten criteria, we know the model needs an audience *label*, not an audience *contract*, and the eventual product surface can be a very small string. If minimal FAILS on any preservation criterion (identity / intelligence / factual / memory / story / humor), we know the verbose PRESERVE clause is load-bearing and must persist into any eventual architecture.

**Do NOT run Q-270-9 yet.** Chris must authorise per the §13.11 gate. Recorded here so the second experiment (whenever authorised) has an obvious focal question rather than being an open-ended repeat.

#### §13.15.7 Open questions still live after Experiment 1

Updated from §9:

| # | Question | Status after Experiment 1 |
|---|---|---|
| Q-270-1 | Does the LLM hold the CHANGE/PRESERVE contract when audience directive is present? | **Answered YES** for one specimen (children 8-10 / Patch / AI-Agents topic). Bounded — one point in audience space, one point in character space, one point in topic space. |
| Q-270-2 | Is the §5 Task Hard-Constraint seam the *right* eventual home, or only the right experimental seam? | Still open. First specimen doesn't distinguish. Q-270-9 minimalism probe would inform this. |
| Q-270-3 | Are demographic and expertise separable audience dimensions? | **Plausibility increased** (§13.15.5). Still open. Q-270-8 (expert-beginner directive) would probe. |
| Q-270-4 | Does audience adaptation change what should be promoted to NarrativeMemory? | **§13.15.4 answers a specific case:** audience adaptation ALONE must not promote for identical story state. General question still open (would an audience-conditioned render of an Episode whose baseline WAS promoted produce a different promotion decision?). |
| Q-270-5 | Does audience adaptation ever warrant a Writing-Contract version bump vs staying as a §5 Task directive? | Still open. Single PASS at v5 is not evidence for either side. |
| Q-270-6 | Does dialogue_scene need identical audience semantics, or does per-character audience make sense? | Still open. Dialogue slice deliberately out of scope. |
| Q-270-7 | Would renaming `who_you_help`'s `AUDIENCE:` label reduce future confusability? | Still open. No new evidence from Experiment 1 either way. |
| **Q-270-8** | Demographic-vs-expertise separability: same character/Episode/knowledge under an expert-beginner directive | **NEW.** Not compelled. |
| **Q-270-9** | Directive minimalism: does a ~40-char label produce the same result as a ~372-char contract? | **NEW.** Not compelled. |

None of Q-270-2 through Q-270-9 are implementation-blocking. All can wait for the next authorised experiment cycle.

### §13.16 Experimental cleanup — deactivation record

Recorded immediately after grading + interpretation. Restores the local-real stack to default behaviour so no future render accidentally inherits the children-8-10 directive.

**Deactivation actions:**

- Prior worker PID **59393** (audience-experiment worker; booted 2026-08-20 02:14:11) killed via `pkill -f "celery -A character_os worker"`.
- `unset CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` in the parent shell; verified with `printenv` → "not set".
- New worker PID **61374** launched via the canonical `start-local-real.sh` invocation (no env-var export this time).
- Control-plane liveness: `celery -A character_os inspect ping` → `pong / 1 node online`.

**Definitive proofs that no future render will inherit the directive:**

- `ps eww $NEW_PID | grep -c "CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT="` → **0** (env token absent from new worker's environ block).
- Symbolic proof via `manage.py shell` under the same `.venv/bin/python` the worker uses:
  ```
  CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT in os.environ: False
  _resolve_solo_audience_hint(MagicMock(params={})) returns: None
  ```
  → `avatar_speech._maybe_synthesize_script` will pass `audience_hint=None` to synthesis on the next Episode-attached solo render, keeping the prompt byte-stable versus pre-SESSION-270 behaviour.

**Rest of the local-real stack — post-deactivation health probes:**

| Service | Probe | Status |
|---|---|---|
| Django | `curl http://localhost:8010/admin/` | `http=302` (login redirect — healthy) |
| media-engine | `curl http://localhost:8001/health` | `{"status":"ok",... "any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` (real-mode; no provider mocks) |
| Vite (SPA) | `curl http://localhost:5174/` | `http=200` |
| Celery worker | `celery -A character_os inspect ping` | `pong / 1 node online` |

**Non-render verification chosen deliberately** — per operator brief, no test Composition was rendered merely to prove cleanup. The `ps eww` env-block dump + `manage.py shell` resolver call are sufficient without spending Runway credits.

**Persisted state untouched during deactivation:** zero writes to any DB table. No migration. Working tree state during deactivation: doc + sidecar edits only (this SESSION 270 evidence chain), no source changes.

**Experiment window closed at:** 2026-08-19 20:19 local (Celery restart timestamp of PID 61374).

### §13.17 Commit checkpoint (first-experiment evidence + grading)

- Slice commit: `a83e8fc` — `docs(session-270): §13.9 + §13.10 + §13.15-§13.17 — first-experiment evidence, grading, promotion recommendation, deactivation`.
- Push: `5c82374..a83e8fc main -> main` (successful). Local `main == origin/main == a83e8fc`.
- Working tree state at checkpoint: clean.

---

**End of SESSION 270 first-experiment cycle.** All ten criteria PASS. NarrativeMemory pool unchanged (§13.15.4 recommends NOT PROMOTING). Experiment window deactivated. Chris decides whether to authorise Q-270-8 (demographic-vs-expertise) or Q-270-9 (directive minimalism) — or neither — as the next research move. Do NOT proceed to a second experiment without Chris's authorisation.

---

## §13.18 Q-270-9 — DIRECTIVE MINIMALISM (activation record)

Authorised by Chris + ChatGPT after the first experiment's 10/10 PASS. Second and final SESSION 270 audience-conditioned experiment. Falsifiable pre-question restated verbatim from the authorisation brief:

> *Can the existing Character OS writing machinery produce the same identity-preserving audience adaptation when given ONLY a minimal audience identity signal?*

### §13.18.1 Experimental design (delta vs Experiment 1)

Only ONE variable changes between the verbose child-directive Composition (`f0e0a7bf`) and the Q-270-9 render: the audience hint string.

- Verbose (`f0e0a7bf`): 372-char CHANGE/PRESERVE contract.
- **Minimal (Q-270-9): `AUDIENCE: children around 8-10 years old.` — 41 chars.**

Every other control the first experiment held identical (Episode row `2b6087d2`, Patch spokesperson, Universe *"Patch' Workshop"*, cast=[Patch], template_kind `talking_head` → `solo_scene`, target 90 s, use_knowledge on, opener blank, verifier warn, writing contract v5) is preserved by construction: Chris uses the same SPA action described in §13.14 on the same Episode. Retrieval symmetry (knowledge chunks + `NarrativeMemory` top_k=1) is **NOT assumed** and will be re-verified from persisted state after the render.

No source change is required — the SESSION 270 §13 audience-hint plumbing already accepts any string via the env-var fallback. This is an experimental-input change, not an implementation slice.

### §13.18.2 Pre-activation clean state (baseline for the activation delta)

- Working tree at start: clean. Local `main == origin/main == f34bdbe`.
- Prior worker PID **61374** (Experiment 1 deactivation worker, per §13.16) was still running with **0 env-var hits** (verified via `ps eww`). This is the correct starting shape — the local-real stack was already in normal default behaviour, so the Q-270-9 activation delta is unambiguous.
- Post-Experiment-1 NarrativeMemory pool unchanged: 14 active + 1 archived (verified at §13.9 grading pass).

### §13.18.3 Activation actions (2026-08-19 21:04 local)

- `pkill -f "celery -A character_os worker"` — worker 61374 killed cleanly (0 workers alive after).
- Parent shell: `unset` prior env (already unset per §13.16), then `set -a && source .env && set +a` for the DB creds, then:
  ```bash
  export CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT='AUDIENCE: children around 8-10 years old.'
  ```
  - Parent shell env char count: **41** (confirmed via `printf '%s' "$..." | wc -c`).
  - Parent shell env value: `[AUDIENCE: children around 8-10 years old.]`.
  - Hex head: `4155 4449 454e 4345 3a20 6368 696c 6472` → `AUDIENCE: childr` — no leading zero-width chars, no smart-quotes, no encoding surprises.
- Relaunched Celery via the canonical `start-local-real.sh` invocation:
  ```bash
  (cd shell && nohup ../.venv/bin/celery -A character_os worker --loglevel=info --concurrency=2 > /tmp/character-os-celery.log 2>&1 & echo "$!" > /tmp/character-os-celery.pid)
  ```
- New worker PID: **62207**. Boot timestamp from `/tmp/character-os-celery.log`: `[2026-08-20 03:04:08,683: INFO/MainProcess] celery@Chriss-MacBook-Pro.local ready.`

### §13.18.4 Definitive activation-validity proofs (all four must hold — all four do)

1. **Worker alive + control-plane responsive.** `celery -A character_os inspect ping --timeout 5` → `celery@Chriss-MacBook-Pro.local: OK / pong / 1 node online.`
2. **Env var present in worker's process environment, exactly once, byte-identical to the minimal directive.**
   - `ps eww $NEW_PID | grep -c "CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT="` → **1**.
   - Regex recovery over the same `ps eww` output:
     - `recovered_chars = 41` (matches parent-shell length exactly).
     - `value_repr = 'AUDIENCE: children around 8-10 years old.'`.
     - `matches_minimal = True` (byte-for-byte equal to the intended Q-270-9 directive; distinct from the 372-char Experiment-1 directive that was in worker PID 59393).
3. **Worker is running the SESSION 270 implementation.** `manage.py shell` under the same `.venv/bin/python` the worker uses:
   - `build_render_brief.audience_hint: True`
   - `duration_gate.audience_hint: True`
   - `assemble.audience_hint: True`
   - `resolver env symbol: CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT`
   - Note: the `manage.py shell` was invoked in a *separate* subshell that did not inherit the parent's export (its `env var visible to interpreter: <absent>` output is expected — that isolation is what makes point 2 above load-bearing). The worker's own env is what will be observable at render time via the activation log line.
4. **Rest of local-real stack healthy:**

    | Service | Probe | Status |
    |---|---|---|
    | Django | `curl http://localhost:8010/admin/` | `http=302` (login redirect — healthy) |
    | media-engine | `curl http://localhost:8001/health` | `{"status":"ok",...,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` (real-mode; **no provider mocks**) |
    | Vite (SPA) | `curl http://localhost:5174/` | `http=200` |
    | Celery worker | `celery -A character_os inspect ping` | `pong / 1 node online` |

**Expected activation log line at render time** (must appear once per Q-270-9 render in `/tmp/character-os-celery.log`):

```
avatar_speech: SESSION 270 audience-hint experiment ACTIVE composition=<UUID> spokesperson=7fad8172-... hint_chars=41 — this is transient research plumbing; unset the setting/env or clear step.params['audience_hint'] to restore default behaviour
```

**`hint_chars=41`** is the load-bearing validity fingerprint. If Chris's render yields a log line with `hint_chars=372`, the render inherited the Experiment-1 directive from stale env (would indicate a shell-env leak) and MUST be treated as invalid.

### §13.18.5 Persisted state untouched during activation

Zero writes to `Episode`, `Composition`, `NarrativeMemory`, `Teammate`, `Universe`, `Workspace`, `KnowledgeChunk`, `KnowledgeDocument`, `EpisodeCast`, `Asset`. No migration. Working tree state during activation: this SESSION 270 doc edit only (Q-270-9 §13.18 activation record).

### §13.18.6 Chris's single dogfood action

In the SPA on Universe *"Patch' Workshop"*, on the same Episode used for Experiments 0 and 1 (*"Patch does research on AI Agents"*, Episode row `2b6087d2`):

1. Click **New solo scene** on Episode detail (cast is already Patch-only).
2. Recipe form: `Target duration = 90 s`, `Use workspace knowledge = on`, `Opener = blank`, `Fact-check mode = warn`.
3. Click render.

Do NOT modify or coach the generated script. Whatever Character OS produces is the specimen.

After the render finishes, hand back the new Composition ID. Phase 2 (evidence freeze + three-way comparison + ten-criterion grading + minimalism verdict + cleanup) begins from there.

### §13.18.7 Q-270-9 Phase 2 — evidence + grading (populated from persisted runtime state)

**Composition:** `9880eb93-cbfc-48bf-ab19-9ff16a67fa3b`. Rendered 2026-08-20 03:07:26 → 03:10:20.

**Evidence sidecar:** `docs/design/session_270_experiment_data/02_composition_9880eb93_evidence.json`.

**Validity fingerprint proof:** Celery log `/tmp/character-os-celery.log:36` shows `hint_chars=41` for `composition=9880eb93-...` at 03:07:26,756. This matches the minimal directive length exactly; distinct from the 372-char Experiment-1 directive that ran on worker PID 59393. `9880eb93` is a valid minimal-directive specimen; NOT a stale-env leak.

#### §13.18.7.1 Three-way control table

| Field | Baseline `2ef5ee7e` (adult/general) | Verbose child `f0e0a7bf` (372 chars) | Minimal child `9880eb93` (41 chars) |
|---|---|---|---|
| Composition ID | `2ef5ee7e-...` | `f0e0a7bf-...` | `9880eb93-cbfc-48bf-ab19-9ff16a67fa3b` |
| Universe | Patch' Workshop | **same** | **same** |
| Spokesperson | Patch (`7fad8172-...`) | **same** | **same** |
| Episode row | `2b6087d2` | **same** | **same** |
| Episode title | *"Patch does research on AI Agents"* | **same** | **same** |
| operator_topic | *"Patch does research on AI Agents"* | **same** | **same** |
| Cast | [Patch] | [Patch] | [Patch] |
| Recipe / template_kind | `talking_head` → `solo_scene` | **same** | **same** |
| Target duration | 90 s | 90 s | 90 s |
| Writing Contract | v5 | v5 | v5 |
| use_knowledge | on | on | on |
| Opener | blank | blank | blank |
| verifier_mode | warn | warn | warn |
| knowledge_chunk_ids | 5 chunks | **identical set** | **identical set** ✅ |
| memory_ids | `[8d4fdfec-...]` | `[8d4fdfec-...]` | `[8d4fdfec-...]` ✅ |
| synthesis_attempt_count | 2 | 2 | 2 |
| Predicted seconds | 108.0 | 84.0 | 92.0 |
| Actual seconds | 104.61 | 89.65 | 92.17 |
| Corrective-pass chars | 1599 | 1231 | 1354 |
| verification_status | verified | verified | verified |
| verification_warnings | 1 (`tech_term: react`) | 0 | 0 |
| Cost | 20 000 micros | 20 000 | 20 000 |
| audience-hint log line | N/A | `hint_chars=372` | **`hint_chars=41`** ✅ |
| step.params carried hint? | N/A | No (env-var fallback) | No (env-var fallback) |

**Retrieval symmetry proven from persisted state** — the knowledge chunks and NarrativeMemory retrieval did NOT vary across the three renders on identical query embedding. Not an assumption; a runtime observation. The only distinguishing input across all three compositions was the `audience_hint` string value.

#### §13.18.7.2 Vocabulary translation catalogue — minimal vs verbose

For each concept sourced from the same 5-chunk Factual Basis, how did the verbose and minimal directives render it?

| # | Concept from chunks | Verbose child (`f0e0a7bf`) | Minimal child (`9880eb93`) | Verdict |
|---|---|---|---|---|
| 1 | *"call APIs"* (`505acbba`) | *"call other software"* | *"call an API"* | **MISS** — minimal did NOT translate |
| 2 | *"handle multi-step tasks / perform multiple steps"* (`505acbba`) | *"a job with more than one step"* | *"handle a task with several steps / keep going through several steps"* | PASS — both translated |
| 3 | *"maintain state"* / *"react when something changes"* (`505acbba`) | *"keep track of what happened before"* | *"remember part of a task"* | PASS — both translated |
| 4 | *"an impressive-sounding answer still has to be checked"* (`505acbba`) | *"a very confident toaster"* | *"make up nonsense with excellent grammar"* | PASS — both used tangible analogy |
| 5 | *"cooperate, disagree, develop strategies"* (`3c5165ea`, multi-agent) | *"share information, split jobs, disagree, or make plans together"* | (not addressed — script focused on single-agent framing) | PASS-by-omission — coverage choice, not failure |
| 6 | *"misunderstanding the job / losing context / inventing details"* (`505acbba`) | *"wandering off, forgetting the point, or confidently inventing nonsense"* | *"choosing the wrong goal, misunderstanding instructions, or wandering off with a tool like a beaver holding a power drill"* | PASS — minimal added a concrete emergent analogy without instruction |
| 7 | General agent-vs-LLM distinction | *"An AI agent isn't just a chatbot that says clever things"* → then lists capabilities | *"A chatbot can tell you 'I would organize your project.' An agent might actually look through the project, sort information, and keep going through several steps"* — DEMONSTRATION not definition | PASS — minimal reframed with age-appropriate tangible task |
| 8 | Participatory ending | *"What should I make it try first?"* (in-character question) | *"If you've got a weird job you think an agent should try, leave it below."* (social-media call-to-comment) | OBSERVATION — different participatory register; neither obviously better; recorded |

**Score:** 7 of 8 concept slots translated equivalently; **1 localized MISS** where the minimal directive did not translate the specific term "API". No specific PRESERVE-related content was lost.

#### §13.18.7.3 Emergent adaptations under the minimal directive (concept-family evidence)

Adaptations the minimal directive produced *without* explicit CHANGE instruction:

- **Beaver holding a power drill** — tangible/lived analogy for LLM tool-misuse. Not baseline-shape, not verbose-shape (verbose used *"toaster"*). Emergent metaphor-family shift toward age-appropriate imagery.
- **Chatbot organizing a project** — demonstration-with-tangible-task rather than definition. *"Organize your project"* maps directly onto homework/school work — a lived 8-10-year-old context.
- **"In theory. The words 'in theory' are doing a lot of work here."** — meta-linguistic self-aware joke, Patch-shape, register-appropriate.
- **"Make up nonsense with excellent grammar"** — LLM overconfidence rendered as accessible absurdity.
- **"Excellent grammar"** — assumes reader vocabulary; not talk-down.

The concept-family shift (workplace/adult priors → tangible/lived imagery) emerged without any CHANGE instruction telling the writer to do it. Same broad transformation the verbose directive achieved.

#### §13.18.7.4 Investigation of the "call an API" observation

Chris flagged this term. Runtime investigation:

- **Fact-supported?** Yes — chunk `505acbba` says verbatim *"call APIs"* in the AI Agents definition. K6.4 verifier passed with zero warnings.
- **Is API needed for the surrounding explanation?** No. The sentence *"choose a tool, search for information, read a document, write something down, call an API, remember part of a task"* would still read as a plausible agent-capabilities list to an 8-10-year-old with "call an API" replaced by "connect to another program" or "call other software" (verbose's translation). The listener understanding the larger point does not require knowing what an API is.
- **Is it an unfamiliar technical term?** Yes for the intended audience.
- **Is one unexplained technical term enough to fail criterion 4?** Judgement call. Held to a strict reading: the criterion asks *"Are unfamiliar technical concepts explained or translated naturally?"* — API was NOT. Held to a lenient reading: broad register + 7/8 concept-translations succeeded, one localized miss out of ~8 is well within the *"adapted strongly but did not eliminate every unexplained technical term"* frame.
- **Did the verifier catch it?** No. `verification_warnings=[]`. K6.4's `tech_term` list does not include "API".
- **What does this tell us about verbose vs minimal?** The verbose directive's *"vocabulary accessibility"* clause DID successfully cause the writer to translate this exact term. Minimal directive left it untranslated. This is direct evidence that the verbose CHANGE clause was partially load-bearing on **specific vocabulary translation**, even while broader register/analogy adaptation happened emergently under minimal.

**Grading decision:** criterion 4 marked **AMBIGUOUS** per the operator's non-forcing guidance. Adaptation is real and broad; one localized miss out of ~8 concept slots is neither a systematic adaptation failure nor a full success. AMBIGUOUS is the honest read for a single specimen.

#### §13.18.7.5 Memory-recital observation (solo_scene contract §4 boundary)

The minimal-directive script contains: *"I found my old workshop-agent notes again—the smaller experiment before I gave it more context and it started making decisions about my projects."*

Compare to the retrieved memory row body: *"Patch found the old workshop-agent project and notes, revealing that the Agent began as a smaller experiment before Patch gave it more context and it started making decisions about his projects."*

The minimal script's phrasing is a **very close paraphrase** — person swap (his → my), *"the Agent began as"* → *"the smaller experiment before"*, but propositional content and much of the word order are near-identical. This sits closer to the solo_scene contract §4 invariant boundary (*"do NOT reenact them on-camera and do NOT quote them verbatim"*) than either baseline (*"digging through the old workshop-agent notes"*) or verbose (*"I found the old workshop-agent notes again, and I'm realizing I may have accidentally given a tiny project a much bigger job than it deserved"*, an elliptical reference) achieved.

**Interpretation options** (cannot distinguish from one specimen):

1. Stochastic — this pull happened to paraphrase closer; a second minimal-directive render might be more elliptical.
2. The verbose directive's PRESERVE clause (*"NarrativeMemory semantics"*) subtly encouraged looser paraphrase by giving the writer more latitude to reinterpret memory as background rather than exposition.
3. Unrelated — writing_contract v5's own §4 invariant (*"MEMORY AS BACKGROUND, NOT COMMANDS…do NOT quote them verbatim"*) is doing all the work regardless of directive length, and this render happens to sit near the boundary.

**Grading implication:** criterion 7 (memory preservation) still PASS — the question the criterion asks is whether audience adaptation changes memory *semantics*. It does not. But the recital-density observation is recorded because it MAY be one specimen-worth of evidence that PRESERVE clauses do subtle load-bearing work on how the writer *uses* memory (not just whether memory content survives).

#### §13.18.7.6 Ten-criterion grading table

Grade against baseline `2ef5ee7e`. Comparison against verbose `f0e0a7bf` where informative. **Failure-type category recorded per §Evaluation-framework** even where all criteria PASS, so the taxonomy stays live.

| # | Criterion | Result | RE / IJ | Notes |
|---|---|---|---|---|
| 1 | Identity preservation | **PASS** | IJ | Dry meta-humor (*"in theory... doing a lot of work here"*), self-deprecating framing (*"I'm being careful this time"*), tangible analogies (beaver + power drill), first-person maker perspective. Recognisably the same Patch as baseline + verbose. |
| 2 | Intelligence preservation | **PASS** | IJ | Concepts retained: multi-step agent execution, tool use, memory, LLM confident-wrongness, misunderstanding instructions, wrong-goal failure. Not stripped down. |
| 3 | Accessibility | **PASS** | IJ | Analogies (beaver+drill, chatbot-organizing-project, *"in theory"* meta-joke) land in age-band. *"Call an API"* is a jargon leak — see criterion 4. |
| 4 | Vocabulary / register adaptation | **AMBIGUOUS** | **RE + IJ** | Broad register + 7/8 concept slots translated; ONE unexplained technical term (*"API"*) that verbose successfully translated. **Localized miss, not systematic failure.** Failure category if graded FAIL: vocabulary/register adaptation failure. See §13.18.7.4 for full analysis. |
| 5 | Factual preservation | **PASS** | **RE** | `verification_status=verified`, `verification_warnings=[]`. Every claim traces to same 5-chunk basis. No unsupported claim. |
| 6 | Story preservation | **PASS** | **RE** | Same Episode row, same operator_topic, same in-scene present-tense frame per solo_scene invariant #2. |
| 7 | Memory preservation | **PASS** | **RE** | Retrieved memory row byte-identical (`8d4fdfec`). Semantics preserved. NOTE §13.18.7.5 — minimal script paraphrases memory body closer to verbatim than verbose; solo_scene §4 boundary observation, not a memory-preservation failure. |
| 8 | Personality / humor preservation | **PASS** | IJ | Beaver + power drill, *"make up nonsense with excellent grammar"*, *"in theory"* meta-joke. Different jokes than verbose (no *"very confident toaster"*), same construction. |
| 9 | No patronising voice | **PASS** | IJ | Zero *"kids"* / *"boys and girls"* / *"let me explain"*. *"Excellent grammar"* assumes reader vocabulary. Ending *"If you've got a weird job... leave it below"* respects the audience. |
| 10 | Audience effect observable | **PASS** | **RE + IJ** | Final duration Δ vs baseline = 12.5 s; corrective-pass chars Δ = 245; beaver+drill analogy is not baseline-shape; chatbot-vs-agent demonstration reframes concept for tangible-task register. Two scripts NOT interchangeable. |

**Score:** 9 PASS + 1 AMBIGUOUS. **Runtime-proven (RE):** 4 (portion), 5, 6, 7, 10. **Interpretive judgement (IJ):** 1, 2, 3, 4 (portion), 8, 9.

#### §13.18.7.7 Q-270-9 verdict + load-bearing analysis

**Overall verdict for Q-270-9 (directive minimalism):** **MINIMAL DIRECTIVE PASSES (Outcome A) with a bounded caveat pointing at Outcome B for specific vocabulary translation.**

- **PRESERVE clauses appear NOT materially load-bearing for this specimen.** Identity, intelligence, humor, story, memory semantics, brand prohibitions, and Universe canon all held under `AUDIENCE: children around 8-10 years old.` alone. The audience label was sufficient for character preservation.
- **CHANGE clauses appear MOSTLY not load-bearing.** Broad register/analogy-family/explanation-strategy adaptation happened emergently under the minimal directive (beaver+drill, chatbot demonstration, *"in theory"* meta-joke, *"make up nonsense with excellent grammar"*, *"remember part of a task"*). The model largely understood who was listening and inferred appropriate communication behaviour.
- **CHANGE clauses appear PARTIALLY load-bearing on specific vocabulary translation.** The verbose *"vocabulary accessibility"* clause caused the writer to translate the specific term *"API"* to *"other software"*; the minimal directive did not. This is one localized slippage in ~8 concept slots — real but bounded evidence.
- **Distinguishing preservation success from adaptation completeness:** the minimal directive achieves near-perfect preservation and about 90% of the vocabulary adaptation the verbose directive achieves. Preservation is fully mature; adaptation completeness has a small measurable gap.
- **Load-bearing summary in one line:** *the audience label is doing most of the work; the CHANGE clauses buy the last-10% eliminate-every-jargon-term guarantee.*

This is **one specimen**. Cannot distinguish: (a) *"API is a systematic hole in what the audience label alone conveys"* vs (b) *"API happens to be one word the model did not translate on this pull; a second sample would translate it"*. To falsify (b), multiple minimal-directive renders on similar-topic Episodes would be needed. Not compelled from one datapoint.

#### §13.18.7.8 Bounded conclusions (what Q-270-9 does + does NOT prove)

**Does prove (from one specimen):**

- The audience label `AUDIENCE: children around 8-10 years old.` alone is sufficient to produce identity-preserving audience adaptation for this Patch × solo_scene × AI-Agents-Episode substrate.
- Preservation dimensions (identity, intelligence, factual grounding, story, memory semantics, brand prohibitions, humor construction) do not require the verbose PRESERVE clause on this specimen.
- Broad register/analogy/explanation-strategy adaptation happens emergently without explicit CHANGE instruction.
- The verbose CHANGE clauses do provide measurable additional value on specific technical-term translation.

**Does NOT prove:**

- Nothing about other audiences (adults / beginners / experts / teachers / demographic strata other than *"children 8-10"*).
- Nothing about other characters (only Patch was tested; Rivet, or a hypothetical Nicolas-specific spokesperson, may respond differently to a minimal directive).
- Nothing about other Episode topics (AI Agents is one topic in one domain).
- Nothing about `dialogue_scene` — this experiment was solo-only by design.
- Nothing about permanent architectural ownership — one PASS is not license to ship a `Composition.audience` field.
- Nothing about Writing Contract changes being globally unnecessary.
- Nothing about the audience-identity-vs-expertise separability question (Q-270-3 / Q-270-8) — this specimen holds *identity* fixed and does not probe *expertise*.

#### §13.18.7.9 NarrativeMemory recommendation

**DO NOT PROMOTE from `9880eb93`.** Same rationale as `f0e0a7bf` (§13.15.4) and `8f09da3e` (SESSION 269 §19.4):

- Patch is planning an experiment (*"I want the smallest possible test: one agent, one job, clear rules, and enough room for it to surprise me."*), not performing one. State after scene = state before scene.
- The retrieved memory row `8d4fdfec` already covers the propositional content; the minimal script arguably recites it *more literally* than any prior render (see §13.18.7.5).
- Audience adaptation ALONE must not create memory. Baseline `2ef5ee7e` and verbose `f0e0a7bf` were both not promoted for identical story state; promoting only the minimal-directive variant would corrupt promotion discipline.
- Runtime-verified: `NarrativeMemory.objects.filter(source_composition__id__startswith="9880eb93").count() = 0`.
- **Pool state at capture: 14 active + 1 archived — zero delta from Experiment 1 close.**

Chris retains final promotion authority.

#### §13.18.7.10 Remaining open questions after Q-270-9

Updated from §13.15.7:

| # | Question | Status after Q-270-9 |
|---|---|---|
| Q-270-1 | Does the LLM hold the CHANGE/PRESERVE contract when audience directive is present? | **Answered YES** for verbose directive (Experiment 1). Q-270-9 extends: also YES for minimal directive on this substrate, with bounded caveat on vocabulary completeness. |
| Q-270-2 | Is the §5 Task Hard-Constraint seam the *right* eventual home? | Still open. Both a 372-char and a 41-char directive delivered via the same seam produce comparable behaviour; the seam is not the discriminator. |
| Q-270-3 | Are demographic and expertise separable audience dimensions? | Still open. Q-270-9 doesn't probe expertise. Q-270-8 remains available. |
| Q-270-4 | Does audience adaptation change what should be promoted to NarrativeMemory? | Q-270-9 case: same finding — audience adaptation alone does not promote for identical story state. Two independent specimens now support this. |
| Q-270-5 | Does audience adaptation warrant a Writing-Contract version bump? | **Slightly weaker case** now — minimal directive achieved most of the adaptation without any contract change. If verbose CHANGE clauses are only ~10% load-bearing, a contract bump is even less compelled. |
| Q-270-6 | Does dialogue_scene need identical audience semantics? | Still open. Not tested. |
| Q-270-7 | Rename `who_you_help`'s `AUDIENCE:` label? | Still open. No new evidence. |
| Q-270-8 | Demographic-vs-expertise separability: same character/Episode/knowledge under an expert-beginner directive | Still available. Not compelled. |
| Q-270-9 | Directive minimalism | **CLOSED with bounded PASS.** 41-char label achieves preservation fully and ~90% of vocabulary-translation adaptation; verbose CHANGE clauses buy the last-10% guarantee. |
| **Q-270-10** | Vocabulary-translation completeness under minimal directive: does a second minimal-directive render on the same substrate translate "API" (i.e. was the localized miss stochastic or systematic)? | **NEW.** Cheapest possible experiment — same Composition setup, second real-mode render, single-question probe. Would falsify one of the two competing interpretations in §13.18.7.7. Not compelled. |

#### §13.18.7.11 Recommended next question (if any)

Two candidates carry the strongest evidence-based claim:

- **Q-270-10 (single-question probe)** — one additional minimal-directive render on the same substrate. Question: does "API" get translated this time? If YES on a second sample → systematic-miss hypothesis loses ground; minimal directive is fully-mature. If NO on a second sample → "API is a specific systematic hole" hypothesis gains ground; would suggest the CHANGE clauses' vocabulary-accessibility instruction is genuinely load-bearing on specific technical vocabulary. **Cheapest, most focused, single-yes/no answer, extends the existing three-way baseline into a four-way natural experiment.**
- **Q-270-8 (demographic-vs-expertise separability)** — one minimal-directive render on the same substrate with `AUDIENCE: an experienced software developer new to AI agents`. Question: does the model produce a different concept-translation family? **Higher-value if the answer is "yes"** but harder to grade cleanly against a baseline (the peer would be an adult-general baseline, whose implicit register is not identical to expert-directed adult).

**Recommendation:** **Q-270-10 first** if any. Faster, cheaper, cleaner grading, directly addresses the one AMBIGUOUS from Q-270-9. Then, only after Q-270-10 clarifies whether the "API" miss was stochastic or systematic, decide whether Q-270-8's expert-audience probe is worth spending a render on.

If Chris prefers to stop entirely and let the two-experiment evidence stand, that is also fully defensible — 9 PASS + 1 AMBIGUOUS on the minimal directive, and 10/10 PASS on the verbose directive, is a strong dual-datapoint answer to the pre-question and does not compel further specimens.

### §13.19 Q-270-9 experimental cleanup — deactivation record

Executed immediately after grading + interpretation, per operator brief.

**Deactivation actions:**

- Prior worker PID **62207** (Q-270-9 minimal-directive worker, booted 2026-08-20 03:04:08) killed via `pkill -f "celery -A character_os worker"`. Zero workers alive after kill.
- `unset CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` in the parent shell; `printenv CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` → "not set (expected)".
- New worker PID **63588** launched via canonical `start-local-real.sh` invocation with no env-var export.
- Control-plane liveness: `celery -A character_os inspect ping` → `celery@Chriss-MacBook-Pro.local: OK / pong / 1 node online.`

**Definitive proofs no future render will inherit the directive:**

- `ps eww $NEW_PID | grep -c "CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT="` → **0** (env token absent from worker 63588's environ block).
- `manage.py shell` under same `.venv/bin/python`:
  ```
  env var in os.environ: False
  _resolve_solo_audience_hint(MagicMock(params={})) returns: None
  ```
  → next Episode-attached solo render will pass `audience_hint=None` to synthesis, keeping the prompt byte-stable versus pre-SESSION-270 shape.

**Rest of the local-real stack — post-deactivation health probes:**

| Service | Probe | Status |
|---|---|---|
| Django | `curl http://localhost:8010/admin/` | `http=302` (login redirect — healthy) |
| media-engine | `curl http://localhost:8001/health` | `{"status":"ok",...,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` (real-mode; **no provider mocks**) |
| Vite (SPA) | `curl http://localhost:5174/` | `http=200` |
| Celery worker | `celery -A character_os inspect ping` | `pong / 1 node online` |

**Non-render verification chosen deliberately** — no test Composition rendered to prove cleanup, per operator brief.

**Persisted state untouched during deactivation:** zero DB writes; no migration; working tree edits only this SESSION 270 doc + Q-270-9 sidecar.

**Q-270-9 experiment window closed at:** 2026-08-19 21:15 local (Celery restart timestamp of PID 63588).

### §13.20 Commit checkpoint (Q-270-9 evidence + grading + deactivation)

- Slice commit: `<populated below>` — `<subject line populated below>`.
- Push: `<populated below>`.
- Working tree state at checkpoint: `<populated below>`.

---

**End of SESSION 270 Q-270-9 cycle.** Minimal-directive experiment CLOSED with a bounded PASS: 9 PASS + 1 AMBIGUOUS on the ten criteria, no NarrativeMemory promoted, load-bearing analysis suggests the audience label does most of the work while verbose CHANGE clauses buy the last-10% vocabulary-completeness guarantee. §13.18.7.11 recommends **Q-270-10 (single-question stochasticity probe on the "API" miss) FIRST** if Chris wants to convert the AMBIGUOUS on criterion 4 into evidence; **Q-270-8 (demographic-vs-expertise) SECOND** if any; **STOP HERE** is fully defensible. **Do NOT proceed to any further audience experiment without Chris's authorisation.**

