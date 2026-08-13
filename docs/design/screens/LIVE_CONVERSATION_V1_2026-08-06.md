---
title: "Character OS — Live Conversation Screen Design"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md", "../PRODUCT_IA_V1_2026-08-06.md", "HOME_V1_2026-08-06.md", "ONBOARDING_V1_2026-08-06.md", "STUDIO_V1_2026-08-06.md", "LIBRARY_V1_2026-08-06.md", "MY_TEAM_V1_2026-08-06.md", "PIECE_DETAIL_V1_2026-08-06.md"]
---

# Live Conversation — Screen Design

## v1 — canonical screen design under PRODUCT_IA_V1

*Anchored in [`PRODUCT_IA_V1_2026-08-06.md`](../PRODUCT_IA_V1_2026-08-06.md) §8.6. Where a teammate has a real-time conversation. The realtime capability — the single largest technical differentiator in the product — expressed as an experience the customer trusts.*

**Naming note:** external documentation may occasionally reference *"Live Call"* as a legacy label, but the file (`LIVE_CONVERSATION_V1_2026-08-06.md`), this design, and the customer surface all use **Live Conversation** — or simply **conversation**. The customer starts a conversation with Alex. Conversation is warmer than call, and it accurately describes what happens.

*Sibling to `HOME_V1_2026-08-06.md`, `ONBOARDING_V1_2026-08-06.md`, `STUDIO_V1_2026-08-06.md`, `LIBRARY_V1_2026-08-06.md`, `MY_TEAM_V1_2026-08-06.md`, `PIECE_DETAIL_V1_2026-08-06.md`. This is the final foundational screen. No wireframes.*

---

## 1. Purpose recap

Live Conversation is where the customer's teammate holds a real-time exchange with the customer (or, in the deferred customer-facing variant, with the customer's own audience). The screen holds three responsibilities:

- **Before** the conversation — setup and confidence, with anxiety made small.
- **During** the conversation — the exchange itself, presented calmly, with the teammate holding the surface.
- **After** the conversation — transition to the record it becomes, with an emotional beat that reinforces the teammate was doing work.

The teammate owns the surface. The screen should never feel like a video-conferencing application pretending to have an AI inside it — it should feel like sitting down with one of the customer's teammates.

---

## 2. Two use cases

Live Conversation serves two use cases; **v1 focuses on the first**. The second is a deferred variant (§18).

### 2.1 Operator-initiated (v1)

The customer starts a conversation with their teammate — often to test how Alex sounds and behaves in a real exchange, or to explore how Alex would handle a specific question a real customer might ask.

Entry point: **[Start a conversation with Alex]** from a teammate detail in My Team (per MY_TEAM_V1 §10 — the entry-action language updates here in parallel to *conversation*).

Participants: the operator (typing or speaking) and the teammate (Alex, speaking and appearing as a live avatar).

The operator experiences the exchange as *"I'm having a conversation with Alex to see how Alex handles things."*

### 2.2 Customer-facing (deferred)

An external party (an actual customer or prospect) starts a conversation via a shared link or embedded surface. Alex handles the conversation on the business's behalf. The operator is not on the exchange.

Entry point: an external URL or embedded surface. Not built in v1.

**Design continuity is a hard requirement.** The customer-facing experience should feel like the same teammate talking to someone else — not like a different product. Every design decision in this screen should be evaluated for how well it will translate to that future public deployment. This continuity is one of the strongest ideas in the redesign; do not compromise it for v1 conveniences.

---

## 3. Before the conversation — Setup

Before the conversation begins, the customer sees a short, warm setup surface. Not a form; a moment of orientation.

### 3.1 Anatomy

- **Alex's face** — large (~240px), calm, still with subtle life.
- **Alex's name and role** — beneath the face. *"Alex · Speaks casually about the bakery to neighborhood locals."*
- **What will happen** — one short paragraph in Alex's voice:
  > *"You'll talk with me like a customer would. I'll respond the way I would to them. Take your time — we can stop whenever you want."*
- **Reassurance sentence** — one additional line, always:
  > *"There's nothing to get right. Just talk to me naturally."*
- **Microphone check** — a conversational offering, not a diagnostic label. Alex says:
  > *"Want to make sure I can hear you?"*
  Beneath: **[Test my microphone]** — small quiet affordance.
- **Optional preview** — a small quiet link: *"See what Alex knows before we start →"* — opens the teammate detail's *What Alex knows* section in an overlay; skippable.
- **Primary action:** **[Start conversation]**
- **Secondary action:** **[Not now]** — returns to teammate detail.

### 3.2 Capacity — protective, not clinical

Capacity is surfaced in language that reassures, not language that measures.

- **Default (plenty of time remaining):** *"You've got plenty of time."*
- **Approaching a limit (~5–8 minutes left, tier-relevant):** *"A little time left on your plan this month."*
- **Very close to a limit (~2 minutes):** *"About two minutes left on your plan this month."*
- **No cap at all:** capacity line omitted entirely.

**Duration expectations are not stated up front.** Copy like *"Calls usually run 5 to 10 minutes"* is removed — it introduces performance pressure. If Alex later wants to reference typical timing, that can happen naturally in-conversation (*"Most people wrap up around this point — but take your time"*).

