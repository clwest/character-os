# OD-3 · Artifact History

**Decision ID:** OD-3
**Title:** Artifact History — existing artifacts are historical records; new work may always be created from them
**Status:** RATIFIED
**Ratified:** 2026-08-08 (SESSION 250)
**Ratifier:** operator
**Scope:** product philosophy for how Character OS treats artifacts once they have been produced — the boundary between history and new work
**Superseded by:** —
**Companion:** `docs/design/IDENTITY_MODEL_V1.md`, `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` §7 OD-3, `docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md`, `docs/design/operator-decisions/OD-2_CREATOR_FIDELITY.md`, `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`

---

## Ratification statement (verbatim, timeless, implementation-agnostic)

### OD-3 RATIFICATION — ARTIFACT HISTORY

Character OS produces every artifact with fidelity to what the customer authored at the moment of generation. An artifact, once produced, belongs to the moment it was produced.

Existing artifacts remain historical records of what was created. Identity edits shape future artifacts; they do not silently modify, regenerate, annotate, or invalidate existing ones.

New artifacts may be created from existing artifacts whenever the customer directs — to rewrite a script, produce a new version, regenerate a portrait, translate an article, turn a blog post into a video, or any other creative act. In every such case, Character OS faithfully produces new work at the customer's direction. The original artifact remains as it was produced. Creating new work from existing work is not modification of history.

The customer retains full agency over their historical work — to preserve it, to derive new work from it, to retire it, or to take any other action they choose. These are customer-driven decisions, not system-driven consequences of authoring changes. The system does not require the customer to manage "up-to-date-ness" or reconcile old artifacts against current authoring as a routine operation.

This principle applies to artifacts once they are complete. Artifacts in progress at the moment of an edit naturally continue with current authoring as the work proceeds; this is not retroactive modification.

---

## Why "artifact history" replaced "identity-edit reprojection" as the framing

An earlier framing of this operator decision (OD-5 in the original three-way comparison list) centered on identity edits and downstream reprojection: *should identity edits trigger regeneration or warnings on downstream artifacts?* That framing centered the wrong subject.

Two problems surfaced under adversarial pressure:

- **Centering "identity edits" makes the customer's own creative acts look adjacent to the principle instead of central to it.** The real subject is authority over existing work. Identity edits are one occasion when that authority is tested; customer-directed transformation of a specific artifact is another; other future occasions may arise. All three are governed by the same principle: history is what was authored; new work is what is being authored now.
- **"Reprojection" is an implementation verb.** It presumes a mechanism — regeneration, propagation, annotation — before the product question is settled. The product question is simpler and more durable: who has authority over an existing artifact, and what happens to that artifact when authoring changes or when the customer directs new work.

The reframed principle handles every scenario the operator pressure-tested:

- *"Rewrite this script."* — the original remains; new work is produced.
- *"Make Version 2."* — the original remains; new work is produced.
- *"Regenerate this portrait with my updated creator."* — the original remains; new work is produced.
- *"Update this presentation."* — the original remains; new work is produced.
- *"Translate this article."* — the original remains; new work is produced.
- *"Turn this blog post into a video."* — the original remains; new work is produced.

None of these are modifications. Every one is the creation of a new artifact using another artifact as source material. The distinction between *system-inferred rewriting of history* (prohibited) and *customer-directed creation of new work from existing work* (fully supported) is the actual product philosophy.

---

## Sub-principles embedded in the ratification

### History is what the customer authored at the moment of production

An artifact's fidelity is measured against the authoring state at the time it was produced, not against later authoring. This closes the trap where "current authoring" retroactively becomes the standard by which historical artifacts are judged inadequate. A script written last month is not "stale" because identity has since evolved; it is what the customer authored last month.

This sub-principle aligns exactly with OD-2's fidelity principle. OD-2 established that fidelity is to what the customer authored; OD-3 extends the same principle across time — fidelity is to what the customer authored at the moment of generation, and it does not decay retroactively because authoring later changed.

### No silent modification, regeneration, annotation, or invalidation

The four verbs enumerate the failure modes the ratification prohibits:

- **Modify** — the system changes the artifact's content in place.
- **Regenerate** — the system replaces the artifact by re-running its generation with current authoring.
- **Annotate** — the system marks the artifact as "outdated" or attaches metadata indicating it no longer matches current authoring.
- **Invalidate** — the system marks the artifact as no longer valid or presents it as such to the customer.

All four are prohibited when triggered by system inference (e.g., "the customer edited identity, therefore this artifact should be marked stale"). The word *silently* is load-bearing: an action driven by the customer's own explicit direction is not silent and is not prohibited.

