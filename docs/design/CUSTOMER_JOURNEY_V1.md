---
title: "Customer Journey — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-07-23 (SESSION 229; three-layer frame + identity surface added SESSION 232; Chapter 6 coaching loop added SESSION 233)
companion_docs:
  - "CHARACTER_OS_WHAT_IT_IS.md"
  - "UI_REDESIGN_V2.md"
  - "CREATE_SPOKESPERSON_WIZARD.md"
  - "KNOWLEDGE_LAYER.md"
  - "WORKSPACE_FABRIC_V1.md"
  - "REALTIME_AVATAR_V1.md"
  - "VIDEO_COMPOSITION_V1.md"
  - "IDENTITY_MODEL_V1.md"
phase: 4
---

> **Ontology reference (SESSION 250, added 2026-08-08):** the
> identity concepts this document uses — spokesperson name,
> personality, business_brief, the six identity slots — sit within
> a broader implementation-agnostic ontology defined in
> [`IDENTITY_MODEL_V1.md`](IDENTITY_MODEL_V1.md). Read the ontology
> for the conceptual model of what a persistent AI creator's
> identity IS (CORE / EXPRESSION / GOVERNANCE); read this journey
> doc for how the identity is authored, presented, and used across
> the customer's product experience. The two are complementary:
> the ontology says what identity is; this doc says how the
> customer meets and shapes it. This doc is NOT silently amended
> to match the ontology; any tension between them is recorded as
> explicit follow-up work in
> [`CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`](CUSTOMER_EXPERIENCE_REVIEW_INDEX.md).

# Customer Journey

> **Read first:** `CHARACTER_OS_WHAT_IT_IS.md` (product object
> map + identity), `UI_REDESIGN_V2.md` (the design lock for the
> launch product), and the SESSION 229 handoff
> (`docs/handoffs/SESSION_229_CUSTOMER_JOURNEY_ARC.md`) which
> narrates the product-review sessions that produced this doc.

---

## Purpose

Character OS's screen-by-screen product design has, until now,
been organized by **feature arc** — the K-arc (Knowledge), the
V-arc (Video composition), the R-arc (Realtime avatar), the
F-arc (Workspace fabric). Feature arcs are the right shape for
shipping. They are not the right shape for **evaluating whether
the customer's story holds together across features.**

This doc locks the customer journey — the story a first-time
small business owner lives through, from before they arrive to
the moment they run an AI team. It sits **above** the feature
arcs and constrains them. When a feature arc's design conflicts
with the customer journey, the customer journey wins.

The journey emerged from a product-review sequence in SESSIONS
228–229. SESSION 228 walked the fresh-user path cold and shipped
the post-creation welcome screen and portrait polish. SESSION
229 turned to the next natural chapter (teaching Oliver about
the business) and uncovered that the redesign wasn't a
Knowledge-page redesign — it was **Character OS's onboarding
philosophy.** The metaphor shift from *"AI spokesperson"* to
*"bringing a new employee onto your team"* was surfaced by the
operator mid-session and became the through-line of this doc.

### Why scope-lock first

The customer journey touches every feature arc already shipped
(K, V, R, F, EB, VO) and every arc queued after it (Chapter 2's
Hire Oliver directly reshapes `CREATE_SPOKESPERSON_WIZARD.md`;
Chapter 6's Ongoing training reshapes the existing
`/workspace/knowledge` page; Chapter 7's Grow the team reshapes
the workspace overview). Locking the story before any of those
rewrites lands keeps the reshaping honest and prevents drift
between chapters designed by different sessions.

---

## Contract rules (load-bearing)

These bind every customer-journey-related design decision the
same way `KNOWLEDGE_LAYER.md`'s rules bind every K-arc slice.

1. **Character OS is the hero of the story. Oliver is a character
   inside Character OS's world.** The heroic voice, the trusted-
   guide role, and the through-line of every chapter belong to
   Character OS. Oliver is the customer's *first employee* inside
   the platform — never equivalent to the platform.

2. **The customer is the protagonist. Their transformation is the
   real arc.** They begin as someone exploring AI. They end as
   someone who runs an AI team for their business. Every chapter
   must move that self-concept one step forward. Product features
   are only meaningful in service of that identity shift.

3. **"First assignment" is a durable platform pattern, not a
   feature.** The v1 delivery is video (Oliver's on-camera
   introduction), but the pattern extends beyond video as
   Character OS grows. Future assignment types (website widget,
   personalized outreach, recorded FAQ) slot into the same
   emotional shape.

4. **Character OS recommends. The customer chooses and assigns.
   Oliver executes.** This is the agency sequence for every act
   the platform initiates on the customer's behalf. Even when v1
   offers only one recommended path, the customer performs the
   conscious act of choosing and the conscious act of assigning.
   Nothing happens *to* Oliver as a side-effect of screen
   advance.

5. **The employee metaphor is loudest at moments of highest
   uncertainty. Character OS's real product vocabulary is loudest
   at moments of highest specificity.** This is the guardrail
   rule. It is the check applied to every screen: does the
   language here match the customer's certainty level in this
   chapter? Mismatched register is a design defect.

6. **The metaphor never obscures system truth.** Oliver may
   react in character to failures, but Character OS must
   communicate the real recoverable state honestly. Provider
   outages, configuration failures, policy blocks, timeouts, and
   broken renders must not collapse into *"Oliver couldn't quite
   get the take right."* See rule 8.

