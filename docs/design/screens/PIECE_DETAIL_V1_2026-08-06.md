---
title: "Character OS — Piece Screen Design"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md", "../PRODUCT_IA_V1_2026-08-06.md", "HOME_V1_2026-08-06.md", "ONBOARDING_V1_2026-08-06.md", "STUDIO_V1_2026-08-06.md", "LIBRARY_V1_2026-08-06.md", "MY_TEAM_V1_2026-08-06.md"]
---

# Piece — Screen Design

## v1 — canonical screen design under PRODUCT_IA_V1

*Anchored in [`PRODUCT_IA_V1_2026-08-06.md`](../PRODUCT_IA_V1_2026-08-06.md) §7.3. Where the customer opens a piece of their work and either enjoys it, shares it, or picks it back up.*

**Naming note:** external documentation may refer to this surface as *"Piece Detail"* (the file remains `PIECE_DETAIL_V1_...` for sequence continuity), but throughout this design the language is deliberately simpler: *the customer opens the piece.* Implementation vocabulary does not leak into the product surface.

*Sibling to `HOME_V1_2026-08-06.md`, `ONBOARDING_V1_2026-08-06.md`, `STUDIO_V1_2026-08-06.md`, `LIBRARY_V1_2026-08-06.md`, `MY_TEAM_V1_2026-08-06.md`, `LIVE_CONVERSATION_V1_2026-08-06.md`. No wireframes.*

---

## 1. Purpose recap

Opening a piece is the moment the customer sees a single work at its full weight — video plays, text reads, audio breathes. The piece is the star; everything on this surface exists to present the work with dignity and give the customer a small set of obvious, appropriate next steps.

Library invites; the piece immerses. Philosophy #6 applies with force — this is *pride displayed*, not asset management.

The customer opens the piece from Library (tap a card), from Home's featured piece (tap the featured piece), from a teammate's *"What Alex has made"* section, or from Studio (post-preview when Alex offers a return path).

---

## 2. Piece types

One screen with **five view variants**, one for each kind of work the customer produces:

- **Video piece** — the most common form.
- **Text-based piece** — welcome messages, product announcements, video outlines, written posts.
- **Audio piece** — voiceovers, spoken pieces.
- **Live-call record** — the record of a real-time conversation. Distinct from creative pieces (§7).
- **Series** — a group of related pieces (§8).

All five share a common frame; the media area and some actions vary by type.

---

## 3. Common screen anatomy

Every view of a piece shares this structure:

- **Top area:**
  - **Back affordance** — context-aware label. When returning to Library: **[Back to everything you've made]** (per revision 24 — reinforces Philosophy #6). When returning to Home: **[Back to Home]**. When returning to a teammate: **[Back to Alex]**. When returning to Studio: **[Back to Studio]**.
  - **Title** — the piece's contextual name. **Large and prominent.** The title carries visual weight befitting the name of something the customer genuinely made.
  - **Small metadata line beneath the title** — publish date + teammate byline (if multiple teammates). For drafts: draft confidence status (§9). For conversation records: date + duration. Small, quiet type — the title dominates.

- **Media area** — the piece itself, presented in its most complete form (§4).

- **Primary action row** — one obvious primary action; up to two secondaries visible; other actions in a quiet **[More]** menu (§5).

- **Related context** — a collapsible section labeled *"About this piece"* (§6). Contains teammate detail, series membership, popular indicator, provenance affordance, and one thoughtful suggestion at the bottom.

- **Persistent nav** in the app frame — unchanged.

Chrome is minimal. Nothing decorative competes with the piece.

---

## 4. Media area — rendering by piece type

The media area gets ~60–75% of the vertical viewport on desktop, and the full useful area on mobile.

### 4.1 Video pieces

- **Full player** with standard controls (play, pause, scrub, volume, mute, captions if available, expand, playback speed).
- Poster frame visible until first play.
- **No autoplay.**
- **No hover-play** (desktop hover reveals controls only).
- Player is generously sized — the piece dominates.
- Beneath the player: **duration only.** No view counts, no engagement metrics, no numeric readouts. *Popular* status (if present) surfaces in the collapsible About section (§6).

**In-progress video (production underway):**
- Player area shows the current plan (per Studio's Zone C state C-2 pattern) with a quiet **draft-confidence status** (§9): *"Still being finished."*
- Primary action becomes **[Come back when it's ready]**; secondary [Keep watching].
- On completion, the plan is replaced by the finished player.

### 4.2 Text-based pieces

- Text rendered in a comfortable reading column (~640px max width, centered on desktop).
- Structured as the piece is structured: title (displayed above the reading area) → body paragraphs → call to action.
- Beautiful typography. Generous line-height. Comfortable margins.
- **Reading controls** (§12) available for text pieces only.
- If the piece has a suggested visual direction from Studio (for video outlines), it may render as a subtle italic note beneath the title: *"Visual direction: Warm daytime footage of the storefront…"* — only when meaningfully attached.

### 4.3 Audio pieces

- **Waveform** at generous size across the width.
- Prominent play affordance centered on the waveform.
- Duration and elapsed time during playback.
- **Transcript below** the waveform if available — presented in reading form; scrubbing the waveform highlights the current position in the transcript.

### 4.4 Live-call records

See §7.

### 4.5 Series

See §8.

---

## 5. Primary and secondary actions

The customer always has **one obvious primary action** when opening a piece. Its label describes exactly what happens next.

### 5.1 Primary action by state

| Piece state | Primary action |
|---|---|
| Published (any type) | **[Remix this]** |
| Draft — *Needs your review* | **[Review the plan]** |
| Draft — *Ready to publish* | **[Publish this]** |
| Draft — *Still being finished* | **[Come back when it's ready]** |
| Draft — *Waiting on rendering* | **[Come back when it's ready]** |
| Live-call record | **[Turn this into a piece]** *(§7.3)* |
| Series | **[Add to this series]** *(§8.4)* |
| Retired *(via Library recovery)* | **[Bring this back]** |

### 5.2 Secondary actions

Up to two secondary actions visible in the action row. Additional actions live in a quiet **[More]** menu.

**Visible secondaries** (best two chosen for the piece type; ordered by likely customer intent):

- **[Share]** — always available for published pieces. See §5.3 for the share flow.
- **[Download \<type\>]** — always available for published pieces. Label adapts to piece type:
  - Video: **[Download video]**
  - Audio: **[Download audio]**
  - Text: **[Download text]**
  - Live-call recording: **[Download recording]**

### 5.3 [Share] flow

The customer's intention is *"share this."* The mechanism (link, share sheet, direct-to-platform) is secondary.

- Tapping **[Share]** opens a compact **share sheet**:
  - **[Copy link]** — copies the shareable link. Confirmation appears inline: *"Link copied."*
  - **[Share via…]** — invokes the system share sheet on mobile; on desktop, expands to a small list of options (social messaging, email).
  - **[Share directly to \<platform\>]** — one row per connected destination (post-reveal per IA §9.2). Tapping publishes there.
  - **[Publish elsewhere]** — expands direct-to-platform options for destinations *not yet connected*. Only shows destinations the piece has not already been published to (per revision 26 Q6).

### 5.4 [More] menu

- **[Rename]** — inline edit of the title.
- **[Move to a series]** — opens a compact picker.
- **[The story behind this]** — opens the archival view (§5.6).
- **[Retire this piece]** — soft delete with 30-day grace (§5.7).
- **[About Alex]** — opens the teammate detail view for this piece's teammate (§6.1).

Menu items adapt by piece state; not every item is available for every piece.

### 5.5 [Remix this] flow

Tapping **[Remix this]** opens Studio with the piece loaded as the starting point of an **alternate take** (§10).

**Studio state on remix opening:**
- The remixed piece's plan is preloaded in Zone C.
- Alex narrates the safety line first, then the action:
  > *"This won't change your original."*
  > *"Ok — remixing your summer sale video. Where should we take it?"*
- The safety line is not a modal or a warning banner — it's a natural sentence from Alex, delivered before the customer takes any action. It eliminates anxiety in one sentence.
- The customer can steer freely. The original piece is untouched — the remix creates a new **alternate take**.

### 5.6 [The story behind this]

Full-screen archival view of the piece's creative journey. Read-only. Purpose: provenance and self-reflection.

**Structure:**
- **Your original brief** — the customer's Q3 answer or Studio prompt-in-place.
- **Figuring it out together** — if the piece came from a Path C warmup, the exchange lands here.
- **The plan** — the plan as it existed at commitment (Studio State 10).
- **Key decisions** — meaningful steers the customer made along the way.
- **What helped Alex create this** *(§6.4)* — sources.
- **Alternate takes** — if this piece has alternate takes (or was itself an alternate take of another piece), a small navigator at the top of the archival view lets the customer move between takes:
  - *Original*
  - *Summer version*
  - *Short version*
  - *Spanish version*
  - Currently viewing: subtle highlight.
- No editing anywhere. Just understanding evolution.

**Back affordance:** **[Back to the piece]** — returns to the standard piece view.

Read-only feels like an artist's process notes, not audit history.

### 5.7 Retiring a piece (soft delete)

**[Retire this piece]** — quiet action in the [More] menu.

**Flow:**
1. Confirmation sheet: *"Retire this piece? You can bring it back within 30 days."* + **[Retire]** / [Not now].
2. On confirmation: piece disappears from Library and from teammate's *"What Alex has made"*.
3. The customer is returned to the entry surface with a soft notice at the top: *"Retired. You have 30 days to bring it back."* + **[Undo]**.
4. The notice **persists until dismissed** or the customer navigates away from the surface. Never auto-dismisses.
5. Within 30 days: recoverable via a **[Retired pieces]** collapsed section at the bottom of Library.
   - **Retired pieces retain their thumbnails** (per revision 11). The customer remembers visually, not by title.
6. After 30 days: silently discarded.

**Recovery from retired:**
When the customer taps **[Bring back]** on a retired piece:
- The piece returns to its natural position in Library.
- A small warm notice appears at the top of the entry surface: *"Welcome back."* — quiet, human, consistent with Alex's voice.
- The notice fades naturally after ~5 seconds.

Never called *"Delete"* in customer copy.

---

## 6. Related context — "About this piece"

Below the media area sits a **collapsible section labeled *"About this piece."*** Most customers won't care every time about teammate, series, popularity, or provenance. The default surface stays clean; the customer expands when curious.

**Default visible above the collapsible section:**

- **Teammate byline:** *"Made with Alex."* Tappable — opens the teammate detail view (called out as *[About Alex]* on hover / in the [More] menu). Face at ~40px alongside the name.

Everything else lives under **[About this piece]**, collapsed by default (small chevron caret to expand).

### 6.1 What's inside the collapsible

- **Made with Alex** — expanded teammate context with quick affordance to open the teammate detail view. Called **[About Alex]** in the menu; on the surface itself, the row reads: *"Made with Alex →"* tappable.
- **Series membership** — *"Part of your summer promotion series — 3 pieces."* Tap opens the series view.
- **Popular** — if the popular reveal has fired and this piece is popular: *"Popular."* No numeric metrics. Ever.
- **The story behind this** — links to the archival view (§5.6). *"See how this came together →"*
- **What helped Alex create this** — links to the sources surface (§6.4). *"See what helped Alex create this →"*
- **One thoughtful suggestion** at the bottom (§6.3): *"You might also like your welcome video."* — a single piece Alex thinks relates. One, never a carousel.

### 6.2 If the customer has no series and no popular status

The collapsible section still exists; it may be shorter. Even if only *Made with Alex* and *The story behind this* remain, the section stays consistent so the surface's shape doesn't shift piece-to-piece.

### 6.3 One thoughtful suggestion

At the bottom of the *About this piece* section (or as its final row), one quiet recommendation:

> *"You might also like [contextual piece name]."*

- **One piece only.** Never a carousel. Never infinite scrolling recommendations.
- Alex curates the suggestion based on the customer's body of work — relatedness by teammate, topic, series, or format.
- Tapping opens that piece.
- If Alex doesn't have a confident suggestion, the row simply doesn't render.

This turns Piece into a subtle pathway between related work without feeling like a recommendation engine.

### 6.4 What helped Alex create this

Human-first source visibility. The customer thinks about documents, not files.

- Section labeled *"What helped Alex create this."*
- Contents rendered as prose:
  > *"I used your menu."*
  > *"I used the welcome guide you shared."*
  > *"I used the FAQ."*
  > *"I drew on what you told me during onboarding."*
- **Never filenames as the primary UI.** If the customer wants to see the underlying artifacts, a small quiet affordance may allow access, but the primary presentation is always human-language source references.
- If no sources contributed (rare — the piece came entirely from the customer's typed brief), the section says: *"You told me everything I needed for this."*

---

## 7. Live-call records

A conversation record is different from creative work — it's evidence of a real-time conversation, not something the customer authored. It has its own view.

### 7.1 Structure — summary leads

**The summary comes first. The transcript is secondary.**

The customer wants *"what happened?"* before *"exactly what was said."*

**Section order:**

1. **Title + metadata** at the top (per §3): *"Call with Jamie · Tuesday, 8 minutes · With Alex."*
2. **Summary** — a one-paragraph third-person summary. Prominent, comfortable to read. Example:
   > *"Jamie asked about catering for a July event. Alex walked through the small-party options and the pricing tiers. Jamie plans to call back next week to confirm the guest count."*
3. **Suggested follow-up** — Alex's proposed next action, when relevant:
   > *"Suggested follow-up: send Jamie the catering menu."*
   Presented as a subtle inline card with an action: **[Send the catering menu →]** — tapping opens Studio pre-scoped to draft that follow-up piece.
4. **Transcript** — below the summary, scrollable, formatted with speaker labels and timestamps. Comfortable typography.
5. **Recording player** (if a recording exists) — audio waveform above the transcript, scrubbable, syncs highlight in the transcript (target — engineering may ship without sync initially per revision 26 Q3).

### 7.2 Primary action — [Turn this into a piece], with proactive suggestions

**Live calls sometimes surface moments worth reusing as creative work.** Alex actively suggests when possible.

**Enhanced flow:**

If Alex can detect obvious content opportunities from the call, they surface first:

> *"This conversation could become:*
>   *• An FAQ*
>   *• A customer story*
>   *• A social post*
> *— or highlight a moment yourself."*

The customer taps one of the suggested types or highlights their own passage from the transcript.

**If Alex detects no obvious opportunities:**

> *"Any moment from this call worth turning into something? A quote, a story, a question worth answering publicly?"*

The customer selects a passage from the transcript (highlight text) or types the moment freely.

On selection/tap: Alex transitions to Studio with the moment loaded as the initial brief for a new piece.

The suggestions and free-text selection paths are both available — proactive suggestions augment rather than replace the customer's autonomy.

### 7.3 Secondary actions

- **[Share]** — same share sheet as creative pieces (§5.3), scoped to what makes sense (link to the transcript view, or copy the summary text).
- **[Download recording]** — if a recording exists. Adapts label to the media type per §5.2.
- **[Copy transcript]** — copies the transcript text to clipboard.

**In the [More] menu:**
- **[About Alex]** — teammate detail.
- **[See all conversations with Alex]** — links to the *Recent conversations* section of the teammate detail view.
- **[Retire this record]** — soft delete with 30-day grace, same pattern as creative pieces.

### 7.4 Retirement of conversation records

Same soft-delete pattern; language adapted:
- Confirmation: *"Retire this conversation record? You can bring it back within 30 days."*
- Welcome-back: *"Welcome back."*

---

## 8. Series view

A series is a group of related pieces (introduced via the series reveal, IA §9.2). It feels like a creative project, not a grouped list.

### 8.1 Structure

- **Series cover** at the top — a **quiet hero image** representing the series (§8.2).
- **Title** — the series' name, prominent below the cover.
- **Metadata line:** *"3 pieces · Started 3 weeks ago · Made with Alex."*
- **Description** (if the customer added one) — a short quiet paragraph beneath the metadata describing the series' theme.
- **Member pieces** — a vertical stack of compact Library-style cards, in the order they were added (or in a customer-specified sequence if that capability reveals later).

### 8.2 The series cover

- Auto-selected default: the poster of the newest published piece in the series.
- Customer override: small **[Change cover]** affordance below the cover (in the [More] menu on mobile). Tap opens a compact picker showing the posters of member pieces.
- Cover size: generous — occupies the media-area position at approximately the same visual weight as a video player.
- If no member piece has a poster (e.g., all-text series), the cover renders as a designed placeholder with the series name centered.

This makes a series feel like an intentional body of work rather than a folder of items.

### 8.3 Sequence

- V1 default: pieces render in the order they were added.
- Customer-configurable sequence is deferred (may reveal later for large series).

### 8.4 Series-level primary action

**[Add to this series]** — opens Studio with the series pre-scoped:
- Alex narrates: *"Adding to your summer promotion series. What's the next piece?"*
- The new piece is drafted; on publish, it joins the series.

### 8.5 Series-level secondary actions

- **[Rename series]** — inline edit of the title.
- **[Change theme]** — inline edit of the description.
- **[Change cover]** — picker for the hero image.
- **[Stop grouping these together]** — the operation formerly known as *"Split into individual pieces."* Removes series membership from all members; individual pieces remain in Library. Confirmation:
  > *"Stop grouping these together? The pieces will stay in your library, but they won't be part of a series anymore."*
  > Actions: **[Stop grouping them]** / **[Cancel]**
- **[Retire this series]** — retires the series with symmetric confirmation:
  > *"Retire this series? Keep the pieces in your library, or retire them too?"*
  > Actions: **[Keep the pieces]** / **[Retire everything]** / **[Cancel]**

All destructive flows offer a Cancel action. Symmetric across the product.

### 8.6 Member piece view

Tapping a member piece opens its individual piece view — with back label *"Back to your summer promotion series"* so the customer can return to the series view naturally.

---

## 9. Alternate takes

The concept formerly known as *"versions"* is renamed. **Customers naturally understand creative takes better than version numbers.**

### 9.1 Language

- Never *"version 2"* or *"v3"* in customer-facing copy.
- Instead: *Original*, *Summer version*, *Short version*, *Spanish version*, *Casual take*, etc.
- Each alternate take is a distinct piece (created via [Remix this]) but linked through provenance.

### 9.2 Where alternate takes appear

- **In the collapsible *"About this piece"* section** — a small row: *"3 alternate takes."* Tap opens a compact list of the takes with their names and small thumbnails.
- **In *The story behind this*** — the archival view shows the take navigator at the top (§5.6).
- **In Library** — cards for alternate takes appear individually (each is its own piece); the *About this piece* row surfaces the relationship.

### 9.3 Naming alternate takes

- Auto-named on remix based on the direction the customer took (Alex proposes a name):
  - If the customer said *"make it shorter,"* the take is named *"Short version."*
  - If the customer said *"in Spanish,"* the take is named *"Spanish version."*
  - Default fallback: *"Alternate take"* with a small subscript when needed (e.g., *"Alternate take · 2"*), but the auto-naming should almost always produce something more meaningful.
- Customer can rename any take at any time via [Rename].

---

## 10. Retirement, recovery, and welcome-back

Consolidated from §5.7 for reference.

**Retirement flow** (per §5.7):
1. Quiet **[Retire this piece]** action in [More].
2. Confirmation sheet with 30-day grace explanation.
3. Post-retirement soft notice at entry surface: *"Retired. You have 30 days to bring it back."* + **[Undo]**. Persists until dismissed.
4. Recovery via Library's *[Retired pieces]* section.

**Retired pieces retain their thumbnails** for visual recognition (per revision 11).

**Welcome-back** — when the customer brings a piece back:
- The piece quietly returns to Library.
- A small warm notice at the top of the entry surface: *"Welcome back."*
- Notice fades naturally after ~5 seconds.
- Small. Human. Consistent with product voice.

---

## 11. Draft confidence — human status

Drafts communicate where they stand in **natural language**, not with technical labels like *"Draft."*

### 11.1 Confidence states

| Draft state | Status label |
|---|---|
| Plan still being drafted (Studio phase 1a) | *"Still being drafted."* |
| Plan complete but not committed (Studio state 8) | *"Needs your review."* |
| Committed to production, media generating (Studio state 11) | *"Still being finished."* |
| Media complete but not yet published (Studio state 12) | *"Ready to publish."* |
| Rendering queued or delayed | *"Waiting on rendering."* |

### 11.2 Where confidence status appears

- **On the metadata line** beneath the piece title in the piece view.
- **On draft cards in Library's *Still in progress*** section.
- **On the piece's card in Home Zone C** when featured.

These statuses feel more human than a generic "Draft" label and communicate exactly what stage the piece is at.

---

## 12. Reading controls (text pieces only)

Text-based pieces support lightweight reading controls for accessibility and longer reading.

- **[A-]** — decrease text size.
- **[A+]** — increase text size.
- Both are small quiet affordances at the top-right of the reading column (or in a compact controls row above the text).
- Steps: 3 sizes total (small / medium / large). Simple, not granular.
- **The customer's chosen text size persists across all text pieces** (across sessions).
- No font choice, no line-height controls, no color-scheme toggle in v1. Just the two size buttons.

---

## 13. All states enumerated

### State 1 — Standard published video piece
- Full player with controls; poster frame; no autoplay.
- Large title, small metadata beneath.
- Primary: **[Remix this]**. Secondaries: **[Share]**, **[Download video]**.
- **[More]** menu with rename, move to series, the story behind this, retire, About Alex.
- Collapsible *About this piece* section.

### State 2 — Standard draft video piece
- Player shows the current draft state (from Studio's plan or partial media).
- Metadata shows draft-confidence status (§11).
- Primary: **[Continue working on this]** or state-specific label per §5.1.
- Secondaries reduced (Share is muted or absent for drafts unlisted for public share).

### State 3 — Standard published text piece
- Text rendered in reading column with reading controls (§12).
- Same action set as State 1; **[Download text]** replaces **[Download video]**.

### State 4 — Standard draft text piece
- Same as State 2 but with text rendering + reading controls.

### State 5 — Published audio piece
- Waveform + player + transcript below.
- Same actions as State 1; **[Download audio]** as secondary.

### State 6 — Draft audio piece
- Same as State 5 but with draft-confidence indicator.

### State 7 — Piece being finished in the background
- Media area shows the current plan (Studio state C-2 pattern) with quiet *Still being finished* draft-confidence indicator.
- Primary: **[Come back when it's ready]**. Secondary: **[Keep watching]**.

### State 8 — Live-call record
- Summary leads; suggested follow-up prominent; transcript below.
- Primary: **[Turn this into a piece]** (with proactive suggestions per §7.2).
- Secondaries: **[Share]**, **[Download recording]**.

### State 9 — Series view
- Series cover at top; title, metadata, description; member pieces below.
- Primary: **[Add to this series]**.
- Secondaries: **[Share]**, **[Rename series]**.
- [More] menu with change cover, change theme, stop grouping these together, retire this series.

### State 10 — Popular piece
- Standard piece view + *Popular* row in *About this piece* section.
- No numeric readouts anywhere.

### State 11 — Piece with alternate takes
- Standard view + *"3 alternate takes"* row in *About this piece* section. Tap opens compact list.
- Each take is a distinct piece with its own view.

### State 12 — Retired piece — recovery view
- Same layout as the piece's standard state, with a soft banner at the top: *"This piece has been retired. Bring it back?"* + **[Bring back]** action.
- Retired thumbnails preserved for visual recognition.

### State 13 — [The story behind this] — archival view
- Full-screen archival view.
- Take navigator at top (if alternate takes exist).
- Sections: Your original brief / Figuring it out together / The plan / Key decisions / What helped Alex create this / Alternate takes.
- Read-only. **[Back to the piece]** returns.

### State 14 — [What helped Alex create this] — sources view
- Full-screen or embedded section within the About this piece expansion.
- Prose descriptions of sources; never filenames.

### State 15 — Retirement flow
- Confirmation sheet with 30-day grace explanation.
- On confirmation: piece disappears; soft notice at entry surface with **[Undo]**.

### State 16 — Welcome-back after recovery
- Piece returns to Library.
- Small warm *"Welcome back."* notice at top of entry surface, fades naturally after ~5s.

### State 17 — [Share] flow
- Compact share sheet with Copy link / Share via / Share directly to \<connected platform\> / Publish elsewhere.

### State 18 — [Turn this into a piece] with proactive suggestions
- Alex surfaces 3 detected opportunities as inline choices (*FAQ / Customer story / Social post*).
- Customer taps one → Studio opens pre-scoped.
- Customer can also highlight a passage or type free-text moment.

### State 19 — Loading
- Layout renders with skeleton in the media area and placeholders in the action row.
- *About this piece* section renders collapsed.

### State 20 — Error (piece failed to load)
- Full-screen empty state with soft message: *"I'm having trouble opening this piece right now. Try again in a moment."* + **[Try again]**.

### State 21 — Error (media failed to render but metadata OK)
- Media area shows a soft placeholder: *"Couldn't load the video right now."* + **[Try again]** scoped to the media area.
- Actions and *About this piece* remain interactive.

### State 22 — Session lost
- Silent redirect to `/sign-in` with `from` preserved.

### State 23 — Playback position resume
- On return to a piece within the recent-history window (persisted across sessions per §15):
  - Video/audio playback offers to resume at the last position.
  - Small quiet affordance: *"Resume from 3:20?"* + **[Resume]** / [Start over].
  - Persists across sessions for at least a recent window (e.g., last several pieces viewed).

### State 24 — Stale platform connection during share
- Customer taps a *Share directly to \<platform\>* action; the connection is stale or broken.
- Instead of an error, conversational recovery:
  > Alex: *"Looks like the Instagram connection needs refreshing. Want to reconnect?"* + inline **[Reconnect]** / [Cancel].
- On [Reconnect]: OAuth refresh; on success, share proceeds.

---

## 14. Copy library

### 14.1 Titles and metadata

- **Title** — contextual, prominent. The name of what the customer made.
- **Metadata line** — small, quiet, beneath the title:
  - Published: *"Published Tuesday · Alex"*
  - Draft: *"Ready to publish · Alex"* / *"Needs your review · Alex"* / *"Still being finished · Alex"* / *"Waiting on rendering · Alex"* / *"Still being drafted · Alex"*
  - Live-call: *"Tuesday, 8 minutes · With Alex"*
  - Series: *"3 pieces · Started 3 weeks ago · Made with Alex"*

### 14.2 Back affordance labels

- Returning to Library: **[Back to everything you've made]**
- Returning to Home: **[Back to Home]**
- Returning to a teammate detail: **[Back to Alex]**
- Returning to Studio: **[Back to Studio]**
- From a series member back to the series: **[Back to your summer promotion series]** (or the specific series name)
- From *The story behind this* back to the piece: **[Back to the piece]**

### 14.3 Primary action labels

- **[Remix this]** — published pieces.
- **[Review the plan]** — draft: Needs your review.
- **[Publish this]** — draft: Ready to publish.
- **[Come back when it's ready]** — draft: Still being finished or Waiting on rendering.
- **[Continue working on this]** — draft: Still being drafted.
- **[Turn this into a piece]** — conversation records.
- **[Add to this series]** — series view.
- **[Bring this back]** — retired recovery view.

### 14.4 Secondary action labels

- **[Share]** — always for published pieces.
- **[Download video]** / **[Download audio]** / **[Download text]** / **[Download recording]** — type-adaptive.

### 14.5 Share sheet

- **[Copy link]** → confirmation: *"Link copied."*
- **[Share via…]** — invokes system share sheet or opens desktop options.
- **[Share directly to \<platform\>]** — per connected destination.
- **[Publish elsewhere]** — expands direct-to-platform options for unconnected destinations only.

### 14.6 [More] menu

- **[Rename]**
- **[Move to a series]**
- **[The story behind this]**
- **[Retire this piece]** *(never "Delete")*
- **[About Alex]**

### 14.7 Related context (*About this piece*)

- Default row (always visible above collapsible): *"Made with Alex →"*
- Collapsible section header: **About this piece**
- Rows inside (when applicable):
  - *"Made with Alex →"*
  - *"Part of your summer promotion series — 3 pieces →"*
  - *"Popular"*
  - *"3 alternate takes →"*
  - *"See how this came together →"* (links to The story behind this)
  - *"See what helped Alex create this →"* (links to sources view)
  - *"You might also like [contextual piece name] →"*

### 14.8 The story behind this

- Section headings inside:
  - *"Your original brief"*
  - *"Figuring it out together"* (when a warmup happened)
  - *"The plan"*
  - *"Key decisions"*
  - *"What helped Alex create this"*
  - *"Alternate takes"*
- Take navigator: labels are the take names (*Original / Summer version / Short version / Spanish version*).

### 14.9 What helped Alex create this

- Section heading: *"What helped Alex create this"*
- Rows: prose descriptions (*"I used your menu."* / *"I used the welcome guide you shared."* / *"I used the FAQ."* / *"I drew on what you told me during onboarding."*)
- No-sources fallback: *"You told me everything I needed for this."*

### 14.10 Remix flow — Studio narration on open

Delivered by Alex when Studio opens after [Remix this]:
1. *"This won't change your original."*
2. *"Ok — remixing your summer sale video. Where should we take it?"*

The safety line comes first — it's the assurance that reduces anxiety before the customer takes any action.

### 14.11 Retirement

- Confirmation: *"Retire this piece? You can bring it back within 30 days."* + **[Retire]** / [Not now]
- Post-retirement notice: *"Retired. You have 30 days to bring it back."* + **[Undo]** (persists until dismissed)
- Welcome-back on recovery: *"Welcome back."* (fades after ~5s)

### 14.12 Live-call — summary and follow-up

- Summary format: *"[Counterparty] asked about [topic]. [Teammate] [what they did]. [Outcome or plan]."*
- Suggested follow-up format: *"Suggested follow-up: [specific action]."*
- Follow-up action button: **[Send the catering menu →]** (or contextual action)

### 14.13 [Turn this into a piece] — proactive suggestions

- Alex's proactive prompt:
  > *"This conversation could become:*
  >   *• An FAQ*
  >   *• A customer story*
  >   *• A social post*
  > *— or highlight a moment yourself."*
- Fallback (no obvious detections):
  > *"Any moment from this call worth turning into something? A quote, a story, a question worth answering publicly?"*

### 14.14 Series — [Stop grouping these together]

- Confirmation: *"Stop grouping these together? The pieces will stay in your library, but they won't be part of a series anymore."*
- Actions: **[Stop grouping them]** / **[Cancel]**
- Post-action: temporary **[Undo]** affordance for ~30 seconds.

### 14.15 Series — [Retire this series]

- Confirmation: *"Retire this series? Keep the pieces in your library, or retire them too?"*
- Actions: **[Keep the pieces]** / **[Retire everything]** / **[Cancel]**

### 14.16 Stale platform connection

- Conversational recovery: *"Looks like the Instagram connection needs refreshing. Want to reconnect?"* + **[Reconnect]** / [Cancel]

### 14.17 Playback resume

- *"Resume from 3:20?"* + **[Resume]** / [Start over]

### 14.18 Error copy

- Load failed: *"I'm having trouble opening this piece right now. Try again in a moment."* + **[Try again]**
- Media failed: *"Couldn't load the video right now."* + **[Try again]**

**Never used:** *Delete (in customer copy), asset, file (except in prose about documents), item, record (except *conversation record* internally), version, HTTP codes, brain.*

---

## 15. Motion & interaction notes

### 15.1 Opening a piece from Library

- Lateral slide from Library (~400ms).
- Library preserves state (per LIBRARY_V1 §10).
- Media area is the first element to draw the eye; other elements fade in coordinated.

### 15.2 Opening a piece from other surfaces

- **From Home:** dissolve (400ms), face persists briefly.
- **From My Team teammate detail:** lateral slide.
- **From Studio (post-preview):** contextual — usually a "back" gesture from Preview.

### 15.3 Media playback

- Play affordance is prominent and central.
- Standard player controls appear on hover (desktop) or tap (mobile) after playback starts.
- Full-screen expand: player takes over the viewport with minimal chrome.
- Playback position offers to resume if applicable (§15.7 for persistence details).

### 15.4 Return to entry surface

- Reverse slide/dissolve.
- Scroll position and focused card preserved.

### 15.5 [Remix this] transition

- Full-screen dissolve to Studio over ~500ms.
- Alex delivers the safety line first (*"This won't change your original."*), then the working line — both as normal narration in Zone L over the first ~1.5 seconds after Studio settles.

### 15.6 [Share] sheet

- Bottom sheet (mobile) / anchored panel (desktop), slides in over ~300ms.
- Dismisses on outside tap or Escape.

### 15.7 [More] menu

- Compact menu opens on tap.
- Anchored to the [More] affordance.
- Dismisses on outside tap or Escape.

### 15.8 About this piece — expand / collapse

- Tap the section header or caret to expand.
- Contents fade in over ~250ms with a slight height animation.
- Collapse reverses.

### 15.9 The story behind this — full-screen transition

- Full-screen slide-up (mobile) or dissolve (desktop) over ~400ms.
- Take navigator (if alternate takes exist) appears at the top.
- Tapping a take in the navigator cross-fades the archival contents (~300ms).
- **[Back to the piece]** reverses the transition.

### 15.10 Retirement flow

- Confirmation sheet slides in over ~300ms.
- On confirmation: piece transitions out (~400ms fade); return to entry surface; retirement notice appears at top with **[Undo]**.
- Notice persists until dismissed.

### 15.11 Welcome-back on recovery

- Piece card fades back into Library (~400ms).
- *"Welcome back."* notice fades in at top of entry surface (~200ms).
- Notice fades out naturally after ~5s.

### 15.12 [Turn this into a piece] with proactive suggestions

- Suggestion chips appear as an inline group beneath the summary or above the transcript.
- Tap a chip → transition to Studio (per §15.5).
- Custom highlight in transcript: standard text selection; on select, a small **[Turn this into a piece]** affordance appears near the selection.

### 15.13 Text pieces — reading control interactions

- Tap **[A+]** or **[A-]**: text size updates instantly.
- Setting persists via localStorage or account settings.

### 15.14 Reduced motion

- All transitions reduce to instant swaps.
- Media playback remains functional.
- Sheet slides become instant appear/disappear.

---

## 16. Responsive behavior

- **Mobile (< 640px):**
  - Full-viewport layout.
  - Media area maximized within available height.
  - Primary action fixed above bottom nav.
  - Secondary actions in a compact row below primary.
  - [More] menu opens as bottom sheet.
  - Reading controls (text pieces) sit above the text column, right-aligned.
- **Tablet (640–1024px):**
  - Similar to desktop but with tighter margins.
  - Media area fills more of the viewport.
- **Desktop (> 1024px):**
  - Content constrained to a comfortable reading/viewing width (max ~960px for video, ~640px for text).
  - Media dominates the viewport.
  - Actions and *About this piece* section below the media, cleanly laid out.

**Never:** sidebars in the piece view. The piece is the focus.

---

## 17. Accessibility notes

- **Focus on opening a piece:** focus lands on the media area (the player controls, or the reading content for text pieces).
- **Return to entry surface:** focus returns to the previously tapped card.
- **Keyboard:**
  - Space/K plays/pauses video and audio.
  - Arrow keys scrub.
  - Tab moves through primary action → secondary actions → [More] → back affordance → related context links → *About this piece* expand affordance → collapsible contents (when expanded).
  - Escape closes [More] menu, [Share] sheet, or confirmation sheets.
  - Text pieces: **[A+]** / **[A-]** are keyboard-focusable and operable.
- **Screen reader:**
  - Title announced first, then metadata line.
  - Media area described contextually (*"Video: Your summer sale video, 30 seconds."* / *"Text piece."* / *"Live call with Jamie, 8 minutes."*).
  - Draft-confidence status announced as part of metadata for drafts (*"Draft, Needs your review, Alex made this."*).
  - Primary action announced with clear context (*"Remix this piece, button."*).
  - *About this piece* section announced as collapsible with expanded/collapsed state.
  - Retirement notice announced via `aria-live` with full copy + actions.
  - Welcome-back notice announced via `aria-live`.
- **Media accessibility:**
  - Video: closed captions required if the piece has spoken content; caption toggle in player controls.
  - Audio: transcript below the waveform serves as the readable form.
  - Live-call transcript: fully readable in reading order; timestamps announced with each turn.
- **`prefers-reduced-motion`:** all transitions reduce to instant; media playback remains functional.
- **Contrast:** title meets AAA (7:1). Metadata meets AA. Reading typography for text pieces meets AAA where possible. Secondary action labels meet AA. About this piece section headings meet AA.

---

## 18. State preservation

### 18.1 Playback position — recent-history persistence

**Playback position persists across sessions** for a recent-history window.

- If the customer paused a video at 3:20 last week and opens the same piece today, they see a quiet affordance: *"Resume from 3:20?"* + **[Resume]** / [Start over].
- Recent-history window: the last ~20 pieces the customer engaged with retain playback position across sessions. Older positions fade quietly.
- Text piece reading position also persists within the recent-history window (return to the paragraph the customer was reading).

Returning tomorrow to a 40-minute recording should resume where the customer left off.

### 18.2 Text size preference

Persists across all text pieces and all sessions (§12).

### 18.3 Return to entry surface

Entry surface state fully preserved (Library filter/sort/search/scroll; Home scroll; My Team scroll and section).

### 18.4 About this piece expanded/collapsed state

Per-piece within the session; not persisted across sessions (defaults to collapsed each new session).

### 18.5 Alternate takes take-navigator position

Persisted within the session; not across sessions.

### 18.6 Session lost mid-view

Silent redirect to `/sign-in`; on return, the piece opens with playback position restored.

---

## 19. Design constraints & trade-offs made explicit

**Trade-off 1 — The piece dominates; chrome is minimal.**
Cost: fewer visible actions at any moment; some customers may look for buttons that live in [More]. Benefit: the piece is presented with dignity.

**Trade-off 2 — Title is large and prominent, metadata quiet.**
Reversal of the typical "title is a header, metadata is the body" pattern. Justified because the title is the name of what the customer made — it deserves visual weight.

**Trade-off 3 — Related context is collapsed by default.**
Some customers may miss the collapsible sections. Justified because most customers don't care every time about series membership, provenance, or teammate detail. The work dominates the default view.

**Trade-off 4 — [Share] is a single action with a menu behind it.**
Cost: an extra tap to reach specific share options. Benefit: customer intent (share) is respected; mechanism is secondary.

**Trade-off 5 — Type-specific Download labels.**
More labels to maintain. Benefit: specificity reduces hesitation (*"Download video"* is unambiguous compared to a generic *"Download"*).

**Trade-off 6 — [Remix this] does not modify the original.**
Some products remix in place. We create a new alternate take to preserve the customer's finished work. Cost: a proliferation of takes if the customer remixes often. Justified because destructive editing of finished work violates the pride principle.

**Trade-off 7 — Retirement is soft with 30-day grace.**
Consistent with Library and My Team retirement patterns. Never called *"Delete."*

**Trade-off 8 — No metrics dashboard on the piece.**
No view counts, no engagement stats, no numeric readouts anywhere. Only qualitative *Popular* status (post-reveal). Justified because raw numbers create comparison and obsession.

**Trade-off 9 — Live-call records lead with summary, not transcript.**
Cost: engineering must produce reliable summaries. Benefit: the customer gets *"what happened"* before *"exactly what was said"* — matches how people actually process meetings.

**Trade-off 10 — Live-call suggested follow-ups.**
Requires Alex to synthesize suggestions from transcripts. Justified because turning memory into action is one of the strongest capabilities the product has.

**Trade-off 11 — [Turn this into a piece] with proactive suggestions.**
Alex actively proposes rather than waiting for the customer to highlight. Cost: suggestions may miss the customer's actual intent. Justified because collaborative reinforcement outweighs occasional misses; the customer can still highlight their own moment.

**Trade-off 12 — Series has a hero cover image.**
Cost: an image to manage per series. Benefit: series feels like an intentional body of work.

**Trade-off 13 — *"Alternate takes"* replaces *"versions."***
Requires vocabulary consistency across the product. Justified because customers understand creative language better than technical language.

**Trade-off 14 — Draft confidence status uses human language.**
Cost: more state labels to maintain. Benefit: draft cards communicate exactly what stage the piece is at without generic *"Draft"* obscurity.

**Trade-off 15 — Reading controls only for text pieces, only two sizes.**
Some customers may want more control (font choice, line-height, color scheme). Justified because two sizes cover the primary accessibility need without becoming a settings surface.

**Trade-off 16 — One thoughtful suggestion at the bottom, never a carousel.**
Cost: some customers may want more recommendations. Benefit: Alex-curated single suggestion feels like a thoughtful pointer, not an engagement engine.

**Trade-off 17 — Back affordance uses warm language.**
*"Back to everything you've made"* is longer than *"Back to Library."* Justified because Philosophy #6 is reinforced every time the customer leaves a piece.

**Trade-off 18 — Welcome-back on recovery is small and fades naturally.**
Cost: some customers may miss it. Justified because a big celebration would feel over-produced; a quiet welcome is more human.

**Trade-off 19 — Playback position persists across sessions in a recent-history window.**
Requires backend storage per-customer per-piece. Justified because returning to a long-form piece and starting over is genuinely frustrating.

**Trade-off 20 — Sources are shown as prose, not filenames.**
Engineering must render source references as human-language descriptions consistently. Justified because customers think about documents, not files.

**Trade-off 21 — All destructive flows include Cancel.**
Symmetric across the product. No exceptions. Justified because destructive actions are anxiety points; symmetry reinforces trust.

---

## 20. Deferred to later work

- **Visual system decisions** — player styling, typography for text pieces, [More] menu visuals, About this piece section styling, series cover treatment, reading-control visuals.
- **Motion timing calibration** — exact easing curves and durations.
- **Take comparison view** — a dedicated surface for comparing alternate takes side-by-side (deferred; individual takes are viewable separately in v1).
- **Piece-level detailed qualitative insight** — an optional Alex-voice report on how a piece is doing (deferred; must never introduce numeric metrics).
- **Series sequence editing** — customer-configurable order for series members.
- **Series with 30+ members** — virtualization and possibly condensed views.
- **Multi-language versions of a piece** — if pieces have been dubbed/translated, how takes appear together.
- **Analytics / performance reporting** — engineering + product analytics track; must remain qualitative.
- **Localization** — English only for v1.
- **Deep-linking / URL structure for pieces** — engineering.
- **Piece embed on external sites** — potential future capability, not v1.
- **Recording-to-transcript sync for live conversations** — desirable, may ship after v1.

---

## Revision History

**v1 — 2026-08-06.** First canonical version. Written and revised during the same session against operator direction. Major decisions incorporated:

- **Internal naming shift:** the surface is *"the piece"* in customer-facing language and design conversation; *"Piece Detail"* is external / documentation-only. The customer opens the piece, does not enter Piece Detail.
- **Title visual weight:** back affordance → large title → small metadata beneath. The title is the name of what the customer made.
- **Related context collapsed by default:** default surface shows only *Made with Alex →*; everything else lives under *"About this piece."*
- **[Share] replaces [Copy shareable link]:** intention-driven; the share sheet holds link, share via, and connected destinations.
- **Type-specific downloads:** [Download video] / [Download audio] / [Download text] / [Download recording].
- **[About Alex] replaces [See who made this]:** warmer; teammate byline tap opens the teammate detail view.
- **[The story behind this] replaces [See how this piece was made]:** feels like creative provenance, not audit history. Includes take navigator when alternate takes exist. Full-screen archival view.
- **[What helped Alex create this] replaces [Show me sources]:** human-first prose descriptions; never filenames primary.
- **[Remix this] safety line:** Alex says *"This won't change your original."* before the working line when Studio opens after remix.
- **Alternate-take navigation** inside *The story behind this* allows moving between takes without editing.
- **Retired pieces retain thumbnails** in the recovery view for visual recognition.
- **Raw view counts removed entirely.** Only qualitative *Popular* status (post-reveal).
- **Live-call records lead with summary**, not transcript. Transcript remains available beneath.
- **Live-call summaries include suggested follow-up** as an inline action that transitions to Studio.
- **[Turn this into a piece] with proactive suggestions:** Alex detects and offers 3 content opportunities; customer can also highlight their own moment.
- **Series has quiet hero cover image**, then description, then pieces. Feels like an intentional body of work.
- **[Stop grouping these together] replaces [Split into individual pieces]:** warmer language.
- **Series retirement has [Cancel]** as a symmetric option (Keep pieces / Retire everything / Cancel).
- **Alternate takes replace versions** in all customer-facing language (Original / Summer version / Short version / Spanish version).
- **Draft confidence exposed:** status labels are human (Needs your review / Ready to publish / Waiting on rendering / Still being finished / Still being drafted).
- **Playback position persists across sessions** in a recent-history window.
- **Reading controls for text pieces:** [A+] / [A-]; three size steps; persists across all text pieces.
- **One thoughtful suggestion at the bottom:** *"You might also like…"* — one piece, never a carousel.
- **Back affordance uses warm language:** *"Back to everything you've made"* reinforces Philosophy #6.
- **Welcome-back on recovery:** *"Welcome back."* small, human, fades naturally.
- **Trade-offs made explicit** across dominant piece framing, title weight, collapsible context, share intent, type-specific downloads, remix safety, no metrics, summary-first live conversations, proactive suggestions, series cover, warm naming, alternate takes, human draft status, cross-session playback, minimal reading controls, single suggestion, warm back affordance, quiet welcome-back, prose-based sources, and universal Cancel affordance.
