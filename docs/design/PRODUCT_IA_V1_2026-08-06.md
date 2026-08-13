---
title: "Character OS — Product Information Architecture"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md"]
supersedes: "docs/design/UI_REDESIGN_V2.md (IA layer; UI_REDESIGN_V2 remains the pre-redesign implementation record)"
---

# Character OS — Product Information Architecture

## v1 — foundation, pre-screen-design

*Companion to the [Product Design Brief](PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md). Where the brief defines philosophy, this defines structure. Where the brief chooses direction, this defines the map. Individual screen designs will follow — they should feel almost mechanical once this document is agreed.*

**Read the Brief first.** This document assumes the brief's philosophy is understood and applied. Where terms are used without introduction (*teammate*, *piece*, *reveal*, *ambient presence*), the Brief is the definition source.

---

## 0. Reading Contract

- Every major surface is defined by five questions: *why it exists, what the customer is trying to answer, what they should feel, what they should accomplish, what leads to the next surface.*
- Every surface has **one obvious primary action.** Secondary actions may exist; the primary is stated explicitly.
- Terms in `code style` are internal-only; they will not appear in customer UI.
- When this doc says "the teammate," it refers to the AI presence — the customer's active teammate at that moment.

---

## 1. Customer-Facing Object Model

Three objects the customer will actually think about.

### 1.1 A piece of work

The deliverable. A video, a script, a live conversation — anything the teammate helps make.

- **UI language:** describe what it is contextually. *"Your summer sale video."* *"Your welcome message."* *"Your Wednesday call with Jamie."* **Never a generic noun.** No *"post,"* no *"piece,"* no *"asset."*
- **States:** In progress → Ready to publish → Published → Archived (archived state is customer-hidden until the archive reveal fires).
- **Belongs to:** exactly one teammate.
- **May belong to:** a series (introduced through the series reveal, not before).

### 1.2 A teammate

The AI face/voice/personality representing the customer's business.

- **UI language:** *"your teammate,"* *"Alex"* (or whatever the customer named them). Never *"spokesperson,"* *"avatar,"* or *"persona."*
- **Has:** a name, a face, a voice, what they know about the business, a body of work.
- **On Day 1:** one teammate is pre-provisioned. Customer can rename, reface, revoice at any point.

### 1.3 A series

A group of related pieces designed to go out together or in sequence.

- **UI language:** *"series,"* *"your welcome series."* Never *"campaign,"* *"bundle,"* or *"recipe."*
- **Introduced:** via reveal, not present at Day 1.

### 1.4 What disappears from the customer-facing model

The following exist in the backend but are **never** named in the UI, navigation, copy, tooltips, error messages, or confirmations:

`composition`, `asset`, `bundle`, `recipe`, `primitive`, `spokesperson`, `spokesperson corpus`, `engine bridge`, `tool invocation`, `workspace`, `tier`, `script` (a state of a piece, not an object), `transcript` (a nested attribute of a live conversation), `knowledge document` (a nested attribute of a teammate), `campaign` (replaced by `series`), `realtime session` (replaced by `live conversation`).

Enforcement: IA-4. Any UI element mentioning any of these fails IA review.

---

## 2. The Four Surfaces

The customer navigates among four surfaces:

1. **Home** — the control room.
2. **Studio** — the making surface. Contextual; entered from Home.
3. **Library** — the body of work. Introduced after first publish.
4. **My Team** — the teammates. Introduced when a second teammate is added.

**The Day-1 navigation contains one item: Home.** Everything else reveals as earned.

**The full nav (post-reveals) contains four items at most.** There is no fifth. No "Settings." No "Help." No "Admin." Where those functions exist, they nest inside the relevant surface — teammate settings live inside a teammate detail view; system status is invisible unless there's a problem.

---

## 3. Onboarding — from sign-up to first Studio session

Before any surface exists, there is a moment. Sign-up lands the customer here.

- **Why does this surface exist?** To go from zero to a first Studio session with the least friction possible.
- **What question is the customer trying to answer?** *"How do I get started?"*
- **What should they feel?** Instantly welcomed and understood. Not interviewed.
- **What should they accomplish?** Answer three short questions and land in Studio, ready to make.
- **What leads them to the next surface?** The third question transitions directly into Studio with a preloaded first project.

### 3.1 The pre-provisioned teammate

Before the customer sees the first question, a teammate is silently provisioned. Neutral warm name (default: *"Alex"* — genderless, universal, easy to say aloud). Neutral warm face. Neutral warm voice. The customer meets them in question 1.

### 3.2 The three questions

