---
title: "Job One — scope lock (product doctrine)"
status: active (scope-locked, no code yet)
generated: 2026-08-05 (drafted during workspace-level ecosystem investigation; session number assigned at fold-in)
companion_docs:
  - "CHARACTER_OS_WHAT_IT_IS.md"
  - "CUSTOMER_JOURNEY_V1.md"
  - "VIDEO_COMPOSITION_V1.md"
  - "AUTO_SCRIPTING_V1.md"
  - "PUBLISH_BUNDLE_V1.md"
  - "ASSET_LIBRARY_V1.md"
  - "VOICEOVER_V1.md"
  - "BRAND_IDENTITY_V3.md"
  - "../../../docs/ECOSYSTEM_PRIMITIVES.md"
phase: doctrine (above phases)
---

# Job One

> **Read first:** `CHARACTER_OS_WHAT_IT_IS.md` (product object
> map), `CUSTOMER_JOURNEY_V1.md` (the customer-narrative doctrine
> this sits alongside), and the workspace-level
> `docs/ECOSYSTEM_PRIMITIVES.md` (the primitive inventory this
> doctrine was distilled from).

---

## Purpose

Character OS today has, by count, 20 recipes, 23 composition
primitives, 6 realtime tools + 3 bridge tools, 9 knowledge slices,
10 workspace-fabric slices, 8 asset-library slices, four workflow
B-arcs (B-1 / B-2 / B-3 / B-14), 6 voiceover slices, 5+ brand
identity slices, and 5 engine-bridge slices. Twelve of twenty
customer journeys are code-complete end-to-end. **One is dogfooded
to real-mode PASS. Four have zero live rows.**

The gap is not capability. The gap is **commitment to a single
recurring customer responsibility that the whole platform serves.**

This doc locks that commitment. It defines the one weekly job
Character OS owns completely for one small-business owner. It sits
**above** the feature arcs (V, R, K, F, A, B, VO, EB, Brand) and
constrains them. When a feature arc's design conflicts with Job
One, Job One wins. When a proposed milestone does not advance
Job One, it is downstream.

`CUSTOMER_JOURNEY_V1.md` locks the *narrative* the customer lives
through. `JOB_ONE_V1.md` locks the *responsibility* the platform
carries on the customer's behalf, week after week. They are peers.
The journey ends at the moment the customer runs an AI team; Job
One is what the AI team does every week after that.

### Why scope-lock first

Job One touches every shipped arc (V provides the render, K
provides the angle context, A persists the deliverable, B-2 drafts
the script, B-14 formats the output, VO synthesizes the voice,
Brand carries the identity) and defers three arcs entirely (R, B-1,
B-3, EB). Locking the responsibility before any implementation
starts prevents Job One from being reframed feature-by-feature into
just another arc — and prevents any single arc from silently
expanding its scope by claiming Job One relevance.

The distillation is documented in `docs/ECOSYSTEM_PRIMITIVES.md`
Part 8 (the primitive-combination that already-exists-and-is-not-
wired) and the follow-up brief that surfaced the weekly-job
shape.

---

## The Job

**One 30–60 second vertical spokesperson video, captioned,
downloaded, delivered to the customer's hand — every week, forever,
for as long as the customer stays subscribed.**

That is the entire job. It is small on purpose. It is recurring
on purpose. It is bounded on purpose.

Persona: a local service-business owner (real-estate agent,
personal trainer, therapist, caterer, small-shop retailer) who
already knows they should post weekly and doesn't. They have a
spokesperson configured. They open Character OS once a week for
under fifteen minutes. They close it with the week's video in
their pocket.

---

## The Promise

The customer-facing commitment, in the customer's voice:

> *"Every week, in under fifteen minutes of your time, we produce
> one polished vertical spokesperson video for you. It's
> captioned, formatted for social, and ready to post. You give us
> a paragraph; we do everything else. If we don't ship your video
> that week, you don't pay for that week."*

