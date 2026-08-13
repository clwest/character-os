# IDENTITY_MODEL_V1 — Three-Way Comparison

**Status:**
- Analytical companion to [`IDENTITY_MODEL_V1.md`](IDENTITY_MODEL_V1.md).
- Compares ontology vs ratified design vs shipped behavior.
- **Does NOT ratify ontology-expanded concepts into product requirements.**
- **Does NOT create implementation work.**
- Classifications are evidence-based; amendable through explicit review.
- Simulated persona findings remain design probes, not empirical customer research.

**Method:** read `IDENTITY_MODEL_V1.md` as the ontology reference; read ratified design docs (`CUSTOMER_JOURNEY_V1.md`, `CUSTOMER_MENTAL_MODEL_V1.md`, its adversarial review, `CREATE_SPOKESPERSON_WIZARD.md`, `CANONICAL_IDENTITY_CONTRACT_V1.md`, `JOB_ONE_V1.md`, `BRAND_IDENTITY_V3.md`); verify shipped behavior via targeted grep against `web/src/`, `shell/apps/`, `media-engine/app/`.

**Disciplines held:**
- Simulated personas remain simulated; conclusions marked accordingly.
- Ontology concepts not silently promoted to ratified requirements.
- "Not implemented yet" kept distinct from "wrong product model."
- `CANONICAL_IDENTITY_CONTRACT_V1.md` evaluated as a Presence-specific specialization, not as an identity-model claimant.
- Two corrections applied during operator review of the first draft: TC-3 downgrade + realtime personality path correction (both documented inline below).

**Companion:** the design-history reading order + known conflicts registry lives in [`CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`](CUSTOMER_EXPERIENCE_REVIEW_INDEX.md).

---

## §1 · Executive summary — highest-value findings

**F1 · The largest confirmed gap is DESIGN-AHEAD-OF-CODE.** `CUSTOMER_JOURNEY_V1.md` §"three layers of a spokesperson" (SESSION 232) ratified that the six identity slots "shape every video and every conversation." Shipped code consumes only a subset — full detail in §4 DAC-1. This is a code-catching-up-to-existing-ratified-design gap, not a product-model disagreement.

**F2 · The 4-template portrait palette is a genuine product-model decision.** `CREATE_SPOKESPERSON_WIZARD.md` Contract rule 5 ratifies the template palette (`mascot / founder / coach / local_guide`) as a customer-facing top-level choice. The ontology's compositional principle challenges this — but the palette is a deliberate ratified design position, not an implementation shortcut. Changing it requires operator judgment.

**F3 · Portrait generation independent of broader identity is an ontology-vs-existing-design decision.** Shipped portrait generation accurately implements the ratified wizard model (`template + subject + style` → `build_prompt()`). The ontology introduces a broader inter-modal coherence requirement that has not been ratified into product doctrine. The current implementation is not "wrong" against ratified design; it is faithful to it. Whether to adopt the ontology's coherence requirement is a separate operator decision.

**F4 · CANONICAL_IDENTITY_CONTRACT_V1.md is a rigorous Presence-specific specialization.** It operates entirely within the ontology's Presence dimension. It is not superseded by the ontology and should not be treated as competing. Its provenance model (CharacterIdentityVersion + PromotionAudit + review journal) is essentially the ontology's Provenance for the Presence dimension.

**F5 · The ONTOLOGY-EXPANDS-SCOPE (OES) list is load-bearing.** Multiple concepts in the ontology are genuinely new to Character OS — Worldview, Behavior as explicit dimension, Relational-disposition-separated-from-role, Situational role as projection rule, Distinctive signal invariant, Inter-modal coherence invariant, Temporal coherence for non-visual dimensions, Continuity contract, Creator-history vs relationship memory split, Proposed-and-ratified specification pattern, Compositional identity principle, Two-sided identity framing. Future sessions must not treat these as previously-ratified.

**F6 · Provenance is well-modeled for visual identity substrate but not for broader identity.** `CharacterIdentityVersion` + `PromotionAudit` + review journal exist for the Presence dimension. No equivalent exists for CORE dimensions.

**F7 · Memory is partially shipped but not modeled as identity-machinery.** SESSION 148 R6 realtime session memory summarizes prior sessions into next-session prompt injection. Ask (SESSION 234) uses conversation-thread history only. The ontology's split of creator-history vs relationship memory is a conceptual refinement neither shipped nor designed at that granularity.