### 3.3 Privacy note

Small and quiet, at the bottom: *"This conversation stays in your workspace."* Full policy behind an optional link.

### 3.4 Confidence grows over time

The pre-conversation surface is not static. As the operator completes successful conversations, it thins:

- **First few conversations:** the full setup surface described in §3.1.
- **After ~5 successful conversations:** the *what-will-happen* paragraph collapses to just the reassurance line.
- **After ~10 successful conversations:** setup is minimal — Alex's face, name, **[Start conversation]**. That's it.
- **Trust earns simplicity.**

The customer never chooses this progression; it happens naturally.

### 3.5 What is NOT on the setup surface

- No permissions modal ambush. Microphone permission is requested inline when [Start conversation] is tapped, and only if not already granted.
- No settings gears.
- No teammate switcher.
- No branding, no logos, no marketing copy about the feature.

---

## 4. During the conversation — Anatomy

The conversation itself is a full-screen surface. **The teammate owns the surface.** Everything else supports the teammate — smaller, quieter, secondary.

### 4.1 Layout

**Center-stage: Alex, large.**
- Desktop: the avatar occupies ~65–70% of the vertical viewport, centered.
- Mobile: the avatar takes ~50–55% of the vertical viewport, centered vertically in the top portion of the screen.
- Larger than before (compared to earlier drafts) — the teammate genuinely dominates.

**Beneath the avatar — captions area:**
- Smaller than the avatar suggests. Comfortable to read but not competing for weight.
- **Adaptive emphasis** (§4.3): current speaker's utterance dominates; prior utterances quietly fade.
- Speaker labeled subtly (*"Alex"* / *"You"*).

**Bottom edge — call chrome (smaller, quieter):**
- **Microphone control** — center. Sized to be reachable and reliable, not to demand attention.
- **Text input toggle** — left of microphone. Small.
- **End** — right of microphone. Distinct treatment (see §7).

**Top area — minimal status:**
- **Duration** — running time, small and quiet.
- **Capacity indicator** — only when approaching a limit (§8). Absent otherwise.
- No teammate name (Alex is right there).

### 4.2 State communication — silence over labels

The conversation has fewer explicit state indicators. Humans don't announce that they're thinking.

- **Alex listening:** subtle behaviors on the avatar (§6.2). No text indicator.
- **Alex speaking:** obvious from the mouth animation and audio; no text indicator.
- **Alex thinking:**
  - Short pause (<~1.5s): no indicator. Silence is expected.
  - Longer pause: Alex's expression shifts — a small thoughtful look, considered smile, slight tilt. Behavior communicates, not text.
- **Connection or processing problem:** if — and only if — something is genuinely wrong, a small quiet indicator appears (§9). Never surfaced for normal pauses.

### 4.3 Adaptive captions

Captions communicate what was said and preserve accessibility, but they are not the star. Their visual weight reflects recency.

- **Current speaker's active utterance:** full emphasis — normal reading weight, clear color.
- **Just-completed prior utterance:** slightly reduced emphasis — lighter color, slightly smaller.
- **Older conversation:** very light — subdued, receding.
- Reading naturally follows the conversation forward. The customer never feels like they're watching a messaging app.

Scrolling up preserves the ability to read older lines at full weight if the customer wants to.

### 4.4 What is NOT on the conversation surface

- No branding, no logo.
- No notification badges.
- No settings gear.
- No "raise hand" or emoji reactions.
- No screen-sharing controls.
- No participant list.
- No "Thinking…" text indicator.

---

## 5. Customer input — Voice and text

### 5.1 Voice input (primary)

- Microphone active by default (after permission granted).
- **Visual responsiveness is instant.** The moment sound arrives at the microphone, the control shows it — a subtle level pulse or ring animation. This happens *before* speech detection completes. Instant responsiveness builds confidence that the microphone is working.
- Push-to-talk is not required. Continuous listening; natural turn-taking.
- Muting is a full action: tap microphone to mute; Alex acknowledges: *"I'll wait until you're back."*

### 5.2 Text input (fallback / accessibility / preference)

- Tap the text input toggle to open a small keyboard surface at the bottom of the screen.
- Microphone can remain active or be muted automatically (customer preference, remembered).
- Typed input submits on Enter; Alex responds in voice + captions.
- Especially important for: hearing-impaired customers, noisy environments, quick corrections, preference.

### 5.3 Interruption — invisible

The customer can interrupt Alex mid-sentence (speak or type). Alex pauses, listens, adapts.

**Alex never says *"Sorry"* or *"Go ahead"* when interrupted.** Real conversation doesn't apologize for turn-taking. Alex simply stops, listens, and continues naturally from where the customer took the exchange.

Engineering must support turn-taking that honors this: sub-second stop responsiveness, no verbal acknowledgment of the interruption itself.

---

## 6. Alex during the conversation

### 6.1 Voice, language, knowledge, personality