The promise is bounded four ways: **one video** (not two, not a
bundle), **under fifteen minutes** (of the customer's attention),
**every week** (fixed cadence), **no charge on miss** (the money
mechanic that keeps us honest).

Nothing else Character OS does is a Job One promise. Realtime
avatar conversation, batch personalization, transcript mining,
engine-bridge tool-invocation, agency-tier multi-spokesperson
workflows — all are legitimate product surfaces. None of them are
Job One. Job One is the anchor commitment.

---

## Definition of Complete

A single week's Job One is **complete** when, and only when, all
of the following are true for the customer's workspace in that
week:

1. An angle was captured (one paragraph, one voice memo, or one
   accepted suggestion) and stored with the week's date.
2. An approved Script exists that was derived from that angle.
3. A talking-head video (vertical 9:16, 30–60 seconds, captions
   burned in, spokesperson brand voice) was rendered from that
   Script against real providers (not mock).
4. An `Asset` row with `role = weekly_short` exists in the
   workspace, anchored to the week's date, with the rendered
   file stored durably.
5. The customer received the file in a form they can post from —
   at minimum, a working download link; ideally, a notification
   channel handoff (email / push / in-app inbox).
6. The customer's Job One streak counter was incremented and is
   visible to them.
7. The total delivered cost is within the tier's weekly budget
   cap.
8. The total elapsed customer attention (measured as time-on-
   task, not wall-clock) was under fifteen minutes.

**Anything short of all eight is not a complete Job One that
week.** Partial results are logged, but the week counts as a
miss, and the miss triggers the no-charge mechanic (rule 6 of
the contract rules).

---

## Non-goals

Explicit. If a proposal falls under any of these headings, it is
not Job One. It may still be valuable — but it must be justified
on its own terms, not by borrowing Job One's legitimacy.

1. **Not a realtime avatar conversation.** R-arc is a distinct
   product. Job One is a recorded artifact, produced without a
   live session.
2. **Not batch fan-out.** B-3 (Personalized Campaigns) produces
   many renders from one template. Job One is unit-one. If the
   customer wants many videos in a week, that is B-3, and it is
   a separate purchase.
3. **Not multi-clip publish bundles.** B-14 (Publish Bundle) as
   a full product produces N platform-formatted variants from
   one clip. Job One consumes only the *vertical* pathway of
   B-14. Horizontal, square, and platform-specific overlays are
   downstream.
4. **Not long-form.** > 60 seconds is out of scope for Job One.
   Long-form (`long_form_ad` recipe) is a separate purchase.
5. **Not transcript mining.** B-1 (Transcript Miner) is a
   different job (extract highlights from recorded conversations).
   Job One's angle input is not sourced from mined transcripts by
   default.
6. **Not the engine-bridge customer.** EB-arc serves enterprise
   customers with their own AI stack. Job One serves the solo /
   small-business persona who has *no* AI stack of their own.
   The two are non-overlapping.
7. **Not direct posting to social platforms.** OAuth into
   Instagram / TikTok / YouTube Shorts / Meta / LinkedIn is a
   post-launch surface. Job One completes at the download link,
   not at the platform post.
8. **Not analytics.** View counts, likes, shares, engagement
   metrics live downstream of the customer's own posting
   behavior. Character OS does not commit to outcomes it does
   not control. Job One's success metric is *delivered*, not
   *performed*.
9. **Not multi-spokesperson.** Job One assumes one active
   spokesperson per workspace. Agency-tier fan-out across
   spokespeople is a separate SKU.
10. **Not the total product.** Job One is a floor, not a
    ceiling. Character OS retains every other capability
    (realtime, personalized campaigns, publish bundles, bridge
    tools, knowledge chat) as additional surfaces. Job One is
    the one thing we promise; the rest is the one thing we
    offer.
11. **Not a multi-format content package.** Creator Content
    Studio (`CREATOR_CONTENT_STUDIO_V1.md`) is a peer doctrine
    covering the multi-format daily content loop for a
    persistent AI Creator (the Character-OS-as-Customer-Zero
    operating mode). Job One's promise, cadence, and scope are
    unchanged by Creator Content Studio; the two doctrines are
    peers with distinct customers, cadences, and units of
    output.

---

## Acceptance criteria

Measurable state that proves Job One is being served, per
workspace. These are the numbers a customer-success dashboard
would report:

- **Delivery rate:** For every week in which an angle was
  submitted, a `role=weekly_short` Asset exists with
  `status=delivered` and a valid download link. **Target: ≥ 95%
  across all active workspaces, per rolling 4-week window.**
- **Time-to-artifact:** Median elapsed wall-clock from angle
  submission to download-link availability. **Target: ≤ 15
  minutes at p50; ≤ 45 minutes at p95.**
- **Customer attention:** Median cumulative in-app time per
  workspace per week attributable to Job One. **Target: ≤ 15
  minutes at p50.**
- **Streak length:** Distribution of active workspace streaks
  (consecutive weeks with a delivered video). **Target: median
  streak ≥ 8 weeks after four weeks in market.**
- **Miss handling:** For every miss (angle submitted, video not
  delivered), a no-charge credit was issued for that week
  before the next invoicing cycle. **Target: 100% honored.**
- **Cost per delivery:** Median COGS (real-provider spend) per
  delivered Job One. **Target: within the tier's per-week
  budget cap defined in `apps/billing`; documented on the
  pricing page.**
- **Failure taxonomy:** Every miss is classified against a
  bounded failure list (provider-outage / policy-block /
  timeout / customer-abandoned / other). Class "other" **≤ 5%
  of misses**.

The dashboard does not measure views, likes, shares, follower
growth, or ROI. Those live downstream of the customer's own
posting behavior and are outside Character OS's contractual
scope (see non-goal 8).

---

## Contract rules (load-bearing)

These bind every Job-One-related design decision the same way
`KNOWLEDGE_LAYER.md`'s rules bind every K-arc slice and
`CUSTOMER_JOURNEY_V1.md`'s rules bind every customer-narrative
decision. Any conflict is resolved in Job One's favor.

1. **Cadence is the primitive.** Job One is not a session, not a
   feature, not a flow. It is a *weekly recurring responsibility*.
   The unit of design is the week. Anything that treats Job One
   as a one-shot ships the wrong thing. The scheduler surface,
   the streak metric, the miss ledger, and the customer's weekly
   attention window are all first-class.

2. **The unit is one.** One angle in, one video out. Not two.
   Not "a batch of three shorts." Not "a video plus a caption
   plus a thumbnail deck." Any expansion of the unit requires a
   `JOB_ONE_V2` amendment. Sub-artifacts (a caption, a hashtag
   suggestion, a thumbnail) may accompany the video as part of
   the one delivery, but only if they add zero decisions to the
   customer's flow.

3. **The customer's attention is the scarcest resource.**
   Fifteen minutes per week is the ceiling, not a target. Every
   proposal that increases customer attention cost must remove
   attention cost elsewhere or be rejected. This is stricter
   than `CUSTOMER_JOURNEY_V1.md` rule 4 ("Character OS
   recommends, customer chooses, Oliver executes"): for Job One,
   Character OS defaults *everything* and only surfaces choices
   the customer opts into.

4. **Complete means delivered.** Persistence is not extraction
   (this echoes `CUSTOMER_JOURNEY_V1.md` rule 7). An `Asset` row
   in the database is not a completed Job One. The file must
   reach the customer via a downloadable link and — where the
   customer has opted in — via a notification channel. Journey
   16 (download / handoff) is not a P3 polish item for Job One;
   it is a Job One completion requirement.

5. **Character OS decides format, length, platform, aspect
   ratio, and voice-take by default.** The customer's only
   recurring decision is the angle for the week. Every other
   Job One decision is Character OS's job. Overrides exist
   (custom aspect ratio, custom length, alternate voice take)
   but are opt-in, are never surfaced during the primary flow,
   and never count toward the fifteen-minute budget. This rule
   is what makes rule 3 achievable.

6. **The promise is bounded by the money mechanic.** If Job One
   is not delivered in a given week, the customer is not
   charged for that week. This is not a refund process, not
   a support-ticket path, and not discretionary — it is an
   automatic ledger reconciliation. The mechanic is the
   promise's teeth; without it, "we ship every week" is
   marketing copy. With it, "we ship every week" is a
   contract.

7. **Every arc is evaluated against Job One.** New slices, new
   recipes, new primitives, new tools, new bridges, new
   endpoints, new UI must answer one question during scope-
   lock: *"Does this advance a customer's completion of this
   week's Job One?"* Yes → the slice may proceed on Job One's
   priority track. No → the slice may still proceed, but on
   its own arc's priority track, and never at the expense of
   Job One capacity.

8. **Job One's scope stays small forever.** The temptation to
   grow Job One (from one video to two; from vertical to
   multi-format; from weekly to twice-weekly; from spokesperson
   video to spokesperson + text-post + email) is a design
   defect. Anything that expands Job One's scope requires a
   published `JOB_ONE_V2` amendment. Adding a *second* recurring
   job (e.g., "Job Two = one weekly newsletter") is legitimate
   and gets its own doctrine doc; expanding Job One in place is
   not.

9. **The measurable output is delivery, not performance.** Job
   One's success metric is *"video shipped this week: yes/no"*
   and *"streak length"*. It is not view count, engagement, ROI,
   or lead generation. Character OS commits to what Character
   OS controls. What happens after the customer receives the
   file lives in the customer's world and their own tools. This
   rule prevents scope drift toward analytics products
   Character OS is not architecturally positioned to own.

10. **Realtime is not Job One.** The R-arc's WebRTC live
    conversation product is legitimate, valuable, and shipped
    (SESSION 152, six-tool v1 catalog complete). It is not Job
    One. Realtime is a *different* recurring pattern (episodic,
    session-based, live). Job One is *asynchronous, recurring,
    artefactual*. Confusing them collapses two products into one
    and diminishes both. This rule prevents a common accident:
    reframing Job One as "a weekly realtime session" — which
    would triple customer attention cost, break rule 3, and
    silently replace the promise with an experience.

---

## Arc alignment matrix

How every existing scope-locked arc supports (or does not
support) Job One. **The right column is the load-bearing lens.**

| Arc | Supports Job One? | Nature of support / non-support |
|---|---|---|
| **V — Video Composition (V0-V17, VO.0-VO.2)** | **YES — primary** | `talking_head` recipe is the render heart. `add_captions` (V9) satisfies the burned-in captions requirement. `reformat_clip` (V9) and the `reels_format` recipe satisfy the 9:16 vertical requirement. `remove_avatar_background` (V16) supports the visual polish. VO.1 + VO.2 provide the voice track. **Job One consumes but does not extend the V-arc.** |
| **K — Knowledge Layer (K0-K10)** | **OPTIONAL — supporting** | Provides optional angle suggestions via `recall_knowledge` when the customer wants inspiration for the week's angle. Not required. The customer's typed paragraph or voice memo is the primary input. K-arc absence does not block Job One; K-arc presence enhances angle capture. |
| **R — Realtime Avatar (R0-R10, R6.1)** | **NO — different job** | See contract rule 10. Realtime is episodic; Job One is artefactual. R-arc capacity does not roll into Job One capacity and vice versa. **Any proposal to reframe Job One as "a weekly realtime session" violates rule 10 and must be rejected.** |
| **F — Workspace Fabric (F0-F10)** | **INDIRECTLY** | Provides the shell inside which Job One lives (workspace overview, nav rail, brand chip). F-arc completion is a precondition for Job One having a home in the SPA; it does not itself produce Job One's artefact. |
| **A — Asset Library (A0-A8)** | **YES — required** | The `Asset` model with role taxonomy is the persistence surface for the delivered `weekly_short`. Job One adds one new role value (`weekly_short`) and one new completion state (`delivered`, versus the current implicit "exists"). **A-arc extension required.** |
| **B-1 — Transcript Miner** | **NO — different job** | Mining highlights from prior transcripts is a distinct customer job. Its output could *feed* Job One's angle input for customers with recorded sessions, but that coupling is downstream and optional. Job One does not depend on B-1. |
| **B-2 — Auto-Scripting** | **YES — primary** | Angle → drafted Script → approved Script is exactly Job One step 2 → step 3. The B-2 arc is currently code-complete with zero live rows. **Job One is the arc's first real use case.** |
| **B-3 — Personalized Video** | **NO — different job** | See contract rule 2 and non-goal 2. B-3 is batch fan-out. Job One is unit-one. |
| **B-14 — Publish Bundle** | **PARTIAL** | Job One consumes only the vertical (9:16) pathway of B-14. The multi-platform variant pipeline (square, horizontal, platform-specific overlays) is downstream. **Job One may ship before B-14's full multi-variant surface ships**, provided the vertical pathway is stable. |
| **BC — B-2 ↔ B-3 Composition** | **NO** | Batch coupling of scripting to personalization. Not Job One. |
| **VO — Voiceover (VO.0-VO.6)** | **YES — supporting** | VO.1 synthesizes the voice track; VO.2 overlays it. **VO.3-VO.6 are not required for Job One MVP** but do not violate Job One if they ship. |
| **EB — Engine Bridge (EB.0-EB.5)** | **NO — different customer** | See non-goal 6. EB serves an enterprise customer with their own AI stack; Job One serves a solo/small-business customer without one. **The two customer types are non-overlapping. Any argument that "EB supports Job One" reflects category confusion.** |
| **Brand Identity V3** | **YES — required** | The brand system carries into each week's video (spokesperson voice, brand chip, editorial palette). Job One assumes Brand Identity is present and consistent. |
| **Media Generation V1** | **OPTIONAL** | Could provide backdrop / broll variety for Job One videos. Not required. Job One's MVP renders `talking_head` without additional generated visuals. |
| **CUSTOMER_JOURNEY_V1** | **PEER doctrine** | Job One begins where CUSTOMER_JOURNEY's onboarding chapters end. Once the customer has hired Oliver and completed the first assignment, Job One is the enduring commitment. **The two docs constrain each other symmetrically; neither overrides the other.** |

---

## Gaps between primitives and Job One

For completeness, the specific pieces missing today that must
land before Job One can be honored as a paid promise. **This list
is not a scope-lock for those pieces** — each will require its
own arc-level design under normal V/A/B-2/B-14 discipline. It is
included here as the reader's aid for interpreting the alignment
matrix above.

Documented gaps, per `docs/ECOSYSTEM_PRIMITIVES.md` §6 and the
Job One breakdown that produced this doctrine:

1. **Weekly cadence trigger.** Customer-facing weekly prompt
   (email / push / in-app). the sibling project's Celery Beat exists but is
   not exposed as a customer surface.
2. **Single-input angle capture.** A one-question surface
   ("what's this week about?") that produces a B-2 Script draft.
   The B-2 arc accepts prompt input but has no minimal customer-
   facing form.
3. **Download / handoff.** Journey 16 (currently FAIL). The
   deliverable must reach the customer's device; a persisted
   Asset row is not a completed Job One (rule 4).
4. **Streak / delivery ledger.** A workspace-scoped counter
   surfaced to the customer, incremented per delivered week,
   reset only by miss.
5. **Miss / no-charge reconciliation.** The billing mechanic
   that honors rule 6. Requires a Job-One-aware
   `apps/billing/services` extension.
6. **Failure taxonomy classifier.** The bounded failure list
   from the acceptance criteria. Missing today; must be
   deterministic so the miss-ledger stays honest.

All other Job One capabilities are already in the primitive
inventory. **Job One is roughly 80% built and 100% unshipped**,
because the last 20% (cadence, capture, handoff, ledger, mechanic,
classifier) is exactly the last mile the current roadmap has been
deferring.

---

## Lens usage — how to evaluate a proposed milestone

Every proposed new slice, arc, or product surface should be
scored against this doctrine before scope-lock. The score is not
a veto — arcs that don't serve Job One can still ship — but the
scoring must happen, and the outcome must be documented.

For each proposed slice, answer:

1. **Does this advance a customer's completion of this week's
   Job One?** (Yes / No / Partial)
2. **If yes: which of the 8 Definition-of-Complete conditions
   does it move forward?** (Cite by number.)
3. **If no: is this arc's own priority track ahead of or behind
   Job One's remaining gaps?** (Ahead → the slice may proceed on
   the arc's own schedule. Behind → the slice defers until Job
   One's gap on the arc's own dependency is closed.)
4. **Does the proposed slice violate any of the 10 contract
   rules?** (If yes, the slice may not scope-lock without
   ratifying a corresponding amendment to Job One or to itself.)
5. **Does the proposed slice expand Job One's scope?** (If yes,
   the slice requires a published `JOB_ONE_V2` before it can
   ship.)