7. **Saving is not extraction.** For any chapter whose payoff is
   an artifact, the emotional close requires the customer to
   move the artifact *into their real business* — download,
   share link, publish, embed. Persistence surfaces ("save to
   your library") may exist but do not by themselves satisfy the
   claim that the transformation has been externally ratified.

8. **Honest latency, honest failure.** No copy fabricates a
   duration ("this usually takes about 30 seconds") without
   observed production latency data. No copy hides operational
   failure inside employee-voice reassurance. Latency copy and
   failure copy must be truthful; measurement is an
   implementation dependency, not a design decision.

9. **The renaming pass is real work, not automatic.** Applying
   the employee metaphor across the product ("Knowledge" →
   "What Oliver has learned"; "Create Spokesperson" → "Hire
   Oliver"; etc.) is a coordinated pass, not a global rename.
   Each surface gets an intentional choice about whether the
   metaphor serves or obscures at that point in the journey.

10. **A spokesperson is defined in three layers, in order: body,
    identity, knowledge.** The wizard builds body (name, portrait,
    voice — the vessel). The identity form defines role,
    positioning, boundaries, and desired emotional outcome — the
    always-on rules. The knowledge library then teaches facts.
    This ordering is not a UI suggestion; it is the substrate for
    every downstream chapter. A skipped identity layer is why a
    freshly-created spokesperson reads as *"an unguided AI that
    doesn't do anything"* in the current product (SESSION 232
    product-review finding).

---

## The four voices

Every screen in the customer journey has at least one of these
four voices present. The rules for who speaks when are the
scope of every chapter design.

| Voice | Role | Speaks when |
|---|---|---|
| **Character OS** | The hero — trusted platform guide | Every transition, every choice moment, every explanation, every failure that needs system truth |
| **The customer** | The protagonist — a small business owner in transformation | Every act of agency (deciding, teaching, correcting, assigning, extracting) |
| **Oliver** | A character inside the platform — the customer's first employee | Greeting, acknowledging, summarizing what he learned, delivering a first take, briefly reacting to his own work. Only when an actual employee would speak. |
| **The customer's inner voice** | The self-concept shifting | Not written as copy — designed *toward.* Every chapter must move this voice one rung up the transformation ladder. |

Rule of thumb: **Character OS never speaks in Oliver's voice,
and Oliver never speaks in Character OS's voice.** If a line
could plausibly belong to either — it belongs to Character OS.
Oliver's presence is quieter and more deliberate this way.

---

## The three layers of a spokesperson

Added SESSION 232. This lens surfaced during a product-review walk
of the spokesperson detail page and became the load-bearing
addition of that session. It is the ratified interpretation of
contract rule 10.

A spokesperson is defined across three layers, in order:

**1. Body.** Name, portrait, voice. Built in the create-spokesperson
wizard (Chapter 2, Beats 1–4). The vessel. Without it, there is
nothing to point at.

**2. Identity.** Business focus, audience, offering, what to always
emphasize, what to never say, how people should feel after
interacting. Always-on operating rules that shape every video and
every conversation. Not facts — the *frame* the spokesperson
operates inside. Filled on the spokesperson detail page's Identity
surface (designed under §"The spokesperson detail page — where
identity gets defined" below).

**3. Knowledge.** Facts. Products, policies, documents, FAQs, URLs.
The reference material the spokesperson looks up when asked
something specific. Filled via the workspace knowledge surfaces
(Chapter 3's guided teach flow + `/workspace/knowledge`).

The three layers are sequenced deliberately:

- Body without identity produces a person who looks the part but
  has no role.
- Identity without knowledge produces a role that can speak in
  the right voice but has nothing specific to say.
- Knowledge without identity produces a document lookup with no
  personality shaping its answers.

Every layer earns the next.

### Chapter mapping

| Layer | Where it lives | Which chapter earns it |
|---|---|---|
| Body | Create-spokesperson wizard | Chapter 2, Beats 1–4 |
| Identity | Spokesperson detail page's Identity surface | Chapter 2's close continues here; feeds every downstream chapter |
| Knowledge | Workspace knowledge surface (`/workspace/knowledge` + Chapter 3's guided teach) | Chapter 3 (first-teach) + Chapter 6 (ongoing training) |

### Why this matters for design

The current product ships layers 1 and (partially) 3. Layer 2 was
largely absent before SESSION 232 — only the single-paragraph
`business_brief` on the wizard captured any of it, and there was
no dedicated surface for the rest. That is exactly why a
freshly-created spokesperson read as *"an unguided AI that doesn't
do anything"* to a customer walking through the flow. The
Identity surface (designed below, shipped SESSION 232) closes the
gap.

### Vocabulary discipline

- "Teaching" in customer copy covers both identity and knowledge
  — the customer does not need to hold the technical distinction.
  Chapter 2 Beat 6's *"Teach {name} about your business"* CTA
  stays as-is; the detail page's *"Define {name}"* signal is the
  identity-first entry point that customer language collapses
  under "teach."
- Internal design + engineering vocabulary uses body / identity /
  knowledge explicitly. This doc is one of the load-bearing places
  where the distinction lives.

---

## The eight-chapter arc

The customer journey has eight chapters, in order, each with a
product-side milestone and a customer-side identity shift. The
right-hand column is the sentence the customer would say about
themselves at the end of the chapter.

| Chapter | Product-side milestone | Customer's inner shift |
|---|---|---|
| 0 — Discover | Sees a real AI spokesperson on-camera | *"This might actually work."* |
| 1 — Arrive | Steps into Character OS after signup | *"I'm about to hire an AI employee."* |
| 2 — Hire Oliver | Meets Oliver as a real person | *"Oliver works for me now."* |
| 3 — Teach Oliver | Shares something with Oliver | *"I'm showing my new hire the ropes."* |
| 4 — Oliver proves he understood | Sees the summary, corrects, asks a question | *"He gets my business."* |
| 5 — First assignment | Holds a real artifact Oliver made | *"My AI made this."* |
| 6 — Ongoing training | Returns to improve Oliver | *"I coach him. He gets better."* |
| 7 — Grow the team | Hires a second employee | *"I run an AI team."* |

The four-phase emotional arc across the eight chapters:

- **Chapters 0–2: Belief** — could this work?
- **Chapters 3–4: Proof** — it works *for my business.*
- **Chapter 5: Value** — I got a real artifact I can show
  someone.
- **Chapters 6–7: Ownership** — this is now how I work.

The employee metaphor carries the customer through belief and
proof. The product identity delivers value. Both together earn
ownership. If any of the three phases fails, the arc breaks.

---

## Detailed chapter designs

The load-bearing middle of the arc — Chapters 2, 3, 4, 5, and 6
— is designed at story-level altitude below. Chapters 0-1 and 7
remain higher-level maps until their respective design sessions
descend into them.

Each detailed chapter includes:

- The customer's emotional state entering
- The identity shift the chapter completes
- Beats with copy
- A voice/agency table
- The metaphor/product-identity balance
- Failure and revision paths
- What the chapter hands to the next

---

## Chapter 2 — Hire Oliver

### Customer's emotional state entering

They stepped through Chapters 0 and 1 believing this platform can
produce a real AI spokesperson (Chapter 0's on-camera reveal) and
that it's the right platform for them (Chapter 1's arrival). What
they don't have yet is a *person.* Their inner voice: *"I'm about
to hire an AI employee."*

They also carry, from Chapter 0's planted frame, a specific
expectation of *what* this spokesperson is going to do — star in
their video ads for TikTok, Facebook, and the like, and answer
customer questions on their website. Both jobs are equally
load-bearing. They are not filling out a configuration form. They
are picking the face and the voice of their brand for two real
jobs.

The friction they bring: mild worry about picking wrong for
either job, a quiet suspicion this will feel more like configuring
software than hiring a person, and the low-grade paralysis of a
first choice in a role that has never existed before.

### Identity shift Chapter 2 completes

From *"I'm about to hire an AI employee"* to *"Oliver works for me
now."*

This is the first chapter where a *specific* character enters the
customer's world. Before Chapter 2, Oliver does not exist. After
Chapter 2, he is a named, faced, voiced person the customer
built, hired, and *watched arrive.* He is not "the AI I'm using."
He is *someone who works here.*

### The beats

Chapter 2 is a six-beat continuous experience. Beats 1–4 are the
existing create-spokesperson wizard, essentially unchanged in
shape — a linear form-driven build that already flows smoothly.
Beats 5 and 6 are new: Oliver's arrival on camera and his own
invitation to the next chapter.

**Beat 1 — Frame the two jobs, then start building.**

Character OS opens the chapter briefly, above the wizard form:

> **Let's build your spokesperson.**
> They'll star in your video ads and answer your customers on
> your site. Pick who they are — you can shape everything.

This is the *restate* of Chapter 0's two-job plant. Deliberately
quiet — one framing line above the form. Not a rebuilt tile row.
Not a job spec. The customer already believes this from Chapter
0; Beat 1 anchors it so the choices that follow carry the right
weight.

Then the wizard's Step 1 opens: name, business brief, personality,
tone archetype. Templates (Riggs, Sasha, Donny, Maya) remain
available as a bootstrap. The existing form flow works well
(SESSION 230 walk verdict) and is not redesigned.

**Beat 2 — Give them a face.**

Wizard Step 2. Three ways: upload a photo, take one with your
camera, or generate a portrait from a visual archetype (mascot /
founder / coach / local guide) and a subject description in the
customer's own words. Existing behavior; retained.

**Beat 3 — Give them a voice — and hear it before you pick.**

Wizard Step 3. Three ways: pick a preset, upload an audio clip,
or record one in-browser. Skip is visible and safe.

**New — voice sampling in the preset picker.** Each voice must be
sampleable *before* selection. The customer taps a voice and hears
a short (~2–3 second) preview of that voice speaking a canned
brand line. This is Chapter 2's one ratified addition to the
wizard shape. Reason (SESSION 230 walk): hiring the voice of your
brand by reading a text label uses the wrong sense. Upload and
Record modes already preview through the operator's own clip;
preset picking is the mode without a preview today.

**DEFERRED (SESSION 231, empirical finding).** Slice 1b was
attempted against Runway's `/v1/voices/preview` endpoint and had
to be reverted the same session. The endpoint **silently ignores
the `{type: "runway-live-preset", presetId: X}` discriminator** —
a call with `presetId="NOT_A_REAL_PRESET"` returns HTTP 200 with
a valid MP3, and a call with no `voice` field at all returns the
same shape. All 30 baked MP3s were the same default voice with
slight prosody variations. Runway's public developer API exposes
no standalone preview surface for the curated preset voices —
they are only reachable via `POST /v1/avatars` avatar creation
(confirmed in `media-engine/app/services/avatar_listing_client.py`
2026-05-08 probe note). Slice 1a's picker UX (per-row play
buttons, SESSION 230 commit `34aa1ac`) remains shipped but every
row renders "Sample coming soon" until either (a) Runway ships a
preset-aware preview endpoint, or (b) we spend the ~$7.50 to bake
per-preset audio via avatar-render + ffmpeg-extract (SESSION
230-declined path). The `GET /api/spokespeople/voice-presets/`
endpoint now returns `sample_url: null` for any preset whose
file is missing on disk, driving the SPA's "coming soon" state
from disk truth rather than a hopeful URL — that infra survives
the revert and is the only surviving code change from this
slice. Full trace:
`docs/handoffs/SESSION_231_SLICE_1B_VOICE_BAKE.md` §"POST-COMMIT
DISCOVERY"; capability lock at
`docs/research/RUNWAY_API_CAPABILITY_MAP.md` §"Voice preview
endpoint is not preset-aware."

**Beat 4 — Extend the offer.**

Wizard Step 4 (Confirm). The customer sees the full package:
portrait, name, business brief, personality, tone, voice. The
primary action stays as the operator's hiring act:

> **[ Create spokesperson ]**

Copy stays in the current product-vocabulary framing (see rule 9
— renaming is intentional work, not automatic). When the button
fires, Character OS begins Oliver's build — the avatar bind, the
voice clone if applicable, and the arrival render (Beat 5).

**Beat 5 — Oliver arrives.**

This is Chapter 2's payoff moment. The moment the operator's
SESSION 230 hypothesis names: *face and voice come together and
he introduces himself.*

The build state resolves deliberately. Character OS narrates
briefly:

> **Oliver's here.**

A one-second held pause. Then Oliver arrives — a rendered
talking-head video plays on the surface. Not a portrait card with
audio playing behind it. Not a mock reveal. His face on camera,
his voice speaking:

> *"Hello, I'm Oliver, and I look forward to being your
> spokesperson. Let's begin by teaching me what I will be
> assisting you with."*

Oliver's own words carry the emotional transition into Chapter 3.
His invitation (*"Let's begin by teaching me..."*) is what makes
the next chapter feel like Oliver's own request, not a Character
OS button caption sitting under a silent portrait.

Character OS is silent through this beat. Oliver's moment.

**Ship bar for Beat 5 (non-negotiable):** Oliver actually appears
on camera and speaks. Portrait-with-audio-playing-behind is not
the shipping shape. The moment fails if the customer sees a still
image and hears a voiceover — because that is exactly what the
current `/spokespeople/{id}/welcome` route delivers, and SESSION
230's cold walk verdict on that route was: *"hollow — Ruby didn't
really show up."* Beat 5's whole point is being the moment the
current flow doesn't deliver.

**Beat 6 — The customer accepts Oliver's invitation.**

Below Oliver's video, primary action (the customer's *choosing*
act to advance):

> **[ Teach Oliver about your business ]**

Two quieter alternatives beneath:

> *Say hi to Oliver first* (opens the live-talk surface)
> *Take a look around* (drops the customer into the workspace)

Because Oliver just invited the teaching, the primary button
carries out what he asked for — the customer is *accepting his
invitation,* not clicking a system next-step. That subtle shift
— from "next screen" to "yes, let's do that" — is what earns
Chapter 2's emotional close.

Character OS does not restate the Chapter 3 handoff above the
fold in Beat 6. Adding *"Now let's teach Oliver about your
business"* below Oliver's video would talk over Oliver and pull
the customer back into system-vocabulary before the emotional
close lands.

The customer's inner voice at Beat 6 close: *"Oliver works for me
now."*

### Voice and agency

| Beat | Character OS | Oliver | Customer |
|---|---|---|---|
| 1 — Frame + start building | Names the two jobs briefly; frames the build | (silent — not yet exists) | Fills in identity |
| 2 — Face | Frames the choice; names the three ways | (silent) | Uploads, captures, or generates |
| 3 — Voice | Frames the choice; makes sampling available | (silent) | Samples, picks, uploads, records, or skips |
| 4 — Extend the offer | Reviews the package | (silent — awaiting build) | **Creates.** The hiring act. |
| 5 — Arrival | Narrates the state change (*"Oliver's here"*), then silent | **Speaks his opener** — face + voice on camera together | (watches, listens) |
| 6 — Invitation accepted | (silent — Oliver already framed the transition) | (silent — invitation delivered) | **Chooses** to accept Oliver's invitation |

The Beat 5 → Beat 6 voice split is load-bearing. Oliver delivers
the invitation *inside* Beat 5. Character OS does not restate the
transition in Beat 6 — the button under the video simply carries
out what Oliver just asked for.

### Locked calibrations (Chapter 2)

**Two-job planting.** Chapter 0 plants "spokesperson = ads
presenter + customer-facing chatbot voice." Chapter 2 Beat 1
restates it in a single opening line above the wizard form. The
wizard fields themselves are not job-labeled; the frame carries.

**Voice sampling in Beat 3.** Preset picking must be auditory
before commit. Duration ~2–3 seconds per sample. Upload and
Record modes preserve their existing self-preview surfaces.

**Beat 5's script is generic-plus-name-and-role.** Oliver's
opener names himself and his role (*"your spokesperson"*) and
invites Chapter 3 (*"Let's begin by teaching me what I will be
assisting you with"*). It does not attempt Chapter 4-style
specificity about the customer's business. Rule 5: at the moment
of highest uncertainty (meeting a person for the first time), the
metaphor is loudest, specifics quietest. Chapter 4 owns the
specificity payoff; Chapter 2 owns the arrival.

**Oliver's arrival is rendered video.** Face + voice on camera,
playing on the surface. Portrait + implied-audio does not clear
the ship bar (SESSION 230 walk).

**Vocabulary stays "spokesperson."** No rename to "assistant" in
v1. Oliver may say *"your spokesperson"* in Beat 5 comfortably;
the product surface stays consistent.

**Oliver's invitation is the transition.** Character OS does not
restate the Chapter 3 handoff in Beat 6. The button under
Oliver's video carries out his invitation and no more.

### Metaphor / product-identity balance

Chapter 2's metaphor is strongest at Beats 5–6 (the arrival + the
invitation) and lightest at Beats 1–4 (the build). Product
vocabulary carries the build because the customer needs it to
describe their choices — visual archetype: `mascot`; tone:
`expert`; preset: `vincent`. The metaphor blooms in Beat 5
because uncertainty is highest there — Oliver is a person for
the first time. Rule 5 in action.

### Wizard scope lock reconciliation

Chapter 2's design **honors** `CREATE_SPOKESPERSON_WIZARD.md`'s
six contract rules in Beats 1–4 and **extends** one rule at Beat
5. It does not supersede any rule.

| Wizard rule | Chapter 2 posture | Notes |
|---|---|---|
| 1 — Wizard is for new spokespeople only | HONOR | Chapter 2 fires once per spokesperson. Re-shaping happens on the detail page. |
| 2 — v1 floor is name + business_brief + portrait | HONOR | Beat 5's arrival renders even when voice is skipped (default preset carries it). |
| 3 — Pure JSON in, pure JSON out | HONOR | No change to the wire contract. |
| 4 — No conversational chat. Linear form-driven. | EXTEND | Beats 1–4 remain form-driven and non-conversational. Beat 5 introduces a *one-way rendered arrival* — Oliver speaks; the customer watches. Not a conversation. No follow-up questions, no multi-turn state, no chat history. |
| 5 — Templates pre-fill; archetypes default | HONOR | Templates remain available as a bootstrap; unchanged. |
| 6 — No silent failure | HONOR + HARDEN | Contract rule 6 (metaphor never obscures system truth) adds honest-failure guarantees to Beat 5's fallback copy. |

The wizard doc's implementation-order slate stays valid; Beat 5
is a new implementation slice landing after the current wizard
shape. The existing post-creation `/spokespeople/{id}/welcome`
route (SESSION 228) is the natural surface to extend into Beat 5 +
Beat 6 — its current static shape *is* the "hollow" Beat 5 that
Chapter 2 replaces.

### Failure and revision paths (Chapter 2)

Following rule 6 — Oliver may react in character where honest;
Character OS must communicate real system state where the failure
isn't Oliver-shaped.

- **Voice sampling fails (Beat 3).** Character OS states honestly
  (*"This voice can't be sampled right now"*) but the customer
  can still pick it. Selection is the load-bearing action;
  sampling is the affordance.
- **Portrait generation fails (Beat 2).** Character OS states
  what happened; Upload and Camera remain as fallbacks. Not
  framed as an Oliver-side problem — he does not exist yet.
- **Voice clone fails (post-Beat 3, pre-Beat 5).** Character OS
  states honestly, offers to proceed with the default preset. The
  customer who skipped voice is already in this state and it
  works.
- **Avatar build or Beat 5 render fails.** Beat 5's rendered
  arrival cannot play. Character OS states the truth: *"His intro
  didn't record — you can try it from his page."* The button
  under the honest-failure block still routes to Chapter 3 (Beat
  6 still opens). The emotional weight of Chapter 2 is reduced
  but the customer is not stuck. Never covered by an Oliver-voice
  reassurance (rule 6).
- **Beat 5 latency exceeds threshold.** Character OS narrates the
  wait honestly. Copy must reflect measured production data
  (rule 8); no fabricated duration.
- **Customer bails mid-wizard.** State preserves across the
  wizard reducer's steps (existing behavior). On return, the
  wizard reopens on the last visited beat with fields intact.
- **Customer wants to redo the hire.** Chapter 2 fires once per
  spokesperson. Re-shaping lives on the detail page (Chapter
  6-adjacent surface). Chapter 2 does not re-run for the same
  person.

### What Chapter 2 hands to Chapter 3

The customer arrives at Chapter 3 holding:

- A named spokesperson with a portrait, a voice, and a bound
  Runway avatar.
- The felt memory of Oliver's arrival — his face on camera, his
  voice, his invitation to be taught.
- A ratified business brief.
- An inner voice that reads: *"Oliver works for me now."*

Chapter 3's Beat 1 opens with a Character OS welcome — *"Let's
teach Oliver about your business"* — that reads as coherent
because Oliver has just asked for exactly that. The two beats
fit together only when Beat 5 delivers on its ship bar.

---

## The spokesperson detail page — where identity gets defined

Added SESSION 232. Chapter 2 Beat 6's *"Teach {name} about your
business"* CTA lands the customer on the spokesperson detail page.
That page is the primary landing surface for every subsequent
interaction with the spokesperson. Its shape is a scope-lock in
its own right, not itself a chapter (no identity shift; the page
persists across the customer's entire relationship with the
spokesperson).

### The three surfaces the detail page hosts

The detail page's structure mirrors the three-layer sequence
(contract rule 10; §"The three layers of a spokesperson" above):

1. **The identity surface** — the primary next action for a
   freshly-created spokesperson. Designed in detail below.
2. **The knowledge surface** — the customer's entry to teaching
   {name} facts (Chapter 3's guided first-teach flow + ongoing
   management via Chapter 6). Present as a secondary surface but
   not the primary next action for a freshly-created spokesperson.
3. **The output surfaces** — Videos (list of renders) and Talk
   (live realtime session). Present but read as *"these get
   better once {name} has been defined and taught."*

A customer who has completed only body (via the wizard) sees an
inviting *"Define {name}"* signal that pulls them into the
identity surface first.

### The Identity surface

**Entry point.** A button in the masthead action area of
`/spokespeople/{id}` (alongside Re-bake and New render). Two
states:

- **Empty state:** button reads **`Define {name}`** with a
  prominent visual signal (implementation-choice: accent styling
  or a "not defined" pill — contract is "this must read as
  fill-me-out"). Fires when fewer than 4 of the 6 identity fields
  are non-empty.
- **Filled state:** button reads **`Identity`** in a plain
  settings-style treatment. Fires once ≥ 4 of 6 fields are
  non-empty.

Copy interpolates the actual spokesperson name. `{name}` is always
the customer's spokesperson (e.g. *"Define Ruby"*, *"Define Sasha"*).
Oliver is a design-doc example only; no production copy hardcodes
his name.

**Route.** `/spokespeople/{id}/identity`. Dedicated full-page
surface, not a modal. The Identity form's stakes and shape justify
a focused screen.

### The six identity slots (locked SESSION 232)

Ordered so the form reads *business → audience → offering →
positive → guardrails → felt outcome:*

| # | Field | One-line help (Character OS voice) |
|---|---|---|
| 1 | **What your business does** | One clear sentence. *(Existing `business_brief` — carries over as slot 1.)* |
| 2 | **Who do you help?** | Who is {name} talking to? |
| 3 | **What you sell** | Products, services, offerings — just the shape, not a full catalog. |
| 4 | **What {name} should always emphasize** | The things you want in every video and every conversation. |
| 5 | **What {name} should never say** | Guardrails. Off-limits topics, competitor names, legal claims. |
| 6 | **How should people feel after talking to {name}?** | The emotional outcome — not personality, how they walk away. |

All slots are short-form text (paragraph max, target ~500–800
characters). No file uploads, no rich media, no URLs — deep
reference material lives on the knowledge side.

### Page shape

- Back link → detail page.
- Character OS opening: *"Define {name}. This is who they are —
  what shapes everything they say and do. You can update it any
  time."*
- Progress signal: *"N of 6 filled."*
- Six field sections, stacked, all visible on the page (single
  scroll, not paginated). Each: label + one-line help + text area
  + a grayed example placeholder inside the field so first-timers
  have something to react to.
- Single **Save** button (primary) + quiet **Cancel** link.
- Save → confirmation + navigates back to the detail page. The
  detail page re-renders with the updated masthead button state.

### Locked behaviors

- **Slot 1 (`business_brief`) carries over pre-filled from the
  wizard** — no lost data, no re-typing.
- **Only slot 1 is server-required.** The other 5 accept empty.
  Rationale: the customer can fill in as much identity as they
  have at hand, save, and come back. Not blocking on complete
  identity respects the incremental way small business owners
  actually think about their business voice.
- **Empty-state signal on the masthead persists until ≥ 4 of 6
  are non-empty.** Threshold is a design choice (not an
  implementation accident) — enough substance for Videos + Talk
  to feel meaningfully grounded, not full completion.
- **Copy interpolates `{name}` universally.** No hardcoded
  "Oliver" in production code or copy. Enforced at review time.
- **Rule 6 honesty on failure.** Save errors preserve field state
  and surface the error honestly; no field data disappears.
- **Deep reference material stays on the knowledge side.** The
  identity form is short-form text only. Documents, FAQs, URLs,
  PDFs continue to live on `/workspace/knowledge`.

### Failure paths

- **Save fails (network / server).** Character OS states what
  happened; field values preserved in the form.
- **Customer navigates away with unsaved changes.** v1 posture:
  no confirm-lose dialog. Uncommitted values are lost; the
  customer returns to previously-saved state. Future iterations
  may add a confirm-lose modal or auto-save; not v1.
- **Customer opens the identity page for the second time.** Form
  re-hydrates with saved values; the progress signal reflects the
  current fill count.

### What the Identity surface hands to the Knowledge surface

Once ≥ 4 of 6 identity fields are non-empty, the masthead's
Identity button demotes to plain style. The next natural
affordance for the customer is teaching {name} facts about the
business — Chapter 3's guided first-teach flow. The visual +
copy weight on the detail page shifts to reflect this
progression, though the exact surface treatment for "knowledge is
now the primary next action" is deferred to a later Chapter 3
implementation slice (not this session).

### Vocabulary reminder

The word "identity" is internal design + engineering vocabulary.
Customer-facing copy uses concrete, natural language:

- **Empty-state button:** *"Define {name}"* (not *"Set up identity"*).
- **Filled-state button:** *"Identity"* (settings-style label is
  acceptable here because the customer is now oriented — they
  already know what this page is).
- **Character OS framing:** *"Define {name}. This is who they are…"*
  (not *"Configure the identity layer"*).

---

## Chapter 3 — Teach Oliver

### Customer's emotional state entering

They just met Oliver (Chapter 2 close). They are motivated but
overwhelmed. They just hired someone; now they have to explain
their whole business to a stranger. Where do they even start?

### Identity shift Chapter 3 completes

From *"new employer"* to *"someone showing a new hire the
ropes."* First moment of managerial identity.

### The beats

Chapter 3 is a four-beat continuous experience that sits
**before** the existing `/workspace/knowledge` page in the
first-time flow. The Knowledge page remains in the product for
ongoing management (Chapter 6). First-time teaching is a
separate emotional experience, not a landing on the CRUD page.

**Beat 1 — Character OS opens the second chapter of onboarding.**

Oliver's portrait is prominent. Character OS speaks:

> **Let's teach Oliver about your business.**
> The more Oliver knows, the more he'll sound like someone who
> actually works here. Start with what's easiest — you don't
> have to teach him everything at once.

Oliver responds briefly:

> *"I'm ready when you are."*

Primary CTA: **Get started.**
Quiet secondary: *"Not yet — I'll come back later"* (routes to
workspace dashboard, no penalty).

**Beat 2 — How would you like to start teaching Oliver?**

Character OS: *"Pick a way to share something. You can add more
later."*

Four cards, equal weight visually. Card 1 gets a small
recommendation tag above it:

- **Recommended for most businesses.** **Tell Oliver about
  your business in your own words** — A paragraph, an FAQ, or
  notes you'd give a new hire.
- **Hand Oliver a document** — Menus, brochures, one-pagers,
  handbooks.
- **Point Oliver to your website** — He'll read the page you
  send him.
- **Practice with a sample business** — See how teaching works
  before sharing your real business. *Nothing you do here
  touches your real business.*

The sample-business card gets an explicit "nothing you do here
touches your real business" line — it is the confidence-unlock
for hesitant owners.

**Beat 3 — The focused input.**

One card, one input surface. Character OS handles the surface;
Oliver is present in portrait but silent until the loading
state.

- *Just tell me* → large text area, Character OS placeholder
  copy in guide voice.
- *Hand me a document* → drop zone, no file-type list. Errors
  become Oliver's voice in-character.
- *Point me to your website* → single URL field.
- *Sample business* → skip straight to loading with a
  short in-character confirmation.

Loading state: Character OS narrates the wait; Oliver's
portrait animates gently. Character OS is honest about
duration (see rule 8 — no fabricated timing).

**Beat 4 — Handoff to Chapter 4.**

Chapter 3 does not close emotionally at the end of the input.
Its emotional close is Chapter 4's payoff. The loading state
of Beat 3 flows continuously into Chapter 4 Beat 1.

### Voice and agency

| Beat | Character OS | Oliver | Customer |
|---|---|---|---|
| 1 — Welcome | Frames the second chapter | Acknowledges: *"I'm ready when you are."* | Receiving |
| 2 — Choice | Frames the four ways | (silent — portrait present) | Picks a card |
| 3 — Input | Handles the surface; narrates load | Silent until load; then *"Reading through this now — one moment."* | Shares |
| 4 — (bridge) | (no bridge copy — flows into Chapter 4) | (thinking) | (waiting) |

### Copy rules for Chapter 3

- **The word "Knowledge" never appears as UI language in this
  flow.** Internal category, not customer vocabulary. Customer
  vocabulary is *"teaching Oliver."*
- **Verbs are relational:** share, hand me, tell me, read, learn.
  Never *upload, ingest, process, embed, index, chunk.*
- **Nouns are human:** *what you shared, the page you sent me,
  things I remember.* Never *documents, records, knowledge base,
  sources, assets.*
- **Errors are Oliver's problem, not the system's** — for
  Oliver-side reading failures. For provider/system failures see
  rule 6.

---

## Chapter 4 — Oliver proves he understood

### Customer's emotional state entering

They just handed Oliver something. They're waiting for evidence
it worked. This is the moment the belief-to-proof arc closes or
collapses.

### Identity shift Chapter 4 completes

From *"wondering if the training worked"* to *"he gets my
business."* Also plants the first three seeds of managerial
agency (correction, question, choice) that Chapter 5 grows into
full operator identity.

### The beats

Five beats, one continuous surface.

**Beat 1 — The reveal.**

The loading state from Chapter 3 ends deliberately, not
instantly.

Character OS narrates the state change first:

> **Oliver finished reading.**

One-second held pause. Oliver's portrait shifts from *thinking*
to *ready.* Oliver speaks:

> *"Here's what I picked up about your business:"*

The pause is what earns the moment. Instant reveals feel like
output; a held beat feels like a person looking up from a page.

**Beat 2 — Oliver's summary.**

Three to five specific bullets, in Oliver's voice, drawn from
Chapter 3's shared content. Example (Mountain Peak Coffee
Roasters):

> — *You roast small-batch coffee out of a shop in Boulder,
> Colorado.*
> — *Your signature roast is Ethiopia Yirgacheffe — floral,
> bright, citrus notes.*
> — *Free shipping over $40. Everything ships within 48 hours.*
> — *You started in 2019 out of a garage. That story matters to
> you.*
> — *Wholesale customers get their own pricing tier.*

**Ship bar (non-negotiable):** a stranger reading the bullets
could name three specific things about the business. If the
platform cannot consistently produce bullets meeting this bar
from what Chapter 3 accepts, Chapter 4 does not ship for that
customer's training level, or Chapter 3's input surfaces need
to change.

Character OS is silent during Beat 2. Oliver's moment.

**Beat 3 — The correction.**

Character OS:

> **Anything sound off? Correct it and Oliver will remember.**

Each bullet inline-editable. When a correction is made, Oliver
acknowledges in-character. Two flavors, following the locked
Chapter 4 calibration:

- **Grounded restatement (preferred when safely derivable):**
  *"Got it — your signature roast is Guatemala Antigua. I'll
  remember that."*
- **Fallback (used when accurate restatement cannot be
  guaranteed):** *"Got it — I'll remember that."*

Oliver never creatively reinterprets the correction. If
Character OS cannot safely derive the corrected fact from the
saved edit, use the fallback.

Correction is *offered,* never required. Most customers with
good summaries skip this beat. The point isn't that they do
correct — the point is that they see they could. Agency is
available whether or not exercised.

**Beat 4 — The first real question.**

Character OS:

> **Try asking Oliver something about your business.**

Suggested question generated from Oliver's summary. Customer
taps suggestion or writes their own. Oliver answers inline. One
exchange, on this surface — not a chat window with history and
a sidebar.

Failure mode — Oliver doesn't know:

> *"I don't know that yet — want to teach me?"*

Below his answer, an inline teaching affordance appears — a
small "Teach me this" surface that lets the customer share the
missing information without leaving Chapter 4. Failure becomes
fuel.

**Beat 5 — The bridge to Chapter 5.**

Character OS, hero voice:

> **Now let's give Oliver his first assignment.**
> He'll use what he learned to create something for your
> business.

Primary action (the customer's *choosing* act — first of two
agency moments across the Chapter 4 → Chapter 5 boundary):

> **[ Choose Oliver's first assignment ]**

Two quieter alternatives beneath (text links, not buttons):

> *Teach Oliver something else*
> *Manage what Oliver knows*

Both legitimate paths. Neither weighted enough to compete for a
first-time customer on the guided arc.

### Voice and agency

| Beat | Character OS | Oliver | Customer |
|---|---|---|---|
| 1 — Reveal | Narrates state change | Delivers opener | (waiting) |
| 2 — Summary | Silent | Speaks the bullets | (reading) |
| 3 — Correction | Invites the correction | Acknowledges if made (grounded or fallback) | Corrects (or skips) |
| 4 — First question | Suggests a question | Answers | Asks (or skips) |
| 5 — Bridge | Recommends the assignment | (silent — ready) | **Chooses** to advance |

### Locked calibrations (Chapter 4)

**Correction acknowledgment.** Grounded restatement when
Character OS can safely derive it directly from the customer's
saved correction. Fall back to *"Got it — I'll remember that"*
otherwise. Oliver never reinterprets creatively.

**Confidence indicators.** No per-bullet confidence scores or
markers in v1. Would pull the customer out of the employee-
coaching metaphor and back into evaluating an AI system. Oliver
may express uncertainty naturally in-character when necessary;
Character OS must not introduce technical confidence
vocabulary here.

---

## Chapter 5 — Give Oliver his first assignment

### Customer's emotional state entering

They just chose to advance from Chapter 4. Belief is earned;
proof has landed. The unspoken question: *"is this real yet?"*
Do they walk out of this session holding something they could
point to and say *"we made this."*

### Identity shift Chapter 5 completes

From *experimenter* to *operator.* This shift is a progression
across four moments, not a single beat:

- **Beat 2 (direct the brief)** — first true operator act.
- **Beat 3 (assign)** — formal delegation.
- **Beat 5 (artifact plays)** — *"my AI made this"* sentence
  lands internally.
- **Beat 6 (extract)** — sentence becomes speakable to someone
  else. Identity is now externally visible.

### The beats

Six beats, one continuous surface.

**Beat 1 — The recommended assignment revealed.**

Character OS opens:

> **Recommended first assignment**
> **Introduce your business on camera.**
>
> A short video Oliver can record from what he's learned about
> you. Share it with customers, post it on your website, or
> send it to a partner.

Oliver acknowledges he's already been thinking about it:

> *"I've got some ideas from what you shared. Want to see what
> I'm thinking?"*

The word **"recommended"** is deliberate. It preserves the
seam that future versions could recommend from a menu, and it
primes the customer to feel like they're evaluating a
suggestion rather than accepting a fait accompli.

**Beat 2 — The brief.**

Character OS:

> **Here's what Oliver's thinking of saying.** Change any
> wording — he'll say exactly what's here.

The second sentence is the trust signal. What the customer
reads is what Oliver will speak. No hidden rewrite.

Oliver's proposed script appears, in his voice, drawn from
what he learned in Chapter 3. Example (Mountain Peak):

> *"Hi, I'm Oliver — I'm here to introduce Mountain Peak
> Coffee Roasters. We roast small-batch coffee out of a shop
> in Boulder, Colorado. Our signature roast is the Ethiopia
> Yirgacheffe — floral, bright, with citrus notes. If you're
> new to us, ordering is easy: free shipping over $40, and
> everything goes out within 48 hours. We started in a garage
> back in 2019, and we still care about every bag. If you'd
> like to try us, we'd love to meet you."*

The script is inline-editable. Customer options:

- Approve as-is (moves to Beat 3).
- Edit inline.
- Quiet secondary: *"Ask Oliver to try a different draft."*

Length advisory, soft, never blocking. If a reliable
speech-duration estimate exists, it is presented; if not,
neutral copy is used (see rule 8).

**Ship bar for Beat 2 (non-negotiable):** the proposed script
must sound specifically like the customer's business. Same
discipline as Chapter 4's summary. Recognizable specificity or
the chapter does not ship for that customer's training level.

**Beat 3 — The commitment.**

Character OS:

> **Ready when you are.**

Primary action (the customer's *assigning* act — second of two
agency moments across Chapter 4 → Chapter 5):

> **[ Assign this to Oliver ]**

Quiet alternative:

> *Not quite right — let me keep editing*

Once *Assign this to Oliver* is clicked, the brief locks and
Oliver begins his work.

**Beat 4 — The work.**

Character OS narrates the wait honestly. **Copy must reflect
observed production latency** (rule 8). If measured production
data is available, use a supported range. If not:

> **Oliver is recording your introduction now.**

Oliver's portrait shifts to a subtle *at work* state — engaged,
present, but silent. No fake progress animation, no work-stage
narration that might not map to what's actually happening.

Graceful escalation copy (still honest):

> **Still recording — his best takes always take a moment.**

**Implementation dependency:** production latency for the v1
first-assignment pipeline (recipe: `talking_head` or the
Chapter-3-grounded equivalent) must be measured before Chapter
5 ships. Latency copy is a data output of measurement, not a
design decision.

**Beat 5 — The artifact revealed.**

Character OS names the artifact above the video, using the
customer's real business name:

> **Oliver's introduction to Mountain Peak Coffee Roasters.**

Not *"Your first video."* Not *"Video 1."* The specificity is
what turns a rendered file into *real work.*

The video appears as the subject of the page — full width,
prominent, not embedded in a template of controls. It plays.

When it ends, Oliver reacts briefly, in-character:

> *"Let me know what you think — I can always try another
> take."*

**Beat 6 — The extraction.**

Chapter 5 does not close emotionally until the customer moves
the artifact into their real business (rule 7).

Character OS:

> **What would you like to do with it?**

**Chapter-closing extraction actions** (equal weight, primary
buttons):

> **[ Download the video ]**
> **[ Copy a share link ]**
> **[ Publish or embed it ]** *(where supported)*

**Persistence action** — available but does not by itself
satisfy chapter close:

> **[ Save it to your library ]**

Quiet alternatives:

> *Have Oliver try another take*
> *Give Oliver a different assignment*

If the customer takes an extraction action, the *"my AI made
this"* sentence becomes speakable to someone else. If the
customer only saves (or does nothing), Chapter 5 is emotionally
incomplete, and Chapter 6 gently re-surfaces the artifact.

### Voice and agency

| Beat | Character OS | Oliver | Customer |
|---|---|---|---|
| 1 — Recommendation revealed | Names the recommendation, previews shape | Acknowledges: *"I've got some ideas — want to see?"* | Receiving |
| 2 — The brief | Frames the review; script is authoritative | Proposes the script from what he learned | Reviews, edits inline, or asks for a different draft |
| 3 — Commitment | Confirmation frame | (silent — awaiting direction) | **Assigns.** Formal handoff. |
| 4 — The work | Narrates the wait honestly (honest latency copy) | Present in portrait, working, silent | Waiting |
| 5 — The artifact | Names the video with the business's real name | Reacts briefly after it plays | Watches |
| 6 — The extraction | Offers next act; distinguishes extraction from persistence | (silent) | **Extracts.** Downloads, shares, or publishes. |

### First-assignment pattern (five criteria)

Any candidate assignment type — v1 or future — must satisfy all
five criteria to qualify as a Chapter 5 first assignment:

1. **Bounded.** Short enough that the customer keeps momentum.
2. **Ratifies the training.** Uses what Oliver learned in
   Chapter 3.
3. **Produces a tangible artifact.** Something the customer can
   point to, download, embed, or share.
4. **Feels like real work, not a sample.** No "here's what a
   video would look like" scaffolding. This is *their* Oliver
   doing *their* business's work.
5. **Extractable.** Meets rule 7 — the customer can move it
   into their real business without persistence-only surfaces
   like a private library.

Today, *"a short on-camera introduction video from Oliver"*
satisfies all five. Future assignments (personalized outreach,
website widget response, recorded FAQ) fit the same pattern.

### Failure paths (Chapter 5)

Following rule 6 — Oliver may react in character, Character OS
must communicate real recoverable state.

- **Provider outage / configuration failure / policy block /
  timeout / broken render:** Character OS states what
  happened, at the level the customer needs, and presents the
  recovery action. Oliver may briefly react in character:
  *"Sorry — mind if I try again?"* Character OS must not
  collapse all of these into a single Oliver-voice
  reassurance.
- **Generic script (Chapter 3 was thin):** ship bar violation.
  Beat 2 collapses. Fix is upstream in Chapter 3, not
  cosmetic.
- **Customer bails mid-brief:** state preserves. Return to
  the same Beat 2 with edits intact.
- **Customer watches but never extracts:** Chapter 6 gently
  re-surfaces:
  > **You never sent Oliver's introduction anywhere. Want to?**

---

## Chapter 6 — Ongoing training

### Customer's emotional state entering

They have been away and returned. The first-time arc (Chapters 2–5)
is done — Oliver was hired, taught, verified, and delivered a first
artifact. Now the customer is a *returning operator.* They know
Oliver. They know what the platform can do. What they do not know
yet is whether they can *shape* Oliver over time — teach him more,
correct what is wrong, watch him get better.

Their inner voice on entering: *"I want to make him better."* They
are looking for a coaching loop, not a form. They are not filling in
configuration; they are training a coworker.

The friction they bring: uncertainty about whether the platform will
treat their return as *"first time again"* or as a returning
operator. Suspicion that if they add a document, they will not know
whether Oliver actually learned it. That last one is the load-bearing
anxiety — Chapter 6 either resolves it in a visible loop or the
whole chapter fails.

### Identity shift Chapter 6 completes

From *"employer who delegated the first work"* to *"coach who makes
their AI employee measurably better."*

This is the ownership shift. Chapters 2–5 earned belief, proof, and
value. Chapter 6 earns **ownership** — the customer's felt sense
that Oliver is not just something they set up, but something they
*maintain and improve.* An AI coworker is only fully theirs when
they can coach it.

Inner-voice target at close: *"I coach him. He gets better."*

### The coaching frame (design commitment)

Chapter 6 is a **feedback loop**, not a management page. The verb is
*coach,* not *manage.* CRUD affordances (list, upload, edit, delete)
may exist but are not the primary shape. The primary shape is:

1. **Ask** Oliver something.
2. **See a receipt** — which of the customer's own materials he
   pulled from.
3. **Fix the source** if the answer is wrong or thin — right there
   on his page.
4. **Re-ask** and watch the answer change.

That loop *is* Chapter 6. Everything else is scaffolding around it.

### The surface split

Chapter 6 lives on the **spokesperson detail page**
(`/spokespeople/{id}`), not on `/workspace/knowledge`.

| Surface | Job in v1 |
|---|---|
| `/spokespeople/{id}` (detail page) | Sitting with Oliver — teaching, testing, correcting. **The coaching surface. Chapter 6 lives here.** |
| `/workspace/knowledge` | Workspace-wide inventory — list all knowledge across all spokespeople, upload without a specific target, tag, delete. **Inventory substrate. Not the primary teaching surface for a single spokesperson.** |

`/workspace/knowledge` keeps its job but is demoted from *the place
customers go to teach* to *the workspace-wide inventory customers
can visit when they want the cross-spokesperson view.* First-time
teaching remains Chapter 3's guided flow; ongoing single-spokesperson
teaching is Chapter 6's detail-page loop.

### The three layers, revisited

Chapter 6 is specifically the **knowledge** layer's ongoing loop. It
is not identity re-editing. Identity lives on
`/spokespeople/{id}/identity` (SESSION 232, contract rule 10). A
returning operator who wants to change Oliver's positioning goes to
Identity; one who wants to correct what he knows about a specific
topic goes to Chapter 6's Ask loop.

The two coaching surfaces on the detail page are parallel:

- **Identity surface** (`/spokespeople/{id}/identity`) — the always-
  on frame. Six slots. Filled once, revisited rarely.
- **Chapter 6 coaching surface** (`/spokespeople/{id}` itself) —
  the ongoing loop. Visited every time the operator wants to teach,
  test, or correct a fact.

### The beats

Chapter 6 is a continuous experience on the detail page, not a
wizard or a linear flow. Beats describe the operator's typical arc,
not screens.

**Beat 1 — Return.**

The operator arrives on Oliver's detail page. His portrait is
prominent. Character OS opens quietly (returning-after-absence
framing, not every-load framing):

> **Welcome back. Oliver's been ready for you.**

Two primary affordances live in the portrait area:

- **Ask** — a text input directly under his portrait:
  *"Ask {name} something."*
- **Talk** — a button that swaps his portrait for a live video
  session in-place (Beat 5).

Un-extracted artifacts from Chapter 5 re-surface here as a small
nudge (rule 7):

> *"You never sent Oliver's introduction anywhere. Want to?"*

**Beat 2 — Ask.**

The operator types a question in natural language. *"What do we
sell?"* / *"What are our store hours?"* / *"How do we describe our
recommendation process?"*

Oliver answers inline, in his voice. Below the answer, a
**receipt** shows which of the operator's own materials he pulled
from:

> **From your notes on** *About Hearth & Hollow Books.*

Multiple docs: receipt names each, comma-separated, most-cited first.
No citation matched: the receipt states that honestly:

> **Oliver answered from what he already knows. He didn't find
> anything specific in what you've taught him.**

The receipt is visually first-class — it is the load-bearing thing
on the panel, not a footnote. The operator's eyes go to the receipt
because that is what *"prove it"* actually means (SESSION 233 walk).

The Ask path costs approximately $0.001 per question (retrieval + a
small LLM call, using the existing `recall_knowledge` R7.1 tool
substrate). No per-question cost UI needed; a cumulative counter may
live on the workspace usage surface.

**Ship bar for Beat 2 (non-negotiable):** the receipt must
accurately identify the source doc(s) or accurately state that no
source was used. Fabricated citations are a rule 6 violation
(metaphor obscuring system truth). If retrieval cannot reliably
identify what was cited, the receipt shows *"Oliver answered from
what he already knows"* — the honest fallback, not a made-up doc
name.

**Beat 3 — Fix the source.**

The operator sees a wrong or thin answer. Two paths, depending on
the receipt:

- **Answer cited a doc, and the doc is wrong.** Click the receipt →
  the doc opens inline on Oliver's page (not a navigation away).
  Edit the text right there. Save.
- **Answer had no citation (empty / "he doesn't know that").** A
  small affordance appears next to the answer:
  *"Teach {name} about this."* Click → an inline compose surface
  pre-scoped to the topic of the question, ready to accept a new
  doc.

Either way, the operator never leaves Oliver's page to fix a source.
The fix is on the same surface as the ask.

Character OS handles the state around the fix. Oliver may briefly
react to being taught in-character (*"Got it — I'll remember that,"*
matching Chapter 4 Beat 3's grounded-restatement pattern), but the
mechanics of edit-and-save are Character OS's job, not Oliver's.

**Ship bar for Beat 3 (non-negotiable):** the fix loop closes on the
same page. Redirecting the operator to `/workspace/knowledge` to
edit a doc is a chapter-shape violation — that page is the workspace-
wide inventory, not the coaching surface.

**Beat 4 — Re-ask.**

Once the fix is saved, the ingest pipeline re-embeds the affected
doc. The re-ask button is presented but **disabled until re-embed
completes** — the load-bearing UX detail without which the whole
chapter's coaching-loop feeling collapses. If the operator hits
re-ask before re-embed finishes, they get the *old* answer and think
the fix did not take.

Copy during re-embed (rule 8, honest latency):

> **Oliver is re-reading your updated notes…**

When re-embed completes:

> **Ready — ask again.**

Re-ask button activates. Operator re-asks. Answer changes (or stays
wrong, in which case the loop continues — Beat 3 again).

The *"watch the answer change"* moment is Chapter 6's emotional
payoff. It is the coaching-loop-worked moment. Without a reliable
retrained signal, the payoff fails silently.

**Beat 5 — Talk (in-place).**

Separately from Ask, the operator may want a live conversation with
Oliver — to hear him under real conversational pressure, not just
one-shot questions. The current `/spokespeople/{id}/talk` route
(R8) exists but requires navigating to a separate page.

Chapter 6 collapses Talk onto the detail page. The **Talk** button
in Oliver's portrait area swaps the portrait for the live video
session in-place. When the session ends (operator ends it, session
times out, WebRTC fails), the portrait returns.

This is the operator's explicit ask (SESSION 233 walk): *"can the
image come back when we end the conversation?"* Ratified.

Talk carries real per-minute cost (see R9 cost governance in
`REALTIME_AVATAR_V1.md`). Cost is surfaced honestly per rule 8 —
R8.2's CostTicker continues to render, positioned near the swapped
video surface.

Talk is *not* the "prove it" path. Prove it lives in Ask (cheap,
receipt-bearing). Talk is *"talk to him for real"* — deeper
conversational testing, or coaching by conversation.

**Beat 6 — Inventory (secondary).**

`/workspace/knowledge` remains available in the workspace navigation
for operators who want the cross-spokesperson view: everything the
workspace has taught, across all spokespeople, in one list. It is a
secondary surface for Chapter 6 — the operator uses it for the
inventory shape or bulk management, not for coaching a specific
spokesperson.

Chapter 6 does not close emotionally at any specific beat. Coaching
is ongoing; the return-visit pattern is the chapter itself.

### Voice and agency

| Beat | Character OS | Oliver | Customer |
|---|---|---|---|
| 1 — Return | Welcome-back framing (absence-aware); re-surfaces un-extracted artifacts | Present in portrait | Arrives |
| 2 — Ask | Handles the surface; renders the receipt honestly | Answers in-voice from retrieval | **Tests** (asks a question) |
| 3 — Fix the source | Handles the edit surface; opens the doc inline | May react in-character to being taught | **Coaches** (edits doc, or teaches a new one) |
| 4 — Re-ask | Narrates re-embed latency honestly; gates the button until ready | (silent during re-embed; then ready) | **Re-tests** (re-asks and watches the answer change) |
| 5 — Talk (in-place) | Manages the portrait/video swap; surfaces cost honestly (CostTicker) | Speaks live in the swapped video | **Converses** live |
| 6 — Inventory (secondary) | (silent — CRUD surface, not coaching surface) | (not present — inventory is spokesperson-agnostic) | Manages workspace-wide |

### Locked calibrations (Chapter 6)

**The coaching surface is Oliver's detail page, not
`/workspace/knowledge`.** Load-bearing calibration.
`/workspace/knowledge` retains a job (workspace-wide inventory) but
is demoted from *the teaching surface* to *the inventory surface.*
First-time teaching lives in Chapter 3's guided flow; ongoing
single-spokesperson teaching lives on the detail page.

**The receipt is visually first-class.** Not a footnote under the
answer. The receipt *is* the "prove it." If the receipt reads as
subordinate, the coaching-loop shape fails to read.

**No fabricated citations.** If retrieval cannot reliably identify a
source, the receipt states that Oliver answered from generic
reasoning. Contract rule 6.

**The fix loop closes on the same page.** Editing a cited doc opens
inline. Adding a new doc from an "I don't know" response opens
inline. Never a navigation to `/workspace/knowledge` to fix a
source.

**Re-ask is gated on re-embed completion.** Without gating, the
operator gets a stale answer and the coaching-loop feeling
collapses. Non-negotiable.

**Talk swaps in-place.** Portrait becomes live video on the detail
page; reverts to portrait on end/error/timeout. No navigation away
from the detail page for live sessions.

**Ask and Talk are parallel, not sequential.** The operator picks
Ask for cheap testing; Talk for live conversation. They are not a
stepped flow (ask first, talk later). Both are available on the same
surface at all times.

**Identity vs. knowledge separation.** Chapter 6 is the *knowledge*
layer's coaching surface. Identity re-editing is a different surface
(`/spokespeople/{id}/identity`, SESSION 232). Chapter 6 does not
conflate the two.

### Metaphor / product-identity balance

Strongest at Beats 2 and 3 (Ask + Fix — the coaching moments).
Lightest at Beat 6 (workspace inventory — CRUD vocabulary is
appropriate because the operator has descended into inventory-
management mode).

Beat 4 (Re-ask) is a delicate middle. Re-embed latency copy uses
honest system-vocabulary (*"Oliver is re-reading your updated
notes…"*) — honest per rule 8 without dropping the operator out of
the metaphor. *"Re-reading your notes"* is the reconciliation:
system-truth ("we are re-processing the doc you edited") delivered
in relational voice ("re-reading your notes" is what a coworker
does).

Beat 5 (Talk) inherits R-arc's existing metaphor balance.

### Failure and revision paths (Chapter 6)

Following rule 6 — Oliver may react in character where honest;
Character OS communicates real system state where the failure is not
Oliver-shaped.

- **Retrieval returns no matches for a question.** Receipt states:
  *"Oliver answered from what he already knows. He didn't find
  anything specific in what you've taught him."* Beat 3's *"Teach
  {name} about this"* affordance appears. Not framed as a system
  failure; framed as an opportunity to teach.
- **Retrieval matches but the answer is wrong (hallucination).**
  Same shape as retrieval-matches-wrong-doc: the operator uses Beat
  3 to fix the source. Chapter 6 does not attempt to distinguish
  *"the doc was wrong"* from *"the model hallucinated over a correct
  doc"* at v1 — both are addressed by fixing the source material.
- **Re-embed fails (worker down, provider error).** Character OS
  surfaces honestly: *"Character OS couldn't retrain Oliver right
  now. Try again in a moment."* Re-ask button stays disabled. Do
  NOT reactivate re-ask on failure and let the operator get the old
  answer silently.
- **Re-embed pending indefinitely (queue backed up, no worker).**
  Same shape. Character OS surfaces the truth after a bounded wait.
  Manual retry available. Never collapse into an Oliver-voice
  reassurance. (SESSION 233 boot uncovered exactly this class: 6 KDs
  sat in `status=pending` because the Celery worker was not running.
  Chapter 6's re-embed signal must be robust to this failure mode.)
- **Ask fails (API outage, LLM timeout).** Character OS states what
  happened honestly. Oliver does not speak — this is a system
  failure, not an Oliver moment.
- **Talk fails (WebRTC, provider outage).** Falls back to R-arc's
  existing failure surfaces (ErrorPanel with *"Make a recorded video
  instead"* CTA per R8.2 Q-r-9). Portrait comes back with the error
  layered.
- **Operator edits a doc but never re-asks.** Chapter 6 does not
  force re-ask; the edit is committed and the retrained state
  stands. The next question that retrieves the edited doc will use
  the updated content. Absence of re-ask is not a failure.
- **Operator asks the same question repeatedly.** No dedup. Each
  ask is independent. At approximately $0.001 per question, cost is
  negligible.

### What Chapter 6 hands to Chapter 7

The customer arrives at Chapter 7 (Grow the team) holding:

- *"I coach him. He gets better."*
- *"He works for me — and I know how to make him work better."*
- *"If I want another one like him but for a different job, I know
  what that would take."*

The last one is the Chapter 7 seam. Chapter 7 is *hiring the second
employee.* The customer arrives having felt Oliver's coaching-loop
enough to know that a second spokesperson is not a duplicate of
Oliver — it is a new employee with a different role, going through
the same three-layer sequence (body → identity → knowledge) with
different content in each layer.

The workspace fabric (F-arc) already supports multiple spokespeople
in a workspace. Chapter 7's design work is naming what the customer
feels when they hire the second one, and how the workspace surfaces
reshape when the roster is no longer *"Oliver and empty slots"* but
*"Oliver plus Ruby, plus a growing team."*

---

## Reconciliation checkpoint — current product truth

This is not the full implementation audit. It is a truth-
preserving checkpoint so the design above does not accidentally
imply these flows already exist. Verify against
`docs/CHARACTER_OS_INVENTORY.md` before implementation.

### Chapter 2 — Hire Oliver

| Element | Current state |
|---|---|
| 4-step wizard at `/spokespeople/new` | **Exists** (SESSION 132 close) — identity / portrait / voice / confirm |
| Template pre-fill (Riggs / Sasha / Donny / Maya) | **Exists** — tile picker on Step 1 |
| Portrait modes (upload / camera / generate) | **Exists** — `WizardPortraitStep` |
| Voice modes (preset / upload / record) with skip | **Exists** — `VoiceCapture` component; skip → `vincent` |
| Voice sampling *before* selection (preset mode) | **Deferred** — picker UX shipped (SESSION 230 slice 1a `34aa1ac`) but every row renders *"Sample coming soon"* until Runway ships a preset-aware preview endpoint. Slice 1b bake attempted + reverted SESSION 231; see §"Voice sampling in Beat 3" for the finding. |
| Two-job frame ("your ads + your customers") in Beat 1 opening copy | **Missing** — current wizard is job-agnostic |
| Beat 5 — rendered arrival video (face + voice together, playing on the surface) | **Missing** — current post-confirm `/spokespeople/{id}/welcome` shows a static portrait with a "here's what she knows so far" list; SESSION 230 verified *"hollow — Ruby didn't really show up"* |
| Beat 6 — customer accepting Oliver's own invitation (Oliver-authored transition) | **Partial** — welcome route already has *"Teach {name} about your business"* CTA, but framed as system next-step; Oliver does not speak in the current welcome page, so there is no invitation to accept |
| Underlying avatar + voice + render infrastructure for Beat 5 | **Exists** — Runway avatar bind (SESSION 116) + voice clone (SESSION 110) + `talking_head` recipe (V3) |

### The spokesperson detail page — Identity surface

| Element | Current state |
|---|---|
| `/spokespeople/{id}` detail page | **Exists** (S-10, SESSION 132+) — masthead + identity panel + setup + talk CTA + videos + knowledge + conversations |
| `/spokespeople/{id}/identity` dedicated route | **NEW — SHIPPED SESSION 232** |
| 5 new identity fields on `Spokesperson` model (`who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`, `desired_feeling`) | **NEW — SHIPPED SESSION 232** (migration + serializer + tests) |
| `business_brief` (slot 1) already on model | **Exists** (SESSION 132 wizard) — carries over unchanged, pre-fills the identity form |
| `Define {name}` masthead button (empty state, < 4 of 6 filled) | **NEW — SHIPPED SESSION 232** |
| `Identity` masthead button (filled state, ≥ 4 of 6 filled) | **NEW — SHIPPED SESSION 232** |
| Six-field identity form (business focus / audience / offering / always-emphasize / never-say / felt outcome) | **NEW — SHIPPED SESSION 232** |
| Progress signal ("N of 6 filled") | **NEW — SHIPPED SESSION 232** |
| Name-interpolation across identity copy (no hardcoded "Oliver") | **Enforced SESSION 232** |

### Chapter 3 — Teach Oliver

| Element | Current state |
|---|---|
| `/workspace/knowledge` page | **Exists** as CRUD management (`web/src/routes/workspace/knowledge.tsx`, `shell/apps/knowledge/`) |
| First-time-onboarding wrapper before the CRUD page | **Missing** — no Chapter 3 second-chapter-of-onboarding flow |
| Four input paths (paste, PDF, URL, sample business) | **Partial** — paste/PDF/URL likely present in current knowledge surface; sample-business path missing |
| Employee-metaphor vocabulary throughout | **Missing** — current surface is CRUD-shaped |
| Oliver-portrait presence during teaching | **Missing** — current surface is spokesperson-agnostic |

### Chapter 4 — Oliver proves he understood

| Element | Current state |
|---|---|
| Summary-of-what-Oliver-learned surface | **Missing** |
| Correction interaction with grounded/fallback acknowledgment | **Missing** |
| Suggested question generated from summary | **Missing** |
| Inline one-exchange test surface (not the full talk page) | **Missing** |
| Oliver-doesn't-know → inline teach-me affordance | **Missing** |
| Underlying knowledge retrieval capability | **Exists** — `recall_knowledge` R7.1 tool + K-arc RAG infrastructure |

### Chapter 5 — First assignment

| Element | Current state |
|---|---|
| Video generation via recipes | **Exists** — `/recipes` gallery, `talking_head` recipe, R7.2 `render_video` tool |
| Knowledge-grounded script generation | **Partial** — `auto_script` starter (SESSION 206) generates scripts from knowledge; the Chapter-5 "recommended first assignment" framing does not exist |
| Recommended-assignment framing (rec text + Oliver-proposed brief) | **Missing** |
| Formal *Assign this to Oliver* commitment step | **Missing** — current flow is direct recipe fire |
| Artifact naming with business's real name | **Missing** — current output is generic |
| Extraction actions (download / share link / publish-embed) | **Partial** — asset surfaces exist; extraction-focused Chapter-6-close surface does not |
| Save-to-library persistence action | **Exists** — `Asset` model + workspace assets page |

### Chapter 6 — Ongoing training

| Element | Current state |
|---|---|
| `/spokespeople/{id}` detail page as coaching surface | **Partial** — page now leads with the Ask + receipt hero (SESSION 234) when the spokesperson is ready; SESSION 235 layered the Beat 3 fix loop (click-citation → inline editor; empty-citation → teach-me compose) so the receipt is now actionable, not just visible. Identity + setup + videos + knowledge + conversations remain below. Full coaching-first restructure (Talk in-place, un-extracted-artifact re-surface, return-visit welcome copy) still pending. |
| Ask surface on the detail page (text input under portrait) | **SHIPPED SESSION 234 (Chapter 6 slice-1)** — `SpokespersonAskPanel` component; portrait hero + `Ask {name} something` input; swaps in-place to a chat surface (last exchange + follow-up input) when engaged; reverts on `Back to portrait`. Gated on `allDone` (masthead ready). Backend: `POST /api/spokespeople/{id}/ask/` + `character_os/spokesperson_ask.py`. |
| Receipt / provenance display under Oliver's answer | **SHIPPED SESSION 234 (Chapter 6 slice-1)** — first-class receipt card. Grounded shape lists source docs sorted most-cited-first with per-doc chunk counts (design lock Beat 2). Ship bar enforced end-to-end: citations name only docs whose chunks were placed in the model context; retrieval workspace scope holds via K2's `retrieve_for_spokesperson`. Backend regression at `apps/spokespeople/tests/test_ask.py::test_ask_citations_only_include_own_workspace_docs`. |
| Honest-fallback receipt (*"Oliver answered from what he already knows"*) | **SHIPPED SESSION 234 (Chapter 6 slice-1)** — amber-toned receipt with `data-shape="honest-fallback"` renders when `used_knowledge=false`. Copy is name-interpolated (no hardcoded "Oliver"). Non-hideable so Beat 3 (later slice) can wire teach-me affordances to the empty-citation state. |
| Click-receipt → inline doc edit on the detail page | **SHIPPED SESSION 235 (Chapter 6 slice-2 Beat 3)** — grounded receipt citations became clickable buttons that open `EditDocSurface` inline in the AskPanel; textarea prefilled from `GET /api/knowledge/{id}/` (detail serializer now surfaces `processed_content`). Save PATCHes `text_content`; K4-era invariant lifted so the doc id + workspace + M2M survive across the re-ingest. Backend: `KnowledgeDocumentSerializer.update` re-ingest branch + `apps/embeddings/tests/test_api.py::test_patch_text_content_*` (6 regression tests). No navigation to `/workspace/knowledge`. |
| "Teach {name} about this" inline compose (from an empty-citation answer) | **SHIPPED SESSION 235 (Chapter 6 slice-2 Beat 3)** — honest-fallback receipt gained a `Teach {name} about this` CTA that opens `ComposeDocSurface` inline; title pre-scoped to the question (`About: <question>`), save POSTs a new doc with `spokesperson_ids=[<this>]` so the note is immediately visible to this spokesperson (narrower than an empty-M2M workspace-wide doc, matching the operator's teach-this-one intent). |
| Re-embed status signal / gated re-ask button | **Missing at the surface.** `KnowledgeDocument.status` field **exists** (`pending / processing / processed / failed`); Chapter 6 must poll / subscribe and gate the re-ask UI accordingly |
| Talk in-place portrait/video swap on the detail page | **Missing** — current Talk button on detail page navigates to `/spokespeople/{id}/talk` (R8) |
| Portrait returns on Talk end / error / timeout | **Missing** — no in-place surface today |
| Un-extracted-artifact re-surface (rule 7, Chapter 5 close) | **Missing** — no session-boundary detection wiring |
| Return-visit welcome copy (*"Welcome back. Oliver's been ready for you."*) | **Missing** — no absence-aware framing today |
| `/workspace/knowledge` as workspace-wide inventory (secondary in Chapter 6) | **Exists** as CRUD; role reframed by Chapter 6, no code change to `/workspace/knowledge` required for the reframe |

### Runtime / provider dependencies

- **Chapter 4 summary quality** depends on the retrieval +
  synthesis capability of the underlying LLM path. Ship bar
  ("stranger could name three specific things") is a product
  bar; achieving it consistently is an implementation
  dependency.
- **Chapter 5 script generation** depends on `auto_script`-style
  synthesis working reliably against Chapter 3 training. Same
  ship-bar discipline applies.
- **Chapter 5 latency** depends on Runway avatar rendering
  latency. See rule 8 — copy must reflect measured production
  data.
- **Failure surfacing** (rule 6) depends on classifying
  provider/system errors before delivering them. Cannot be
  designed away in copy.
- **Chapter 6 receipt accuracy** depends on retrieval returning
  chunk-to-doc provenance reliably. K-arc supports this at the
  retrieval layer; the Ask surface must surface it faithfully
  and must not fabricate a doc name when none matched (rule 6).
- **Chapter 6 re-embed latency** depends on Celery worker
  liveness and OpenAI embedding API responsiveness. Re-ask
  gating copy must reflect measured production latency (rule 8).
  Re-embed must be robust to worker outage (SESSION 233 boot
  observed 6 KDs stuck in `status=pending` because the worker
  was not running — Chapter 6 must not silently reactivate
  re-ask in that state).
- **Chapter 6 Talk in-place swap** inherits R-arc's provider
  dependencies (Runway avatar bind, R9 cost governance,
  R8.2 CostTicker + WebRTC fallback).

---

## What is ratified vs. what is not

This doc explicitly separates categories to prevent future
sessions from treating deferred ideas as commitments.

### Ratified design rules

Contract rules 1–9 above. These are load-bearing across every
customer-journey design decision. Change requires explicit
supersession, not silent evolution.

### v1 decisions

- Chapter 2 fires once per spokesperson; re-shaping happens on
  the detail page.
- Chapter 2 Beat 1 restates Chapter 0's two-job frame (video ads
  + customer-facing chatbot) in one opening line above the
  wizard form. The wizard fields themselves are not job-labeled.
- Chapter 2 Beat 3 adds voice sampling (~2–3 sec preview) to
  preset selection.
- Chapter 2 Beat 5 uses a rendered talking-head arrival video
  with Oliver speaking. Portrait-only + audio-playing-behind
  does not satisfy the ship bar.
- Chapter 2 Beat 5 script: *"Hello, I'm Oliver, and I look
  forward to being your spokesperson. Let's begin by teaching
  me what I will be assisting you with."* Generic-plus-name-
  and-role; no Chapter 4 specificity.
- Chapter 2 Beat 6 primary CTA is the customer accepting
  Oliver's invitation, not a system next-step. Character OS is
  silent above the fold in Beat 6 — Oliver's own line delivered
  the transition inside Beat 5.
- "Spokesperson" vocabulary stays in v1. No rename to
  "assistant."
- Chapter 3 uses four input paths (paste, PDF, URL, sample
  business) with "Tell me in your own words" as the
  recommended default.
- Chapter 4 uses grounded-restatement correction acknowledgment
  with fallback to *"Got it — I'll remember that"* when
  restatement cannot be guaranteed.
- Chapter 4 exposes no per-bullet confidence indicators.
- Chapter 5 has one recommended first assignment
  (on-camera business introduction video).
- Chapter 5 agency sequence: Chapter 4 *Choose Oliver's first
  assignment* → Chapter 5 *Recommended first assignment: …* →
  Chapter 5 *Assign this to Oliver.*
- Chapter 5 extraction surface distinguishes extraction actions
  from persistence actions (rule 7).

**Added SESSION 232 (three-layer frame + Identity surface):**

- Identity is a first-class layer, distinct from knowledge (facts)
  and body (wizard artefacts). The three-layer sequence (body →
  identity → knowledge) is the substrate for every downstream
  chapter (contract rule 10).
- The spokesperson detail page's primary next action for a
  freshly-created spokesperson is defining identity, not teaching
  knowledge. Chapter 2 Beat 6's *"Teach {name} about your
  business"* CTA lands the customer on the detail page; the
  *"Define {name}"* signal is what draws them in first.
- **Six identity slots** (SESSION 232 lock): business focus,
  audience, offering, always-emphasize, never-say, desired felt
  outcome. Slot 1 = existing `business_brief`. Other 5 are new.
- `business_brief` remains the sole server-required identity
  field. The other 5 accept empty.
- Empty-state signal on the masthead persists until ≥ 4 of 6
  identity fields are non-empty.
- Identity route lives at `/spokespeople/{id}/identity` —
  dedicated full-page surface, not a modal.
- Masthead entry button states: `Define {name}` when < 4 of 6
  filled; `Identity` once ≥ 4.
- Copy interpolates the actual spokesperson name. No production
  copy hardcodes "Oliver" — he is a design-doc example only.
- Deep reference material (documents, FAQs, URLs, PDFs) stays on
  the knowledge side. The identity form is short-form text only.
- "Teaching" in customer copy covers both identity and knowledge;
  the customer does not need to hold the internal distinction.

**Added SESSION 233 (Chapter 6 — Ongoing training):**

- Chapter 6 is a **coaching feedback loop** (Ask → receipt → Fix →
  Re-ask), not a management page. Verb is *coach,* not *manage.*
- The coaching surface is **the spokesperson detail page**
  (`/spokespeople/{id}`), not `/workspace/knowledge`.
  `/workspace/knowledge` retains its job (workspace-wide inventory)
  but is demoted from *the teaching surface* to *the inventory
  surface.*
- Chapter 6 covers the **knowledge** layer's ongoing loop only.
  Identity re-editing remains on `/spokespeople/{id}/identity`.
- **Ask** — a text input directly under Oliver's portrait. Uses
  the retrieval substrate `recall_knowledge` provides (~$0.001
  per question, R7.1 rate).
- **Receipt** under Oliver's answer names the source doc(s) — or
  states honestly that no source matched. Receipt is visually
  first-class, not a footnote. Fabricated citations are a rule 6
  violation.
- **Fix loop closes on the detail page.** Click a receipt → the
  cited doc opens inline. Empty citation → a *"Teach {name} about
  this"* inline compose surface pre-scoped to the question topic.
  Never a navigation to `/workspace/knowledge` to fix a source.
- **Re-ask is gated on re-embed completion.** Load-bearing UX
  detail — without it, the operator gets stale answers and the
  coaching-loop feeling collapses. Copy during re-embed:
  *"Oliver is re-reading your updated notes…"* When ready:
  *"Ready — ask again."*
- **Talk swaps in-place.** The Talk button in Oliver's portrait
  area swaps the portrait for the live video session on the
  detail page. Portrait returns on end / error / timeout. No
  navigation away from the detail page for live sessions.
- **Ask and Talk are parallel, not sequential.** Both available
  on the same surface at all times. Ask is the "prove it" path
  (cheap, receipt-bearing). Talk is *"talk to him for real"*
  (per-minute cost, deeper conversational testing).
- **Un-extracted-artifact re-surface** (Chapter 5 rule 7) lives
  on Beat 1 of Chapter 6: *"You never sent Oliver's introduction
  anywhere. Want to?"*
- **Return-visit copy is absence-aware.** Chapter 6 Beat 1 uses
  *"Welcome back. Oliver's been ready for you."* on returning-
  after-absence loads, not every-load framing.

### Implementation dependencies

- Chapter 2 Beat 5 depends on the same rendering pipeline
  Chapter 5 depends on (`talking_head` or a Chapter-2
  arrival-video starter). Ship bar: real face + real voice,
  playing on the surface.
- Chapter 2 Beat 5 latency copy requires measured production
  data. Same rule 8 discipline as Chapter 5.
- Chapter 2 Beat 3 voice sampling requires a per-preset sample
  clip. If Runway does not serve one, it must be pre-rendered
  and cached.
- Chapter 2 Beat 1's job-frame restate depends on Chapter 0
  (Discover) actually planting the two-job frame; Beat 1 has
  nothing to restate against otherwise. Chapter 0 remains a
  higher-level map today.
- Chapter 5 latency copy requires observed production latency
  measurement before ship.
- Chapter 4 summary and Chapter 5 script generation require
  meeting the "recognizable specificity" ship bar consistently.
- Failure copy requires provider/system error classification.
- Chapter 6 re-surface of un-extracted artifacts requires
  session-boundary detection.

**Added SESSION 232 (Identity surface):**

- Backend: 5 new `Spokesperson` model fields (`who_you_help`,
  `what_you_sell`, `always_emphasize`, `never_say`,
  `desired_feeling`) + migration + serializer + tests. **Shipped
  SESSION 232.**
- SPA: `/spokespeople/{id}/identity` route + 6-field form +
  `Define {name}` masthead button state signal + vitest tests.
  **Shipped SESSION 232.**
- Copy: field labels + placeholders + Character OS framing, all
  name-interpolated (no hardcoded "Oliver"). **Shipped SESSION
  232.**
- Threshold for "meaningfully filled" empty-state signal is 4 of
  6 non-empty fields. Chosen to require enough substance for
  Videos + Talk to feel grounded, not full completion.

**Added SESSION 233 (Chapter 6 — Ongoing training):**

- Backend: `Ask` requires a small viewset that composes retrieval
  (`recall_knowledge` R7.1 substrate) with a small LLM synthesis
  call and returns `{answer, citations: [{document_id, title,
  chunk_ids, score}], no_source: bool}`. Design deferred to the
  Chapter 6 implementation slice.
- Backend: inline doc-edit requires an authenticated PATCH on
  `KnowledgeDocument` that triggers re-embed (existing
  `embeddings.embed_document` Celery task is idempotent and
  wipes prior chunks — reuse). Design deferred to the
  implementation slice.
- Backend: re-embed status polling / subscription surface — the
  SPA needs to know when a re-embed finishes so re-ask can
  activate. `KnowledgeDocument.status` (`pending / processing /
  processed / failed`) is the substrate; the surface is a poll
  endpoint or WebSocket push, TBD in the implementation slice.
- Backend: worker-liveness at session start — the SESSION 233
  boot experience proved that a missing Celery worker is a
  silent failure class. The queued **P1 2.8-d** doctor extension
  (runserver freshness check) should be paired with a companion
  worker-liveness check so Chapter 6's re-embed gate has a
  bounded worst case. Not blocking Chapter 6's design lock; is
  blocking for its ship bar.
- SPA: detail-page Ask panel (text input + answer + receipt +
  fix affordances). New component.
- SPA: in-place Talk swap — refactor of the existing
  `/spokespeople/:id/talk` route's lifecycle component into an
  embeddable panel that can mount inside the detail page's
  portrait slot. Cost governance (R9 CostTicker, R8.2 error
  fallback) preserved.
- SPA: return-visit welcome copy on Beat 1 — requires a
  last-visited-at signal per (user, spokesperson). Design
  deferred.
- SPA: un-extracted-artifact re-surface on Beat 1 — requires a
  Chapter 5 close-signal (asset was created, was never
  extracted). Also deferred.
- Copy: all Chapter 6 copy must interpolate `{name}` (no
  hardcoded "Oliver"). Same rule enforced by the SESSION 232
  identity surface.

### Deferred future possibilities (not v1)

- Chapter 2 Beat 5 script personalization beyond Oliver naming
  himself + his role. Chapter 4 owns specificity; keep Chapter
  2 generic to preserve Chapter 4's payoff.
- Chapter 2 multi-take arrivals ("Oliver tries a different
  intro"). Chapter 2 fires once.
- Chapter 2 Beat 1 candidate-tile row rebuilt as job-fit
  surfaces. SESSION 230 walk verdict: wizard is smooth; do not
  rebuild.
- Vocabulary rename ("Spokesperson" → "Assistant" or similar).
  SESSION 230: *"changing to Assistant doesn't change anything
  but a title."*
- Oliver referencing his own script choices in Beat 5 reactions
  (*"I led with the origin story because you said it
  mattered"*). Commits to defensible reasoning about script
  choices — postpone to a later iteration.
- Oliver asking follow-up questions during teaching (Chapter 3
  dialogue-style). Postponed post-arc to avoid over-scoping v1.
- Multiple recommended first assignments in Chapter 5. Pattern
  supports it; v1 delivers one.
- Confidence indicators of any kind. Explicitly deferred (rule
  5 tension with metaphor).

### Unresolved questions

- **Trust boundary for script edits (Chapter 5 Beat 2).** If a
  customer edits Oliver's script to contradict what he was
  taught, does Character OS surface the conflict? v1 posture:
  customer's edit is authoritative, no override. A future
  *"trust boundary"* affordance may flag conflicts to the
  operator without blocking; not designed here.
- **"Have Oliver try another take" branching (Chapter 5 Beats
  5–6).** Should the affordance branch between "same script,
  different take" and "let me edit the script first"? v1
  proposal: small chooser, one click. Ratify in Chapter 5's
  implementation slice.
- **Chapter 6 re-surface timing.** Session-based vs time-based
  vs action-based. Belongs to Chapter 6's session design.
- **Chapter 2 shape.** RESOLVED SESSION 230 — see §"Chapter 2 —
  Hire Oliver" above. The existing `CREATE_SPOKESPERSON_WIZARD.md`
  is honored across rules 1, 2, 3, 5, 6 and *extended* on rule 4
  (Beat 5's one-way rendered arrival is not a conversation).
- **Chapter 2 Beat 5 render location.** The current post-confirm
  flow navigates to `/spokespeople/{id}/welcome`. Beat 5 could
  extend that route, or render inline in the wizard's Confirm
  step before navigation. Ratify in Chapter 2's implementation
  slice.
- **Chapter 2 Beat 5 fallback recipe.** If `talking_head`
  latency isn't fast enough for the arrival moment, is there a
  lighter arrival recipe (voice-only, portrait-only)? First
  hypothesis: no fallback — Beat 5 either renders or the honest-
  failure path fires. Depends on measured latency.
- **Voice sampling source (Beat 3).** Do Runway's presets ship
  with sample clips, or does the platform need to bake and
  cache them? Small implementation question, but affects the
  slice sequencing.
- **Chapter 0 / Chapter 1 two-job plant surface.** Where and
  how the two-job frame is planted (marketing / landing /
  arrival) is deferred to Chapter 0's and Chapter 1's design
  sessions. Chapter 2's Beat 1 restate assumes it exists.

---

## Next design target

**SESSION 233 update:** Chapter 6 — Ongoing training is now
scope-locked (design). Reframed from *"management page"* to
*"coaching feedback loop"* during the product-review walk. Lives
on the spokesperson detail page, not on `/workspace/knowledge`.
Ratified during a live returning-operator walk against
"Chris's workspace" (bookstore-themed KDs, Oliver spokesperson).
See §"Chapter 6 — Ongoing training" above.

**SESSION 232 update (still current):** The spokesperson detail
page's Identity surface (design + implementation) shipped that
session. The three-layer distinction (body / identity /
knowledge — contract rule 10) is foundational for every
downstream chapter and lives in §"The three layers of a
spokesperson" above.

Chapter 2 (SESSION 230), Chapter 3 (SESSION 229), Chapter 4
(SESSION 229), Chapter 5 (SESSION 229), the Identity surface
(SESSION 232), and Chapter 6 (SESSION 233) are now all scope-
locked at design level. The next highest-value design work is
one of three candidate chapters, in priority order:

1. **Chapter 1 — Arrive.** The signup → first-landing chapter
   that precedes Chapter 2 and (with Chapter 0) plants the
   two-job frame Chapter 2 Beat 1 restates. Small in surface
   area; load-bearing for Chapter 2's Beat 1 to actually
   restate against a plant.
2. **Chapter 7 — Grow the team.** The multi-spokesperson chapter
   Chapter 6 hands to. Downstream from Chapter 6's coaching-loop
   ownership shift. Requires designing what the workspace
   surfaces feel like when the roster is no longer *"Oliver and
   empty slots."* Higher-value than Chapter 0 for customers who
   reach it.
3. **Chapter 0 — Discover.** The marketing / landing chapter.
   Plants the two-job frame that Chapters 1 and 2 restate.
   Furthest from the current product surface; may be an
   operator-authored content pass rather than a Claude design
   session.

The parallel implementation-planning reconciliation of
`CREATE_SPOKESPERSON_WIZARD.md` against Chapter 2's design and
the Chapter 6 implementation slice both remain queued. Chapters
0-1 and 7 remain higher-level maps until their respective
design sessions land.

---

## Cross-references

- `CHARACTER_OS_WHAT_IT_IS.md` — narrative anchor. Should
  reference this doc as the scope-lock for onboarding + first-
  work journey.
- `CREATE_SPOKESPERSON_WIZARD.md` — Chapter 2 predecessor.
  Reconciliation is the next design session's work.
- `KNOWLEDGE_LAYER.md` — K-arc scope lock. Chapter 3 sits
  *above* the K-arc as an onboarding wrapper; the K-arc is the
  retrieval + ingest substrate. Chapter 6's Ask receipt depends
  on K-arc chunk-to-doc provenance; Chapter 6's re-ask gate
  depends on `KnowledgeDocument.status`.
- `WORKSPACE_FABRIC_V1.md` — F-arc scope lock. Chapter 7's
  team-roster affordance sits in the workspace fabric surface.
  `/workspace/knowledge` (Chapter 6 Beat 6 secondary surface)
  is an F-arc-adjacent inventory page.
- `REALTIME_AVATAR_V1.md` — R-arc. Chapter 4's inline first
  question uses R-arc infrastructure (`recall_knowledge` +
  `RealtimeSession` short forms) but is not itself a realtime
  conversation. Chapter 6 Beat 5 (Talk in-place) is an R8
  refactor — the existing lifecycle component collapses into
  the detail page's portrait slot. R9 cost governance + R8.2
  CostTicker + WebRTC fallback carry over unchanged.
- `VIDEO_COMPOSITION_V1.md` — V-arc. Chapter 5's v1 delivery
  uses V-arc recipe infrastructure (`talking_head` or a
  Chapter-3-grounded successor).
