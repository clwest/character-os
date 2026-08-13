---
title: "Creator Content Studio — scope lock (product doctrine)"
status: active (ratified 2026-08-05, implementation queued)
generated: 2026-08-05
ratified: 2026-08-05 (operator, this session)
companion_docs:
  - "JOB_ONE_V1.md"
  - "CHARACTER_OS_WHAT_IT_IS.md"
  - "../../../docs/AI_CREATOR_READINESS.md"
  - "../CUSTOMER_ZERO_DOGFOOD.md"
phase: doctrine (above phases)
---

# Creator Content Studio

> **Read first:** `JOB_ONE_V1.md` (Character OS's core weekly
> promise, unchanged by this doctrine) and the workspace-level
> `docs/AI_CREATOR_READINESS.md` (which frames the Character-OS-
> as-Customer-Zero operating mode this doctrine serves).

---

## Purpose

Creator Content Studio is a doctrine for a **distinct operating
mode**, not an extension of Job One. It defines the recurring
responsibility Character OS carries when the operator is running
one persistent AI Creator whose purpose is to build an audience
through daily multi-format content.

Job One remains unchanged: *one weekly angle → one delivered video
for a small-business customer with minimal decisions.* Creator
Content Studio serves a different customer, a different cadence,
and a different unit of output. The two doctrines are peers.

### Why a separate doctrine

`JOB_ONE_V1.md` contract rule 8 permits, and explicitly names,
adding a second recurring job with its own doctrine rather than
expanding Job One in place. This doc is that pattern.

Job One's customer is a solo/small-business owner who opens
Character OS once a week for under fifteen minutes and closes it
with one polished video. Creator Content Studio's operator is the
Character OS team itself (Chris as Customer Zero), building an
audience for Character OS via one persistent public creator that
publishes daily across multiple text and video surfaces.

Confusing these two would either bloat Job One past its
promise-bounded shape or push the multi-format creator loop into
the wrong constraints (weekly cadence, one artefact, fifteen-
minute customer attention). Keeping the doctrines separate keeps
both honest.

---

## The Job

**One idea from the operator becomes one coherent daily content
package, adapted for the channels the operator chooses.**

Six adaptations of one idea, not six unrelated pieces and not six
paraphrases of the same paragraph. The operator supplies one idea
and one Creator; Content Studio does the rest.

Initial Customer Zero package (v1, six formats):

1. **SHORT_VIDEO** — a short-form spoken script suitable for
   TikTok, Instagram Reels, and YouTube Shorts.
2. **LINKEDIN** — one useful professional observation.
3. **X** — one concise, opinion-led post or short thread.
4. **INSTAGRAM** — one caption appropriate to the accompanying
   visual/video.
5. **BLOG** — one useful standalone article.
6. **NEWSLETTER** — one draft with subject, preview text,
   opening, central lesson, and close.

---

## Definition of Complete

A single Content Studio package is **complete** when, and only
when, all of the following are true:

1. One `ContentPackage` row exists, anchored to a Creator
   (`Spokesperson`) and the operator who submitted the idea.
2. Six `ContentOutput` rows exist under the package, one per
   `content_type`, each with body text.
3. Each output is materially adapted to its format — not the same
   prose truncated or expanded.
4. Every output was generated using the Creator's structured
   identity slots + persona-scoped knowledge retrieved for that
   Creator only (no cross-persona bleed).
5. The operator can, from a single UI surface: read the package,
   edit each output, save edits, regenerate one output
   independently of the others, copy the text, and download the
   text as Markdown or plain text.
6. Package-level approval is a single action ("Approve all" or
   "Ready to use"); six individual approvals are not required to
   reach a useful state.