- Voice matches the teammate's configured voice.
- Language matches configured language.
- Personality matches the teammate's description sentence.
- Knowledge draws on What Alex knows (from My Team).
- Alex references sources honestly: *"I know from your menu that the lemon gelato is featured this summer."*
- Alex hedges when uncertain: *"I think you offer catering, but I'd want to confirm before I said more."*
- Alex does not fabricate specifics.

### 6.2 Listening — subtle continuous behaviors

Presence matters more than realism. Alex's listening is composed of tiny natural behaviors — nothing exaggerated.

- **Eye movement** — occasional gentle shifts, tracking, blinking naturally.
- **Breathing** — subtle chest movement.
- **Weight shifts** — occasional small posture adjustment.
- **Blinking** — natural rhythm.
- **Small smiles** — reactive but small; a quiet response to warmth in the customer's tone.

Behaviors run continuously during listening. The avatar never becomes a static image while the customer is speaking. Presence is the point.

Engineering and the avatar-system design track own the specific animation rules; this design guarantees the behavior category.

### 6.3 Handling unknowns

- Alex is honest: *"I don't have that information yet — but I can note the question and come back to you with an answer."*
- Unanswered questions surface as **first-class items in the post-conversation summary** (§7.5) with a one-tap **[Would you like me to learn this?]** affordance that transitions to teaching Alex the fact (per MY_TEAM_V1 §6.6 pattern).

### 6.4 Handling out-of-scope requests

- *"That's outside what I can help with — let me pass that back to the team."*
- Recorded as a note in the summary.

### 6.5 Handling abusive speech — progressive warnings

Warnings escalate in tone as behavior continues. Escalation feels human, not scripted.

- **First warning (soft):** *"I want to help."*
- **Second warning (firmer):** *"Let's keep this respectful."*
- **Third — Alex ends the conversation:** *"I'm going to end here."*

The gentle escalation feels human. Alex does not escalate faster than needed; a customer having a bad moment gets grace before Alex leaves.

### 6.6 What Alex does not do

- Does not read teammate knowledge verbatim.
- Does not disclose the operator's identity to a caller.
- Does not make promises about the business unless the knowledge supports them.
- Does not use customer data outside the workspace's scope.

---

## 7. Ending the conversation

### 7.1 Operator-initiated end

- Customer taps **End**.
- **Confirmation, when it makes sense:** *"End the conversation?"* + **[End]** / [Keep going].
- **Skipped when the conversation has already concluded naturally.** If Alex has said a warm closing (*"Alright — good talking with you."*) and there's been several seconds of silence, tapping End skips the confirmation and proceeds directly to close. Ending should feel effortless when the exchange is already complete.
- The heuristic (design-level): confirmation is asked only when there's meaningful active exchange in the ~5 seconds before End is tapped.

### 7.2 Alex-initiated end (natural)

Alex ends the conversation when:
- The natural exchange completes.
- Third abuse warning breached (§6.5).
- A hard cap is reached (§8).

When Alex ends the conversation naturally, they signal warmly:
- *"Alright — thanks for talking with me. I'll save this."* (natural end)
- *"I'm going to end here."* (abuse escalation)
- *"We've reached the conversation time included with your plan. I've saved everything we talked about."* (cap reached — see §8.2)

### 7.3 System-initiated end (failure)

- Alex says (if audible): *"We lost our connection."*
- Screen transitions to error state (§9 State 12).
- Any exchange captured up to the failure point is preserved.
- **Never expose infrastructure language.** No *"provider error,"* *"WebRTC failure,"* *"session expired."* Just: *"We lost our connection."*

### 7.4 Post-conversation transition — an emotional beat

The transition from active conversation to the resulting record is not just a loading state. It's a moment.

**Sequence:**
1. Alex delivers the closing line.
2. Alex's avatar quietly fades out over ~600ms.
3. A brief moment of empty stillness (~400ms).
4. A single line appears in Alex's voice: *"I'm putting this together for you…"*
5. Loading proceeds (transcript, summary, follow-up suggestions).
6. When ready: transition into the live-conversation record view in Piece Detail (per PIECE_DETAIL_V1 §7 — with the following additions for the post-conversation entry, §7.5).

The empty stillness followed by the *"putting this together for you…"* line reinforces that Alex is doing work even after the exchange ends. Not a spinner. Not a progress bar. A held moment.

### 7.5 Post-conversation summary — follow-up as first-class

The summary the customer sees in the live-conversation record (Piece Detail) always contains **four first-class sections**, not just one paragraph:

- **What we talked about** — the summary paragraph.
- **Questions to follow up on** — items the customer asked about that Alex couldn't confidently answer, each with a one-tap **[Would you like me to learn this?]** affordance that opens the teaching flow.
- **Things Alex learned** — new facts or context Alex picked up during the conversation, each with a subtle **[Save to what Alex knows]** affordance.
- **Possible content ideas** — the proactive content suggestions that were previously in the *[Turn this into a piece]* flow (PIECE_DETAIL_V1 §7.2), now surfaced automatically in the summary as a section with tappable affordances.
- **Suggested updates** — if Alex noticed something in the conversation that might contradict or update existing knowledge (*"You mentioned the summer menu is ending Friday — should I update that in what I know?"*).

