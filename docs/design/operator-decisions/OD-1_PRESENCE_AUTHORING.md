# OD-1 · Presence Authoring

**Decision ID:** OD-1
**Title:** Presence Authoring — customer-facing Presence is driven by creative intent
**Status:** RATIFIED
**Ratified:** 2026-08-08 (SESSION 250)
**Ratifier:** operator
**Scope:** product philosophy for customer-facing Presence authoring
**Superseded by:** —
**Companion:** `docs/design/IDENTITY_MODEL_V1.md`, `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` §7 OD-1, `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`

---

## Ratification statement (verbatim)

### OD-1 RATIFICATION — PRESENCE AUTHORING

Character OS ratifies that customer-facing Presence authoring is driven by the customer's creative intent, not by a required fixed template palette.

Visual templates are implementation scaffolding and/or optional authoring aids, not a required product abstraction the customer must understand in order to create a persistent identity.

Character OS may:

- use templates internally,
- derive or select templates automatically,
- offer templates as optional shortcuts,
- expose template controls to advanced users,

provided none of those mechanisms becomes a required translation layer between the customer's intent and the creator they are trying to author.

The current `mascot` / `founder` / `coach` / `local_guide` palette therefore remains valid as existing implementation scaffolding during transition, but it is no longer ratified as the required or primary customer-facing model for Presence.

The mechanism may continue to persist internally for regeneration/re-bake continuity.

This ratification deliberately does NOT decide:

- the replacement Presence-authoring UI,
- whether the current four templates remain long-term,
- whether templates are eventually hidden completely,
- how intent is captured,
- how Character OS derives visual scaffolding from that intent,
- database/schema changes,
- migration sequencing.

The product principle is simply:

> *Customers express what they want their creator to be and feel like; Character OS handles the scaffolding needed to produce it.*

---

## Context — what this decision resolves

- The three-way comparison's TC-1 (visual-template palette as ratified design vs ontology compositional principle) is resolved as a product-level judgment.
- The three-way comparison's TC-2 (portrait derivation from CORE identity) is NOT resolved by this decision; that remains OD-2.
- `CREATE_SPOKESPERSON_WIZARD.md` Contract rule 5 (templates as pre-fill/archetype defaults) continues to accurately describe shipped behavior during any transition; it is superseded in intent for its specific claim that templates are the required or primary customer-facing abstraction. The wizard doc body is preserved unchanged as historical evidence from its SESSION 123 ratification era.

## Design-history that informed the decision

- `docs/design/IDENTITY_MODEL_V1.md` — §4.2 Presence, §6 Specification framework (including the "Proposed and ratified" pattern), §8 Compositional identity principle
- `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` — TC-1 (visual-template palette), F2 (persona-review palette-fit distortion), §Q4 (abstraction-level mixing analysis)
- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` — Contract rule 5 (templates pre-fill; archetypes default; ratified SESSION 123)
- `docs/design/CUSTOMER_MENTAL_MODEL_V1.md` + adversarial review — F5 (universal class-noun question) and object-model discussion
- `docs/design/PERSONA_REVIEW_SESSION_250.md` — P-1 (persona noun/palette misfit signal, simulated evidence)
- SESSION 171 (Character OS engineering history) — persisted `visual_template` field on `Teammate` row enables re-bake continuity; a bug where re-bake hardcoded "coach" flipped Marcus from a stylized battle unicorn to a photorealistic human. The persistence mechanism this decision preserves is the same one that fix introduced.
- SESSION 123 (Character OS engineering history) — original template palette solving blank-page cognitive load; ratified per its era. This decision preserves the blank-page-mitigation goal while releasing the palette-as-primary implementation of it.
- Analogy to provider treatment — Character OS already treats providers (Runway, Stability, OpenAI) as important internally but not customer-facing choices. OD-1 extends the same treatment to templates.

## What this decision deliberately does not do

- Does not design the replacement Presence-authoring UI.
- Does not decide whether the current four templates (`mascot / founder / coach / local_guide`) remain long-term.
- Does not decide whether templates are eventually hidden completely.
- Does not specify how creative intent is captured (description, reference image, brand context inference, structured intent capture, LLM-assisted extraction, or any other technique).
- Does not specify how Character OS derives visual scaffolding from that intent.
- Does not touch database or schema.
- Does not specify migration sequencing (whether the current palette remains in a transitional state until an alternative interface is designed, or whether an alternative interface is designed before the current palette is retired).
- Does not resolve OD-2 through OD-5.

## Effect on existing documentation

- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` — Contract rule 5's specific claim that templates are the required or primary customer-facing abstraction is superseded in intent. The doc body is preserved unchanged as historical evidence. The rule continues to accurately describe shipped wizard behavior during any transition.
- `docs/design/IDENTITY_MODEL_V1.md` — unchanged. This ratification is a downstream product-model choice; the ontology itself is upstream.
- `docs/design/CANONICAL_IDENTITY_CONTRACT_V1.md` — unchanged. The visual identity substrate contract operates within the Presence dimension regardless of how Presence is authored at the customer-facing layer.
- `docs/design/CUSTOMER_JOURNEY_V1.md` — unchanged. The journey doc's identity-slot discussion is orthogonal to this decision.
- `docs/design/CUSTOMER_MENTAL_MODEL_V1.md` and its adversarial review — unchanged; preserved as historical design-history evidence.
- `docs/design/PERSONA_REVIEW_SESSION_250.md` — unchanged; preserved as historical simulated-persona probe.

## Amendment protocol

If the operator later decides to change this ratification:

- Amendment must be an explicit operator ratification event, not a silent edit.
- A superseding operator decision (OD-N) is preferred over amending this file in place.
- If this file is amended, add a dated amendment note at the bottom and preserve the prior ratification statement verbatim above it.
- Any amendment must be recorded in `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` chronology.

## Downstream sequencing note

Ratification of OD-1 does not itself trigger implementation. The ratification is a product-philosophy stake that future design and implementation work can build against. The next operator decisions (OD-2 through OD-5) may be reviewed in any order the operator chooses; each is a separate judgment.

---

## STOP

OD-1 durably recorded. No implementation. No UI design. No database changes. No migration sequencing. The ratification is a philosophy stake, not a build plan.