### The customer's own actions are always permitted

The customer may do anything they choose with their own work — including asking Character OS to create new artifacts from existing ones. Every such customer-directed action produces new work; the original remains. This makes customer agency and history-preservation the same principle, not two competing ones.

### The customer is not made responsible for reconciliation

A system that requires the customer to routinely audit their historical work against current authoring — to decide, per artifact, whether it should be re-baked to stay current — has quietly shifted an implementation problem onto the customer. OD-3 refuses that shift. Reconciliation is not a routine customer task. When the customer wants to update past work, they do so through explicit creative direction, not through a housekeeping obligation the system imposes.

### In-progress work is not retroactively modified

If the customer edits identity mid-generation, the in-progress artifact naturally continues with the current authoring — because current authoring *is* the state at the moment of generation for that artifact. This is not retroactive modification; it is generation-time fidelity. The ratification applies to *completed* artifacts.

---

## Explicit non-decisions

OD-3 deliberately does NOT decide:

- The UI for viewing, deriving from, or retiring historical artifacts.
- Whether the customer sees an "authoring state at time of generation" record alongside each artifact.
- Whether "derived from" provenance is surfaced to the customer, and how.
- Storage model, versioning schema, or database changes required to preserve history.
- Whether creating a new artifact from an existing one uses the same recipe / composition / model as the original, or whether the customer selects fresh.
- Migration sequencing for any existing shipped surface that currently violates this principle.
- Whether legacy behaviors (SESSION 171 hardcoded re-bake path, or any other silent regeneration) require immediate deprecation or transitional shims.
- How Character OS surfaces the existence of historical artifacts to the customer over long time horizons (archival, search, discovery).
- Whether the customer is offered proactive prompts to derive new work from historical work; and if so, on what triggers.

The specific mechanism belongs to design and implementation. The ratification is a product-philosophy stake, not a build plan.

---

## Relationship to OD-1 and OD-2

The three operator decisions ratified in SESSION 250 form a coherent philosophy stack:

- **OD-1 (Presence Authoring).** Customers express creative intent. Implementation mechanisms — including but not limited to templates — stay behind the curtain.
- **OD-2 (Creator Fidelity).** Character OS faithfully realizes the customer's authored creator. Relevant authored intent is not silently ignored; explicit choices are not overridden by hidden defaults; intentional tension is preserved.
- **OD-3 (Artifact History).** Artifacts faithfully represent what was authored when they were created. Existing artifacts remain historical records. New work may always be created from existing work at customer direction. System inference does not rewrite history.

Each ratification stakes a different axis of the same underlying philosophy: *the customer is the authority; Character OS is the faithful producer.* OD-1 governs the authoring interface; OD-2 governs the mapping from authoring to artifact; OD-3 governs what happens to artifacts across time as authoring evolves.

OD-3 does not weaken OD-1 or OD-2. It extends OD-2's fidelity principle across time (fidelity is to what the customer authored *at the moment of generation*, and fidelity does not retroactively demand re-baking) and does not touch OD-1's authoring-interface stake.

---

## Relationship to `IDENTITY_MODEL_V1.md` — GOVERNANCE dimension

The ontology's GOVERNANCE layer (§4.3) names Memory, Continuity contract, and Provenance as identity-machinery dimensions. OD-3 is Character OS's ratified product principle governing how these dimensions interact with produced artifacts.

- **Provenance.** The ontology names Provenance as authoring event + amendment authority + change history for any dimension. OD-3 ratifies that this history is preserved and never silently rewritten; artifacts carry the authoring state they were produced against.
- **Continuity contract.** The ontology names Continuity contract as tolerance specifications per dimension (what may change; what must not; how much drift is allowed). OD-3 does not itself define continuity tolerances; it defines how continuity handling relates to already-produced artifacts. Even if a future continuity contract specified that certain identity dimensions may evolve freely, OD-3 rules that such evolution does not silently rewrite existing artifacts.
- **Memory (creator-history + relationship).** The ontology's memory dimensions are additive — new memory accumulates across sessions. OD-3 governs the artifact side of that accumulation: memory formation is forward-going; historical artifacts do not retroactively acquire new memory-derived content because memory later changed.

The ontology document is not amended by this ratification. `IDENTITY_MODEL_V1.md` remains an implementation-agnostic ontology reference. OD-3 is Character OS's specific product commitment about how GOVERNANCE-layer identity evolution relates to already-produced artifacts.

---

## Relationship to SESSION 171 — the hardcoded re-bake incident

SESSION 171 (Character OS engineering history) documented a bug where a re-bake operation hardcoded the `coach` template, flipping Marcus from a stylized battle unicorn to a photorealistic human. That was a system-initiated re-bake governed by system-side logic, not a customer-directed transformation. The customer had not asked for it and had no explicit path to consent to it.