Each item is small and low-friction. The summary becomes a bridge from conversation to Studio, Library, and My Team — a source of next actions.

### 7.6 Piece-creation celebration

When the customer arrives at the live-conversation record view (in Piece Detail), Alex quietly notes at the top of the summary:

> *"I've organized everything for you."*

Small. Quiet. Not a modal. Not a celebration animation. Just an acknowledgment that reinforces something useful happened. Consistent with the product voice.

---

## 8. Cost and capacity — human, protective

Cost visibility is important for informed use, but raw dollar counters create anxiety. Capacity is framed protectively.

### 8.1 Design principle

**Cost is presented as capacity, and capacity as reassurance.** Only become specific when specificity is needed.

Layered defaults:
- Plenty of time: *"You've got plenty of time."* (or capacity omitted entirely if the customer has no cap).
- Approaching (5–8 minutes remaining): *"A little time left on your plan this month."*
- Very close (~2 minutes): *"About two minutes left on your plan this month."*
- Hard cap reached: Alex speaks the empathetic close (§8.2).

Forbidden across all copy:
- *"$0.42 spent so far."*
- Any per-minute dollar figure.
- Real-time dollar counters.
- Percentage-full progress bars.

### 8.2 Ending on cap — empathy over limitation

When a hard cap is reached:

Alex says:
> *"We've reached the conversation time included with your plan. I've saved everything we talked about."*

The emphasis stays on **preservation** — *"everything we talked about is saved"* — not on limitation. The customer's work is intact; the plan's cap is a fact, but not a failure.

Approaching-cap warning during conversation:
> *"A couple minutes left on your plan this month. Want to wrap up, or should I keep going and we'll pick this back up next month?"*

Customer chooses. Alex honors the choice.

---

## 9. All states enumerated

### State 1 — Pre-conversation setup (first-time or early conversations)
- Full setup surface (§3.1) with Alex's face, name, role, what-will-happen paragraph, reassurance sentence, microphone-check offering, optional preview, primary [Start conversation], secondary [Not now].
- Capacity note and privacy note (small, quiet).

### State 2 — Pre-conversation setup (returning operator, ~5 successful conversations in)
- Reduced setup: face, name, role, reassurance sentence, [Start conversation], [Not now].
- What-will-happen paragraph collapsed.

### State 3 — Pre-conversation setup (experienced operator, ~10+ successful conversations)
- Minimal setup: face, **[Start conversation]**. That's it.
- Trust earns simplicity.

### State 4 — Microphone permission request
- Triggered by [Start conversation] tap if permission not granted.
- Native browser permission prompt.
- If denied: pre-conversation surface shows: *"I'll need microphone access to hear you. You can also type instead."* + **[Try microphone again]** / **[Type instead]** / **[Not now]**.

### State 5 — Microphone check
- Triggered by [Test my microphone] tap.
- Small level meter; Alex says: *"Say a few words — I want to make sure I can hear you."*
- On success: *"Sounds good — you're all set."*
- On no detection: *"I'm not hearing you — try speaking louder, or check that the right microphone is selected."*

### State 6 — Connecting
- Very brief (target <3s).
- Alex's face fades into the conversation layout; small quiet line: *"Getting ready…"*
- On success → State 7. On failure → State 12.

### State 7 — Active conversation — Alex listening
- Alex visible with subtle continuous listening behaviors (§6.2).
- No text indicator.
- Live captions of customer speech appearing in real time, with adaptive emphasis (§4.3).
- Microphone active with instant visual responsiveness (§5.1).

### State 8 — Active conversation — Alex thinking (short)
- Pause <~1.5s after customer speech ends.
- No text indicator. Silence is normal.
- Alex's expression may shift subtly.

### State 9 — Active conversation — Alex thinking (longer)
- Pause exceeds ~1.5s.
- Alex's expression shifts to a thoughtful look, considered smile, or slight tilt — behavior communicates thoughtfulness.
- No text indicator.

### State 10 — Active conversation — Alex speaking
- Mouth movement synced to speech.
- Live captions of Alex's speech appearing with full emphasis.
- No text state indicator.

### State 11 — Muted state
- Microphone control shows muted visual state (distinct pattern, not color alone).
- Alex acknowledges: *"I'll wait until you're back."*
- Alex remains present; does not speak until unmuted.

### State 12 — Text input mode
- Text input surface open at the bottom.
- Microphone can remain active or auto-mute (customer preference).
- Alex continues to respond in voice + captions.

### State 13 — Interruption
- Customer speaks or types mid-Alex-utterance.
- Alex pauses gracefully (no verbal *"Sorry"* or *"Go ahead"*).
- Alex listens, then continues from where the customer took the exchange.

### State 14 — Approaching cap warning
- When capacity drops below ~2 minutes: Alex speaks the approaching-cap message (§8.2).
- Customer responds naturally; Alex honors the choice.

### State 15 — Conversation failed
- Connection lost / provider error / system failure.
- Alex (if audible): *"We lost our connection."*
- Screen transitions to error state: *"Something went wrong. I've saved what we captured — you can pick it up in the record."* + **[See the record]** / **[Try again]** / **[Back to Alex]**.
- Any exchange captured up to the failure is preserved.

