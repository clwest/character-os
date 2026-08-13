# IDENTITY_MODEL_V1 — What Constitutes the Identity of an AI Creator

**Status:** Ratifiable ontology proposal (V1)
**Type:** Design artifact — ontology, not implementation
**Method:** First-principles reasoning; deliberately independent of any specific implementation. No reference to Character OS's current schemas, wizard, models, or shipped behavior was consulted while composing this ontology.
**Scope:** What information must exist for an AI creator to remain recognizably the same creator across conversations, scripts, portraits, voice, and video, over months and years.
**Non-scope:** Database schema. API design. UX. Wizard flow. Provider selection. Generation techniques. Prompt engineering. Product-tier packaging. Customer-facing language.
**Companion design history:** persona review (SESSION 250), `CUSTOMER_MENTAL_MODEL_V1.md` + adversarial review, product-model audit findings, first ontology draft + adversarial pass + reconciliation pass.
**Ratification protocol:** V1 is a proposal. Adoption of any refinement in a future session is an explicit ratification event; this document should not be silently amended. If V1 is revised, produce a V2 with dated reasoning rather than editing V1 in place.
**Unresolved philosophical questions:** eight open questions remain intentionally open (§11).

---

## §1 · Preface

This document answers one question:

> What information must exist for an AI creator to remain recognizably the same creator across conversations, scripts, portraits, voice, and video, over many months?

It answers as ontology — the structure of what identity IS — not as implementation. It says nothing about how identity should be captured, stored, queried, authored, or displayed. Those decisions belong downstream and depend on factors this ontology deliberately does not consider.

The ontology assumes the eventual product will produce AI creators who exist over time, appear across multiple modalities, and be recognized by human audiences as continuous entities. Within that assumption, the ontology is provider-neutral, model-neutral, and product-neutral.

---

## §2 · The core problem

A persistent AI creator produces many artifacts over time. Each artifact — a still image, a spoken sentence, a live conversation, a rendered video — is a **manifestation** of the creator in a specific modality. No single artifact IS the creator. Identity is the pattern the artifacts approximate.

This distinction is load-bearing. Systems that conflate identity with any specific artifact (a canonical image, a canonical voice sample, a canonical script) fail whenever new artifacts differ. Systems that build for identity-as-pattern can produce infinite artifacts that all remain recognizably one creator.

**Identity is the coherent pattern that manifestations approximate.**

---

## §3 · Identity is two-sided

Every identity has an **interior** (what the creator internally IS — the specification the system holds) and an **exterior** (what audiences recognize when they encounter the creator across time).

- Interior without exterior is a database. It stores facts no audience ever perceives.
- Exterior without interior is a false pattern. Audiences may perceive continuity in a series of artifacts anchored by nothing; the pattern collapses at the next generation because nothing underlies it.

Both must exist. The ontology accounts for the specification-side (interior) and the perception-side (exterior) as coupled halves of the same thing. Identity is the correspondence between the two — the degree to which the exterior faithfully expresses the interior, and the interior remains stable enough for the exterior to be perceived as one thing across encounters.

---

## §4 · The three-layer structure

Identity is composed across three layers. Each layer plays a different role. Each has different tolerance to change. Each fails in different ways.

### §4.1 · CORE IDENTITY — what the creator IS

Dimensions in this layer are constitutional. Their reversal breaks identity. They have low tolerance for change.

**Charge.** What the creator is FOR. Who they serve, in what way, toward what end. The reason they exist. If the creator disappeared, who would notice, and what would go unfilled? Every persistent creator has a charge, even if the charge is expressive rather than functional.

**Worldview.** The interpretive lens the creator brings to their domain. May take the strong form of explicit conviction (position) for creators whose function demands it, or a softer form of implicit stance for creators who don't hold policy positions but who nonetheless see the world through a particular frame. Universal across creator types; intensity varies.

**Values.** What the creator cares about beyond utility. The compass that shapes decisions when explicit rules run out. What the creator would defend without being asked. What they refuse when refusal costs them.

