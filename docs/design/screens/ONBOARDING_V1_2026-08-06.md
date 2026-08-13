---
title: "Character OS — Onboarding Screen Design"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md", "../PRODUCT_IA_V1_2026-08-06.md", "HOME_V1_2026-08-06.md"]
---

# Onboarding — Screen Design

## v1 — canonical screen design under PRODUCT_IA_V1

*Anchored in [`PRODUCT_IA_V1_2026-08-06.md`](../PRODUCT_IA_V1_2026-08-06.md) §3. The flow that delivers the customer from sign-up to Home in State 1 (celebration). Not a wizard. Not a form. A short, warm conversation with a durable state model behind it.*

*Sibling to [`HOME_V1_2026-08-06.md`](HOME_V1_2026-08-06.md). No wireframes.*

---

## 1. Purpose recap

Onboarding takes the customer from zero to a first Studio session with the least friction possible. Three questions. No progress indicator. No account settings. The customer meets Alex, not a form.

The exit criterion is a **framed piece of work materializing in Studio** — never an *"Onboarding complete!"* modal.

---

## 2. Screen anatomy

Onboarding is a **single full-screen surface** that changes contents as the conversation progresses. It has no header, no footer, no nav, no logo, no progress bar, no skip, no back button.

Three primary elements, vertically centered:

- **Face** — Alex, ~120px on desktop, ~80px on mobile. Top of the visible column.
- **Question** — the largest text on screen, centered, one sentence.
- **Input** — a single-line text field, generously sized, centered. Below the question.

Two peripheral affordances:

- **[Leave for now]** — visually quiet escape affordance, small, in the top-right corner (subject to visual-system pass).
- **[Change that]** — appears briefly beneath each acknowledgment, disappears once the next answer is submitted.

Nothing else. The customer's attention is single-file.

---

## 3. Flow specification

Onboarding has one canonical path and one branch for genuine uncertainty. Both end in Studio.

### 3.1 Canonical path

```
[Sign-up]
    ↓
Pre-provision Alex silently
    ↓
Q1  "Hi. I'm Alex. What kind of business are you running?"
    ↓  (customer answers, e.g. "A neighborhood bakery")
Alex acknowledges  "Got it — a bakery."
    ↓
Q2  "Who are you making this for?"
    ↓  (customer answers)
Alex acknowledges  "Got it — local customers looking for good sourdough."
    ↓
Q3  "One more. What do you want to make today?"
    ↓  (route by answer type — see §3.2)
Alex acknowledges  "Alright — let me get started. Here's what I'm thinking."
    ↓
[Optional Q4, only if a specific missing detail could materially change the work — see §3.3]
    ↓
[Transition to Studio, face persists]
```

### 3.2 Q3 has three paths

The Q3 answer is routed by the detection layer into one of three paths.

**Path A — Specific deliverable named.**
The customer named a piece of content or format. Examples: *"A video announcing our new summer menu,"* *"A reel for Instagram,"* *"A welcome message for new customers,"* *"An email about our sale."*

Alex acknowledges and transitions directly to Studio.

**Path B — Clear business goal, no specific deliverable.**
The customer named an outcome or need without specifying a piece. Examples: *"I need more customers,"* *"I want to launch our new product,"* *"I want to explain our tune-up service."*

Alex proposes a direction with one confirmation question. Example:

- Customer: *"I need more customers."*
- Alex: *"Let's work toward that. I'd start with a short video giving people one clear reason to visit this week. Sound good?"*
- Customer confirms → Studio.
- Customer rejects → Alex offers a second proposal.
- Customer rejects second proposal → fall to Path C with modified opening (see §3.4).

**Path C — Genuine uncertainty.**
The customer signaled no direction. Examples: *"I don't know,"* *"help me figure it out,"* *"you tell me,"* empty or single-word answers with no usable signal.

Alex enters the bounded warmup (see §3.4).

**Detection layer** (design-level requirement):
- **Bias toward Path A when the customer supplied usable direction.** *"Something for summer"* is Path A: Alex should confidently propose *"Let's make a short summer promotion. I'll start broad, and you can steer me once you see it."* rather than ask more questions.
- **Bias toward Path B when a real goal is present but no piece is named.** Not warmup — a proposal.
- **Bias toward Path C only when signal is genuinely absent.**
- Studio is designed to support interpretation and steering. Onboarding should not try to produce a perfect brief.