### State 16 — Reconnecting silently
- Brief network interruption; system attempts silent reconnect for ~2 seconds.
- After ~2s: a small quiet indicator appears: *"Trying to reconnect…"* — visible reassurance without alarm.
- If successful within ~5–10s: returns to active conversation state.
- If not: transitions to State 15.

### State 17 — End confirmation (when warranted)
- Customer taps End during active exchange.
- Small inline confirmation: *"End the conversation?"* + **[End]** / [Keep going].

### State 18 — End without confirmation (post-goodbye silence)
- Customer taps End after Alex's warm closing and several seconds of silence.
- No confirmation. Direct transition to State 20.

### State 19 — Alex-initiated end
- Alex closes naturally (§7.2) or on abuse escalation (§6.5) or on cap reached (§8.2).
- Warm closing delivered in Alex's voice.
- Direct transition to State 20.

### State 20 — Post-conversation transition (emotional beat)
- Alex's avatar fades out (~600ms).
- Brief moment of empty stillness (~400ms).
- Small line in Alex's voice: *"I'm putting this together for you…"*
- Loading proceeds silently.
- On completion: transition to Piece Detail live-conversation record view.

### State 21 — Arrival at live-conversation record (Piece Detail)
- Handled by PIECE_DETAIL_V1 §7 with the enhanced summary (§7.5 of this doc).
- Small quiet note at the top of the summary: *"I've organized everything for you."*
- Follow-up sections rendered: What we talked about / Questions to follow up on / Things Alex learned / Possible content ideas / Suggested updates.

### State 22 — Hard-cap end
- Cap reached during conversation.
- Alex speaks the empathetic close (§8.2).
- Transitions to Post-conversation flow (State 20 → State 21).

### State 23 — Alex ending due to abusive behavior
- Third abuse warning breached (§6.5).
- Alex: *"I'm going to end here."*
- Transitions to post-conversation record; summary includes a gentle note in the abuse-explanation.

### State 24 — Loading (initial screen)
- Layout renders with skeleton in avatar area.
- Face fades in; setup content appears.

### State 25 — Session lost (before or during conversation)
- Before: redirect to sign-in; on return, pre-conversation setup restored.
- During: attempted graceful reconnect (State 16); if unrecoverable, State 15.

---

## 10. Copy library

### 10.1 Pre-conversation setup

- What-will-happen (full version): *"You'll talk with me like a customer would. I'll respond the way I would to them. Take your time — we can stop whenever you want."*
- Reassurance sentence (always): *"There's nothing to get right. Just talk to me naturally."*
- Microphone offering: *"Want to make sure I can hear you?"* → **[Test my microphone]**
- Optional preview link: *"See what Alex knows before we start →"*
- Primary action: **[Start conversation]**
- Secondary: **[Not now]**
- Privacy note: *"This conversation stays in your workspace."*

### 10.2 Capacity messaging

- Plenty of time: *"You've got plenty of time."*
- Approaching: *"A little time left on your plan this month."*
- Very close: *"About two minutes left on your plan this month."*
- Approaching-cap in-conversation warning: *"A couple minutes left on your plan this month. Want to wrap up, or should I keep going and we'll pick this back up next month?"*
- Hard-cap end: *"We've reached the conversation time included with your plan. I've saved everything we talked about."*

### 10.3 Microphone check

- Prompt: *"Say a few words — I want to make sure I can hear you."*
- Success: *"Sounds good — you're all set."*
- No detection: *"I'm not hearing you — try speaking louder, or check that the right microphone is selected."*

### 10.4 Microphone permission denied

- Message: *"I'll need microphone access to hear you. You can also type instead."*
- Actions: **[Try microphone again]** / **[Type instead]** / **[Not now]**

### 10.5 Connecting

- Line: *"Getting ready…"*

### 10.6 Mute acknowledgment

- Alex on mute: *"I'll wait until you're back."*

### 10.7 End conversation

- Confirmation (when warranted): *"End the conversation?"* + **[End]** / [Keep going]
- Alex's warm closing (operator-initiated end): *"Alright — good talking with you."*
- Alex's warm closing (natural end): *"Alright — thanks for talking with me. I'll save this."*
- Alex's closing for abuse escalation: *"I'm going to end here."*
- Post-conversation transition line: *"I'm putting this together for you…"*

### 10.8 Post-conversation record top note

- *"I've organized everything for you."*

### 10.9 Summary section headings (in Piece Detail live-conversation record view)

- **What we talked about**
- **Questions to follow up on** — with per-item **[Would you like me to learn this?]** affordance.
- **Things Alex learned** — with per-item **[Save to what Alex knows]** affordance.
- **Possible content ideas** — with per-item tappable action opening Studio pre-scoped.
- **Suggested updates** — with per-item **[Update what Alex knows]** affordance.

### 10.10 Connection issues

- Reconnecting (after ~2s): *"Trying to reconnect…"*
- Connection lost — Alex (if audible): *"We lost our connection."*
- Error screen: *"Something went wrong. I've saved what we captured — you can pick it up in the record."*
- Actions on error: **[See the record]** / **[Try again]** / **[Back to Alex]**