Under OD-3, that class of behavior is prohibited: silent regeneration of an existing artifact, driven by system logic rather than customer direction, is exactly the failure mode the ratification rules out. The corrective SESSION 171 shipped (persist `visual_template` on the row to preserve continuity) remains valid; OD-3 provides the deeper product-philosophy justification for why that class of silent regeneration must not recur.

If the same customer asked Character OS to *regenerate this portrait with my current creator*, that would be a customer-directed action: the original remains, and Character OS faithfully produces new work at the customer's direction. That is not the SESSION 171 failure mode.

---

## Effect on existing documentation

- `docs/design/IDENTITY_MODEL_V1.md` — **preserved unchanged.** The GOVERNANCE layer (§4.3) remains as ontological reference material. OD-3 is Character OS's specific product commitment about how the ontology's GOVERNANCE dimensions relate to already-produced artifacts.
- `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` — updated to mark the identity-edit-reprojection row and the OD-3 operator decision as RATIFIED with a pointer to this file.
- `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` — updated to record OD-3 ratification in the chronology and reading order.
- `docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md` — unchanged.
- `docs/design/operator-decisions/OD-2_CREATOR_FIDELITY.md` — unchanged. OD-3 extends OD-2's fidelity principle across time but does not amend OD-2's ratified text.
- `docs/design/CUSTOMER_JOURNEY_V1.md` — unchanged. The journey doc's identity-slot discussion is orthogonal at the product-philosophy level.
- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` — unchanged. Wizard doc body preserved as historical evidence.
- `docs/design/CANONICAL_IDENTITY_CONTRACT_V1.md` — unchanged. The visual identity substrate's version-supersede handling (`CharacterIdentityVersion` + `PromotionAudit` + review journal) is consistent with OD-3's history-preservation stance for the Presence dimension.
- Historical design-history quartet (persona review, mental model, adversarial review) — unchanged. Preserved as historical artifacts.

---

## Amendment protocol

If the operator later decides to change this ratification:

- Amendment must be an explicit operator ratification event, not a silent edit.
- A superseding operator decision (OD-N) is preferred over amending this file in place.
- If this file is amended, add a dated amendment note at the bottom and preserve the prior ratification statement verbatim above it.
- Any amendment must be recorded in `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` chronology.

---

## Transition / context notes (separate from the ratified principle above)

*These notes describe current shipped state and transitional considerations. They are not part of the ratified principle. The ratified principle above is timeless and implementation-agnostic.*

**Current shipped state, portrait re-bake.** The SESSION 171 corrective (persist `visual_template` on the Teammate row) prevents the specific hardcoded-`coach` re-bake pathology. Whether other silent-regeneration paths exist across the current codebase (SPA + Django + media-engine) has not been surveyed in service of this ratification; the ratification is what future implementation work builds against.

**Current shipped state, downstream artifact behavior on identity edit.** Identity slots are editable at `/spokespeople/{id}/identity`. Downstream artifacts (K6 scripts, portraits, videos, campaigns) are not currently invalidated, re-baked, annotated, or warned about when identity is edited. Shipped behavior is silent-on-both-sides: nothing regenerates, and nothing tells the customer that older artifacts were produced under prior authoring. Under OD-3, the silent-regeneration side is correct as a product principle (no silent rewriting of history); the silent-on-authoring-state side is not resolved by OD-3 (whether the customer sees "produced against authoring state X" metadata is an explicit non-decision above).

**No mechanism prescription.** OD-3 does not require any specific storage model, provenance schema, UI treatment, or migration sequence. Whether historical artifacts carry snapshots of authoring state, whether "derived from" links are exposed, whether the customer can browse authoring history — all deferred to design and implementation.

**No sequencing.** Whether existing silent-regeneration paths (if any beyond the SESSION 171 fix) are deprecated immediately, in a phased rollout, or retained transitionally is deferred. The ratification governs future direction.

**Relationship to `CANONICAL_IDENTITY_CONTRACT_V1.md`.** The visual identity contract's supersede semantics — `CharacterIdentityVersion` rows persist across amendments, `PromotionAudit` records the promotion event, the review journal is append-only — are consistent with OD-3's history-preservation stance for the Presence dimension. No amendment required.

---

## STOP

OD-3 durably recorded. Ratified principle is timeless and implementation-agnostic. Transitional notes are separate. GOVERNANCE-layer ontology relationship recorded without editing the ontology. SESSION 171 relationship recorded as product-philosophy anchor for the corrective shipped there.
