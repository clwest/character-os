# SESSION 270 — Handoff

Concise starting point for the next Character OS session. Full
SESSION 269 context lives in
`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md` (§0-§20)
with nine frozen evidence sidecars under
`docs/design/session_269_experiment_data/`. Read the sections
referenced below BEFORE implementing anything.

Working method (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Persist important findings, audits, and decisions under
`docs/design/` before stopping.

Methodology rules that ripened during SESSION 269 (keep applying):

- **§13.1 four-level verification hierarchy** — SOURCE IMPLEMENTED → TESTED → LIVE VISIBLE → OPERATOR REACHABLE. Never upgrade a claim without evidence at the claimed level.
- **§14.12 product-contract-before-prefill rule** — for creator-facing work, verify the PRODUCT CONTRACT with the operator BEFORE verifying prefill mechanics. Prefill working ≠ product mode correct.
- **§15.7 polymorphic-parameter grep rule** — when adding a new value to a polymorphic parameter (enum, shape, mode), grep the parameter name across the entire call chain and enumerate every allow-list / whitelist / validator that gates it.
- **§16.8 promotion discipline** — *good content ≠ automatic memory*. Only bounded, durable state change justifies a NarrativeMemory promotion.
- **Restart Celery after backend slices** — Celery does NOT autoreload; a slice landing on `main` does not mean the worker is running the new code. §11.3 + §15.7 both flagged this.

---

## Current Character OS state (as of SESSION 269 close)

- Branch: `main`. Working tree clean at close.
- HEAD after SESSION 269 closeout: recorded in §20.6 of the SESSION 269 doc.
- `NarrativeMemory` retrieval `top_k = 1` — unchanged since SESSION 264 Slice 2.
- Retrieval predicate + witness eligibility filter
  (`shell/apps/embeddings/retrieval.py:499-543`) — unchanged since §10.
- **Symmetric witness enforcement** proven end-to-end through the ship path (§17.6 + §18.4).
- **`solo_scene` writing contract** live at `WRITING_CONTRACT_VERSION = 5` for Episode-attached talking_head; standalone talking_head + `long_form_ad` + `dialogue_scene` contracts byte-stable.
- **Episode create UX** captures cast atomically (§12). Episode detail scene-CTA gated on cast cardinality.
- **`Composition.memory_ids`** provenance recipe-agnostic; MemoriesUsedPanel + MemoriesUsedSummary mount unconditionally on Composition detail.
- Duration calibration + writing contract v5 + GPT-5.6-terra — unchanged.

## Patch's Workshop NarrativeMemory pool at SESSION 269 close

**14 active memories** across three witness classes. Verified
against runtime at closeout; §20.3 preserved for reference.

Whole-cast (10) — availability *"In any future scene"*:

- `f25e53af` — the agent Patch wired to the workshop thinks it runs the place.
- `48746f69` — The workshop agent began deciding which of Patch's projects it considers necessary.
- `eda32b58` — The workshop agent began rearranging the order of Patch's projects without explaining its criteria.
- `a34cc005` — Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting before the details are settled.
- `d98962e2` — Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process.
- `87d4e553` — Patch decided the workshop should create a mascot as a character-consistency experiment.
- `6b5222b1` — Patch built a workshop helper that watches for interesting events and leaves messages, but it has already started adding its own commentary to what it observes.
- `42acc26d` — Patch decided the workshop needs rules and began adopting Rivet's more methodical approach to experiments, including making predictions and changing one thing at a time.
- `8d4fdfec` — Patch found the old workshop-agent project and notes, revealing that the Agent began as a smaller experiment before Patch gave it more context and it started making decisions about his projects.
- `36c21641` — Patch fixed a software bug by changing only one thing and testing the same failure again, discovering firsthand that isolating a change made it possible to identify the actual fix. Rivet witnessed the unusually disciplined experiment. **(NEW SESSION 269 §19)**

Rivet-only (3) — availability *"When Rivet is present"*:

- `cd73d52f` — Because it had an opinion about our work. An uninvited opinion. That is scientifically interesting and operationally irritating. *(observational)*
- `c86d4902` — While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him. *(observational)*
- `6d8191b1` — Rivet has come to believe Patch built him partly to be the one who asks the inconvenient questions and brings methodical testing to Patch's impulsive experiments. *(introspective — NEW SESSION 269 §18)*

Patch-only (1) — availability *"When Patch is present"*:

- `c614ca86` — Patch deliberately gave the workshop agent one small decision to make: choose which project he should work on next, while keeping the Agent's authority tightly limited. **(NEW SESSION 269 §17)**

## SESSION 269 shipped implementation summary

Full details in SESSION 269 §20.1. Four source-code slices:

- **§10 solo talking_head NarrativeMemory lane** (`765bb73`) — Universe-scoped `talking_head` compositions now retrieve `NarrativeMemory` under the same witness predicate `dialogue_scene` uses.
- **§12 one-character Episode creator workflow** (`06ba772`) — Create Episode form gains atomic cast picker; Episode detail scene-CTA gated on cast cardinality (cast=0 → no CTA + hint; cast=1 → *"New solo scene"*; cast=2+ → *"New dialogue scene"*).
- **§15 Episode-attached solo talking_head STORY MODE** (`44618fc`) — new `solo_scene` writing contract (WRITING_CONTRACT_VERSION 4→5); primitive routes to `solo_scene` when `composition.episode_id is not None AND template_kind == "talking_head"`; SPA hides script + use_knowledge for Episode-solo and force-supplies both on submit.
- **§15.7 whitelist hotfix** (`251b3b0`) — `build_render_brief` input-guard extended to accept `"solo_scene"`.

**Full backend suite at closeout: 1566 passed. SPA: 640 passed.**

## SESSION 269 organic-dogfood chronology

Five Episodes rendered + audited in SESSION 269 §16-§19:

- `2ef5ee7e` (§16, Patch solo research) — first §15 acceptance render; §10 wire path proven live; not promoted (setup/intention).
- `d3107ed2` (§17, Patch solo action) — promoted `c614ca86` (first Patch-only witness class in the pool).
- `be39452d` (§18, Rivet solo introspection) — first symmetric solo witness test (Patch-only `c614ca86` correctly excluded); promoted `6d8191b1` (first introspective Rivet-only).
- `8f09da3e` (Patch solo debugging setup) — NOT promoted; validated *good content ≠ automatic memory* principle.
- `ba431203` (§19, Patch+Rivet dialogue debugging) — actually fixed the bug; promoted `36c21641` (whole-cast); demonstrated Rivet-private memory retrieved into a Patch+Rivet scene without disclosure to Patch (writer behaviour, NOT enforcement).

**Cumulative invariant scoring:**

- `solo_scene` renders (3 Episodes): **18/18 PASS, 8 STRONG.**
- `dialogue_scene` renders (1 Episode on the new domain): **11/11 PASS, 4 STRONG.**

## Deferred / non-blocking findings carried forward

Full enumeration in SESSION 269 §20.4. Not restated here in
full to keep the handoff short — key items to be aware of:

- Chronology / story-time primitive on Episode (D-3 / §9.7) — still not built.
- Per-character epistemic isolation in dialogue prompts (D-4 / §19.3) — writer-behaviour-only; may become load-bearing for 3+ cast Universes.
- Repeated weak-retrieval signal from `c86d4902` (D-2 / §4 updated through §19) — no relevance floor built.
- Runners-up + distances probe on retrieval (D-1 / §4.2) — not built; not compelled.
- Audience-participation loop (D-10 / §18.6) — FUTURE / DEFERRED per operator instruction; DO NOT IMPLEMENT.
- Composition-detail Episode-solo helper-copy staleness (D-9 / §16.9) — cosmetic follow-up.
- `EXP266-*` universe cleanup — deliberately preserved.

**None of the deferred items are implementation-blocking for
SESSION 270.**

---

## SESSION 270 opening question — Audience-aware character performance

**INITIAL question only. Do NOT investigate or implement it
during SESSION 269 closeout. This is the SESSION 270
starting-point specification only.**

### The observation

Character OS currently understands, at synthesis time:

- **Who is speaking** — spokesperson identity (`Teammate` + K2 identity fields + personality).
- **What the story intent is** — `Episode.operator_topic` or `talking_head` script/topic.
- **What is factually grounded** — Universe canon (`KnowledgeChunk` shared + per-character), retrieved `NarrativeMemory`.
- **What shape to write** — recipe / `WritingContract` shape (standalone / long_form / dialogue_scene / solo_scene).

It does **NOT** currently understand:

- **Who the characters are speaking TO.**

Every SESSION 269 render was implicitly written to a
general/adult audience. Patch's *"digital duct tape"* and
Rivet's *"a coincidence wearing a tiny hat"* land there. Neither
character was ever asked to speak to a different audience.

### The design question

Could the SAME Patch and Rivet — with the SAME identities,
knowledge, relationships, memories, and Episode intent —
communicate naturally to children around 8-10 years old without
becoming different characters or merely *"dumbing down"* the
content?

### Desired conceptual distinction

**CHANGE:**

- audience / register
- vocabulary accessibility
- explanation style
- analogy choice
- assumed background knowledge

**PRESERVE:**

- character identity
- intelligence
- personality
- relationship dynamics
- factual grounding
- story state
- NarrativeMemory semantics
- Episode intent

### What SESSION 270 must NOT do at opening

- **Do NOT decide the eventual architecture** (Composition-level? Episode-level? Universe-level? Teammate-level default? default+override hierarchy?). That is a downstream conversation.
- **Do NOT implement** any audience field, prompt block, or writing-contract change until evidence-first inspection is complete.
- **Do NOT confuse "audience awareness" with the deferred audience-participation loop** (§18.6 / D-10). Those are separate directions:
  - **Audience-aware character performance** (SESSION 270 opener) = the character adjusts *how they speak* based on *who is listening*.
  - **Audience-participation loop** (D-10, deferred) = viewer submissions become operator-approved story inputs. Not on the SESSION 270 opening path.

### Prescribed SESSION 270 first move

Evidence-first inspection: determine **where audience / register
currently exists implicitly**, if anywhere, in the writing
pipeline. Sources worth reading before proposing anything:

- `shell/character_os/writing_contract.py` — every shape's contract text; look for implicit-audience assumptions.
- `shell/character_os/script_synthesis.py::_build_character_voice_section` + `_build_brand_voice_section` — the character-voice and brand-voice blocks; audit whether `who_you_help` / `desired_feeling` / `voice_energy` / `tone_archetype` already carry any audience implication.
- `shell/character_os/dialogue_synthesis.py::_build_character_voice_block` — same audit for dialogue.
- Any Teammate identity fields that could plausibly be interpreted as audience specifiers (e.g. `who_you_help` — currently framed as audience-*served*, not audience-*addressed*).
- Recipe metadata: `RecipeField` help text on `script` and `topic` fields — do they imply an audience?

If the inspection reveals audience is truly absent from the
current pipeline, the natural next move is to name the smallest
place it could live (analogous to §14 for STORY MODE) without
proposing an eventual architecture.

If the inspection reveals audience already lives implicitly
somewhere (e.g. `who_you_help` on some Teammates already
constrains vocabulary), the natural next move is to make that
existing state explicit before adding new plumbing.

### Falsifiable form for SESSION 270's first render dogfood (if the design converges)

*"Can the current Patch, currently in the pool of 14 memories,
speak to an 8-10-year-old audience about the same Episode
topic without becoming a different character?"*

Answerable via a bounded solo render if the eventual mechanism
is in place. Not compelled at session opening — investigate
first.

---

## Recommended first SESSION 270 moves

None are prescribed. All are candidates; SESSION 270 must begin
with an audit / orient pass and a falsifiable question, not
implementation.

1. **Read SESSION 269 §20 CLOSEOUT + §20.3 preserved findings** to load context.
2. **Confirm live runtime state** — pool = 14 active memories; branch clean.
3. **Read the audience-aware pipeline sources** listed above.
4. **Return with an evidence-first report** on whether audience already lives implicitly in the pipeline.

Do NOT skip step 3 — the operator's brief is explicit that the
first move is evidence-first inspection of the existing
pipeline.

---

**Do NOT start SESSION 270 in this handoff. This document is a
starting point, not a plan of record. The next session begins
with an audit / orient pass and follows evidence.**