### 10.11 Alex behaviors during conversation

- Unknown answer: *"I don't have that information yet — but I can note the question and come back to you with an answer."*
- Out-of-scope: *"That's outside what I can help with — let me pass that back to the team."*
- Uncertain claim: *"I think you offer catering, but I'd want to confirm before I said more."*
- Confident claim with source: *"I know from your menu that the lemon gelato is featured this summer."*

### 10.12 Abuse handling — progressive warnings

- **First:** *"I want to help."*
- **Second:** *"Let's keep this respectful."*
- **Third:** *"I'm going to end here."* (ends conversation)

### 10.13 Non-standard ending explanations in summary

Each non-standard end reason surfaces gently in the summary, in one sentence:
- Cap reached: *"We stopped because your monthly conversation time ran out."*
- Abuse: *"I ended this one early to keep things respectful."*
- System failure: *"We lost our connection near the end."*

**Never used across all copy:** *tokens, credits, per-minute rate, session ID, provider, model, RTP, WebRTC, error codes, HTTP codes, spinner, brain, WebSocket.*

---

## 11. Motion & interaction notes

### 11.1 Pre-conversation setup arrival

- Full-screen dissolve from the previous surface over ~400ms.
- Alex's face fades in first; setup content follows.

### 11.2 Start conversation transition

- On [Start conversation] tap: pre-conversation content fades; avatar transitions to conversation-layout position.
- Total: ~1 second to State 6 (Connecting).

### 11.3 Avatar during listening

- Subtle continuous behaviors run throughout: eye movement, breathing, weight shifts, blinking, small smiles (§6.2).
- Nothing exaggerated. Presence is the point.

### 11.4 Avatar during speaking

- Mouth movement synced to audio.
- Natural expression shifts appropriate to sentiment.

### 11.5 Avatar during longer thinking

- Expression shift to a thoughtful look, considered smile, slight tilt.
- No abrupt transition; smooth morph from listening/speaking to thinking.

### 11.6 Adaptive captions

- Current utterance appears with full emphasis; previous utterance's opacity drops smoothly over ~500ms as new utterance takes focus.
- Older utterances fade further with each new utterance.
- Scrolling up temporarily returns older utterances to full weight for reading.

### 11.7 Microphone visual responsiveness

- Sound arriving at microphone triggers immediate visual pulse on the control (within ~50ms of sound onset).
- This happens before any speech recognition processing — pure audio-level responsiveness.
- Builds confidence that the microphone is working.

### 11.8 Interruption

- Alex's audio and animation stop within ~300ms of customer speech/typing detection.
- Avatar shifts to listening state immediately.
- No verbal acknowledgment.

### 11.9 End confirmation

- When warranted: small inline confirmation appears (~200ms fade-in).
- When skipped (post-goodbye silence): direct transition to post-conversation.

### 11.10 Post-conversation transition — emotional beat sequence

- Alex's closing line completes.
- Avatar fades out over ~600ms.
- ~400ms of empty stillness (screen at rest, no elements visible).
- Small line in Alex's voice fades in center-screen: *"I'm putting this together for you…"* — over ~300ms.
- Line holds for the loading duration (usually 1–3 seconds).
- On completion: slide transition into Piece Detail live-conversation record view.

### 11.11 Reconnection indicator

- After ~2s of silent reconnect attempt: *"Trying to reconnect…"* fades in near the top of the screen over ~300ms.
- On successful reconnect: fades out over ~200ms; conversation resumes.
- On failure: transitions to error state.

### 11.12 Reduced motion

- Avatar retains speech sync and listening behaviors (functional, not decorative).
- Fades and slides become instant.
- Adaptive captions still adjust emphasis but without animated transitions.
- Emotional-beat sequence at post-conversation compresses to instant transitions but preserves the *"I'm putting this together for you…"* line.

---

## 12. Responsive behavior

- **Mobile (< 640px):**
  - Avatar occupies top ~50–55% of viewport.
  - Captions in middle third.
  - Call chrome at bottom, respecting safe area.
  - Text input surface slides up as a bottom sheet.
  - Duration/capacity in top status row.
- **Tablet (640–1024px):**
  - Similar to mobile with more generous margins.
- **Desktop (> 1024px):**
  - Avatar ~65–70% of vertical viewport, centered horizontally.
  - Captions below avatar with adaptive emphasis, comfortable reading width.
  - Call chrome at bottom, sized for reachability.

**Never:** side panels, secondary content areas, or floating widgets during a conversation.

---

## 13. Accessibility notes

- **Focus on setup:** primary action **[Start conversation]**. During the conversation, focus lands on the microphone control by default; text input when in text mode.
- **Keyboard:**
  - Space (microphone control focused): toggles mute.
  - T: toggles text input mode.
  - E: end conversation (opens confirmation, or ends directly per §7.1 heuristic).
  - Escape (in confirmation): cancels.
  - Tab: microphone control → text input toggle → end → captions (readable via SR).