The output is a one-paragraph "Job One alignment" section that
belongs in every new arc's scope-lock frontmatter. The absence of
this section on a post-`JOB_ONE_V1` scope-lock is a design
defect — the same way a missing `verify.yaml` claim is a
documentation defect.

---

## Amendment discipline

Amendments to Job One follow the same discipline as the
Engineering Playbook's amendment cycle (per
a sibling private-project source module §10):

- **Job One MINOR (`v1.1`, `v1.2`)** — clarifications, expanded
  acceptance criteria, tightened non-goals. Do not change the
  10 contract rules. Do not change the customer promise.
- **Job One MAJOR (`v2`)** — changes to the contract rules,
  changes to the customer promise, changes to what "one" means
  (§rule 2), changes to the cadence, or addition of a second
  recurring job. Requires an operator ratification event
  documented in a `docs/handoffs/SESSION_NNN_JOB_ONE_V2_RATIFIED.md`
  handoff and a superseding `JOB_ONE_V2.md` doc.

Job One is intended to be **maximally stable**. The customer
promise depends on the doctrine not moving underneath them. A
Job One amendment is a bigger event than a scope-lock revision.

---

## What this doc is not

- **Not a feature specification.** No slice numbers. No
  implementation plan. No file paths for new code. No estimates.
  Those live in the arc-level scope-locks that Job One
  constrains (`AUTO_SCRIPTING_V1.md`, `VIDEO_COMPOSITION_V1.md`,
  `PUBLISH_BUNDLE_V1.md`, `ASSET_LIBRARY_V1.md`, and future
  arcs for cadence / handoff / ledger).
- **Not a roadmap.** No sequencing. No dates. No milestones.
  Sequencing is a downstream decision made against this lens,
  not encoded in it.
- **Not a marketing brief.** The customer promise is engineered
  to be operationally verifiable, not persuasive. Marketing
  language derives from this doctrine; it does not modify it.
- **Not a pricing doc.** Pricing lives in `apps/billing`. Job
  One constrains pricing (rule 6 — no charge on miss); it does
  not set prices.

---

*End of doctrine. Next natural work: fold Job One's alignment
question into the scope-lock template used by all future arcs
(`docs/design/*_V1.md`), and open a slice-level scope-lock for
the six documented gaps (cadence trigger, angle capture, handoff
surface, streak ledger, no-charge mechanic, failure classifier)
under a new J-arc — but that is a subsequent decision, not part
of this doctrine.*
