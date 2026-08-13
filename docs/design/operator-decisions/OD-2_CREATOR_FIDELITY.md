# OD-2 · Creator Fidelity

**Decision ID:** OD-2
**Title:** Creator Fidelity — the whole authored creator drives every artifact
**Status:** RATIFIED
**Ratified:** 2026-08-08 (SESSION 250)
**Ratifier:** operator
**Scope:** product philosophy for how Character OS's system-produced artifacts relate to what the customer has authored about their creator
**Superseded by:** —
**Companion:** `docs/design/IDENTITY_MODEL_V1.md`, `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` §7 OD-2, `docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md`, `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`

---

## Ratification statement (verbatim, timeless, implementation-agnostic)

### OD-2 RATIFICATION — CREATOR FIDELITY

Character OS's job is fidelity to the customer's authored creator across contexts and modalities.

Each artifact should be shaped by the authored inputs relevant to it — where "relevant" means what the customer would reasonably expect the artifact to draw on, not what the system finds convenient to use. Different modalities may express different facets of the creator without becoming different creators.

Relevant authored intent must not be silently ignored.

Explicit customer choices must not be overridden by hidden implementation defaults. Legitimate overrides are limited to declared safety, legal, and explicitly ratified product constraints.

When the customer's authored inputs are in tension, that tension is part of what the customer expressed. The system honors it; it does not silently smooth divergent inputs into a system-preferred coherence.

The customer does not need to author "fidelity," "coherence," or "coordination between inputs" as concepts; the system's responsibility is faithful realization of what the customer did author.

---

## Why fidelity replaced coherence

An earlier draft of OD-2 (Position D from the initial pressure-test) proposed "system is responsible for coherence" as the primary product principle. An adversarial pass surfaced three material problems with that framing:

- **Coherence privileges one possible quality of a creator over others.** Creators with intentional tension (a stern-looking character with a warm voice; a corporate visual paired with playful behavior; a serious brand with subversive commentary) are legitimate. A system that enforces coherence would strip these creators of the tension that defines them.
- **"Coherence" collapses several distinct concepts into one word.** Identity coherence, stylistic coherence, brand coherence, narrative coherence, and modality coherence are provably distinct. Treating them as one invariant is the same abstraction-level error the template palette committed. The ontology's §7.2 uses "inter-modal coherence" as a specific term; OD-2's earlier draft over-generalized it.
- **Coherence is an outcome, not a mechanism.** Templates were correctly identified as implementation because they're a mechanism. Coherence is a property of the output — more like quality than like a technical choice. Treating coherence as a system responsibility that must be enforced conflates outcome with obligation.

Fidelity is the deeper principle. When the customer authored a coherent creator, fidelity produces coherence. When the customer authored intentional tension, fidelity preserves the tension. When different modalities emphasize different facets, fidelity honors both. Fidelity is what Character OS actually owes; coherence is one thing that can result from fidelity when the customer's authoring points that way.

---

## Sub-principles embedded in the ratification

### Relevant authored intent (not all authored data)

The ratification specifies "relevant" to avoid the failure mode where every artifact tries to encode every dimension of the customer's authoring. A portrait cannot meaningfully express relationship memory. A five-second silent clip cannot express linguistic voice. A text reply cannot express visual Presence. Forcing every artifact to reference every dimension would be technically absurd.

The guardrail against the opposite failure mode — the system deciding everything is "irrelevant" so it can ignore inputs — is embedded in the definition: "relevant" means what the customer would reasonably expect the artifact to draw on, not what the system finds convenient to use. If a customer authored `never_say` guardrails, a reasonable customer expectation is that scripts will honor them. If they authored a specific Presence intent, a reasonable expectation is that portraits will reflect it. The definition of "relevant" is customer-anchored, not system-anchored.

### Explicit intent beats hidden defaults