Engineering will tune the specific detection rules; the design requires that the three paths be distinguishable and that the middle path exists.

### 3.3 Optional Q4 — contextual, conditional

Q4 only appears when the Q3 answer references time, event, or specific context AND a **specific missing detail could materially change the work**: an event name, an offer, a deadline, a location, or a required call to action.

Otherwise, urgency is passed silently into Studio as brief context (Studio adapts pacing and format).

Q4 copy **always explains why the question appeared**:

- *"You mentioned tomorrow. Is there an event or deadline I should know about?"*
- *"You mentioned the weekend. Is there an offer or event happening?"*
- *"You mentioned your grand opening. Is there a date, time, or offer I should include?"*

Q4 accepts empty submission (soft skip via Enter on blank input). Alex acknowledges briefly regardless.

### 3.4 Warmup exchange (Path C)

Warmup is bounded. Alex may ask **at most three** questions before making a concrete proposal. The teammate leads.

```
Alex  "No problem. Let's figure it out together."
    ↓
Layout adapts to conversation mode (see §4.5)
    ↓
Alex Q1  (e.g. "Tell me one thing that's on your mind for your business right now.")
    ↓
[Customer answers]
    ↓
Alex Q2  (e.g. "Are you thinking about right now, or a specific time of year?")
    ↓
[Customer answers]
    ↓
Alex Q3  (optional, only if still unclear)
    ↓
[Customer answers]
    ↓
Alex must now propose:
    "Alright — I have an idea. Let's make [X]. Sound good?"
```

**Rejection handling:**
- If the customer rejects the first proposal, Alex offers a second.
- If the customer rejects the second proposal, Alex asks: *"Tell me what you definitely do not want, and I'll take another direction."*
- Alex must not chain more than three unsuccessful proposals. If the third proposal is rejected, Alex offers to save progress and try later: *"Let's give it fresh eyes tomorrow. I'll save what we've talked about."*

---

## 4. Element specification

### 4.1 Alex — the face

- Position: top-centered, ~120px desktop / ~80px mobile / ~56–64px on mobile when keyboard is open.
- Idle expression: warm, calm, slight friendliness. Occasional blink, subtle breath.
- Between questions: brief expression shift is nice-to-have but not required for v1 — static portrait with subtle life is acceptable.
- The face **never moves position** during onboarding (except the mobile-keyboard resize case). Stability grounds the experience.

### 4.2 The question

- Centered, one sentence, body-large or display-small weight (final size TBD by visual system track). Should feel spoken, not headline-y.
- Appears below the face with generous vertical spacing.
- Between questions, the previous question is replaced by a brief **acknowledgment** (*"Got it — a bakery."*), which is then replaced by the next question.
- The acknowledgment is smaller than the question — signals *"integration"* rather than *"new prompt."*
- **Mobile with keyboard open: the current question is always fully visible.** Never truncated. Prior log entries in conversation mode may collapse or scroll off to preserve question visibility.

### 4.3 The input

- Single-line text field. Generous height (~56px min on desktop). Full-width up to a max of ~640px, centered.
- No visible placeholder after typing starts.
- No pre-filled example text.
- **Submit affordance [→]** appears at the right edge of the input as soon as any non-whitespace character is typed. Both desktop and mobile.
- **Enter submits.** Same on desktop and mobile.
- **No character-count threshold.** Valid businesses and answers can be short (*"DJ,"* *"bar,"* *"moms,"* *"reel"*). The input accepts anything non-whitespace.
- No visible label — the question above IS the label.
- Focus lands on the input automatically when a new question appears (Onboarding is an active input surface).

Low-information or ambiguous answers are handled by the routing logic (§3.2), not by validation gates.

### 4.4 [Change that] — the correction affordance

After each acknowledgment (Q1, Q2, Q3, warmup exchanges, Q4), a small **[Change that]** text link appears briefly beneath the acknowledgment.

- Visible: from the moment the acknowledgment renders until the next answer is submitted.
- Disappears: as soon as the customer submits their answer to the current question.
- Tap behavior: the acknowledgment fades out; the previous question returns to the question position; the customer's prior answer populates the input for editing; the input reactivates with focus.
- **Bounded scope:** only the immediately previous answer is correctable. The affordance never allows navigating further back than one turn.

