# CUSTOMER EXPERIENCE REVIEW — INDEX

**Status:** reading guide (not a summary)
**Purpose:** provide a durable map into the design history produced during SESSION 250 — a four-artifact customer-experience review plus a subsequent identity-ontology definition — so future sessions can enter the reasoning without reconstructing the conversation
**Session of origin:** SESSION 250 (2026-08-08)
**Ratification state:** the customer-experience-review quartet is preserved as design history pending explicit operator ratification of individual items. `IDENTITY_MODEL_V1.md` is a ratifiable proposal, not yet ratified.
**Sibling context:** Step 10 (`§19.3 row 10 — benchmark round one`) remained intentionally unopened throughout this work; the product-review + ontology tracks ran in parallel to the paused Step 10 architecture track and do not affect its sequencing.
**Scope of this index (2026-08-08 amendment):** originally covered the three-artifact design history plus its own index (quartet). Extended in the same session to also cover `IDENTITY_MODEL_V1.md`, produced as a follow-up ontology work that grew out of the audit findings.

---

## Why this review was initiated

SESSION 250 opened for Step 10 architecture inspection. Two prerequisites surfaced during the read-only inspection pass:

- **P-0** — Step 9.b workflow shipped in tests, not exercised on the persistent dev DB (Chris's real reviewer workflow pending).
- **P-1** — `PortraitProvider` cannot perform contract-defined reference-conditioned regeneration; a narrowly-scoped provider-extension slice (PP-EXT) is required before Step 10 opens.

Both prerequisites were accepted. Rather than resume the technical track immediately, the operator invoked a parallel product-level pause: **the customer-facing shape of Character OS had never been reviewed against real-world users**, and the operator wanted to understand what the product actually is before continuing to build on top of it.

The three documents indexed below are the result of that pause. They are design history, not implementation plans.

---

## Reading order

Read in this order. Each document was authored knowing the prior one existed and reacts to it.

### 1. `PERSONA_REVIEW_SESSION_250.md` — the evidence

*Question it answers:* what happens when 10 different kinds of real-world users encounter the shipped Character OS product for the first time?

*What it is:* a walk-through of every major SPA surface (dashboard, wizard, spokesperson pages, knowledge, transcripts, scripts, recipes, campaigns, videos, assets, bundles, settings, bootstrap-review) from ten simulated persona voices — coffee shop owner, first-grade teacher, child therapist, realtor, dentist, church pastor, museum curator, fitness coach, accountant, solo consultant. Ends with 12 cross-persona findings, 8 product-level observations, and a 20-item prioritized friction list.

*Method to keep in mind while reading:* the personas are simulated by a design-sensitive reviewer imagining first-time reactions to shipped SPA copy. This is design pressure-testing, not customer research. The adversarial review (document 3) formalizes this distinction.

### 2. `CUSTOMER_MENTAL_MODEL_V1.md` — the proposal

*Question it answers:* given that evidence, what does a customer actually believe they are creating, teaching, asking, making, and publishing — and what would the product's mental model look like if it were designed around customer jobs rather than backend entities?

*What it is:* a design-lock-candidate document that proposes a three-object customer model (your AI / what it knows / what it makes), a vocabulary contract (which internal terms should not appear on customer surfaces, and what customers actually need to understand instead), a customer-facing information architecture proposal, a preservation list of the shipped UI pieces that already speak well, and a set of acceptance criteria for a future UX implementation milestone. Includes ten intentionally unresolved questions.

*Ratification state:* proposed only. Not ratified. Not implemented.

### 3. `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` — the critique

*Question it answers:* where did the proposal outrun its evidence, mix strategy with UX, harden hypotheses into conclusions, or cross from principle into implementation prematurely?

*What it is:* an intellectual self-review of document 2, structured as eight findings (F1-F8), nine specific recommended edits (E1-E9), a wording-precision table, a "Ready for Design Lock" list of claims mature enough to become foundational principles, and a "Still Requires Operator Judgment" list of intentionally unresolved questions.

*Ratification state:* the review's own recommendations are proposals; none have been folded into document 2. The separation is deliberate — future ratification of any recommendation should be a conscious decision that references this critique, not a silent edit that loses the reasoning.

---

## What has been intentionally ratified

**Nothing yet.**

The trio is complete as design history but no item has been formally ratified. The "Ready for Design Lock" section in document 3 identifies eight claims that are mature enough to become foundational principles when the operator chooses to ratify them; until that happens they are recorded as candidate ratifications, not commitments.

---

## What remains intentionally unresolved

The full open-question list lives in the "Still Requires Operator Judgment" section of document 3. In brief, these questions were left open on purpose:

- The universal-noun question (does Character OS need a class term at all in customer surfaces?)
- The go-to-market target audience
- The Data & Providers surface (blocked on business/legal decisions)
- The customer object model's shape (three-object reduction vs jobs-based frame)
- Several specific IA choices (destination vs action, top-level nav shape)
- The verifier's exposure to the customer
- Multi-AI product shape
- Live vs asynchronous conversation product shape
- The italic-gold section-mark typography and brand voice
- Pricing and upgrade surfacing

Each of these should remain unresolved until the operator has enough evidence or business decision to answer them.

---

## What was intentionally NOT touched during this work

- **Step 10** (`§19.3 row 10 — benchmark round one`) remained closed and unopened throughout. The product-review track did not affect its sequencing.
- **P-0** (Chris's real Step 9.b operator review workflow on the persistent dev DB) remained pending.
- **PP-EXT** (the PortraitProvider regeneration prerequisite scope-locked earlier in SESSION 250) was not implemented.
- **No code was written** during the product-review track. No SPA files edited. No backend files edited. No migrations.
- **No backend model renamed.** Customer-vocabulary proposals in document 2 apply to presentation-layer surfaces only; Django model names (`Spokesperson`/`Teammate`, `Composition`, `Asset`, etc.) are contract identifiers and were not proposed for change.
- **No contract amended.** `CANONICAL_IDENTITY_CONTRACT_V1.md` and all sibling design locks are unaffected.
- **Document 2 was not edited in response to document 3.** The critique's recommendations remain inside the critique artifact; the design document is preserved in its original form.

---

## How to use this trio in a future session

If a future session needs to make any decision that touches the customer-facing product:

1. **Read document 1** to ground yourself in the range of user reactions that surfaced.
2. **Read document 2** to understand the proposed customer model.
3. **Read document 3** to understand which parts of that proposal are load-bearing, which are provisional, and which are known to overreach.
4. **Check the "Ready for Design Lock" and "Still Requires Operator Judgment" lists** in document 3 before treating any claim as settled.
5. **If ratifying any item**, do so consciously — reference this trio in the ratification, and if adopting a document 3 recommendation into document 2, treat that as an explicit ratification event rather than a silent edit.

If a future session needs to *revise* the customer model, the honest move is to append a `V2` document that supersedes V1 with dated reasoning, rather than editing V1 in place. V1 + its adversarial review are the design record of what SESSION 250 knew; that record should not be rewritten to look like it always agreed with V2.

---

## Chronology of the design investigation

For future readers reconstructing what happened:

| Order | Artifact | What it represents |
|---|---|---|
| 1 | Step 10 architecture inspection (SESSION 250 conversation, not persisted as a doc) | Identified P-0 and P-1 as prerequisites to Step 10 |
| 2 | P-0/P-1 architecture responses (SESSION 250 conversation) | Scope-locked PP-EXT and defined Chris's Step 9.b operator workflow |
| 3 | Chris promoted to `is_staff=True` (targeted DB update) | Enables Chris's real Step 9.b operator workflow when he chooses to run it |
| 4 | Product review invoked (parallel track, SESSION 250 conversation) | Operator pause: understand the product before building more of it |
| 5 | `PERSONA_REVIEW_SESSION_250.md` created | Evidence |
| 6 | `CUSTOMER_MENTAL_MODEL_V1.md` created | Proposal |
| 7 | `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` created | Critique |
| 8 | This index created | Reading guide (initial four-artifact scope) |
| 9 | Chris's Phase 9.b operator review revealed zero canonical-quality bootstrap candidates across all four fixtures | Product finding: bootstrap generation matrix failed to produce a canonical identity Chris would approve |
| 10 | Iterative discovery experiments (E-Ident, Phase -1, E-Persona v2) | Falsified strong-form H7 for humans; discovered concept-persistence vs identity-persistence distinction; discovered creator-first paradigm; discovered that ad-hoc research scripts bypass production |
| 11 | Production Step 2 audit + product-model audit | Established that a rich creator model already exists in Character OS's substrate (SESSION 232 identity slots) but is not consumed by downstream systems |
| 12 | Ontology first draft + adversarial pass + reconciliation | Established the three-layer identity ontology as an implementation-agnostic foundation |
| 13 | `IDENTITY_MODEL_V1.md` created | Ratifiable ontology proposal |
| 14 | Documentation-integration pass | CLAUDE.md + CUSTOMER_JOURNEY_V1 + design-history preface pointers + this index extension |
| 15 | `IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` created (with post-review corrections) | Three-way comparison classifying every ontology concept against ratified design + shipped behavior; TC-3 removed on operator re-read; realtime personality path corrected; Charge and Values reclassified PARTIAL |
| 16 | Operator-decision reviews opened (one at a time per operator preference) | Structured product-judgment reviews for OD-1 through OD-6 |
| 17 | OD-1 ratified — Presence authoring driven by creative intent | `operator-decisions/OD-1_PRESENCE_AUTHORING.md`. Templates demoted from required customer-facing abstraction to implementation scaffolding + optional aid; palette remains valid during transition; replacement UI, template disposition, and migration deliberately left open |
| 18 | OD-2 review — initial Position D ("system responsibility for coherence") failed adversarial pass | Coherence framing surfaced three problems: privileges one possible creator quality (excludes intentional-tension creators), collapses distinct concepts (identity / stylistic / brand / narrative / modality coherence), and treats an outcome as if it were an implementation mechanism. Reframed toward fidelity. |
| 19 | OD-2 ratified — Creator Fidelity | `operator-decisions/OD-2_CREATOR_FIDELITY.md`. Character OS commits to fidelity to the customer's authored creator across contexts and modalities. Relevant authored intent must not be silently ignored; explicit customer choices must not be overridden by hidden implementation defaults; intentional tension is preserved; declared safety/legal/product-constraint exceptions are legitimate. Coherence is not ratified as the controlling principle; it emerges from fidelity where the customer authored coherence. Ontology §7.2 preserved unchanged as reference material; the OD-2-vs-§7.2 relationship is recorded explicitly in the OD-2 artifact and the three-way comparison. |
| 20 | OD-3 review — initial framing as "identity-edit reprojection" reshaped under adversarial pressure | Original framing centered "identity edits" and used "reprojection" as an implementation verb, presuming a mechanism before the product question was settled. Pressure-tested against customer-driven transformation scenarios ("rewrite this script," "regenerate this portrait with my updated creator," "make Version 2," "translate this article," "turn this blog post into a video"), the deeper principle surfaced: existing artifacts are historical records; new artifacts may be created from existing artifacts whenever the customer directs. The distinction between *system-inferred rewriting of history* (prohibited) and *customer-directed creation of new work from existing work* (fully supported) became the governing frame. |
| 21 | OD-3 ratified — Artifact History | `operator-decisions/OD-3_ARTIFACT_HISTORY.md`. Character OS produces every artifact with fidelity to what the customer authored at the moment of generation. Existing artifacts remain historical records of what was created. Identity edits shape future artifacts; they do not silently modify, regenerate, annotate, or invalidate existing ones. New artifacts may always be created from existing artifacts at the customer's direction — the original remains as it was produced; customer-directed transformation produces new work from existing work, not modification of history. The customer retains full agency over their historical work (preserve, derive, retire) as customer-driven decisions, not system-driven consequences of authoring changes. Ontology GOVERNANCE layer (§4.3) preserved unchanged as reference material; the OD-3-vs-GOVERNANCE relationship is recorded in the OD-3 artifact. SESSION 171 hardcoded-`coach` re-bake incident is explicitly anchored under OD-3 as the class of system-initiated re-bake the ratification rules out. Three-way comparison §7 renumbered: the identity-edit reprojection question (prior §7 OD-5) is SUBSUMED by OD-3; the meta-question of OES adoption (original §7 OD-3 slot) is now handled per-concept as each becomes decision-worthy. |
| 22 | OD-4 review — hypothesis under test was whether a universal customer-facing class noun is required at all | Discipline held: do not begin from the assumption that Character OS needs a class noun; treat the assumption itself as the hypothesis. Four positions pressure-tested (A: one universal noun everywhere; B: different layers use different nouns; C: customers rarely need a class noun because name-anchoring carries interaction; D: name-primacy as ratified frame; class-term-in-UI-moments is copy, not product-model). OD-1 disappearance discipline applied: if a universal class noun vanished tomorrow, nothing becomes impossible; if name-primacy vanished, the customer's whole relationship with each individual creator flattens. Position D preferred. Adversarial pass survived. |
| 23 | OD-4 ratified — Name Primacy | `operator-decisions/OD-4_NAME_PRIMACY.md`. Character OS is centered on individual creators, not on a customer-facing class taxonomy. Customers primarily relate to each creator by its chosen name; a universal customer-facing class noun is not required for the product to function or for the customer to form a coherent mental model. Where a class reference is used, the language chosen is a communication decision, not a defining product concept. An earlier OD-4 draft embedded editorial policy (UI wording, marketing language, engineering identifiers, documentation conventions) within the ratification body; that draft was tightened by roughly half on operator review — editorial policy is not product philosophy, and freezing it in a ratification would over-constrain future product work. The ratified statement is three sentences that survive UI redesigns, marketing changes, engineering refactors, URL migrations, database renames, documentation rewrites, model providers, and new product surfaces. Ontology §10 non-scope preserved unchanged as reference material; OD-4 makes the non-scope itself the ratified product principle. Three-way comparison §2 F10 (universal class noun) reclassified from UNRESOLVED-across-all-three to RATIFIED under OD-4. |

At the close of this update: Step 10 still unopened; P-0 still pending; PP-EXT still unimplemented; no customer-facing code changed; ontology V1 preserved; the four ratified operator decisions (OD-1 Presence Authoring, OD-2 Creator Fidelity, OD-3 Artifact History, OD-4 Name Primacy) form a coherent product-philosophy stack — customer authors intent, system faithfully realizes the authored creator, history is preserved and new work may be created from history at customer direction, and the customer relates to individual creators by name rather than to a class taxonomy; OD-6 (whether the three-way comparison should trigger any doc amendments) remains the sole pending item from the original §7 list (OD-5 was subsumed by OD-3).

---

## Reading order — extended

The original four-artifact reading order (§ "Reading order" above) has been extended in the same session with two additional documents. Full sequence:

1. `PERSONA_REVIEW_SESSION_250.md` — evidence
2. `CUSTOMER_MENTAL_MODEL_V1.md` — proposal
3. `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` — critique
4. This index — reading guide
5. `IDENTITY_MODEL_V1.md` — implementation-agnostic identity ontology (later work that grew out of the audit findings; establishes what identity IS before any architecture is derived)
6. `IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` — analytical companion to document 5; classifies each ontology concept against ratified design docs and shipped behavior (ALIGNED / DESIGN-AHEAD-OF-CODE / CODE-AHEAD-OF-DESIGN / ONTOLOGY-EXPANDS-SCOPE / TRUE-CONFLICT / HISTORICAL-ONLY / UNRESOLVED); surfaces the operator decisions required before implementation planning; does NOT ratify ontology concepts into product doctrine
7. `operator-decisions/` — folder holding durable operator-decision artifacts. Each ratified OD becomes a standalone file (`OD-N_TOPIC.md`) with a verbatim ratification statement, context, effect on existing docs, and amendment protocol. Current entries: [`OD-1_PRESENCE_AUTHORING.md`](operator-decisions/OD-1_PRESENCE_AUTHORING.md) (ratified 2026-08-08), [`OD-2_CREATOR_FIDELITY.md`](operator-decisions/OD-2_CREATOR_FIDELITY.md) (ratified 2026-08-08), [`OD-3_ARTIFACT_HISTORY.md`](operator-decisions/OD-3_ARTIFACT_HISTORY.md) (ratified 2026-08-08), [`OD-4_NAME_PRIMACY.md`](operator-decisions/OD-4_NAME_PRIMACY.md) (ratified 2026-08-08).

Documents 1-4 are design history frozen at their point in time. Document 5 is a ratifiable ontology proposal that supersedes several conceptual discussions in documents 2 and 3 at the ontological layer, while documents 2 and 3 remain preserved unchanged as the record of what was known at each point. Document 6 is analytical — it does not itself add ratified product requirements; it identifies where operator judgment is needed. The `operator-decisions/` folder holds the ratified answers to those decisions as they land; each is a durable product-philosophy stake, not an implementation plan.

---

## Known conflicts and follow-up items

The ontology has been preserved without silently amending any prior document. Known conflicts that intentionally remain unresolved:

- **Wizard Step 2 vs Presence dimension.** The shipped spokesperson wizard's Step 2 collects `template + subject + style` for portrait generation. Under `IDENTITY_MODEL_V1.md` §4.2, Presence is an EXPRESSION dimension that should be authored, proposed-and-ratified, or constrained by CORE — not populated from a 4-template palette that mixes visual style with creator role. This conflict is a product-model gap between shipped code and the ratified ontology; it is not silently rewritten here. `CREATE_SPOKESPERSON_WIZARD.md` is unchanged.

- **Teammate model identity slots vs downstream consumption.** The Teammate model has six identity slots on the row (SESSION 232) — `business_brief`, `who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`, `desired_feeling`. Under `IDENTITY_MODEL_V1.md` these map broadly onto Charge, Values, and other CORE dimensions. The audit found that five of these six fields are not currently consumed by any downstream system (K6 script synthesis, realtime document composition, portrait generation, campaigns). This is a wiring gap between ratified design intent (`CUSTOMER_JOURNEY_V1.md` says these slots "shape every video and conversation") and shipped implementation. It is not silently rewritten here.

- **4-template portrait palette (`mascot / founder / coach / local_guide`) vs ontology's compositional principle.** Under `IDENTITY_MODEL_V1.md` §8, identity belongs to the composed pattern, not to a top-level customer choice from a fixed palette. The template palette also mixes visual style (mascot vs photorealistic) with creator role (founder / coach / local_guide) — an abstraction-layer conflict. `CREATE_SPOKESPERSON_WIZARD.md` retains the palette; no silent edit.

- **`CANONICAL_IDENTITY_CONTRACT_V1.md` (visual identity contract) is unmodified.** It operates within the Presence dimension of the ontology and does not conflict with the ontology; it is a specialization. No pointer added to its preface because the contract is a ratified, heavily-referenced 5000-line document and preserving its shape matters more than adding a cross-reference. Readers who reach it via CLAUDE.md's Read-first will already know the ontology exists.

- **`spokesperson` / `Teammate` class term.** The persona review (P-1), the mental model (§4.1), the adversarial review (F5), and `IDENTITY_MODEL_V1.md` (§10 non-scope + Q-η open question about compositional identity) all touch this. **Reframed and ratified 2026-08-08 under OD-4 (Name Primacy):** a universal customer-facing class noun is not a required product concept; the customer's relationship is with the individual creator by chosen name. Where a class reference is used, the language chosen is a communication decision, not a defining product concept. Engineering identifiers (`Teammate` model class, `spokesperson_*` DB / URL / API contracts) and SPA / marketing / documentation copy remain communication decisions rather than product-model conflicts. `§17.1.b`'s ratification of `Teammate` as the code term stands and is orthogonal to OD-4.

- **Situational role.** `IDENTITY_MODEL_V1.md` §5 treats this as a projection rule (Relational disposition + context → situational posture). Shipped code may or may not implement or expose situational-role-adjacent behavior; this is not surveyed here. No conflict recorded because no ratified doc claims to define situational role.

Each item above is a legitimate follow-up work item. None is silently resolved.

**Ontology-vs-ratified-OD relationship notes (2026-08-08):**

- **`IDENTITY_MODEL_V1.md` §7.2 (inter-modal coherence) vs OD-2 (Creator Fidelity).** The ontology's §7.2 names inter-modal coherence as a required invariant for any persistent identity in the abstract. OD-2's ratified product principle is fidelity, not coherence. Where the customer's authored inputs point at a coherent creator, OD-2's fidelity principle produces coherence indirectly. Where the customer's authored inputs contain intentional tension, OD-2's fidelity principle preserves the tension rather than enforcing §7.2's coherence claim. The ontology document is preserved unchanged; the relationship between §7.2 and OD-2 is recorded in the OD-2 artifact and the three-way comparison, not by editing the ontology in place. Future amendment of the ontology (e.g., a V2 that refines §7.2 in light of OD-2's fidelity framing) would be a separate ratification event.

- **`IDENTITY_MODEL_V1.md` GOVERNANCE layer (§4.3 Memory / Continuity contract / Provenance) vs OD-3 (Artifact History).** The ontology's GOVERNANCE layer names the machinery that keeps identity coherent and manages change across time. OD-3 is Character OS's ratified product commitment about how that machinery interacts with produced artifacts: existing artifacts remain historical records of what was created; identity evolution shapes future artifacts and does not silently rewrite historical ones; customer-directed transformation of an existing artifact produces new work and preserves the original. Where the ontology's Continuity contract concept would specify tolerance for identity evolution, OD-3 rules that any such evolution does not by itself silently regenerate, modify, annotate, or invalidate existing artifacts. Where the ontology's Provenance concept spans all identity dimensions, OD-3 rules that artifacts carry the authoring state they were produced against and that authoring state is not retroactively rewritten. The ontology document is preserved unchanged; the relationship is recorded in the OD-3 artifact and the three-way comparison, not by editing the ontology in place.

- **Four ratified operator decisions form a coherent philosophy stack.** OD-1 (Presence Authoring — customers express creative intent; implementation mechanisms stay behind the curtain), OD-2 (Creator Fidelity — Character OS faithfully realizes the customer's authored creator; relevant intent is not silently ignored; explicit choices are not overridden by hidden defaults; intentional tension is preserved), OD-3 (Artifact History — existing artifacts remain historical records; new work may always be created from existing work at customer direction; system inference does not rewrite history), and OD-4 (Name Primacy — Character OS is centered on individual creators, not on a customer-facing class taxonomy; customers primarily relate to each creator by its chosen name) together stake four axes of the same underlying philosophy: *the customer is the authority; Character OS is the faithful producer; the customer's authored intent per individual creator is what the product serves.* OD-1 governs the authoring interface; OD-2 governs the mapping from authoring to artifact; OD-3 governs what happens to artifacts across time as authoring evolves; OD-4 makes explicit the singular-individual-creator framing that all three quietly assumed. The four are non-redundant, non-conflicting, and mutually reinforcing.

- **`IDENTITY_MODEL_V1.md` §10 (customer-facing class term non-scope) vs OD-4 (Name Primacy).** The ontology explicitly non-scoped the customer-facing class term. OD-4 does not amend that non-scope; it makes the non-scope itself the ratified product principle. The ontology names structural properties of persistent identity; it does not require the customer to internalize those properties as class instances. OD-4 confirms that the customer's mental model is anchored at the individual-creator level, not at the ontology-dimension or class-instance level. The ontology document is preserved unchanged; the relationship is recorded in the OD-4 artifact and the three-way comparison.

- **SESSION 171 hardcoded-`coach` re-bake incident anchored under OD-3.** The SESSION 171 corrective (persist `visual_template` on the Teammate row to prevent silent portrait re-bake) is retroactively anchored to OD-3 as the class of system-initiated re-bake that the ratification rules out. Same-customer explicit re-generation (customer asks Character OS to regenerate a portrait with current authoring) is fully supported under OD-3 and is not the SESSION 171 failure mode.

**Additions from the three-way comparison pass (2026-08-08):**

- **Provenance scope (three-way comparison §DA-3).** The ontology's Provenance concept spans all identity dimensions. `CANONICAL_IDENTITY_CONTRACT_V1.md` handles Provenance rigorously for the Presence dimension only (`CharacterIdentityVersion` + `PromotionAudit` + review journal, all shipped per SESSION 249 9.b). Provenance for CORE dimensions (Charge, Values, Worldview, Relational disposition) is unmodeled in both design and shipped code. Not a conflict; a scope-distinction worth naming so future readers do not assume the visual contract covers the whole space.

- **`CREATE_SPOKESPERSON_WIZARD.md` scope note (three-way comparison §DA-4).** The wizard scope-lock (SESSION 123) describes wizard/body creation from its ratification era. Later work — the identity surface (SESSION 232) and the identity ontology (SESSION 250) — expanded the broader product identity model beyond what the wizard doc scopes. The wizard doc's body is preserved unchanged; readers should understand its scope as body-creation-during-onboarding, not as the full identity model.

- **First-draft classification correction (three-way comparison §TC-3 REMOVED).** The first draft of the three-way comparison classified an internal conflict between `CUSTOMER_JOURNEY_V1.md` and `CREATE_SPOKESPERSON_WIZARD.md`. On operator-requested re-read of exact wording, the journey doc's claim ("identity slots shape every video and every conversation") does not extend to portraits; the wizard doc's portrait derivation is orthogonal. The two ratified docs are consistent at the wording level. The ontology's inter-modal coherence requirement is what would extend identity's reach to portraits; that is an ontology-vs-ratified-design tension, not a ratified-vs-ratified one. Methodological lesson: classifications must trace to exact ratified-doc wording, not to what a reader might wish the older doc had said.

- **Persona-review P-8 empirical correction (three-way comparison §DAC-2 + §DA-2).** P-8 claimed operator surfaces are "in the customer nav." On direct SPA inspection during the three-way comparison, only `/settings/provider-status` is footer-linked; `/settings/bootstrap-review` and `/settings/engine-connections` are direct-URL only. Correction note added to `PERSONA_REVIEW_SESSION_250.md`; original body preserved.

---

## How to use this trio-now-quintet in a future session

The reading protocol from the original index still holds. Extended:

1. Read documents 1-4 to ground yourself in the design history that produced the ontology.
2. Read document 5 (`IDENTITY_MODEL_V1.md`) to understand the ontology itself.
3. When any decision touches identity, consult document 5 first for the conceptual model.
4. When any decision touches customer experience, consult documents 1-4 for the evidence base.
5. Before ratifying any change or beginning a three-way comparison (ontology vs ratified design docs vs shipped behavior), acknowledge the known conflicts above.
6. If you revise `IDENTITY_MODEL_V1.md`, produce a V2 with dated reasoning rather than editing V1 in place.

---

## STOP

Reading guide preserved. Extended to include the ontology work. Conflicts recorded. No implementation. No ratification of the ontology. No Step 10 movement.
