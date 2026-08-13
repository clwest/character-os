---
title: "Character OS — Product Design Brief"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["PRODUCT_IA_V1_2026-08-06.md"]
supersedes: "docs/design/UI_REDESIGN_V2.md (philosophy layer; UI_REDESIGN_V2 remains the pre-redesign implementation record)"
---

# Character OS — Product Design Brief

*The philosophy foundation for the Character OS redesign. Defines the beliefs, the mental model, the customer journey, and the goals the product optimizes for.*

**Read this document first.** Then read the companion [Product Information Architecture](PRODUCT_IA_V1_2026-08-06.md), which turns this philosophy into structure — surfaces, onboarding, reveal system, object relationships, and the principles that keep them coherent.

---

## Design Philosophy

Six beliefs anchor the redesign. Each is decision-forcing — when a design question arises, one of these should end the debate.

### 1. The customer is never asked to think in objects.
A small-business owner opening the app for the first time should encounter **three** customer-facing concepts. Everything else is either a state of one of those three (draft vs. published), an implementation detail (assets, bundles, compositions, recipes), or an advanced concept that discloses later when the customer's use pattern demands it (series, tools, engine connections).

### 2. The AI teammate is the surface — but the teammate is a peer, not a doorway.
The teammate is the primary metaphor. It greets the customer, understands context, makes suggestions, and offers help. It brings the app's warmth.

But the teammate is a **coworker, not a receptionist.** Always nearby, never required for obvious actions. The customer never thinks *"I have to ask Alex before I can do anything."* They think *"Alex is always nearby if I need help."* The buttons carry the app; the teammate carries the relationship.

### 3. The publish moment is the axis the product rotates around.
Everything before publish is preparation. Everything after publish is reinforcement. This principle collapses several artificial distinctions: drafts and published items live in the same place with different states; publishing gets promotion; returning users see wins first, drafts second.

The success moment is not rendering — it is **publishing something the customer is genuinely proud to put in front of customers.**

### 4. Capability is earned, not offered.
No feature appears in the first-run experience unless it directly serves the "one useful thing today" wedge. The Realtime Avatar, Bridge Tools, series, and multi-teammate features do not exist in Day-1 navigation. They surface through **capability reveals** — a hybrid pattern combining time-based, usage-based, and ask-triggered disclosure (with ask-triggered winning precedence).

### 5. The customer accomplishes work; they never configure software.
Every screen must pass one test: *"Does this feel like setup or like work?"* Setup screens get merged, deferred, or eliminated. Work screens get invested in.

Forbidden anti-patterns:
- Settings pages that appear before the customer has done anything worth configuring.
- Preference dialogs that ask about workflow before workflow exists.
- Empty states that ask the customer to add data before the app does anything useful.
- Configuration wizards masquerading as onboarding.

The customer does not want to *"manage their spokesperson"* — they want to **make things with the teammate's help.**

### 6. The customer's work is displayed as pride, not inventory.
Every surface that shows what the customer has made — Home's featured piece, Library's gallery, My Team's body of work, Studio's preview — treats each piece as an accomplishment worth admiring. Not files to organize. Not assets to manage. Not analytics to interrogate. **Pride.** Everything else exists to support that emotion.

Consequences ripple across the product:
- Cards render pieces in their native form, never as thumbnails or list rows.
- Batch operations use conversational, respectful framing (*"tidy up"* not *"select and manage"*).
- Delete is soft by default; discard language is avoided.
- Metadata is minimal so the work itself dominates.
- The customer never encounters storage terminology, file-system metaphors, or administrative controls.

---

## Mental Model

Three customer-facing concepts. Everything else is state, picker, or nested detail.

| Concept | What the customer thinks it is | What it replaces internally |
|---|---|---|
| **Home** | *"Where I go when I want to make something."* An active surface with obvious next actions. My AI teammate is here. | Dashboard, Recipe gallery entry, Campaign entry, Conversation entry |
| **Library** | *"Everything I've made, in one place."* Drafts and published, unified. A gallery of accomplishments. | Videos list, Compositions list, Assets library, Scripts list, Bundles list, Campaigns list, Transcripts list |
| **My Team** | *"The people who show up in my marketing."* Each teammate has a face, a voice, a personality, and — when I'm ready — the ability to talk live with my customers. | Spokespeople list + detail, Knowledge dashboard, Realtime talk route, Bridge tools, Engine connections |

