# OD-4 · Name Primacy

**Decision ID:** OD-4
**Title:** Name Primacy — the customer's relationship is with the individual creator, not with a class
**Status:** RATIFIED
**Ratified:** 2026-08-08 (SESSION 250)
**Ratifier:** operator
**Scope:** product philosophy for how Character OS relates to the customer's mental model of what they create — specifically, whether a universal customer-facing class noun is a required product concept
**Superseded by:** —
**Companion:** `docs/design/IDENTITY_MODEL_V1.md`, `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` §7 OD-4, `docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md`, `docs/design/operator-decisions/OD-2_CREATOR_FIDELITY.md`, `docs/design/operator-decisions/OD-3_ARTIFACT_HISTORY.md`, `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`

---

## Ratification statement (verbatim, timeless, implementation-agnostic)

### OD-4 RATIFICATION — NAME PRIMACY

Character OS is centered on individual creators, not on a customer-facing class taxonomy.

Customers primarily relate to each creator by its chosen name. A universal customer-facing class noun is not required for the product to function or for the customer to form a coherent mental model.

Where a class reference is used, the language chosen is a communication decision, not a defining product concept.

---

## Why this exists

The three prior ratified operator decisions all quietly assumed name-primacy without ever stating it:

- **OD-1** centers *the customer's authored creator* — a singular authored entity, not a Teammate configuration or a class instance.
- **OD-2** obligates fidelity to *what the customer authored* for their creator — again, a singular authored entity.
- **OD-3** protects *artifacts once they are produced* as belonging to the moment they were produced by that creator — again, singular.

None of the three ratifications makes sense if Character OS's product concept is a class of creators that customers pick from a taxonomy. Each ratification makes clean sense when the customer's product concept is an individual creator with a name the customer chose.

The class-noun question ("what should Character OS call this thing?") was raised repeatedly in the SESSION 250 design history and was left UNRESOLVED across all three layers of documentation. OD-4 does not answer *what word to use*; it answers the prior question of *whether a word is required as a product concept*. The answer is no.

The narrower question ("if a word is used, which word?") is a communication decision that can be made per surface, per audience, per era, without disturbing the ratified philosophy.

---

## Design history

The class-noun question surfaced at five distinct points during SESSION 250 without ever resolving into a "which word" answer:

1. **`PERSONA_REVIEW_SESSION_250.md` P-1** — simulated personas showed no shared expectation of a class term; each persona related to what they'd built by its chosen name or by its purpose.
2. **`CUSTOMER_MENTAL_MODEL_V1.md` §4.1** — proposed a direction in which the creator's chosen name carries the primary customer relationship. Recorded as a candidate direction, not ratified.
3. **`CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` F5** — critique concluded that a universal class noun is "probably not needed" as a substantive design finding, not a punt.
4. **`IDENTITY_MODEL_V1.md` §10** — explicitly non-scoped the customer-facing class term, marking it as a product decision separate from the ontology.
5. **`IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` §2 F10** — classified UNRESOLVED across all three layers (ontology / ratified design / shipped behavior).

The convergence across five separate design artifacts — all reaching the same "not required" or "unresolved" conclusion — was the pattern OD-4 crystallizes. What earlier discussions read as an unresolved *naming* question was actually a resolved *necessity* question hiding underneath: the class noun's necessity was never established, so no naming choice needed to be made.

An adversarial pass during OD-4 review explicitly tested whether the ratification should also constrain UI wording, marketing language, engineering identifiers, or documentation conventions. It should not. Editorial policy is not product philosophy; freezing it in a ratification would over-constrain future product work and would not survive predictable evolution of UI copy, marketing tone, engineering refactors, or documentation audience. The ratification therefore stops at the product-philosophy layer and returns downstream questions to communication decisions where they belong.

An earlier OD-4 draft embedded examples of candidate class terms and enumerated engineering / marketing / documentation channels within the ratification body. That draft was tightened by roughly half on operator review, on the grounds that examples date, editorial policy evolves, and only the timeless product-philosophy claim belongs in the ratified statement.

---

## Relationship to OD-1, OD-2, OD-3

OD-4 is the fourth axis of the same underlying philosophy the prior three stake:

- **OD-1 (Presence Authoring).** Customers express creative intent; implementation mechanisms stay behind the curtain.
- **OD-2 (Creator Fidelity).** Character OS faithfully realizes the customer's authored creator; relevant intent is not silently ignored.
- **OD-3 (Artifact History).** Existing artifacts remain historical records; new work may always be created from existing work at customer direction.
- **OD-4 (Name Primacy).** The customer's relationship is with the individual creator, not with a class taxonomy.

Each stake protects a different failure mode from the same class of overreach — the product forcing its own internal taxonomy onto the customer's mental model. OD-1 protects against required template palettes; OD-2 protects against required system-coherence framing; OD-3 protects against system-inferred rewriting of history; OD-4 protects against a required class-noun taxonomy.

The common thread across the four: *the customer is the authority; Character OS is the faithful producer; the customer's authored intent per individual creator is what the product serves.* Every prior ratification quietly assumed the singular-individual-creator framing; OD-4 makes it explicit so future work cannot silently regress toward a class-taxonomy-first product model.

OD-4 does not weaken OD-1, OD-2, or OD-3. It is the substrate assumption they all rest on, now stated directly.

---

