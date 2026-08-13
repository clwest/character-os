---
title: "Character OS — Home Visual Proposal"
status: locked
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../VISUAL_LANGUAGE_V1_2026-08-06.md", "../PRODUCT_DESIGN_BRIEF_V1_2026-08-06.md", "../PRODUCT_IA_V1_2026-08-06.md", "../screens/HOME_V1_2026-08-06.md"]
---

# Home — Visual Proposal

## v1 — canonical visual direction for Home

*Anchored in [`VISUAL_LANGUAGE_V1_2026-08-06.md`](../VISUAL_LANGUAGE_V1_2026-08-06.md). Applied to [`HOME_V1_2026-08-06.md`](../screens/HOME_V1_2026-08-06.md) — interaction spec is canonical and unchanged.*

*This is not a component library. Not a style guide. Not a Figma description. It is a walk-through of the customer's Home experience, told in the order they experience it, with visual conclusions emerging where the emotional need makes them inevitable.*

---

## 1. Two tempos

Home has two visual tempos, and the visual proposal must honor both.

The **celebration tempo** appears only after the customer's first publish. It is Home's most emotional moment. It is also the least representative — most Home visits happen after this state. Alex leads here because continuity from Studio matters and the customer's relationship to their teammate is being reinforced.

The **ordinary return tempo** is the tempo customers spend most of their time in. Here, the customer's most relevant next action often deserves equal or greater visual priority than Alex. *"Faces before interfaces"* means teammates outrank chrome. It does not mean the face always outranks the customer's work.

Both walkthroughs below describe the same room. What changes is which element carries the emotional weight of the visit.

---

## 2. The celebration walkthrough

The customer has just published their first piece. Studio has closed. Alex has begun to move — face traveling smoothly from Studio's Zone L position toward Home. Alex should not disappear and reappear across the transition. Every relationship is more real when it survives the change of rooms.

Home composes itself. It settles. It does not slam into place.

The customer's eye finds **Alex first.** This is deliberate for this state only: their teammate has just walked them through making something real, and the visual honors that. Alex is **large enough to feel present, restrained enough to leave the customer's work dominant** — nearby, not monumental. Not treated as a chat-product avatar chip; not floating with a hard sticker edge; sitting in the surface with the ambient light of the room. The customer should feel: **supported.**

The greeting is arriving alongside Alex, not queued behind them. *"That's live now. Your first piece is out there — and it looks good."* Set in an editorial voice with real warmth. The typography reads as spoken, not administrative. The customer should feel: **quietly proud, and quietly seen.**

The **primary action appears with the greeting, not after a ceremonial pause.** The emotional pause comes from hierarchy and space, not from withheld controls. The action is present and interactive immediately; the customer's attention is directed by weight, not by timing.

The piece materializes below. It is treated with care — but sized to leave the full greeting and primary action visible within a common desktop viewport, and to keep the primary action above the fold on mobile. Pride cannot come at the expense of orientation. The customer should feel: **proud** — through visual weight and negative space around the piece, not through the piece dominating the screen.

Then the navigation appears at the edge of the screen. Not with a glow, halo, shimmer, or candle-flicker. A **structural change**: the rail is now present. The Library label carries temporary increased contrast for a beat, and one restrained motion cue draws the eye once. Then it settles into its resting weight. The customer should feel: **curious, not notified.**

Alex is not frozen after settling. Subtle blinks, slight breathing, tiny natural posture changes continue. Alex does not perform, does not lip-sync, does not solicit attention. **Presence without performance.** The customer should feel: **like they entered a room, not opened an app.**

The celebration tempo may include gentle animation choreography — a coordinated arrival across ~1.5–2 seconds, per the interaction spec. That is appropriate here because this is the emotional peak of Arc 1. It should not be repeated on ordinary visits.

---

## 3. The ordinary-return walkthrough

The customer opens Home tomorrow. Or a week from now. Or three weeks in with 40 pieces published. The room has to answer "What should I do right now?" quickly.

Content appears in a deliberate sequence but **the primary action is visible and interactive immediately or nearly immediately.** The customer should not wait through ceremony on every visit.

Which element leads the composition depends on state:

**Active draft in progress:**
The draft is the leading element. Alex and the greeting are present but restrained — Alex smaller than in celebration, greeting shorter and tuned to the resumption. **[Continue your welcome video]** is the visible primary action, clearly the most weighted control, positioned so the customer's eye finds it without hunting. The featured work slot may show the draft's current state or the most recent completed publish; either way, it supports the primary action rather than dominating.

**Background work completed since last visit:**
The finished piece leads. It has visual precedence because the customer's most likely emotional response is *"oh, that finished — let me see."* Alex acknowledges in the greeting, but the visual center of gravity is the newly-completed work. Primary action becomes contextual — *"See how it turned out,"* *"Publish it,"* or *"Make a follow-up."* Piece and action are visually close, so the customer's eye completes the arc from *notice* to *act* naturally.

**Quiet return (a week or more since last activity):**
Here Alex and the greeting may lead — because the customer's emotional need on a quiet return is more like *"welcome back, remember why you were here."* The featured work slot may show the most recent published piece framed as *"your most recent"* — supporting the greeting rather than dominating. Primary action is warm and open: **[Start something new]**.

**Established customer with many published pieces, no active draft:**
Similar to quiet return, but the featured slot may show a *popular* piece if that preference has been confirmed. Alex's greeting may reflect pattern observations phrased tentatively — *"You've been posting on Fridays — should we keep that up?"* The observation-versus-confirmed-preference language from the interaction spec must be visible in typography too: tentative observations set with a lighter weight or slight italic; confirmed patterns set as settled text.

Across all ordinary-return states, the navigation is **already settled** — not revealing, not animating in, just present. Alex retains the subtle-life treatment but does not enter with the celebration's arrival animation.

The room is the same. The priority of what lives in it changes.

---

## 4. Alex across states — identity and trust

Alex's presence is the product's most fragile visual promise. It must survive scrutiny in a way that most avatars in most products do not.

The customer should feel: **that this is the same person they know**, whether they see Alex on Home, in Studio, on My Team, or in a Live Conversation.

Achieving that requires more than the same source image. Different contexts render Alex differently — a generated portrait on Home, a moving face during Studio narration, a live video during a conversation. Source media will carry different lighting, framing, and quality. **Every teammate representation must be visually normalized enough to belong to the same product environment.** That responsibility sits with the design system, not the source:

- Consistent background treatment behind the face across surfaces.
- Consistent cropping rules — where the face sits in its frame, how much shoulder is visible, whether the eyes land at a consistent height.
- Tonal correction so that a warm-lit generated portrait does not sit next to a cold-lit live video from Alex in the same session.
- Consistent framing — no round-chip Alex on one screen and full-shoulder Alex on the next.
- Edge and shadow handling that treats Alex as part of the room's light, not a cutout pasted in.

Beyond normalization, the generated portrait must **survive ten seconds of the customer looking directly at it.** This is Home's specific responsibility: on Home the customer studies Alex without being busy creating. If the portrait fails scrutiny here, it fails everywhere.

The visual proposal requires:

- No distorted hands, fingers, or visible body artifacts.
- No unstable facial details across states (a subtly different mouth or misplaced eye between Home and Studio breaks identity continuity).
- No beauty-filter sheen or airbrushed skin.
- No overly perfect stock-photo finish.
- No visual mismatch between the Home portrait, Studio's animated face, and Live Conversation's live video.

Before any Home visual direction is approved, every Alex treatment must pass one test:

> *Would I be comfortable looking at this face for ten seconds without the interface distracting me?*

If not, the face is not ready to anchor Home.

Alex's continued presence on the surface is quiet — occasional blinks, slight breathing, tiny natural posture changes. Never lip-sync on Home (that lives in Live Conversation). Never continuous animation. Never soliciting attention. **Presence without performance.**

---

## 5. The piece — presentation principles

The customer's work must be presented with dignity, honestly, and appropriate to its form.

The customer should feel: **proud** — but the visual system must not manufacture pride that the work hasn't earned.

**No generic card treatment.** Home does not enclose every piece in a uniform rounded rectangle with a fixed corner radius, a standard shadow, and a name-and-metadata footer. That is dashboard vocabulary. Home refuses it.