**A fourth surface, contextual only:**
- **Studio** — the actual making surface. Not a place you navigate to; a full-screen state you enter *from Home* when you decide what to make. Replaces the Recipe form, Script draft/detail, Composition status, Bundle new, and everything wizard-shaped.

**Naming is placeholder.** *Home / Library / My Team / Studio* are working words. What matters is the **shape**: three nouns, one contextual surface, everything else nested.

---

## Customer Journey

### Arc 1 — The Wedge (Day 1 → First Publish)

*The customer's question: "Can this actually help me?"*
*Design pattern: focus, urgency, no branching.*

1. **Sign up.** Two fields. No email verification wall unless legally required. The customer lands on Home in under 60 seconds.
2. **Meet your teammate.** Home opens with a warm, human greeting from a *pre-provisioned* AI teammate. The customer does not create a teammate to start — one is waiting. They can rename it, change the face, adjust the voice later. First run defers all customization.
3. **Tell it what you need.** Single conversational prompt: *"What are you trying to do today?"* The teammate parses intent and routes to Studio with the right maker preloaded. **No recipe gallery. No format picker. The teammate infers.** If the customer is uncertain, the teammate helps them find direction rather than failing.
4. **Make one thing.** Studio is single-focus. The customer sees the draft take shape. The teammate narrates progress in warm, plain language. No jargon. No status codes.
5. **Preview & publish.** The publish action is the largest visual affordance in Studio. Publishing lands the customer back on Home with a **celebration moment** — the published thing is featured. This is the emotional peak; design accordingly.

**Success signal:** the customer publishes something they are genuinely proud to put in front of customers. **Time to first publish** is the north-star metric of Arc 1.

**Explicitly deferred in Arc 1:**
- Multiple teammates.
- Knowledge upload (the teammate uses inferred defaults and the short onboarding for Day-1 grounding).
- Series.
- Realtime avatar.
- Publish bundles (one thing at a time).
- Any concept of a "recipe" — the teammate picks; the customer never chooses from 20 options.

### Arc 2 — The Habit (Return → Operating System)

*The customer's question shifts: "Is this where I come to work on my marketing?"*
*Design pattern: dwelling, ambient value, capability reveals.*

1. **Return.** Home looks different. The teammate greets them by referencing what they published last time and reflecting patterns it has silently observed: *"Last week's ad got some traction — and I've noticed you tend to post on Fridays. Want to make a follow-up, or something new?"* Ambient status, not a dashboard of numbers.
2. **Library appears in navigation** — only after the first publish. Before that, the concept isn't relevant.
3. **Capability reveals** are woven into the teammate's conversation, not a settings screen. Reveals follow three trigger types — **time-based, usage-based, and ask-triggered** — with ask-triggered winning precedence. Reveals never interrupt active work.
4. **My Team becomes navigable** when the customer adds a second teammate. Before that, the single teammate lives inside Home's context.
5. **Library becomes the operating system.** Progressive filtering, sort by series, sort by teammate, batch actions. The customer discovers these as they scale — they are not present when the library holds 1–3 items.

**Success signal:** the customer returns unprompted, publishes again, and expresses **ownership language** — *"my teammate," "our voice," "our next series."* **Weekly active use** is the north-star metric of Arc 2.

---

## Load-Bearing Experience Patterns

Two cross-cutting patterns are foundational enough to name at the philosophy level. Their full treatment lives in the IA spec.

### Process transparency
The teammate narrates continuously in warm editorial language during Studio. Loading spinners are replaced by *sentences*. Progress isn't a bar; it's observations: *"I'm drafting the script..."* *"I found information about your bakery that should work well here."* The teammate is always interruptible. Narration is optional to attend to — the customer can read it, ignore it, or scroll it — but it makes the app feel collaborative rather than transactional. Narration is also a **confidence-building surface**: when the customer sees what the teammate knows, they trust it more.

### Pattern memory
The teammate silently observes and reflects patterns — topic focus, publishing cadence, format preferences, tone preferences, working hours. These observations surface in the Home greeting and shape the teammate's suggestions. **The customer never configures memory.** No memory settings screen exists. Correction and forgetting happen through natural conversation: *"Actually, that was just this summer,"* or *"Stop reminding me about the sale — it's over."*

Memory is what turns Home from a control room into a colleague you know.

---

## Information Architecture Principles

The IA is governed by **ten principles**, defined in full in the companion IA spec. Summarized here for orientation:

1. **Three nouns, no more.** Home, Library, My Team — plus contextual Studio.
2. **State, not screens.** Drafts, published, in-progress, archived are states of the same object.
3. **The teammate is present on every surface.** Ambient, warm, escape-hatch present.
4. **No internal vocabulary leaks.** Composition, asset, bundle, recipe, spokesperson corpus, engine bridge, workspace, tier — none appear in customer UI.
5. **Progressive disclosure has triggers, not toggles.** Capability reveals happen because the customer earned or asked, not because they flipped a switch.
6. **Errors speak human.** No HTTP codes, no stack traces, every error has: what happened, what to do, one-tap resolution where possible.
7. **The teammate is a coworker, not a receptionist.** Never a gate to obvious actions.
8. **Reveals respect flow.** Reveals fire between actions, never during them.
9. **The teammate remembers; the customer never configures memory.**
10. **Reveals feel inevitable, never announced.** No "unlocked" badges. If the customer notices the reveal *system*, we failed.

Full articulation, rationale, and enforcement rules are in [PRODUCT_IA_V1_2026-08-06.md §11](PRODUCT_IA_V1_2026-08-06.md#11-the-ten-information-architecture-principles).

---

## Experience Goals

Measurable outcomes to design for. Every design decision should improve at least one; every design decision that harms one requires an explicit trade-off note.

| Goal | What it measures | Why it matters |
|---|---|---|
| **Time to first publish** | Median minutes from sign-up to first published work | Arc 1's north star. Above 15 minutes = the wedge is failing. |
| **First-publish pride score** | Post-publish micro-survey: *"How proud are you of what you just made?"* 1–5 | The success moment must be genuine. High publish rate with low pride is a failure mode. |
| **7-day return rate** | % of customers who return unprompted within 7 days of first publish | Wedge → retention handoff. Below 40% signals the operating system isn't taking. |
| **Vocabulary miss rate** | Support tickets or in-app confusion signals mentioning internal terms | Enforces IA-4. Should trend to zero. |
| **Capability reveal acceptance** | % of triggered reveals the customer engages with | Validates IA-5. Low acceptance = reveals firing at the wrong moment. |
| **Advanced-user drop-off** | % of returning users who abandon a workflow because they can't find something | Guards against progressive disclosure hiding what returning users know exists. |

---

## Signal to the Lead Project Designer

**Preserve:** the editorial voice, the trust the app has earned, the technical capability (every backend feature remains — only the surface changes), the calm/warm tone.

**Discard without apology:** the 4-step wizard, the recipe gallery as a customer surface, the split between Videos / Compositions / Assets, the Bundle noun, the Campaign as a Day-1 concept, all "advanced mode" thinking, any error copy that includes an HTTP status code.

**Question everything else.**

The IA spec ([PRODUCT_IA_V1_2026-08-06.md](PRODUCT_IA_V1_2026-08-06.md)) turns this philosophy into structure. Screen designs will follow, one screen at a time, once IA is agreed.

---

## Revision History

**v1 — 2026-08-06.** Initial version. Written during an intensive product design session between the operator (Chris D) and the Head of Product Design LLM. Major decisions incorporated:

- Scope framed as a **true product redesign**, not a UI refresh. All existing screens and flows treated as questionable.
- **Customer scope:** launch customer AND advanced operator, with capability emerging through progressive disclosure.
- **JTBD scoped in two arcs:** wedge (*"one useful thing today"*) and retention (*"marketing operating system"*).
- **Success moment anchored on first publish**, not first render.
- **Mental model collapsed** from 11 internal nouns to 3 customer-facing concepts (Home / Library / My Team) plus contextual Studio.
- **Home resolved as action-first** with ambient teammate presence, not conversation-first.
- **Teammate positioned as coworker, not receptionist** — never a gate.
- **Studio narrates continuously**; supports invisible collaboration-style spectrum (autonomous / collaborative / guided).
- **Onboarding uncertainty at Q3** treated as a marquee moment, not a failure.
- **Home personalizes through pattern memory**, never through settings.
- **Reveal system:** hybrid time / usage / ask, with ask-triggered winning precedence. Reveals respect flow and feel inevitable.
- **Realtime avatar deferred** to Day-14+/10-publish reveal or ask trigger.
- **Publish destinations Day 1:** download + shareable link. Direct-to-platform via reveal only.
- **Ten IA principles** locked (from an original six).
- **Six philosophy pillars** locked (from an original four). Pillar #6 (*"the customer's work is displayed as pride, not inventory"*) emerged from Library screen design and applies across all surfaces displaying customer work.