- **Screen reader:**
  - Pre-conversation setup: announced in reading order (name, role, what-will-happen, reassurance, capacity, privacy).
  - During conversation: captions announced via `aria-live="polite"` regions. Speaker labels included.
  - Alex's meaningful state changes (thinking-transition, reconnecting) announced sparingly.
  - Post-conversation transition line announced.
- **Live captions:**
  - Always on. Not optional.
  - Adaptive emphasis (§4.3) preserved in visual rendering; screen reader reads all utterances in order.
  - Font size adjustable via the same reading controls as text pieces (PIECE_DETAIL_V1 §12).
- **Text input fallback:** available at all times.
- **`prefers-reduced-motion`:**
  - Avatar retains speech sync and subtle listening behaviors (functional).
  - Fades and slides become instant.
  - Emotional-beat sequence compresses but keeps the *"putting this together"* line.
- **Contrast:**
  - Captions meet AAA (7:1) — critical for live-conversation accessibility.
  - Microphone control and end control meet AAA — must be effortlessly reachable during a conversation.
  - Reconnecting indicator meets AA.

---

## 14. State preservation and recovery

- **During-conversation state** is maintained by the live-conversation provider infrastructure.
- **Silent reconnect** for ~2 seconds on brief network drops; visible *"Trying to reconnect…"* indicator afterward.
- **Full failure**: partial exchange preserved; customer accesses via **[See the record]** in the error state.
- **Post-conversation persistence**: transcript, summary, follow-up sections all persist as the live-conversation record piece.
- **No mid-conversation resume**: every conversation becomes a complete record. If the customer wants to continue a topic, they start a new conversation and can reference the prior record.
- **Recording**: always on for operator-initiated conversations in v1 (the operator is recording themselves; low privacy risk). Customer-facing recording policies belong with the deferred public deployment.

---

## 15. Design constraints & trade-offs made explicit

**Trade-off 1 — Chrome is deliberately minimal; teammate dominates.**
Cost: some customers may want more visible controls. Benefit: the surface feels like a conversation, not software.

**Trade-off 2 — Cost is presented as capacity, framed as reassurance.**
Raw dollar counters create anxiety. Capacity language protects the customer's focus.

**Trade-off 3 — No explicit "Thinking" text indicator.**
Cost: customers may briefly wonder what's happening during a longer pause. Justified because silence and expression communicate more honestly than labels; humans don't announce thinking.

**Trade-off 4 — Alex never says *"Sorry"* or *"Go ahead"* on interruption.**
Cost: some customers may find it strange that Alex doesn't verbally acknowledge being interrupted. Justified because real conversation doesn't apologize for turn-taking; verbal acknowledgment reads as robotic.

**Trade-off 5 — Adaptive captions reduce emphasis over time.**
Cost: reading older text requires scrolling. Benefit: the surface never feels like a messaging app.

**Trade-off 6 — End confirmation is context-aware.**
Cost: engineering must detect *"post-goodbye silence"* reliably. Benefit: ending an already-concluded conversation feels effortless.

**Trade-off 7 — Emotional beat after conversation end.**
Cost: an extra ~1s before the customer reaches the record. Benefit: reinforces Alex was doing work; makes the record's arrival feel intentional.

**Trade-off 8 — Follow-up suggestions are first-class in the summary.**
Cost: engineering must synthesize follow-ups reliably. Benefit: the summary becomes a bridge to future action, not just a memory.

**Trade-off 9 — Unknown answers become one-tap learning opportunities.**
Requires the runtime to distinguish confidently-unknown from uncertain answers. Justified because it turns conversation gaps into growth.

**Trade-off 10 — Pre-conversation surface simplifies over time as trust grows.**
Requires tracking successful conversation count. Justified because setup friction should decrease as the customer's competence increases.

**Trade-off 11 — Progressive abuse warnings, then Alex ends.**
Cost: some borderline cases may be tolerated longer than they should. Benefit: graceful escalation feels more human than immediate termination.

**Trade-off 12 — Error copy never exposes infrastructure.**
Cost: engineering must translate every error class into human language. Justified because infrastructure language breaks the teammate metaphor.

**Trade-off 13 — Reconnecting shows after ~2s, not immediately.**
Immediate indicators cry-wolf on brief hiccups. Justified because silent recovery for genuinely brief interruptions preserves conversation flow.

**Trade-off 14 — Microphone visual responsiveness is instant, before speech processing.**
Requires engineering separation of audio-level indication from speech recognition. Justified because instant feedback builds confidence the microphone is working.

**Trade-off 15 — Customer-facing continuity is a hard requirement, deferred implementation.**
Cost: v1 doesn't ship the highest-business-value variant. Justified because operator-initiated conversations build the trust necessary for public deployment; continuity discipline now avoids a fragmented experience later.

**Trade-off 16 — Post-conversation always transitions to Piece Detail live-conversation record.**
Rather than dropping the customer at teammate detail. Justified because the summary and follow-up affordances are the value the customer just earned; they should see them immediately.

**Trade-off 17 — Ending on cap emphasizes preservation, not limitation.**
The customer's plan reached its limit, but their work is intact. Framing matters — this shapes how the customer feels about the entire experience.