This is the pattern the current shipped product violates: five of six identity slots authored, none consumed by portrait generation — the customer's explicit inputs silently ignored in favor of a system default. Ratifying "explicit customer choices must not be overridden by hidden implementation defaults" protects against recurrence.

The distinction between hidden defaults (bad) and declared constraints (legitimate) is load-bearing. A safety refusal, a legal-constraint moderation, or a Character-OS-ratified product commitment are not hidden defaults — they are public product boundaries the customer can know about. Hidden defaults are what happens when the system quietly fills a gap with an inference the customer never authorized. Legitimate overrides are declared, documented, and applied consistently.

### Intentional tension is preserved

Some creators exist because their tension is the point. The system does not smooth authored tension into a system-preferred harmony. If the customer's inputs express contradiction, fidelity means the contradiction is realized, not resolved.

This distinguishes fidelity from coherence-enforcement decisively. A coherence-enforcing system would treat tension as a bug; a fidelity-honoring system treats it as an intentional feature when authored deliberately.

### Declared exceptions for safety, legality, and explicitly ratified product constraints

Character OS retains the right to refuse or modify output for:

- **Safety** — harm to users or third parties
- **Legality** — jurisdiction-specific requirements, IP constraints, platform-mandated restrictions
- **Explicitly ratified product constraints** — Character OS's own declared commitments about what it will and will not produce

These exceptions are:

- Public — the customer can know about them (even if they didn't know they'd hit one)
- Consistent — applied the same way across customers, not arbitrary
- Not silent implementation defaults — a legitimate override is a declared constraint, not a system convenience

---

## Explicit non-decisions

OD-2 deliberately does NOT decide:

- How the system determines "relevance" per artifact in practice
- How the system integrates multiple authored inputs when producing a single artifact
- How conflicts between explicit authored inputs are handled operationally (does the system compose, propose, ask for clarification, prioritize by artifact context, etc.)
- How relevant subsets of authored inputs are surfaced to any generation mechanism (prompt composition, image conditioning, LoRA, RAG, agentic composition, or future techniques)
- What Character OS's specific safety / legal / product-constraint list contains
- The threshold or definition for "silently ignored" or "hidden defaults" in operational terms
- Temporal continuity — whether editing an authored input causes downstream artifacts to be regenerated, warned about, or left alone (properly the domain of a future OD)
- Database schema, API surface, wizard flow, UI, provider selection, migration sequencing, or any other implementation concern

The specific mechanism belongs to design and implementation. The ratification is a product-philosophy stake, not a build plan.

---

## Relationship to OD-1

OD-1 established that customer-facing Presence authoring is driven by creative intent, not a required fixed template palette. OD-2 extends that discipline: not only is Presence not authored via a template palette, but Presence is also not authored in isolation from the rest of the customer's authoring. The customer's Presence intent is one input among several relevant inputs; other CORE-adjacent authoring (identity slots, personality, tone) also legitimately shapes Presence artifacts where relevant.

Together OD-1 + OD-2 establish two related product-philosophy stakes:

- **OD-1:** the customer authors Presence through intent, not through a required implementation-derived palette
- **OD-2:** the whole of what the customer authored (not any single input alone; not a system-enforced coherence over inputs) drives every artifact the system produces

OD-2 does not weaken OD-1 or change its scope. Templates remain implementation scaffolding per OD-1; whether the internal mechanism uses templates, image conditioning, LoRA, or something else to integrate authored inputs into Presence artifacts is unspecified by both ratifications.

---

## Relationship to `IDENTITY_MODEL_V1.md` §7.2 (inter-modal coherence)

The ontology's §7.2 names inter-modal coherence as a required invariant for any persistent identity: *"When multiple modalities are combined (voice + portrait; video with narration; live conversation with visible presence), they must project the same CORE consistently."*

OD-2 does **not** ratify inter-modal coherence as the controlling product principle. It ratifies fidelity instead. The relationship between the two is:

- The ontology's §7.2 states a general property of identity coherence in the abstract. It is preserved in the ontology as ontological reference material.
- OD-2 is Character OS's ratified product decision about what Character OS commits to producing. OD-2 chooses fidelity as the controlling principle because fidelity handles both coherent creators (where the customer authored coherence) and tension-carrying creators (where the customer authored tension), while coherence-as-invariant handles only the first.
- Where the customer's authored inputs point at a coherent creator, OD-2's fidelity principle produces a coherent creator — indirectly satisfying the ontology's §7.2 in that case.
- Where the customer's authored inputs contain intentional tension, OD-2's fidelity principle preserves the tension — deliberately not satisfying the strong form of §7.2, on the grounds that the strong form was over-general.

The ontology document itself is not being amended by this ratification. `IDENTITY_MODEL_V1.md` remains an implementation-agnostic ontology reference. The way to read the two together: the ontology names structural properties of persistent identity in general; OD-2 records Character OS's specific product commitment about what it produces on the customer's behalf. Where they diverge (intentional tension), OD-2 governs Character OS's behavior.

If the operator later decides to amend the ontology to reflect this refinement, that would be a separate ratification event. The current record is: OD-2 supersedes the ontology's §7.2 as the controlling product principle for Character OS's behavior; the ontology remains preserved unchanged as reference material with this cross-reference documented here and in the three-way comparison.

---

## Effect on existing documentation

- `docs/design/IDENTITY_MODEL_V1.md` — **preserved unchanged.** The §7.2 inter-modal coherence description remains as ontological reference material. The relationship between §7.2 and OD-2 is recorded here (this file) and in the three-way comparison, not by editing the ontology in place.
- `docs/design/IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md` — updated to mark OD-2 as RATIFIED with a pointer to this file.
- `docs/design/CUSTOMER_EXPERIENCE_REVIEW_INDEX.md` — updated to record OD-2 ratification in the chronology and reading order.
- `docs/design/CUSTOMER_JOURNEY_V1.md` — unchanged. The journey doc's identity-slot discussion is orthogonal at the product-philosophy level; OD-2's principle applies to how the system uses those slots but doesn't require editing the journey doc's description of them.
- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` — unchanged. Wizard doc body preserved as historical evidence from its SESSION 123 era, per OD-1's preservation discipline.
- `docs/design/CANONICAL_IDENTITY_CONTRACT_V1.md` — unchanged. Visual identity substrate contract operates within OD-2's principle regardless of how CORE inputs relate to Presence.
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

**Current shipped gap.** Character OS's shipped portrait pipeline (`/api/spokespeople/generate-portrait/` → `/internal/portrait/` → `character_studio_client.build_prompt()`) consumes only `template + subject + style` as inputs and does not read any CORE-adjacent identity fields (`who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`, `desired_feeling`, and mostly not `business_brief` or `personality` either for the portrait specifically). This is the primary silent-ignoring pattern OD-2 rules out as the target product philosophy. It is transitional and continues to accurately describe shipped behavior. The ratification does not require it be resolved on any specific timeline; the ratification is what future implementation work builds against.

**K6, ask, realtime.** These flows already consume a partial CORE subset (`name + business_brief + personality + tone_archetype` variably per flow). They are closer to OD-2 compliance than portrait generation but still narrow. Whether they qualify as "faithful realization" today is a subjective judgment; the ratification governs future direction.

**No mechanism prescription.** OD-2 does not require any specific mechanism for integrating authored inputs. Prompt composition, image conditioning, LoRA, RAG, agentic composition, and future techniques are all valid mechanisms as long as they serve the ratified principle.

**No sequencing.** Whether the shipped state is corrected via a wizard/pipeline evolution, an alternative interface, a phased identity-slot rollout, or some other path is deferred to design and implementation. The ratification is not itself a build plan.

---

## STOP

OD-2 durably recorded. Ratified principle is timeless and implementation-agnostic. Transitional notes are separate. Ontology §7.2 relationship is recorded here without editing the ontology.