## Relationship to `IDENTITY_MODEL_V1.md`

The ontology explicitly non-scoped the customer-facing class term (§10). OD-4 does not amend that non-scope; it makes the non-scope itself the ratified product principle. The ontology names structural properties of persistent identity; it does not require the customer to internalize those properties as class instances. OD-4 confirms that the customer's mental model is anchored at the individual-creator level, not at the ontology-dimension or class-instance level.

The ontology document is preserved unchanged. OD-4 is Character OS's specific product commitment that follows naturally from §10's non-scope: the class-noun question was never a required product decision to begin with; the individual creator is the customer-facing unit.

---

## Explicit non-decisions

OD-4 deliberately does NOT decide:

- The specific words used in any current SPA surface.
- Whether existing URL paths, engineering identifiers, or persistence identifiers change, remain, or are eventually superseded.
- Marketing language, positioning, or class terminology used in customer acquisition materials.
- Documentation language conventions for customer-help vs technical vs internal contexts.
- Whether Character OS eventually adopts a formal class term in a distinct product-model layer for future features (e.g., plural aggregate views, cross-creator flows, ensemble constructs).
- Migration, copy-rewrite, or rename sequencing for any current surface where a class term already appears.
- The specific words used at pre-naming moments in creation flows, in empty states, in aggregate list labels, or in onboarding copy.
- Whether Character OS uses different class references in different contexts (per surface, per audience, per era) or maintains consistency within any defined scope.
- Whether any current surface's class-reference usage needs to change to align with this ratification (the ratification governs product philosophy, not current shipped copy).

All of the above are communication decisions. The ratification is a product-philosophy stake, not a copy guide.

---

## Current shipped context (separate from the ratified principle above)

*These notes describe current shipped state and transitional considerations. They are not part of the ratified principle. The ratified principle above is timeless and implementation-agnostic.*

**Engineering identifiers.** The Django model class is `Teammate` (renamed from `Spokesperson` in SESSION 240 per Canonical Identity Contract §17.1.b). Persistence identifiers remain `spokesperson_*` (Django app label, DB table, DB constraints, URL paths, router basename, FK field names, response payload keys, error codes). These are engineering identifiers, not customer-facing product concepts, and OD-4 does not require them to change. Their eventual disposition is a communication and refactor decision, not a ratification decision.

**SPA copy state.** The current SPA mixes engineering-derived class references (in URLs and some copy) with `{name}` interpolation (three-way comparison F9 confirmed name-primacy is already the dominant pattern in customer-visible copy). This is consistent with OD-4 at the product-philosophy level; specific SPA copy choices remain communication decisions.

**Marketing and documentation.** Not surveyed for this ratification. Whatever class terminology those channels currently use continues to be a communication decision, not a defining product concept.

**Future product surfaces.** OD-4 does not preclude Character OS from introducing new product surfaces that involve plural aggregates, ensembles, or cross-creator flows. It requires only that any such surface not be introduced as a required customer-facing class taxonomy at the individual-creator level. Aggregate constructs are distinct product concepts and may be ratified separately if and when they arise.

**No sequencing.** Whether SPA copy, URL paths, engineering identifiers, marketing language, or documentation conventions evolve toward or away from any specific class term is deferred to design and implementation. The ratification is not a rename plan.

---

## Effect on existing documentation

- `docs/design/IDENTITY_MODEL_V1.md` — **preserved unchanged.** The §10 non-scope of the customer-facing class term remains as ontological reference material. OD-4 is Character OS's specific product commitment that follows naturally from that non-scope.
- `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` — updated to mark the universal-class-noun matrix row and the OD-4 operator decision as RATIFIED with a pointer to this file.
- `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` — updated to record OD-4 ratification in the chronology and reading order.
- `docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md`, `OD-2_CREATOR_FIDELITY.md`, `OD-3_ARTIFACT_HISTORY.md` — unchanged. OD-4 makes explicit the name-primacy assumption they all quietly rest on but does not amend their ratified text.
- `docs/design/CUSTOMER_JOURNEY_V1.md` — unchanged. Copy interpolates `{name}` universally per its own ratified pattern; OD-4 confirms this pattern as the product-philosophy baseline.
- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` — unchanged. Wizard doc body preserved as historical evidence.
- `docs/design/CANONICAL_IDENTITY_CONTRACT_V1.md` — unchanged. §17.1.b's ratification of `Teammate` as the code term is orthogonal to OD-4; engineering identifiers are not customer-facing product concepts per OD-4.
- Historical design-history quartet (persona review, mental model, adversarial review) — unchanged. Preserved as historical artifacts that led to OD-4.

---

## Amendment protocol

If the operator later decides to change this ratification:

- Amendment must be an explicit operator ratification event, not a silent edit.
- A superseding operator decision (OD-N) is preferred over amending this file in place.
- If this file is amended, add a dated amendment note at the bottom and preserve the prior ratification statement verbatim above it.
- Any amendment must be recorded in `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` chronology.

---

## STOP

OD-4 durably recorded. Ratified principle is timeless and implementation-agnostic. Editorial and communication decisions are explicitly non-decisions. Ontology §10 non-scope preserved unchanged. The four ratified operator decisions (OD-1 Presence Authoring, OD-2 Creator Fidelity, OD-3 Artifact History, OD-4 Name Primacy) form a coherent product-philosophy stack.
