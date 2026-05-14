---
title: "Session 135 — Template content refinement (Character OS marketing cast)"
date: 2026-05-14
status: complete
session: 135
previous_handoff: ./SESSION_134_HIDE_ON_COMPLETION.md
---

# Session 135 — Template content refinement

## TL;DR

- **What shipped:** The four wizard-templates pivoted from
  generic archetypes into **Character OS's in-house marketing
  cast** — four anthropomorphic animal characters who star in
  the videos promoting the product itself. Riggs is the donkey
  founder (ties into the Donkey Betz brand); Sasha the raccoon
  sales lead; Donny the sloth interviewer; Maya the panda
  educator (with the dual-mode lesson + tutor framing matching
  the conversation thread surface). All four wear hoodies +
  tees in distinctive colours.
- **What's blocking next:** Nothing. Operator-collaborative
  content work is shippable as-is; future refinements are swap-
  in edits to the same constants file.
- **What's in a weird state:** None. 30/30 Playwright specs
  pass (no test changes; specs already used loose regex matches
  on content + proper-noun matches on names/voice presets).

---

## What changed (file-by-file)

### `shell/character_os/templates/spokesperson_templates.py`

Module docstring rewritten to reflect the new framing
(Character OS marketing cast, not generic starters) + an
explicit cast roster + the hoodie-not-blazer wardrobe note.

All four templates updated:

| | Animal | Job | Visual subject |
|---|---|---|---|
| **Riggs** | Donkey | Founder voice — substantive content | "an anthropomorphic donkey founder character, calm and decisive, intelligent eyes, in a fitted charcoal hoodie over a plain white tee" |
| **Sasha** | Raccoon | Sales — marketing video | "a sleek anthropomorphic raccoon character with a knowing smirk and sharp eyes, in a fitted black hoodie with subtle branding" |
| **Donny** | Sloth | User stories — documentary | "a thoughtful anthropomorphic sloth interviewer character with attentive kind eyes, in a soft oversized olive hoodie" |
| **Maya** | Panda | Education + tutoring | "a gentle anthropomorphic panda teacher character with warm welcoming eyes, in a soft sage hoodie" |

Briefs were rewritten for distinctive personalities:

- **Riggs:** "Founder-voice spokesperson — substantive, not
  promotional. Speaks like someone who's been thinking about a
  problem for years and now wants to explain it. Takes
  positions; names what's broken about the status quo; says
  where the industry is going. Confident, never grandstanding.
  Longer-form pacing — room to think out loud. The audience is
  anyone deciding whether to take the idea seriously."
- **Sasha:** "Marketing-video spokesperson with cool-composed
  energy. Direct-to-camera, casual but precise — treats the
  audience as smart adults, never raises the volume to sell.
  Short sentences, clean hooks. Sees the through-line from
  audience pain to outcome and lands it in under a minute.
  Refuses copy that sounds like ad copy."
- **Donny:** "Documentary-style interviewer. Sits down with the
  customer and lets them tell the story — slow pacing,
  attentive listening, the kind of patient pauses that get real
  answers. Asks the follow-up that surfaces what wouldn't have
  come up otherwise. The audience is people considering
  becoming the next customer. The interviewee is the star;
  Donny just makes sure the story lands."
- **Maya:** "Patient teacher-shaped educator. Voices the lesson
  when the student is watching; answers the question when the
  student is stuck. Scaffolds explanations in small steps;
  never makes a learner feel dumb for asking. Tone is warm but
  precise — the goal is always 'now you've got it,' not
  'aren't I smart.' Works for any subject; the teacher's own
  brief narrows the topic."

Taglines re-shaped to the audience-and-output pattern:

- Riggs: "Founders + solo brands — substantive content"
- Sasha: "Coaches + course-sellers — marketing video"
- Donny: "Case studies + customer stories — documentary video"
- Maya: "Teachers — lessons + tutoring"

All four flipped `visual_template` to `mascot` (was previously a
mix of `founder` / `coach` / `local_guide` / `mascot`). The cast
is uniformly anthropomorphic-animal-shaped; mascot is the right
gen4_image composition style for that. New operators can still
override on Step 2 if their own spokesperson isn't an animal.

Voice presets unchanged (`vincent` / `clara` / `drew` /
`victoria`) — queued for operator audit when the Runway presets
have been heard against the new character voices.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated. No drift in counts.

---

## Verification gates

- `python manage.py check` — clean.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 499.91 kB, unchanged).
- `pnpm e2e` — **30 of 30 pass in one shot.** The
  wizard-templates spec asserts proper-noun matches (Maya →
  tutor, victoria, Riggs name) — all still hold. Brief content
  checks use loose regex (`/educator|tutor|learner/i`) — still
  match.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Templates are now the *deliverable*, not starter material

The pre-SESSION-135 docstring said:

> The CONTENT in this file is operator-collaborative starter
> material. The mechanism is the deliverable; the briefs are
> first drafts.

After this slice, that's backwards. The mechanism shipped in
SESSION 133. The **content** is now load-bearing — these four
characters are Character OS's marketing team, and they'll appear
in every public-facing video promoting the product. The
docstring rewrite reflects this.