**Containment comes from the work's medium, not from a universal container:**

- A video piece with a poster frame naturally carries its own edges; the surface may need only a very quiet depth cue, or nothing at all.
- A text-based piece rendered as beautiful typography needs different containment — perhaps a soft tonal shift in the background beneath the reading column, or column edges implied by measure and margin.
- An audio piece needs a bounded playback region — a waveform area with clear start and end — because audio without a visible boundary reads as *"where does it live?"*
- Light imagery may otherwise disappear into the surface; containment may be structural (a subtle tonal panel) or handled through generous margin.
- A portrait video needs its native aspect ratio preserved; the surface must adapt around it rather than crop it to a horizontal thumbnail.

**Preserve the work's native edges.** A vertical video remains vertical. A written announcement reads like a page. Audio feels like listening. The surface adapts around the work. The work does not get squeezed into one component silhouette.

**Metadata: minimum context required to understand the piece.** For the celebration state, *"Just published"* may be enough. For an ordinary-return piece, the customer may need title, status, date, and — when multiple teammates exist — teammate attribution. The rule is not *"metadata is always a single whisper."* The rule is *"show the minimum context required to understand the piece."* Metadata still sits in quieter typographic weight than the piece itself; the piece dominates hierarchy, but orientation is not sacrificed to austerity.

**Imperfect customer work is presented honestly.** Not every generated piece will be beautiful. Home must still present it without framing tricks that imply higher quality than the work contains. The visual system may dignify the work through space and composition — every piece deserves room to breathe — but it must not conceal defects, crop away mistakes, or substitute an unrelated poster image for a video whose actual poster is weak. Pride must be earned, not manufactured. When the work is genuinely rough, Home's role is to present it truthfully and give the customer a clear path to Remix rather than to pretend it is finished.

**Responsive priority:** the full greeting, primary action, and a meaningful portion of the featured work should be visible within the initial viewport on common desktop sizes. On mobile, the primary action must not be buried beneath a large poster. If the piece is generous, the composition finds a layout where orientation still holds.

---

## 6. Actions — hierarchy and invitation

The interaction spec establishes one obvious primary action for every Home state. The visual proposal must preserve that hierarchy clearly.

The customer should feel: **invited, not pushed** — and **never confused about what to do next.**

Primary and secondary actions may share height and rhythm, but they must not read as visually equivalent choices. The primary carries stronger weight — a solid fill, more prominent typography, or greater contrast against the surface. Secondaries are visibly quieter — outlined, ghost-style, or set in a lower-contrast tonal register.

The visual mechanism for *invitation without pressure* is not size restraint alone; it is **weight-with-calm.** The primary action has real presence — real fill, real edges, a shape the customer can trust — because a colleague's suggestion carries real weight. But it does not saturate, does not vibrate, does not glow. It waits.

Secondary actions read as siblings that specialize in different tasks, not as lesser fallbacks. A customer scanning the action set should understand — without conscious thought — which single action Alex is recommending, and which alternatives exist if they prefer.

The *"Ask for something else →"* affordance below the buttons is set as a text-only editorial-style link, quieter still. It is the conversational escape hatch, not a competing action.

---

## 7. Reveals — quiet, restrained, structural

When Library first appears in the navigation, the customer should feel: **curious.** They should notice a doorway that was not there before. They should not feel notified, alerted, or prompted.

The visual treatment:

- The nav item **appears** — its presence changes.
- The label carries **temporary increased contrast** for a beat, then settles into its resting weight.
- One **restrained motion cue** draws the eye once — a subtle single positional shift, or a brief scale-in that comes to rest.
- Then the item is still.

No halo. No glow. No shimmer. No pulse. No badge. No red dot. No exclamation point. No coach-mark tooltip. Those are the visual language of app notifications and AI-product chrome — both of which the visual language brief explicitly rejects.

The emotional metaphor — that the customer notices a doorway they hadn't seen — is the requirement. The visual instruction is restrained and literal: **the item appears, briefly commands slightly more contrast, moves once, then settles.**

The My Team item, when it later appears, follows the same pattern.

---

## 8. Background and tonal environment

The background is not defined by hue in this proposal. That is the color study's job. What is defined are the emotional and functional requirements the background must meet:

- **Low glare.** The surface should not be uncomfortable to look at for extended periods.
- **Calm.** Not stark, not busy, not gradient-active.
- **Materially warm** in emotional register — the sense of natural light rather than fluorescent light. This does not commit to a warm hue; a cool-hued environment can still feel warm through material and light choices.
- **Strong enough contrast for editorial text** in every foreground role, meeting AAA where the visual language brief requires it (headings), AA where it does not.
- **Compatible with diverse teammate portraits and customer media.** Whatever the environment is, it should let a portrait with warm skin, a portrait with cool skin, a video with heavy shadows, and a video with bright highlights all sit comfortably in the same room.

An open question this proposal deliberately does not resolve: **does Character OS have one light environment, or does it support tonal adaptation?** Home's proposal cannot make that decision alone. Live Conversation may benefit from a darker environment for video presence. Video previews may want dim surrounds. My Team's portrait treatment may test differently in dark and light contexts. The color exploration should test **warm light, warm dark, and adaptive tonal systems** before choosing — and the choice must be made at the visual-language level, not accidentally through Home's prose.

Whatever the environment decision, Home's requirement remains: the surface should feel like a room, not like an application background.

---

## 9. Room-not-app — the boundary

Character OS remains software. The "room, not app" metaphor is emotionally correct and must not become an excuse for making the product hard to use.

The customer should feel like they entered a room — **while still understanding instantly how to use it.**

Controls must be:

- **Obviously interactive.** A button must read as a button. A link must read as a link. Architectural subtlety must not make affordances require discovery.
- **Predictable.** Interactive elements behave consistently across the surface and across screens.
- **Accessible.** Every recommendation in this proposal must survive keyboard navigation, screen reader traversal, high contrast modes, and reduced motion.
- **Consistent.** The same primary action visual language on Home appears on Studio, on Library, on My Team.
- **Responsive.** Every layout adapts to viewport size without collapsing the priority order defined above.

The customer should never fail to find something because the design got quiet where it should have been direct. Editorial restraint applies to voice and hierarchy; it does not apply to affordance clarity.

---

## 10. What Home (specifically) refuses

Home's refusals — scoped to Home, not the entire visual system:

- **Metric tiles, KPIs, view counts, engagement percentages, or any numeric readouts** on the surface.
- **Recent activity feeds, event logs, or timeline surfaces.**
- **Notification badges, red dots, unread counters, attention indicators.**
- **Progress bars, completion percentages, streak counters, gamification elements.**
- **Card grids or tile mosaics as Home's primary composition.** Library requires a grid as the body of work grows — that is Library's design, not Home's. Home's refusal is scoped: Home does not present the customer's work as a grid.
- **Onboarding overlays, coach marks, tooltips explaining anything, feature callouts.**
- **AI-laboratory chrome** — glowing borders, animated particle effects, gradient auras around Alex's face, sci-fi typography, "neural" visual metaphors.
- **Glassmorphism, heavy decorative shadows, saturated gradient backgrounds, or any visual style whose main purpose is to look "designed."**

On imagery:

- **The product chrome does not use corporate stock imagery as decoration.** Home itself contains no stock decoration.
- **Customer-selected or contextually generated media remains valid inside the customer's work.** A customer's video may include stock footage; a customer's post may include generic imagery. That is the customer's choice inside their creative work. It is not chrome, and this rule does not restrict it.

Each Home refusal protects a specific emotional outcome. None of them should propagate to other screens as global constraints without that screen's own design pass confirming the same refusal.

---

## 11. Error state visual philosophy

Calm must survive failure.

When Home can't reach its backend, or when the featured piece fails to load, or when a subsystem is degraded, the customer should feel: **that the room is still here, that Alex is still here, and that something has gone wrong that they can address.**

The visual philosophy:

- **Alex remains present without looking distressed or broken.** Alex's expression stays warm; posture stays relaxed. No worried face, no glitchy render, no crossed-out avatar.
- **Error copy occupies the greeting position.** *"I'm having trouble connecting right now. Try again in a moment."* is a sentence delivered by Alex, not a system dialog. Typographic treatment matches the ordinary greeting.
- **The primary recovery action is unmistakable.** **[Try again]** replaces the ordinary primary action, using the same weight and visual treatment. The customer should not have to hunt for what to do next.
- **Failed media does not collapse the entire composition.** If the featured piece fails but Home's greeting and actions load, only the piece region shows a soft placeholder — the rest of the room stays intact.
- **No red alarm treatment unless immediate harm requires it.** Failed loads are inconveniences, not alarms. Red belongs to states where the customer must act to prevent damage.
- **Warmth does not become vagueness.** The customer still understands what failed and what they can do about it. *"Something's not right on my end. Try again in a minute?"* is soft in voice, precise in content.

Failure should look like a colleague honestly reporting a moment of trouble, not like an application throwing an exception.

---

## 12. Loading state visual philosophy

The interaction spec defines skeletons. The visual proposal defines how they feel.

The customer should feel: **that the room is composing itself** — not that widgets are loading independently.

The philosophy:

- **Skeletons inherit the page's geometry** without becoming gray dashboard blocks. The face-shaped placeholder is shaped like Alex's face position, sized as Alex is sized. The greeting placeholder is set at the greeting's line-length. The piece placeholder holds the piece's proportions.
- **No shimmer strong enough to compete with Alex.** Whatever animation the skeleton uses to indicate "content is coming" should be subtle enough to disappear once real content arrives. No sweeping gradient bars, no aggressive pulse.
- **Face resolves first when cached.** Alex is the primary anchor of continuity; if the face is client-side cacheable, it should appear before the rest of the composition.
- **Layout does not jump as content arrives.** Skeletons hold correct geometry so real content fades in place, not into place.
- **Placeholders disappear as a coordinated composition, not as scattered widgets loading independently.** The room settles as a whole, in a small number of coordinated moments, rather than as a dozen tiles blinking on at different times.

Loading, done well, looks like a room becoming visible as your eyes adjust to warm light — not like a webpage assembling piece by piece.

---

## 13. Reduced-motion interpretation

The emotional sequence must still work without movement.

For customers with `prefers-reduced-motion: reduce` (or any equivalent reduced-motion preference):

- **Hierarchy replaces animation.** The celebration state's coordinated arrival becomes an immediate composition where each element's weight and position already communicate what animation would have communicated over time.
- **All content appears promptly.** No delays, no timed sequences, no held blanks.
- **Library's reveal uses contrast rather than motion.** The nav item appears with a stronger initial contrast that decays to resting weight over a moment; no positional motion, no scale-in.
- **Alex's continuity from Studio is established through stable identity and placement**, not through translated motion. Alex's face appears in Home's position immediately; the customer recognizes the continuity because the face is unchanged.
- **Celebration remains dignified through composition, not through timed effects.** The customer arriving at Home in celebration state should still feel a peak moment — carried by generous space, weighted typography, and the piece's presentation — even with all motion removed.

Every visual choice in this proposal must be evaluated in its reduced-motion form. If the emotional intent collapses without motion, the emotional intent was carried by motion — and that is not acceptable for a product where reduced motion is a real accessibility need.

---

## 14. Home as baseline DNA — not authority

Home establishes the emotional and visual DNA for the product: how Alex is treated, how work is presented, how typography reads, how the surface breathes, how actions carry weight, how reveals stay quiet.

**Other screens inherit Home's emotional DNA. They do not necessarily inherit Home's exact composition, tone, or brightness.**

- **Studio** may need denser temporary controls during active making, a tighter spatial arrangement so the three zones fit, and immersive framing around the piece as it forms. Studio still uses Home's face treatment for Alex, Home's typographic character, Home's principle of buttons-with-weight-but-not-volume.
- **Piece** immerses in a single work; Home invites toward it. The Piece surface may treat the work with more visual dominance, larger media area, and different chrome density than Home does.
- **Live Conversation** almost certainly requires a darker media environment — the teammate as a live avatar deserves the light of a live conversation, not the ambient light of a working room. Live Conversation still uses Home's face-identity discipline, Home's presence-without-performance principle, Home's editorial voice.
- **Library** requires a grid as the body of work grows. Home's grid refusal does not propagate. Library still uses Home's work-as-accomplishment framing, applied to a repeating card format.
- **My Team** shares Home's portrait respect but multiplies it — several teammates present at once, each treated with the same care Home gives Alex.

