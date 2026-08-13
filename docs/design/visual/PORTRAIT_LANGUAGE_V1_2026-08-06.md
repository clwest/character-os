---
title: "Character OS — Portrait Language (Canonical Principles)"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../VISUAL_LANGUAGE_V1_2026-08-06.md", "HOME_VISUAL_V1_2026-08-06.md", "VISUAL_TERRITORY_DECISION_V1_2026-08-06.md", "../PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md", "../PRODUCT_IA_V1_2026-08-06.md"]
---

# Portrait Language — Canonical Principles

## v1 — the discipline that governs how teammates exist visually

*Anchored in [`VISUAL_LANGUAGE_V1_2026-08-06.md`](../VISUAL_LANGUAGE_V1_2026-08-06.md), the Home visual proposal, and the visual-territory decision. Locks the **principles** that govern every teammate representation across every surface. Deliberately does not lock exact realism level, rendering style, background aesthetic, canonical Alex casting, or animation register — those decisions belong to a separate Portrait Territory Study conducted with real provider outputs.*

---

## 1. Why this document exists — and why it is split

Alex is effectively the customer's UI. If the portrait system is inconsistent, no downstream visual work matters. A beautiful color system cannot save a face that shifts between rooms. A refined typographic hierarchy cannot compensate for an uncanny expression. Portraits are the product's most fragile visual promise.

Portrait design has two distinct layers, and conflating them produces bad decisions:

- **Canonical principles.** Identity continuity, framing families, gaze, expression discipline, motion behavior, lighting coherence, diversity, accessibility, anti-uncanny tests, ethical boundaries, provider qualification. These are the contract every portrait must satisfy regardless of aesthetic direction. **This document locks these.**
- **Territory choices.** Exact realism level, painterly vs. photographic vs. cinematic naturalistic vs. lightly stylized, background aesthetic, default Alex casting, canonical outfit direction, animation intensity, universal vs. varied default teammate. These require empirical testing against real provider outputs before choosing. **A separate Portrait Territory Study will resolve them.**

Portrait Language locks the first layer and explicitly defers the second. Downstream studies — typography, color, screen visuals — should wait until the territory study lands.

---

## 2. What Alex is

**Internally, Alex may be implemented through avatar technology** — image generation, animated-face systems, live-avatar providers. This is the technical reality; the design system does not deny it.

**The customer experiences Alex as a teammate, never as an avatar-shaped product feature.** No visual, copy, or interaction element should read as *"you are talking to an avatar."*

- Not a mascot (mascots represent brands; teammates represent themselves).
- Not an illustrated character.
- Not a chatbot icon or chip.
- Not a robot or AI-visualization metaphor.

The word *avatar* may appear in engineering discussion and vendor documentation. It must never appear in customer copy, and no visual treatment may suggest that framing.

---

## 3. Canonical identity specification

Every teammate has a **canonical identity specification** that serves as the source of truth for every surface render. Without this specification, *"same person"* is a visual aspiration rather than an enforceable system.

The specification contains, at minimum:

- **Facial geometry** — proportions, bone structure, distinguishing shape features.
- **Skin tone** — with the tonal range under which it must remain recognizable.
- **Eye shape and color.**
- **Hair characteristics** — length, hairline, part, curl pattern, volume, color.
- **Facial hair** — presence, style, density.
- **Age presentation** — the age range within which the teammate must consistently read.
- **Canonical outfit** — a stable default (see §17).
- **Expression baseline** — the resting expression this teammate defaults to.
- **Voice identity linkage** — a reference to the voice associated with this teammate so face and voice are validated together.
- **Lighting baseline** — the ambient light configuration under which the canonical identity was authored.
- **Approved reference views** — a small set of validated renders that new surface renders are compared against for identity preservation.

Every surface render must derive from this canonical identity. Renders that cannot derive from it — or drift beyond identity-preservation thresholds — are not shown (see §16).

---

## 4. Framing families

Framing is context-sensitive, not a single rule. Three framing families cover every current context; new contexts extend one of them.