This preserves conversational truth without turning onboarding into a form.

### 4.5 Conversation mode (Path C warmup)

When Q3 routes to Path C, the layout adapts:

- The face stays in the same top-centered position.
- Below the face, prior exchanges become visible as a short vertical log — Alex's messages on the left, the customer's answers indented to the right. Small, quiet type. Feels like a note being taken together, not a chat window.
- The current turn (Alex's next question or proposal) is the largest text on screen, styled the same as canonical-path Q1/Q2/Q3.
- The input remains below.
- No timestamps. No avatars on log entries. No message bubbles. Quiet conversation view — not a chat interface.
- Log clears on transition to Studio.
- **On mobile with keyboard open**, log entries collapse to preserve the current question and input visibility (§4.2, §8).

### 4.6 [Leave for now] — the escape affordance

- Small, visually quiet text-only affordance in the top-right corner of the surface (or top-left; final placement subject to visual-system pass).
- Present on every Onboarding screen — Q1, Q2, Q3, warmup, Q4.
- Tap or Escape key opens the escape sheet (§4.7).

### 4.7 The escape sheet

Triggered by [Leave for now] tap or Escape keypress.

- **Mobile:** slides up from the bottom, takes ~30% of viewport.
- **Desktop:** anchored side sheet or compact panel, connected visually to the Onboarding surface.
- **Never a centered modal** unless accessibility or viewport constraints force it.

Contents:
- Heading: *"Leave for now? Your answers are saved."*
- Primary action (quiet): **[Keep going]** — closes the sheet, returns focus to the input.
- Secondary action: **[Leave for now]** — persists state and returns the customer to sign-in (or a neutral account state; see §10).

---

## 5. All states enumerated

### State 1 — Arrival (post-sign-up)
- Face fades in from center over ~400ms.
- Q1 fades in over ~600ms, delayed to start after face is ~50% visible.
- Input fades in over ~800ms, delayed to start after Q1 is visible.
- [Leave for now] fades in with the input.
- Focus lands on the input as it becomes interactive.
- Total to interactive: ~1s.

### State 2 — Q1 active
- Face + Q1 + input + [Leave for now] visible.
- Customer typing: subtle border color shift on the input to indicate active editing.
- [→] appears as soon as any non-whitespace character is entered.
- Submit: input transitions to *"confirmed"* state (softer color, small checkmark) for ~200ms.

### State 3 — Q1 → Q2 transition (with [Change that] window)
- Q1's text cross-fades to the acknowledgment (*"Got it — a bakery."*) over ~300ms.
- Input clears.
- **[Change that] appears** below the acknowledgment.
- Acknowledgment holds for ~500ms.
- Acknowledgment fades out; Q2's question fades in over ~400ms.
- **[Change that] persists** until Q2's answer is submitted.
- Input reactivates; focus returns.

### State 4 — Q2 active / Q2 → Q3 transition
- Same pattern as States 2 and 3.

### State 5 — Q3 active, Path A (specific deliverable)
- Customer answers with a specific deliverable.
- Alex acknowledges: *"Alright — let me get started. Here's what I'm thinking."*
- Transition to Studio (State 12).

### State 6 — Q3 active, Path B (business goal, no deliverable)
- Customer answers with a goal but no specific piece.
- Alex acknowledges the goal and proposes:
  - *"Let's work toward more customers. I'd start with a short video giving people one clear reason to visit this week. Sound good?"*
- Below the proposal, two quick-reply affordances: **[Sounds good]** / **[Something else]**. The input remains available for free-text response.
- **[Sounds good]** or *"yes"* / *"ok"* / equivalent → transition to Studio (State 12).
- **[Something else]** or a corrective response → State 7.

### State 7 — Path B second proposal
- Alex acknowledges the rejection: *"Ok — let me try again."*
- Alex offers a second proposal in the same shape.
- **[Sounds good]** → Studio.
- Rejection → Fall to Path C warmup opening (State 8) with the modified prompt: *"Tell me what you definitely do not want, and I'll take another direction."*

### State 8 — Q3 active, Path C (genuine uncertainty), or fallback from Path B
- Alex says: *"No problem. Let's figure it out together."* (Path C direct) OR *"Tell me what you definitely do not want, and I'll take another direction."* (Path B fallback).
- Layout adapts to conversation mode (§4.5).
- Alex asks the first warmup question.

### State 9 — Warmup exchange (bounded)
- Alex asks up to three questions before making a proposal.
- Each customer answer visible in the log.
- The current Alex question is the largest text on screen.
- [Change that] appears after each Alex question is answered; disappears once the next Alex turn begins.

### State 10 — Warmup proposal
- After at most 3 questions, Alex must propose.
- Proposal appears in the question position with the same [Sounds good] / [Something else] affordances.
- Rejection → second proposal.
- Second rejection → third proposal with the *"tell me what you don't want"* framing.
- Third rejection → Alex offers to save progress and try later: *"Let's give it fresh eyes tomorrow. I'll save what we've talked about."* Two actions: **[Yes, save for later]** (persists state, redirects as [Leave for now]) / **[Try once more]** (returns to State 10 with a fresh proposal attempt).

### State 11 — Q4 active (conditional, contextual)
- Inserted after Q3 acknowledgment when the detection layer identifies a specific missing detail.
- Question explains why it appeared (§3.3).
- Empty submission accepted as skip.
- Acknowledgment brief regardless of answer.

### State 12 — Studio transition
- Alex acknowledgment fades in for the last time in Onboarding.
- Full-screen wipe to Studio over ~500ms.
- Face persists across the wipe — position translates from Onboarding's top-centered to Studio's Zone L.
- In Studio, Alex's first narration line begins as soon as the wipe completes.
- Onboarding surface is fully replaced; local draft state is finalized and cleared.

### State 13 — Escape sheet open
- Triggered by [Leave for now] tap or Escape key.
- Sheet slides in.
- Underlying Onboarding content is dimmed (~50%) but visible.
- Focus moves to the sheet's primary action **[Keep going]**.
- Dismissing (tap outside on desktop, drag-down on mobile, Escape a second time) returns to the previous Onboarding state with focus restored to the input.

### State 14 — [Change that] engaged
- Customer taps [Change that] after an acknowledgment.
- Acknowledgment fades out (~200ms).
- Previous question reappears in the question position (~300ms).
- Prior answer populates the input; input is focused with cursor at end of text.
- On submit, flow continues to the next question normally.

### State 15 — Interpreting (short delay while Alex processes)
- If Alex's response takes longer than ~600ms to render (e.g., routing Q3 or generating a proposal), a subtle **narration line** appears in the question position: *"Thinking about that…"*
- Customer's input remains populated with their prior answer.
- The interpretation line is not a spinner — it's Alex speaking. Fades in and out with the same rhythm as any other question.

### State 16 — Extended interpretation (longer delay)
- If interpretation continues beyond ~5 seconds (design-level threshold; engineering to tune), the narration escalates: *"I'm still working on that. You can try again, or keep waiting."*
- Two quiet actions appear: **[Keep waiting]** (dismisses the escalation, continues waiting) / **[Try again]** (re-submits the same answer to the backend).
- **The customer's answer is preserved throughout.** Input does not clear. The customer is never asked to retype.

### State 17 — Definitive failure (backend confirmed unreachable)
- Only reached when the backend has confirmed a failure (not a timeout).
- Question position: *"I'm having trouble connecting right now. Give me a moment."*
- Single action: **[Try again]**.
- All customer answers preserved locally; retry resumes at the current question with input still populated.

### State 18 — Recovery from prior session
- Customer signs in with an incomplete onboarding session in draft state.
- Onboarding opens at the last completed question — not from the beginning.
- Alex greets the customer warmly on the current question: *"Welcome back. We were figuring out what to make today."* Then the last question reappears with prior answers already integrated into Alex's tone.
- If the customer left in the middle of a question (typed but did not submit), the input is populated with the unsent text.

### State 19 — Nonsense or accidental input
- Detection layer identifies input as random or accidental (*"asdf,"* keyboard mashing, all-punctuation, etc.).
- Alex re-asks the same question with a soft prompt: *"I didn't quite catch that. What kind of business are you running?"*
- No penalty, no error state, no stored abusive interpretation.
- Alex may re-ask twice at most; on the third failed answer, Alex opens a support prompt: *"If you're having trouble, want to leave this for now and come back?"*

### State 20 — Abusive input
- Detection layer identifies input as abusive (profanity directed at Alex, slurs, obvious trolling).
- Alex redirects without engaging: *"I'm here to help you build something for your business. What kind of business are you running?"*
- The abusive input is **not** stored, not paraphrased, not surfaced in acknowledgment.
- Alex may redirect twice; on the third abusive input, the escape sheet opens automatically with the message: *"Let's try again another time."*
- False positives on abuse detection are acceptable (over-tolerance is bad); false negatives (abuse getting stored) are unacceptable.

---

## 6. Copy library

### 6.1 Questions

- **Q1:** *"Hi. I'm Alex. What kind of business are you running?"*
- **Q2 (with context integration):** *"Who are you making this for?"*
- **Q3:** *"One more. What do you want to make today?"*
- **Q4 (conditional, contextual — see §3.3):** *"You mentioned [context]. Is there [specific missing detail — event / offer / deadline / location / CTA] I should know about?"*

**Copy rules for questions:**
- Q1 introduces Alex by name — the only formal introduction.
- Q2 uses conversational transition (context absorbed into Alex's tone, not restated).
- Q3 uses *"One more"* as the only progress signal.
- Q4 explains why it appeared; never generic.

### 6.2 Acknowledgments (canonical path)

**Rule of restraint:** Acknowledgments confirm understanding without rewriting meaning unless confidence is high. Never invent specifics the customer did not supply.

**After Q1 — echoes the business type in shortest natural form:**
- *"Got it — a bakery."*
- *"Got it — an HVAC company."*
- *"Got it — a solo bookkeeping practice."*

**After Q2 — matches Alex's confidence to what the customer actually said:**

*High-confidence echo (customer named specifics that are clear):*
- *"Got it — homeowners in Denver needing furnace tune-ups."*

*Softened general echo (customer named a general audience):*
- *"Got it — local customers looking for good sourdough."* (rather than inventing *"West Loop"* if the customer only said *"local"*)

*Low-confidence hold (Alex is unsure how to summarize):*
- *"Got it. I'll keep that audience in mind."*

**After Q3, Path A (specific deliverable):**
- *"Alright — let me get started. Here's what I'm thinking."*

**After Q3, Path B (business goal, no deliverable) — Alex proposes:**
- *"Let's work toward more customers. I'd start with a short video giving people one clear reason to visit this week. Sound good?"*
- *"Ok — for launching a new product, I'd start with a short teaser. Sound good?"*

**After Q4 (answered):**
- *"Noted."*
- *"Got it — I'll weave that in."*

**After Q4 (skipped via empty submission):**
- *"Ok — let's get to it."*

**Copy rules for acknowledgments:**
- Always short — 3–8 words for canonical acknowledgments; proposals can be one sentence.
- Never repeat the exact question or restate the answer verbatim beyond the key noun.
- Never end with a comma or continuation ellipsis — feel complete.
- Never contain hedges unless describing genuine uncertainty (*"I'll keep that in mind"*).
- **Do not paraphrase into specifics the customer did not provide.**

### 6.3 Warmup exchange (Path C)

**Trigger:** *"No problem. Let's figure it out together."*
**Trigger (fallback from Path B rejections):** *"Tell me what you definitely do not want, and I'll take another direction."*

**Warmup question templates** (examples; the design ceiling is three Alex questions total per warmup):

| Alex asks | Purpose |
|---|---|
| *"Tell me one thing that's on your mind for your business right now."* | Surface a real concern, not a content type. |
| *"Are you thinking about right now, or a specific time of year?"* | Narrow the temporal frame. |
| *"Who are you hoping to reach with this?"* | Reuse Q2's answer or refine. |
| *"What would success look like — more people through the door, more repeat customers, awareness?"* | Frame the goal without jargon. |
| *"What do you usually tell people about your business?"* | Surface authentic voice. |

**Warmup proposal:**
- *"Alright — I have an idea. Let's make [specific piece]. Sound good?"*

**Rejection handling copy:**
- After first rejection: *"Ok — let me try again."*
- After second rejection: *"Tell me what you definitely do not want, and I'll take another direction."*
- After third rejection: *"Let's give it fresh eyes tomorrow. I'll save what we've talked about."*

### 6.4 Error and delay copy

- **Between-question delay (300ms+):** *"Thinking about that…"*
- **Longer interpretation delay (5s+):** *"I'm still working on that. You can try again, or keep waiting."*
- **Backend definitively unreachable:** *"I'm having trouble connecting right now. Give me a moment."* + **[Try again]**
- **Nonsense/accidental input:** *"I didn't quite catch that. What kind of business are you running?"* (re-asks the current question)
- **Abusive input:** *"I'm here to help you build something for your business. What kind of business are you running?"*
- **Escape sheet:** *"Leave for now? Your answers are saved."* + **[Keep going]** / **[Leave for now]**
- **Recovery greeting (returning to incomplete onboarding):** *"Welcome back. We were figuring out what to make today."* (adjusted for the specific question being resumed)

**Never used:** any HTTP code, *"validation error,"* *"required field,"* *"Failed,"* *"Error,"* *"brain"* (anthropomorphized infrastructure), or any language that suggests the customer did something wrong.

### 6.5 Quick-reply affordance copy (Path B / warmup proposals)

- **[Sounds good]** — primary quick-reply.
- **[Something else]** — secondary quick-reply.

Both appear as small buttons beneath the proposal. The input remains available for free-text response — the customer can type instead of tapping.

---

## 7. Motion & interaction notes

### 7.1 Arrival (State 1)

- Face fades in from center over ~400ms.
- Q1 fades in over ~600ms, delayed to start after face is ~50% visible.
- Input fades in over ~800ms.
- [Leave for now] fades in with the input.
- Focus lands on the input as it becomes interactive.
- Total to interactive: ~1s.

### 7.2 Between-question transitions

- **Submit:** input transforms to confirmed state (200ms).
- **Question → Acknowledgment:** cross-fade over 300ms.
- **[Change that] appears** at the start of the acknowledgment hold.
- **Acknowledgment hold:** 500ms.
- **Acknowledgment → Next question:** cross-fade over 400ms.
- **Input reactivation and focus:** immediate at start of new question's fade-in.
- **[Change that] persists** through the acknowledgment hold and the transition; disappears when the new answer is submitted.
- Total: ~1.2s per transition.

### 7.3 Q3 → Studio transition (Path A)

- Q3 acknowledgment fades in (300ms).
- Holds for 500ms.
- Full-screen wipe to Studio over ~500ms. Face position translates smoothly from Onboarding's top-centered to Studio's Zone L position.
- In Studio, Alex's first narration line begins as the wipe completes.

### 7.4 Q3 → Path B proposal

- Q3 acknowledgment fades in with the proposal in one continuous phrase.
- [Sounds good] / [Something else] fade in beneath the proposal over 300ms.
- Input remains available.

### 7.5 Q3 → Path C (warmup) transition

- Acknowledgment (*"No problem. Let's figure it out together."*) fades in over 300ms, holds ~700ms.
- Layout adapts to conversation mode: the log region fades in below the face over 400ms.
- First warmup question replaces the acknowledgment in the question position.
- Input reactivates.

### 7.6 [Change that] engaged

- Acknowledgment fades out (~200ms).
- Previous question fades back in (~300ms).
- Prior answer populates the input (instant); focus lands with cursor at end.
- Submitting continues the flow normally.

### 7.7 Escape sheet

- Sheet slides in from bottom (mobile) or side (desktop) over ~300ms.
- Underlying content dims to ~50% opacity.
- Focus moves to [Keep going].
- Dismissal reverses the animation and restores focus to the input.

### 7.8 Interpreting states (15 and 16)

- Question position swaps to *"Thinking about that…"* with a soft fade (~200ms).
- On completion, cross-fades back to the next question or acknowledgment.
- If escalation to State 16 fires, the copy shift is another cross-fade; **[Keep waiting]** / **[Try again]** fade in beneath.

### 7.9 Reduced motion

- All fades and slides reduce to instant appearance/disappearance.
- Layout changes happen in the same *sequence* but without transition durations.
- The Studio wipe becomes an instant swap.
- Face-position translation to Studio is instant.

---

## 8. Responsive behavior

- **Mobile (< 640px):** face at ~80px, centered top. Question below, generous vertical breathing room. Input full-width with 24px padding on each side. Log entries in conversation mode are smaller and stack tightly.
- **Tablet (640–1024px):** face at ~100px. Question and input constrained to ~560px max width, centered. Vertical spacing generous.
- **Desktop (> 1024px):** face at ~120px. Question and input constrained to ~640px max width, centered. Vast whitespace around the column — resist filling it.

**Mobile keyboard open:**
- Face reduces to 56–64px.
- Vertical spacing compresses.
- **The current question remains fully visible at all times.** No truncation.
- Prior conversation-log entries collapse or scroll out of view above the visible column.
- Input stays above the keyboard.
- On very small phones in landscape, the face may hide entirely; the question and input remain visible. This is the only case where the face is not shown.

**Never:** two-column layouts. Never a sidebar. Never nav. The screen is deliberately empty except for the conversation and the quiet [Leave for now] escape.

---

## 9. Accessibility notes

- **Focus on load:** input receives focus as it becomes interactive. Onboarding is an active input surface — auto-focus is correct here (unlike Home).
- **Keyboard:**
  - Enter submits.
  - Escape opens the escape sheet (see §4.7). Escape is **never** silently trapped.
  - Tab moves focus among interactive elements: input → [Change that] (if visible) → [Sounds good] / [Something else] (if visible) → [Leave for now].
- **Screen reader:**
  - Initial arrival announces the face once: *"Alex, your AI teammate."*
  - Subsequent screens: the face image is decorative (`alt=""`) — not re-announced.
  - Face is not described by age, gender, ethnicity, or physical appearance in alt text at any point.
  - If face state ever communicates something functionally important (e.g., error), that state is announced via `aria-live` region — never via face alt text.
  - Questions are announced as they appear.
  - Acknowledgments are announced.
  - [Change that] is announced as *"Change your previous answer, button."*
  - [Leave for now] is announced as *"Leave onboarding for now, button."*
  - Log entries in conversation mode are announced in order.
- **`prefers-reduced-motion`:** all fades reduce to instant appearance/disappearance; sequences preserved but without delays.
- **Contrast:** question text meets AAA (7:1). Input text meets AA. Acknowledgments meet AA. Log entries meet AA. [Leave for now] meets AA even in its quiet visual treatment.
- **Language:** English only for v1. Copy layer is translation-ready.

---

## 10. Persistence & recovery

Onboarding is **stateful.** The design depends on durable draft state — recovery after tab close, connection loss, or explicit [Leave for now] must resume the customer at the correct question with prior answers intact.

### 10.1 Persistence model (design-level requirement)

- After each submitted answer, state is persisted (server-side, indexed by user account and onboarding session).
- Persisted state includes: which questions have been answered, the customer's exact submitted answers, and Alex's chosen path (A/B/C for Q3, warmup progress if applicable).
- If the customer is mid-question (typed but not submitted), local browser state may retain the unsent text; this is best-effort and not required for resumption.

### 10.2 Recovery flows

**Tab close / refresh / navigation away:**
- Customer signs back in.
- Onboarding opens at the last completed question with prior answers preserved.
- Alex greets: *"Welcome back. We were figuring out what to make today."* — adjusted to the current question's context.
- Customer proceeds normally.

**Connection loss mid-question:**
- Local state preserves the typed answer.
- On reconnect, the flow continues at the same question with the typed answer restored to the input.

**Explicit [Leave for now]:**
- Same as tab close: state persisted, customer returned to sign-in or a neutral account state (design decision — see §11 open note).
- Next sign-in resumes.

**Draft expiration:**
- Draft state expires after 7 days of inactivity (design-level; engineering can tune).
- On expiration + return, Alex greets warmly and restarts onboarding: *"It's been a while — let's start fresh."*

### 10.3 Studio transition and draft finalization

On successful Q3 (or Q4) completion and transition to Studio:
- Draft state is **finalized** into the customer's account:
  - Alex's initial knowledge is seeded from Q1 (business), Q2 (audience), and any Q4 context.
  - The Studio brief is composed from Q3's answer (Path A) or the confirmed proposal (Path B/C).
- Draft state is cleared.
- If Studio fails to open immediately (rare), the finalized state remains available for retry.

---

## 11. Design constraints & trade-offs made explicit

**Trade-off 1 — Escape hatch exists, but is deliberately quiet.**
[Leave for now] adds an exit some customers will take. But locking customers into onboarding would be worse — a trap creates resentment. The affordance is small enough that it doesn't invite exit; large enough that it doesn't feel like a trap.

**Trade-off 2 — [Change that] is bounded to the immediately previous answer.**
Full wizard-style back navigation would introduce configuration-feel. But zero-correction is untrue to how conversation works. The bounded correction preserves conversational truth without expanding scope.

**Trade-off 3 — Auto-focus on input (contrary to Home).**
Home prohibits auto-focus. Onboarding does the opposite because the customer's clear next action is typing. Justified because Onboarding is a focused input flow, not a browseable surface. Screen reader users still hear the question announced before focus lands on the empty input.

**Trade-off 4 — The face does not move (except mobile keyboard).**
Static face position is boring by animation standards. But motion during a conversation would compete with the customer's attention. Alex's expression can shift subtly; position holds.

**Trade-off 5 — Uncertainty branch is bounded to three Alex questions.**
Open-ended warmup could uncover a better direction with more turns, but the cost is a first-run experience that feels endless. The teammate must lead. If three questions plus proposals cannot produce direction, saving progress and returning later is a better outcome than more questions.

**Trade-off 6 — Path B (proposal-first) may occasionally propose something the customer didn't want.**
Better than the alternative (making them answer more questions). Studio is designed to support steering; a wrong proposal is recoverable in seconds, more questions never are.

**Trade-off 7 — Acknowledgments soften when confidence is low.**
Costs specificity in the return-user greeting later. Wins on trust: a teammate who overstates what it heard undermines the relationship immediately.

**Trade-off 8 — Q4 explains why it appears.**
Adds copy length. But an unexplained fourth question after Q3's "One more" would feel like a bait-and-switch. The explanation is the tradeoff for surfacing genuinely useful context.

**Trade-off 9 — Statefulness requires backend investment.**
Building durable draft state is more engineering work than a purely client-side flow. Justified by the customer experience: connection failures and accidental closes should not restart a first impression.

---

## 12. Deferred to later work

- **Visual system decisions** — typography scale, exact face composition, input styling, [Leave for now] visual placement.
- **Voiced questions** (audio version of Alex asking) — accessibility track.
- **Localization** — Q1–Q4 and warmup templates all need translation-ready copy.
- **Detection layer implementation** — engineering, informed by the routing rules in §3.2.
- **Face-expression system** (multi-state face for subtle emotional variation) — separate face-system track; static portrait with subtle life is v1.
- **[Leave for now] destination** — sign-in vs. neutral account state; final choice depends on the account-status surface design, not on onboarding.
- **Abuse detection thresholds** — engineering-tunable; design guarantees false-positives are preferred over false-negatives.
- **7-day draft expiration** — engineering-tunable; may adjust based on usage data.

---

## Revision History

**v1 — 2026-08-06.** First canonical version. Written and revised during the same session against operator direction. Major decisions incorporated:

- **Escape route added:** quiet [Leave for now] affordance + Escape key open a confirmation sheet. State persists; customer can resume.
- **Correction affordance added:** [Change that] appears after each acknowledgment; scoped to the immediately previous answer only.
- **Q3 routing:** three paths, not two — specific deliverable (Path A), business goal (Path B, proposal-first), genuine uncertainty (Path C, bounded warmup).
- **Warmup bounded:** max three Alex questions before Alex must propose. Third rejection offers to save and try later.
- **Q4 rewritten:** conditional (only fires when a specific missing detail could materially change the work) and always explains why it appeared.
- **Submit threshold removed:** any non-whitespace input can be submitted. Submit affordance appears on both desktop and mobile.
- **Softer paraphrasing rule:** acknowledgments confirm without inventing specifics; use *"I'll keep that in mind"* fallback when confidence is low.
- **Statefulness required:** durable draft state after every submitted answer; refresh/tab-close/connection-loss resume at the correct question.
- **Timeout copy revised:** *"Thinking about that…"* → *"I'm still working on that. You can try again, or keep waiting."* Answers are always preserved; never force retype.
- **Face accessibility:** name announced once on initial introduction; decorative alt on subsequent screens; never encode physical description in repeated alt text.
- **Escape not trapped:** Escape key opens the escape sheet, never silently ignored.
- **Mobile keyboard behavior:** current question remains fully visible; log entries collapse; face shrinks or hides on the smallest viewports.
- **Bias to Path A on borderline answers:** *"something for summer"* becomes a confident proposal, not a warmup.
- **Nonsense vs abuse distinction:** two separate response paths; abusive input never stored or paraphrased.
- **Trade-offs made explicit** across escape hatch, correction bounding, auto-focus, uncertainty ceiling, Path B risk, and paraphrase softness.
