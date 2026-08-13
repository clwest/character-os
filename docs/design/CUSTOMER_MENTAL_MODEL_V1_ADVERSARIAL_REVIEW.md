# CUSTOMER_MENTAL_MODEL_V1 — ADVERSARIAL SELF-REVIEW

> **Later ontology (added 2026-08-08):** SESSION 250 later produced
> [`IDENTITY_MODEL_V1.md`](IDENTITY_MODEL_V1.md), an
> implementation-agnostic ontology that resolves several of the
> concerns this adversarial review flagged (F4 object model, F5
> universal noun) at the ontological layer. This adversarial review
> remains preserved unchanged as design history from its point in
> time. The reading order for the full design-history arc lives in
> [`CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`](CUSTOMER_EXPERIENCE_REVIEW_INDEX.md).

**Status:** critique artifact (companion to `CUSTOMER_MENTAL_MODEL_V1.md`)
**Purpose:** stress-test the design document before it becomes a design-lock candidate; preserve the reasoning that pressure-tested the proposal so future ratifications are conscious rather than silent
**Method:** adversarial self-review of my own prior output, structured around 8 target areas requested by the operator (evidence-vs-hypothesis, product-language-vs-GTM, product-vs-surfaces, three-object-model, universal-noun, IA, data-and-providers, ratification-readiness)
**Companion:** `docs/design/CUSTOMER_MENTAL_MODEL_V1.md` (the proposed customer model this review critiques)
**Non-goals:** does not rewrite the design document; does not resolve unresolved questions; does not modify code or open any implementation
**Ratification protocol:** if any recommendation in this review is folded into the design document, it should be done consciously — the folding session should reference this artifact so the reasoning is not lost

---

## How to read this document alongside the design doc

`CUSTOMER_MENTAL_MODEL_V1.md` is the proposed customer model. This document is the critique of that proposal.

Both are preserved intentionally. When a future session decides to ratify any part of the design document, this review is the record of what was known to be uncertain, overreaching, or premature at the time of the proposal. That record is load-bearing: if a design lock is later ratified without accounting for a finding in this review, the reviewer should know they are consciously overriding a recorded concern rather than accidentally forgetting one.

The recommendations in this document (edits E1-E9, wording precision table) are proposals only. They should not be silently folded into the design document. Any adoption should be an explicit ratification event.

---

## Findings

### F1 · The persona review is treated as customer research more often than it should be

Throughout `CUSTOMER_MENTAL_MODEL_V1` I made statements of the form "5-7 of 10 personas reject the noun," "8/10 personas can complete without help," "no persona thinks in this term." These read as empirical findings but they are not. They are **the fractional distribution of adverse reactions I simulated when I authored 10 persona voices reacting to shipped SPA copy.** That is design pressure-testing — a real and useful method — but it is not customer research.

Two specific overreaches:

- The document reads as though the persona review *establishes* that words like "spokesperson," "render," and "composition" alienate specific fractions of the audience. What it actually establishes is that a design-sensitive reviewer, imagining first-time reactions across a diverse cast, expected those words to alienate those fractions. The fractions are illustrations of range, not measurements.
- The document occasionally implies that the wizard and welcome page work for real users ("delightful experience 8/10 personas can complete without help"). We have not tested this. The wizard has clear copy and a well-shaped step model; that is a design observation, not a completion-rate measurement.

The intellectually honest framing is: **the persona review surfaces plausible failure modes; each is a hypothesis worth validating with real users; the value is in the range of concerns exposed, not in the specific counts.**

### F2 · Product language (UX) and go-to-market strategy (business) are conflated in several places

Two independent questions blur in the document:

- **UX question:** Can an intelligent non-technical person read this page and understand what it does?
- **GTM question:** Who is Character OS's initial ideal customer?

These are related but not the same decision. Plain language benefits every audience — including technical users, who prefer clear terms when precision isn't required. So the UX question can be answered without settling the GTM question. But the document sometimes lets the GTM question drive UX conclusions:

- §7 Q-3 frames the GTM target as a determinant of vocabulary scope ("If Q-3 lands on 'technical creator/consultant' the current product is closer to right"). That's not accurate. Even in a technical-creator market, "provision" and "bake" and "K6.4" are not defensible as customer labels — a technical user still recognizes "provision" as IT-server-speak and "K6.4" as internal versioning.
- §4.1's "leaning toward 'character' aligned with the product name" is a branding/GTM instinct dressed as a UX finding. It may be right, but the reasoning is marketing (alignment with product name), not UX evidence.
- §11's "recommended next actions" tie the whole UX roadmap to the GTM decision. In fact the vocabulary and IA improvements should mostly be independent of the GTM answer.

The document should say clearly: **plain-language and operator-surface-gating hold regardless of GTM target. Only the *elaboration* of vocabulary (e.g., whether to use "character," "creator," or "presenter" as marketing surface term) depends on GTM.**

### F3 · "Two products" is inaccurate; "two surfaces of one product" is what we actually mean

§5.1 calls the customer product and operator product "two entirely separate products." That framing implies market separation ("we sell A to customers and B to operators") which is wrong. Chris is a real example: he is simultaneously the operator, the developer, and a proxy customer. A future support engineer troubleshooting an issue may need to see both surfaces in the same session.

The accurate framing is: **one product, with a set of surfaces gated to staff users**. The staff surfaces are not lesser or peripheral; they are legitimate parts of the same product, held to different tone standards because their audience differs.

This distinction matters because "two products" invites a mental model of full separation (separate URLs, separate branding, separate teams), which is not what the operator problem requires. Gating and vocabulary-tone-per-surface is enough.

### F4 · The three-object model may hide two important customer concepts

§3's model — Your AI / What it knows / What it makes — is a clean simplification, but pressure-testing surfaces two hidden concepts:

- **Interactions (live conversations and chats).** I filed these under "what it makes," but a live conversation is not "made" in the same sense as a video. It is an **event**. The customer perceives having-a-conversation as fundamentally different from making-a-video. Collapsing them under one object obscures the difference.
- **Plans (campaigns).** I glossed campaigns as an output type, but a campaign is neither a source nor a made-thing. It is a **plan or a run** — a batching of outputs across recipients. It has its own lifecycle (draft → in-flight → complete) unlike a single video.

Two possible corrections:

- Expand to five objects: Your AI · Sources · Outputs · Interactions · Plans.
- Or acknowledge that **the customer's actual mental model is jobs, not objects.** Users think "I want to make a video today" or "I want to have a live chat" or "I want to send a batch" — not "I want to work with my Interactions object." Object models are useful for designers reasoning about state, not for customers reasoning about tasks.

The document currently presents the three-object model as if it captures the customer's mental map. It probably captures a designer-friendly reduction. Different thing.

### F5 · The universal-noun question was framed too narrowly

§4.1 poses the question as "which class term replaces 'spokesperson'?" but the deeper question is: **does the product need a universal class noun at all?**

Evidence that it might not:
- The wizard already asks the customer to name their creation.
- The sidebar shows names (Bean, Pastor Dan Video, The Docent) — a class label isn't required.
- In flows, the system uses the name back ("Meet Bean") — no class label required.
- Empty states DO need a phrase ("Build your first ___"), but that phrase can be tone-appropriate to the specific empty state ("Build the AI presenter your business will use" vs "Create the character for your class") rather than forcing a single class term everywhere.
- Marketing and documentation DEFINITELY need a class term. But that is a marketing question, not a customer-experience question.

If we accept this, the noun problem shrinks: it's not "pick the right class term for every surface"; it's "**stop using 'spokesperson' in customer surfaces; use the customer's chosen name wherever possible; use a tone-appropriate phrase in the few places where a phrase is genuinely required; pick a marketing/documentation term as a separate decision.**"

Direction B in §4.1 gestures at this but doesn't commit. The stronger statement is: **the product may not need a universal class noun at all in its customer surfaces.**

### F6 · The IA section crossed from principle into implementation

§5.2 proposes six nav items ("Home / Your team / Sources / Make / Library / Campaigns"). This is nav design, not a design principle. Several of the items don't clearly earn their place:

- **"Make"** as a destination — really? Or is "make a video" an action available from multiple places (button on the AI's page, button on the Home dashboard, button on an empty library, keyboard shortcut)? Compare Notion, Figma, Google Docs — none has a "Make" tab; "new" is an action, not a place. The recipes-gallery-as-a-picker could be a modal, not a destination.
- **"Library"** as a top-level nav — versus a filter on a single detail page, versus a section on Home, versus a search affordance.
- **"Your team"** — is the plural of the AIs a first-class destination, or is it just visible on Home when you have more than one?
- **"Sources"** — plausible as a destination for professional-services users (who need to audit what's been uploaded), less plausible for creators (who upload once and forget).

The **principles** underlying my IA proposal are ratifiable:
- Operator surfaces gated to staff.
- Assets / Videos / Compositions / Bundles overlap is real and should be resolved before further additions.
- Video detail should be primary; engineering internals behind progressive disclosure.
- A single unified browse experience for outputs (whatever it's called and however it's surfaced).

The **specific nav proposal** is not ratifiable yet; it depends on choices about how much the product wants to reward navigation (destination-heavy) vs action (contextual-affordance-heavy).

I collapsed these two levels in §5.2. They should be separated.

### F7 · The Data & Providers acceptance criterion is inconsistent with the unresolved question

§7 Q-4 correctly flags Data & Privacy as unresolved ("These are business-and-legal decisions the design cannot make on its own"). But §9.2 makes a mandatory acceptance criterion: "A Data & Providers surface exists (even if minimal — see Q-4) and is linked from the primary sign-up and from every ingest flow."

If the substance is unresolved, we can't require the surface. Two paths to consistency:

- Downgrade the criterion to something like: "The product's IA has a *reserved position* for a Data & Providers surface, whose contents are conditional on Q-4's resolution." (Weaker but honest.)
- Drop the criterion entirely and let Q-4's resolution add it back with real substance.

Either way, the current version overpromises. A promise the product cannot truthfully make is worse than no promise; if we mandate a surface without content, we compound the trust problem the therapist/dentist/accountant personas surfaced.

### F8 · Language of certainty is uneven

The document uses phrases like "unrecoverable," "will always feel wrong," "cannot be recovered," "the most consequential vocabulary decision." Some of these are appropriate to design-lock language; several run ahead of the evidence.

Examples:
- "The word 'spokesperson' should be retired from customer surfaces irrespective of which direction is chosen. It is unrecoverable for the majority of target users." — "Unrecoverable" is a strong claim from a persona-simulation reviewer. "Likely to be a persistent friction for a wide range of non-technical users" is more honest.
- "The verifier is a moat AND a wall." — Rhetorical. Accurate spirit; overstrong phrasing for a design doc.
- "The onboarding tour is the product's best surface AND uses its worst vocabulary at the highest-stakes moment." — Compact and defensible; keep.
- "There is a real product here." — Reasonable observation, but "real product" is not defined; downgrade to "the shipped product has clear PMF signals with some persona sketches and none with others."

The document is stronger when it distinguishes what it knows from what it suspects from what it recommends.

---

## Recommended edits (specific, surgical)

### E1 · Add a "How to read this document" preamble

Between the frontmatter and §1, add a short block:

> **Reading contract.** This document is design pressure-testing built on a 10-persona simulated walk-through of shipped SPA copy. Every quantitative claim ("N of 10 personas…") should be read as *"a design-sensitive reviewer authoring N of 10 persona voices expected that reaction."* The value is in the *range of concerns surfaced*, not in the counts. Every recommendation in this document is a hypothesis awaiting real-user validation.

### E2 · Downgrade quantitative claims to range language

Sweep §1, §2, and §3 for "N of 10" statements. Replace with:
- "Most personas…" (where a strong majority)
- "Several personas…" (where a plurality)
- "At least one persona…" (where the single strongest counterexample is what matters)

Do not lose the specificity; keep the persona names (Jamie, Ms. Patel, Dr. Reyes, etc.) so the reader can trace which reaction came from which simulated voice. But drop the false precision of denominators.

### E3 · Separate the vocabulary/plain-language principle from the GTM question

In §7 Q-3, add a clarification: "Plain-language and operator-surface-gating are independent of the GTM answer. Even in a technical-creator market, engineering codenames and IT verbs are not defensible as customer labels. Q-3 only affects *which specific vocabulary elaboration* is chosen (e.g., 'character' vs 'presenter' as marketing surface term)."

### E4 · Reframe "two products" as "one product, staff-gated surfaces"

In §5.1, replace "two entirely separate products" with something like: "**One product, with a set of surfaces gated to staff users.** The staff surfaces (bootstrap-review, provider-status, engine-connections) are legitimate parts of Character OS; they simply have a different audience — operators and engineers, not the workspace's normal customer — and are held to different tone standards accordingly."

Add: "The same human can legitimately hold both roles (Chris is currently both operator and proxy customer). What must not happen is: operator vocabulary bleeding into non-staff-user workflows."

### E5 · Acknowledge the object model's blind spots

In §3, add a short subsection after "the three customer-first objects":

> **Where this model is provisional.** The three-object reduction (Your AI / Sources / What it makes) helps designers reason about state. It may hide two customer-facing concepts:
> - **Interactions** (live conversations, chats) are *events*, not made-things. Some customer flows treat them as first-class ("I want to have a live chat with Pastor Dan Video"). Whether they are a distinct object or a sub-type of output is unresolved.
> - **Plans** (campaigns) are neither sources nor made-things; they are batched-output plans with their own lifecycle. Whether they are a distinct object or a mode of output creation is unresolved.
>
> The stronger claim this document *can* make: **the customer's mental map is jobs, not objects.** Users think "I want to make a video today" / "I want a live chat" / "I want a batch send" — not in terms of objects. The three-object model is a design tool, not a customer's actual frame.

### E6 · Deepen the noun question

In §4.1, replace the "three directions" framing with a prior question:

> **The prior question.** Before choosing a replacement noun, ask: does Character OS need a universal class noun in customer surfaces at all? Evidence that it may not:
> - The wizard asks the customer to name the thing.
> - The sidebar and empty-state copy can use the customer's chosen name.
> - Tone-appropriate phrases per empty state can substitute for a universal class term.
> - Marketing and documentation *do* need a class term — but that is a marketing decision, not a customer-experience one.
>
> **If this framing holds,** the noun problem shrinks to: "retire 'spokesperson' from customer surfaces; use the customer's chosen name wherever possible; use tone-appropriate phrases where a phrase is required; make marketing-noun a separate decision."
>
> The three directions in the previous version of this section (single-generic-term / contextual-terms / elevate-'character') remain valid as candidates *for the marketing-noun decision*. They are not required as system-wide vocabulary choices.

### E7 · Split IA principles from IA proposals

Restructure §5. Currently §5.2 mixes principle ("operator surfaces gated to staff") with implementation ("six nav items: Home / Your team / Sources / Make / Library / Campaigns"). Separate them:

- **§5.2a — IA principles (ratifiable).**
  - Operator surfaces (bootstrap-review, provider-status, engine-connections) live behind a staff-only gate.
  - Assets, Videos, Compositions, and Bundles as coequal nav items is a false decomposition; the customer sees them as overlapping views of one thing.
  - The video detail should be the primary surface for a video; engineering internals belong behind progressive disclosure.
  - No customer-facing nav item should use an internal codename or engineering verb.

- **§5.2b — IA proposals (illustrative, not ratifiable).**
  - One possible customer nav shape: Home / [collection of AIs] / [browse sources] / [browse outputs] / [batched-outreach].
  - Whether "Make a video" is a destination or an action available from many places is a design decision to make later against actual user-flow evidence.
  - Whether the plural of AIs deserves its own nav item, or lives on Home when >1, is a design decision.
  - Naming ("Home / Team / Sources / Make / Library / Campaigns") is illustrative, not lock-worthy.

### E8 · Downgrade the Data & Providers acceptance criterion

In §9.2, replace: "A Data & Providers surface exists (even if minimal — see Q-4) and is linked from the primary sign-up and from every ingest flow."

With: "The product's IA reserves a position for a Data & Providers surface. Whether that surface exists, what it contains, and how it links from ingest/session flows is conditional on Q-4's resolution. Until Q-4 resolves, the product **must not** make privacy or data-handling promises it cannot substantiate; the acceptance criterion is negative (no unsubstantiated promises), not positive (surface exists)."

### E9 · Soften language of certainty throughout

Sweep for:
- "unrecoverable" → "likely a persistent friction for a wide range of non-technical users"
- "will always feel wrong" → "risks feeling wrong to"
- "cannot be recovered" → "is a poor fit for"
- "the most consequential vocabulary decision" → "a consequential vocabulary decision"
- "real product" (as a claim) → drop or replace with a specific PMF-signal observation

Keep rhetorical compactness where it earns its keep ("the wizard is the product", "moat and wall") but flag them explicitly as design shorthand rather than empirical claims.

---

## Wording that should become more precise

| Current wording | Sharper wording | Reason |
|---|---|---|
| "5-7 of 10 personas reject the noun" | "The noun feels wrong across a wide range of the personas simulated, especially teachers, pastors, therapists, coaches, and small-business owners" | Removes false precision; keeps range signal |
| "the customer's mental model" | "the customer's likely mental model, based on persona simulation" | Marks as hypothesis |
| "two entirely separate products" | "one product with staff-gated surfaces" | Corrects framing |
| "the three objects the customer needs" | "a three-object reduction that helps designers reason about state; the customer's actual frame is jobs" | Reframes ownership |
| "the K6.4 verifier is invisible-to-the-competent-user" | "the K6.4 verifier's UI is opaque to users who would benefit most from it, based on the reactions simulated for the dentist, accountant, and teacher personas" | Marks source of judgment |
| "The wizard is the product" | "The wizard is the shipped surface most likely to convert a first-time user; downstream surfaces should aspire to its clarity" | Keeps punch; drops overstatement |
| "there is a real product here" | "some personas were simulated as ready-to-buy on shipped shape; others were simulated as blocked by specific friction. The friction patterns are actionable." | Concrete |
| "The persona review shows…" | "The persona simulation surfaces…" | Consistent framing |
| "customers think in this concept" | "based on persona simulation, customers likely think in this concept" | Marks source |

---

## Ready for Design Lock

These claims are mature enough to be foundational principles. They should survive scope-lock unchanged.

1. **Operator surfaces (bootstrap-review, provider-status, engine-connections) live behind a staff-only gate.** They are not present in the nav for non-staff users. This does not preclude a staff user seeing them; it precludes exposing them to non-staff.

2. **Internal codenames and engineering verbs do not appear on customer surfaces.** Specifically: `K2`, `K6`, `K6.4`, `K6.6`, `primitive`, `chunk`, `embedding`, `corpus`, `ingest` (as verb/adjective), `pipeline`, `composition` (as user-facing noun), `mock` (as customer-visible badge), `provision`, `fire` (as verb), `ship` (as verb), `bake`. This holds regardless of GTM target audience.

3. **The word "spokesperson" is retired from customer surfaces.** What replaces it — a single class term, contextual phrases, or no class term at all in customer flows — remains open. What is settled: the current word does not serve the range of use cases the wizard already invites in.

4. **The Assets / Videos / Compositions / Bundles overlap is a real product problem.** These are four coequal nav items showing overlapping views of substantially the same thing. Whatever the resolution, the product cannot ship additional features on top of this decomposition without compounding the confusion. The specific resolution (unified library, video-as-primary with progressive disclosure, etc.) remains a design decision.

5. **The video-detail page's default view is the video and its brief; engineering internals (steps, primitive kinds, K-code labels, pipeline lineage) belong behind progressive disclosure.** This holds independent of the broader IA decisions.

6. **The wizard, welcome page, and empty states are the tone-and-voice model the rest of the customer product should grow toward.** Warm without cutesy, honest about limitations, concrete about next steps, uses the customer's own name back to them. This is a positive model to preserve, not a claim about completion rates.

7. **The onboarding tour's structure is sound; its verbs are not.** The three-step scaffold (build → teach → make) is the correct shape; the specific verbs currently used are examples of what to change.

8. **The customer product and the staff-gated surfaces are one product with different audiences, not two products.** Vocabulary and tone contracts differ across the two surface classes; product identity, branding, and ownership do not.

---

## Still Requires Operator Judgment

These are intentionally unresolved. They should not be locked yet, and the design document should stop implying they are near-decisions.

1. **The universal-noun question.** Does Character OS need a customer-surface class noun at all, or does the customer's chosen name plus contextual phrasing carry the load? If a class term is needed for marketing/documentation, which one — and does the marketing choice have to match the in-product choice, or can they be different?

2. **GTM target audience.** Is the initial ideal customer the technical creator/consultant (Rob), the volume-outreach professional (Marcus), the broad small-business owner (Jamie), the regulated professional (Dr. Reyes / Dr. Alvarado / Priya), the institutional educator (Sara / Ms. Patel / Pastor Dan), or a segment not surfaced by the persona set? The UX principles above hold across all of these, but the *elaboration* of the product's language and prioritization of features depends on this answer.

3. **Data & Providers surface.** Does the product have one? What does it truthfully commit to? Are there BAAs? Retention guarantees? Third-party-processor disclosures? These are business/legal questions. The design must not manufacture the surface until the substance is decided; the design must not ignore the need indefinitely either, since it blocks entire verticals.

4. **The object model's shape.** Three objects (Your AI / Sources / Outputs), five objects (adding Interactions and Plans), or an entirely jobs-based frame with no fixed object list? This depends on whether designers reason about state or customers think about tasks — and probably both need to be true simultaneously.

5. **Whether "Make" is a destination or an action.** Whether "Library" is a top-level nav item or a browse mode within a video-detail experience. Whether the plural of AIs earns its own nav item or lives on Home when count > 1. These are design decisions that require real user-flow evidence, not persona-simulation inference.

6. **The verifier's exposure to the customer.** Hidden entirely with a sensible default mode? Exposed as a labeled slider with plain-language explanation? Made into a rich configurable surface for the professional-services vertical? Each has different pricing, positioning, and support implications.

7. **Multi-AI product shape.** Is the primary model one-workspace-equals-one-AI (like Slack — you set up one team), one-workspace-equals-many-AIs (like a stock library), or one-AI-per-purpose within a workspace (like Notion pages)? The current product allows the second but nothing tells the user which is intended.

8. **Live conversation vs asynchronous chat product shape.** Are these unified in the customer's mental frame ("Talk to it" — mode chosen contextually) or presented as two distinct capabilities? The technical implementation currently shares a model but the frontend treats them differently.

9. **The italic-gold "§" typography and wordy-verb H1 pattern.** Brand-voice question that outranks vocabulary. Splits the audience per persona simulation; unclear whether it's an asset to protect or a phase to move past.

10. **Pricing and upgrade surfacing.** Proactive (Priya-style transparency) or reactive (value-first-price-second). Depends on the target segment and the tier structure the business wants to charge for.

---

## Summary in one paragraph

`CUSTOMER_MENTAL_MODEL_V1` is a solid design document, but it repeatedly presents persona-simulation reactions as if they were empirical customer research; it conflates the plain-language principle (which holds universally) with GTM decisions (which are separate); it uses "two products" when it means "one product with staff-gated surfaces"; its three-object model is a designer reduction rather than a customer's actual mental frame; the noun question is posed too narrowly ("pick a replacement") when the deeper question is whether a universal class noun is needed at all; its IA section crossed from principle into specific nav design too early; and one acceptance criterion (Data & Providers surface) overpromises against an unresolved business question. Sharpening the language of certainty, separating principle from proposal, and moving the specific implementation choices into "still requires judgment" would leave the document harder to be wrong about — which is the point.

---

## STOP

Adversarial review preserved. `CUSTOMER_MENTAL_MODEL_V1.md` NOT modified. No implementation, no code, no ratification.