**Q1 — *"Hi. I'm Alex. What kind of business are you running?"***
One line, free-text. *"A neighborhood bakery."* *"An HVAC company."* *"A solo bookkeeping practice."*

**Q2 — *"Got it — a bakery. Who are you making this for?"***
One line, free-text. *"People in the West Loop looking for good sourdough."* If the customer struggles, an inline hint appears: *"Just tell me who your ideal customer is."*

**Q3 — *"One more. What do you want to make today?"***
One line, free-text. *"A video announcing our new summer menu."* The teammate confirms understanding and transitions to Studio.

### 3.3 Optional Q4

If the Q3 answer mentions time, urgency, or event (*"this weekend," "for tomorrow"*), a fourth prompt appears: *"Anything special going on I should know about?"* Answered or skipped, the transition to Studio proceeds.

### 3.4 The transition

**Primary action:** submitting Q3 IS the transition — no "Continue" button.

The customer's answer becomes the working brief. The teammate says: *"Alright — let me get started. Here's what I'm thinking."* Studio opens; the piece begins to materialize.

**No wizard. No form. No configuration. Three answers, and they are making.**

### 3.5 Design rules for onboarding

- One question visible at a time.
- The teammate's face and name are visible from Q1 onward — the customer is meeting a person, not filling in a form.
- No progress indicator. Three questions is short enough that a "1 of 3" bar is anxiety-inducing overhead.
- No optional fields. Anything not essential is a reveal.
- No email verification, industry picker, business-size picker, or account settings.

### 3.6 Handling uncertainty at Q3

If the customer's Q3 answer signals uncertainty (*"I don't know,"* *"I'm not sure,"* *"I need more customers,"* empty answer, *"help me figure it out"*), the teammate does not fail or push forward with nothing. Instead:

**Teammate: *"No problem. Let's figure it out together."***

Studio opens in a **conversational warmup** — a short back-and-forth (3–5 exchanges) where the teammate helps the customer surface a specific direction:

1. Teammate: *"Tell me one thing that's on your mind for your business right now."*
2. Customer: *"I want more foot traffic."*
3. Teammate: *"Got it. Are you thinking about right now, or a specific time of year?"*
4. Customer: *"Right now, summer's slow."*
5. Teammate: *"Alright — I have an idea. Let's make a short video that gives people a reason to come in this week. Sound good?"*
6. Customer: *"Yes."*
7. Studio proceeds normally; the piece is now framed.

**This is one of the strongest moments in onboarding.** Customers who arrive uncertain get their most reassuring experience early: *the teammate is a thinking partner, not just a producer.*

Composed with §5.6: an uncertain arrival defaults Studio to **guided** for the first piece — more teammate involvement, more explanation, slower pace. Confidence is built through the first success; autonomy earns its way in from there.

---

## 4. Home