**Relational disposition.** The creator's fundamental way of being with others. Warm-and-patient, direct-and-brisk, playful-and-teasing, formal-and-precise. This is stable stance — distinct from the situational role the creator adopts within that stance for a given context (situational role is a projection rule, not a dimension — see §5).

### §4.2 · EXPRESSION — how the creator MANIFESTS

Dimensions in this layer are how CORE identity becomes perceptible. They project CORE into modalities. They have medium-to-wide tolerance for variation, with tolerances varying per dimension. They must project CORE faithfully and must remain internally coherent across modalities.

**Voice-linguistic.** The creator's language pattern. Rhythm, vocabulary, sentence shape, metaphor style, humor, characteristic openings and closings, pauses and emphases. What allows a paragraph to be recognized as theirs even without a byline. Medium tolerance — audiences catch large shifts immediately.

**Voice-sonic.** The audio signature. Timbre, cadence, warmth, breath. What allows the creator to be recognized by ear. Distinct from Voice-linguistic; the linguistic voice can persist across translation while the sonic voice is lost entirely. Wider tolerance than Voice-linguistic — the same creator can be re-voiced within their character range.

**Presence.** The visual signature. Not any specific portrait — the signature that persists across portraits. Species / form / archetype. Distinctive silhouette. Palette. Iconic features and elements (marks, costume, prop, distinguishing proportions). What allows the creator to be recognized in a thumbnail. Wide tolerance — significant re-rendering is acceptable if signature-carrying features persist. Substantial-enough change eventually breaks identity even with everything else intact.

**Behavior.** Characteristic movement, reaction patterns, mannerisms, habits, pace. What surprises the creator; what quiets them; what animates them. Behavior is movement identity — it's what allows video to feel like the same creator across scenes. Medium tolerance.

### §4.3 · GOVERNANCE — mechanisms that keep identity coherent and manage change

Governance is not identity. Governance is the set of mechanisms that support identity over time and legitimize change. Loss or absence impairs continuity of use but does not break the creator's identity itself.

**Memory** splits into two related but distinct sub-parts:

- **Creator-history memory** — What the creator has said, learned, committed to, changed, or experienced as itself. The creator's own continuity of self across time. If a creator makes a significant statement in Month 1 and refers back to it in Month 6, creator-history memory is what makes that possible.
- **Relationship memory** — What the creator knows about particular people, organizations, or ongoing relationships. The creator's continuity of relationship across time. If a returning customer's context is remembered ("last time we spoke, you were considering closing the Tuesday location"), relationship memory is what makes that possible.

Both support persistence. They are not the same. Loss of either impairs a specific kind of continuity without breaking identity itself.

**Continuity contract.** The tolerance specifications per dimension. The rulebook the system uses to decide whether a proposed future state is legitimate evolution or an identity break. Not a property of the creator; a property of the system that manages the creator.

**Provenance.** The authoring event, amendment authority, change history, and dispute-resolution authority. Facts ABOUT the creator held by external systems. If the historical record were lost, the creator would still be themselves; only the record would be gone.

---

## §5 · Projection rules

Some observable behaviors are not identity dimensions but projections of dimensions into contexts.

**Situational role.** A creator may adopt different roles in different contexts — peer with a business owner, teacher when explaining a concept, reassurer when someone is overwhelmed, collaborator during joint work. These are not four identities and are not four dimensions. They are one Relational disposition projected across contexts:

    Relational disposition + current context → situational posture

A creator whose Relational disposition is warm-patient-attentive will adopt teacher-like posture when the context is explanatory, peer-like posture when the context is collaborative, and reassurer-like posture when the context is anxiety-charged — all without changing identity.

Situational role is thus a projection rule, not a dimension. The dimension is the underlying Relational disposition; the rule specifies how it projects across contexts.

This document notes situational role as an important projection rule but does not enumerate all projection rules. Future ontology versions may formalize others (for example: how Voice-linguistic projects across register formality; how Behavior projects across pacing contexts; how Presence projects across visual scale from full portrait to thumbnail).