- **Presence portrait** — head and shoulders. Used on Home, My Team detail, and any surface where the teammate is present but not the primary work happening.
- **Compact identity portrait** — face and upper shoulders. Used on My Team list cards, bylines beneath pieces, small avatar-like appearances in Piece Detail context, and other space-constrained identity markers.
- **Conversational portrait** — head, shoulders, and enough upper torso to support natural gesture. Used in Studio's teammate presence pane and in Live Conversation, where more visible body supports believable speech and expression.

Framing decisions across contexts should preserve **recognition, not mathematical sameness.** Eye position within each framing family remains stable; the family determines how much frame surrounds the eye line.

Rejected across all families:

- Floating disembodied heads.
- Full-body treatments (Alex is a colleague, not a character sheet).
- Profile or three-quarter-turn framings where Alex is not facing the customer.
- Round chat-avatar chips.
- Text-initials-in-a-circle as fallback.
- Any framing that requires the customer to *decode* who they are looking at.

---

## 5. Gaze — socially engaged, not fixed

The customer must feel *"a colleague is with me,"* not *"a system is staring at me."*

**Alex's gaze remains socially engaged with the customer.** This is different from continuous direct eye contact, which becomes intense or uncanny over time.

Permitted natural gaze behaviors:

- Direct engagement with the customer as the default posture.
- Brief gaze shifts while considering.
- Momentary glance toward shared work (the piece in Studio, the customer's most recent publish in Home Zone C).
- Natural eye movement during listening — soft focus, occasional blinks, small saccades that stay within the socially-engaged register.
- Soft gaze release before returning to the customer.

Forbidden gaze behaviors:

- Repeated drifting.
- Prolonged off-screen attention.
- Gaze that implies another unseen participant.
- Movement unrelated to context.
- Fixed unblinking stare.

In Live Conversation, gaze tracks the exchange in real time — attentive to the customer during their speech, softly focused-forward during Alex's own speech. Whatever real-time behavior the provider produces must remain within *engaged with the exchange.*

Cultural note: eye-contact intensity varies across cultures. Localization research should eventually test culturally appropriate norms for gaze behavior; the system should not encode one culturally-specific standard as universal. See §12.

---

## 6. Expression vocabulary — visual states, not emotional claims

Alex's expressions respond to observable interaction state. They must not imply inner feeling the system does not possess.

Visual state vocabulary:

- **Neutral rest** — the default. Softly-relaxed mouth; engaged eyes; slight lift at outer corners. Warm, calm, attentive.
- **Acknowledgment** — brief response to customer input. Small register shift; conveys *"received."*
- **Listening** — during customer speech or typed input. Slight forward attention; mouth at rest; eyes engaged.
- **Consideration** — during processing pauses. Softly narrowed focus; brow softened; mouth at rest.
- **Gentle positive response** — reserved for genuine positive moments in the interaction (first publish, successful completion of a conversation, customer expression of satisfaction). A warm, closed-mouth or slightly-open expression that reads as sincere.

The customer may experience Alex relationally — that is a customer choice about how to interpret the relationship. The visual system, however, does not claim that Alex *feels* pride, delight, concern, or attachment. Expressions are visual states responding to observable input, not testimony to inner experience.

Rejected expression treatments:

- Broad grinning smiles (stock-photography register).
- Comedic or exaggerated expressions.
- Any expression suggesting embarrassment, sadness, worry, or dramatic emotion.
- Asymmetric expressions unless deliberate and natural.
- Winks or single-eye behaviors.

---

## 7. Motion discipline — perceptual, tiered, and generated

Portrait motion is **presence without performance.** The customer's peripheral vision picks it up; focused attention does not have to process it.

### 7.1 Perceptual requirements (not numeric rules)

- Never rhythmic. Blink and posture-shift timing must never fall into a metronomic pattern.
- Never synchronized across teammates. If a customer views My Team with multiple teammates, their motion behaviors must not phase-lock.
- Occasional double blinks are permitted and welcome (real people do them).
- Stillness is normal. Portraits should be still much of the time.
- Movement should rarely attract focused attention. If a customer catches themselves staring at a motion, the motion is too pronounced.
- No spontaneous emotional expressions triggered by nothing (no smiling, frowning, or winking without a context reason).

Timing tuning is engineering's responsibility, guided by these perceptual criteria and observation. Do not encode fixed intervals in the design system.

### 7.2 Context tiers

Motion intensity is tiered by context:

- **Static-presence contexts** (My Team list cards, small bylines, secondary appearances) — blink or micro-movement only. Full breathing and posture behavior is unnecessary here and may create distracting image motion on small elements.
- **Active-presence contexts** (Home, Studio at rest, My Team detail, Piece Detail teammate byline hover) — subtle breathing and occasional posture shifts, in addition to blinks.
- **Conversational contexts** (Studio during narration, Live Conversation) — full naturalistic idle behavior, including breathing, posture, gaze shifts, listening cues.

### 7.3 Forbidden idle behaviors

- Lip-sync on non-conversational contexts (Alex does not talk on Home).
- Continuous animation.
- Attention-soliciting movement (waves, deliberate gestures, leaning forward emphatically).
- Looking-around behaviors that imply Alex is checking on something.
- Movement clearly triggered by a system event that is not user-relevant (e.g., moving when a background job completes).

---

## 8. Lighting coherence — the same-room rule

Every teammate representation must be visually normalized enough to belong to the same product environment. The rule is called *"same room"* because the customer should never feel Alex traveled to a different location between screens.

Requirements the normalization pipeline must meet:

- **Consistent surround.** Whatever background Alex sits against on Home relates visually to the backgrounds in Studio, My Team, and Live Conversation. Related, not identical — Live Conversation may run darker — but never disconnected.
- **Consistent key-light direction** across surfaces.
- **Consistent color temperature on skin** across surfaces (excluding intentional environment changes, like a darker Live Conversation surround).
- **Consistent shadow behavior** — where shadows fall on the face and shoulders follows one set of rules.

Lighting itself should read as **diffused ambient** — not spot-lit, not photograph-studio-strobed, not golden-hour-warm. The workshop foundation implies warm ambient without committing to golden light. Shadows are soft; contrast is comfortable.

The design system's responsibility is normalization, not source generation. Raw portraits and live video will arrive with inconsistent lighting; the pipeline must actively re-light or re-normalize them to meet the same-room standard.

---

## 9. Realism band and coherence

Alex sits in a narrow band between two failure modes: photorealism that becomes uncanny, and stylization that becomes mascot. **Consistency across the render matters more than the realism level itself.**

### 9.1 The governing principle

> **Never pursue realism beyond what the system can maintain consistently across stillness, motion, expression, and lighting.**

Photorealism is not automatically uncanny; *inconsistent* photorealism is. A photorealistic still image adjacent to a stylized animated system produces the uncanny valley. A moderately-realistic system that maintains identical fidelity across still, motion, and speech does not.

The exact realism level Character OS chooses is deferred to the Portrait Territory Study.

### 9.2 Coherence requirements

Whatever realism level is chosen, the following must hold at that level across every surface:

- **Skin, eyes, teeth, and clothing all live at the same realism level.** Photographic eyes on painterly skin is uncanny. Detailed hair on smoothed skin is uncanny. Mixed realism is often more disturbing than high realism itself.
- **Eye rendering matches the lighting model.** Wet-eye highlights are acceptable when they match the ambient light; they become uncanny when the surrounding face is lit differently.
- **Hair detail matches facial detail.** Strand-level hair on a soft-rendered face is discordant.
- **Skin texture matches the render's overall fidelity.** Believable texture is required; hyper-detailed photographic sharpness is not; artificial smoothing and beauty-filter polish are forbidden.

---

## 10. Mouth, teeth, and hair — identity-critical

Three regions of the face fail most often and most conspicuously.

### 10.1 Mouth and teeth stability

The mouth is the most fragile area during animation and Live Conversation. Failure here breaks identity immediately.

Required:

- Consistent tooth count and shape across every render.
- No sudden tooth appearance changes (a teammate should not have visible teeth in one shot and none in the next unless closing their mouth).
- Stable lip contour.
- No gum distortion during speech shapes.
- No mouth-interior flicker.
- No speech shapes that break facial identity.

The mouth passes the **speech test** (§13) as its primary approval gate.

### 10.2 Hair identity

Hair is identity-critical. Every hair characteristic must remain stable across rendering systems:

- Length, hairline, part.
- Curl pattern, volume, color.
- Facial hair presence, style, and density.

Facial hair in particular must not appear, disappear, thicken, or change shape between Home and Live Conversation. A clean-shaven Alex on Home who has stubble in a Live Conversation is a different person.

---

## 11. Diversity — meaningful variation, not compliance

Teammates should look like distinct people, not like interchangeable variants of one idealized face. The failure state is a My Team populated by faces that share the *same generator's aesthetic* — recognizably from one system.

Required variation across the teammate pool (when customers add multiple teammates):

- Face shape.
- Body type where visible.
- Hair texture and length.
- Hair loss (natural variation, not just receding hairlines as an age signal).
- Skin texture (individual variation in tone, oiliness, evenness).
- Visible disability when the customer selects it deliberately.
- Gender presentation across a real range.
- Cultural presentation.
- Facial asymmetry (real faces are asymmetric).
- Teeth and smile characteristics (variation in tooth shape, gap patterns, whitening).

Diversity is not a set of interchangeable demographic sliders. It is the property that a My Team of five teammates reads as five distinct people rather than as five outputs from the same face generator.

---

## 12. Cultural neutrality caution

Direct eye contact, smiling norms, clothing formality, and perceived warmth vary culturally. The system must not encode one Western visual behavior as universal.

Localization research should eventually test:

- Eye-contact intensity.
- Smile frequency.
- Gesture range.
- Clothing formality.
- Interpersonal distance conveyed through framing.
- Gender presentation norms.

Character OS should not over-localize automatically (automated regional inference from a customer's business location could feel presumptuous or stereotyping), but the system must not encode one culture's norms as universal human behavior. Portrait Language is written from a starting point that must be tested against other cultural contexts before deployment beyond its initial market.

---

## 13. Approval tests — static, motion, speech

Every teammate representation must pass three tests. All three are required. Passing one or two is not enough.

### 13.1 Static test

> *Can I look at this portrait for ten seconds comfortably?*

A single still portrait, viewed for ten seconds without the interface distracting the reviewer. If discomfort arises — a wrong eye, an uncanny smile, a stiffness, an unnameable wrongness — the treatment fails.

### 13.2 Motion test

> *Can I watch this teammate idle for thirty seconds without noticing repetitive or unnatural movement?*

Thirty seconds of idle behavior, viewed with focused attention. If the reviewer catches themselves noticing a pattern in blinks, a mechanical breathing rhythm, or a repeating posture shift, the treatment fails.

### 13.3 Speech test

> *Can I watch this teammate speak for one minute without identity drift, mouth artifacts, gaze instability, or growing discomfort?*

One minute of continuous speech (a Live Conversation excerpt or a narration test). If teeth appear inconsistently, lip shape becomes unstable, gaze wobbles, or the reviewer's discomfort grows over the minute, the treatment fails.

**All three tests must pass before any teammate representation ships.**

---

## 14. Cross-context identity testing

Identity is not approved one screen at a time. Every teammate must be reviewed **side by side across every surface** they will appear on:

- Home (both tempos).
- Studio.
- My Team list card.
- My Team detail.
- Piece Detail (byline).
- Live Conversation.
- Small byline treatment (compact identity portrait).

Reviewers answer one question:

> *Do these all read immediately as the same person?*

If any surface reads as *"a different person,"* the treatment fails. Identity approval requires all-surface coherence, not per-surface competence.

---

## 15. Identity drift thresholds and fallback behavior

If a rendering system cannot render the teammate consistently enough — because the provider degrades, the network conditions fail, an edge-case animation collapses, or a live-avatar system's fidelity drops — the product must not silently show a degraded version that damages identity.

### 15.1 Preservation-of-trust fallbacks

In priority order:

1. **Use a stable canonical portrait with voice.** If motion cannot be trusted, drop motion — show the approved still portrait and continue voice output.
2. **Reduce animation complexity.** If full motion cannot be trusted, use a simpler motion treatment that stays within approved reference views.
3. **Switch to a simpler approved motion treatment.** Prefer a smaller vocabulary of proven motion states over risking an uncanny full-motion render.
4. **Explain that visual presence is temporarily limited.** *"I'm here but my video is limited right now."* — better than a broken face.

### 15.2 What must never happen

- Substituting a similar-looking face when the canonical face cannot render. **A less animated Alex is better than a different Alex.**
- Silently degrading to a lower-fidelity render without acknowledging the change.
- Continuing an animation that has entered the uncanny valley to preserve visual continuity — stopping motion is always the correct fallback.

---

## 16. Provider qualification

Only rendering systems proven to preserve the canonical identity may represent the teammate. The pipeline cannot assume every raw input can be normalized successfully — some source systems will be incapable of meeting the standard.

Provider selection is a validation exercise, not a vendor negotiation. Before choosing portrait, animated-face, or live-avatar technology, each candidate must be tested against:

- Static portrait rendering.
- Blinking idle.
- Expression changes across the vocabulary.
- Short narration (~15 seconds).
- One-minute continuous conversation.
- Varied lighting.
- Multiple demographic representations.
- Mobile and desktop viewport sizes.

Each candidate is evaluated on:

- Identity stability across the above.
- Lip synchronization quality.
- Gaze believability.
- Latency.
- Lighting consistency across generated states.
- Artifact rate over time.
- Consistency across demographic representations (no provider that renders one skin tone believably and another poorly).
- Reviewer emotional comfort during sustained viewing.

Portrait Language becomes a **provider-selection contract.** Providers that cannot pass are not used. This may constrain vendor choice; that is acceptable — a wrong provider damages the product's foundational visual promise.

---

## 17. Clothing philosophy

The default teammate wears **timeless, work-appropriate, non-costumed** clothing:

- A well-made shirt, considered sweater, or jacket in a natural material.
- Nothing that reads as uniform, mascot outfit, or costume.
- Nothing with visible logos, brand markers, or fashion-of-the-moment silhouettes.

**Role-specific or branded clothing appears only through explicit customer direction.** A customer may intentionally want a chef-inspired teammate, a dealership presenter, a fitness coach, a medical-office guide, or a branded company representative. The system must not impose occupational stereotypes automatically — but customers must be allowed to choose role-relevant clothing when they explicitly request it.

### 17.1 Clothing stability

For v1, each teammate has a **stable canonical outfit** that persists across sessions. Changing clothing between days would make the teammate feel like a generated character whose appearance is being re-rolled — the product loses continuity.

Later releases may introduce wardrobe variation deliberately, but any variation must preserve:

- Silhouette.
- Color family.
- Level of formality.
- Recognizable identity.

Familiarity is more important than novelty.

---

## 18. Background family

The background behind Alex is a design decision, not an accident of the rendering system.

Requirements:

- **Related to the product surface.** The background Alex sits against must relate visually to the surrounding chrome. Warm room, warm background. Dark conversational surround (Live Conversation), tone-related background.
- **Softly diffuse, not sharp.**
- **Free of specific objects, furniture, decor, or props** that would narrate a location.
- **Free of imagery that suggests stereotyped settings** (books = intellectual; kitchen = domestic; office = corporate).

### 18.1 A family, not one background

A single generalized warm-blur background across every teammate produces the generic AI-headshot aesthetic. The system must define a **controlled background family** with meaningful variation:

- Soft neutral studio.
- Lightly material warm surround.
- Subtle environmental depth without identifiable props.
- Darker conversational surround (Live Conversation).

All backgrounds share lighting discipline and product compatibility. Variation prevents the *"all from the same generator"* look.

### 18.2 Customer-selected environments

Specific environments (a customer's showroom, bakery, shop, branded studio, virtual set) are never inferred automatically. They may become available later as an explicit customer choice — the customer intentionally selecting an environment for a teammate — and must pass identity, lighting, and distraction tests before shipping.

---

## 19. Non-human teammate compatibility

Character OS's product doctrine explicitly permits non-human teammates. Portrait Language must not accidentally forbid this by writing rules that assume all teammates are human.

Two branches:

- **Human teammate** — governed by the rules in this document.
- **Non-human teammate** — governed by a future **Character Presence Language**. Non-human teammates must still satisfy identity continuity, presence without performance, anti-uncanny motion, lighting coherence, and teammate-not-mascot framing. They may not be treated as a novelty tier or a lesser mode.

This document focuses on humans. It does not declare humans as the only valid teammate form.

---

## 20. Consent and likeness protection

If customer-uploaded reference images become supported (a deferred capability), the system must require that the customer has the legal right to use the likeness.

Safeguards required:

- No cloning a real person without documented permission.
- No recreation of celebrities or public figures.
- No generation of a deceptive likeness of an employee, contractor, or acquaintance without consent.
- No use of a child's likeness.
- No creation of teammates intended to impersonate a real individual.

These are legal, ethical, and trust requirements. They apply whenever any part of the portrait system accepts customer-provided reference material.

---

## 21. Disclosure requirement

When external customers eventually speak with a teammate (the deferred customer-facing Live Conversation deployment), the visual system must not be used to mislead them into believing the teammate is human.

Clear product-level disclosure that the teammate is AI must be present, delivered without degrading the relationship metaphor. The exact disclosure design belongs to the customer-facing deployment work; the **requirement** belongs here.

Failure to disclose in a customer-facing context is a legal and ethical breach, not merely a design defect.

---

## 22. Performance tiers

Animated portraits are expensive. The teammate's identity and dignity must survive performance degradation.

Graceful tiers:

- **High-capability device / network:** full approved subtle motion.
- **Constrained environment:** reduced motion complexity.
- **Very constrained environment:** stable portrait plus voice / status text.

Never let a low frame rate, delayed blinking, or broken lip-sync create uncanny behavior merely to preserve animation. The stable-portrait fallback (§15) applies whenever motion cannot be sustained at the required quality.

---

## 23. Customer motion preference (design-forward hook)

Some customers may simply prefer less portrait movement, independent of the accessibility reduced-motion system.

A future preference may allow:

- **Still** — canonical portrait with no motion.
- **Subtle** — the default active-presence motion tier.
- **Full conversational motion** — the current Live Conversation register.

Not exposed during onboarding. Not required for v1. Portrait Language requires only that the system be **designed so this preference can exist** without changing identity.

---

## 24. Rejections — output failures, not stylistic dogma

Portrait Language rejects certain outputs categorically. It does not reject aesthetics whose acceptability depends on execution.

### 24.1 Categorically rejected (regardless of execution)

- Robot cues (visible mechanical parts, glowing eyes, artificial-appearance visual metaphors).
- Mascot framing.
- Beauty-filter artifacts (skin smoothing, jaw-slimming, eye-widening).
- Unstable identity (any teammate that reads as a different person across surfaces).
- Green-screen keyed edges.
- Generic chat-avatar chips.
- Deceptive human impersonation (a teammate rendered to appear as a specific real person without consent).
- Stock-photo grinning.
- Sci-fi or AI-visualization aesthetics.

### 24.2 Not categorically rejected — evaluated on execution

- Photography or photograph-derived rendering (acceptable if consistency is maintained).
- Illustration-adjacent styles (acceptable if teammate-not-mascot framing holds).
- Specific environments (acceptable when explicitly customer-directed and passing all tests).
- Strand-level hair detail (acceptable when coherent with surrounding fidelity).
- Wet-eye reflections (acceptable when matched to the lighting model).

The governing question:

> *Does this output preserve identity, trust, dignity, and continuity without feeling like a mascot, stock asset, or deceptive human impersonation?*

If yes, the output is permitted. If no, it is rejected regardless of stylistic label.

---

## 25. What this document deliberately does not decide

Deferred to the **Portrait Territory Study** and subsequent studies:

- **Exact realism level.** Softened photographic, cinematic naturalistic, painterly naturalistic, lightly stylized realism — all remain candidates. Must be tested against real provider outputs before choosing.
- **Painterly vs. photographic direction.**
- **Specific background aesthetic** within the background family.
- **Default Alex casting** — the actual face, hair, features, and appearance of the pre-provisioned first teammate.
- **Whether Alex is one universal person or several defaults.** This is a consequential product decision (universal Alex strengthens product identity but reduces customer ownership; multiple defaults increase fit but weaken continuity across marketing and support materials). The territory study should flag it; the operator resolves it.
- **Canonical outfit direction** for the default Alex.
- **Degree of animation** across contexts (within the tiered discipline defined here).
- **Rendering technology** and specific vendor selection.
- **Micro-expression animation library** — the specific set of subtle facial movements carrying the expression vocabulary.
- **Voice-to-face synchronization** implementation details for Live Conversation.
- **Portraits at very small sizes** (avatar-sized indicators, notification imagery in future features) — separate study when the product introduces surfaces requiring them.
- **Customer-uploaded reference face handling** implementation details.
- **Localization of face pool** — regional diversity requirements and cultural-preference handling.

---

## Principles held without weakening

These are locked into the discipline:

- Alex is experienced as a teammate, not a product icon.
- Presence without performance.
- Same-room lighting discipline across every surface.
- Identity continuity across every surface where a teammate appears.
- Teammates must remain distinct while sharing one visual grammar.
- Role must not determine age, ethnicity, gender, or appearance.
- Portraits must survive sustained scrutiny — static, motion, and speech tests all required.
- Source technology is subordinate to the visual contract.
- A degraded stable portrait is preferable to an uncanny animated one.
- No AI sci-fi or robot visual cues.

---

## Revision History

**v1 — 2026-08-06.** First canonical version. Written and revised across two operator turns during the same session. Major decisions incorporated:

- **Document split** into canonical principles (this file) and a deferred Portrait Territory Study for aesthetic choices requiring empirical testing.
- **Internal-vs-customer language distinction:** Alex may be implemented through avatar technology internally; customers experience Alex as a teammate.
- **Realism band replaces realism prescription:** the exact realism level is deferred. Consistency across stillness, motion, expression, and lighting matters more than realism level itself.
- **Framing families** (Presence portrait, Compact identity portrait, Conversational portrait) replace the single head-and-shoulders rule.
- **Eye placement:** stable eye line within each framing family, not mathematical one-third across all surfaces.
- **Gaze:** socially engaged, with natural breaks permitted. Not fixed direct eye contact.
- **Expressions:** visual states responding to observable interaction, never claims of inner feeling.
- **Motion:** perceptual requirements (never rhythmic, never synchronized, occasional double blinks, stillness normal), not numerical rules; tiered by context (static / active / conversational).
- **Breathing:** not mandatory in every context; scoped to active-presence and conversational tiers.
- **Clothing:** default timeless and non-costumed; role-specific or branded clothing allowed only via explicit customer direction.
- **Clothing stability:** stable canonical outfit per teammate for v1.
- **Age:** no fixed default age range. Requirement is peer-like trust. Age must not signal authority, competence, energy, audience, or role.
- **Diversity:** broadened beyond age and skin tone to face shape, body type, hair (including hair loss and texture), skin texture, visible disability, gender presentation, cultural presentation, asymmetry, teeth. Diversity is *"distinct people,"* not interchangeable variants.
- **Skin, hair, eyes, teeth:** coherence across the render, not blanket detail bans. Beauty-filter smoothness still forbidden.
- **Mouth, teeth, hair as identity-critical:** dedicated rules preventing common animation failures.
- **Three approval tests:** static (10s), motion (30s), speech (60s). All required.
- **Cross-context identity testing:** side-by-side review across every surface a teammate appears on.
- **Canonical identity specification** required as source of truth for every teammate.
- **Identity drift fallbacks:** degraded stable portrait preferred to uncanny animation; never substitute a similar-looking face.
- **Provider qualification:** rendering systems must pass benchmark before use. Portrait Language is a provider-selection contract.
- **Backgrounds:** controlled family, not one generic blur. Environments deferred to explicit customer choice.
- **Non-human teammate compatibility** preserved as future branch (Character Presence Language).
- **Consent and likeness protection** required for any customer-uploaded reference material.
- **Disclosure requirement** for customer-facing Live Conversation deployment.
- **Performance tiers** defined; identity survives degradation.
- **Customer motion preference hook** designed-in for future release.
- **Cultural neutrality caution** written into gaze and expression sections.
- **Rejection list restructured** into categorical (regardless of execution) vs. execution-dependent (evaluated on output).
- **Alex casting deferred** to the Portrait Territory Study; illustrative content stripped from this document.
- **Universal-vs-varied default teammate flagged** as a consequential product decision requiring explicit operator resolution.