**F8 · The wizard's body-first sequence aligns with ratified journey design.** `CUSTOMER_JOURNEY_V1.md` §"three layers" ratifies body-first / identity-second / knowledge-third. The wizard implements body-first per this design; identity is collected post-wizard at `/spokespeople/{id}/identity`. This is DESIGN-AND-CODE-ALIGNED. The ontology's inversion argument (author CORE first, derive Presence) is a separate design proposition; whether to adopt it is a distinct operator decision.

**F9 · Creator chosen name as primary handle is the strongest ALIGNED finding.** All three layers agree.

**F10 · Class-noun question is UNRESOLVED across all three layers.**

---

## §2 · Comparison matrix

Confidence codes: **H** = directly verified from source/code; **M** = inferred with strong evidence; **L** = interpretive judgment on limited evidence.

Corrections applied during operator review are noted in the row's Notes column.

| Concept | Ontology position | Ratified design position | Shipped behavior | Classification | Conf | Notes |
|---|---|---|---|---|---|---|
| **Charge / mission / purpose** | CORE dimension (§4.1); *"why does this creator exist, who does it serve, toward what end?"* | `CUSTOMER_JOURNEY_V1.md` slot 1: "what your business does" (= `business_brief`) | `Teammate.business_brief`; consumed by K6, realtime, ask | **PARTIAL** | H | Corrected from earlier "ALIGNED." `business_brief` captures shallow "what the business does"; the ontology's Charge asks a deeper why-and-for-whom question that business_brief can inform but not contain. E.g. "Neighborhood coffee shop serving espresso and pastries" (business brief) vs "Help regular customers feel connected to the neighborhood and give them a reason to come back" (Charge). |
| **Worldview** | CORE dimension (§4.1) | Not explicitly named in any design doc | No field; not consumed | ONTOLOGY-EXPANDS-SCOPE | H | |
| **Values** | CORE dimension (§4.1); "compass beyond utility; what shapes decisions when explicit rules run out" | `CUSTOMER_JOURNEY_V1.md` §"six identity slots" — `always_emphasize` (slot 4), `never_say` (slot 5), `desired_feeling` (slot 6) carry value-like constraints | Fields exist on `Teammate` (SESSION 232); NOT consumed by K6, realtime, portrait, campaigns, ask | **PARTIAL** | H | The three slots carry value-like constraints but do not fully instantiate the ontology's "compass beyond utility." A creator could satisfy always_emphasize + never_say + desired_feeling without having authored values that guide decisions when the rules run out. The overlap is real but incomplete. |
| **Relational disposition** | CORE dimension (§4.1); fundamental way of being with others | `Teammate.tone_archetype` enum (Tutor/Authority/Friend/Expert/Performer) is adjacent but conflates disposition with role | `tone_archetype` field; consumed by K6 | ONTOLOGY-EXPANDS-SCOPE | M | Ontology's disposition-vs-role separation is a refinement. |
| **Voice-linguistic** | EXPRESSION dimension (§4.2); language pattern | `CUSTOMER_JOURNEY_V1.md` implicit through `personality` (SESSION 175 split); "how the teammate speaks" | `Teammate.personality`; consumed by K6, ask, realtime | ALIGNED | H | |
| **Voice-sonic** | EXPRESSION dimension (§4.2); audio signature | `CREATE_SPOKESPERSON_WIZARD.md` Step 3 (Voice) | `Teammate.voice_id`; consumed by video, realtime | ALIGNED | H | |
| **Presence** | EXPRESSION dimension (§4.2); visual signature — species + silhouette + palette + iconic elements | `CREATE_SPOKESPERSON_WIZARD.md` Step 2 (Portrait) + template palette; `CANONICAL_IDENTITY_CONTRACT_V1.md` for visual substrate | `Teammate.portrait_path`, `visual_template`, `visual_subject`; portrait via 4-template palette | PARTIAL — concept present in all three; ontology's compositional treatment richer than shipped palette (see TC-1 below) | H | |
| **Behavior** | EXPRESSION dimension (§4.2); characteristic movement/reactions | Not explicitly named | No field; behavior emerges implicitly from prompt + provider defaults | ONTOLOGY-EXPANDS-SCOPE | H | |
| **Creator-history memory** | GOVERNANCE (§4.3); what creator has said/committed/learned as itself | Not explicitly named as such; realtime memory arc (SESSION 148 R6) is closest analog | `realtime_memory.compose_session_memory()` for realtime session-to-session; ask uses thread-scoped history; no cross-modality creator-history | PARTIAL — some shipped; none modeled as identity-machinery. R6 mechanism is CODE-AHEAD-OF-DESIGN for that specific realtime pattern; the creator-history framing itself is ONTOLOGY-EXPANDS-SCOPE | M | |
| **Relationship memory** | GOVERNANCE (§4.3); what creator knows about particular people/orgs | Not explicitly named | Not present; workspace-level `Membership` is coarser than per-relationship memory | ONTOLOGY-EXPANDS-SCOPE | H | |
| **Continuity contract** | GOVERNANCE (§4.3); tolerance specifications per dimension | Not present in any design doc | Not present | ONTOLOGY-EXPANDS-SCOPE | H | Entirely new concept. |
| **Provenance** | GOVERNANCE (§4.3); authoring event + amendment authority + change history | `CANONICAL_IDENTITY_CONTRACT_V1.md` §19 shipped `CharacterIdentityVersion` + `PromotionAudit` + review journal — for visual identity substrate only | Visual identity provenance shipped; no provenance for CORE dimensions | PARTIAL — provenance well-modeled for Presence dimension; not modeled for CORE. Presence-provenance ALIGNED; CORE-provenance ONTOLOGY-EXPANDS-SCOPE | H | |
| **Distinctive signal (invariant)** | Cross-layer requirement (§7.1) | `PERSONA_REVIEW_SESSION_250.md` P-1 noted distinctive silhouette matters (as observation, not requirement) | No enforced signal check | ONTOLOGY-EXPANDS-SCOPE | H | |
| **Inter-modal coherence (invariant)** | Cross-layer requirement (§7.2) | `CUSTOMER_JOURNEY_V1.md` §"three layers" implies coherence; no formalization | No coherence check; portrait, voice, script generated independently | ONTOLOGY-EXPANDS-SCOPE | H | |
| **Temporal coherence (invariant)** | Cross-layer requirement (§7.3) | `CANONICAL_IDENTITY_CONTRACT_V1.md` handles version supersede + amendment for visual only | Visual has versioning; other identity dimensions overwrite on edit | PARTIAL — same split as Provenance | H | |
| **Creator chosen name as primary customer handle** | Non-scope (§10); implicitly favored via "Meet {name}" pattern | `CUSTOMER_JOURNEY_V1.md`: "Copy interpolates `{name}` universally"; `CUSTOMER_MENTAL_MODEL_V1.md` §4.1 Direction B | SPA uses `{name}` throughout | ALIGNED (strongest alignment) | H | |
| **Universal class noun** | Non-scope (§10) | `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` F5: probably not needed; §17.1.b ratified `Teammate` as code term; customer term undecided | Code uses `Teammate`; SPA mixes "spokesperson" (URLs, copy) with `{name}` | RATIFIED under OD-4 (Name Primacy) | H | Under OD-4 the "unresolved across all three" state is now the ratified product principle: a universal customer-facing class noun is not a required product concept. The customer's relationship is with the individual creator, not with a class. Where a class reference is used, the language chosen is a communication decision, not a defining product concept. Engineering identifiers (`Teammate`, `spokesperson_*`) and SPA/marketing/doc copy remain communication decisions rather than product-model conflicts. |
| **Full-identity downstream consumption** | CORE dimensions should shape output | `CUSTOMER_JOURNEY_V1.md`: identity slots "shape every video and every conversation" | 5 of 6 identity slots consumed by ZERO downstream generation system (K6, realtime document composition, portrait, campaigns, ask) | DESIGN-AHEAD-OF-CODE | H | Largest gap. |
| **Visual-template palette** | Templates should be derived defaults; palette mixes visual style + creator role at same abstraction level | `CREATE_SPOKESPERSON_WIZARD.md` Contract rule 5: palette explicitly ratified | 4-template palette in shipped wizard | TRUE-CONFLICT — ontology-vs-ratified-design | H | Operator judgment required. |
| **Portrait-generation derivation from CORE identity** | Presence can be Authored / Proposed-and-ratified / Constrained; should derive from CORE where practical | Wizard Step 2 collects `template + subject + style` independently of CORE identity fields; `CUSTOMER_JOURNEY_V1.md` says identity slots shape "video and conversation" — **portraits are neither** | `/api/spokespeople/generate-portrait/` takes `{template, subject?, style?}`; no identity input | TRUE-CONFLICT — ontology-vs-ratified-design (NOT ratified-vs-ratified — see correction below) | H | **Correction from first draft:** originally classified as an internal ratified-doc conflict (wizard-vs-journey). On re-read of exact wording, journey doc says identity slots shape "video and every conversation" — portraits are not videos or conversations. The two ratified docs are consistent at the wording level; the ontology's inter-modal coherence requirement is what would extend identity's reach to portraits. Correctly this is ontology-vs-ratified-design. |
| **Identity editing → downstream invalidation/reprojection** | Editing identity has visible downstream effects (implied by ontology minimum truths) | Identity slots editable at `/spokespeople/{id}/identity`; downstream invalidation not designed | No invalidation; old videos/scripts unchanged | RATIFIED under OD-3 (Artifact History) | H | Under OD-3 the shipped behavior (no silent invalidation / regeneration / annotation of historical artifacts) is now the ratified product principle, not an unresolved gap. The ontology's implication that identity edits have visible downstream effects is answered: effects are forward-going into future artifacts; they do not retroactively rewrite historical artifacts. Customer-directed transformation of an existing artifact remains permitted and produces new work rather than modifying the original. |
| **Multiple creators per workspace** | §11 Q-ε open (collaborative creators) | `CUSTOMER_JOURNEY_V1.md` assumes Oliver-as-primary but allows multiple | Workspace supports multiple `Teammate` rows | ALIGNED for singular; UNRESOLVED for collaborative/ensemble | M | |
| **Customer mental model** | Two-sided (interior/exterior); compositional identity (§8) | `CUSTOMER_MENTAL_MODEL_V1.md` proposed three-object model (Your AI / Sources / What it makes) | Wizard produces Teammate + Knowledge + Videos; roughly matches | ALIGNED for three-object shape; ONTOLOGY-EXPANDS-SCOPE for two-sided framing + compositional principle | M | |
| **Operator/customer boundary** | Non-scope (§10) | `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` F3: "one product with staff-gated surfaces" | `IsOperator` gates at API layer (verified). SPA nav does not link bootstrap-review or engine-connections; provider-status is footer-linked. Direct URLs reachable to any authenticated user (403 kicks non-staff at API) | DESIGN-AHEAD-OF-CODE for nav-hiding intent (design says hide; SPA doesn't fully) — see also DA-2 correction below | H | |

### §2.1 · Correction to realtime personality consumption

An earlier grep restricted to `shell/character_os/realtime_document.py` reported that realtime does NOT consume `Teammate.personality`. That grep was too narrow.

The actual shipped path: `shell/apps/realtime/views.py:205-218` reads `spokesperson.personality` (with fallback to `business_brief`) and injects it into the Runway realtime session's `personality` field at session-creation time. `realtime_document.py` — the document-composition helper for grounding in workspace knowledge — reads only `name`, `business_brief`, `workspace`, `pk`. Both are shipped; both are realtime-adjacent; they serve different purposes.

So the Voice-linguistic row's "consumed by K6, ask, realtime" statement is correct. The mechanism note is corrected here: realtime consumption is via the session-creation code path (`apps/realtime/views.py`), not via the document composition path.

---

## §3 · True conflicts

Only conflicts that genuinely require product/operator judgment.

### TC-1 · Visual-template palette vs ontology's compositional principle

- **Ratified design:** `CREATE_SPOKESPERSON_WIZARD.md` Contract rule 5 ratifies the 4-template palette as a customer-facing top-level choice.
- **Ontology position:** §8 (compositional identity) argues identity is the composed pattern; §4.2 treats Presence as a signature; the palette conflates visual style with creator role at the same abstraction level.
- **Why true conflict, not implementation gap:** the palette is deliberate ratified design, not code lagging behind design. The ontology's compositional principle is a deliberate ontological choice.
- **Operator judgment required.**

### TC-2 · Portrait generation independent of CORE identity

- **Ratified design + shipped:** wizard Step 2 collects `template + subject + style`; `character_studio_client.build_prompt()` uses only those three inputs; no CORE identity dimension enters the prompt.
- **Ontology position:** §4.2 Presence + §7.2 inter-modal coherence require visual output to faithfully project CORE; §6 lists Presence as a candidate for "Proposed and ratified."
- **Note (correction from first draft):** this was previously classified with TC-3 (below) as a companion "internal ratified conflict." On re-read, `CUSTOMER_JOURNEY_V1.md` claims identity slots shape "every video and every conversation" — not portraits. The ratified docs do not internally conflict on this specific point. What remains is a genuine ontology-vs-existing-design tension.
- **Operator judgment required.**

### TC-3 · REMOVED

The first draft classified an internal ratified-design conflict between `CUSTOMER_JOURNEY_V1.md` (identity slots "shape every video and every conversation") and `CREATE_SPOKESPERSON_WIZARD.md` (portrait via template + subject + style). On operator-requested re-read of the exact wording: journey doc restricts the claim to videos and conversations. Portraits are neither. The two ratified docs are consistent at the wording level; no internal conflict exists on this specific claim.

The ontology's inter-modal coherence requirement (§7.2) would extend identity's reach across all EXPRESSION dimensions including Presence, which would then create a coherence expectation for portraits. But that is an ontology-vs-ratified-design tension (already captured as TC-2), not a ratified-vs-ratified conflict.

**Lesson recorded:** classifications must trace to exact ratified-doc wording, not to what a reader might reasonably wish the older doc had said. Preserved here as a methodological note.

---

## §4 · Design-ahead-of-code gaps

### DAC-1 · Full identity slot consumption

- **Design ratifies:** `CUSTOMER_JOURNEY_V1.md` §"six identity slots" — all six "shape every video and every conversation."
- **Shipped code:** K6 script synthesis reads `name`, `business_brief`, `personality`, `tone_archetype`. Realtime document reads `name`, `business_brief`, `workspace`. Realtime session-creation reads `personality` (fallback `business_brief`). Ask reads `name`, `business_brief`, `personality`. Campaigns/video composition consume even less. **`who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`, `desired_feeling` are not read by any generation path.**
- **Not a product-model disagreement.** Design says these should shape output; code doesn't yet. Engineering, not architecture.

### DAC-2 · Staff-gated surface isolation

- **Design ratifies:** `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` F3 corrects "two products" to "one product with staff-gated surfaces."
- **Shipped code:** `IsOperator` permission gate at API layer works (verified). SPA nav does not link bootstrap-review or engine-connections; provider-status is footer-linked. Direct URLs remain reachable; API kicks non-staff via 403.
- **Related correction:** `PERSONA_REVIEW_SESSION_250.md` P-8 claimed operator surfaces were exposed in the customer nav. Verified this session: only provider-status is footer-linked; bootstrap-review and engine-connections are direct-URL only. P-8's spirit stands (unlinked surfaces still surprise via direct URL) but the specific "in the customer nav" claim was inaccurate for two of three surfaces. Correction handled via a note added to `PERSONA_REVIEW_SESSION_250.md` preserving the original text — see DA-2 below.

### DAC-3 · Wizard body-first vs post-wizard identity

- **Design ratifies:** `CREATE_SPOKESPERSON_WIZARD.md` v1 floor is body (name + business_brief + portrait); identity slots authored later at `/spokespeople/{id}/identity` per `CUSTOMER_JOURNEY_V1.md` §"The Identity surface."
- **Shipped code:** matches design.
- **Class:** essentially ALIGNED between design and code. The ontology's alternative (creator-first: author CORE first, derive Presence) is a distinct design proposition — not the same as this alignment finding. See F8 exec summary.

---

## §5 · Ontology-expands-scope findings

Genuinely new ideas the ontology introduces. These MUST NOT be treated as previously ratified.

### OES-1 · Worldview as CORE dimension (§4.1)

Not present in any prior Character OS doc.

### OES-2 · Behavior as explicit EXPRESSION dimension (§4.2)

Character OS docs discuss video composition and realtime behavior but not "characteristic behavior" as an identity dimension.

### OES-3 · Relational disposition as separate from tone archetype

`tone_archetype` enum conflates disposition (how the creator relates) with role (what the creator does). Ontology separates them.

### OES-4 · Situational role as projection rule, not dimension (§5)

No prior Character OS doc treats context this way.

### OES-5 · Distinctive signal as invariant requirement (§7.1)

No prior enforcement or design commitment.

### OES-6 · Inter-modal coherence as invariant requirement (§7.2)

Design implicitly assumes coherence; ontology formalizes as requirement.

### OES-7 · Temporal coherence for non-visual dimensions (§7.3)

Visual identity has version handling via `CANONICAL_IDENTITY_CONTRACT_V1.md`. Non-visual identity dimensions have no version handling.

### OES-8 · Continuity contract as tolerance specifications per dimension (§4.3)

New concept.

### OES-9 · Creator-history vs relationship memory split (§4.3)

R6 realtime memory is the shipped analog to creator-history memory for realtime sessions only. Relationship memory is unshipped.

### OES-10 · Specification categories including "Proposed and ratified" (§6)

Wizard flows are essentially Authored or Model-generated. No pattern exists for "system proposes, operator ratifies."

### OES-11 · Compositional identity principle (§8)

Foundational stance not previously articulated.

### OES-12 · Two-sided identity (interior/exterior) (§3)

New framing.

---

## §6 · Historical artifacts

Preserved as history rather than treated as current guidance.

- **HA-1 · Pre-SESSION 175 flat `business_brief` field** — pre-split model. Historical.
- **HA-2 · Pre-SESSION 232 spokesperson identity model** — pre-six-slot. Historical.
- **HA-3 · Pre-SESSION 240 `Spokesperson` class name** — code renamed to `Teammate`; customer-facing term unresolved.
- **HA-4 · `an earlier hackathon prototype` sibling repo** — historical reference; read-only.
- **HA-5 · `CREATE_SPOKESPERSON_WIZARD.md` v1 floor scope** — accurate for its SESSION 123 era. The wizard describes body-creation scope; identity slots + surface (SESSION 232) are later product-model expansions that live in `CUSTOMER_JOURNEY_V1.md`. The wizard doc is preserved unchanged; see DA-4 below for the scope note that will accompany it in the index.

---

## §7 · Operator decisions required before any implementation planning

Not implementation tasks. Product decisions.

### OD-1 · TC-1 · Visual-template palette · **RATIFIED 2026-08-08**

**RATIFIED.** See [`docs/design/operator-decisions/OD-1_PRESENCE_AUTHORING.md`](operator-decisions/OD-1_PRESENCE_AUTHORING.md).

The ratified product principle is that customer-facing Presence authoring is driven by creative intent, not by a required fixed template palette. Templates are implementation scaffolding and/or optional authoring aids; they are not a required product abstraction the customer must understand. The current `mascot / founder / coach / local_guide` palette remains valid as existing implementation scaffolding during transition. The replacement Presence-authoring UI, disposition of the four current templates, intent-capture technique, scaffolding derivation, database changes, and migration sequencing are all deliberately left open by the ratification.

The original open-question framing (below) is preserved for historical continuity of the review:

> Preserve 4-template palette as ratified vs evolve toward compositional Presence specification?

### OD-2 · TC-2 · Portrait derivation from CORE identity · **RATIFIED 2026-08-08**

**RATIFIED as Creator Fidelity.** See [`docs/design/operator-decisions/OD-2_CREATOR_FIDELITY.md`](operator-decisions/OD-2_CREATOR_FIDELITY.md).

The ratified product principle is that Character OS's job is fidelity to the customer's authored creator across contexts and modalities — not enforcement of a system-defined coherence. Relevant authored intent (per artifact) must not be silently ignored; explicit customer choices must not be overridden by hidden implementation defaults; intentional tension between authored inputs is preserved, not smoothed. The specific integration mechanism and conflict-handling behavior are deliberately left open.

An important reframing occurred during ratification: the original OD-2 pressure-test proposed "system is responsible for coherence" as the primary principle. An adversarial pass surfaced three problems with that framing — coherence privileges one possible creator quality (excluding intentional-tension creators), collapses several distinct concepts into one word, and treats an outcome as if it were an implementation mechanism. The ratified principle is fidelity; coherence emerges from fidelity when the customer authored coherence but is not itself the controlling principle. Full detail in the OD-2 artifact.

**Relationship to IDENTITY_MODEL_V1 §7.2 (inter-modal coherence):** OD-2 does not ratify §7.2's inter-modal coherence invariant as the controlling product principle. The ontology's §7.2 remains preserved as ontological reference material describing a structural property of persistent identity in the abstract. OD-2 governs Character OS's specific product behavior — which is fidelity, not coherence enforcement — and takes precedence over §7.2 where the two would diverge (specifically: when the customer's authored inputs contain intentional tension, fidelity preserves the tension and does not enforce §7.2's coherence claim). The ontology itself is not amended by this ratification.

The original open-question framing (below) is preserved for historical continuity of the review:

> Derive portrait from CORE identity per inter-modal coherence, or preserve independent Presence authoring per current wizard?

### OD-3 · Artifact History · **RATIFIED 2026-08-08**

**RATIFIED as Artifact History.** See [`docs/design/operator-decisions/OD-3_ARTIFACT_HISTORY.md`](operator-decisions/OD-3_ARTIFACT_HISTORY.md).

The ratified product principle is that Character OS produces every artifact with fidelity to what the customer authored at the moment of generation, and existing artifacts remain historical records of what was created. Identity edits shape future artifacts; they do not silently modify, regenerate, annotate, or invalidate existing ones. New artifacts may always be created from existing artifacts whenever the customer directs — the original remains as it was produced; customer-directed transformation produces new work from existing work, not modification of history. The customer retains full agency over their historical work (preserve, derive, retire) as customer-driven decisions, not system-driven consequences of authoring changes.

An important reframing occurred during ratification: the original framing centered "identity-edit reprojection" and used "reprojection" as an implementation verb, which presumed a mechanism before the product question was settled. The reframed principle centers artifact history — who has authority over an existing artifact, and what happens to that artifact when authoring changes or when the customer directs new work. Under the reframed principle, the distinction that matters is *system-inferred rewriting of history* (prohibited) vs *customer-directed creation of new work from existing work* (fully supported). The reframed principle survives every pressure-tested scenario (rewrite, regenerate, translate, transform, version, edition) because none of those are modifications — each is the creation of new work using existing work as source material. Full detail in the OD-3 artifact.

**Scope shift from prior §7 numbering.** This slot was previously labeled *"Whether to adopt any OES concept as ratified product doctrine"* — a broad meta-question about ontology-expanded concepts. That meta-question is now handled per-concept as each becomes decision-worthy on its own (OD-1 handled the Presence question that arose from TC-1; OD-2 handled the fidelity question that arose from TC-2; OD-3 handles the artifact-history question that arose from GOVERNANCE-layer identity evolution). The three ratified ODs together already exercise that per-item pattern.

**Subsumption of prior §7 OD-5.** The prior OD-5 slot — *"Should identity edits trigger regeneration or warnings on downstream artifacts?"* — is answered by OD-3: identity edits shape future artifacts, do not silently regenerate historical ones, and do not annotate historical artifacts as "stale." Warnings-on-old-artifacts as a system-driven behavior fall under the "silently annotate" prohibition. Customer-directed regeneration remains fully supported and produces new work.

**Relationship to IDENTITY_MODEL_V1 GOVERNANCE layer.** The ontology's GOVERNANCE dimensions (Memory, Continuity contract, Provenance) name the machinery that keeps identity coherent and manages change. OD-3 is Character OS's ratified product commitment about how those dimensions interact with produced artifacts: history is preserved, forward-going evolution shapes future work, and customer authority governs any transformation of existing work.

The original open-question framing (below) is preserved for historical continuity of the review:

> Whether to adopt any OES concept as ratified product doctrine (original OD-3 slot, superseded by Artifact History ratification per the reshape note above).

### OD-4 · Name Primacy · **RATIFIED 2026-08-08**

**RATIFIED as Name Primacy.** See [`docs/design/operator-decisions/OD-4_NAME_PRIMACY.md`](operator-decisions/OD-4_NAME_PRIMACY.md).

The ratified product principle is that Character OS is centered on individual creators, not on a customer-facing class taxonomy. Customers primarily relate to each creator by its chosen name; a universal customer-facing class noun is not required for the product to function or for the customer to form a coherent mental model. Where a class reference is used, the language chosen is a communication decision, not a defining product concept.

An important reframing occurred during ratification: the class-noun question was initially framed as "which word should Character OS use?" (`spokesperson`, `Teammate`, `creator`, name-only, or something else?) — treating it as a naming choice awaiting resolution. Pressure-testing revealed the question underneath: whether a universal customer-facing class noun is a required product concept at all. The answer, consistent with `PERSONA_REVIEW_SESSION_250.md` P-1, `CUSTOMER_MENTAL_MODEL_V1.md` §4.1, `CUSTOMER_MENTAL_MODEL_V1_ADVERSARIAL_REVIEW.md` F5, and `IDENTITY_MODEL_V1.md` §10, is no. The class-noun's necessity was never established, so no naming choice needed to be made at the product-philosophy level.

An earlier OD-4 draft embedded editorial policy (UI wording, marketing language, engineering identifiers, documentation conventions) within the ratification body. That draft was tightened by roughly half on operator review, on the grounds that editorial policy is not product philosophy and freezing it in a ratification would over-constrain future product work. The ratified statement is three sentences that survive UI redesigns, marketing changes, engineering refactors, URL migrations, database renames, documentation rewrites, model providers, and new product surfaces. Full detail in the OD-4 artifact.

**Relationship to IDENTITY_MODEL_V1 §10.** The ontology non-scoped the customer-facing class term. OD-4 does not amend that non-scope; it makes the non-scope itself the ratified product principle. The individual creator is the customer-facing unit; the ontology's structural dimensions are not required customer-facing product concepts.

The original open-question framing (below) is preserved for historical continuity of the review:

> Customer-facing term: `spokesperson`, `Teammate`, `creator`, name-only, or something else? (superseded by OD-4's reframing — the necessity question, not the naming question, was the load-bearing one).

### OD-5 · Identity edit → downstream reprojection · **SUBSUMED by OD-3**

Answered by [`OD-3 Artifact History`](operator-decisions/OD-3_ARTIFACT_HISTORY.md). System-driven reprojection (silent modification, regeneration, annotation, or invalidation of historical artifacts triggered by identity edits) is prohibited under OD-3. Customer-directed transformation is fully supported and produces new work rather than modifying the original. Warnings-on-old-artifacts as a system-driven behavior fall under OD-3's "silently annotate" prohibition. What OD-3 does not itself decide (surfaced authoring-state metadata; UI for deriving new work; storage / provenance schema) is deliberately deferred to design and implementation per that ratification's non-decisions.

### OD-6 · Whether the three-way comparison should trigger any doc amendments

The comparison itself may indicate places where ratified docs would benefit from clarifying preface notes. That decision is separate from the individual OD items above.

---

## §8 · Recommended documentation actions

No implementation. Only documentation-hygiene actions this comparison surfaces.

- **DA-1 · REMOVED** — the "wizard-vs-journey internal conflict" it originally recommended recording was based on a misreading (see TC-3 REMOVED above); nothing new to add to the conflicts registry from that source.
- **DA-2 · Preserve `PERSONA_REVIEW_SESSION_250.md` original body; add a small correction note.** P-8's specific claim about operator surfaces being "in the customer nav" was empirically wrong for bootstrap-review and engine-connections (only provider-status is footer-linked). The finding's spirit stands; the specific empirical claim needs correction. Note added, original preserved as historical evidence.
- **DA-3 · Provenance scope note in the index.** Add clarifying note that the ontology's Provenance concept spans all dimensions; `CANONICAL_IDENTITY_CONTRACT_V1.md` handles Provenance rigorously for the Presence dimension only.
- **DA-4 · `CREATE_SPOKESPERSON_WIZARD.md` scope note in the index.** Preserve the wizard doc body unchanged. Note in the index that its scope covers wizard/body creation from its SESSION 123 ratification era; later work (SESSION 232 identity surface, ontology V1) expanded the broader product identity model beyond what the wizard doc scopes.
- **DA-5 · No amendments to ratified contracts.** No silent changes to `CANONICAL_IDENTITY_CONTRACT_V1.md`, `CUSTOMER_JOURNEY_V1.md` body, `CREATE_SPOKESPERSON_WIZARD.md` body.

---

## §9 · Confidence and limits

- **What this analysis definitely knows (H):** the six identity slots exist on `Teammate` and are unused by downstream generation code (grep verified this session); wizard collects `template + subject + style` (source read); `character_studio_client.build_prompt()` uses only those three (source read); K6, realtime document, ask consumption verified via grep; realtime session-creation (`apps/realtime/views.py`) DOES read `personality` (added under §2.1 correction).
- **What this analysis inferred (M/L):** classifications of ontology dimensions against design intent rely on interpretation. Confidence codes noted per row.
- **What this analysis did NOT do:** re-read every ratified design doc line-by-line; survey every video composition / recipe / knowledge / F-arc doc for identity references; check whether any downstream code path uses the 5 currently-unused identity slots via paths my grep missed; assess whether R6 realtime memory infrastructure could be repurposed for the ontology's creator-history memory.
- **Corrections applied during operator review:** TC-3 downgraded; realtime personality consumption path corrected in §2.1; Charge classification downgraded PARTIAL; Values classification held as PARTIAL with clearer note.
- **What could change this analysis:** if any of the 5 currently-unused identity slots turns out to be consumed by a code path grep missed, DAC-1 severity drops. If any design doc I didn't survey contains a formalized inter-modal coherence check or continuity contract concept, some OES findings become ALIGNED.

---

## §10 · Non-content — what this document is not

- Not a set of implementation tasks.
- Not a scope-lock. Individual concepts are not ratified by inclusion here.
- Not a rewrite of any ratified doc.
- Not a claim that ontology-expanded concepts should be adopted; those are per-concept operator decisions handled as each becomes decision-worthy (the original §7 OD-3 slot for that meta-question was reshaped when Artifact History was ratified under OD-3 — see §7 OD-3 reshape note).
- Not a critique of `CANONICAL_IDENTITY_CONTRACT_V1.md`. That contract handles its scope well; the ontology extends coverage to CORE dimensions the contract was never intended to cover.

---

## STOP

Three-way comparison preserved as design-history artifact. Corrections applied. Four operator decisions ratified 2026-08-08 (OD-1 Presence Authoring, OD-2 Creator Fidelity, OD-3 Artifact History, OD-4 Name Primacy — see `docs/design/operator-decisions/` and §7 for each). Prior §7 OD-5 (identity edit reprojection) SUBSUMED by OD-3. Only §7 OD-6 (whether the three-way comparison should trigger any doc amendments) remains pending. This document remains an analytical companion, not a ratification track; individual matrix rows are reclassified to RATIFIED as their governing OD lands.