---

## 16. Deferred to later work

- **Customer-facing deployment** — the largest business value; requires separate design pass covering the external landing page, identity/privacy handling, opt-in recording disclosure, and asynchronous notifications to the operator. **Design continuity is a hard requirement** for that work: the customer-facing experience should inherit this design almost unchanged.
- **Visual system decisions** — avatar rendering polish, chrome styling, caption typography, state-indicator visuals, mic-level animation.
- **Motion timing calibration** — exact easing curves; avatar motion tuning.
- **Recording-to-caption sync polish** — highlighting in transcript during playback.
- **Multi-language conversations** — if a teammate is configured for a specific language, cross-language interaction handling.
- **Operator video / camera on** — deferred; voice-only for v1.
- **Screen-share during a conversation** — not planned.
- **Group conversations** — not planned for v1.
- **Live-conversation scheduling** — pre-scheduled conversations with a customer at a specific time — deferred.
- **Analytics on live-conversation performance** — engineering + product analytics track; must remain qualitative.
- **Accessibility settings** — customer preferences for caption visibility, text sizes, etc. — deferred to a settings-lite surface later.
- **Localization** — English only for v1.
- **Voice input for languages other than English** — deferred to localization.

---

## Revision History

**v1 — 2026-08-06.** First canonical version. Written and revised during the same session against operator direction. Major decisions incorporated:

- **Naming shift:** *"Live Call"* → *"Live Conversation"* in customer-facing and internal design language. File renamed to `LIVE_CONVERSATION_V1_2026-08-06.md` during the SESSION 237 housekeeping sweep; older documentation may still reference "Live Call" as a legacy label.
- **Anxiety reduction in pre-conversation:** added a reassurance sentence — *"There's nothing to get right. Just talk to me naturally."*
- **Microphone check conversational:** *"Want to make sure I can hear you?"* → **[Test my microphone]**.
- **Removed duration expectation copy:** *"Calls usually run 5 to 10 minutes"* removed to avoid performance pressure.
- **Capacity framed protectively:** *"You've got plenty of time"* by default; specifics only when nearing a limit.
- **Teammate owns the surface:** avatar larger; captions, status indicators, and controls all smaller and quieter.
- **Removed explicit *"Thinking"* text state:** silence + expression communicate thoughtfulness.
- **Subtle continuous listening behaviors:** eye movement, breathing, weight shifts, blinking, small smiles. Presence over realism.
- **Interruptions invisible:** Alex never says *"Sorry"* or *"Go ahead"* — just stops, listens, continues.
- **Adaptive captions:** current speaker full emphasis; prior utterances quietly fade. Never feels like a messaging app.
- **End confirmation smarter:** skipped after natural goodbye + silence; asked only during active exchange.
- **Post-conversation emotional beat:** avatar fades → moment of stillness → *"I'm putting this together for you…"* → transition. Reinforces Alex is doing work.
- **Follow-up first-class in summary:** dedicated sections for Questions to follow up on, Things Alex learned, Possible content ideas, Suggested updates.
- **Unknowns become learning opportunities:** one-tap **[Would you like me to learn this?]** on each unanswered question.
- **Progressive abuse warnings:** *"I want to help."* → *"Let's keep this respectful."* → *"I'm going to end here."*
- **Error recovery preserves trust:** *"We lost our connection."* — never exposes infrastructure.
- **Reconnection visible after ~2s:** *"Trying to reconnect…"* — visible reassurance without alarm.
- **Microphone visual responsiveness is instant:** sound arrival triggers pulse before speech-recognition processing.
- **Ending on cap emphasizes preservation:** *"We've reached the conversation time included with your plan. I've saved everything we talked about."*
- **Piece-creation celebration:** small quiet *"I've organized everything for you."* at the top of the summary.
- **Operator confidence grows over time:** pre-conversation setup thins with successful conversations; eventually reduces to face + [Start conversation].
- **Customer-facing continuity is a hard requirement** — the deferred public deployment should inherit this experience almost unchanged.
- **Trade-offs made explicit** across minimal chrome, capacity-as-reassurance, silence-over-labels, invisible interruptions, adaptive captions, context-aware end confirmation, emotional beat, first-class follow-ups, learning-from-unknowns, thinning setup over time, progressive abuse escalation, human error copy, delayed reconnect indicator, instant mic responsiveness, deferred customer-facing continuity, always-to-Piece-Detail transition, and preservation-framed cap ending.

---

## Interaction design phase — complete

With Live Conversation locked, the seven-screen foundational set is complete:

1. **Home** — locked.
2. **Onboarding** — locked.
3. **Studio** — locked.
4. **Library** — locked.
5. **My Team** — locked.
6. **Piece Detail** — locked.
7. **Live Conversation** — locked.

The four surfaces of the product (Home / Studio / Library / My Team) plus their natural next steps (Piece Detail, Live Conversation) are all specified. Onboarding delivers the customer into the loop; the loop sustains itself.

The next phase is no longer *"What should the product do?"* — it becomes *"How should it feel?"* That is an entirely different discipline: visual language, motion, and implementation.