7. For the SHORT_VIDEO output, an "Approve short video" action
   creates the smallest compatible bridge into the existing
   render pipeline (Job One's Script → talking_head path) without
   asking the operator to visit the Scripts page or the Recipes
   gallery.
8. **A rendered MP4 is not a completed Content Studio
   deliverable until the operator visually reviews and accepts
   it.** A "processed" status on a Composition row is
   necessary but not sufficient.

Anything short of items 1–7 is a partial package; item 8 gates
the video sub-deliverable specifically.

---

## Non-goals

Explicit. If a proposal falls under any of these headings, it is
not part of Creator Content Studio v1.

1. **Not Job One.** Job One's promise, cadence, and non-goals are
   unchanged by this doctrine. Any argument that Content Studio
   "is Job One with more outputs" is a category error.
2. **Not automatic publishing.** No OAuth into social platforms,
   no scheduled posts, no direct upload adapters. Publishing is
   the operator's job for this slice.
3. **Not scheduling.** No content calendar, no next-post-due
   timers, no cadence enforcement. Cadence is the operator's job.
4. **Not autonomous topic discovery.** No trend watchers, no
   background angle generators, no signal aggregators. The
   operator supplies each idea.
5. **Not engagement analytics.** No view / like / share / follow
   capture, no funnel model, no dashboard.
6. **Not creator-performance memory.** No "what worked last week
   influences this week's package" loop.
7. **Not blog hosting.** BLOG outputs are Markdown drafts the
   operator can copy or download; Character OS does not run a
   blog CMS.
8. **Not newsletter sending.** NEWSLETTER outputs are drafts the
   operator can copy or download; Character OS does not send
   email.
9. **Not a second video system.** SHORT_VIDEO renders through
   the existing Job One Script → talking_head path. Content
   Studio does not duplicate the video pipeline.
10. **Not a redesign of Spokesperson, Knowledge, Scripts, or
    Recipes.** Those surfaces remain as-is during this slice.
11. **Not a redesign of the portrait/avatar system.** F-DGF-016
    (uncanny-valley content-quality finding) is *scoped-around*,
    not solved here.
12. **Not a sibling-project port.** No `a sibling private project` code moves in.

---

## Contract rules (load-bearing)

These bind every Creator-Content-Studio design decision the same
way `JOB_ONE_V1.md`'s rules bind Job One decisions. Any conflict
is resolved in this doctrine's favor within its own scope, and
never against Job One outside its scope.

1. **The unit is one package.** One submitted idea produces one
   package. Six outputs are one delivery, not six deliveries.
   The operator does not submit six ideas to get six packages;
   they submit one idea to get one adapted package.

2. **Package-level approval is the default.** A single
   "Approve all" or "Ready to use" action reaches the useful
   state. Per-output edit / regenerate / approve are opt-in
   affordances the operator uses when a specific output falls
   short. Six mandatory approvals is a design defect.

3. **Six outputs are adaptations of one core angle.** A single
   package-level `core_angle` is derived first and constrains
   every format. Outputs may not disagree on the central
   insight, factual claims, audience, or boundaries. Outputs
   may — and should — differ in structure, rhythm, register,
   hook, and closing per format.

4. **Persona consistency binds the package.** Every output uses
   the same Creator's structured identity slots
   (`who_you_help`, `what_you_sell`, `always_emphasize`,
   `never_say`, `desired_feeling`, `business_brief`,
   `personality`, `tone_archetype`) and the same persona-scoped
   knowledge retrieval. Retrieval isolation (per
   F-DGF-015 evidence) holds: another Creator's knowledge does
   not leak into this package.

5. **Each format follows its own conventions.** SHORT_VIDEO is
   written for spoken delivery; LINKEDIN reads as a professional
   observation; X is opinion-led and compact; INSTAGRAM is a
   caption for accompanying visual; BLOG is a standalone article
   with headings; NEWSLETTER has a subject, preview, opening,
   lesson, close. Do not truncate one prose block six ways.

6. **The customer-facing UI uses customer-facing language.**
   Words that do not appear in Content Studio surfaces: `K2`,
   `K6`, `Composition`, `Recipe`, `Primitive`, `Provider`,
   `Runway`, `OpenAI`, `pgvector`, `embedding`, `chunk`,
   `Serper`, `Celery`. Words that do: *idea, package, output,
   Creator, edit, regenerate, copy, download, approve, render*.
   The "Render with Tulsi" button (and its Creator-name
   variants) is the only surface where the render bridge is
   exposed; it never says "Create Script", "Fire Composition",
   or "Open Recipe".

7. **The video bridge reuses the existing pipeline.** The
   approved SHORT_VIDEO output creates the smallest compatible
   record required by the existing Script + talking_head path
   (Job One's mature substrate). Content Studio does not build
   a second video pipeline. If the bridge requires a schema
   change to the mature Script model, prefer instead to hold
   the FK on the Content-Studio side (`ContentOutput ↔ Script`),
   so the experimental doctrine depends on the stable one and
   not the reverse.

8. **A rendered file is not a deliverable until the operator
   visually accepts it.** The pipeline completing (`status =
   processed`) is a necessary condition, not a sufficient one.
   A per-render visual-accept step is required before the
   SHORT_VIDEO output can be marked "delivered". This is the
   direct doctrinal consequence of F-DGF-016 (photorealistic
   human render uncanny-valley finding).

9. **Any existing Creator kind is permitted.** Photorealistic
   humans, animals, robots, mascots, and stylized figures are
   all valid Creators for Content Studio. The first public
   house Creator may be non-human without any doctrine
   exception. Content Studio does not require photorealistic
   human appearance.

10. **Scope stays small until runtime evidence forces expansion.**
    The six-format v1 package, package-level approval default,
    three-call generation experiment, and single `/workspace/content`
    surface are the boundaries. Adding a seventh format, a
    scheduling surface, a publishing integration, an analytics
    capture, or a performance-memory loop requires a
    `CREATOR_CONTENT_STUDIO_V2` amendment ratified by the
    operator with a `SESSION_NNN` handoff.

---

## Format contracts

Verbatim from the operator's scope-lock prompt (2026-08-05).
These bind the generator's output shape per format.

**SHORT_VIDEO**
- Spoken, conversational language.
- Written for 30–60 seconds of spoken delivery.
- Immediate hook.
- Short beats rather than essay paragraphs.
- One opinion or insight.
- One concrete example where possible.
- Memorable closing.
- No generic "Hey, I'm..." opening by default.
- No automatic Character OS sales pitch.
- No LinkedIn prose read aloud.

**LINKEDIN**
- Useful professional observation.
- Readable paragraph rhythm.
- Enough substance for discussion.
- Not a transcript.

**X**
- Concise, sharp, opinion-led.
- One post or short thread only where justified.
- No bloated hashtag block.

**INSTAGRAM**
- Caption appropriate to the accompanying visual / video.
- Conversational.
- Optional compact hashtag set.
- Not a duplicate of LinkedIn.

**BLOG**
- Useful standalone article.
- Headings.
- Developed reasoning and examples.
- No filler added merely to make it long.

**NEWSLETTER**
- Subject.
- Preview text.
- Conversational opening.
- One central lesson.
- Useful close.
- Not the blog pasted into an email template.

---

## Generation strategy (default; adjust only under runtime evidence)

Three named LLM calls, not seven.

- **Call 1 — Core angle.** Derive core angle, audience tension,
  central opinion, factual grounding, and content objective.
  Input: Creator identity + persona-scoped knowledge + idea (+
  optional objective).

- **Call 2 — Short-form batch.** In one validated structured
  response, generate SHORT_VIDEO, LINKEDIN, X, and INSTAGRAM
  outputs from the shared core angle.

- **Call 3 — Long-form batch.** In one validated structured
  response, generate BLOG and NEWSLETTER outputs from the same
  core angle plus enough context to prevent generic expansion.

Splitting to six independent format calls is permitted **only
after runtime evidence** shows the batched calls produce
materially worse quality or unreliable structure.

Independent regeneration (operator asks Content Studio to
regenerate one output only) may use a format-specific single
call, holding the package's `core_angle` constant.

Every call must be:

- named (one of `derive_core_angle`, `generate_short_form_batch`,
  `generate_long_form_batch`, `regenerate_<format>`);
- attributable to a `ContentPackage` (and, for regeneration, to a
  `ContentOutput`);
- cost-logged (via existing `LLMCallLog` or equivalent);
- token-bounded per call;
- visible in the ledger's runtime evidence for verification.

---

## Domain model (minimum honest shape)

Two models. `ContentIdea` is not modeled separately unless
repository evidence proves one submitted idea must exist without
producing a package.

**ContentPackage**
- `workspace` (FK)
- `spokesperson` (FK — the Creator)
- `idea_text`
- `objective` (nullable; enum: `teach` / `story` / `opinion` /
  `demonstrate` / `promote` — only surfaced in UI if it
  materially improves output)
- `core_angle` (JSON: angle / tension / central_opinion /
  factual_grounding / objective_resolved)
- `status` (enum: `pending` / `generating` / `ready` / `failed`)
- `generation_metadata` (JSON — call names + model + tokens)
- `cost_metadata` (JSON — micros per call)
- `created_by` (FK User)
- `created_at`, `updated_at`

**ContentOutput**
- `package` (FK)
- `content_type` (enum: `SHORT_VIDEO` / `LINKEDIN` / `X` /
  `INSTAGRAM` / `BLOG` / `NEWSLETTER`)
- `title` (nullable — used for BLOG heading + NEWSLETTER subject)
- `subject` (nullable — NEWSLETTER)
- `preview_text` (nullable — NEWSLETTER)
- `body` (text)
- `structured_metadata` (JSON — format-specific: e.g., hashtags
  array for INSTAGRAM/X, thread-parts array for X thread, hook
  string for SHORT_VIDEO, beats array for SHORT_VIDEO)
- `status` (enum: `draft` / `edited` / `approved` / `rendered` —
  `rendered` applies to SHORT_VIDEO only, and only after the
  video bridge has produced an Asset)
- `version` (integer; incremented per regeneration or edit-save)
- `verification_result` (JSON — flags from claim verifier)
- `generation_metadata` (JSON — call name + model + tokens)
- `bridged_script` (nullable FK to `apps.scripts.Script`, set
  when SHORT_VIDEO is approved and the render bridge fires)
- `created_at`, `updated_at`

**Bridge policy.** `ContentOutput` holds the FK to `Script`, not
the reverse. The mature Scripts subsystem does not learn about
the experimental Content Studio. If the bridge later needs a
back-reference for observability, prefer a separate small bridge
row over adding a nullable FK to the Script model.

---

## UI

Single new route: **`/workspace/content`**.

Nav-rail entry: **CONTENT** (between SPOKESPEOPLE and KNOWLEDGE).

**Initial state.**

> **Content Studio**
>
> *Turn one idea into today's content.*
>
> - Creator selector (dropdown of existing spokespeople in the
>   workspace)
> - "What's on your mind today?" text field
> - Objective selector (optional; five options; suppressed in v1
>   UI unless runtime evidence shows it improves output)
> - "Generate package" primary button

**Package view.**

Six outputs presented as cards or tabs (implementation choice
during build). Each output shows:

- format label ("Short video", "LinkedIn", "X", "Instagram",
  "Blog", "Newsletter");
- body text (editable in place);
- Save (persists edit, increments version);
- Regenerate (fires one format-specific call, replaces body,
  increments version);
- Copy (copies text to clipboard);
- Download (Markdown for BLOG, plain text for others).

Package-level actions:

- **Approve all** (or "Ready to use") — single action, no
  cascade of six required decisions.
- **Render with `{Creator name}`** — appears on the SHORT_VIDEO
  card only. Fires the video bridge. Label never says "Create
  Script", "Fire Composition", or "Open Recipe".

No engineer vocabulary appears anywhere in this surface (rule 6).

Existing `/workspace/scripts` and `/recipes` remain untouched.

---

## Video bridge

On operator click of **"Render with `{Creator name}`"** for an
approved SHORT_VIDEO output:

1. Content Studio creates one `Script` row in the existing
   Scripts subsystem, populated from the SHORT_VIDEO body, with
   `status = READY` (skipping DRAFT, because the operator has
   already approved via the package flow).
2. Content Studio persists the FK back:
   `ContentOutput.bridged_script = Script.id`.
3. Content Studio fires the existing `auto_script` recipe with
   the newly-created Script and the package's Creator.
4. The existing V-arc render path (talking_head + reels_format
   if applicable + captions if requested) executes as-is.
5. When the render completes and produces an Asset, Content
   Studio surfaces the Asset in the package view with a
   **"Review video"** button.
6. Operator clicks Review, plays the clip inline, and either
   **Accepts** (marks `ContentOutput.status = rendered` and
   completes the deliverable) or **Rejects** (leaves status
   `approved`, no automatic re-render — operator decides next
   action).

The bridge does not modify Scripts, Recipes, K6, or V-arc code.

---

## Verification (before this slice can be called complete)

Two live runs by the operator:

**Run 1 — Tulsi, text-only verification.**

Idea: *"People think AI is too complicated."*

Verify at runtime:
1. Package generated end-to-end via the UI.
2. Six outputs exist and are materially different in structure
   and register (not the same paragraph six ways).
3. Persona-scoped knowledge retrieval fires for Tulsi only;
   Oliver's knowledge does not appear in the core-angle
   grounding.
4. Factual claims pass or are flagged by the verifier.
5. Package + outputs persist across page reload.
6. One output regenerated independently updates only that row.
7. Edits save + survive reload.
8. Each output copies + downloads correctly.
9. Cost + call logs recorded.
10. All of the above through the UI only.

**Run 2 — non-human Creator, video-render verification.**

Same or similar idea. Uses one existing mascot / animal /
stylized Creator (per F-DGF-016).

Verify at runtime:
11. Package generation works identically for a non-human Creator.
12. SHORT_VIDEO approved + "Render with `{Creator}`" fires the
    bridge.
13. Existing render pipeline produces the file.
14. Operator visually reviews and accepts (or rejects) — Content
    Studio does not mark the deliverable complete on
    `status=processed` alone (rule 8).

Both runs record their evidence in `docs/CUSTOMER_ZERO_DOGFOOD.md`
as F-DGF-NNN rows. The slice is not shipped until both runs pass.

---

## What this doc is not

- **Not a feature specification.** No file paths for new code
  beyond the model-shape sketch. No slice numbers. No estimates.
  Implementation-order sequencing lives in the operator's
  scope-lock prompt (2026-08-05) that produced this doctrine
  and in the session handoff after the slice ships.
- **Not a roadmap.** No sequencing beyond "generation before
  UI, UI before render bridge, both runs before ship."
- **Not a marketing brief.** The operator-facing framing here
  is engineered to be operationally verifiable, not persuasive.
- **Not a pricing doc.** Cost governance for Content Studio
  packages reuses existing `apps/billing` mechanics; this
  doctrine constrains nothing about pricing.

---

## Amendment discipline

- **MINOR (`v1.1`, `v1.2`)** — clarifications, tightened non-
  goals, generation-strategy adjustments under runtime
  evidence, added format-specific rules. Do not change the 10
  contract rules or the six-format initial package.
- **MAJOR (`v2`)** — adds a seventh format, changes the
  package-level-approval default, adds publishing / scheduling
  / analytics / performance-memory surfaces, or changes the
  video bridge policy. Requires operator ratification with a
  `docs/handoffs/SESSION_NNN_CREATOR_CONTENT_STUDIO_V2_RATIFIED.md`
  handoff.

Creator Content Studio is intended to be **maximally stable at
its own small scope**, the same way Job One is stable at its own
small scope. Both doctrines share the discipline: expansion is a
doctrinal event, not a slice.

---

*End of doctrine. Next work: implement the vertical slice
described in the operator's 2026-08-05 scope-lock prompt, in the
order specified there (models + migration → generation contract +
tests → SPA → render bridge → both verification runs → ledger
evidence → handoff).*