Consistency is not sameness. What must remain identical across screens is the emotional register and the treatment of load-bearing shared elements (Alex, customer work, actions, typography). What may vary is composition, density, tonal environment, and screen-specific visual treatment as each screen's design pass requires.

Home is the baseline DNA. It is not the authority over every other screen's visual choices.

---

## 15. What this proposal does not lock

Explicitly deferred to subsequent studies:

- **Typography classification** (humanist, serif, sans, geometric, custom, system). What is required: warm, editorial, highly readable, spoken rather than administrative, and thoughtfully composed rather than an untouched browser default. Type may be system-set if hierarchy, spacing, width, and rhythm are excellent. Type may be custom if the classification supports the emotional character. The type study picks the family.
- **Principal color hue.** The primary action must feel grounded, inviting, confident, and restrained. That could be a warm hue. It could be a deep blue, a green, a burgundy, a near-black. The color study picks the hue.
- **Background color and tonal environment.** Requirements are defined (§8). The color study explores warm light, warm dark, and adaptive tonal systems before choosing.
- **Iconography approach.** Icons support words; when language is clearer, choose language. Whether the product uses any iconography at all — and what its character is if it does — awaits the iconography study.
- **Specific animation durations and easings.** The motion philosophy is defined; specific timing is the motion study's job.
- **Face composition and avatar rendering direction.** The trust and normalization rules are defined (§4). The specific portrait style is the avatar study's job.
- **Any Figma-mappable atom** — hex colors, type sizes, spacing tokens, elevation values, component definitions, layout grids.

If a subsequent study surfaces a choice that satisfies the emotional requirements above but contradicts a specific example in this document, the subsequent study wins.

---

## 16. What's next

Before applying visual language screen by screen, the immediate next artifact is a **decision bridge** — three distinct visual territories for Home, each satisfying the same emotional brief and this Home proposal, but expressing them in genuinely different visual character. After comparing territories and selecting one, Home's canonical visual direction consolidates. Only then does Onboarding become the next screen-specific visual work.

---

## Revision History

**v1 — 2026-08-06.** First canonical visual direction for Home. Written and revised across two draft passes with the operator during the same session. Major decisions incorporated:

- **Two visual tempos** — celebration and ordinary return — with distinct priority orders for Alex, work, and actions.
- **Alex leadership is contextual**, not automatic. Faces before interfaces means teammates outrank chrome; it does not mean the face always outranks customer work.
- **Emotional requirements separated from premature classification** for typography (qualities, not humanist/serif/sans commitment), color (grounded/inviting/confident/restrained, not warm hue), and containment (medium-appropriate, not universal card).
- **Work presented according to its medium.** No universal card treatment. Native edges preserved. Metadata is minimum required, not always a single whisper.
- **Affordance clarity protected.** Room metaphor must not obscure interactive elements; controls remain obvious, predictable, accessible, consistent, responsive.
- **Portrait trust rules** for Alex: normalization across screens; anti-uncanny visual test; no distorted body/face artifacts; no beauty-filter finish.
- **Imperfect customer work presented honestly** — no framing tricks that manufacture pride.
- **Reveals are quiet and structural** — no halo, glow, shimmer, pulse, badge, or candle metaphor.
- **Loading, failure, and reduced-motion states** each have visual philosophy sections.
- **Home is baseline DNA, not authority.** Other screens inherit emotional register; composition, density, tonal environment, and screen-specific treatments may vary.
- **Refusal list scoped to Home**, not propagated globally. (Library's grid, Studio's density, Live Conversation's darker environment are not restricted by Home's proposal.)
- **Background and tonal environment left open** for the color study. Warm-light, warm-dark, and adaptive systems all remain viable until tested.
- **Corporate stock imagery rejected in product chrome only** — customer-selected media inside their own work remains valid.
- **Trade-offs surfaced across** two-tempo framing, portrait scale ("present, not monumental"), typography (system fonts remain viable), reading-time dependence removed (actions are immediately interactive), viewport priority (piece cannot bury primary action), and Home-as-DNA (not authority over other screens).