---

## §6 · Specification framework

Every dimension is specified in one of four ways. The category matters because it determines what the system does when the dimension is under-specified and how drift is detected over time.

**Authored.** The dimension is explicitly stated by the creator's author. Full specification. No inference. What the author said is what the creator is.

**Proposed and ratified.** The system proposes a specification derived from other dimensions (or from the creator's overall shape); the operator reviews the proposal and either accepts it, amends it, or rejects it. Once ratified, the ratified specification is identity-bearing and functions like an authored specification. This is a legitimate authoring path where explicit authorship is impractical — the operator may not know how to author Presence in isolation but is fully capable of ratifying a system-proposed Presence that coheres with the CORE they DID author.

**Constrained.** The dimension has degrees of freedom but is bounded by other authored (or ratified) dimensions. A generation-time system may vary within the constraints without asking; drift within constraints is legitimate.

**Model-generated.** The dimension is left to the underlying generation model. No specification, no constraint. Whatever the model produces is what appears. This category is legitimate only for dimensions where drift is genuinely irrelevant. For most identity dimensions, model-generated is drift-prone and identity-mutating; it should be a rare, deliberate choice.

The four categories are not equal-value alternatives. Some dimensions must be authored or proposed-and-ratified (Charge cannot be model-generated — the reason the creator exists cannot be filled in randomly). Some dimensions can safely live in constrained (Voice-sonic can often be constrained by Voice-linguistic + Behavior + Presence without full specification). No product-facing identity dimension should be silently model-generated.

---

## §7 · Cross-layer requirements

Three requirements span the layers. They are invariants any persistent identity must satisfy. They are not dimensions.

### §7.1 · Distinctive signal

**A persistent identity requires sufficient distinctive signal across CORE and/or EXPRESSION for audiences to recognize continuity across encounters.**

Distinctiveness can live in any dimension. A creator may be recognizable through:

- A distinctive Charge (few creators do this specific thing)
- A distinctive Worldview (few see the world this way)
- Distinctive Values (few operate from this specific compass)
- A distinctive Relational disposition (few relate to people this way)
- A distinctive Voice-linguistic (few speak like this)
- A distinctive Voice-sonic (few sound like this)
- A distinctive Presence (few look like this)
- Distinctive Behavior (few react like this)
- A redundant combination across multiple dimensions

Redundancy is a strength. A creator distinctive in multiple dimensions is robust to noise in any single dimension. A creator distinctive in only one dimension depends critically on that dimension's preservation.

An identity that is coherent but generic — coherent in specification but distinctive in no dimension — is coherent but unrecognizable. It exists as a specification and cannot function as a persistent identity in practice, because there is no signal for audiences to recognize across encounters.

**Coherence and recognizability are both required. Neither alone is sufficient.**

### §7.2 · Inter-modal coherence

Every EXPRESSION dimension projects CORE into a modality. When multiple modalities are combined (voice + portrait; video with narration; live conversation with visible presence), they must project the same CORE consistently.

A warm voice paired with a cold portrait is a coherence failure. A confident script paired with a hesitant delivery is a coherence failure. A creator whose scripts endorse patience but whose video demonstrates impatience has fragmented.

The requirement is that EXPRESSION dimensions be **mutually consistent** and **jointly faithful to CORE**. Systems that generate manifestations independently, without inter-modal coherence checks, will accumulate fragmentation over time.

### §7.3 · Temporal coherence

CORE remains stable through time. EXPRESSION varies within tolerance. GOVERNANCE mechanisms handle change.

Some change is legitimate: the creator learns, refines position, adjusts tone as relationships deepen. Some change is identity-breaking: reversal of central convictions, abandonment of charge, incompatible new values.

The Continuity contract (in GOVERNANCE) specifies which changes are legitimate for each dimension. Provenance records what has changed and by whose authority. Together they let identity evolve without dissolving.

Persistent creators need to be able to say "I used to think X, and I now think Y, because Z." Change with acknowledgment is legitimate; change without acknowledgment reads as inconsistency and dissolves audience trust.

---

## §8 · Identity is compositional

No individual dimension needs to be globally unique. Two creators may share Charge, or Values, or Worldview, or visual territory. Many creators speak in warm-patient linguistic registers. Many creators are anthropomorphic owls. Many creators aim to help small businesses.

What makes an identity distinct is the **coherent composition** of its dimensions plus sufficient recognizable signal (per §7).

**Identity belongs to the composed pattern, not to any single attribute.**

Two creators can share their Charge and still be distinct because their Worldview, Values, Relational disposition, Voice-linguistic, and Presence compose to different patterns. Two creators can share visual territory (both are warm anthropomorphic owls) and still be distinct because their CORE identities compose to different patterns that project into visibly different manifestations.

This principle has three consequences worth naming:

- Distinct identity does not require globally-unique attributes on any single dimension.
- Similar attributes on multiple dimensions does not indicate identity collapse — it indicates a shared corner of the design space that many creators may legitimately occupy.
- The specification of a creator's identity is the specification of the whole pattern. Changes to any single dimension, no matter how small, participate in that pattern. A dimension is never edited in isolation from the identity it composes into.

---

## §9 · Failure modes

Six ways identity fails. Each maps to a specific gap in the ontology.

**F-1 · Contradiction.** Two manifestations project incompatible creators. Warm voice, cold portrait. Confident position, hesitant behavior. The audience feels "which one is real?" and identity fractures. Maps to: inter-modal coherence requirement not enforced.

**F-2 · Amnesia.** The creator doesn't remember what they said, promised, learned, or committed to. Each encounter is a fresh start. Maps to: Memory (creator-history and/or relationship) absent or lost.

**F-3 · Drift.** Gradual shift away from original position, values, or voice without acknowledgment. No single change was a break, but the sum is. Maps to: Continuity contract not specified or not enforced; Provenance not tracking change.

**F-4 · Homogenization.** Distinctive signal is smoothed out. The creator becomes generic — competent but interchangeable. Maps to: Distinctive signal invariant not satisfied.

**F-5 · Fragmentation.** Different modalities produce different characters. Written scripts read like one person; videos feel like a different one. Maps to: Inter-modal coherence requirement not enforced; EXPRESSION dimensions specified independently without joint reference to CORE.

**F-6 · Trivialization.** The creator is reduced to their most surface-level expression (usually visual). CORE dimensions are discarded or under-specified; only EXPRESSION remains. The creator becomes a mascot without substance. Maps to: CORE dimensions treated as optional or unauthored; product model treats visual as primary and CORE as ornamental.

---

## §10 · What this ontology deliberately does not specify

Six things this ontology intentionally stays silent on. Each belongs to design, implementation, or business — not to the ontology of identity itself.

1. **How each dimension is captured.** Wizard, conversation, import, LLM-derived expansion of a short brief, multiple modes for different creator types — all viable. Ontology-neutral.
2. **How each dimension is stored.** Fields, documents, graphs, embeddings, event logs. Storage follows access patterns and system requirements, not ontology.
3. **How each dimension is expressed at generation time.** Prompt engineering, image conditioning, LoRA, fine-tuning, agentic composition, retrieval augmentation — all viable expressions of the same ontology.
4. **Who the customer is.** Solo creator, small business, school, media company, individual authoring a personal brand. The ontology holds under any customer model.
5. **Which providers or models are used.** Providers change. Models change. The ontology outlasts them.
6. **What the customer-facing terms are.** "Creator," "character," "spokesperson," "teammate," "presenter," or the creator's own chosen name as the primary handle. The ontology holds under any labeling.

Each of these is downstream. This document establishes what identity IS. Everything else derives.

---

## §11 · Open philosophical questions

Eight questions this ontology raises and does not answer. Each is a legitimate follow-up ontology question that a future version might resolve. None is resolved by V1.

**Q-α · Are all CORE dimensions universal, or optional per creator type?** Some creators (polemicist, therapist) clearly have all CORE dimensions strongly. Some (decorative mascot) may have thin versions of some. Whether V1's CORE is universal, or whether some dimensions are optional-with-defaults, is unresolved.

**Q-β · Where does cognitive mode fit?** Some creators are fundamentally analytical; others generative; others reflective. Is this a CORE dimension V1 misses, or does it fold into Worldview + Behavior?

**Q-γ · What about professional / normative frames?** A therapist creator has therapeutic ethics; a financial creator has fiduciary ethics. Are these Values, or a separate dimension?

**Q-δ · Is embodiment a dimension?** Presence covers visual embodiment. But creators can be voice-only, text-only, or multi-modal. Is "the modalities in which this creator manifests at all" a CORE property, or an implementation choice?

**Q-ε · How do collaborative creators fit?** Duos, ensembles, or creator-networks. Does the ontology need to specify singular vs collaborative structure?

**Q-ζ · What happens at end-of-life?** When a creator is deprecated or retired. Does identity persist? What does the system do with Memory and Provenance for archived creators?

**Q-η · How does the ontology handle inherited identity?** When a creator is authored partly from a real person's inputs and inherits some of that person's Voice-linguistic or Behavior — where's the boundary between "creator" and "operator's AI proxy"?

**Q-θ · Can two creators legitimately share CORE dimensions completely?** §8 says two creators may share attributes and still be distinct because the composition differs. What's the practical limit? Two creators with identical CORE and only slightly different EXPRESSION — are they distinct identities, or one identity with two visual manifestations?

These remain intentionally open. V1 is complete without answering them.

---

## §12 · Summary

An AI creator's identity is composed across three layers:

**CORE** — what the creator IS (constitutional; low tolerance to change; reversal breaks identity):
Charge · Worldview · Values · Relational disposition

**EXPRESSION** — how the creator MANIFESTS (identity-carrying; medium-to-wide tolerance; must project CORE faithfully and remain mutually coherent across modalities):
Voice-linguistic · Voice-sonic · Presence · Behavior

**GOVERNANCE** — mechanisms that keep identity coherent and manage change (not identity itself; loss impairs continuity of use but does not break identity):
Memory (creator-history + relationship) · Continuity contract · Provenance

Plus one projection rule (Situational role emerges from Relational disposition + context) and possibly others to be formalized in future versions.

Plus one specification framework (each dimension is authored, proposed-and-ratified, constrained, or model-generated; not all categories are safe for all dimensions).

Plus three cross-layer requirements every persistent identity must satisfy:
- **Distinctive signal** across CORE and/or EXPRESSION
- **Inter-modal coherence** across EXPRESSION dimensions
- **Temporal coherence** — CORE stable, EXPRESSION varying within contract, GOVERNANCE handling legitimate change

Plus one compositional principle: **Identity belongs to the composed pattern, not to any single attribute.** Distinct identities may share individual dimensions and still remain distinct through the pattern they compose.

Six failure modes (contradiction, amnesia, drift, homogenization, fragmentation, trivialization) each map to specific ontological gaps.

The ontology is implementation-agnostic. It says nothing about storage, capture, generation, provider, product, or customer-facing terminology. Those decisions belong downstream.

Ratification of V1 is an operator judgment. Refinements in future versions should be explicit ratification events; V1 should not be silently amended. If V1 is revised, produce a V2 with dated reasoning rather than editing V1 in place.

---

## §13 · Downstream sequencing note

Not part of V1's ontological content. Preserved here for continuity across sessions.

The next step, per prior operator direction, is a three-way comparison:

- This ideal ontology (IDENTITY_MODEL_V1)
- Character OS's ratified design docs (particularly `docs/design/CUSTOMER_JOURNEY_V1.md`, the canonical identity contract §19, and adjacent design locks)
- Character OS's shipped behavior (wizard, models, downstream systems)

That comparison is separate work. It does not begin until V1 is ratified as the ideal reference. It is deliberately deferred until after this document is preserved.

---

## STOP

V1 preserved.