- **Why does this surface exist?** To orient the customer to what's happening in their marketing and give them an obvious next step.
- **What question is the customer trying to answer?** *"What should I do right now?"*
- **What should they feel?** Grounded, welcomed, in control. Like sitting down beside a helpful colleague who already knows what's going on.
- **What should they accomplish?** Choose their next action.
- **What leads them to the next surface?** Choosing an action leads to Studio (make), Library (see what's been made), or My Team (adjust a teammate).

### 4.1 Structure

Home has three zones stacked vertically.

**Zone A — The greeting.**
A single-sentence, context-aware greeting from the teammate:
- *"Welcome back. Last week we published your summer sale video."*
- *"Morning. You have a draft from yesterday — want to keep working on it?"*
- *"Good to see you. Nothing new since Tuesday — want to make something today?"*

**Zone B — The action set.**
Three to five **contextual action buttons**. Never more than five. The **first button is the primary action** — visually dominant. The teammate's role in choosing them is invisible curation, not presentation. The buttons carry the app.

Returning user with an in-progress piece:
- **[Continue your summer sale video]** ← primary
- [Start something new]
- [See everything you've made]

Returning user with 5+ published pieces:
- **[Start something new]** ← primary
- [Continue your welcome video draft]
- [Repurpose your best-performing post]
- [See everything you've made]

**Zone C — The featured piece.**
The most recently published work rendered inline. Not a thumbnail — the actual playable/readable piece. Below it, one soft affordance: *"Want to make a follow-up?"* — this is a reveal surface (ask-triggered pattern in visual form).

### 4.2 Primary action on Home

**Exactly one primary action per Home state.** Rendered as the visually dominant button in Zone B.

| State | Primary action |
|---|---|
| Fresh customer, no drafts, no publishes | **[Start something new]** |
| Has a draft | **[Continue your \<piece name\>]** |
| Just published | **[Make a follow-up]** *(reveal-driven)* |
| Been quiet a week+ | **[Start something new]** |
| 20+ published, no draft | **[Start something new]** *(with soft "explore what you've built →" nudge to Library)* |

### 4.3 What is NOT on Home

No metrics dashboard. No usage stats. No "Recently viewed" carousel. No teammate roster (that's My Team). No settings gear. No notifications inbox — critical updates surface as the teammate's greeting. No search bar (Library owns search).

**Home is deliberately small.** A control room, not a dashboard.

### 4.4 "Ask something else" — the conversational escape hatch

Below Zone B, a quiet affordance: *"Ask for something else →"*

Tapping it opens a short conversation with the teammate. This is where ask-triggered reveals fire. Deliberately quieter than the action buttons — most customers click; the customer with an unusual need has a way to type.

### 4.5 Pattern memory

The teammate silently observes and reflects patterns. The Zone A greeting draws from accrued patterns:

- **Frequency:** *"You've been posting every Friday."*
- **Topic:** *"Your last few videos have all been about summer promotions."*
- **Format preference:** *"You seem to prefer shorter videos."*
- **Timing:** *"You usually work on this in the morning."*
- **Voice preferences:** *"You've asked me to keep things warm and casual — sticking with that."*

**Rules:**
- No memory settings screen. Ever.
- No *"what should I remember about you?"* dialogue.
- Memory accrues silently from observed behavior.
- The customer can **correct memory in natural conversation** (*"Actually, that was just this summer — I don't usually post that often"*) and the teammate adjusts.
- The customer can **ask the teammate to forget** (*"Stop reminding me about the summer sale, that's over"*) and it does.

This is the mechanic that turns Home from a control room into a colleague you know. Not through settings — through observation.

---

## 5. Studio

- **Why does this surface exist?** To make one specific piece of marketing with the teammate's continuous collaboration.
- **What question is the customer trying to answer?** *"How do I turn this idea into something I can publish?"*
- **What should they feel?** Collaborative, in-flow, watched-over. Like a partner is working alongside them.
- **What should they accomplish?** Bring one piece from idea to preview-ready, and either publish or save.
- **What leads them to the next surface?** Publish → celebration in Home + placement in Library. Save → back to Home with the piece in "In progress" state.

### 5.1 Structure

Studio is **full-screen**, edge-to-edge. A subtle "back to Home" affordance top-left is the only nav element.

Three zones — horizontal on desktop, stacked on mobile.

**Zone L — The teammate presence pane.**
A persistent, warm visual channel showing the teammate. Their face, at rest or animated as they work. Below their face, a **narration stream**:

> *"Reading your brief..."*
> *"I think this should be a short vertical video — good for reels."*
> *"I found information about your bakery that should work well here."*
> *"Drafting the script now."*
> *"I'm going with a warm, friendly tone. You can steer me anytime."*

Narration is **optional to attend to.** The customer can scroll it, ignore it, or read it — the piece progresses regardless.

**Zone C — The piece as it forms.**
The center of Studio. As the teammate works, the piece materializes here — the script appears, the video preview builds, the audio waveform draws.

**Zone R — The steering pane.**
Quiet, contextual. Length options. Tone options. Format options. A free-text *"Tell me anything"* box. Each control is a **live steer** — changing it doesn't submit a form; it interrupts the teammate mid-work. Narration acknowledges: *"Switching to a playful tone."*

### 5.2 Interruption model

The teammate is **always interruptible.** The customer can:
- Change a steer (Zone R) — narration acknowledges.
- Click into a specific piece of the work (a line of script, a video segment) and say what they want changed. Voice or text.
- Say *"start over"* — teammate confirms, restarts.
- Say *"show me options"* — teammate produces two or three variants.

### 5.3 Primary action in Studio

Shifts as the piece progresses:

| Studio state | Primary action |
|---|---|
| Teammate is working | Passive — watch. No button dominates. |
| Piece hits "Ready to publish" | **[Preview]** |
| In preview mode | **[Publish]** *(see §6)* |
| After publish | Studio closes; Home appears with celebration. |

At any point, the secondary action is **[Save and come back later]** — puts the piece in "In progress" and returns to Home.

### 5.4 What is NOT in Studio

- No format picker at the entry (the teammate infers).
- No "Recipe" selector (invisible concept).
- No "Save Draft" as a *distinct* concept — everything is auto-saved. The button says *"Save and come back later"* but state was already persisted.
- No progress bar. Narration IS the progress.
- No modal dialogs. Everything happens in the three zones.

### 5.5 Design rules for Studio

- The teammate's face is always visible. The customer is not alone.
- Narration is always present but never blocks input.
- Preview is a moment of quiet — narration pauses; the piece is the only thing.
- Publish is one tap from preview. Confirmation exists but is warm (*"Ready to put this in front of your customers?"*), not clinical.

### 5.6 Collaboration-style spectrum

A **spectrum, not modes.** The teammate infers the customer's preferred style from tone, pace of interruption, and explicit ask. Three points on the spectrum:

- **Autonomous.** Teammate makes decisions, narrates them, delivers. Customer watches.
- **Collaborative.** Teammate makes proposals, checks in at key moments, invites input. Default.
- **Guided.** Teammate proposes, waits for approval on each step. Slower but more control.

**Signals that push toward each pole:**
- *"Take your best shot"* / *"just make it"* → autonomous.
- Frequent steering-control use or *"show me options"* → guided.
- Onboarding Q3 answered specifically and confidently → default to autonomous for first piece.
- Onboarding Q3 answered vaguely (see §3.6) → default to guided for first piece.

**The spectrum is invisible to the customer.** They never see a mode selector. They feel that the teammate adapts.

---

## 6. The Publish Flow

The axis moment. Not a surface in nav but a defined flow — treated with its own mental-progression frame because it deserves the discipline.

- **Why does this exist?** To make the moment of putting work in front of customers feel like a real accomplishment.
- **What question is the customer answering?** *"Is this ready? Am I proud enough of it to share?"*
- **What should they feel?** A small held breath. Then release.
- **What should they accomplish?** Move a piece from "made" to "shared."
- **What leads them next?** Celebration in Home. Placement in Library. Suggestion for what to do next.

### 6.1 The flow

1. **Studio, when the piece is preview-ready.** Teammate: *"I think this is ready. Want to see the finished piece?"* Preview button becomes visually dominant.
2. **Preview.** Full-screen, minimal chrome. The piece plays. Two buttons at the bottom:
   - **[Publish this]** — primary, visually dominant.
   - [Keep working] — secondary, quiet.
3. **Publish confirmation.** Short modal: *"Ready to put this in front of your customers?"* with destination line: *"Sending to: Download + shareable link."* Two buttons:
   - **[Yes, publish]** — primary.
   - [Not yet] — secondary.
4. **Publishing state.** Modal closes; teammate narrates: *"Publishing now."* Target under 3 seconds when destination is download or link.
5. **Celebration.** Studio closes. Home appears. The featured piece slot (Zone C) shows the just-published work with celebration copy: *"Published. This is out there now."* No confetti. Dignified.
6. **Next-step nudge.** Below the featured piece, the teammate's next suggestion appears (variant, follow-up, series). Ask-triggered reveals may fire here.
7. **Library placement.** If Library nav wasn't yet visible, this is the moment it appears — with a subtle one-time "draw the eye" animation. The customer can click through or wait.

### 6.2 Publish destinations

**Day 1: Download + shareable link.** The published piece is available for download and behind a copy-shareable link. **No platform OAuth on Day 1.** This is a design commitment — the customer never configures software during their first publish. They publish, get a link, share it wherever they want.

**Reveal: Direct-to-platform publishing.**
- **Trigger:** ask (*"I want to post this to Instagram directly"*) OR usage (after 3+ published pieces).
- **Teammate offer:** *"I can post directly to Instagram for you if you connect it once. Want to?"*
- **Flow:** OAuth in a modal. Future publishes offer direct-to-platform as a destination option.

---

## 7. Library

- **Why does this surface exist?** To show the customer what they've built and give them ways to reuse, refine, or celebrate it.
- **What question is the customer trying to answer?** *"What have I made — and what should I do with it now?"*
- **What should they feel?** Proud, accomplished, curious about their body of work.
- **What should they accomplish?** Find, view, reuse, share, or refine a specific piece.
- **What leads them to the next surface?** Opening a piece → detail view; "Remix this" → Studio; "See more from this teammate" → My Team.

Library is the primary embodiment of Philosophy #6 (the customer's work is displayed as pride, not inventory). Every downstream decision in this section is answerable by asking: *does this feel like pride, or like storage?*

### 7.1 First appearance

Library **does not exist in navigation until the customer has published their first piece.** The concept isn't relevant before that. The moment of first-publish surfaces it (see §6.1 step 7).

### 7.2 Structure — three progressive display modes

**Mode A — Small library (1–9 published pieces).**
A vertical stack of large, playable/readable cards. Each piece is shown in its final form — video plays inline on hover, script text is visible. No thumbnails, no rows of icons. This is a **wall of the customer's work.**

**Mode B — Growing library (10–30 pieces).**
A denser grid; pieces still play/render inline. Sort defaults to newest first; a soft filter row appears: *"All / Videos / Scripts / [Teammate name]."* No dropdowns — just visible chips.

**Mode C — Established library (30+ pieces).**
Grid remains. Search bar appears at top. Series filter becomes prominent (if series exist).

**Drafts are shown separately** in every mode, in a quieter zone at the bottom labeled *"Still in progress."* Drafts are not the star of Library.

### 7.3 Primary action in Library

**On the list view:** the primary action is **opening a specific piece.** The whole card is tappable; there is no "View" button. The card IS the button.

**On a piece detail view:** contextual —
- Piece is Published: **[Remix this]** — direct action; opens Studio with the piece as starting point. Narration may follow *after* the click, but the click itself is unmediated.
- Piece is a Draft: **[Continue working on this]** — opens Studio at the point they left off.

Secondary on detail: **[Copy shareable link]**, **[Download]**, **[See who made this]** (link to teammate in My Team), **[Delete]** (quieter, with confirmation).

### 7.4 Library-side reveals

- **Best performing** — reveals after 5+ published pieces with measurable data (or after 14 days). *"I can show you what's performing best. Want to see?"* Adds a "Best performing" filter chip.
- **Series view** — reveals when the first series is created. Adds a series toggle.
- **Repurpose** — ask- or usage-triggered. Adds a "Remix" primary action on piece detail.
- **Batch actions** — reveals at 20+ pieces. Long-press or shift-click enters batch mode.

### 7.5 What is NOT in Library

- No folder tree. Never.
- No tag manager as a management screen.
- No "shared with" surface until multi-user is real.
- No "trash" as a distinct nav destination — deleted pieces vanish with a 30-day teammate-managed grace period (*"You deleted your welcome video a week ago — want it back?"*).

---

## 8. My Team

- **Why does this surface exist?** To let the customer manage who represents their business and what each teammate knows.
- **What question is the customer trying to answer?** *"Who is showing up in my marketing, and are they representing me well?"*
- **What should they feel?** Confident about the presences representing them.
- **What should they accomplish?** Review teammates, adjust one's voice/knowledge/face, or add a new teammate.
- **What leads them to the next surface?** Selecting a teammate → detail. "Make something with them" → Studio, pre-scoped.

### 8.1 First appearance

My Team **does not exist in navigation until the customer has added a second teammate.** Before that, the single teammate is present ambiently on Home and can be adjusted via a small "Edit Alex" affordance in Home Zone A.

When the customer adds a second teammate — via reveal (§9) — the My Team nav item appears with the same one-time "draw the eye" animation used for Library.

### 8.2 Structure — list view

A vertical stack of large teammate cards. Each card shows:
- The teammate's face (large, expressive).
- Their name.
- A one-line description (*"Speaks casually about the bakery to neighborhood locals"*).
- Their body of work count (*"34 pieces made"*).

**Primary action:** open a teammate.
**Secondary action:** **[Add another teammate]** — quiet, at the bottom.

### 8.3 Structure — teammate detail

A single teammate's full profile. Not a settings screen — a **work surface for adjusting the teammate.**

Three zones:

**Zone A — Presence.**
Face (with quiet *"Try a different face"* affordance). Voice (with *"Play sample"* and *"Change voice"*). Name (editable in place). Personality traits surfaced as short sentences (*"Speaks casually. Warm. Optimistic."*) with a quiet *"Adjust"* that opens a natural-language dialogue with the teammate about their own presence.

**Zone B — What they know.**
The teammate's knowledge of the business, rendered as short paragraphs the customer can read and edit. When the customer clicks *"Adjust,"* the teammate asks: *"What should I know differently?"* Free-text updates knowledge.

**Never rendered as** a file browser of uploaded documents, a URL list, a raw knowledge-graph view, or chunk-level detail. The customer sees what the teammate **knows**, in the teammate's voice. If a document was uploaded, its content appears as *"I read your product catalog — here's what I understood."*

**Zone C — Their body of work.**
Preview of pieces this teammate has made. Tapping opens the piece in the Library context.

### 8.4 Primary action on teammate detail

**[Make something with them]** — opens Studio pre-scoped. Visually dominant.

Secondary: adjust presence, adjust knowledge, view body of work, **[Retire this teammate]** (quiet, at bottom — archives but preserves body of work).

### 8.5 Adding a teammate

Triggered by reveal or via the [Add another teammate] affordance.

A short conversation, mirroring onboarding:
1. *"Who are they representing?"* — *"Our Spanish-speaking customers."* *"The commercial side of the business."*
2. *"What should they sound like?"*
3. *"Anything they should know that Alex doesn't?"*

Then a face is generated (customer accepts, adjusts, or replaces), a voice is chosen (with samples), and the teammate is created. Customer can jump straight into Studio with them.

### 8.6 Realtime avatar — introduced here

Realtime is a **teammate capability**, not a top-level surface. Once revealed (§9), each teammate has a *"Start a conversation with \<name\>"* affordance in their detail view.

A live-conversation session is a full-screen mode with the teammate's live video, cost ticker if applicable, and end-session control. Transcripts from conversations appear in the teammate's body of work (Zone C).

---

## 9. The Capability Reveal System

The reveal system is what makes the operating system emerge over time. Every reveal has a trigger, a teammate phrasing, and a surface change.

### 9.1 Trigger types (in order of precedence)

1. **Ask-triggered** — the customer expresses need. Fires immediately when flow allows (see §9.4). **Strongest.**
2. **Usage-triggered** — the customer has done something that earns the reveal. Fires at the completion of that action.
3. **Time-triggered** — the customer has been engaged long enough. Fires on their next session after the threshold, at a completion moment.

### 9.2 The full reveal table (v1)

| Capability | Trigger | Phrasing | Surface change |
|---|---|---|---|
| Library appears in nav | Usage: first publish | Silent — nav item draws in once. | Library nav item appears. |
| Follow-up / variant | Usage: after first publish | *"Want me to write a follow-up in a different tone?"* | Studio reopens in variant mode. |
| Second teammate | Usage: 3rd publish | *"You might want a second face for a different audience. Want to add one?"* | Add-teammate conversation. |
| Second teammate (ask) | Ask: *"I wish I had another voice / face / person"* | *"Absolutely. Let's set them up."* | Add-teammate conversation. |
| My Team nav | Usage: adding second teammate | Silent — nav item draws in once. | My Team nav item appears. |
| Series | Time: Day 7 + 3 publishes | *"You've been posting regularly. Want to plan a short series that goes out together?"* | Series creation opens. |
| Series (ask) | Ask: *"I want these to go out on a schedule / together"* | *"Let's build that series."* | Series creation opens. |
| Repurpose / remix | Usage: 5+ publishes | *"Want me to remix your best-performing post into something new?"* | Studio in remix mode. |
| Direct-to-platform | Usage: 3+ publishes OR Ask | *"I can send this straight to Instagram for you. Want to connect it once?"* | Publish destination modal expands; OAuth. |
| Language / dubbing | Ask: *"I want this in Spanish / another language"* | *"I can do that. Which language?"* | Studio → variant with target language. |
| Live conversation | Time: Day 14 + 10 publishes | *"I can also talk live with your customers. Want to see how?"* | Realtime setup opens in current teammate's context. |
| Live conversation (ask) | Ask: *"Can this talk to my customers live?"* | *"Yes — let me set that up."* | Realtime setup opens. |
| Batch mode | Usage: 20+ pieces in Library OR Ask | *"Let's do that. What varies?"* | Studio in batch mode / Library in batch-select. |
| Best performing | Time: 14 days after 5+ publishes | *"I can show you what's performing best. Want to see?"* | "Best performing" filter chip in Library. |
| Knowledge editing | Ask: *"The AI got a fact wrong"* / *"I want to update what it knows"* | *"Let's fix that. What should it know?"* | My Team → teammate's knowledge editing. |
| Archive concept | Usage: 30+ pieces | *"Some of these are getting old. Want to tidy your library?"* | Archive action reveals; archived section becomes accessible. |

### 9.3 The intent-mapping layer (implementation-facing)

Ask-triggered reveals require the teammate to recognize customer phrasing as intent. Design constraints:

- **False-positive is worse than false-negative.** Revealing when the customer didn't intend feels invasive. Missing a reveal is recoverable — the customer will express again.
- **Confirmation before commitment.** Ask-triggered reveals always land as an **offer**, not an automatic action. *"Want me to..."* not *"I've set up..."*
- **One reveal at a time.** If a message could trigger two reveals, pick the one closest to the literal ask.

### 9.4 Reveal timing — reveals respect flow

**No reveals in Studio during active creation.** Ever.

Post-completion reveals only. Home after a publish, Library after opening a piece, My Team after adding a teammate — these are the reveal windows.

**Ask-triggered during active work:** acknowledged in narration, deferred to next completion moment. Example — customer in Studio: *"Can this go out on a schedule?"* Teammate: *"Yes, I can help with that. Let's finish this one first, then set it up when we're done."* After publish, the celebration state includes: *"Ready to set up that series?"* The reveal fires at completion, not interruption.

**The customer's flow is louder than the product's ambition.** If the customer is making something, that's the whole app until they're done.

### 9.5 Reveals must feel inevitable

- No *"New!"* badges on newly-revealed features.
- No *"You unlocked X"* celebration copy.
- No changelog surfaced to the customer.
- Reveals appear as natural offers in teammate voice, or as silent nav additions (subtle one-time draw-the-eye animation only — no modal).
- Post-hoc, the customer can't easily distinguish *"was this always here?"* from *"did this just appear?"* — and that's the goal.

**Test:** if a customer describes a reveal as *"the feature that appeared,"* we failed. If they describe it as *"the thing my teammate suggested,"* we succeeded.

---

## 10. Resolving the Five Open Questions from the Brief

**Q1: The onboarding conversation.** Three core questions (business / audience / today's need), optional fourth if urgency is mentioned. Ends with direct transition to Studio. See §3. Uncertain answers to Q3 handled via §3.6.

**Q2: The teammate's identity on Day 1.** Pre-provisioned. Default name *"Alex"* (genderless, warm, universal). Neutral face and voice. Customer can rename / reface / revoice immediately, but is not asked to before their first Studio session.

**Q3: Publish destinations.** Day 1: Download + shareable link. Direct-to-platform (Instagram, TikTok, LinkedIn, YouTube) reveals through usage or ask. OAuth happens in-flow, once, when the customer opts in.

**Q4: My Team unification.** Knowledge folds fully into individual teammate detail (Zone B). No global "About my business" surface. Onboarding seeds the first teammate's knowledge. When a second teammate is added, they inherit shared knowledge and can specialize.

**Q5: The operator surface.** No hidden advanced mode. The advanced operator is a My Team + Library power user at the far end of the reveal curve — same product, same nav, farther along. Philosophical commitment; violations require an explicit exception in a future decision doc.

---

## 11. The Ten Information Architecture Principles

- **IA-1: Three nouns, no more.** Home, Library, My Team — plus contextual Studio. If a feature can't be placed inside one, question whether the customer needs it.
- **IA-2: State, not screens.** Drafts, published, in-progress, archived are states of the same object. Never a separate list.
- **IA-3: The teammate is present on every surface.** Ambient greeting, warm narration, easy escape hatch — but see IA-7.
- **IA-4: No internal vocabulary leaks.** `Composition, asset, bundle, recipe, primitive, spokesperson corpus, engine bridge, tool invocation, tier, workspace` — none of these appear in the customer UI. See §1.4.
- **IA-5: Progressive disclosure has triggers, not toggles.** Capability reveals happen because the customer did something, not because they flipped an "advanced mode" switch.
- **IA-6: Errors speak human.** No *"Request failed (409)."* No stack traces. Every error state has: what went wrong (one sentence), what the customer can do about it, and — where possible — a one-tap resolution.
- **IA-7: The teammate is a coworker, not a receptionist.** Every obvious action is tappable directly. The teammate narrates, explains, and offers — but never stands between the customer and what they came to do.
- **IA-8: Reveals respect flow.** Reveals fire between actions, never during them. Ask-triggered during active work is acknowledged in narration and deferred to the next completion moment. See §9.4.
- **IA-9: The teammate remembers; the customer never configures memory.** Pattern memory accrues silently. Correction and forgetting happen in natural conversation, never in a settings screen. See §4.5.
- **IA-10: Reveals feel inevitable, never announced.** If a customer describes a reveal as *"the feature that appeared,"* we failed. If they describe it as *"the thing my teammate suggested,"* we succeeded. See §9.5.

---

## 12. Naming Decisions

### 12.1 Locked for v1

- **Teammate** (customer-facing, singular and generic).
- **My Team** (nav label — working; see 12.2).
- **Library** (nav label).
- **Home** (nav label).
- **Series** (customer-facing noun; replaces "campaign").
- **Live call** (customer-facing noun for realtime session; replaces "realtime session" / "realtime avatar").

### 12.2 Still placeholder

- **My Team** — no measurably clearer alternative surfaced during IA drafting. Held; may iterate during screen design.
- **Studio** — the customer may never see this word. If primary action language is *"Continue your video"* / *"Start something new,"* the customer enters Studio without being told they're in Studio. Recommend: use *"Studio"* internally for IA/design reference; leave open whether it appears in customer UI at all.
- **"Alex" (default teammate name)** — English-market default. Localization is a separate track.
- **The deliverable's generic noun** — no persistent noun in customer UI. Contextual only. Internal shorthand: *"a piece."*

### 12.3 Killed with prejudice

Composition, asset, bundle, recipe, primitive, spokesperson (→ teammate), spokesperson corpus, engine bridge, tool invocation, tier, workspace, script (as noun), transcript (as noun), knowledge document (as noun), campaign (→ series), realtime session (→ live conversation), avatar (→ teammate / face).

---

## 13. What This Doc Deliberately Does Not Cover

- Individual screen layouts, wireframes, or component design — that's the next phase.
- Visual system and typography — separate track.
- Motion / animation rules — separate track (referenced but not specified here).
- Empty-state copy — ships with screen design.
- Loading state design — largely obviated by process transparency; details ship with screens.
- Accessibility spec — distinct pass, after screen designs stabilize.
- Payment / upgrade flow — reveals for paid capabilities exist in §9; the actual pricing surface is a distinct track.
- Error copy library — produced alongside screen design under IA-6.
- Tier-limit surfacing in copy — falls under the pricing/upgrade track. Working principle: tier limits surface as teammate voice (*"I can only make one more video for you today. Want me to save the rest for tomorrow, or want to lift your limit?"*), never as a modal titled "Upgrade."

---

## 14. Ready-to-review checklist

Before proceeding to screen design, this IA needs a nod on:

- [ ] The four-surface model (Home / Studio / Library / My Team) is the right shape.
- [ ] The onboarding conversation is the right length and voice — including the uncertainty handling in §3.6.
- [ ] The Day-1 primary flow (sign-up → 3 questions → Studio → publish → celebration in Home) is the right customer journey.
- [ ] The reveal table (§9.2) is complete and correctly ordered.
- [ ] The publish destination decision (Day-1 = download + link, direct-to-platform via reveal) is correct.
- [ ] The pre-provisioned teammate name ("Alex") is acceptable as a default.
- [ ] Locked naming (§12.1) is acceptable.
- [ ] The "no advanced mode ever" commitment (§10, Q5) is acceptable.
- [ ] The ten IA principles (§11) are load-bearing beliefs the team commits to defending.

Once these are nodded, the next artifact is screen design — starting with **Home** (per operator's requested sequence: Home → Onboarding → Studio → Library → My Team → Piece Detail → Live Conversation).

*(Historical note: all seven screens above shipped as canonical during the same design session. See `docs/design/screens/` and `docs/handoffs/SESSION_237_PRODUCT_REDESIGN_INTERACTION_COMPLETE.md` for the current state.)*

---

## Revision History

**v1 — 2026-08-06.** Initial version. Written during an intensive product design session between the operator (Chris D) and the Head of Product Design LLM, alongside the companion [Product Design Brief](PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md). Major structural decisions incorporated:

- Four-surface model established (Home / Studio / Library / My Team) collapsing 37 audited screens into three top-level nouns plus one contextual full-screen surface.
- **Object model:** three customer-facing objects (a piece of work, a teammate, a series); 15 internal object types killed from the customer UI.
- **Day-1 navigation contains one item (Home)**; other surfaces appear via reveal.
- **Onboarding:** three questions, no wizard, direct transition to Studio; §3.6 handles Q3 uncertainty as a marquee moment.
- **Home:** three-zone structure (greeting / action set / featured piece); action-first; one obvious primary action per state; pattern memory personalizes the greeting.
- **Studio:** full-screen three-zone; process-transparency narration; always-interruptible; invisible collaboration-style spectrum (autonomous / collaborative / guided).
- **Publish flow:** seven-step axis moment from Studio-ready → celebration on Home → Library placement; Day-1 destinations are download + shareable link.
- **Library:** three progressive display modes (small / growing / established); primary action is opening a piece; direct [Remix this] on published detail.
- **My Team:** teammate detail as a work surface with three zones (presence / what they know / body of work); realtime avatar introduced as a teammate capability, not a top-level surface.
- **Reveal system:** three trigger types (ask / usage / time) with ask-triggered winning precedence; §9.4 protects flow (never interrupt Studio); §9.5 enforces the "feels inevitable" test.
- **Ten IA principles** locked (expanded from the six in the pre-IA brief).
- **Naming discipline:** locked / placeholder / killed lists in §12.
- **Philosophy #6 folded in (post-Library design):** *"The customer's work is displayed as pride, not inventory."* Referenced in §7. Applies across Home Zone C, Library, My Team's body of work, and Studio's preview.