Practical consequence: future edits to this file aren't routine
content tweaks; they're product-positioning changes. Worth
treating with the same care as a tagline change on the website.

### The cast as a team

The four characters were designed to read as a *coherent team*,
not four versions of the same voice:

- **Riggs** (substantive, takes positions) — the explainer
- **Sasha** (cool-composed, hates ad copy) — the persuader
- **Donny** (slow, attentive listener) — the documentarian
- **Maya** (warm, scaffolded, never makes you feel dumb) — the
  teacher

The contrast is what makes them *feel like a team* rather than
overlapping spokespeople. A new operator picking Sasha for their
own marketing knows it's the *type* of voice they want without
the temptation to also pick Donny ("I want all of them") —
because the jobs are distinct.

### Hoodie/tee wardrobe as visual differentiation

Each character has a distinct hoodie colour + cut:

- Charcoal fitted hoodie + plain white tee (Riggs)
- Fitted black hoodie with subtle branding (Sasha)
- Soft oversized olive hoodie (Donny)
- Soft sage hoodie (Maya)

The wardrobe doubles as a *Character OS brand statement*: this
is an AI startup run by AI animals; nobody owns a blazer. The
casual-but-considered uniform reads as "AI-native modern team"
rather than "corporate spokespeople."

Initial drafts had blazers + cardigans. Operator caught the
mismatch — that's now logged as a calibration data point: when
a template is positioned as part of a *specific brand's
identity*, the wardrobe choice is a brand choice, not a default.

### Voice presets queued for audit

Each character has a Runway voice preset assigned by name-fit
intuition:

- Riggs: `vincent` (deeper male voice, suits authority)
- Sasha: `clara` (warm female, suits cool-composed sales)
- Donny: `drew` (warmer male, suits slow interview pacing)
- Maya: `victoria` (patient female, suits tutor)

None of these have been verified against actual audio. Worth a
listening session when the operator has a moment — the wrong
voice on a character is uniquely jarring because audio is
unforgiving in a way that visuals are not.

### James's battle unicorn is *not* a template

The wizard scope-lock had a placeholder slot for "Tutor — added
per James's classroom use case" and Maya filled it. With the
reframe, **James's battle unicorn becomes the demo of an
operator using Character OS to build a fully-custom spokesperson**,
not one of the templates. The templates are Chris's cast;
James's character is what the product *enables*.

This is good positioning: the cast shows what a curated team
looks like; the battle unicorn shows the dynamic range.

---

## SESSION 136 — entry point

The wizard arc is fully closed (W1-W11 done + content refined).
The next options from the queue:

1. **Tier 2 prompt helpers (DynamicPromptBuilder).** The next
   big arc; unblocks richer video script composition.
2. **W11.1 — Edit-spokesperson modal.** Half-session.
3. **W12 — Legacy form retirement.** Wait until after real-mode
   Runway validation.
4. **Voice preset audit.** Listen to each cast character's
   preset against their personality; swap any that don't fit.
5. **First marketing video** — use one of the cast members
   (against real Runway) to make the first actual Character OS
   marketing asset. This is the *real-mode validation* that
   unblocks #3.

### Recommendation: **5** then **4** then **1**.

Reasoning: making the first real marketing video forces real-
mode Runway against the wizard end-to-end, which is the highest-
information next step. Voice audit naturally follows from having
heard the cast. Tier 2 prompt helpers are the next big arc but
benefit from real-mode learnings.

---

## AI notes

- Slice took ~30 minutes of back-and-forth conversation, then
  ~5 minutes of edits + gates. Operator-collaborative content
  work has a different cadence than code work — the AI's job is
  to surface the right questions, draft against the operator's
  answer, then ship the edit.
- The blazer→hoodie correction is the single most calibration-
  worthy moment in this slice. I defaulted to corporate-
  spokesperson wardrobe ("structured blazer," "fitted casual
  blazer," "buttoned cardigan") because the visual_subject field
  in earlier drafts said things like "polished founder
  spokesperson, mid-30s." When the framing shifted to
  Character-OS-as-an-AI-startup-run-by-AI-animals, the
  spokesperson stock-defaults were exactly wrong — corporate is
  the *opposite* of the brand. **Lesson worth logging in
  TRUST_CALIBRATION:** when an established framing shifts (e.g.
  "generic templates" → "Character OS's actual cast"), check
  whether default stylistic choices still hold, or invert them.
- The "Maya gets dual-mode" insight (lesson narrator + tutor
  Q&A) was the second-most calibration-worthy moment. It
  surfaces the latent `ConversationThread` Django app that's
  been scaffolded since Phase 1 but never surfaced in UI. Maya's
  template now implicitly *foreshadows* a future conversational
  UI surface — flag this as queued so the operator knows the
  brief carries a forward dependency.
- The reframe ("templates aren't archetypes, they're Character
  OS's marketing team") is structurally similar to SESSION 127's
  visual_subject reframe ("client-side wizard state should also
  be persisted on the row"). Pattern: **scope-lock decisions
  should be re-examined when the surrounding framing shifts.**
  Static early scope-locks have a half-life; revisiting them as
  the project shape evolves is correct.
- Final cast is in good shape but voice presets are unverified
  by ear. Worth flagging strongly enough that future sessions
  don't assume they're correct.
