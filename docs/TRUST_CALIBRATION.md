---
title: "Trust Calibration Log"
status: active
---

# Trust Calibration Log

Append-only ledger of AI ↔ human calibration events. See
[`docs-pattern/08_collaboration_roles.md`](docs-pattern/08_collaboration_roles.md)
for why this exists.

Three event types:

- **AI confidently wrong** — AI asserted something with confidence; turned out false.
- **AI right despite pushback** — AI raised a concern, human was skeptical, AI was right.
- **Near-miss** — human nearly approved something the AI later caught.

Keep both sides of the ledger. One-sided logs recalibrate trust in the wrong direction.

---

## Format

```markdown
## YYYY-MM-DD — <event type>: <one-line headline>

- **Context / claim:** <what the AI said or human was about to approve>
- **Reality / outcome:** <what turned out to be true>
- **Found by:** <verifier, test run, staging, reviewer>
- **Lesson:** <one-line calibration takeaway for future sessions>
```

---

## Log

## 2026-05-13 — AI right to flag, operator right to escalate: Celery pulled into Phase 2

- **Context / claim:** SESSION 109 started with the AI flagging a
  fire-then-poll design question for the video pipeline and
  recommending a **thread-helper middle path** (Django daemon
  thread polls the media-engine, writes back to the row). The
  AI's reasoning was "defers Celery to Phase 4 as originally
  planned." The AI also surfaced the real tradeoff: the thread
  approach is not crash-safe — a Django restart loses the polling
  thread.
- **Reality / outcome:** Operator said *"bring it in now, so we
  already have it as the project is merging and growing."*
  Celery + Redis landed in SESSION 109 as the foundation. Cost
  was ~80 lines of config + a docker-compose service + 2 new
  Python deps. SESSION 110's voice clone slice didn't need
  Celery, but the next async surface (video kinds 2-4,
  embeddings, scheduled tasks) will — landing it once costs less
  than retrofitting later.
- **Found by:** Operator judgement during the SESSION 109 design
  call.
- **Lesson:** When the AI proposes "smallest thing now" vs.
  "real foundation now," and the foundation is **clearly going
  to be needed within 1-3 sessions**, default to the real
  foundation rather than the smallest thing. The thread-helper
  middle path was technically correct as a Phase 2 minimum, but
  the operator's intuition that "this will become tech debt
  fast" was right. **For this operator specifically:** when
  scope expansion costs <1 session of work and saves a future
  retrofit, lean toward expanding.

## 2026-05-14 — AI right despite pushback: right-shape-foundations pattern confirmed 3+ times

- **Context / claim:** Across SESSIONS 124-132, the AI repeatedly
  recommended landing foundations *before* the surfaces that
  consume them. Pattern instances:
    - SESSION 128 — wizard scaffold (slice 5) lands *before* the
      step bodies (slices 6-9). Empty placeholder bodies, full
      navigation + reducer shape exercised end-to-end via spec
      before any step UI lands.
    - SESSION 127 — `visual_subject` + `tone_archetype` fields
      land *before* the wizard step that consumes them. Both
      have safe model defaults so the migration is backwards-
      compatible.
    - SESSION 130 — the W3.5 → W7 deferral: the
      `visual_subject` *field* shipped in W3.5 but the
      `/internal/portrait/` orchestration that consumes it
      didn't land until W7. The intermediate sessions had a
      stored-but-not-yet-threaded field. Operator pushed back
      mildly on this gap during SESSION 127 ("where do I say my
      spokesperson is a raccoon?"); AI's framing held — the
      foundation belongs early, the threading belongs with the
      consuming surface.
- **Reality / outcome:** All three foundation slices made the
  consumer slices smaller and safer. The wizard scaffold's
  reducer + navigation were proven by Playwright before any step
  body had real inputs, so when each step body landed (slices
  6-9), the only thing to test was the step's own UI — not the
  surrounding nav + state-management plumbing.
- **Found by:** Pattern observed across 5 sessions of clean
  gate runs; commits stayed atomic (under 1000 LOC each); no
  rewrites of the scaffold or foundation fields needed during
  the body slices.
- **Lesson:** **For this operator specifically:** when a slice
  could be either (a) one big "everything-at-once" feature or
  (b) a foundation slice followed by surfaces, **default to
  (b)**. The foundation slice can ship empty placeholders; the
  surface slices stay atomic. Operator already calibrated to
  this — codified here so future AI sessions don't argue
  against it.

## 2026-05-14 — Near-miss: queue-ahead-of-slice-4 interrupt

- **Context / claim:** At the end of SESSION 126, the AI handed
  off SESSION 127 as "tone archetype field (slice 4)." After
  reviewing the handoff, the operator asked: *"Is there a place
  for users to define what they want the spokesperson to look
  like? Like I want a raccoon or a battle unicorn or whatever?
  We have business_brief but not sure if it goes there."*
- **Reality / outcome:** The AI had documented the wizard's
  Step 2 "Generate" tab in the SESSION 123 scope-lock with a
  `subject` parameter (already plumbed through to
  `/internal/portrait/` from SESSION 125), **but the
  `Spokesperson` model had no field to persist it.** The wizard
  would have collected the subject as client-state only,
  losing it on every page refresh + every detail-page
  regeneration. The operator's intuition correctly caught the
  gap. AI agreed and queued a new slice (W3.5) *ahead* of W4.
- **Found by:** Operator question between sessions.
- **Lesson:** When a scope-lock says "this field is collected
  client-side and threaded through to an external API," check
  whether it should *also* be persisted on the row for later
  edits. Default to "yes, persist it" — the cost of an extra
  CharField is trivial; the cost of losing operator intent on
  refresh is high. Generalisation: **fields that capture
  operator authorial choice should persist by default**, even
  if no current UI re-reads them yet. Future sessions will
  thank past sessions for this.

## 2026-05-14 — AI confidently wrong: `ACCOUNT_RATE_LIMITS = {}` doesn't disable allauth rate limits

- **Context / claim:** SESSION 131 closed queued #14 (allauth
  signup rate limit biting the e2e suite) with a tiny settings
  override. AI's first attempt: `if DEBUG: ACCOUNT_RATE_LIMITS = {}`.
  Reasoning: "empty dict = no limits." Confidence: high (looked
  like the natural override shape).
- **Reality / outcome:** The Playwright suite still hit the
  20/m signup cap. Inspection of allauth's `app_settings.py`
  revealed `if rls is False: return {}` as the explicit
  disable path — `{}` falls through to a default-merge codepath
  that re-applies the factory defaults. **The disable value is
  `False`, not the empty dict.** Verified by running
  `python -c "from allauth.account import app_settings; print(app_settings.RATE_LIMITS)"`
  with the override in place — showed the full factory dict,
  not the empty one.
- **Found by:** E2e suite failing on the same test after the
  "fix" + AI inspecting the allauth source on the second pass.
- **Lesson:** **Library-shipped settings are not always
  overridden by their "obvious empty value."** Some libraries
  use `None` as the disable, some use `False`, some use a
  string literal `"disabled"`, some merge the user value with
  defaults. **For overrides to library defaults: verify the
  override actually took effect** before claiming the fix. A
  one-line probe (`python -c "from library import setting_view;
  print(setting_view)"`) takes 10 seconds and prevents an
  e2e-suite-rerun debugging spiral.

## 2026-05-14 — Near-miss: K6.5 framed too narrowly; operator's scope-up was the right call

- **Context / claim:** SESSION 141's render-pipeline audit
  found that K6 routes to the wrong Runway endpoint
  (`gen4_turbo` image-to-video instead of `/v1/avatar_videos`
  talking-head). The end-of-session handoff scoped this as
  **K6.5 — one endpoint swap, ~one session of work**. SESSION
  142 opened ready to execute that swap.
- **Reality / outcome:** Before writing any code, the AI ran
  a `runway-hackathon` pipeline-audit Explore call (because the
  CLAUDE.md "map the predecessor first" calibration from K3 /
  K6 sessions was carried forward). The audit surfaced **15+
  output kinds shipped at the hackathon + 5 distinct Runway
  endpoints in active use + ~2,000 lines of dormant
  composition logic** in `media-engine/app/services/*` that
  the migration left intact but the `/internal/*` contract
  doesn't expose. The *real* architectural blocker isn't K6's
  wrong endpoint — it's that every existing endpoint is a
  **terminal leaf** (input → finished MP4) with no notion of
  one clip being an *input* to a bigger composition. K6.5 as
  "swap the endpoint" papers over the architecture gap and
  guarantees the same shape continues. K6.5 absorbed into
  **V3** (a step primitive in the new Asset+Composition arc)
  — same Runway endpoint target, the data shape that ships
  with it is now reusable for every later primitive.
- **Found by:** The runway-hackathon pipeline audit at the
  start of SESSION 142, which the AI ran by default rather
  than as a debugging step. Operator's pushback ("we should
  import ALL the endpoints we built; the way we built
  everything none of the possibilities connect together")
  then anchored the architecture conversation on connectivity
  rather than endpoint selection.
- **Lesson:** **Map the predecessor before scoping** is now a
  default rule, not a debug-mode escalation. The pattern fired
  four times across SESSIONS 138 → 142 (cost-cap math, Maya
  tutor-mode framing, gpt-5 vs gpt-4o-mini, K6.5 → V3) — every
  time the operator + AI converged faster when one of them ran
  the predecessor mapping first. **For this operator
  specifically:** when scoping a slice that touches a system
  imported from `runway-hackathon/` or `unified-donkey-betz`,
  spend the first 10-30 minutes mapping what existed in the
  predecessor before locking the slice. Tokens spent on the
  audit pay back 3-5x in scope-correctness downstream.

## 2026-05-14 — AI confidently wrong (deferred-to-v2 framing): long-form AI video is a launch differentiator

- **Context / claim:** SESSION 142's first draft of
  `VIDEO_COMPOSITION_V1.md` sequenced **V7 — long-form ad
  (`split_script` + `concat_clips`)** as the seventh
  capability slice — after backwards-compat (V5),
  talking_head_with_backdrop (V6), and before polish (V8) +
  composite (V9). The AI's reasoning: "long-form is a more
  advanced capability that builds on the simpler starters."
  The AI was rendering long-form as a power-user feature, not
  a launch differentiator.
- **Reality / outcome:** Operator surfaced (via a ChatGPT
  conversation) the realization that **no major AI video
  provider — Runway, Sora, Veo, Kling, Pika, Luma — ships
  single-call video generations longer than ~10-20 seconds.**
  Every "AI movie" / multi-minute ad / long-form AI video
  output in the wild is N short clips stitched with ffmpeg
  (or MoviePy, or Premiere, or Resolve). The model providers
  don't advertise this because "we make movies" is a better
  marketing story than "we make 10-second clips you
  assemble." Most SaaS competitors sell 5-15 second outputs
  because that's what the provider APIs ship. A platform
  that says "give me your script, get back a 2-minute ad
  your spokesperson stars in" is the actual positioning
  advantage. V7 promoted to V5 (third capability slice
  instead of seventh) the same session, before any V3-V6
  code lands.
- **Found by:** Operator's external research + the dawning
  realization that the hackathon's `long_ad_service.py`
  (already imported into `media-engine/app/services/`) was
  doing the load-bearing capability — but the migration's
  narrow `/internal/*` contract dropped it.
- **Lesson:** **Capability that competitors don't ship is a
  feature ordering signal, not just a feature.** The AI was
  ordering slices by "architectural dependency from simple
  → complex" — a defensible engineering frame, but a
  *wrong* product frame when one of the "complex" slices is
  the one differentiating capability. **For this operator
  specifically:** when scoping a multi-slice capability arc,
  ask "which of these slices does no AI SaaS competitor
  ship today?" early in the design lock — that slice is the
  product story, and it should land as soon as the
  dependency graph allows, not when the architectural
  comfort says "we've earned it." The reorder cost zero code
  (V5's only hard dependency is V3, which was already going
  to be first). The wrong ordering would have cost months
  of "we have the architecture but no differentiating
  capability yet" until V7 finally shipped.

## 2026-05-14 — Near-miss: latent slice-dependency caught twice (V5 promotion, V9→V7 promotion)

- **Context / claim:** Both V0's slice plan (locked SESSION
  142) and the post-V5-promotion sequence I shipped looked
  internally consistent at design time. V7
  (`talking_head_with_backdrop`) and V9 (composite primitives)
  were both reasonable next-slice candidates after V6's
  backwards-compat shim.
- **Reality / outcome:** SESSION 143's V6 close exposed that
  V7's `talking_head_with_backdrop` recipe structurally
  requires the `composite_video` primitive, which was
  scheduled for V9. The same shape as SESSION 142's V5
  promotion (long-form's "no provider ships >20s single-
  call" reality). Both reorders required only docs edits +
  rationale; zero code was wasted because the dependency
  was caught between slices, not after. The second
  reorder (V9 → V7) was operator-prompted with a single
  flag — *"V7 needs `composite_video`?"* — that I
  confirmed against the V7 starter design.
- **Found by:** Operator's pattern recognition (same shape
  as V5 promotion) plus my own re-read of V7's recipe
  before locking the next slice.
- **Lesson:** **The slice-dependency check has to happen
  against the dependency graph of every prior slice's data
  shape, not just the immediate predecessor.** V0's
  contract rules locked workspace anchors + cross-workspace
  rejection + linear ordering — but didn't lock per-slice
  inputs/outputs against per-primitive needs. Two reorder
  events into the arc, this is now the rule: **at the end
  of each slice, list the next 2-3 slices' required
  primitives + check the registry for gaps before
  committing to a sequence.**
  Generalisation: when a design lock enumerates more than
  ~8 slices, the latent-dependency rate goes up. Either
  scope-lock fewer slices, or run an explicit "what does
  the next-next slice need" pass per slice. For this
  operator: the latent-dependency call-out is welcome
  (zero-cost catch); don't paper over it with "this works
  in isolation."

## 2026-05-14 — AI confidently wrong (v2-deferral framing): "we already had this" for V10, V11, V13

- **Context / claim:** V0's slice plan labeled V10 (voice
  flows), V11 (Aleph), and V13 (storyboard) as
  hackathon-port slices. My slice-intro framing for each
  treated them as "first-time implementations under the
  new architecture" — language matched a new feature
  rollout (cost estimation, contract rule fit, etc.).
- **Reality / outcome:** Operator flagged each one
  explicitly:
  - V10 (mid-slice): *"We should have had the multi-
    language connected in the hackathon project; I used
    it."*
  - V11 (post-V10 framing): *"another hackathon-shipped
    capability to restore."* (My commit message language
    converged toward "restoration" after this.)
  - V13: same pattern. The 29-language dubbing,
    `noir`/`anime`/etc. style presets, and the 3-shot
    Hook/Action/Payoff storyboard had all shipped in
    production at the hackathon.
- **Found by:** Operator's recall of live production
  usage at the hackathon, which I didn't have direct
  access to (`runway-hackathon/` repo only shows code,
  not what operators used).
- **Lesson:** **When porting from runway-hackathon,
  default-frame as "restoration of shipped capability"
  not "first-time feature implementation."** The
  hackathon's `audio_client.py`, `aleph_client.py`, and
  `storyboard_service.py` exist because operators ran
  them in production — that's stronger evidence than
  "the code is here." When the operator says "I used
  this," update commit-message framing + design-lock
  language to match. The shipped behavior + Runway
  billing + operator muscle memory all need to stay
  consistent; "restoration under new architecture" makes
  that constraint explicit.

## 2026-05-14 — Near-miss: doc-discipline gap (V3-V13 commits without context-kit updates)

- **Context / claim:** SESSION 143's V3-V13 shipped 11
  feature commits without paired context-kit updates.
  My (incorrect) implicit assumption: per-commit feature
  messages would serve as documentation; the slice table
  + change log + handoff would catch up at end-of-session
  in one batch.
- **Reality / outcome:** At end of session the operator
  asked *"Are you updating documentation and committing
  each step?"* The honest answer was "no — commits yes,
  docs no." Stale state across 6 anchor docs (slice
  tables, START-HERE Next section, CLAUDE.md Phase 4
  row, WHAT_IT_IS arcs section, TRUST_CALIBRATION log,
  inventory). A new session starting from those anchors
  would have gotten 11-slices-of-drift wrong.
- **Found by:** Operator directly. The catch-up pass
  (this commit batch) closed the gap.
- **Lesson:** **Feature commits and context-kit updates
  are paired by design, not optional.** Per-slice
  context-kit work is tiny (one slice-table mark + one
  change-log line + a status column flip) — the expense
  is forgetting to do it, not doing it. **Rule
  codified in CLAUDE.md as "Doc-with-commit discipline":
  every feature commit either includes the slice-table /
  change-log updates or is immediately followed by a
  docs commit that does. The session handoff aggregates
  but doesn't replace per-slice updates.**
  For this operator specifically: anchor docs that lag
  behind code are a real session-cost (next session has
  to re-derive the state from `git log`). The catch-up
  works once; the discipline avoids the catch-up.

## 2026-05-14 — Near-miss: operator's "brief mode" insight reshaped F4

- **Context / claim:** SESSION 144's F4 was scoped as
  "video-recipe knowledge preview" — show the operator the
  retrieval results their script will surface, debounced.
  Mid-scoping the operator asked: *"are we using the LLM to
  write the script? Can I just say 'Create a 60-sec ad about
  X'?"* The capability was already there (K6's
  `script_synthesis` writes the script from the brief), but
  the SPA labelled the field "Script — what the avatar will
  say." Operators were reading the label literally and
  pasting in pre-written scripts, not realizing they could
  hand off the writing to the model.
- **Reality / outcome:** F4 expanded mid-slice from
  preview-only to also include a **brief-mode helper** — a
  toggle that re-labels the field "Brief" and re-frames the
  generation flow as "describe the video, model writes the
  script." No model change; pure SPA framing + a label
  toggle. Operators surface the capability they already
  had.
- **Found by:** Operator's direct question during F4
  scoping. The handoff records this as "without the
  operator's question, F4 would have shipped a useful but
  smaller surface."
- **Lesson:** **Ask the operator what they think a field
  does, not what the model thinks.** When the label and the
  capability diverge, the label wins for the operator's
  mental model — and the capability stays hidden. **For
  this operator specifically:** when locking a UI-touching
  slice, ask "what would the operator type here?" before
  the field copy ships. F4 is the second instance of the
  same pattern (W3.5 was the first — visual_subject field
  collected client-side without a persistence layer until
  operator flagged it). Both shipped from "operator names
  the gap I missed."

## 2026-05-14 — AI confidently wrong (scope-lock taken at face value): K8 was partly shipped during K2

- **Context / claim:** SESSION 145 opened K8 with the K0
  scope-lock framing: *"K8 — `ConversationMessage` +
  `ConversationEmbedding` models + `retrieve_for_thread()`.
  Schema slice; mirrors K2."* The implicit assumption was
  that K8 is a fresh schema slice — design the migration,
  ship the models, add the retrieval helper.
- **Reality / outcome:** On opening K8 to scaffold the
  migration, the discovery: **all three of those models +
  retrieve_for_thread() landed during K2 in SESSION 138.**
  K2's commit shipped the full conversation-side schema as
  a sibling to KnowledgeDocument's, just without the
  ingestion-side pipeline. What was actually missing for
  K8 was `embed_message` (the Celery task) + the post-save
  signal on `ConversationMessage` that fires it. The K8
  work this session shipped exactly that — 11 backend
  tests + the task + the signal, no model migration.
- **Found by:** AI reading `apps/conversations/models.py`
  before drafting the K8 migration. The models existed;
  the scope-lock had over-counted what K8 needed to do.
- **Lesson:** **Before opening a scope-locked slice, read
  the modules it claims to touch — the scope-lock can be
  stale from earlier slice landings.** K0 was drafted at
  K-arc start; K2's actual implementation went further
  than K2's slice description (it shipped the conversation
  schema "while we were here"). The slice-lock didn't
  track the over-delivery, so K8 read as bigger than it
  was. **For this operator specifically:** opening a
  slice always starts with "what's already here?" — five
  minutes of reading the target modules before writing
  the migration prevents the next AI session from
  re-shipping work that already exists. Generalisation:
  scope-lock documents are a snapshot; the modules they
  reference are the ground truth.

## 2026-05-15 — Multi-failure-mode session: TIER_LIMITS edit shadowing + cross-arc isolation rule + replace_all hazard + hackathon-client coexistence

- **Context / claim:** SESSION 146's R1-R5 buildout
  surfaced four distinct failure modes worth carrying
  forward as separate rules. Bundling them here because
  they all fired in the same session — separate entries
  would scatter the same calibration moment across the
  log.
- **Reality / outcome:**
  1. **TIER_LIMITS edit shadowing** — twice the
     `realtime_sessions_per_month` Edit on
     `apps/billing/models.py` reported success but the
     R3 tier-limit test still failed. Recovery: read the
     file to verify state, then re-Edit with a slightly
     different context window. The pattern looked like
     Edit's `old_string` matched a *cached* view of the
     file from a prior read rather than disk. **Rule:**
     after any Edit on a hot file (one that other edits
     have touched in the same turn), read a small window
     of the target to confirm the change landed before
     moving on.
  2. **Cross-arc isolation `ALLOWED_FILES`** — R1's
     `test_models.py` creates a `Composition` to
     exercise the `RealtimeToolInvocation.produced_composition`
     cross-workspace check; R5's transcript tests create
     `Asset(TRANSCRIPT)` rows via the broker. Both
     tripped `apps/compositions/tests/test_isolation.py`
     until the new test paths were added to
     `ALLOWED_FILES` in the *composition* isolation test
     (not just the realtime one). **Rule:** every new
     test file that creates rows in a cross-arc model
     needs an `ALLOWED_FILES` entry in *both* isolation
     tests (and embeddings if it touches chunks). The
     isolation tests are the right gate — adding the
     path is a code-review event with a one-line note.
  3. **`replace_all=true` back-fill hazard** — three
     slices had back-fill commit attempts fail because
     `Edit replace_all=true` on the literal `(commit TBD)`
     matched *multiple* TBD markers and replaced them
     all to the same hash, which is wrong if they
     reference different slices. **Rule:** never use
     `replace_all=true` for back-fills like `(commit
     TBD)`. Use targeted Edits with a unique context
     window per occurrence.
  4. **Hackathon client coexistence** — R2's provider
     abstraction is the v2 path the R-arc consumes; the
     hackathon's 807-line `realtime_avatar_client.py`
     stays alongside it for the legacy `/api/*` surface
     (no retirement slice planned). **Rule:** when an
     arc has a hackathon implementation, read it for
     HTTP shapes / endpoint contracts — don't port from
     it. The hackathon code optimized for fewer
     abstraction layers; character-os optimizes for
     arc-by-arc substitution. Same Runway endpoint can
     have different consumer code in both files; that's
     fine.
- **Found by:** Test failures (1, 2) + Edit no-op
  symptom (3) + reading both clients before the R2
  provider design (4). All caught in-session, no
  downstream cost.
- **Lesson:** **For this operator specifically:** when a
  session adds a new arc, the first slice's test pass is
  also a check on every prior arc's isolation gate.
  Cross-arc isolation `ALLOWED_FILES` updates are
  cheaper than letting a new test file trip an unrelated
  isolation test on a stranger's session. Generalisation:
  defensive structural tests (isolation grep, repo-level
  lints) become noisier as the system grows — keep them
  by paying the maintenance cost (one `ALLOWED_FILES`
  line per new sanctioned test file), not by relaxing
  them.

## 2026-05-15 — Sub-slicing the over-scope-locked: R7, R8, and the one-slice-per-session calibration

- **Context:** SESSION 148 (R6 cross-session memory)
  landed in one focused single-slice session. The
  resulting calibration moment — "one slice per
  session is the natural unit when the discipline is
  honored" — got applied retroactively to the
  scope-locked R7 and R8 in subsequent sessions.
- **Direction:** Carry-forward calibration.
- **Detail:** R7 was scope-locked SESSION 142 as
  "tool catalog (6 tools, workspace-scoped) +
  RealtimeToolInvocation audit trail + approval-
  threshold modal" — one slice. R8 was scope-locked
  as "SPA `/spokespeople/:id/talk` route +
  `@runwayml/avatars-react` integration + cost
  forecasting + tool-approval modal." Both proved
  too large for the one-slice-per-session discipline.
  Sub-sliced at proposal time:
  - **R7 → R7.0 / R7.1 / R7.2 / R7.3** —
    foundation, sync tools + tier filtering, async
    dispatch + render_video, attach_memory + R6.1
    widen (SESSIONS 149-152).
  - **R8 → R8.0 / R8.1 / R8.2** — SPA foundation,
    tool-approval modal + cost forecast, SDK native
    invocation + cost ticker + WebRTC fallback
    (SESSIONS 153-155).
- **Found by:** Operator's SESSION 148 framing held
  across 7 subsequent slices. Each sub-slice landed
  in 1 session with full doc-with-commit discipline +
  inline test coverage. No catch-up passes needed
  (contrast SESSION 143's V3-V13 11-commit catch-up).
- **Lesson:** **For this operator specifically:** the
  one-slice-per-session unit is real, not aspirational.
  Scope-locks predate the calibration; treat the
  scope-lock as "the v1 contract about what
  eventually lands" rather than "the boundary of one
  commit." Sub-slice in the design doc at proposal
  time with the operator's explicit confirmation +
  update the slice table in the same commit batch.
  Generalisation: when a discipline calibrates after
  scope-locks land, audit the unshipped slices' sizes
  against the new discipline. Splitting at proposal
  time is free; splitting mid-implementation costs a
  session.

## 2026-05-15 — AI confidently wrong: `sendClientEvent` exists in the Runway SDK

- **Context:** R0 scope-lock (SESSION 142) said the
  Runway SDK's `<AvatarCall>` exposes
  "`onClientEvent` for tool invocations and
  `sendClientEvent` for narration back to the
  avatar's LLM." The narration loop was the basis
  for Q-r-2's planned resolution: server-side
  rejection records the reason, SPA sends the
  reason back via `sendClientEvent`, avatar
  narrates apologetically.
- **Direction:** AI was wrong; operator's R8 design
  + my own AvatarCall integration in R8.2 surfaced
  it.
- **Detail:** Runway's `@runwayml/avatars-react@0.16.0`
  exposes `useClientEvent` / `useClientEvents` /
  `onClientEvent` — all *listeners* for events
  FROM the avatar. There's no `sendClientEvent` in
  the public API. `clientTool(...)` lets you
  register tools whose handlers run client-side,
  but the handler's return value doesn't appear to
  flow back to the avatar's LLM as a server-pushed
  narration cue.
- **Found by:** SESSION 155 reading
  `node_modules/.pnpm/@runwayml+avatars*/dist/*.d.ts`
  to wire `AvatarSessionInner`. The R8.2 plan
  assumed `sendClientEvent` based on the
  scope-lock — first verification was attempting
  the import.
- **Lesson:** **For this operator specifically:**
  scope-locks codify the v1 *intent*; SDK feature
  names in a scope-lock are *hypotheses* until
  exercised by code. The R0 scope-lock was correct
  about every other API surface (the avatar invokes
  via data channel, the SDK handles WebRTC
  handshake, `(sessionId, sessionKey)` is the
  client mount surface); just wrong about one
  return-channel name. Generalisation: when a
  scope-lock references SDK features, verify each
  one before relying on it for downstream scope. The
  fix for this miss was straightforward — Q-r-2
  shifted to "partial v1 resolution; narration is
  operator-mediated" — but the misdirection cost
  ~10 minutes of looking for an API that doesn't
  exist.

## 2026-05-15 — Near-miss: type-system + runtime config drift on testing-library

- **Context:** R8.0 (SESSION 153) wired
  `@testing-library/jest-dom` into vitest's setup
  file. Tests ran clean. SPA build also passed —
  because tsc didn't traverse the one R8.0 test
  file that used `toBeInTheDocument`.
- **Direction:** AI noticed in time (R8.1 surfaced
  it).
- **Detail:** R8.1 (SESSION 154) added more matcher
  calls in the new modal test. Build broke
  immediately:
  `Property 'toBeInTheDocument' does not exist on
  type 'Assertion<HTMLElement>'`. The fix was one
  line in `tsconfig.app.json`:
  `"types": ["vite/client", "vitest/globals",
  "@testing-library/jest-dom"]`. But the gap had
  been latent for an entire session — runtime
  worked while build was secretly missing the
  types.
- **Found by:** SPA build failure on R8.1's new
  modal test file.
- **Lesson:** **For this operator specifically:**
  when wiring a test framework plugin at runtime,
  also wire it at type-check time. One-test
  consumers paper over the gap. Generalisation:
  type system + runtime config are two
  configuration surfaces for the same logical
  feature; treat them as a pair. Vitest setup
  files + tsconfig types are the same shape — once
  per project, not per test.

## 2026-05-15 — Near-miss: fake timers + setSystemTime double-count

- **Context:** SESSION 155 R8.2 CostTicker tests
  drive fake timers to verify the 1-second
  interval. First draft used:
  `vi.setSystemTime(new Date(ANCHOR + 30_000))` +
  `vi.advanceTimersByTime(1000)` to simulate "30s
  elapsed, interval fires."
- **Direction:** AI noticed in time (test failure
  surfaced it).
- **Detail:** Vitest's `vi.useFakeTimers()` makes
  `Date.now()` mock-controlled. `setSystemTime`
  sets the clock to ANCHOR + 30s.
  `advanceTimersByTime(1000)` then advances BOTH
  the timer queue AND the system clock by 1s. So
  at interval-fire time, `Date.now()` returns
  ANCHOR + 31s. The component reads `elapsed =
  31`, test asserts `30`, fail.
- **Found by:** Test failure with off-by-one in
  `data-elapsed-seconds` attribute. Initially
  looked like a state-management bug; the timer
  arithmetic was the actual cause.
- **Lesson:** **For this operator specifically:**
  when using `vi.useFakeTimers()`, pick ONE control
  surface — `setSystemTime` for arbitrary jumps OR
  `advanceTimersByTime` for "elapse N ms + fire
  intervals." Mixing them double-counts.
  Generalisation: when a test framework controls
  both clock-time and timer-queue advancement,
  identify which APIs touch which channel before
  composing them. The double-count is a recurring
  shape in fake-timer libraries (Jest's
  `jest.useFakeTimers()` has the same gotcha).

## 2026-05-15 — AI confidently wrong (deliverable framing): "shipped" before operator review

- **Context:** SESSION 158 fired the first real-Runway
  composition (Donny + trafilatura doc, talking_head).
  Composition completed; cost stamped; MP4 URL
  returned. AI's response message led with "✅
  Marketing video shipped."
- **Direction:** AI was operationally precise but
  operator-facing wrong; operator flagged the gap
  ("Donny has some issues with his teeth").
- **Detail:** The pipeline ran cleanly — every layer
  fired, the composition reached `status=completed`,
  Runway returned a signed MP4. By system criteria,
  shipped. But the AI hadn't watched the video, and
  the model output had a visible quality issue
  (lip-sync artifacts on sustained close-up speech).
  Operator's framing — "the video is okay but Donny
  has some issues with his teeth" — surfaced the
  distinction between "system completed" and
  "deliverable ready to publish."
- **Found by:** Operator review of the actual MP4
  after AI's "shipped" claim.
- **Lesson:** **For this operator specifically:**
  when an AI-driven slice produces operator-facing
  media (video, audio, image, text-someone-will-read),
  "shipped" framing belongs to the operator after
  they've reviewed the output — not to the AI after
  the pipeline closes. The right AI-facing framing
  is "system completed: cost $X, MP4 at <url>,
  please review" — present the deliverable as
  artifact, let the operator's review be the
  shipping signal. **Generalisation:** when a
  deliverable's quality depends on a model's output
  (not just the pipeline returning 2xx), the AI's
  success criterion is "the pipeline ran cleanly,"
  not "the deliverable is good." Conflating the two
  was the failure mode this session.

## 2026-05-15 — Operational calibration: avatar voice × lip-sync quality varies

- **Context:** SESSION 158 second render switched
  from Donny (`drew` voice) to Sasha (`clara` voice)
  after the dental-artifact issue. Same recipe, same
  knowledge doc, shorter script. Render came out
  clean.
- **Direction:** Carry-forward operational
  calibration.
- **Detail:** Runway's avatar lip-sync model produces
  visible artifacts on some voice + avatar
  combinations. The R-arc scope-lock treated voice as
  a Runway pricing / metering concern; it's also a
  quality concern operationally. First two real
  renders this session:
  * `drew` voice + Donny's avatar bake → dental
    artifacts on sustained speech.
  * `clara` voice + Sasha's avatar bake → clean.
  Whether the variable is voice, avatar bake, script
  length, or the intersection is unknown without more
  combinations tested.
- **Found by:** Operator review of the first render.
- **Lesson:** **For this operator specifically:** when
  a future cast member or voice lands, run a 10-second
  talking_head smoke render before declaring them
  production-ready. The cast-management CLI
  (`seed_cast`) could grow a `--smoke-test` flag that
  fires a tiny render + auto-flags artifacts visible
  in operator review (v2 work; v1 doesn't need it).
  **Generalisation:** when a feature shipping
  end-to-end depends on a third-party model's output
  quality, the system test ("did the pipeline run?")
  is necessary but not sufficient. A separate quality
  test ("does the output meet the operator-facing
  bar?") needs to ride alongside. The slice plan for
  R-arc didn't budget for this; future model-output
  arcs should.

## 2026-05-15 — Near-miss: R9 hardcoded placeholder was accurate enough

- **Context:** R9 (SESSION 156) shipped with
  `cost_per_minute_micros = 80_000` as a
  "conservative placeholder until real rates ship."
  SESSION 158's two real renders cost $0.25 each
  (~$0.43/min for partial-minute renders).
- **Direction:** Near-miss / AI calibration win.
- **Detail:** The R9 placeholder was a stub-and-refine
  decision — we didn't have real Runway billing data
  at R9 time. The placeholder estimate matched real
  spend within ±50% (close enough that the SPA's
  cost-forecast pill doesn't over- or under-state by
  more than a multiple). No urgent refinement needed.
- **Found by:** First two real renders this session
  surfaced real $/min data.
- **Lesson:** **For this operator specifically:**
  stub-and-refine is a valid v1 pattern when the
  stub's wrongness is bounded AND the operator-facing
  failure mode is graceful. Here: bounded (~$0.43/min
  real vs $0.08/min stub — off by ~5x, but
  over-forecasts; operator under-uses budget rather
  than overspends). Graceful (UI shows a
  conservative number; never a panic-inducing
  surprise). Generalisation: track placeholder
  constants explicitly so the first real-data event
  triggers the schedule for refinement. The R9
  placeholder's "next real render" check is now done;
  the refinement schedule moves from "TODO" to "when
  R9 finally ships per-provider rates."

## 2026-05-15 — Architectural calibration: cross-repo workflow worked

- **Context:** SESSION 159 closed drift-prevention items 2
  + 3 from the SESSION 147 audit backlog. The items lived on
  character-os's backlog but the right implementation site
  was the sibling `context-kit` repo (the tool that runs the
  drift checks). Work happened entirely in context-kit;
  character-os saw only docs changes (anchor frontmatter
  backfill + the SESSION 159 handoff + this entry).
- **Direction:** Carry-forward architectural.
- **Detail:** Two commits in two repos — context-kit
  `9590737` (the `handoff write` subcommand + tests + docs)
  and character-os SESSION 159 (the doc-only commit). The
  character-os backlog entry closes even though no
  character-os code changed, because the tool that ships
  closes the *capability* the backlog entry tracked. The
  alternative — porting the subcommand into character-os
  itself — would have duplicated logic across every project
  using the pattern.
- **Found by:** Operator framing during SESSION 159 — "let's
  do drift-prevention items 2 and 3."
- **Lesson:** **For this operator specifically:** when a
  backlog item names a *capability* (a thing the workflow
  should be able to do) rather than a *feature in this repo*,
  evaluate whether the right implementation site is the
  tool or the project. The tool repo wins when the
  capability is general-purpose. The project repo records
  the trigger event; the tool repo owns the solution.
  **Generalisation:** when shipping pattern-level
  infrastructure, the test is "would the next project to
  hit this drift class benefit from the fix?" If yes —
  ship in the tool, not the project. The project's
  backlog still closes; it just closes on a different
  commit in a different repo.

## 2026-05-15 — AI confidently wrong (K6 hallucination): Donny's first marketing video contained fabricated source claims

- **Context:** SESSION 158 shipped Donny's first
  real-Runway render against a custom-titled Wikipedia RAG
  page attached to him as his only knowledge document. The
  pipeline returned 2xx; cost stamped at $0.25; MP4 URL
  signed and persisted. The render was framed as "shipped
  but visual quality bad" (dental artifacts on `drew`
  voice). SESSION 159 fact-checked the *script* after the
  operator asked to verify what Donny actually said.
- **Direction:** AI confidently wrong (system + AI).
- **Detail:** Donny's ~80-word script makes three
  substantive claims:
  1. character-os uses **trafilatura** for URL ingestion.
  2. The doc he "just studied" with the Character OS team
     taught him this.
  3. Trafilatura is "the cleanest text extraction you'll
     see from any AI tool" with Wikipedia as its
     "absolute home turf."
  Verification against the source doc
  (`KnowledgeDocument 33c07feb-...`, 2,352 words from
  `https://en.wikipedia.org/wiki/Retrieval-augmented_generation`):
  * Claim 1: **TRUE about the product** —
    `shell/apps/embeddings/url_fetch.py` imports
    `trafilatura` and calls `bare_extraction()`. Landed
    K7 SESSION 140.
  * Claim 2: **FALSE** — the attached doc is the Wikipedia
    article *about RAG-the-concept*. Zero occurrences of
    "trafilatura," zero occurrences of "Wikipedia" across
    22 chunks. The doc Donny supposedly learned from
    teaches nothing about either word.
  * Claim 3: **FABRICATED** — superlative marketing;
    "Wikipedia is its home turf" is not in any chunk.
  Two leak vectors are plausible. The operator-given
  custom title for that doc was *"Wikipedia is
  trafilatura's home turf"* — note the verbatim phrase
  in claim 3.
  `script_synthesis.py:211-214` only feeds `chunk_text`
  (not `title`) into the prompt, so vector 1 requires
  an operator-prompt path that referenced the title.
  Vector 2 is direct: gpt-5-mini drew on its own training
  knowledge of trafilatura while pretending to cite
  chunks. The K6 system prompt at line 249 says
  explicitly: *"Use facts only from the knowledge chunks
  the user supplies. Do not invent product details,
  prices, or features. If a fact isn't in the chunks,
  leave it out."* The model ignored the instruction.
- **Found by:** Operator review during SESSION 159 ("verify
  the facts of the statements that were made"). Forensics:
  Django shell query against `Composition
  e485d9f9-...`, `CompositionStep`, `KnowledgeDocument
  33c07feb-...`, and per-chunk text search for the named
  terms.
- **Lesson:** **For this operator specifically:** the K6
  system-prompt-only no-invention contract is insufficient
  in practice. `gpt-5-mini` hallucinates factual claims
  that *happen to be true about the product* even when the
  retrieved chunks contain zero supporting content. The
  failure mode is asymmetric and dangerous: the claim
  sounds authoritative because (a) it's actually true and
  (b) the model frames it as coming from the source the
  spokesperson "studied." A reviewer who knows the product
  reads it as "Donny got the trafilatura fact right";
  a reviewer who knows the source doc reads it as "Donny
  made stuff up." Both are correct simultaneously.
  **Generalisation:** when a knowledge layer instructs the
  model to cite chunks and the model already knows the
  truth via training data, the prompt-only no-invention
  contract leaks. The fix isn't a stronger prompt —
  prompt strength is already maxed at "Use facts only from
  chunks. Do not invent. Leave it out." — it's a
  post-synthesis claim verifier that runs after the script
  comes back: extract claims, check each against retrieved
  chunks, fail or retry. **Queued as K6.4.** Second
  carry-forward: operator-given custom doc titles are a
  hostile prompt-stuffing surface even when the title
  isn't directly fed to the LLM, because the title biases
  the operator's mental model of what the doc contains,
  which biases the operator brief, which biases the model.
  Doc titles should match doc content; the system should
  warn (or refuse to embed) when they don't.

## 2026-05-15 — Carry-forward methodology: operator-mediated dogfooding caught the silent staleness

- **Context:** SESSION 159 shipped `context-kit handoff
  write` against character-os SESSION 158 as the live
  target. The dry-run output named the exact drift the
  SESSION 147 audit had flagged: four anchor docs sitting
  with `generated: 2026-05-13` and no `last_revised:`
  field, across 50+ sessions.
- **Direction:** Carry-forward methodology.
- **Detail:** Reading the SESSION 147 audit summary felt
  different than reading the SESSION 159 dry-run output.
  The audit *named* the drift class as a category;
  the dry-run *showed the count of docs affected* and
  named each by path. The smoke output is the truest
  validator of "does this catch the thing we said it
  would catch?" — boring dry-run output (all `unchanged`)
  would have indicated either a leaky abstraction or a
  drift class that wasn't actually present.
- **Found by:** Dry-run output during SESSION 159's smoke
  test.
- **Lesson:** **For this operator specifically:** when
  shipping pattern-level infrastructure (drift checks,
  invariant validators, doctor-style health probes), land
  it in dry-run mode against the original problem repo
  before declaring it done. The smoke output is the
  validator. If the dry-run is loud (multiple `would
  restamp` / `would warn` lines), the abstraction is doing
  real work. If it's boring, the abstraction is leaky or
  the drift wasn't there. **Generalisation:** treat the
  first real-target dry-run as a contract test, not a
  demo. The output proves the spec.

## 2026-05-15 — Architectural calibration: v1 verifier caught the load-bearing case despite documented limitation

- **Context:** K6.4 (SESSION 160) shipped substring-based
  named-entity extraction. The scope-lock acknowledged that
  lowercase technology names (`trafilatura`, `pgvector`)
  would slip through v1 — the regex extractor only catches
  capitalized words 4+ chars + multi-word capitalized
  phrases + numerics. The trafilatura miss looked like a
  real gap when scope-locking.
- **Direction:** Carry-forward architectural.
- **Detail:** Replaying Donny's SESSION 158 script against
  the v1 verifier flagged `Wikipedia` (the load-bearing
  hallucination: "Wikipedia is its absolute home turf")
  while letting `trafilatura` slip through. But trafilatura
  is *factually true about the product* (`apps/embeddings/
  url_fetch.py` does use trafilatura); the Wikipedia
  "home turf" claim is a pure fabrication. v1 catches the
  unambiguous fabrication and misses the
  arguably-true-but-unattributed claim. The cost of catching
  trafilatura in v2 (semantic similarity, small-model NER,
  or curated lowercase tech list) trades implementation
  complexity for a less-bad failure mode.
- **Found by:** Smoke replay of the actual SESSION 158
  Composition `e485d9f9-...` script + chunks during
  SESSION 160 closing checks.
- **Lesson:** **For this operator specifically:** when
  scope-locking a verifier / detector / classifier with
  a known coverage gap, identify which case in the gap is
  *load-bearing* (catching it justifies the slice) vs
  *also-nice-to-catch* (catching it would be ideal). v1 is
  allowed to explicitly miss the second class if catching
  it requires substantially more machinery. Anchor the
  miss as a regression test so the upgrade is visible.
  **Generalisation:** "v1 misses X but catches Y" is a
  sufficient ship gate when Y is more dangerous than X.
  Here: a fabrication (Y) reads more confidently than
  an unattributed-but-true claim (X), so catching Y is
  the higher-leverage v1 win.

## 2026-05-15 — Near-miss: stoplist grew during test runs, not before

- **Context:** K6.4 (SESSION 160)'s named-entity extractor
  filters sentence-starter false positives via a hand-
  curated stoplist of common English words. The first
  draft stoplist had ~80 entries
  (`the`/`that`/`turns`/`drop`/...). First test run caught
  two false positives the stoplist had missed:
  `Cleanest` and `Welcome`. Both at sentence starts in
  the test fixtures.
- **Direction:** Near-miss / AI calibration win.
- **Detail:** If the verifier had shipped to production
  with those misses, the failure mode would have been
  "verifier rejects legitimate renders that start with
  superlative or greeting words" — a *new* failure class
  more annoying than the original hallucination problem
  this slice exists to fix. The two missed words were
  caught by tests written *before* the stoplist was
  declared done. One-line edits closed both. The slice
  shipped without the false-positive class reaching
  operators.
- **Found by:** Initial test run of
  `test_claim_verifier.py` —
  `test_extract_skips_common_sentence_starters` and
  `test_verify_claims_returns_empty_on_clean_script`.
- **Lesson:** **For this operator specifically:** when
  shipping a detector with a hand-curated stoplist /
  allow-list / known-pattern table, drive a few false-
  positive tests *before* declaring the table done. The
  test set is what makes the table a living list rather
  than a one-shot guess. Stoplist coverage is testable;
  stoplist correctness isn't until real data exposes
  the gap. **Generalisation:** for any classifier with a
  hand-curated stop / allow list, the test suite should
  include both representative true-positive cases AND
  representative false-positive cases the list is
  supposed to guard against. The false-positive test is
  what catches the curator's bias.

## 2026-05-15 — Architectural calibration: Strict mode is a forcing function, not just a gate

- **Context:** K6.4 (SESSION 160) shipped the
  post-synthesis verifier with Warn as the default and
  Strict as opt-in. SESSION 161 dogfooded Strict mode
  against the live system. The K6.4.1 stoplist fix
  closed the `'Modern'` false-positive class. Repeated
  the dogfood: same operator prompt that produced a
  `'Modern'`-claiming hallucination in K6.4 now produced
  a chunk-grounded script in K6.4.1.
- **Direction:** Carry-forward architectural.
- **Detail:** The K6.4 design framed the verifier as a
  *gate* — synthesis runs, verifier checks, gate opens
  or blocks. The dogfood revealed a second-order effect:
  under strict-mode pressure, K6's outputs are
  qualitatively different. Same operator prompt, same
  retrieved chunks, same model, same temperature —
  different output distribution because the operator's
  prompt-writing has shifted to "what will pass the
  verifier" and the model's generation surface has
  shifted to "what survives substring-match against the
  chunks." The verifier is a forcing function on the
  synthesis, not just a downstream filter.
- **Found by:** Three real-Runway dogfood renders under
  `K6_CLAIM_VERIFIER_MODE=strict` during SESSION 161 —
  all three produced chunk-grounded scripts; none
  triggered the verifier.
- **Lesson:** **For this operator specifically:** when
  designing a constraint layer (verifier, post-filter,
  validator), expect downstream behavior shifts. The
  constraint isn't just "block bad output" — it changes
  the operator's mental model of what the system will
  generate, which biases prompts, which narrows what the
  system generates. **Generalisation:** anchor design
  decisions on the system's *equilibrium* behavior with
  the constraint active, not just the gate's
  immediate semantic. A constraint that's "always
  active in Warn mode" generates one set of equilibrium
  behaviors; "opt-in Strict" generates another. Worth
  thinking about which equilibrium you want before
  picking the default mode.

## 2026-05-15 — Near-miss: bypass case looks identical to clean render

- **Context:** First strict-mode render attempt in
  SESSION 161 fired without `OPENAI_API_KEY` in the
  shell environment. The pipeline still completed —
  retrieval degraded, synthesis didn't run, K6 fell
  back to the operator's prompt verbatim, verifier
  never ran. Composition row showed
  `status=completed`, `verification_warnings=[]`,
  `rejected_synthesis=""` — visually identical to a
  successfully-verified render.
- **Direction:** Near-miss.
- **Detail:** The operator's prompt happened to contain
  `"Wikipedia"` and `"Character OS"`. The render fired
  to Runway and cost $0.25. If strict mode had actually
  run, those terms would have been allow-listed by
  `KNOWN_PLATFORM_TERMS` (Character OS) and operator-
  prompt corpus (Wikipedia), so the outcome would have
  been the same. But the operator couldn't *audit*
  whether the result was verified or just trusted —
  no flag on the composition row distinguishes the
  two cases.
- **Found by:** SESSION 161 dogfood post-mortem — the
  operator noticed the first render hadn't actually
  exercised the verifier despite the env var being set.
- **Lesson:** **For this operator specifically:**
  distinguish "verifier passed" from "verifier didn't
  run." `ScriptResult.used_knowledge` already encodes
  this internally; surface it onto the composition row
  in a future slice (queued as K6.4 v1.2 —
  `Composition.verification_status` TextChoices
  `verified | trusted_passthrough | skipped`).
  **Generalisation:** when a pipeline degrades
  gracefully (retrieval failure → operator prompt
  verbatim), the degraded path's output must be
  visually distinguishable from the happy path's
  output. Silent degradation that produces the same
  row shape is the failure mode that hides bypass
  events. Audit trails want explicit state, not
  implicit absence.

## 2026-05-15 — AI confidently wrong (K6.5): verifier punished an honest refusal

- **Context:** K6.5 (SESSION 162) ported the K6.4 claim
  verifier onto `conversation_synthesis.py`. Live
  strict-mode dogfood against Donny's conversation thread.
  Three prompts tested; the third was the calibration
  event. User asked "What's the library you use under
  the hood for parsing pages?" The Wikipedia-RAG doc
  attached to Donny contains zero information about
  parsing libraries.
- **Direction:** AI confidently wrong (system + slice
  design).
- **Detail:** The model responded *honestly*: "Short
  answer: the workspace docs you gave me don't say
  which library we use to parse pages. What I'd like to
  do next is clarify what you mean by 'parsing pages'
  (HTML scraping, PDF/text extraction, or...)." That's
  the right answer — it refuses to invent, asks for
  clarification, names the relevant problem space. But
  the strict-mode verifier rejected it on
  `'Short', 'Which', 'HTML'`: words used in the refusal
  meta-language, not as fact claims. The substring
  matcher can't tell the difference between *"the model
  invented HTML as a product fact"* and *"the model
  named HTML while clarifying what kind of parsing the
  user might mean."* The 422 returned to the user
  contained no spokesperson reply — the operator never
  saw the honest answer.
- **Found by:** Manual probe of the strict-mode
  conversation surface during SESSION 162 close-out
  dogfood. Took three prompts to surface; would have
  remained latent under the unit tests, which inject
  pre-known hallucinations.
- **Lesson:** **For this operator specifically:** when
  a verifier / classifier / guardrail ships, maintain a
  curated set of *honest refusal* prompts that should
  always pass through. Treat any change to the verifier
  stack as gated on those staying green. The K6.5 inline
  fix widened the stoplist with refusal-pattern words
  (`Short, Which, Frankly, Honestly, Plain, ...`), but
  the underlying class — "honest meta-language uses
  meta-terms not in the source" — can resurface. v2
  upgrade should add a heuristic for refusal context.
  **Generalisation:** when a filter's purpose is "block
  X, pass Y," and X / Y look identical to the filter's
  primitive, write test cases that include legitimate-Y
  examples alongside the blocked-X ones. Failing to
  distinguish inverts the filter's purpose. The K-arc
  verifier work needs both hallucination test fixtures
  AND honest-refusal test fixtures from here on.

## 2026-05-15 — Near-miss: live dogfood caught what unit tests didn't

- **Context:** K6.5 shipped with 6 unit tests in
  `test_k6_5_verifier.py` (warn-mode persistence,
  strict-mode raise, off-mode bypass, user-prompt
  allow-list, API 201 in warn, API 422 in strict). All
  6 used hand-crafted hallucination payloads as the
  LLM-output fixture. None used an honest-refusal
  payload. The unit suite went green. The live dogfood
  surfaced the honest-refusal failure class within three
  prompts.
- **Direction:** Near-miss / AI calibration win.
- **Detail:** The slice would have shipped with the bug
  latent. Unit tests confirmed the slice handles what
  the test fixture forces; the live probe confirmed it
  handles what the model actually produces. SESSION 158
  had already taught this lesson once ("AI's 'shipped'
  framing belongs to the operator after review"), but
  the K6.5 test design didn't yet incorporate it — the
  K6.4 path under test always assumed the LLM
  hallucinates because the fixture forced it to.
- **Found by:** Live operator-mediated dogfood at K6.5
  close-out. Three prompts in, the verifier rejected an
  honest refusal. Without the dogfood, the slice would
  have shipped and the operator would have hit the
  failure mode in production.
- **Lesson:** **For this operator specifically:** when
  a slice's risk surface is "the model behaves
  unexpectedly," at least one live-system dogfood probe
  is part of the ship gate. **Generalisation:** for
  verifiers / classifiers / guardrails specifically,
  the **third or fourth real prompt** is often the
  calibration event the test fixture can't anticipate.
  The first two prompts tend to be on the happy path;
  the third stress-tests the edge cases. Budget for
  3-5 live-system probes alongside the unit suite at
  every verifier-related slice close-out.

## 2026-05-15 — Architectural calibration: metadata-driven forms paid off

- **Context:** K6.4 v1.1 (SESSION 163) needed a
  Strict/Warn/Off select on the make-video form.
  Character OS's SPA uses a metadata-driven form
  renderer — recipe metadata in
  `apps/compositions/recipes.py` declares each field
  + the renderer emits the right input.
- **Direction:** Carry-forward architectural.
- **Detail:** Adding the new field took two edits:
  declare `_VERIFIER_MODE_FIELD` once at the top of
  `recipes.py`, then add it to the `talking_head`
  recipe's `fields` tuple. Zero form-renderer changes,
  zero SPA route changes for the make-video path,
  zero new serializer fields, zero new TypeScript
  schemas. The metadata layer absorbed the new field
  without ceremony. By contrast, the conversation
  composer (non-metadata-driven) needed full SPA
  component additions: a `VerifierModeSelect`
  component, state plumbing, schema work — comparable
  shape to the make-video toggle but ~5x more code
  to land.
- **Found by:** Reviewing the diff at K6.4 v1.1
  close-out — the make-video toggle was buried in a
  metadata edit; the conversation toggle dominated the
  SPA diff.
- **Lesson:** **For this operator specifically:**
  metadata-driven surfaces compound. When the same
  pattern needs to scale across many similar things
  (17 recipes), invest in the metadata layer. Each
  additional field arrives nearly free. The cost is
  the upfront renderer; the return is durable
  cheapness. **Generalisation:** before adding the
  Nth ad-hoc field to an ad-hoc form, check whether
  the surface should be metadata-driven. The break-
  even point is usually low (3-5 similar surfaces).
  After that, every new field added the ad-hoc way is
  pure tech debt against an inevitable migration.

## 2026-05-15 — Methodology calibration: SPA tests went lighter than expected

- **Context:** K6.4 v1.1 (SESSION 163) added three
  user-visible SPA surfaces (toggle, rejection panel,
  inline warning bubble) but only 3 vitest cases —
  all on the schema parsing layer
  (`verifierRejectionSchema`). No component-level
  tests for `VerifierRejectionPanel`,
  `VerifierModeSelect`, or `VerifierInlineDetail`.
- **Direction:** Carry-forward methodology.
- **Detail:** The components are small (50-100 lines
  each), encode no real logic (they render flat
  pre-shaped data), and consume well-tested backend
  shapes via zod-validated API types. A UI regression
  that doesn't break the schema parsing wouldn't be
  caught by the vitest suite — visual confirmation
  needs operator-driven SPA testing. The trade-off
  was deliberate: ~15 minutes per component test vs.
  ~5 minutes to spot-fix a UI regression an operator
  surfaces.
- **Found by:** Reviewing test coverage at K6.4 v1.1
  close-out before commit. Considered adding
  component tests but the cost-vs-coverage math
  argued against.
- **Lesson:** **For this operator specifically:**
  small UI components hand-tied to a well-tested API
  can ship with schema-only vitest coverage when
  the visual is straightforward and the data shape
  is the load-bearing contract. Component tests
  earn their weight when the component encodes
  significant logic (interaction state, conditional
  rendering, etc), not when they wrap a flat render.
  **Generalisation:** test depth should follow logic
  depth, not file count. A 100-line component that's
  a flat render of pre-shaped data needs less testing
  than a 30-line function that branches across 4
  paths. Don't equate "user-visible" with "test-
  heavy" — equate "logic-heavy" with "test-heavy."

## 2026-05-15 — Architectural calibration: recipe rollouts get cheaper as the metadata layer matures

- **Context:** K6.4 v1.1 (SESSION 163) added
  `_VERIFIER_MODE_FIELD` once + applied it to 1 recipe
  (`talking_head`). K6.4 v1.2 (SESSION 164) rolled the
  same field to the three remaining K6-aware recipes.
- **Direction:** Carry-forward architectural.
- **Detail:** The v1.2 rollout was ~15 minutes total
  for 3 recipes: 3 one-line tuple insertions (the
  `RecipeField` reference) + 3 starter-signature
  additions (the `verifier_mode` kwarg + a 3-line
  step-params copy). Zero form-renderer changes,
  zero SPA changes (the field auto-renders), zero
  serializer changes (the field auto-flows via
  `resolve_kwargs`). By contrast the v1.1 work — adding
  the same single field to the metadata model — was a
  couple of hours including the SPA conversation
  composer side (which is NOT metadata-driven). The
  marginal cost of the Nth recipe after the metadata
  invariant is established approaches zero.
- **Found by:** Reviewing the v1.2 diff at close-out —
  the recipe edits were tiny mechanical patches once
  the design pattern was set.
- **Lesson:** **For this operator specifically:** when
  reusable field templates land, roll them to siblings
  while the design is fresh. The first 1 rollout is
  design work; the rest is mechanical. Batching v1.x
  rollouts with the field's debut is cheaper than
  coming back later when the operator has flipped
  contexts. **Generalisation:** metadata-driven
  surfaces have superlinear payoff. The first field
  costs effort O(renderer + field); each subsequent
  field is O(field). The total cost of N similar fields
  is O(renderer + N) vs O(N·renderer) for ad-hoc
  surfaces. Worth quantifying at design time.

## 2026-05-15 — Near-miss: dataclass evolution + MagicMock leaked through ORM

- **Context:** K6.4 v1.2 refactored
  `_maybe_synthesize_script` from a 3-tuple to a 4-tuple
  (added `verification_status`). One existing test
  patches `build_render_brief` with a `MagicMock()` and
  sets only `.brief` and `.chunk_ids` explicitly. The
  new code path reads `.verification_status` from the
  mock — MagicMock lazily creates the attr as another
  MagicMock, which then gets passed to the Django ORM
  field assignment.
- **Direction:** Near-miss / AI calibration win.
- **Detail:** The ORM raised a confusing
  `FieldError: Aggregate functions are not allowed in
  this query (verification_status=<MagicMock
  name='mock.verification_status.resolve_expression()
  .resolve_expression()' id='...'>).` — diagnostically
  correct but operationally opaque. The root cause was
  "MagicMock leaked into ORM assignment because the
  test fixture didn't stamp the new attr." The fix
  was one line on the fixture; cost was ~5 minutes
  of confused diff inspection.
- **Found by:** Running the targeted regression suite
  after the primitive refactor. Test failed; error
  trace pointed at the ORM layer; root cause walked
  back to the unset MagicMock attr.
- **Lesson:** **For this operator specifically:** when
  adding new fields to a dataclass that's mocked
  elsewhere, audit the mocks for attrs the new code
  path will read. **Generalisation:** Python's
  duck-typing + MagicMock's structural typing means
  dataclass evolution + mocks have a sharp edge.
  Pyright would catch this on a real type; MagicMock
  is invisible to static analysis. Two mitigations: (a)
  prefer real dataclass instances in tests when
  practical, (b) when MagicMock is necessary, treat
  every new dataclass attr as a fixture-touch event.

## 2026-05-15 — Architectural calibration: watchdog reports surface problems in the wrong layer

- **Context:** K6.4 stoplist watchdog (SESSION 165) ran
  against the live DB. Surfaced `Drop a Wikipedia` as a
  "sentence-initial false-positive candidate" and
  recommended adding `"drop a wikipedia"` to the
  stoplist.
- **Direction:** Carry-forward architectural.
- **Detail:** The recommendation can't actually be applied —
  `_COMMON_PROPER_NOUN_FALSE_POSITIVES` is a single-word
  set; multi-word entries don't match the extractor's
  per-token check. The real problem is upstream:
  `_MULTIWORD_CAPS_RE` includes `a` as a joining word,
  so `"Drop"` (capitalized sentence-start) + `"a"` +
  `"Wikipedia"` parses as one multi-word entity. The
  fix lives in the regex / multi-word extraction layer,
  not the stoplist.
- **Found by:** Reading the watchdog's "Suggested
  additions" output during the SESSION 165 live run.
- **Lesson:** **For this operator specifically:** when a
  scripted reporter recommends a fix the receiving
  subsystem can't apply, the report is correctly
  identifying a problem but in the wrong layer.
  Treat the recommendation as signal that the *matcher*
  needs tightening, not that the stoplist needs widening.
  **Generalisation:** classifier/filter pipelines
  have multiple layers; an event flagged by one layer
  may be fixable only at a different layer. Reporters
  should surface the event + let the operator decide
  which layer to touch — auto-applying the reporter's
  suggestion risks fixing the symptom in the wrong
  place.

## 2026-05-15 — Methodology calibration: test isolation has its own stoplist (ALLOWED_FILES)

- **Context:** K6.4 stoplist watchdog (SESSION 165) added
  a new test file (`test_stoplist_watchdog.py`) that
  seeds `Composition` rows to exercise the warn-mode
  "no text context" branch. That tripped the V1
  isolation guard
  (`test_only_composition_module_writes_composition_tables`)
  which restricts who can call
  `Composition.objects.create`.
- **Direction:** Carry-forward methodology.
- **Detail:** The fix was a one-line edit to the
  `ALLOWED_FILES` set in `test_isolation.py` — the same
  hand-curated allowlist pattern as the verifier's
  stoplist. Both guards mirror each other: a strict
  default + a curated allowlist + a CI failure when
  the allowlist is out of sync. The cost of adding to
  the list is one line with a code-review-style note;
  the cost of forgetting is a CI failure that
  explains itself.
- **Found by:** Full test suite run after writing the
  new watchdog tests. CI surfaced the violation with
  an actionable error message.
- **Lesson:** **For this operator specifically:**
  V1's privacy-anchor contract uses the allowlist
  pattern + clear violation messages — that's the
  shape every "default-strict + curated exceptions"
  guard should take. **Generalisation:** when shipping
  a strict-by-default guard, pair it with (a) a
  curated allowlist that operators can append to,
  (b) an error message that explicitly mentions the
  allowlist + a code-review note convention. Both
  pieces together make the guard discoverable,
  modifiable, and self-documenting. K6.4's stoplist
  and the V1 isolation allowlist are mirror images;
  the K-arc work has been compounding this pattern.

## 2026-05-15 — Architectural calibration: curated lists carry implicit semantics — naming matters

- **Context:** K6.4 v2 (SESSION 166) added
  ``KNOWN_TECH_TERMS`` alongside the existing
  ``KNOWN_PLATFORM_TERMS``. Both start with ``KNOWN_*``
  and look at first glance like parallel allow-lists.
  They aren't.
- **Direction:** Carry-forward architectural.
- **Detail:** ``KNOWN_PLATFORM_TERMS`` is an
  *allow-list* — entries flow into ``build_corpus()`` so
  the substring check finds them and they pass through
  unchecked (Character OS is always allowed regardless of
  chunk content). ``KNOWN_TECH_TERMS`` is the opposite —
  it's an *extraction trigger*. Entries get pulled out of
  the script as named entities by the new lowercase
  extractor, then checked against the corpus same as
  proper nouns. The semantics are nearly inverse.
  A future reader who skims and adds ``stripe`` thinking
  they're whitelisting Stripe-the-payment-processor gets
  the opposite outcome: their script can no longer
  casually mention Stripe without it appearing in the
  chunks.
- **Found by:** Reviewing the v2 diff at close-out —
  spotted the parallel ``KNOWN_*`` naming + the inverse
  semantics. The fix was the docstring (explicitly say
  "this isn't a known-good list — it's a 'worth
  extracting' list").
- **Lesson:** **For this operator specifically:** when
  curated constants accumulate in a verifier /
  classifier stack, each new one should explain its
  relationship to the existing ones in its docstring.
  Parallel naming creates implicit "these are the same
  shape" assumptions; opposite semantics + parallel
  naming is a future-reader trap.
  **Generalisation:** when shipping curated lists,
  the name + docstring carry the load — a future
  rename
  (``EXTRACT_FROM_LOWERCASE`` or ``MUST_EXTRACT_TERMS``)
  would make the intent self-documenting without
  requiring careful reading of the docstring. v3
  candidate.

## 2026-05-15 — Methodology calibration: locked-in-limitation tests can flip when the limitation closes

- **Context:** K6.4 v1 (SESSION 160) shipped with a
  documented lowercase-tech-name miss. The test
  ``test_extract_misses_lowercase_trafilatura_known_v1_gap``
  explicitly asserted ``"trafilatura" not in claims`` —
  locking in the limitation as a contract about v1's
  current state. v2 (SESSION 166) closed the
  limitation; the test got renamed to
  ``test_extract_now_catches_lowercase_trafilatura_k6_4_v2``
  and the assertion flipped to ``"trafilatura" in claims``.
- **Direction:** Carry-forward methodology.
- **Detail:** The test count stays the same; the test's
  *intent* shifted from "this is the v1 ceiling" to
  "v2 broke through it." The historical name + the
  assertion shift tells the story of how the contract
  evolved. A future reader doing
  ``git log -p test_claim_verifier.py`` can trace the
  ``v1_gap → v2`` calibration without consulting
  TRUST_CALIBRATION or handoffs.
- **Found by:** Test-rename moment during the v2 commit
  prep — almost deleted the v1 test outright, then
  recognized the value in preserving the name as a
  pointer.
- **Lesson:** **For this operator specifically:**
  locked-in-limitation tests are contracts about
  *the current state*, not permanent prohibitions.
  When the limitation closes, flip the test rather than
  delete it — the rename + assertion swap is a
  self-documenting story of how the gap got closed.
  **Generalisation:** test history is documentation.
  When a "this is intentionally bad" test ships, name
  it so the future test that flips its assertion can
  share a clear lineage (``_known_v1_gap`` →
  ``_now_catches_..._k6_4_v2``).

## 2026-05-15 — Architectural calibration: strict mode reveals over-rejection cleanly when synthesis is grounded

- **Context:** K6.4 v2.1 (SESSION 167) first real-Runway
  dogfood under strict mode. Same operator prompt class
  that originally caused the SESSION 158 hallucination.
- **Direction:** Carry-forward architectural.
- **Detail:** The dogfood's surprise was that K6 *didn't*
  hallucinate this time — it produced clean grounded
  content (embeddings + vector databases + chunking +
  retrieval, all in the chunks). v2's extractor + stoplist
  improvements paid off in shaping the synthesis. But
  strict mode still rejected, on innocent CTA verbs
  (`Want` / `Reach` at sentence starts in the closer).
  The failure mode *shifted*: v1's failures were misses
  (lowercase trafilatura, etc); v2's failures are false
  positives on CTA closers; v3's failures will be
  something else (semantic paraphrase?). The verifier
  is doing its job at each iteration — the new failure
  class is the next iteration's input.
- **Found by:** Live dogfood of strict mode + a fresh
  composition against Donny's Wikipedia RAG attachment.
- **Lesson:** **For this operator specifically:** when
  a verifier / classifier / guardrail ships and gets
  iterated, expect the failure mode to *shift* with each
  iteration, not just shrink. v1 misses → v2 false
  positives → v3 paraphrases. Each iteration is doing
  its job; the new failure class becomes the next
  calibration target. **Generalisation:** in classifier
  pipelines, "fixed failure mode" isn't a destination —
  it's a moving target that follows the easiest
  remaining bug. Plan for ongoing calibration; don't
  expect a final-state shipment. The K6.4 v2.1 stoplist
  additions are themselves transient (v3 might subsume
  them via semantic matching) — they're a snapshot of
  the current failure surface, not a permanent fix.

## 2026-05-15 — Methodology calibration: the watchdog paid for itself on its first production fire

- **Context:** K6.4 stoplist watchdog shipped SESSION 165
  as speculative tooling — preventive infrastructure for
  a class of false positives that had been surfacing one
  at a time across SESSIONS 161-164. SESSION 167's first
  real-Runway dogfood surfaced two new false positives
  (`Want`, `Reach`).
- **Direction:** Carry-forward methodology.
- **Detail:** Running
  ``python manage.py stoplist_watchdog --days=1``
  immediately classified them as sentence-initial
  candidates + emitted a copy-pasteable Python set
  literal. Total operator effort to identify: ~10 seconds.
  Without the watchdog, the loop would have been: read
  the error message → diff against existing stoplist →
  guess at the right additions → repeat. ~5-10 minutes
  per discovery event. The watchdog also captured the
  `Drop a Wikipedia` historical event + correctly noted
  v2's regex fix would have prevented it — useful
  contextual signal for the operator.
- **Found by:** First production dogfood event after the
  watchdog shipped. Ran the watchdog reflexively after
  reading the rejection error; it surfaced the right
  candidates immediately.
- **Lesson:** **For this operator specifically:**
  preventive tooling for known failure classes pays off
  the moment the next observation event arrives. The
  watchdog's design (SESSION 165) was speculative; SESSION
  167's dogfood event validates it. **Generalisation:**
  when a failure class has surfaced 3+ times manually
  (the SESSIONS 161-164 dogfood loop), investing in
  scripted detection beats hoping the next one is the
  last. The cost is ~30 minutes; the payoff is the
  observation → patch loop dropping from minutes to
  seconds.

## 2026-05-15 — Methodology calibration: operator feedback on rendered output ≠ feedback on the pipeline

- **Context:** SESSION 167 dogfood landed
  ``verification_status=verified`` + a real Runway
  render at $0.25. By system metrics: success. SESSION
  168 the operator watched the actual video and said:
  *"they still need some tweaking, or clean up on how
  the conversation is flowing — a couple of them feel
  like it's picking up mid conversation and you don't
  really know what's going on."*
- **Direction:** Carry-forward methodology.
- **Detail:** Two distinct failure modes were collapsed
  in our review:
  * **System failure** — pipeline returns non-2xx,
    the verifier rejects, or the model hallucinates.
    The K-arc verifier work catches these.
  * **Quality failure** — pipeline is green but the
    rendered output doesn't read well. The verifier
    doesn't see these — they're rhetorical / structural,
    not factual. SESSION 167's render was factually
    grounded but rhetorically jarring (cold open with
    no setup).
  The fix in K6.6 was prompt engineering for *structure*,
  not for *correctness*. They live in different layers
  and need different feedback loops.
- **Found by:** Operator-mediated video review at
  SESSION 168 start, after SESSION 167 closed with a
  green system signal.
- **Lesson:** **For this operator specifically:**
  distinguish "the pipeline worked" from "the output
  was good." For any AI-output deliverable, treat them
  as separate review gates — operator-facing preview
  beats system metrics for quality calls. **For
  systems with AI-output**: ML correctness and ML
  quality decouple. A green correctness signal can
  hide a real quality regression. Build a quality-
  review surface explicitly (persistence + UI), don't
  rely on operators noticing.

## 2026-05-15 — Architectural calibration: persistence enables retroactive feedback

- **Context:** K6.6 (SESSION 168) added
  ``Composition.synthesized_brief`` to persist what K6
  said on *successful* renders. Pre-K6.6 only
  ``rejected_synthesis`` (strict-mode failures)
  survived; successful renders left no trail of the
  generated text.
- **Direction:** Carry-forward architectural.
- **Detail:** The SESSION 167 render that motivated
  this work isn't recoverable. When the operator said
  "picking up mid conversation" we couldn't go back
  and look at the specific text — we only knew it
  from rejection paths where K6 had been blocked, not
  from the rendered text that actually shipped. The
  ``synthesized_brief`` field closes that gap going
  forward; every future composition's actual rendered
  text is on the row. Operator can review at any
  time, give specific feedback; the agent can quote
  the actual text in calibration entries.
- **Found by:** Trying to debug "which render was
  the operator talking about?" during SESSION 168
  diagnosis. The audit data we needed didn't exist.
- **Lesson:** **For this operator specifically:**
  persist the artifact that the operator might
  review later, even when "the system worked."
  Audit trails are operator-facing, not just
  debugging-facing. **Generalisation:** ML pipelines
  should persist their generated content alongside
  their state transitions. State alone is necessary
  but not sufficient for retroactive operator
  review. If the operator might ever want to ask
  "what did the model say?", the answer needs to
  live on a persisted row, not a transient log line.

## 2026-05-15 — Methodology calibration: operator-facing test loops scale with audit fields

- **Context:** SESSION 169 dogfooded W11.1 (edit modal) by
  editing Marcus's business_brief and firing a fresh
  render. Confirmation was instant: read
  ``composition.synthesized_brief`` (K6.6, SESSION 168) on
  the new composition row → spot the new signature phrase
  in the first sentence.
- **Direction:** Carry-forward methodology.
- **Detail:** Pre-K6.6 the same loop would have been:
  fire render → wait for Runway → download the MP4 →
  watch it → maybe read media-engine logs to find the
  brief. ~5-10 minutes. With ``synthesized_brief``
  persisted: ~5 seconds via a Django shell query. The
  K6.6 audit field that we built for *retroactive
  operator review* turned out to also accelerate
  *iterative prompt tuning*.
- **Found by:** Realizing during the W11.1 dogfood that
  I never opened the MP4. The DB row had everything
  needed.
- **Lesson:** **For this operator specifically:** audit-
  trail fields aren't just for debugging or retroactive
  review — they're test infrastructure. Every "what did
  the model actually say?" surface collapses the
  iteration loop on prompt / persona / recipe tuning by
  an order of magnitude. **Generalisation:** when adding
  persistence for one stated use case (audit / debug),
  consider whether the same field unlocks faster
  iteration loops for adjacent use cases. The marginal
  cost is zero; the marginal value scales with how often
  the field gets queried.

## 2026-05-15 — Architectural calibration: the metadata gap is the SPA gap

- **Context:** SESSION 169 surfaced operator feedback:
  *"We don't have a way to edit the Avatars [on the
  UI]."* Backend has supported PATCH on Spokesperson
  since the ``SpokespersonViewSet`` (ModelViewSet)
  shipped. The gap was the SPA never grew an edit
  surface.
- **Direction:** Carry-forward architectural.
- **Detail:** Six weeks of K-arc work shipped through
  metadata-driven forms (recipes, verifier toggle, mode
  select). Each new K-feature got a SPA surface
  for-free via the metadata renderer. But spokesperson
  edit is hand-built UI — the ModelViewSet's CRUD is
  *not* metadata-driven; it's just DRF defaults. The
  feature was effectively backend-only until W11.1
  shipped the modal. Operators don't discover features
  through `curl`; they discover them through visible
  affordances. The "we don't have X" moment was
  inevitable.
- **Found by:** Operator stating the gap mid-session.
- **Lesson:** **For this operator specifically:** any
  new model that ships via ModelViewSet should get a
  SPA surface paired with it within the same arc —
  otherwise the gap surfaces as
  *"we don't have a way to do X"* months later.
  **Generalisation:** read-only metadata-driven
  surfaces + hand-built write surfaces is a stable
  pattern, but the write side scales linearly with
  feature surface area. Budget for the hand-built UI
  alongside every CRUD endpoint, not as a follow-up
  slice.

## 2026-05-16 — AI confidently wrong: hook-order violation across early returns

- **Context:** SESSION 169's W11.1 edit modal added a
  `useState(editing)` to the SpokespersonDetailRoute
  component. I placed it after the existing early
  returns (`if (sp.isLoading) return …`,
  `if (sp.isError) return …`, etc.). The unit tests
  passed (Marcus's modal renders fine); the SPA build
  succeeded; the live SPA opened cleanly.
- **Direction:** AI confidently wrong.
- **Detail:** When `sp.isLoading` flipped true → false
  on the live SPA, React saw a different hook count
  per render (loading render had 4 hooks; data render
  had 5). Console error: *"Rendered more hooks than
  during the previous render."* The unit tests didn't
  catch it because the test fixture pre-seeds the
  spokesperson cache, so `isLoading` never flips on
  mount — both renders have the same hook count.
- **Found by:** Operator browser console output
  during a live SPA session.
- **Lesson:** **For this operator specifically:** when
  adding hooks to an existing route component with
  conditional early returns, the new hook must live
  ABOVE the returns. **Generalisation:** React's
  Rules of Hooks ban conditional hook calls; an early
  return *is* a conditional execution path. Unit tests
  with pre-seeded caches systematically miss this
  failure mode — the loading → ready transition only
  fires in real navigation. Pattern to internalize:
  ALL hook calls at the top of the component, then
  early returns, then conditional rendering. Audit
  any route component that has both
  `useState`/`useEffect` and early returns when adding
  new hooks.

## 2026-05-16 — Architectural calibration: JWT expiry on external CDN URLs is a recurring class

- **Context:** SESSION 169 surfaced 5× `401 Unauthorized`
  on cast avatar thumbnails. Runway's CloudFront URLs
  embed a JWT with `exp` ~30 days from avatar create
  time. We persist the URL into
  `Spokesperson.portrait_path` at avatar-bake time and
  never refresh it.
- **Direction:** Carry-forward architectural.
- **Detail:** The original SESSION 137 work persisted
  the thumbnail URL so the SPA's Portrait component
  had something to render without re-baking. That was
  the right v1 call — the alternative (re-fetch on
  every load) would have hammered Runway. But we never
  added a refresh path, so the URLs silently rot 30
  days later. The fix this session (`/internal/avatars/
  <id>/refresh/` + `useRefreshPortrait` + `<img
  onError>` auto-refresh) is the v2 shape this should
  have launched with. Every JWT-bearing URL we persist
  needs a refresh path budgeted alongside the
  persistence.
- **Found by:** Operator browser console — the URLs
  expired between SESSIONS and started 401-ing
  organically.
- **Lesson:** **For this operator specifically:** any
  persisted URL with `exp` baked in is going to break
  on schedule. Build the refresh path in alongside
  the original persistence, not as a follow-up.
  **Generalisation:** persisting time-bound external
  identifiers (signed URLs, OAuth tokens, JWT-bearing
  CDN paths) without an explicit refresh strategy is
  a debt that resolves itself only when an operator
  notices broken UX. Audit pattern: grep the codebase
  for fields that store URLs sourced from external
  signed APIs; for each, confirm a refresh path
  exists. If not, ship one with the next adjacent
  feature.

## 2026-05-15 — Architectural calibration: distinct request boundaries for distinct side-effects

- **Context:** SESSION 170's W11.2 introduced the first
  spokesperson-edit case where a "save" spans both a DB
  write and an external-system side-effect (Runway
  `PATCH /v1/avatars/<id>` for the voice block). W11.1
  was pure DRF `partial_update`. The temptation was to
  bundle voice into the same PATCH and have the
  Spokesperson save loop fire the Runway call.
- **Direction:** Carry-forward architectural.
- **Detail:** Two operationally bad shapes if bundled:
  (1) couples DB transactionality to a 5-15s HTTP call;
  (2) hides the Runway round-trip from the
  operator-facing log. The two-request shape — PATCH for
  persona fields, `change-voice` action for the
  Runway-bound side-effect — keeps the edit modal thin
  and surfaces partial success (`voice_patch: {status,
  error}`) explicitly. Operator sees DB persisted /
  Runway failed as distinct states.
- **Found by:** Design call at the start of W11.2; no
  failure event. Calibration is preemptive.
- **Lesson:** **For this operator specifically:** when an
  SPA save spans a DB write + an external-system call,
  model them as two requests, not one bundled PATCH.
  The action endpoint surfaces the side-effect result.
  **Generalisation:** serializer save loops are the wrong
  layer for synchronous external HTTP calls. Pattern:
  thin form → DRF default PATCH; expensive/risky
  side-effects → dedicated `@action` endpoint with an
  explicit response envelope that distinguishes DB
  success from side-effect success.

## 2026-05-15 — Methodology calibration: mock-fetch needs route-aware routing once endpoints multiply

- **Context:** SESSION 170's W11.2 broke an existing
  `spokesperson-edit-modal.test.tsx` test pattern. The
  mock-fetch was a single switch on `/voice-presets/`
  (W11.1 only hit two endpoints — voice-presets GET +
  spokesperson PATCH). W11.2 added a third
  (`change-voice` POST). The default branch returned the
  bare Spokesperson shape; the change-voice schema
  expects `{spokesperson, voice_patch}` envelope. Schema
  parse threw inside the mutation; `onClose` expectation
  failed far from the actual cause.
- **Direction:** Carry-forward methodology.
- **Detail:** Two test failures in the W11.2 commit ladder:
  (1) "Save fires a PATCH" — expected fetch count of 1,
  got 2 because `useVoicePresets` fires a GET on mount.
  Fixed by finding the PATCH call by method instead of
  asserting count. (2) "W11.2 voice change" — schema parse
  threw because the mock didn't route-switch
  `change-voice` to the envelope shape. Both fixed in the
  same edit pass, but the diagnostic distance was much
  larger than the cause.
- **Found by:** Test failure; root-cause analysis on
  the second iteration.
- **Lesson:** **For this operator specifically:**
  vitest mock-fetch implementations deserve route-aware
  switching from day one when a component hits more than
  one endpoint. **Generalisation:** the failure mode
  (schema parse → mutation throws → distant expectation
  fails) is hard to diagnose. Pattern: every
  mock-fetch starts as a `switch (url)` over the
  endpoints the component hits, not a single default
  branch. Adding endpoints later is cheap; retrofitting
  the switch is expensive.

## 2026-05-16 — AI confidently wrong: Tier 2 prompt-composer hypothesis disproved by hackathon diff

- **Context / claim:** Operator flagged Marcus + Sasha rendering
  "plasticy" while Donny / Riggs / Maya look natural. AI
  proposed Tier 2: replace `"Polished commercial portrait"`
  with `"Character illustration of"` + drop `"Professional
  advertising character design."` from the mascot path —
  hypothesis was that these phrases were anchoring gen4_image
  toward plastic 3D-mascot product-render aesthetic. Operator
  approved + AI shipped the change with test updates.
- **Reality / outcome:** Tier 2 visual judgment: still plasticy.
  Operator asked AI to "go back to the hackathon and see how we
  were prompting those." Diff revealed the hackathon's
  `character_studio_client.py` is **bit-identical** to
  character-os's pre-SESSION-171 state (subtree migration moved
  it verbatim). Donny / Riggs / Maya were baked with the EXACT
  same prompt template that's producing Sasha / Marcus today.
  The plastic-vs-natural difference is **variance + subject
  complexity** (Marcus's elaborate armor + Sasha's
  "sleek...subtle branding" push the commercial anchor harder
  than Donny's casual hoodie), not the prompt template.
  Reverted Tier 2; kept Tier 1.
- **Found by:** Operator instinct ("go back to the hackathon")
  + AI verified by diffing the two files.
- **Lesson:** When operator says "go back to how X was working
  in <prior codebase>", **diff the actual files first** before
  proposing a fix that moves AWAY from <prior codebase>. The
  subtree migration was verbatim — there was no different
  hackathon prompt to recover. **For this operator specifically:**
  when comparing failure modes across the cast, the subject
  complexity axis matters more than the prompt-template axis.

## 2026-05-16 — AI right (with proof): Runway avatar rig requires Runway-generated portraits

- **Context / claim:** Operator's W11.3 vision (SESSION 171)
  was to use unused Stability AI credits to generate avatar
  portraits, piping the resulting PNG into Runway's
  `create_avatar` reference image — the hackathon proved
  Runway accepts arbitrary portrait inputs at bake time. AI
  ported the Stability service + style library + orchestrator
  and ran the end-to-end test through Marcus.
- **Reality / outcome:** Every Stability portrait baked
  cleanly (Runway accepted the referenceImage) but lip-sync
  consistently mis-mapped — mouth movement landed on the
  nose tip instead of the actual mouth. Tested multiple
  style presets (`concept_art`, `pixar`); the mouth-vs-nose
  problem persisted regardless of style. Conclusion: Runway's
  avatar rig is trained on gen4_image's face geometry
  distribution; Stability's output passes the avatar-bake
  gate but the landmark detection misfires. **Stability is
  the right provider for non-avatar image gen** (scenes,
  b-roll, products) — not avatars.
- **Found by:** AI end-to-end test against real Runway + real
  Stability.
- **Lesson:** Provider-mix architectures are only as
  composable as the **downstream consumer** allows. Runway's
  avatar rig is the bottleneck here, not the image-gen
  step. Future "swap provider X for Y" experiments should
  cheap-test the downstream consumer's tolerance before
  scoping a full port. Saved as
  `feedback_runway_avatar_rig_needs_runway_portraits.md` so
  future sessions don't redo the experiment.

## 2026-05-16 — Calibration: Human/AI testing split during live-services dogfood

- **Context:** Mid-SESSION 171, operator was driving the SPA
  manually (clicking through edit modal, rebake modal,
  visual judgment) while AI was running shell scripts
  (database queries, log tails, curl probes). AI proposed
  "drive via curl" vs "drive via SPA" as a binary choice for
  a subsequent step. Operator clarified: *"I was doing the
  Human testing (i.e. visuals/UI stuff), while you do the
  other testing lol."*
- **Direction:** Calibration on collaboration boundaries
  during real-services dogfood.
- **Detail:** Operator drives the SPA + visual / auditory
  judgment — the things only a human can verify. AI drives
  the parallel API / DB / log verification — the things
  that don't need human eyes. Not either-or — **both in
  parallel**.
- **Found by:** Operator clarification.
- **Lesson:** When operator says "I'll do X in the UI," AI's
  default response is "I'll watch the DB/logs/etc. and
  report what I see" — NOT "should I drive via curl
  instead?" Saved as
  `feedback_human_ai_testing_split.md` so the lane-split
  loads via session-start MEMORY read.

## 2026-05-15 — AI right (preemptive application): the hook-order lesson held

- **Context:** SESSION 170 added a new `rebaking` state
  hook to the SpokespersonDetailRoute component
  (same file that surfaced the SESSION 169 hook-order
  violation when `useState(editing)` was added below the
  early returns). The SESSION 169 lesson was applied
  preemptively — `rebaking` went above the early
  returns on first write.
- **Direction:** AI right despite no prompt to apply it
  (the operator didn't surface the rule; the prior
  TRUST_CALIBRATION entry did).
- **Detail:** Zero console errors on first live load.
  The rule is now load-bearing in this route file —
  every new state hook goes above the loading / error /
  not-found returns. Pattern internalized one session
  after the initial failure.
- **Found by:** Author at write time; verified by
  operator's clean console.
- **Lesson:** TRUST_CALIBRATION entries that get
  surfaced via the start-of-session anchor read pay off
  by reducing the failure-rediscovery loop to once.
  **For this operator specifically:** keep adding
  carry-forward entries to TRUST_CALIBRATION — they're
  not retrospective ornament, they're load-bearing
  context for the next session's first code-write. The
  cost is one extra paragraph per session; the savings
  is the second occurrence of every failure mode.

## 2026-05-16 — AI confidently wrong: dependency_overrides reach service-direct `get_settings()`

- **Context / claim:** SESSION 173 W11.6.1 — the new
  `/internal/image_stability/` endpoint takes
  `settings: Settings = Depends(get_settings)`. The first
  test for the backwards-compat call pattern
  (`generate_stability_portrait(subject, template=...)`
  without `purpose=`) used the standard mock fixture:
  `Settings(stability_api_key="")` + `app.dependency_overrides[get_settings] = lambda: settings`.
  AI's mental model: "the override flows through wherever
  `get_settings()` is called, so the inner service sees
  `stability_mock=True` and short-circuits."
- **Reality / outcome:** `get_settings()` has `@lru_cache`.
  FastAPI's `Depends` resolution honors the override; *direct*
  `get_settings()` calls inside service code bypass it
  entirely and hit the cached real settings. The operator's
  `.env` had a populated `STABILITY_API_KEY`, so the first
  test run accidentally fired a real Stability render —
  9.6 seconds, 6.5 credits, ~$0.0065 burned in CI.
- **Found by:** First `pytest` run on W11.6.1's test suite.
  Test assertion `result.mock_mode is True` failed; the real
  result came back with `mock_mode=False`, `cost_credits=6.5`,
  `elapsed_ms=9632`, and a path to a real generated PNG on
  disk. Visible immediately; loud failure.
- **Lesson:** Two patterns to keep dependency overrides
  honored: (1) the test monkeypatches the module-level
  `get_settings` reference inside the service module
  (`monkeypatch.setattr("app.services.X.get_settings", lambda: fake)`),
  OR (2) the service accepts `settings` as a parameter and
  the endpoint passes its `Depends(get_settings)` injection
  down. The W11.6.1 endpoint switched to pattern 2 (mock-mode
  short-circuit at the endpoint level using the injected
  settings); the unit test uses pattern 1. **For future
  media-engine tests**: assume any `lru_cache` on settings
  bypasses overrides unless explicitly handled. The 6.5-credit
  cost is a cheap calibration vs running into this in a
  larger test suite that burns through credits per run.

## 2026-05-16 — AI confidently wrong: `fireEvent.click` on Radix Tabs under jsdom

- **Context / claim:** SESSION 173 W11.6.3 — testing
  `StylePresetPicker`, which uses Radix `Tabs`. AI's first
  pass used the established pattern: `fireEvent.click` on
  the TabsTrigger to switch tabs, then `findByTestId` on a
  preset card in the new active panel. AI's expectation:
  Radix's tab-change is synchronous; the inactive panel
  becomes interactable after the click.
- **Reality / outcome:** Test failed. The inactive tabpanel
  stayed `hidden=""` after `fireEvent.click(genreTab)`, so
  `findByTestId("style-preset-cyberpunk")` (inside the
  genre panel) timed out waiting for the element. Radix's
  Tabs implementation needs real pointer events
  (`mousedown`/`mouseup`/`click`) to flip the active panel
  under jsdom — synthetic click events aren't enough.
- **Found by:** Test run produced a 30-second timeout +
  DOM dump showing the genre tabpanel still in its hidden
  state.
- **Lesson:** For Radix UI primitives under jsdom, default
  to `userEvent.setup() + await user.click()`. The
  `tool-approval-modal.test.tsx` (from R8.1) already used
  this pattern. New pattern established for the SPA test
  suite: when a component renders Radix Tabs / Dialog /
  Popover / etc., use `userEvent`, not `fireEvent.click`.
  Mark it as the default for new test files going forward.

## 2026-05-16 — Near-miss: scope-lock missed prompt-vs-subject distinction

- **Context / claim:** SESSION 172's W11.6.0 scope-lock
  enumerated 7 image Asset fields (purpose / model /
  style_preset / prompt / negative_prompt / aspect_ratio /
  spokesperson). Journey 1 + Journey 3 both described a
  Regenerate CTA as "re-fires with same params, new seed."
  AI signed off on the scope-lock without flagging that
  Regenerate needs more than the listed fields. Through
  W11.6.1 + W11.6.2 + W11.6.3, the AI continued to build
  on the 7-field assumption.
- **Reality / outcome:** When AI got to W11.6.4's
  ImageDetailModal and went to wire Regenerate, the gap
  surfaced: the *composed prompt* has the purpose framing
  baked in ("A detailed scene illustration of…", "A
  high-quality product image of…"). Sending the composed
  prompt back as the new `subject` would double-apply the
  framing ("A detailed scene illustration of A detailed
  scene illustration of…"). The original operator subject
  (pre-composition) is what's needed for round-trip — and
  it wasn't being stored.
- **Found by:** AI itself, before writing the modal code.
  The fix landed in W11.6.4 as a small additive change:
  `Asset.subject` TextField + migration 0007 + ViewSet
  persistence + serializer surface + SPA schema with
  `.default("")` so pre-W11.6.4 rows parse cleanly. The
  modal disables Regenerate (with a tooltip) on those rows.
  Total scope creep: ~30 minutes for the catch + fix.
- **Lesson:** **Scope-lock reviews for any composition-step
  surface should explicitly distinguish *what the operator
  types* (or selects) from *what the model sees* after
  composition.** The composed prompt is rarely the right
  thing to round-trip — operator inputs are. Wherever the
  product story includes a "Regenerate" / "Adjust" /
  "Variant" CTA, the scope-lock should list the
  pre-composition operator inputs as required persistence
  fields. Apply this lens proactively in future scope-locks
  (K, V, R, F arcs all had composition-step surfaces; none
  were caught by the same lens in time, though K6.6
  shipped a similar gap fix for synthesized_brief).

## 2026-05-16 — AI confidently wrong: SESSION 173 inventory claimed "mock-only embeddings"

- **Context / claim:** The SESSION 173 mid-session inventory
  ("what's the platform actually capable of?") listed under
  "What it can NOT do yet": *"Mock-mode-only embeddings —
  EMBEDDING_FORCE_MOCK is on by default; real embeddings
  haven't been dogfood-validated at scale (only ~32 chunks
  live)."* The claim was the AI's own synthesis from
  reading docs + grep'ing for the force-mock flag.
- **Reality / outcome:** SESSION 174 real-mode embedding
  dogfood probed the live runtime. All 32 chunks across 3
  knowledge documents in `Admin's workspace` already have
  **real OpenAI text-embedding-3-small vectors**:
  unit-normalized (magnitude ≈ 1.0), dense (1536/1536
  non-zero), `cost_micros` populated, model field reads
  `text-embedding-3-small` (no "(mock)" suffix). The
  operator's `.env` has `OPENAI_API_KEY` set and does NOT
  have `EMBEDDING_FORCE_MOCK` set. Real embeddings have
  been the active production path for an unknown number
  of sessions. AI just didn't check the runtime.
- **Found by:** SESSION 174 dogfood task. Direct shell
  inspection of `KnowledgeChunk.embedding_vector` magnitude
  + cost_micros revealed the production reality.
- **Lesson:** **When the inventory question is "what can we
  do today?", read the runtime FIRST, the docs and code
  SECOND.** The runtime is the only authoritative answer to
  "is this surface live?" The narrative + design lock + grep
  results all describe *intent* and *guards*, not *state*.
  The CHARACTER_OS_INVENTORY.md anchor exists for exactly
  this reason — it's regenerable, it reads runtime, and
  INVENTORY wins on conflict. I should have driven a 5-line
  shell query against the chunk magnitudes before asserting
  anything about embedding mode. Cheaper than the wrong
  inventory claim that nearly steered the session into a
  re-embed task that wasn't needed.

## 2026-05-16 — Near-miss: K6.4 verifier false-positives on sentence-opener words

- **Context / claim:** SESSION 174 dogfood drove a real K6
  brief synthesis for Marcus with the prompt *"Tell me
  about the five good emperors and why historians consider
  them a golden age."* Pipeline: real OpenAI embed → real
  pgvector retrieval (top-5 chunks) → real gpt-5 synthesis
  → K6.4 verifier in Warn mode → ScriptResult.
- **Reality / outcome:** Brief was clean, grounded, all
  claims traceable to the Nerva-Antonine doc. But the
  verifier flagged 2 "unsupported claims":
  * `{"claim": "Today", "kind": "proper_noun", "position": 0}`
  * `{"claim": "Think Antoninus", "kind": "multi_word", "position": 371}`
  Both are sentence-opener artifacts. "Today" is a
  sentence-initial capitalized adverb the verifier
  misidentifies as a proper noun. "Think Antoninus" is the
  verifier concatenating an imperative-mood sentence opener
  ("Think Antoninus' peaceful, Senate-sharing reign…") with
  the genuine proper noun that follows, treating the pair
  as one multi-word entity.
  The brief itself was correctly verified — every real
  named entity (Nerva, Trajan, Hadrian, Antoninus Pius,
  Marcus Aurelius, Machiavelli, Gibbon, Commodus) traced
  cleanly. The false positives are verifier-sensitivity
  noise on capitalized sentence-openers, not actual
  hallucinations.
- **Found by:** Real-mode dogfood probe. Without the
  dogfood, the false-positives would have surfaced first
  during operator inspection of a render's
  `verification_warnings` field — confusing because the
  brief reads correctly.
- **Lesson:** **K6.4 stoplist / multi-word detection needs
  sentence-position awareness.** Capitalized words at
  position 0 of a sentence are not reliably proper nouns
  (English capitalizes the first word regardless). Two
  cheap improvements queued for a later K6.4 v2.x:
  1. Add common sentence-opener adverbs ("Today",
     "Tomorrow", "Now", "Then", "Here", "There", "Yesterday")
     to the stoplist.
  2. Multi-word detection should skip sentence-initial verbs
     ("Think X", "Consider X", "Imagine X") and treat only X
     as the candidate proper noun.
  Real impact: ~2 false positives per warn-mode brief is
  noisy enough to make operators distrust the warnings list.
  Worth a small surgical fix in the next K-arc session.

## 2026-05-16 — Near-miss: YouTube ingest pollution confirmed by retrieval probe

- **Context / claim:** The operator's MEMORY entry
  `project_youtube_ingest_silent_failure.md` noted K7
  reports YouTube URLs as "processed" but trafilatura
  captures nothing useful. AI flagged this in the
  SESSION 173 inventory as a queued backlog item without
  verifying current impact.
- **Reality / outcome:** SESSION 174 retrieval dogfood
  probed off-topic queries against Marcus's knowledge
  surface (3 docs: Nerva-Antonine + Wikipedia trafilatura
  test + a YouTube URL titled "Create Your Own Character
  in 5 Minutes | Runway"). The off-topic query
  "best ways to bake sourdough at home" surfaced the
  YouTube doc as top-1 with chunk content:
  *"About Press Copyright Contact us Creators Advertise
  Developers Terms Privacy Policy & Safety How YouTube
  works Test new ..."*. That's YouTube's nav-bar / footer
  boilerplate — NOT video content. Trafilatura extracted
  the page chrome, not the transcript or description.
  Concrete production impact: any operator query against a
  workspace with YouTube-ingested docs will return
  meaningless chunks that pollute retrieval. Worse, the
  YouTube doc's single boilerplate chunk is short and
  generic enough to be semantically "close" to almost any
  query (distance ~0.85 to sourdough), so it surfaces above
  the genuine on-topic chunks in any cross-document query.
- **Found by:** SESSION 174 deliberate off-topic retrieval
  probe.
- **Lesson:** **The K7.x YouTube fix is higher-priority than
  "queued backlog" framing suggested.** A single bad doc in
  a workspace degrades retrieval quality across the entire
  knowledge surface, not just for queries that target that
  doc. Two practical paths:
  1. Detect-and-reject at ingest time: if the YouTube URL
     extraction returns < N chars of useful content (heuristic:
     "About Press Copyright Contact us" substring match),
     reject with operator-visible error.
  2. Per-host extractor: route YouTube URLs to the
     YouTube transcript API or oEmbed instead of trafilatura.
     Heavier lift; more reliable.
  Promote to "next queue item after current session priority."

## 2026-05-16 — Near-miss: W11.6.5.1 narrow-fix rationalisation

- **Context / claim:** Shipped W11.6.5.1 (Asset.title for image
  pickers) in SESSION 174. My commit message said *"Future work
  flagged: clip + audio assets still leave title empty (their
  legacy filename-based labels are at least somewhat readable).
  Plumbing a title through the composition runtime when it
  persists step outputs is a natural follow-on, but is its own
  slice."* The framing was: "images are fixed; clips can wait."
- **Reality / outcome:** Operator opened the
  ``backdrop_composite`` recipe minutes later and the clip
  picker labels read like
  ``5cf5ab4e-0398-480c-b33b-f994f567ccc1.mp4?_jwt=eyJh…`` —
  CDN URL tails after `file_path.split("/").pop()` truncation.
  Indistinguishable from each other; looked exactly like the
  raw UUIDs the operator had originally complained about. The
  "somewhat readable" framing was AI rationalisation, not a
  real assessment of the operator-facing surface. The right
  answer was to fix all asset types in W11.6.5.1 — the
  composition runtime change in W11.6.5.3 was 1 line of
  production code (``title=composition.name``) plus a small
  backfill. Splitting it bought nothing.
- **Found by:** Operator opening the recipe immediately after
  W11.6.5.1 shipped and saying "the background and foreground
  clips are all listed by id still." Within 15 minutes of the
  W11.6.5.1 commit.
- **Lesson:** **Don't rationalise "somewhat readable" — look
  at what the operator-facing surface ACTUALLY renders for the
  case being deferred.** Before claiming a fix is "narrow" or
  scoped, check the rendered output for every variant the SPA
  surfaces. For asset_picker specifically: the dropdown shows
  ``assetLabel(asset)`` for EVERY asset_type the picker can
  list; verify each one renders something human-friendly. The
  cost of folding W11.6.5.3 into W11.6.5.1 would have been
  ~15 minutes; the cost of the operator finding the
  half-fixed state was a small trust-impact + the cycle of
  shipping the followup.

## 2026-05-16 — Near-miss: W11.6.5.2 cap-too-tight, caught by real dogfood

- **Context / claim:** W11.6.5's unit tests passed. 5 new
  Django tests covered the recipe metadata, the resolver's
  data-URI extraction, the workspace isolation path, the
  clip-picker invariant. All green. I declared the slice
  shipped + invited operator to dogfood.
- **Reality / outcome:** The W11.6.5 resolver passes a
  ~4.5 MB data URI as ``prompt_image`` to the
  ``cinematic_visual`` starter. Starter passes that through
  to ``MediaEngineClient.create_visual_clip``. Media-engine's
  ``/internal/clips/visual/`` endpoint has
  ``prompt_image: Optional[str] = Field(default=None,
  max_length=2048)``. Pydantic rejected with 422 the
  first time the operator-driven dogfood fired. The 2048
  cap was sized for URL-shape inputs (the pre-W11.6.5
  contract); data URIs blow through it 2000x over.
  Unit tests didn't catch this because they used
  ``mock_mode=True`` which short-circuits before any
  media-engine HTTP call.
- **Found by:** First operator-driven real-mode dogfood
  attempt. Failed composition with the 422 in
  ``error_message``.
- **Lesson:** **When a slice adds a NEW input shape to an
  existing field (here: data URI to a previously-URL-only
  ``prompt_image``), audit ALL downstream max_length /
  size guards before declaring success.** Grep for the
  field name across both Django and media-engine; check
  every Pydantic Field constraint that mentions it. Better:
  add at least one real-mode integration test that
  exercises the new input shape end-to-end, even if it's
  expensive. The 2048-char cap was visible in source for
  >a year before W11.6.5; nobody had reason to look at
  it until the picker landed.

## 2026-05-16 — AI confidently wrong: Celery worker restart rule was too narrow

- **Context / claim:** SESSION 173 close note read: *"Restart
  Celery only if next session touches K6 / K9 / R6 / R7.2 /
  render_video flows."* The framing — which I wrote — was that
  only LLM-using async surfaces need a worker restart.
- **Reality / outcome:** The W11.6.5 dogfood
  ``cinematic_visual`` composition crashed at the persistence
  step with ``null value in column "aspect_ratio" of relation
  "compositions_asset" violates not-null constraint``. The
  stale worker (pid 62107, started 2026-05-15 23:52) predated
  every W11.6 migration. Its in-process Asset model class
  knew nothing about the 8 W11.6.x image fields. INSERT
  omitted them; Postgres rejected NOT-NULL because Django's
  ``default=""`` is Python-level not column-level DEFAULT.
  Restart fixed it; re-fired succeeded.
- **Found by:** Real-mode dogfood. The W11.6.5 unit tests
  ran the resolver + view paths but used eager celery
  (which runs synchronously in-process with current model
  classes) so they didn't expose the stale-worker scenario.
- **Lesson:** **ANY model-extending session needs a Celery
  worker restart**, not just LLM flows. Generalize the rule:
  if migrations were applied OR ``apps/compositions/tasks.py``
  changed OR any primitive in
  ``apps/compositions/primitives/`` changed OR any model
  the worker creates rows for added/removed fields, the
  worker must be restarted before next composition fires.
  The SESSION 173 close note's narrower phrasing missed
  the model-change case. Updated the SESSION 174 close
  note to use the broader rule.

## 2026-05-16 — AI right (preemptive application): real-mode dogfood after every operator-facing slice

- **Context / claim:** SESSION 174 shipped two operator-
  facing slices in a row (W11.6.5 image picker, W11.6.5.1
  Asset.title). After each one I proposed a real-mode
  dogfood to the operator. After the image picker:
  operator agreed; dogfood found 2 bugs. After
  W11.6.5.1: operator agreed; dogfood found 1 (the clip
  pickers still showing CDN URL tails — the W11.6.5.3
  trigger).
- **Direction:** AI right despite no prior calibration
  saying "always dogfood after operator-facing slices."
  The pattern emerged from the SESSION 173 W11.6 close
  (which was where the operator first said "dog food it
  and I will look at the results on the UI") and has
  carried forward consistently.
- **Found by:** Author at slice-close; reinforced by
  the operator's behavior of accepting the dogfood
  proposal every time.
- **Lesson:** **Default to "let's dogfood this against
  real APIs and a real workspace" after every
  operator-facing slice ships.** The cost is small
  ($0.005-$0.50 per render depending on path), the
  value is high (catches bugs unit tests miss + builds
  operator-AI shared mental model of the working state).
  Save as `feedback_real_mode_dogfood_after_operator_slices.md`
  so the lane carries forward into future sessions
  without re-deriving it.

## 2026-05-17 — AI confidently wrong: vitest atomic assertions masked a real UX bug

- **Context / claim:** SESSION 174's W11.x voice telemetry
  slice (commit `3ecb6fe`) shipped with 4 vitests covering
  the success / skipped / failed banner states. The
  `voice_patch ok renders a success banner and auto-closes`
  test asserted both that the banner was in the document
  AND that `onClose` had fired — both true in jsdom, both
  passing. AI shipped confident that the success-path
  telemetry worked.
- **Reality / outcome:** SESSION 175 operator-driven dogfood
  (voice swap on Marcus → vincent → david; Sasha →
  felix) reported "I switched to Vincent's voice and saved
  it but I didn't see anything to verify it's saved." The
  banner technically rendered. It just rendered for ~10ms
  before `onClose()` unmounted the modal in the same React
  tick that `setVoicePatch` set the banner state. jsdom
  asserts atomically — both ends of a render→unmount land
  true in the same test tick — but a human eye sees only
  the final state.
- **Found by:** Real-mode operator dogfood. Without the
  dogfood, the banner would have been invisible in
  production for an unknown number of operator swaps before
  the gap surfaced.
- **Lesson:** **Vitest assertions that fire ATOMICALLY pass
  for behavior that's INVISIBLE in real time.** When a
  render → unmount sequence runs in a single React tick,
  jsdom asserts both ends true; the human eye sees only the
  second. Pattern to watch: any test that asserts both
  "X is in the document" AND "onClose was called" without
  a delay or timing gate between them. Real-mode dogfood
  is the only way to catch this class. The W11.x.1 fix
  (commit `edff9f2`) removed the auto-close on voice
  change — modal stays open until operator clicks Close
  — and the test was updated to assert the inverse
  (`onClose NOT called` while banner visible).

## 2026-05-17 — Near-miss: source greps don't match operator-reported UI text → stale browser bundle

- **Context / claim:** SESSION 175 voice-swap dogfood. After
  the W11.x.1 fix shipped (`edff9f2`), operator reported
  seeing "Voice applied" text appearing briefly on the card
  before it closed. AI grepped the entire SPA source — zero
  matches for "Voice applied" or "applied" (outside an
  unrelated comment). AI initially considered: third-party
  browser extension injecting a toast? Service worker
  serving an old bundle? Different SPA build entirely?
- **Reality / outcome:** Stale browser bundle. The operator's
  browser tab held an older SPA bundle in memory. `pnpm
  build` had rebuilt `dist/` after the W11.x.1 commit, but
  the browser hadn't picked up the new bundle without a
  hard refresh. After Cmd+Shift+R (or equivalent), the
  modal showed the actual W11.x.1 behavior (banner stays
  visible until operator clicks Close).
- **Found by:** Process of elimination. AI suggested two
  diagnostics — port confirmation + hard refresh — and the
  operator chose to skip the diagnostic + move on. The
  cache hypothesis was the most likely answer but never
  formally validated.
- **Lesson:** **When source greps don't match operator-
  reported UI text, suspect stale browser BEFORE suspecting
  the code.** Hard refresh (Cmd+Shift+R) is the first move,
  not an after-thought. If on Django's :8000 (serves
  built `dist/` bundle), check whether `pnpm build` has
  run since the last source change. If on Vite's :5174,
  HMR usually works but can glitch — full page reload
  forces a fresh bundle. Save 5-10 minutes of confused
  source-spelunking by trying the cache hypothesis first.

## 2026-05-17 — Near-miss: K6.4 stoplist curation trickle suggests v3 architectural fix

- **Context / claim:** SESSION 166's K6.4 v2 added ~30 verbs
  to the sentence-opener stoplist (CTA verbs surfaced by
  real-Runway dogfood). SESSION 174's v2.1 added 11 more
  (time adverbs + prepositions + `think`). SESSION 175's
  v2.2 added 17 more (`respect`, `protect`, `prepare`,
  etc.). Every K6 dogfood across multiple cast members
  surfaces 1-2 new gaps the stoplist needed to cover.
  Each addition is cheap (~1-line + small test).
- **Reality / outcome:** The cumulative trickle is real.
  v2 → v2.1 → v2.2 covers a growing slice of
  imperative-mood English verbs but never the full set.
  Future K6 dogfoods will keep surfacing 1-2 more per
  unique operator prompt shape. The pattern is sustainable
  but compounds maintenance.
- **Found by:** Pattern recognition across SESSIONS 166,
  174, 175 dogfood. Three sessions, three near-identical
  fix shapes (stoplist addition + multi-word leader
  demotion when leader is stoplisted).
- **Lesson:** **The K6.4 stoplist curation pattern is a
  near-miss with v3 architectural debt.** v3 should
  generalize sentence-position-aware imperative-verb
  detection beyond the curated stoplist — likely a small
  NER classifier OR a structural test ("does this leader
  start an imperative clause? does the rest of the multi-
  word still contain a real proper noun?"). The curation
  pattern stays cheap per-addition but compounds across
  operator content variety. Worth scoping v3 when operators
  ship more verb-heavy K6 prose OR when the verifier flags
  start eroding operator trust again (current count: zero
  false-positive reports since v2.2). The v3 fix amortizes
  the ongoing maintenance + closes a latent class of
  false-positives operators haven't surfaced yet.


## 2026-05-18 — Runway DELETE on /v1/realtime_sessions cancels the conversation

- **Context / claim:** R5 (transcript capture) shipped
  SESSION 146 with full mock-mode test coverage. The
  natural-end path was: operator clicks End → SPA calls
  broker's `_end_session` → broker calls
  `client.realtime_session_end()` → media-engine PATHs to
  Runway DELETE `/v1/realtime_sessions/<id>` → broker
  enqueues `fetch_transcript_for_session` Celery task.
- **Reality / outcome:** Every real-mode session today
  (5 attempts) produced an empty transcript. The Runway
  DELETE returned 204 but the linked
  `/v1/avatar_conversations/<id>` resource flipped to
  `status: "failed", failureCode: "UNKNOWN", endedAt: null,
  transcript: []` permanently. No amount of retry / wait /
  re-fetch produced turns. Three hours of investigation
  chased: (a) webcam request mismatch, (b) DELETE-vs-SDK
  cleanup race, (c) missing END_CALL data-channel message
  — all shipped + tested; all failed.
- **Found by:** Operator's framing reframed the problem.
  "Maybe me hitting the end button is causing the issue?"
  Natural test: start a session, talk, navigate to dashboard
  instead of clicking End → no broker DELETE fired → Runway
  reported `status: "COMPLETED", duration: 76,
  transcript: [3+ real turns]`. The first real
  `Asset(TRANSCRIPT)` of the project (`5e0a488b-...`, 713
  chars, full Caesar-Rubicon dialogue) immediately followed
  via `capture_transcript` running against the same id.
- **Lesson:** **Runway's `/v1/realtime_sessions/<id>` DELETE
  is a cancel, not a normal end.** It marks the session
  CANCELLED and poisons the linked conversation record to
  `failed` with no transcript. The hackathon's `_safe_delete`
  was a teardown-on-failure helper, not the normal end path.
  For programmatic close: skip the DELETE entirely; let the
  SDK's WebRTC disconnect propagate the room close — Runway
  flips to COMPLETED + transcript on its own ~5-15s later.
  Schedule the transcript fetch with `apply_async(countdown=30)`
  to give Runway the finalization window. Fixed
  SESSION 176 (`a0b1843`); persisted as a 1-line comment in
  `_end_session` so a future refactor can't regress.

## 2026-05-18 — Mock-only test coverage hides real-mode contract drift

- **Context / claim:** R-arc shipped 10 slices + R6.1 across
  SESSIONS 142-157 with 150+ Django tests + 32 media-engine
  tests + 95 SPA tests, all green. R10 (the explicit drift
  verifier) checked that every concrete provider implements
  every Protocol method via AST analysis. The R-arc was
  marked "real-mode dogfooded SESSION 158" but that session
  was actually a `talking_head` video bake, not a realtime
  session with knowledge attached.
- **Reality / outcome:** SESSION 176 was the first real-mode
  realtime dogfood with knowledge attached. Found five
  distinct day-1 root causes that the mock-mode coverage had
  hidden:
  1. R4's `MediaEngineClient.realtime_document_create` method
     was never added despite the commit message claiming it
     shipped.
  2. Runway's `/v1/realtime_sessions` payload contract drifted:
     `avatar` must nest as `{type:"custom",avatarId:x}`; tools
     wrap with `{type:"client_event"}`; `parameters` field
     rejected.
  3. SDK `<AvatarCall>` requires `<AvatarVideo />` child + the
     correct `audio`/`video` flag semantics to render anything
     visible.
  4. Transcript fetch parsed Runway response with wrong key
     (`turns`/`messages` instead of `transcript`).
  5. The DELETE-poisons-conversation root cause above.
- **Found by:** Operator dogfood, iteratively. Each fix
  shipped + tested then the next hidden cause surfaced.
- **Lesson:** **Tests that mock the upstream wire never
  assert the upstream wire.** When the test stubs the entire
  external API surface, the test verifies our internal
  glue, not the contract. Pattern: at scope-lock time AND
  after every major upstream API touch, add httpx mocks
  that assert the actual outgoing payload shape against
  the documented contract. R10 (drift verifier) catches
  Protocol-method-set drift but not field-shape drift in
  request bodies. Real-mode dogfood remains the only proof
  of upstream contract compliance until those payload-shape
  tests land. Repeated calibration of the
  `feedback_real_mode_dogfood_after_operator_slices` memory:
  this isn't a one-off, it's a category.

## 2026-05-18 — Operator framing unlocks blockers AI alone misses

- **Context / claim:** After fixing 4 root causes in
  SESSION 176's R-arc dogfood, the operator's session END
  still produced a failed conversation. AI iterated three
  hypotheses in sequence: (a) webcam request → fixed → still
  failed; (b) DELETE-before-SDK-cleanup race → fixed with
  2.5s timer → still failed; (c) missing END_CALL data-channel
  message → fixed by routing through SDK `end()` → still
  failed. Each fix shipped with full test coverage. Three
  hours of work, no real-mode improvement.
- **Reality / outcome:** Operator suggested: "So I just
  thought of something. Does me hitting the end button cause
  the problem? I can tell the avatar bye and that will end
  the conversation as well." Natural test (talk, say bye,
  navigate away — no End button) immediately produced the
  first real transcript of the project. The DELETE itself
  was the killer, not its timing or any SDK-side handshake
  detail.
- **Found by:** Operator's plain-language reframing. The AI
  was deep in specific code theories ("the END_CALL message
  isn't reaching Runway because the SDK unmounted before the
  promise resolved"); operator's question was at a layer
  above: "what if the End button itself is the problem?"
- **Lesson:** **When the AI burns iterations on increasingly
  specific code theories, the operator's plain-language
  reframing is the broader hypothesis worth testing first.**
  The pattern recognition: AI fixes that ship with full test
  coverage but produce zero real-mode improvement on the
  third iteration are a signal that the theory class is
  wrong, not the implementation. Stop iterating; ask the
  operator what they'd test if they were debugging in plain
  English. Their answer is often one level of abstraction
  higher than where the AI is stuck.

## 2026-05-18 — gpt-5 reasoning silently eats output budget

- **Context / claim:** `conversation_synthesis` (K9) used
  `MAX_OUTPUT_TOKENS=400` for chat replies with model
  `gpt-5`, reasoning effort `low`. Documented as "conversation
  replies are shorter than scripts" with the script path
  using 2000.
- **Reality / outcome:** Operator dogfood (Marcus answering
  about teaching Rome to bored 17-year-olds) produced replies
  truncating mid-sentence: "First lens: Machiavelli. He
  argued" — the visible text was ~3 short paragraphs but the
  response capped at the token ceiling. gpt-5 with reasoning
  burns hidden reasoning tokens against the same
  `max_output_tokens` budget; the visible text gets less than
  the nominal cap suggests. Bumping to 1000 immediately
  produced complete 638-token replies with closing questions
  intact.
- **Found by:** Operator visible truncation in chat dogfood
  reply. The token counts in the response confirmed the
  cap was being hit, not the model deciding to stop.
- **Lesson:** **Any operator-visible-text surface using
  gpt-5 needs at least 800-1000 token ceiling.** gpt-5
  reasoning effort `low` still consumes ~30-50% of the
  budget invisibly. Pattern to watch: visible text length
  scales sublinearly with `max_output_tokens` for gpt-5
  vs gpt-5-mini. If a user-facing reply reads as
  truncated mid-thought, suspect the ceiling before the
  prompt.

## 2026-05-18 — Tool descriptions need narration guidance, not just trigger conditions

- **Context / claim:** R7.1's tool descriptions were
  150-200 chars each ("Search the spokesperson's workspace
  knowledge for a specific fact. Use when..."). The
  descriptions told the avatar's LLM WHEN to invoke each
  tool but said nothing about narration around the
  invocation.
- **Reality / outcome:** Operator dogfood: tools fired
  correctly (R7 dispatcher worked, audit rows created, async
  approval flow exercised) but Marcus went silent around
  every invocation. Operator described: "he just moved his
  head back and forth but never said anything." The avatar's
  LLM treats tool calls as silent operations unless the
  description scaffolds the narration explicitly.
- **Found by:** Operator real-mode dogfood. Mock-mode debug
  buttons fire tools through the dispatcher directly, never
  exercising the LLM's narration path. The gap stayed
  invisible until the avatar actually invoked the tool from
  the data channel.
- **Lesson:** **Tool descriptions for LLM-invoked surfaces
  must include narration guidance.** Hackathon descriptions
  were 400-700 chars with explicit:
  * SAY ALOUD before invoking: '<exact phrase>'.
  * After invoking, do NOT wait silently — '<exact next
    action>'.
  * Behavioral rules (do NOT recite chunks verbatim, do NOT
    invent specific dates, etc.).
  Without this scaffolding the avatar invokes silently. With
  it, the next session's transcript showed Marcus saying
  exactly the words from the description ("Let me pull up
  what we covered last time" before
  `recall_recent_conversations`). Pattern: tool descriptions
  are user-facing prompt material, not just dispatch
  triggers — write them like you'd write the avatar's
  script. Length cap 500 for character-os media-engine
  validation; Runway accepts up to 1024.


## 2026-05-18 — Lossy paraphrase of scope locks in start-here menu copy

- **Context / claim:** SESSION 176's wrap re-listed the
  FIRST THING menu for SESSION 177. K10 / F8.1 appeared as:
  "F8.1 K10 seed corpus — draft one piece of seed content,
  then K1-K7 ingest flow exercises against real operator
  knowledge instead of test fixtures. High value because it
  grounds K-arc + R-arc dogfood in operator-authored
  content." The framing assumed "operator-authored markdown"
  was the missing input.
- **Reality / outcome:** Operator pushed back at SESSION 177
  boot: "the whole point of the way we set everything up is
  that the platform creates the content, the user provides
  all of the data, creates the spokesperson and gives the
  spokesperson a personality." The actual K10 scope lock
  (KNOWLEDGE_LAYER.md L1253) is "Onboarding seed:
  `seed_workspace_knowledge` task. `docs/seeds/character_os/
  *.md` corpus. Trigger on `is_operator=True` workspace
  creation." The seed is **platform-shipped content about
  Character OS itself**, ingested automatically into every
  new operator's workspace so day-1 dogfood has real
  reference content. Not operator-authored data uploads;
  not user content the platform synthesizes — platform-
  authored docs about the platform.
- **Found by:** Operator's product-framing pushback against
  the menu copy. AI menu paraphrase had drifted from the
  scope lock's actual shape.
- **Lesson:** **FIRST THING menu items in the start-here
  doc must quote or paraphrase the scope lock accurately;
  re-state the actual blocker, not an AI re-interpretation
  of what the work entails.** When the operator asks "what's
  the blocker?" the answer should match the scope lock's
  own description of the slice. Drift between scope lock
  and menu copy is a load-bearing source of confusion —
  the operator reads the menu, not the scope lock, in
  session-start decisions. Pattern to watch: any FIRST
  THING bullet that paraphrases what a slice involves
  should be cross-checked against the slice's own
  description in the relevant design lock doc. Fixed
  SESSION 177 — start-here K10 entry now references the
  actual scope-lock wording (`docs/seeds/character_os/*.md`
  + `is_operator=True` trigger) and accurately names the
  block as "5-10 short markdown files about Character OS
  itself need to be authored."


## 2026-05-18 — PostCSS silently drops @import declarations placed after @tailwind directives

- **Context / claim:** B2 (SPA flip to V2 dark + gold) shipped
  the V2 token CSS via `@import "./tokens.css";` placed in
  `web/src/styles/globals.css` AFTER the `@tailwind base /
  components / utilities` directives. The TS-side token
  source + the HTML `data-brand="v2"` attribute + the
  Tailwind utility classes all looked correct.
- **Reality / outcome:** Operator reported: "the colors don't
  really look Navy and Gold, they still look like its just
  Black words on a white background." Diagnostic: built CSS
  bundle was MISSING `[data-brand="v2"]` selector entirely
  AND missing the V1 `[data-brand="v1"]` block (also wrapped
  in @layer inside globals.css). CSS spec requires `@import`
  declarations at the absolute top of a CSS file before any
  other rule; PostCSS / Tailwind silently drop misplaced
  imports during compilation. With tokens.css dropped,
  `bg-background` (Tailwind utility → `hsl(var(--background))`)
  resolved to `hsl()` with undefined custom property → invalid
  CSS → browser fallback to white. Gold accents in
  components rendered fine because some component-level
  styles used hardcoded `#C8A35F` or shadcn variants that
  bypassed the var chain.
- **Found by:** Operator dogfood + post-fix diagnostic
  scripting (python regex over `dist/assets/index-*.css`
  checking for `--background:` declarations + their
  enclosing selectors).
- **Lesson:** **`@import` MUST be at the very top of any CSS
  file processed by Tailwind / PostCSS.** No `@tailwind`
  directives, no `@layer` blocks, no comments-then-rules-then
  @import. The hotfix was a 1-line move + a 6-line comment
  block inside globals.css explaining the order requirement so
  a future refactor can't regress. Pattern to watch: when a
  Tailwind utility resolves transparent / undefined and the
  referenced custom property IS defined in an `@import`ed
  file, check import position before debugging cascade /
  specificity. The diagnostic that nailed it: `python3` script
  greppping the built CSS bundle for the selector + the var
  name — would have surfaced the missing block in seconds at
  the start instead of an hour of cache + selector + scope
  speculation.

## 2026-05-18 — Operator catches premature extraction (B-arc B6)

- **Context / claim:** `docs/design/BRAND_ECOSYSTEM_V1.md`
  locked SESSION 178 included `B6 — multi-product extraction
  prep` in the slice breakdown: "lib/brand/ shape audited +
  documented for npm-package extraction. Stub product config
  files for DealerOS / AgentOS / etc. (config-only, no UI) to
  prove the structure." After B5 shipped, the natural AI
  inclination was to keep marching down the slice list and
  ship B6.
- **Reality / outcome:** Operator pushback: "Lets hold off on
  B6 since it sounds like its outside the scope of the actual
  app we are working in right now. We can go back to finishing
  up making sure everything is completed, we still need to
  test the rest of the recipes and things like that anyways."
  Correct call — the BRAND_ECOSYSTEM_V1 lock itself listed
  multi-product extraction in §"Out of scope" with the note
  "Reserved for product #2 reality." B6 was on the boundary of
  that constraint; the AI hadn't read its own scope-lock §"Out
  of scope" carefully enough to refuse the slice.
- **Found by:** Operator pushback at the slice handoff.
- **Lesson:** **The operator's "are we building this for
  something that exists?" framing is the right circuit-breaker
  on architectural slices in a multi-product / extensibility
  arc.** AI tendency in framework-style arcs is to "complete
  the framework" by shipping all the slices; operator tendency
  is "ship for the product reality" and defer extensibility
  work until the second product is real. Operator wins this
  trade by default in this project — premature extraction is
  the trap. Pattern reinforcement of the existing
  "feedback_real_mode_dogfood_after_operator_slices" memory:
  shipping for hypothetical future products is YAGNI; ship for
  the product that exists now, defer the extraction until
  there's a second concrete product driving the requirement.
  Scope-lock §"Out of scope" sections are load-bearing — read
  them before opening a slice that's on the boundary.

## 2026-05-18 — "Visual change isn't applying" mystery was operator cache + color perception, not code

- **Context / claim:** B2 hotfix landed (PostCSS @import bug
  above). Operator hard-refreshed; reported: "The background,
  most of the text is still white, theres a 'A product of
  24/7 GLOBAL AI' in the top left with some of the text in
  gold, the Make a Video button si gold and some of teh ready
  buttons are gold." Partial evidence — gold accents were
  rendering (which proved `--accent` was reaching `bg-accent`
  classes), but background + body text were reported as
  unchanged.
- **Reality / outcome:** Asked operator to paste DevTools
  console output from a one-line snippet
  (`getComputedStyle(body).backgroundColor` etc.). Result:
  `body computed bg: rgb(15, 17, 21)` — exactly V2's
  `--background: 222 18% 7%` = #0F1115. V2 WAS perfectly
  applied. The "white" perception had two contributors: (a)
  operator is color blind and dark navy looks like other dark
  / desaturated surfaces, (b) several components had
  hardcoded light backgrounds (`bg-amber-50`, `bg-white/60`,
  etc.) that were genuinely visible against the V2 dark body
  — those got cleaned up in B3.1 + B3.2.
- **Found by:** Targeted DevTools console snippet returning
  computed style + custom property values. The data
  immediately ended a multi-hour "is V2 actually applying?"
  thread.
- **Lesson:** **When operator reports a visual regression but
  partial evidence shows the change IS live, the fastest
  diagnostic is a DevTools console snippet that reads
  runtime computed styles directly.** Skip code-spelunking,
  skip rebuilding, skip cache-busting. Ask for the actual
  computed values + custom property resolution in 5 lines of
  console output. Pattern to watch: in any "I think the visual
  change didn't apply" debugging thread, the THIRD round of
  hypotheses is the right moment to switch from code-side
  speculation to operator-side DevTools data. Also worth
  noting: operator color blindness affected perception of
  the dark navy palette — future B-arc tone calibration
  (e.g. choosing between subtle palette variants) should
  factor accessibility / color blindness into the choice,
  not assume the operator sees what designers see.

## 2026-05-18 — AI confidently wrong: Celery worker doesn't auto-reload on new primitive registrations

- **Context / claim:** SESSION 179 shipped V16
  (`remove_avatar_background` primitive). After commit
  `57c2530`, I told the operator "Django auto-reloaded the
  new starter (pid 14769). Celery worker (pid 12005) already
  knows `concat_clips` from V5 — no restart needed." That
  framing was correct for V5's already-registered primitive
  but I generalized it to V16's NEW primitive without
  checking. First operator dogfood failed:
  `UnknownPrimitiveError: No primitive registered for
  'remove_avatar_background'`. The Celery worker had been
  running since SESSION 178 close — before V16's
  `apps/compositions/primitives/__init__.py` edit registered
  the new entry. Worker imported the registry at startup;
  later edits don't hot-reload.
- **Reality / outcome:** Restart the worker (`kill -TERM <pid>;
  nohup celery -A character_os worker ...`). New worker
  imports the post-V16 registry. `retry_step` on the failed
  step let the composition resume from the matting stage
  without re-spending Runway credits on already-succeeded
  backdrop + speech steps.
- **Found by:** Operator dogfood of the V16 flow surfaced
  it; Monitor watch caught the `UnknownPrimitiveError` at
  step transition.
- **Lesson:** **Django runserver auto-reloads on `.py`
  changes; Celery does NOT.** Any commit touching
  `apps/compositions/primitives/` OR `apps/*/tasks.py` OR
  `apps/*/signals.py` needs a Celery worker restart on the
  operator's box. The cheap insurance is `ps aux | grep
  "celery -A"` at session start (already in the boot drift
  sweep) PLUS the moment any new primitive / task / signal
  ships. **Pattern**: when committing a registry / signal /
  task change, include a "Celery restart needed" callout in
  the commit message AND restart it before telling the
  operator to dogfood. Same gotcha as the SESSION 147 drift
  audit's "stale running processes" item but for a different
  trigger surface.

## 2026-05-18 — AI confidently wrong: ffmpeg can't infer muxer from .webm.tmp tempfile suffix

- **Context / claim:** V16's media-engine endpoint mirrored
  the existing tempfile pattern from other endpoints
  (`output_path.with_suffix(".webm.tmp")`) and the ffmpeg
  cmd relied on ffmpeg's default "infer muxer from output
  extension" behavior. I shipped V16 (commit `57c2530`)
  thinking the pipeline was correct — the standalone spike
  worked when I tested against `/tmp/test-mat-real.webm`
  (single extension).
- **Reality / outcome:** First real-mode dogfood failed
  with a 500. Standalone repro with the actual function's
  output_path showed ffmpeg dying immediately with "Unable
  to choose an output format for '<file>.webm.tmp'; use a
  standard extension for the filename or specify the format
  manually." This propagated as a BrokenPipeError when the
  rembg-frame writer hit the closed stdin. ffmpeg's
  extension-based muxer inference only handles single
  extensions; `.webm.tmp` is two extensions and the
  inference silently drops it as unknown. Fix in commit
  `88b341e`: add `-f webm` to the ffmpeg cmd to pin the
  muxer explicitly.
- **Found by:** Operator dogfood + AI standalone repro
  capturing ffmpeg stderr to a file (the original code
  routed stderr to PIPE and the BrokenPipeError prevented
  draining it; capturing to a file bypassed that).
- **Lesson:** **When shelling out to ffmpeg with double-
  extension tempfile names (`.webm.tmp`, `.mp4.tmp`,
  `.mp3.tmp`, etc.), always pair the temp suffix with an
  explicit `-f <muxer>` flag.** Default behavior of "infer
  from extension" is silently lost the moment the extension
  isn't a single recognized format. Why the other tempfile-
  pattern endpoints (concat / composite / mix) happened to
  work: their output formats overlap with whatever ffmpeg
  falls back to for unknown extensions in `.mp4.tmp`. The
  `.webm.tmp` combination is the failure case. Pattern to
  watch: when introducing a new output format alongside an
  existing pattern, always sanity-check the muxer is being
  chosen as expected with `ffmpeg -loglevel info` on a tiny
  test invocation. Secondary lesson: capturing stderr to
  PIPE while writing to stdin can deadlock if stderr buffer
  fills — the SESSION 179 fix also drains stderr on
  BrokenPipeError so operators see the real ffmpeg
  diagnostic instead of a generic 500.

## 2026-05-18 — Reinforcement: real-mode dogfood found a bug in every recipe it touched

- **Context / claim:** SESSION 176's R-arc hardening
  established the pattern: mock-only test coverage hides
  upstream drift. The V-arc shipped 18 starter recipes
  SESSIONS 142-144 with mock-mode tests only;
  `talking_head` was the only one real-mode validated
  (SESSION 158). The risk profile was theoretical at
  slice-ship time.
- **Reality / outcome:** SESSION 179 validated three more
  recipes (`long_form_ad`, `cinematic_visual`,
  `talking_head_with_backdrop`). Each surfaced production
  bugs that mock-mode coverage missed:
    - `talking_head_with_backdrop` real-mode → visible 3-
      second backdrop motion seam during a 22s avatar
      speech (V8 single-backdrop limitation; mock-mode
      doesn't render motion so the seam was invisible).
      Fixed in `077c349`.
    - `cinematic_visual` real-mode → 400 because text-only
      prompts defaulted to `gen4_turbo` which requires a
      reference image. Fixed in `9db31c3`.
    - `talking_head_with_backdrop` multi-backdrop real-mode
      → 500 on composite step because concat output's
      `/data/_internal/...` path couldn't be resolved as an
      absolute filesystem path on the media-engine side.
      Fixed in `04fcdb0`.
    - V16 first real-mode dogfood → 500 because ffmpeg
      couldn't infer the output format from `.webm.tmp`.
      Fixed in `88b341e`.
  Three real-mode runs, four production bugs. Two of those
  bugs (`cinematic_visual` model selection and the resolver
  path translation) had been latent for months — would have
  bitten any operator who tried those recipes in production.
- **Found by:** Operator-driven real-mode dogfood. Each bug
  surfaced within seconds of clicking submit; none would
  have been caught by additional mock-mode unit tests.
- **Lesson:** **Real-mode dogfood is not optional for
  operator-facing slices.** Mock-mode test coverage is
  necessary (catches refactoring regressions, exercises
  state machines, hits 4/5 nines of correctness) but
  insufficient (misses upstream provider drift, missing
  field requirements, model-routing logic, format-
  inference bugs). Budget the ~$0.50-$2.00 of Runway spend
  per validation as the cost of not shipping broken
  recipes. Pattern reinforcement of the existing
  `feedback_real_mode_dogfood_after_operator_slices`
  memory: the V-arc's "17 of 18 recipes never real-mode
  validated" backlog is high-probability hidden-bug
  territory. SESSION 180 priority: keep walking through
  the recipes. Don't claim a recipe is "shipped" until a
  real-mode render succeeds end-to-end.

## 2026-05-18 — AI confidently wrong: "200 OK + plausible byte count" doesn't mean correct output

- **Context / claim:** SESSION 180's `talking_head_polished`
  dogfood ran intro_outro through four "fix and re-fire"
  iterations. Each time I told the operator "endpoint
  returns 200, mp4 is the expected size, the fix is in."
  My basis: HTTP 200 status, response body with
  duration_seconds and size_bytes, file at expected path
  on disk. The previous SESSION 180 tests I'd just written
  (`test_dual_card_with_apostrophes_on_non_default_size`
  etc.) all passed.
- **Reality / outcome:** Every one of those "shipped" mp4s
  rendered the intro card as pure-black with no visible
  text. The operator extracted a frame in their player
  and saw blank cards. My status-code-checking tests had
  zero overlap with "is the output visually correct."
  Only after I extracted a frame myself + counted bright
  pixels did the failure mode surface. Three separate
  underlying bugs (missing fontfile=, drawtext text=
  apostrophe collision with fontfile=, and a stale uvicorn
  worker — see next entry) all rolled up to identical
  output md5 hashes that passed every byte-level check.
- **Found by:** Operator playback of the rendered video
  in their browser. The diagnostic that nailed it for me
  was `ffmpeg -ss 1 -i <output> -frames:v 1 frame.png`
  + PIL pixel-count + visual inspection of the PNG —
  the kind of probe I should have run from the very
  first "fix" iteration.
- **Lesson:** **For any endpoint that produces visual
  output, the regression test MUST probe the actual
  rendered output — not just the request/response
  surface.** Status code + byte count + duration is
  necessary but vastly insufficient. The `bright_pixels
  > N` assertion in
  `test_intro_frame_has_visible_text_not_pure_black`
  is the right shape — extract a frame, count
  non-background pixels, fail loud when below threshold.
  Pattern: every drawtext / filter_complex / composite
  endpoint should have at least one test that probes
  rendered pixels, not just response shape. Generalizes
  beyond ffmpeg to anything where "the server happily
  returns success after silently producing the wrong
  output" is even possible — image generators, audio
  mixers, document renderers, anywhere output quality
  isn't a 1-to-1 function of input validity.

## 2026-05-18 — Near-miss: uvicorn --reload has a stale-during-restart window

- **Context / claim:** SESSION 180 mid-session I made
  several rapid edits to `media-engine/app/routers/
  internal.py` (drawtext escape variants, fontfile=
  addition, textfile= pivot). Each edit, I ran
  `retry_step` on the failing composition immediately
  and the operator's logs showed the endpoint returning
  200. I assumed the freshly-edited code was serving
  each re-fire.
- **Reality / outcome:** The regenerated mp4 had
  byte-IDENTICAL md5 hashes to the prior broken
  version across multiple "fix" iterations. That's
  almost impossible if the new code was actually
  running. Eventually I noticed the WatchFiles reload
  log entries clustered around my edit timestamps —
  uvicorn was mid-swap when my retry_step landed and
  the in-flight POST got served by the previous
  module's code. After I killed uvicorn cleanly and
  restarted without --reload, the next regeneration
  produced different bytes + visible text on the very
  first try.
- **Found by:** md5 comparison of "regenerated"
  outputs across iterations, followed by ps inspection
  of the uvicorn pid timestamp vs the edit timestamp.
- **Lesson:** **When iterating on a media-engine
  endpoint with `--reload` active, wait for the
  "Application startup complete" log line between edits
  and re-fires.** Or, more reliably, kill + restart
  uvicorn cleanly between iterations once a single
  test-fix-test cycle is more than a couple seconds.
  The signal that you're in the stale-reload window:
  regenerated output with byte-identical content to
  the prior failed version. Same code path → same
  output. Pattern: when an mp4 / image / artifact has
  the SAME md5 after a code change you expected to
  alter it, suspect process / module staleness before
  suspecting the new code is wrong.

## 2026-05-18 — AI confidently wrong: drawtext text= becomes unusable once fontfile= joins the filter

- **Context / claim:** SESSION 180's first intro_outro
  500 was the drawtext apostrophe escape bug.
  I implemented the POSIX close-escape-reopen pattern
  (`'It'\''s'` parses as `It's`) and verified it
  against ffmpeg directly — the standalone command
  rendered "Riggs's Rules." cleanly. I shipped the
  fix. Then the missing-fontfile= bug surfaced; I
  added `fontfile=` to the same filter. At that point
  every drawtext rendered blank. I cycled through four
  text-escape strategies — POSIX, octal `\047`,
  backslash-only, plain — each of which I confirmed
  "should work" by reading drawtext docs + testing
  variants in isolation. None rendered text once
  fontfile= was in the same filter.
- **Reality / outcome:** The combination of two
  quoted arguments in the same drawtext filter
  confuses ffmpeg's in-filter argument tokenizer in
  ways the docs don't describe and tests-in-isolation
  don't reveal. The escape that works for the
  standalone `text='...'` case silently fails when
  `fontfile='...'` is also present in the filter. The
  fix that actually works: drawtext's `textfile=`
  option reads the literal bytes from a disk file —
  no in-filter escape rules apply. The endpoint now
  writes intro/outro card text to per-cache-key text
  files alongside the cached output mp4.
- **Found by:** Side-by-side comparison: my
  `_build_card_filter` output worked when invoked
  via direct shell ffmpeg, but produced blank when
  invoked via uvicorn / Celery. Eventually traced to
  the fontfile + text combination by manually
  removing fontfile= from the filter (text rendered)
  vs removing the apostrophe from the text (text
  rendered with fontfile=).
- **Lesson:** **Any drawtext invocation that's been
  touched once should use `textfile=` for the text
  argument, not `text=`.** drawtext's in-filter text
  escape rules are a footgun the moment ANY other
  quoted argument joins the filter — even ones
  documented as independent. `textfile=` sidesteps
  the whole problem at the cost of a one-file write
  per call. For media-engine endpoints with caching,
  the textfile naturally piggybacks on the cache_key
  so it's idempotent across reruns. Pattern: never
  trust drawtext text= escape correctness in
  isolation — only test it in the full filter
  context the endpoint actually emits. Generalizes:
  any time a complex filter argument "should work
  per the docs," verify by extracting an actual frame
  from the rendered output, not by parsing the
  command line.

## 2026-05-18 — AI right despite pushback (delayed): operator "are we using X?" framing surfaces capability gaps the dogfood loop wouldn't

- **Context / claim:** SESSION 181 dogfooded 11 V-arc
  recipes end-to-end. All ran through; storyboard_ad
  produced a 3-shot narrative the operator reviewed and
  approved. The character-drift across the 3 shots was
  visible but I framed it as "expected Runway gen4_turbo
  limitation, not a bug." V-arc validation count moved
  from 5 to 16 of 18.
- **Reality / outcome:** Operator paused the dogfood with
  "Are we using Extend Video and Keyframes? I was just
  looking over some other things we have done in the past
  with another Claude Code and it mentioned that one.
  That's a big thing if we aren't using it because that's
  why our scenes aren't flowing longer!" — a recall from a
  different Claude session in a different project. Grep
  confirmed: zero references to Runway's extend endpoint
  or multi-image keyframes anywhere in the codebase. These
  are exactly the features that would cure the V8
  multi-backdrop seam workaround, V13 character drift, and
  V4 10s ceiling — three concrete user-visible gaps the
  V-arc has been working around with chains + concats.
  The "all 11 recipes green" framing missed the
  capability gap completely.
- **Found by:** Operator framing + grep verification +
  Runway API docs review.
- **Lesson:** **The dogfood loop catches bugs (status
  codes, broken outputs, escape footguns); operator
  framing catches missing capabilities the loop literally
  can't see.** All-green dogfood doesn't mean no gaps —
  it means no bugs in the as-shipped surface. Capabilities
  that were never integrated produce no errors and pass
  every assertion. Pattern to carry: when an operator
  questions "are we using X?" with citation from prior
  context (other sessions, other projects, other operators),
  treat it as a capability-audit signal, not a bug report.
  Grep the codebase to confirm before answering; if X
  truly isn't there, that's worth scoping as a slice
  (V17 in this case) rather than hand-waving as "expected
  limitation." Generalizes: the bug-finding loop and the
  capability-completion loop are different. Both are
  necessary; neither substitutes for the other.

## 2026-05-18 — AI confidently wrong: asset upload UI is a recurring gap, not a one-off workaround

- **Context / claim:** SESSION 181's music_bed_pass
  dogfood needed an AUDIO music bed; the workspace had
  zero AUDIO assets. I framed the shell-side
  `Asset.objects.create` + ffmpeg-generated synth pad as
  a "pragmatic dogfood workaround" — implying it was a
  one-off. The next recipe (multi_lang_dub) also needed
  AUDIO; same workaround (extract Riggs voice via ffmpeg
  + shell asset row). Two recipes in one session, same
  gap, same hand-rolled fix.
- **Reality / outcome:** The asset upload gap is a
  **structural product hole**, not a one-off. Any recipe
  that takes an AUDIO or IMAGE input the operator hasn't
  already produced via another recipe runs into it. The
  current workarounds (shell-side rows + manual file
  drops into `data/_internal/uploads/`) work for me but
  are completely unavailable to a real operator using
  the SPA. The dogfood is succeeding because I have
  shell access; the production user would be stuck on
  music_bed_pass and multi_lang_dub indefinitely.
- **Found by:** Recurrence in one session. The first
  workaround should have triggered "this is a missing
  surface, not a missing asset"; the second confirmed it.
- **Lesson:** **When a workaround fires twice in one
  session for different reasons, it's not a workaround —
  it's a missing surface.** Pattern to watch: any shell-
  side ad-hoc `objects.create` to satisfy a recipe form
  signals an SPA-side hole that real operators will hit
  first time. Scope the surface (an asset upload flow
  per the workspace-fabric arc) rather than continuing
  to ad-hoc the workaround. Queued as a follow-up task
  for the workspace-fabric extension arc, not part of
  the V-arc validation push.

## 2026-05-18 — AI confidently wrong: external API validation tightens over time — re-dogfood periodically

- **Context / claim:** V13's gen4_image endpoint shipped
  in SESSION 143 with a 1×1 neutral-grey PNG as the
  no-op reference seed for prompts without an operator-
  supplied reference. The code had unit tests, was
  validated against Runway's API at ship-time, and was
  marked DONE in the V-arc closure. I treated V13 as
  validated when ramping up SESSION 181's storyboard_ad
  dogfood ("storyboard family is the next-lowest-friction
  next-pick — heaviest is storyboard_voiced; the rest
  should be clean since V13 was validated"). storyboard_ad
  failed step 0 immediately: Runway returned 400 "Invalid
  asset dimensions. Height and width must be at least 2px.
  Got 1×1."
- **Reality / outcome:** The 1×1 seed had been accepted
  by Runway when V13 shipped. Runway tightened the API
  validation in the interim (some time between SESSION
  143 and SESSION 181, ~38 sessions or roughly 5 weeks
  of operator-clock time). The code didn't change; the
  upstream contract did. Same shape for the SESSION 181
  V17 framing — Runway's extend + keyframes features
  exist now and might have existed when the V-arc was
  scope-locked but weren't integrated. The shipped-and-
  tested boundary doesn't insulate against upstream
  evolution.
- **Found by:** Operator-driven real-mode dogfood. No
  unit test would have caught it (the seed PNG hasn't
  changed; Runway has).
- **Lesson:** **APIs that "worked when shipped" need
  periodic re-validation against current upstream
  contracts — not just when local code changes touch
  the path.** Pattern to carry: any code path that
  hits a third-party API should be considered
  potentially-stale if it hasn't been real-mode
  validated in the last ~4-6 weeks of operator-clock
  time. Dogfood passes (like SESSION 181's V-arc
  validation sweep) are the cheapest path to surface
  this drift; CI integration tests against live APIs
  are the more expensive but more durable alternative.
  Concrete next-step from this: when re-validating
  recipes against Runway's current API, check for
  newly-available capabilities (extend / keyframes /
  whatever) the same way we check for newly-tightened
  validation. Both are upstream changes that affect us.

## 2026-05-18 — AI confidently wrong: API claim in design doc was hypothesis, not fact

- **Context / claim:** The V17 proposal (SESSION 181)
  was written with the line "Runway's /v1/video_to_video
  extend mode (gen4_turbo / gen4.5). Takes an existing
  rendered clip + a continuation prompt; generates new
  content that flows from the source's tail frame as
  one coherent motion." This was load-bearing for the
  V17.0 endpoint design — the proposal's whole architecture
  assumed Runway shipped an extend API at video_to_video
  with gen4_turbo or gen4.5 as the model. The wording was
  confident enough to scope-lock against.
- **Reality / outcome:** At V17.0 slice-open SESSION 182,
  live WebFetch against `docs.dev.runwayml.com/guides/models/`
  surfaced that `/v1/video_to_video` only accepts
  `gen4_aleph` (V11's style remix model). There is no
  `gen4_turbo` or `gen4.5` mode at that endpoint. The
  capability the proposal described (Runway extends a
  clip API-side) doesn't exist as written. Runway's own
  product UI ships "extend video" via client-side last-
  frame extraction + image_to_video — the external
  observation matches, but the API mechanism is different.
- **Found by:** Live-doc verification at slice-open.
  This is the moment the proposal's hypothesis became
  testable.
- **Lesson:** **A confident API claim in a design doc
  is a hypothesis, not a fact, until live-doc verified.**
  The V17 proposal had been reviewed + edited + scope-
  locked + had rules merged into V1 with the wrong API
  shape baked in. Three of those four steps would have
  been cheap to defer until after live-doc check. The
  fix going forward: **before scope-lock of any slice
  that references a third-party API capability, fetch
  the live doc page and verify the specific
  endpoint+model+param combination exists.** Cheap
  check, prevents an entire scope-lock that has to be
  pivoted mid-implementation. This is the third recent
  entry in this pattern (SESSION 175 KW, SESSION 181
  gen4_image min-dim, SESSION 182 V17 extend). The
  pattern is recurring enough to deserve a slice-open
  checklist item: "1. Live-doc check the API surface
  this slice depends on."

## 2026-05-18 — Pre-implementation pause when a finding shifts scope

- **Context / claim:** During SESSION 182 V17.0 slice-
  open, Q-v17-1 live-doc check found that the V17
  proposal's API premise was wrong (above entry). At
  that moment I had two paths: (a) keep implementing
  with the broken premise, fix the doc later; (b) stop,
  surface the finding to the operator with options,
  wait for direction.
- **Reality / outcome:** I picked (b). Wrote up three
  options (A — pivot to last-frame extraction, B — try
  aleph as extend, C — defer V17) with tradeoffs. The
  operator confirmed A explicitly. Implementation
  proceeded against the correct architecture.
- **Found by:** Self-check at the moment the finding
  came in.
- **Lesson:** When a finding shifts the scope of an
  in-flight slice, **stop and surface to the operator
  before continuing — even if a fork looks "obviously"
  right.** The cost of ~5 minutes of operator review is
  much smaller than committing wrong-shape code, having
  to rip it out, and re-litigating the design after the
  fact. The pause forced me to articulate the three
  options cleanly (instead of barging ahead with my
  preferred one), which surfaced the tradeoffs the
  operator needed. Pattern to carry: **"finding shifts
  scope" + "still implementing" is the failure mode**;
  the right response is always pause + surface +
  operator confirms direction.

## 2026-05-18 — Sync vs async endpoint contract is a design-time decision

- **Context / claim:** The V17 proposal originally
  framed `/internal/clips/extend/` as mirroring V4's
  `/internal/clips/visual/` contract — fire-and-poll,
  return task_id, caller polls
  `/internal/tasks/{task_id}/`. This was written by
  conceptual analogy: both endpoints "create a video
  clip", so they should share contract shape.
- **Reality / outcome:** When Q-v17-1's pivot came in,
  the actual implementation flow surfaced: download
  source clip + ffmpeg-extract last frame + Runway
  image_to_video round-trip (90s) + Runway download +
  ffmpeg concat re-encode. That chain doesn't fit
  fire-and-poll because there's no Runway task to poll
  during the ffmpeg + download stages — the caller would
  have to manage state across multiple disjoint phases.
  Pivoted to V11 style_remix's synchronous shape: one
  HTTP request, the endpoint blocks for the full chain,
  returns one terminal result. The operator gets one
  state per call instead of orchestrating polling against
  a phantom task id.
- **Found by:** Realising that mapping the implementation
  flow onto the proposed async shape produced an awkward
  contract (poll endpoint that has to know about ffmpeg
  state).
- **Lesson:** **Mirror the nearest existing endpoint with
  the same architectural shape**, not the nearest endpoint
  in the same conceptual family. V4 visual_clip is
  conceptually closest to extend (both produce a CLIP
  asset), but architecturally it's fire-and-poll-the-
  provider. V11 style_remix is conceptually farther
  (style transform, not extend) but architecturally
  identical (download + ffmpeg + provider call + concat,
  synchronously wrapped). Synchronous was the right
  choice. Pattern to carry: when designing a new endpoint
  whose flow includes pre/post-processing around the
  third-party call, search for existing endpoints with
  similar wrap-around shape — that's the contract twin,
  even if it lives in a different conceptual family.

## 2026-05-18 — Recipe choice values must be strings per SPA Zod schema (V17.2)

- **Context / claim:** V17.2's `target_duration` field shipped
  with integer choice values (`{"value": 15, "label": "..."}`).
  Backend tests passed; SPA Zod schema check at recipe-add
  time was not performed.
- **Reality / outcome:** First dogfood load of `/recipes`
  returned "Couldn't load recipes" with a Zod parse error
  listing all six int-valued choices as
  `expected string, received number`. **Zod parse failure
  short-circuits the ENTIRE recipe list**, not just the bad
  recipe — every operator in every workspace would have lost
  the gallery until a fix shipped. This is a session-end-
  quality bug class, not just a V17.2 bug.
- **Found by:** Operator-driven SPA navigation, first load
  of `/recipes` after V17.2 ship.
- **Lesson:** **Recipe `choice` values MUST be strings** per
  `web/src/lib/api/recipes.ts` (`recipeFieldChoice.value:
  z.string()`). The backend can carry int choices, but the
  contract crossing the API requires string. Coerce in the
  starter, not the schema. **Add to slice-open checklist for
  any new recipe with non-text choices:** verify the choice
  values are strings before opening the slice. The SPA Zod
  schema is the contract source of truth.

## 2026-05-18 — New recipes need three SPA touchpoints, not one (V17.2)

- **Context / claim:** V17.2 shipped the backend recipe
  (`cinematic_visual_extended` in `recipes.py` + starter).
  Assumption: the V15 form renderer is generic; opening the
  SPA `/recipes` would surface the new card as live, same as
  every other recipe.
- **Reality / outcome:** **Three SPA touchpoints are required**
  for a new recipe to fully ship, not one:
  1. Choice values must be strings (above entry).
  2. The kind must be added to `LIVE_RECIPE_KINDS` in
     `web/src/lib/api/recipes.ts` — otherwise the card
     renders "coming soon" and isn't clickable.
  3. The form-renderer's submission path needs default
     values to be applied (separate entry below).
- **Found by:** Operator-driven SPA navigation. Card rendered
  but showed "coming soon" overlay; operator surfaced.
- **Lesson:** **New-recipe checklist has three SPA items in
  addition to the backend starter + recipe entry:**
  (a) string choice values, (b) opt into `LIVE_RECIPE_KINDS`,
  (c) verify any required-with-default fields submit cleanly.
  None of these are visible from backend unit tests; all three
  surface only at SPA load/use time. Worth a runtime drift
  check at session-start: any recipe in `RECIPES` not in
  `LIVE_RECIPE_KINDS` is either an operator-visible
  "coming soon" or an oversight.

## 2026-05-18 — Form-renderer renders defaults but DROPS them on submission (V17.2)

- **Context / claim:** V17.2's `target_duration` field is
  required + has a default value of "15". The recipe form
  renders the default via `defaultedValue = value ?? field.default`.
  Operator left the select at its default ("15"), clicked
  submit.
- **Reality / outcome:** **POST /api/compositions/ returned
  500** with `TypeError: cinematic_visual_extended() missing
  1 required keyword-only argument: 'target_duration'`. Root
  cause: the form-submission loop checks `form[field.name]`
  (the operator-touched value, undefined if untouched) and
  skips the field entirely if it's undefined — regardless of
  whether `field.default` is defined. The default is shown
  for display but never makes it into the POST body. This
  is a **latent bug across the entire form-renderer** that
  never surfaced before V17.2 because no prior recipe had a
  required-AND-default field (every required field had no
  default; every defaulted field was optional).
- **Found by:** Operator-driven SPA submission with default
  select value.
- **Lesson:** **Form render and form submission must apply
  defaults symmetrically.** Render-side `defaultedValue = value
  ?? field.default` has a submission-side twin: when the form
  state for a field is undefined/empty/null, fall back to
  `field.default` BEFORE submitting. Fixed in commit
  `01ea94d`. The render/submit asymmetry is a class of bug
  worth flagging at SPA reviews — any UI that shows a "default"
  to the operator must also submit it. Pattern to carry:
  **default in render = default in submit, no exceptions.**

## 2026-05-18 — Unit test fixtures must mirror provider output shape (V17.0 silent-clip bug)

- **Context / claim:** V17.0 shipped with 13 unit tests
  covering the extend endpoint. The `_extend_concat` helper
  test used lavfi-generated clips with `anullsrc` audio
  padding (because that's the easy way to make a tiny
  test MP4). Tests passed; helper was considered validated.
- **Reality / outcome:** **First real-mode V17.2 dogfood
  failed at the final concat step with ffmpeg exit 234**
  because Runway's `gen4_turbo` and `gen4.5` outputs are
  SILENT MP4s — neither input has an audio stream. My concat
  filter requested `a=1` on the output; ffmpeg couldn't
  satisfy that from two silent inputs and exited. The unit
  tests never exercised this case because the fixture was
  the easy-to-construct shape (with-audio), not the
  production shape (silent). Classic "fixtures don't match
  production data" trap.
- **Found by:** Operator-driven real-mode dogfood — the first
  time the helper saw real Runway outputs as input.
- **Lesson:** **Unit test fixtures for any helper that
  processes provider outputs MUST mirror the provider's
  actual output shape**, not the easiest-to-construct test
  shape. For Runway visual clips: silent MP4 with no audio
  stream is the canonical shape; `with_audio=True` lavfi
  fixtures are a fiction. Fixed in commit `9fac2b3`:
  `_extend_concat` now probes audio + builds the filter
  conditionally, with 4 new regression tests covering the
  silent-input + mixed-audio cases. Pattern to carry: when
  writing unit tests for code that wraps an external API,
  shape the fixtures after a SAMPLE of the API's actual
  output, not the easiest-to-construct shape. Spending five
  minutes downloading a real Runway output and stripping
  audio would have caught this before ship.

## 2026-05-19 — V17.5 extend chain holds ambient motion, drifts on complex subjects (gen4.5 → gen4_turbo handoff)

- **Context / claim:** V17.5 shipped the
  `use_extend_for_backdrop` opt-in. The design lock anticipated
  motion-continuity would hold at the gen4.5 → gen4_turbo
  extend boundary (last-frame conditioning carries the pose);
  subject-identity continuity was scoped as "best-effort, not
  guaranteed by the API." V17.5 mock-mode tests covered the
  chain shape; real-mode quality was deferred to dogfood.
- **Reality / outcome:** Four real-mode renders SESSION 183
  (Sunset 2 / Underwater 2 / Poker #1 + #2) produced a clear
  split:
  * **Ambient motion holds clean across extends** — Sunset
    coastline (waves + golden light) chained seamlessly; no
    visible quality drop at 10s / 15s / 20s boundaries. Same
    for soft cigarette haze / amber casino light in the poker
    renders.
  * **Discrete-subject identity drifts** — Underwater school
    of fish became "kind of a blob of white" at the first
    extend boundary (~11s) per operator dogfood. Individual
    fish identity that gen4.5 maintained internally was lost
    the moment gen4_turbo took over with only a single last
    frame to condition on. Still visibly better than the
    concat path (no 10s seam), but the failure mode is real
    and operator-visible.
- **Found by:** Operator-driven real-mode dogfood; my
  hypothesis that camera-direction + ambient elements would
  outperform subject-identity was confirmed.
- **Lesson:** V17.5 is a net win for any backdrop dominated
  by **ambient motion or atmospheric elements** (waves, mist,
  fog, smoke, light shafts, fabric, foliage, slow camera
  pans). It loses identity at the boundary for **discrete-
  subject scenes** (named animals, distinct people, vehicles).
  Recipe-form help-text should steer operators toward the
  former; future V17.3 (multi-keyframe conditioning) is the
  architectural fix for the subject-identity case — pin the
  same subject reference image at every extend boundary
  instead of relying on last-frame inference alone. Pattern
  to carry: when a primitive's continuity guarantee is
  scoped to motion-only, operator-facing help text MUST name
  the failure mode by example, not abstraction.

## 2026-05-19 — Avatar speech asset doesn't record duration_ms (composite trim direction wrong)

- **Context / claim:** `composite_video` (kind=backdrop) was
  documented as "trims to the shorter input" — the design
  intent being: render a backdrop chain slightly
  over-provisioned, let composite trim to the speech length.
- **Reality / outcome:** Sunset 2's final clip ran 25.2s
  (the backdrop length); Riggs stopped talking at ~20s.
  The composite trimmed to the LONGER edge, not shorter,
  because the speech step's output asset has
  `duration_ms=None` — `composite_video` couldn't compare
  edges so it defaulted to backdrop length. Operator-visible
  as "Riggs stopped talking before the video ended."
- **Found by:** Operator real-mode dogfood after first
  V17.5 success; surfaced by post-render asset inspection.
- **Lesson:** Two latent gaps, neither V17.5-specific:
  1. **`generate_avatar_speech` primitive doesn't write
     `duration_ms` on its output `Asset`.** The Runway
     response carries the duration; the primitive drops it.
     One-line fix: capture `result.duration_seconds * 1000`
     into the `PrimitiveResult.duration_ms` field, same
     pattern V4's `generate_visual_clip` already follows.
  2. **`composite_video` trim direction silently falls
     back to backdrop when one input's duration is null.**
     Either error loudly (preferred — both inputs should
     have known durations) or document the fallback in the
     primitive header. Pattern to carry: primitives that
     mediate other primitives' outputs should treat
     null-duration as a bug condition, not silently absorb
     it. Both queued for SESSION 184.

## 2026-05-19 — Backdrop prompts need density adjectives; "cigarette haze" reads as people smoking

- **Context / claim:** I drafted three poker-room backdrop
  prompts for V17.5 real-mode dogfood. Option #2's prompt
  was "cinematic slow tracking shot moving past poker tables
  at midnight, warm amber light, soft cigarette haze, motion
  blur on chips and cards, anonymous silhouettes, continuous
  forward camera, locked path" — intended to elicit a busy
  poker room atmosphere.
- **Reality / outcome:** gen4.5 rendered "individuals
  sitting one and twos at tables and smoking" — operator
  feedback. The prompt's "poker tables" + "anonymous
  silhouettes" was insufficient density signal; gen4.5
  defaulted to a sparse scene. Worse: "soft cigarette haze"
  was interpreted literally as **people smoking
  cigarettes**, not as ambient atmospheric haze. Option
  #1's prompt ("busy upscale poker room") did better
  because the density adjective was explicit.
- **Found by:** Operator dogfood comparing Option #1 vs #2
  side-by-side; finding generalizes beyond poker rooms.
- **Lesson:** Backdrop prompts need **explicit density
  adjectives** for populated scenes — "busy," "crowded,"
  "full house," "hundreds of," "every table full" — not
  just the location noun. **Ambient atmospheric elements
  must be named as atmosphere**, not as their physical
  source — "amber light haze" or "warm ambient mist," not
  "cigarette haze" or "smoke from cigarettes." Pattern to
  carry: when writing backdrop prompts for cinematic-fill
  recipes, density words sit alongside subject words; the
  model treats nouns that name humans differently from
  nouns that name atmosphere. Recipe-form help-text should
  carry one example of each shape.

## 2026-05-19 — Default Celery acks-early means worker SIGKILL drops in-flight task without redelivery

- **Context / claim:** When marking compositions FAILED
  mid-flight didn't abort the runtime (execute_composition
  checks composition status at task-start only, not between
  steps), I expected `celery control revoke --terminate`
  with `--pool=solo` to terminate the in-flight task.
- **Reality / outcome:** **`--pool=solo` runs the task in
  the main worker process; SIGTERM via revoke is a no-op
  because terminating it would kill the worker itself.**
  Worker kept polling Runway. Fallback: SIGKILL the worker
  PID. Surprise upside: **Celery defaults to `acks_late=False`**
  (acks-early), so the in-flight task was NOT re-delivered
  to the restarted worker — only queued-but-unstarted tasks
  came back. This saved the remaining backdrop spend on
  the cancelled composition.
- **Found by:** Operator-driven cancel during V17.5 dogfood
  retry sequence (concat-path renders kicked off pre-hard-
  refresh); needed to clear queue cleanly before V17.5
  could fire.
- **Lesson:** Two operational facts worth carrying:
  1. **`--pool=solo` + revoke --terminate is a no-op.** The
     only way to stop an in-flight solo-pool task is
     SIGKILL the worker PID. Cost: ~5s downtime + need to
     pre-stage state (mark queued compositions FAILED with
     no-pending-steps so their re-delivery is a no-op
     bail). Pattern to carry: if a long-running composition
     needs cancellation, plan the worker restart, don't
     trust revoke.
  2. **acks-early is the default and is the right default
     here.** Means worker death loses only the in-flight
     task, not the queue. Pattern to carry: if you ever
     flip `acks_late=True` for safety, plan the
     consequence — every worker death will re-deliver the
     in-flight task to the next worker, and if it's a
     long-tail render, you'll pay twice.

---

## SESSION 184 — six entries

### Live-doc-check discipline is now 2-for-2 on V17 surface
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** Opening V17.3 (keyframes) per the SESSION
  183 close-out plan. Before writing code, ran a live-doc
  check against Runway's auto-generated Python SDK
  (`runwayml/types/image_to_video_create_params.py`).
- **Surface / artefact:** V17 proposal's claim that
  `gen4_turbo` supports a `keyframes: [str]` array.
- **AI expectation (before):** Code straight against the
  proposal's described shape.
- **Reality / outcome:** **No `keyframes` array exists;
  conditioning is `promptImage: str | Iterable[{position,
  uri}]`; `gen4_turbo` only accepts `position: "first"`.**
  Only `gen3a_turbo` (ratio cliff) and `veo3.1_fast`
  (Google Veo brokered through Runway) support both
  first+last. The slice's motivating use case (Hook +
  Payoff on `gen4_turbo`) is not implementable as
  written.
- **Found by:** AI's slice-open live-doc check per the
  discipline codified at SESSION 182's Q-v17-1 resolution.
- **Lesson:** Two-for-two now — Q-v17-1 (SESSION 182,
  `/v1/video_to_video` model constraint) AND Q-v17-6
  (SESSION 184, keyframes shape) both surfaced
  before-code by the live-doc check. **The rule
  hardens:** third-party-wrapping slices MUST live-doc-
  check the API surface against the provider's
  source-of-truth (auto-generated SDK, OpenAPI spec, or
  official docs — NOT the design doc) before code is
  written. Two saves of multi-session rewrites; pattern
  is established.

### V18 + duration mismatch needs starter-time guard
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** V18 real-mode dogfood. Operator picked a 5s
  backdrop_clip (gen3a_turbo smoke output) on a script
  that estimated to ~9s of speech.
- **Surface / artefact:** Composition `b2188dcf` output.
- **AI expectation (before):** Composite would trim to
  speech length (matching the SESSION 183 Sunset 2
  symmetry — speech short, backdrop long → trim long edge).
- **Reality / outcome:** **Composite trimmed to the
  SHORTER input (backdrop, 5s), cutting Riggs's 9s speech
  mid-sentence.** The composite primitive's "trim to
  shorter input" rule is symmetric; v1 has no asymmetry
  for "speech is the load-bearing track."
- **Found by:** Operator-visible "audio ends in middle of
  sentence" on the composite output.
- **Lesson:** When a recipe consumes a duration-bearing
  input as a backdrop (V18's case), the starter MUST
  validate the input's duration covers the estimated
  speech duration. Add to slice-open checklist for any
  starter that wires asset inputs at known-duration
  positions: validate `backdrop.duration_ms >=
  _estimate_avatar_speech_seconds(len(script)) * 1000`
  BEFORE Composition rows are created. Patterns extends
  beyond V18 — anywhere a CLIP input must outlive another
  CLIP input, validate at starter-time.

### Asset taxonomy gap is structural
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** V18 dogfood. Operator picked a backdrop_clip
  from the recipe-form asset_picker that turned out to
  be the gen3a_turbo smoke output — a 5s person
  interpolation, not a scene. "Two random people" appeared
  in the backdrop track because gen3a_turbo's keyframe
  drift produced two visibly different humans across the
  5s clip.
- **Surface / artefact:** Recipe form asset_picker
  dropdown listing 119 CLIPs of mixed primitive-kinds.
- **AI expectation (before):** Operator picks a backdrop
  by inferring from composition name + creation date.
- **Reality / outcome:** **Inference fails at 119 assets.**
  The asset_picker filters by `asset_type` (the medium)
  but not by *intended use* (backdrop vs talking-head vs
  composite-output vs intro/outro card vs reference image).
  A talking-head MP4 and a cinematic backdrop MP4 are both
  `asset_type=CLIP`; the picker can't tell them apart.
- **Found by:** Operator-driven scope discussion after the
  V18 dogfood's "two random people" finding.
- **Lesson:** When metadata categorizes assets by
  production method but the operator filters by intended
  use, the categorization is the wrong shape. Triggered
  the Asset Library scope proposal
  (`docs/design/ASSET_LIBRARY_V1.md`) with a 9-role closed
  enum stamped at primitive-emit time. Pattern: anytime a
  picker UI exists, audit whether its filter axes match the
  user's mental model of "what does this asset DO" not
  "how was this asset MADE."

### Smoke commands without --save-assets produce orphans
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** Wrote `smoke_keyframes` management command
  as "no DB writes" for minimum-footprint design. Fired
  both models, got back two HTTPS Cloudfront URLs in
  stdout.
- **Surface / artefact:** Smoke output URLs.
- **AI expectation (before):** Operator opens the URLs in
  a browser, picks the winner, design decision happens.
- **Reality / outcome:** **Operator wanted to see the
  smoke outputs in the workspace UI.** "I don't see any
  new videos on the UI, are they hidden somewhere I can't
  see them?" The URLs work but they're not browsable
  through normal product surfaces — operators expect
  workspace outputs to land in the workspace.
- **Found by:** Operator surfaced the UI gap immediately
  after the smoke completed.
- **Lesson:** Smoke / dogfood / scratch commands should
  default to creating workspace Asset rows with audit
  metadata (model, task_id, prompt, session). Opt-out via
  `--no-save-assets` flag if a smoke wants to skip the
  side-effect. The "minimal footprint" framing is wrong
  shape — minimal in CODE doesn't mean minimal in
  OPERATOR EXPERIENCE. Future smokes default to
  backfilling.

### Celery worker stop-state is silent
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** Operator fired the V18 dogfood via the SPA
  recipe form. Composition row was created with status
  `draft`; step 0 status `pending`. After 8.5 minutes
  the operator noticed "seems like it's been running for
  longer than normal."
- **Surface / artefact:** Composition `b2188dcf` stuck
  in `draft` for 8.5 minutes.
- **AI expectation (before):** Composition would
  transition `draft → running → completed` within 1-3
  minutes of fire.
- **Reality / outcome:** **No Celery worker was running.**
  The recipe view queued `execute_composition.delay()`
  to Redis but there was no consumer. The runtime gave
  no signal — no SPA error, no admin alert, no log line
  saying "queued but no worker available."
- **Found by:** Operator-driven "this is taking too long"
  intuition; AI investigation found the missing worker
  process.
- **Lesson:** A queued-but-not-consumed task is currently
  invisible at every operator-facing surface. The SPA
  shows the composition card as if it's running; admin
  shows status=draft indistinguishable from
  legitimately-draft. Either the health monitor should
  treat zero workers as a critical alert OR the
  composition runtime should detect "queued >30s with no
  worker pickup" and surface it. Today's behaviour: silent.
  Until that's fixed, session-start should include `ps
  aux | grep celery` as part of the stack-up sanity
  check.

### Re-using smoke outputs as backdrops is a testing-shape mismatch
- **Date:** 2026-05-19
- **Session:** 184
- **Context:** V18 dogfood after the smoke_keyframes
  comparison. Operator picked the gen3a_turbo smoke
  output (`89a1ce5f`) as the V18 `backdrop_clip` to
  validate the picked-clip path.
- **Surface / artefact:** V18 composition output showing
  "two random people" instead of a clean backdrop.
- **AI expectation (before):** Any workspace CLIP is fine
  as a V18 backdrop — composite just overlays the
  avatar.
- **Reality / outcome:** **The gen3a_turbo smoke was a
  person-interpolation, not a scene.** Its source was a
  V13 storyboard Hook (founder at 3am) + Payoff (founder
  at sunrise); the keyframe interpolation produced two
  visibly different "founder" humans across 5 seconds.
  Wiring that into V18's backdrop slot dragged the
  Q-v17-3-shape drift INTO V18's output. The V18 bug
  signal wasn't a V18 bug; it was a picker-wrong-content
  bug.
- **Found by:** Operator-visible "two random people" in
  the V18 dogfood output; AI initially mis-diagnosed as
  Riggs's avatar identity issue before the operator
  reframed it.
- **Lesson:** When testing a feature that consumes a
  generic input slot (asset_picker, file upload, URL),
  the test materials must match the slot's intended
  shape. The gen3a_turbo smoke was a "subject animation"
  test artifact; it doesn't belong in a "backdrop scene"
  slot. Asset Library A7 (role-filter on picker) is the
  structural fix; meanwhile the discipline is "pick
  testing materials with intent." Triple-check the test
  fixture before claiming the system-under-test is the
  bug source.

### Walk a proposal's mechanism through its motivating calibration before locking
- **Date:** 2026-05-19
- **Session:** 185
- **Context:** Asset Library v1 scope-lock review. The arc
  was proposed in SESSION 184 because of the V18
  smoke-output-as-backdrop bug (SESSION 184 calibration #6
  — "Re-using smoke outputs as backdrops is a
  testing-shape mismatch"). The design doc explicitly cited
  A7 (role-filter on asset_picker) as the structural fix.
- **Surface / artefact:** Pre-lock review of
  `docs/design/ASSET_LIBRARY_V1.md` §In-scope
  clarifications. The doc said smoke_keyframes outputs
  backfill as `BACKDROP` ("they were produced as
  scene/motion experiments, fit the backdrop role even
  though produced via a smoke command").
- **AI expectation (before):** The 9-role taxonomy was the
  contract foundation; defer ambiguity to A2 slice-open.
- **Reality / outcome:** **Backfilling smoke outputs as
  BACKDROP would have re-triggered the exact bug A7 was
  supposed to fix.** If smoke outputs carry `role=BACKDROP`,
  A7's "role-filter on picker" change still surfaces them
  in the backdrop dropdown. The operator's "two random
  people" finding from V18 would re-run unchanged. The
  scope-lock review caught this; operator agreed to add a
  10th role (`EXPERIMENT`) and switch the backfill
  heuristic. Resolved at lock, not deferred to a later
  slice.
- **Found by:** AI pre-lock-review pass against the design
  doc + the originating calibration event.
- **Lesson:** When locking a scope motivated by a specific
  prior calibration, **walk the proposed mechanism through
  the original failing scenario.** If the mechanism doesn't
  fix the failure end-to-end, the proposal needs revision
  before lock — not at the first implementation slice.
  Same shape as the SESSION 182 / 184 "live-doc-check the
  API surface" discipline, but applied to design proposals
  against their motivating evidence rather than to
  third-party API shapes.

### Doctor heuristics over-match on project-shape naming conventions
- **Date:** 2026-05-19
- **Session:** 185
- **Context:** SESSION 185 boot drift-sweep. context-kit
  `doctor` reported 3 warnings: missing inventory file,
  version drift, missing handoffs SESSION_053/SESSION_172.
- **Surface / artefact:** `context-kit doctor` output.
  Two of the three "version drift" hits were doctor's
  `_VERSION_RE` regex (`\b\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)?\b`)
  matching `127.0.0.1` (uvicorn `--host` literal in
  stack-up bash) AND `W11.6.5.1-3` (W-arc sub-slice naming).
- **AI expectation (before):** Doctor warnings reflect
  real drift between code and docs.
- **Reality / outcome:** **Two of three "drifts" were
  doctor heuristic false positives** driven by the
  regex over-matching project-shape strings (IP literals
  + multi-component slice IDs). pyproject was correctly
  `0.0.0` (intentional monorepo placeholder); no real
  version drift existed. The fix was to scrub the
  matching literals from start-here (uvicorn → localhost;
  `W11.6.5.1-3` → `W11.6.5 sub-slices 1/2/3`).
- **Found by:** AI investigation of doctor source code
  in `cli/state.py` + `cli/doctor.py`.
- **Lesson:** **Doctor heuristics are guidance, not ground
  truth, when project naming conventions overlap the
  regex shape.** Treat doctor warnings as a starting point
  — investigate the actual heuristic before scrubbing
  state. Cleanup that disguises a literal to defeat a
  regex is a smell that the heuristic, not the project,
  is wrong — but for SESSION 185's purpose (clean exit)
  the disguise was the right call. Upstream fix sits with
  context-kit (skip IP-shaped + alpha-prefix-shaped
  strings); pragmatic fix sits with the project.

### One-runner-emit, many-callers is the cleanest shape for cross-cutting Asset metadata
- **Date:** 2026-05-19
- **Session:** 186
- **Context:** A2 — every primitive in
  `apps.compositions.primitives` must stamp `role` on its
  output Asset. At slice-open, three architectural options:
  centralize in the runner (look up role from primitive_kind
  at persist time); have each primitive import the mapping
  table; or have each primitive stamp an explicit
  `AssetRole.X.value` at the emit site.
- **Surface / artefact:**
  `apps/compositions/asset_roles.py` (new shared mapping
  module), `apps/compositions/primitives/mock.py`
  (`PrimitiveResult.role` field), all 14 primitive modules
  (explicit `role=AssetRole.X.value` at every
  `PrimitiveResult(...)` call), `apps/compositions/tasks.py`
  (`_persist_output_asset` raise-on-missing backstop).
- **AI expectation (before):** Centralizing in the runner
  seemed minimal — one lookup site, no per-primitive
  changes. Each primitive importing the mapping seemed
  cleanest from a "single source of truth" angle.
- **Reality / outcome:** **Stamping explicit role
  literals at each emit site was the right shape.** The
  emit site reads cleanly in isolation (no chasing an
  import); the runner enforces (defense-in-depth raise);
  the coverage test guarantees the explicit literal
  matches what PRIMITIVE_TO_ROLE says (so the two stay
  aligned by test rather than by indirection). A2
  covered 28+ emit paths with two architectural-layer
  edits (PrimitiveResult.role field + runner pass-through
  + raise) + per-primitive literal additions. The realtime
  arc has its own single Asset.objects.create site
  (`capture_transcript`) — same pattern applied there.
- **Found by:** AI architecture pass at slice-open;
  operator implicitly confirmed via the design lock's
  "single source of truth" framing.
- **Lesson:** **When a new cross-cutting Asset field
  lands, find the funnel point first (single
  Asset.objects.create site), add the field there, then
  push to the source-of-truth producers (PrimitiveResult).
  The producers stamp explicitly (readable); the funnel
  enforces (defense-in-depth); the coverage test binds
  the two halves.** This shape generalizes: any future
  cross-cutting metadata (tier annotation, region, retention
  policy) can follow the same pattern.

### Subagent went to source-of-truth and caught an upstream brief error
- **Date:** 2026-05-19
- **Session:** 189
- **Context:** A5 delegated to the `react-web-delivery` subagent
  with a detailed brief covering the A4 endpoint shape, Zod
  schemas, and AssetType / AssetRole enum values to mirror. The
  brief was assembled from memory + a quick read of
  `_serialize_list_asset`; AssetType values were rendered in the
  brief as uppercase (``"CLIP" | "IMAGE" | ...``).
- **Surface / artefact:**
  `web/src/lib/api/workspace-assets.ts` Zod enum definitions.
  AssetType in `shell/apps/compositions/models.py` is in fact
  ``CLIP = "clip", "Video Clip"`` (TextChoices — the second
  value is the human label; the first is what the API returns).
- **AI expectation (before):** The subagent would honor the
  brief verbatim, including the uppercase enum values, and
  produce Zod schemas that wouldn't parse real API responses.
  This would have been caught at the first vitest fixture or
  the first dev-server fetch, but later than at slice-open.
- **Reality / outcome:** **The subagent went to
  `apps/compositions/models.py` itself, read the actual
  TextChoices values, and wrote the Zod enums in lowercase.**
  All 25 new vitest tests pass; build clean. The brief error
  was silently corrected without escalation.
- **Found by:** AI spot-check during the verify-trust pass
  after the subagent reported done.
- **Lesson:** **Subagents with read-tool access can and should
  cross-check brief claims against source-of-truth. Write
  briefs that POINT at source-of-truth (file paths) rather
  than RESTATING it (the values themselves), so the agent
  doesn't get a worse signal than reading the code directly.**
  Generalizes: any subagent delegation should treat the brief
  as a pointer to ground truth, not a substitute for it. When
  the brief and source disagree, source wins — and the agent
  is the right place to enforce that.

### A-arc growth template — 7 narrow slices, half-session cadence, backend → SPA progression
- **Date:** 2026-05-19
- **Session:** 192
- **Context:** Asset Library v1 closed in 7 sessions (185-192,
  one arc-close ceremony commit aggregated with A8). All 9 slices
  shipped without scope creep, deferrals beyond the pre-lock
  Q-a-6 v2 punt, or session overruns.
- **Surface / artefact:** Slice breakdown in
  `docs/design/ASSET_LIBRARY_V1.md`; commit history
  `78ddd5d..` through `<A8 commit>`; 14 feat+docs commit pairs.
- **AI expectation (before):** A 9-slice arc would feel
  similar to V (16 slices) or R (10 slices) — multiple
  multi-session features, real-mode validation between
  slices, occasional re-scoping.
- **Reality / outcome:** **A-arc was the cleanest arc to date.**
  The template that worked:
  * **Backend before SPA**: A0 (model) → A1 (data migration) →
    A2 (production emit) → A3 (helper) → A4 (read endpoints)
    formed the entire backend in 4 sessions. SPA started at A5
    with a live, stable endpoint to consume.
  * **One-runner-emit, many-callers** (the SESSION 186 A2
    calibration) — adding a cross-cutting field to PrimitiveResult
    + threading through the single Asset.objects.create site
    covered 28+ primitive emit paths.
  * **Subagent delegation for SPA slices** — A5 + A6 both
    landed via `react-web-delivery` with high precision once
    briefs pointed at source-of-truth files rather than
    restating values (SESSION 189 calibration).
  * **Operator-visible payoff prioritized mid-arc** — A7
    (role-filtered picker) was the structural fix the arc
    existed to ship. Operator picked A7 over A6 at SESSION 190
    slice-open; arc continuity resumed after.
  * **Arc-close ceremony pattern** — regen INVENTORY, mark
    status: complete in design lock, TRUST_CALIBRATION entry,
    handoff names the arc closed. Same shape as V-arc and
    R-arc closures.
- **Found by:** Retrospective at arc close (SESSION 192).
- **Lesson:** **The 9-slice / ½-session-each shape works.** For
  the next arc with a clear backend-then-SPA shape, default to:
  * Lock 9 slices.
  * Ship backend in 4 sessions (model → backfill → emit →
    endpoint).
  * Ship SPA in 2 sessions via the react-web-delivery agent.
  * Reserve 1 session for the operator-visible structural fix
    (the slice the arc exists to enable) — operator picks the
    timing.
  * Close with 1 session for cross-link / lineage / arc-close
    ceremony.

### Celery worker is NOT optional for mock_mode — promote to hard stack-up rule
- **Date:** 2026-05-19
- **Session:** 193
- **Context:** SESSION 193 Asset Library v1 arc-close dogfood. The
  SESSION 192 start-here stack-up notes claimed
  *"mock-mode covers both — no media-engine / Celery required"*.
  Operator opened the dogfood, browsed assets (A5), exercised the
  role-filtered picker (A7), and fired a `talking_head_with_backdrop`
  composition with `mock_mode=true`. **Composition sat at DRAFT for
  104s with both steps `pending`, no error_message, no Celery worker
  in `ps`, 65 messages backed up in the Redis `celery` queue.**
- **Surface / artefact:** `00-START-NEXT-SESSION.md` stack-up notes;
  `docs/handoffs/SESSION_192_*.md` stack-up section. The wrong claim
  was written at SESSION 192 close and survived into SESSION 193
  start-here.
- **AI expectation (before):** Mock_mode would short-circuit the
  primitive pipeline somewhere upstream of Celery, so a worker
  wouldn't be needed.
- **Reality / outcome:** **Mock_mode skips Runway / Stability API
  calls (it controls primitive behavior); it does NOT bypass the
  Celery task wrapper.** The composition runtime still enqueues
  `execute_composition.delay(...)`. Without a worker consuming the
  queue, the task envelope sits in Redis forever and the composition
  hangs silent at DRAFT. **This is the SESSION 184 calibration #5
  "Celery worker stop-state is silent" trap, hit for the second
  time** — and the dogfood pass caught the start-here error within
  2 minutes of opening the session.
- **Found by:** Operator firing the composition during the
  arc-close dogfood pass; AI tail of the DB / Celery queue
  identified the stuck-DRAFT shape immediately.
- **Lesson:** **PROMOTE to hard stack-up rule.** Any session that
  will fire compositions — mock_mode OR real-mode — requires a
  running Celery worker. The `celery -A character_os worker
  --loglevel=info --pool=solo` line moves from "optional helper" to
  "required step" in the stack-up checklist. The wording in
  start-here stack-up sections that calls mock-mode "Celery-free"
  is **wrong** and must be scrubbed at the SESSION 193 close.

### Arc-close dogfood is high-yield even after every slice was test-validated
- **Date:** 2026-05-19
- **Session:** 193
- **Context:** Asset Library v1 closed SESSION 192 with 134 SPA
  vitest + 995 Django pytest tests passing — full automated
  coverage of every slice. Real-mode dogfood was framed as
  "optional verification" in the SESSION 192 close-out.
- **Surface / artefact:** SESSION 192 start-here recommended the
  dogfood pass; SESSION 193 ran it.
- **AI expectation (before):** With every slice automated-test
  covered, the dogfood pass would be a green-rubber-stamp
  formality.
- **Reality / outcome:** **Dogfood caught a real start-up rule error
  in the stack-up notes within 2 minutes.** The unit + integration
  tests use `CELERY_TASK_ALWAYS_EAGER=True` (via fixture / settings
  override) so they bypass the broker entirely. **The "is the dev
  stack actually usable for the operator" question is structurally
  outside the test surface** — tests verify the code; dogfood
  verifies the dev experience.
- **Found by:** Operator hitting submit on the V18 form during the
  arc-close pass.
- **Lesson:** **Arc-close dogfood is non-negotiable, not optional.**
  Even with full automated coverage, the dogfood pass catches a
  category of failure tests cannot: stack-up notes, environment
  assumptions, default-on/off settings, the gap between "tests pass
  with EAGER=True" and "real runserver needs a worker." Same shape
  as SESSION 173's "real-mode dogfood after operator-facing
  slices" calibration — that one was about Runway-side drift;
  this one is about local-dev drift. Generalizes:
  **test passing ≠ dev stack usable**.

### mix_audio assumes base clip has audio — silent-base recipes 500 at ffmpeg
- **Date:** 2026-05-19
- **Session:** 195
- **Context:** SESSION 195 V-arc closure dogfood. Operator fired
  `storyboard_voiced` (V15.4 bonus, 10 steps) in real-mode against
  the dev Runway+Stability stack. Steps 0-8 succeeded (3 images +
  3 visual clips + concat + avatar speech + audio extract).
  **Step 9 (`mix_audio`) failed with 500** from
  `POST /internal/audio/mix/` in 60ms (server-side rejection, not
  a real ffmpeg run).
- **Surface / artefact:** ffmpeg filtergraph in media-engine's
  `/internal/audio/mix/`:
  `[1:a]volume=...,afade=t=in:st=0:d=0,afade=t=out:st=999999:d=0[bed];[0:a][bed]amix=inputs=2:duration=first:normalize=0[outa]`
  ffmpeg error: *"Stream specifier ':a' in filtergraph description
  matches no streams. Error binding filtergraph inputs/outputs:
  Invalid argument."*
- **AI expectation (before):** `mix_audio` would handle any
  base+overlay audio combination since both upstream outputs
  exist with valid file paths.
- **Reality / outcome:** **`mix_audio`'s filtergraph references
  `[0:a]` (the base's audio stream), but in `storyboard_voiced`
  the base is the silent visual concat (3× `generate_visual_clip`
  outputs stitched together — video-only, no audio track).**
  `generate_visual_clip` produces silent clips; concat of silent
  clips is still silent. ffmpeg fails fast because `[0:a]`
  doesn't exist.

  The V14 `mix_audio` primitive was designed for the
  **music_bed_pass** use case (base = avatar speech WITH audio +
  overlay = music track → `amix` combines them). V15.4's
  `storyboard_voiced` bonus added an `audio_extract` + `mix_audio`
  chain assuming the same mix semantics would work for "narration
  over silent storyboard" — they don't. The needed semantics
  are audio REPLACEMENT (`-map 1:a` from overlay), not audio
  MIXING.
- **Found by:** Real-mode dogfood pass at SESSION 195. Caught at
  step 9 of 10 after $1.92 of upstream Runway+Stability spend
  was already committed.
- **Lesson:** **Two-layer finding.**

  (1) **Primitive boundaries need to be tested across all
  consumer recipes, not just the recipe that motivated the
  primitive.** `mix_audio` was test-covered for music_bed_pass +
  unit tests with mock-mode primitives; storyboard_voiced
  exercises a different audio shape that mock tests didn't see
  because mock primitives don't actually decode media streams.

  (2) **`generate_visual_clip` produces silent output** is an
  invariant the downstream pipeline must accommodate. Either
  `mix_audio` detects missing base audio + falls through to
  `-map 1:a` (best — same endpoint, smarter behavior); OR the
  starter pre-encodes a silent track; OR a new `replace_audio`
  primitive lands. Half-session fix slice. Operator picked the
  media-engine-side fix path at SESSION 195 close.

### concat_clips role semantics are recipe-dependent — A2's unconditional BACKDROP stamp is wrong for dialogue_scene
- **Date:** 2026-05-19
- **Session:** 195
- **Context:** SESSION 195 V-arc closure dogfood. Operator fired
  `dialogue_scene` (V14, 5 lines + concat) in real-mode. End-to-end
  success — 145s wall-time, $1.25, 6 produced assets. **But the
  concat output (final deliverable) was stamped `role=backdrop`
  by the A2 emit-time logic.**
- **Surface / artefact:** `apps.compositions.primitives.concat_clips`
  unconditionally sets `role=AssetRole.BACKDROP.value` on its
  PrimitiveResult (introduced in SESSION 186 A2). Recipe consumers:
  * `talking_head_with_backdrop` V18 chain — concat of N backdrops
    → BACKDROP ✓ semantically right
  * `storyboard_voiced` V15.4 — concat of 3 silent visual clips
    → BACKDROP ✓ same shape
  * `dialogue_scene` V14 — concat of N talking_head clips → final
    deliverable → **BACKDROP ✗** should be COMPOSITE_OUTPUT or
    similar
- **AI expectation (before):** A2 stamped role per primitive_kind
  with a 1:1 mapping. The mapping was operator-validated against
  the SESSION 184 V18 dogfood evidence + the SESSION 185 backfill
  heuristics — both motivated by the backdrop use case.
- **Reality / outcome:** **The same primitive serves multiple
  recipes with different semantic intents.** Static `primitive_kind
  → role` mapping breaks down for combinator primitives (`concat_clips`,
  `composite_video`, `mix_audio`) whose role depends on what's
  being combined.

  Operator-visible consequence: A7 role-filtered backdrop_clip_id
  picker would now offer the dialogue_scene's 25-second final as
  a valid backdrop. Picking it would produce a nonsensical V18
  render (avatars-over-avatars).
- **Found by:** AI tail of the post-completion Asset Library
  state at SESSION 195 dogfood close.
- **Lesson:** **A2's contract rule 20 ("every primitive stamps a
  role") is structurally correct but the implementation needs a
  per-recipe override for combinator primitives.** The cleanest
  fix path (operator-picked at SESSION 195 close): add a
  `result_role` param to combinator primitives (`concat_clips`
  first; `composite_video` + `mix_audio` likely too). Recipe
  starter passes `result_role` in the step's params; primitive
  reads + stamps. Backwards-compat default keeps the V18 /
  storyboard_voiced behavior.

  **Generalizes:** when a primitive serves multiple recipes with
  different deliverable semantics, role assignment needs to live
  at the recipe layer, not the primitive layer. The runner-funnel
  + per-primitive stamp pattern (SESSION 186 A2 calibration) holds
  for emitters; combinators need the override seam.

### Real-mode dogfood finds bugs in EVERY recipe — confirmed 2-for-2 on V-arc closure attempt
- **Date:** 2026-05-19
- **Session:** 195
- **Context:** SESSION 195 set out to validate the last 2
  unvalidated V-arc recipes (`storyboard_voiced` + `dialogue_scene`)
  in real-mode to close the V-arc to 100%. Both recipes pass mock-mode
  tests cleanly; mock-mode test coverage at SESSION 195 was 1006
  Django pytest + 134 SPA vitest. Operator was prepared to "validate
  + close" the V-arc.
- **Surface / artefact:** Two real-mode fires, two production bugs
  caught:
  * `storyboard_voiced` — mix_audio silent-base ffmpeg filtergraph
    bug (V14 design oversight, never seen because music_bed_pass
    always has audio base).
  * `dialogue_scene` — concat_clips role semantics mismatch (A2
    implementation gap, never seen because mock primitives don't
    drive the role-filter SPA picker).

  Combined spend: ~$3.17 ($1.92 wasted on storyboard_voiced
  partial; $1.25 productive on dialogue_scene).
- **AI expectation (before):** Both recipes had clean mock-mode
  test coverage shipped at V15.4 + V14. Operator framed the
  session as "validate + close the V-arc" with mild risk of a
  finding.
- **Reality / outcome:** **2-for-2 real-mode bugs in 2 recipes
  attempted.** Stronger evidence than SESSION 158's calibration
  warranted — "real-mode dogfood finds bugs in every recipe"
  is now empirically near-certain, not just "high yield."
  Both bugs were latent for many sessions (V14 shipped
  SESSION 143 era; A2 shipped SESSION 186) without any test
  surface catching them, because:
  * mock primitives don't decode media streams (so mix_audio's
    filtergraph never sees a real silent-input)
  * unit tests don't exercise the A7 picker semantics with
    real recipe finals
- **Found by:** Operator firing both recipes in real-mode against
  the dev Runway+Stability stack. AI tail diagnosed both bugs
  within 1-2 minutes of the symptom appearing.
- **Lesson:** **Promote the SESSION 158 calibration from "high
  yield" to "expected behavior."** Every untested-in-real-mode
  recipe carries a near-certain latent bug. Two corollaries:
  * Real-mode dogfood is non-negotiable before any recipe
    claims "shipped." Mock test coverage is necessary but
    not sufficient.
  * Recipes that landed before the current test discipline
    (V14, V15.4 — both pre-SESSION-186-A2) are highest-risk;
    each one validated will likely surface ≥1 bug.

  The SESSION 192 A-arc growth template now needs a
  9th step: **arc-close ceremony must include a real-mode
  validation pass for every recipe affected by the arc**. The
  Asset Library v1 arc-close ceremony at SESSION 193 ran ONE
  composition (talking_head_with_backdrop, mock_mode); A7's role-
  filter behavior across other recipes wasn't validated, and we
  paid for it at SESSION 195 with the concat_clips finding.

### V-arc 100% real-mode closure — first time the full arc is end-to-end-validated against real providers
- **Date:** 2026-05-19
- **Session:** 197
- **Context:** V-arc shipped 16 mock-mode recipes (SESSIONS 142-144)
  + 2 V17/V18 post-close additions; real-mode validation rolled out
  incrementally (SESSION 158 first real-Runway marketing video;
  16/18 by SESSION 184). SESSION 195 attempted to close to 100%
  via real-mode `storyboard_voiced` + `dialogue_scene` — bagged
  2 production bugs (mix_audio silent-base, concat_clips role
  mismatch). SESSION 196 shipped both fixes. SESSION 197 fired
  `storyboard_voiced` real-mode + the new `outro_text` brand
  card to close the arc.
- **Surface / artefact:** Composition `1ce4d201-6640-415e-8bba-796e117dad67`
  — 11 steps end-to-end, 245s wall-time, $1.12 spend (under the
  $1.92 forecast). All 11 steps `succeeded`. Final asset
  `8abd8a1f` carries the "Dog Food Coffee House" brand outro
  card. **First end-to-end real-mode run of any V-arc recipe
  exercising the full storyboard pipeline including the SESSION
  196 mix_audio silent-base fix + the new SESSION 197 outro
  feature.**
- **AI expectation (before):** Storyboard_voiced was the last
  unvalidated V-arc recipe. SESSION 196 fixes addressed both
  SESSION 195 findings; the SESSION 197 fire would either close
  the V-arc or surface a third real-mode bug (per SESSION 195's
  "bugs in every recipe" calibration).
- **Reality / outcome:** **No new bugs.** Both SESSION 196
  fixes (mix_audio silent-base branched filtergraph + concat
  result_role override) held under real-mode load. The outro
  add_intro_outro step worked first-fire. Spend came in under
  forecast. **V-arc is now 18/18 real-mode-validated** — the
  first time the entire V-arc has been end-to-end-validated
  against real Runway + Stability.
- **Found by:** Pre-fire planning identified the SESSION 196 mix
  step as the critical path; real-mode fire confirmed.
- **Lesson:** **The V-arc real-mode validation journey took 5
  sessions of layered work** (SESSION 195 found 2 bugs;
  SESSION 196 fixed both; SESSION 197 added an operator-noticed
  polish + closed). The pattern that worked:
  * Real-mode dogfood surfaces bugs invisible to mock tests.
  * Bugs become next-session fix slices.
  * Operator-noticed UX gaps queue up as same-session polish
    work alongside re-firing.
  * V-arc closure is **not** declared based on mock-mode test
    coverage alone. Real-mode validation is the load-bearing
    gate.

  Same shape generalizes to future arcs (R-arc closed SESSION
  176, A-arc SESSION 193, V-arc SESSION 197).

### Operator-noticed-during-dogfood → next-session ship + re-fire is a high-yield loop
- **Date:** 2026-05-19
- **Session:** 197
- **Context:** During SESSION 195 dogfood, operator noticed the
  storyboard ended cold without any brand mark — flagged it
  in passing as a UX gap. SESSION 197 opened with the operator
  explicitly requesting "Dog Food Coffee House" branding for
  the closure fire. Option A (extend `storyboard_voiced` with
  optional `outro_text` field, mirror `talking_head_polished`
  shape) shipped in ~15 minutes + the closure fire validated
  the new feature first-fire ($1.12, 11/11 steps green).
- **Surface / artefact:** SESSION 197 commits (feat:
  storyboard_voiced outro_text + add_intro_outro append) +
  the closure composition's step 10 succeeded in 760ms.
- **AI expectation (before):** Brand outro asks would typically
  queue as a separate polish slice for "next session." The
  operator's framing ("can you have Dog Food Coffee House
  show up at the end") prompted a check whether this was a
  small enough change to bundle into the closure session.
- **Reality / outcome:** **Bundling the UX polish with the
  closure fire was the right call.** The ~15-min implementation
  + ~5-min real-mode fire (covered by the $1.12 storyboard
  spend that was happening anyway) delivered:
  * V-arc 100% closure (the planned session goal).
  * Branded video deliverable (the operator's same-session ask).
  * Real-mode validation of the new outro feature on first
    fire — no separate validation session needed.
- **Found by:** Operator noticing the UX gap in SESSION 195;
  AI recognizing the bundle opportunity at SESSION 197 open.
- **Lesson:** **When operator-noticed UX gaps surface mid-arc,
  evaluate whether they can ride along with the next
  composition fire.** Criteria for bundling:
  * The feature is small (~30 min implementation) AND
  * It mirrors an existing pattern (here: `talking_head_polished`'s
    outro_text was a 1:1 template) AND
  * The composition fire is already happening for a different
    reason (here: V-arc closure validation).

  When all three are true, bundling avoids a separate
  validation session and delivers operator-visible value in
  the same beat. Same shape as SESSION 194's V18 polish double
  (multiple fixes one session) but operator-noticed instead
  of pre-planned. **Pattern name:** "operator-noticed-during-
  dogfood → next-session ship + re-fire."

### Celery worker doesn't auto-reload — third hit; promote to pre-fire checklist
- **Date:** 2026-05-19
- **Session:** 200
- **Context:** Operator fired storyboard_ad real-mode at 21:48
  immediately after SESSION 200's feature commit landed at
  21:38. Composition `bf155c0a` completed 11/11 steps but the
  concat step's output was 30.25s @ 24fps — the naive sum of
  3 × 10.083s extends with **no crossfade overlap subtracted**,
  despite step.params carrying `crossfade_ms: 500`. Probe of
  the recipe form + step.params + media-engine schema all
  showed the data was correct. The bug was operational: the
  Celery worker (pid 76106) had started at 19:03, 2h35m before
  the feature commit landed. It was running the SESSION 199
  primitive code that didn't know about `crossfade_ms`. Django
  runserver auto-reloaded the new starter (so step.params was
  written correctly); the OLD Celery primitive consumed
  step.params, ignored the unknown `crossfade_ms` key, and
  called the client with the default 0 → endpoint took the
  concat-demuxer fast path.
- **Surface / artefact:** First fire concat output:
  `bdcc695dfa8dbfab.mp4` (30.25s @ 24fps = naive 3 × 10.083s).
  Re-fire after Celery restart: `659f3951...` (29.27s @ 30fps
  = 30.249 − 2×0.5s overlap, framerate normalized by the
  xfade chain). Same inputs, same params, different output —
  the Celery restart was the only change.
- **AI expectation (before):** The TRUST_CALIBRATION entry
  "Celery worker doesn't auto-reload on new primitive
  registrations" exists from SESSION 18B. SESSION 193 added
  "Celery worker is NOT optional for mock_mode" as a hard
  stack-up rule. Neither caught this case because the worker
  was already running and a composition could fire — it just
  fired with stale primitive code that silently produced a
  semantically-different output. **Failure was silent**: 11/11
  steps `succeeded`; only careful ffprobe of the output
  revealed the missing crossfade.
- **Reality / outcome:** Silent semantic regression. Operator
  spent ~$1.62 on a fire whose deliverable had only 2 of 3
  intended features (extend chain ✓, outro ✓, crossfade ✗).
  Re-firing after Celery restart cost another ~$1.62. **Net
  cost of the calibration miss: one wasted real-mode fire.**
- **Found by:** ffprobe of the concat output during dogfood
  triage. Symptom: output framerate was 24fps (Runway source)
  instead of the 30fps the xfade chain normalizes to.
- **Lesson:** **Promote Celery restart from "watch for new
  primitive REGISTRATIONS" to "any feature commit touching ANY
  primitive .py file."** Adding new primitives is the loud
  failure mode (`unknown_primitive` raised). Modifying existing
  primitives is the SILENT failure mode — the worker still
  knows the primitive name + signature, just executes the old
  body. There is no error.

  **Pre-fire checklist addition:** Before any real-mode fire,
  if the last `git log` against `shell/apps/compositions/primitives/`
  is newer than the Celery worker start time, **restart the
  worker first.** Concrete check:
  ```
  CELERY_PID=$(pgrep -f "celery -A character_os" | head -1)
  CELERY_START=$(ps -o lstart= -p $CELERY_PID 2>/dev/null)
  PRIMITIVE_MTIME=$(git log -1 --format=%ai -- shell/apps/compositions/primitives/)
  # If PRIMITIVE_MTIME > CELERY_START: restart Celery
  ```

  Bonus: same rule applies to `shell/apps/compositions/runner.py`,
  `shell/apps/compositions/tasks.py`, and `shell/character_os/clients/media_engine.py`
  (the client library Celery imports). The composition is
  Django+Celery shared code; only Django auto-reloads.

  This is the **third** hit of "Celery doesn't auto-reload" —
  SESSION 18B (new primitive registration), SESSION 193 (worker
  not running), now SESSION 200 (worker running stale code).
  The pattern is robust enough to promote to a pre-fire smoke
  check, not just a calibration to remember.

### Mock-mode test coverage hides upstream stream-shape drift — fourth hit
- **Date:** 2026-05-19
- **Session:** 200
- **Context:** SESSION 198 added `outro_text` to `storyboard_ad`
  with 3 tests, all in mock_mode. The starter test asserted
  the add_intro_outro step lands at position 7 with the right
  inputs + params. All assertions passed. SESSION 200's first
  real-mode fire of storyboard_ad with outro_text hit a 500
  from `/internal/clips/intro_outro/` at step 10:
  `Error binding filtergraph inputs/outputs: Invalid argument`.
  The intro_outro filter graph references `[0:a]` (body
  clip's audio) but storyboard_ad with no narration has a
  silent concat output — `[0:a]` matches no streams. **Same
  shape as the SESSION 196 mix_audio silent-base bug.**
- **Surface / artefact:** Composition `bf155c0a` step 10
  failed with PrimitiveError. Direct curl reproduced the
  500 with body shape: silent concat + outro request.
- **AI expectation (before):** SESSION 198's mock tests passed
  the same shape they always do — verifies step layout, not
  the ffmpeg behavior. AI didn't flag the gap before SESSION
  200 because the SESSION 198 polish triple shipped 3 small
  parity slices and the storyboard_ad path was assumed safe
  given storyboard_voiced (similar shape) was working
  real-mode.
- **Reality / outcome:** storyboard_voiced worked real-mode
  (SESSION 197) BECAUSE its concat output gets mix_audio's
  silent-base fix layered on top — by the time intro_outro
  consumes the mix output, the audio stream exists. storyboard_ad
  has NO mix step. Concat → intro_outro directly. The audio
  invariant intro_outro assumed never held for this shape.
- **Found by:** SESSION 200 real-mode dogfood; operator's
  storyboard_ad fire with use_extend_for_shots=True +
  outro_text="A crazy day in the word".
- **Lesson:** **Stream-shape invariants are sticky bugs that
  only surface when the shape changes.** Generalizes the
  SESSION 196 mix_audio finding:
  * V14/V15.4 mix_audio designed assuming base had audio
    (music_bed shape) → broke on silent storyboard.
  * V9 intro_outro designed assuming base had audio (talking
    head shape) → broke on silent storyboard.
  * Both have the same "presence assumption" failure mode.

  **The fix template is the same**: ffprobe the body, branch
  the filter_complex based on actual stream shape, synthesize
  silent audio when absent. The `_has_audio_stream` helper
  added SESSION 196 is reusable infrastructure.

  **Forward defense**: any ffmpeg endpoint that references
  `[N:a]` from a downloaded clip should ffprobe-detect the
  stream before building the filter. Audit candidates:
  add_captions, composite_video, trim_clip, reformat_clip,
  style_remix — any new endpoint consuming workspace CLIP
  assets without checking audio stream presence is at risk.
  **Mock tests for SESSION 198-style "parity by template"
  polish slices should explicitly real-mode-fire one
  representative once, not solely rely on the template
  precedent.**

### SESSION 200 dogfood — two bugs, one fix, one operational lesson
- **Date:** 2026-05-19
- **Session:** 200
- **Context:** SESSION 200 shipped storyboard extend-chain +
  crossfade end-to-end. Operator dogfooded immediately. Two
  bugs surfaced + a recurring operational trap.
- **Surface / artefact:** Compositions `bf155c0a` (partial →
  retried after fix → completed; $0.85 wasted on the missed
  crossfade due to stale Celery) + `c592dd51` (re-fire after
  both fixes + Celery restart; $1.62, 11/11 green, all three
  SESSION 200 features validated). Final video carries the
  "24/7 Global AI" outro on a 29.27s extend+crossfade concat.
- **AI expectation (before):** SESSION 200 ships were all
  mock-tested. Operator wanted to validate real-mode. Per
  the SESSION 197 calibration "real-mode finds bugs in EVERY
  recipe" — expected at least one bug.
- **Reality / outcome:** **Two bugs in one dogfood pass**:
  intro_outro silent-base (latent since SESSION 198, surfaced
  by SESSION 200's no-narration extend+crossfade pipeline) +
  Celery worker stale (operational; recurring). The
  intro_outro fix mirrored SESSION 196 mix_audio fix exactly;
  shipped same-session with regression tests. The Celery
  restart promoted from advisory to pre-fire-required.
- **Found by:** Operator's real-mode fire of
  storyboard_ad(use_extend_for_shots=True, crossfade_ms=500,
  outro_text="A crazy day in the word") — the
  storyboard_ad real-mode unvalidated state from SESSION 198
  caught up to us.
- **Lesson:** "Real-mode finds bugs in EVERY recipe" continues
  to hold. The pattern is now 4-for-4 across SESSIONS
  195/197/200 dogfoods. **SESSION 200 ships:** 4 slices in
  the feature commit + 1 follow-up fix commit + 1 docs commit.
  Total SESSION 200 spend (this dogfood): ~$2.50. **Pattern
  confirmation:** post-feature real-mode dogfood is
  load-bearing for any feature touching ffmpeg endpoints.

### Forward-defense audits surface latent bugs cheaply
- **Date:** 2026-05-19
- **Session:** 201
- **Context:** SESSION 200 calibration #2 ("mock-mode hides
  upstream stream-shape drift") named 5 ffmpeg endpoints worth
  auditing: add_captions, composite_video, trim_clip,
  reformat_clip, style_remix. SESSION 201 ran the audit + fixed
  what was at risk in advance of any real-mode fire surfacing
  the same shape again.
- **Surface / artefact:** Three endpoints were already safe:
  composite_video (`-map N:a?` optional mapping), add_captions +
  reformat_clip (`-c:a copy` silently no-ops missing audio),
  trim_clip (`-c copy`). `_extend_concat` was already guarded
  by `_has_audio_stream` from V17. Two paths were at risk:
  `_build_reencode_cmd` (concat with reencode=True →
  unconditional `[N:a]aresample`) and `_aleph_split_into_chunks`
  (style_remix segmenter → unconditional `-c:a aac` + `-map 0`).
  Both fixed with the same `_has_audio_stream` helper pattern.
  Five callers of that helper now (mix_audio SESSION 196,
  extend_concat V17, intro_outro SESSION 200, reencode_concat
  SESSION 201, aleph_split SESSION 201).
- **AI expectation (before):** Per SESSION 200 calibration,
  expected at least 1-2 latent bugs in the 5 candidates given
  the shape's recurrence rate (3 confirmed hits across SESSIONS
  196/200/200-post-close).
- **Reality / outcome:** **2 latent bugs in 5 endpoints
  reviewed = 40% hit rate** at zero real-mode spend. Total
  effort ~30 minutes including tests. Mock tests sufficient
  because the failure mode is deterministic (ffmpeg rc=234 on
  the silent-input shape) — no real-provider drift to worry
  about. Media-engine tests 204 → 209 (+5).
- **Found by:** Mechanical grep + read of every `[N:a]` /
  `:a]aresample` / `-c:a` reference in
  `media-engine/app/routers/internal.py`.
- **Lesson:** **When a bug shape repeats, audit every endpoint
  with that shape immediately — don't wait for real-mode to
  hit each one.** The SESSION 200 dogfood pattern ("real-mode
  finds bugs in EVERY recipe") doesn't mean each bug has to
  be found by real-mode. Once the SHAPE is known, a mechanical
  source-code audit is cheaper than the next dogfood fire that
  would surface the same shape.

  **Forward-defense audit template** (codified for future
  recurrence):
  1. Identify the shape (e.g. "unconditional `[N:a]` reference
     on a downloaded clip").
  2. Mechanical grep across the relevant module for the shape.
  3. For each match, classify: already-guarded / safe-by-arg
     (e.g. `-c:a copy`, `-map N:a?`) / at-risk.
  4. Patch at-risk paths with the same helper + branching used
     in the prior fix. Tests cover both the silent path + an
     audio-path regression guard.
  5. Total: ~30 min per shape; cheaper than one wasted
     real-mode fire.

  Run a forward-defense audit after every shape-discovery
  dogfood. SESSION 201 was the first explicit application;
  worth keeping the pattern as a follow-up step on the
  "real-mode finds bugs in every recipe" loop.

### gpt-5 reasoning eats output budget — char-offset math is a recurring trigger
- **Date:** 2026-05-20
- **Session:** 202 (B1.7 dogfood)
- **Context:** B1.1 originally asked gpt-5-mini to return each
  highlight with ``text`` + ``char_start`` + ``char_end`` +
  ``reasoning``. The prompt enforced the offset-math contract
  ("transcript[char_start:char_end] must equal text"). Mock-mode
  tests passed (the mock never exercises the LLM); real-mode
  first fire returned ``output_text=""`` despite consuming 1984
  of 2000 max_output_tokens — the entire output budget burned on
  reasoning about how to count characters, with nothing left for
  the actual JSON.
- **Surface / artefact:** SPA showed "The model ran but found no
  shareable highlights" (the ``used_synthesis=True, picks=[]``
  branch). Direct ``_call_responses_api`` probe confirmed
  ``tokens_out=1984`` + empty ``output_text``. **Same shape as
  the SESSION 171 K6 calibration** — promoting that entry from
  "specific to K6's script synthesis" to "any gpt-5 task asking
  for substring-math-y output."
- **AI expectation (before):** gpt-5-mini at
  ``reasoning_effort="low"`` was assumed cheap enough for a
  5-highlight structured-JSON pick. The mock-mode test coverage
  felt sufficient because the mock was deterministic.
- **Reality / outcome:** **The mock didn't cover the failure
  mode.** Asking the model to do char-counting alongside content
  selection is enough to blow the budget at "low" effort — and
  the failure is silent (empty output, no exception, the
  helper's "degraded to empty result" path looks identical to a
  legitimately uninteresting transcript).
- **Found by:** B1.7 real-mode dogfood + a direct
  ``_call_responses_api`` probe with DEBUG logging.
- **Lesson:** **Architectural fix beats budget bumps for
  substring-math-y LLM tasks.** Two options when the model needs
  to "locate" a substring in a larger body:

  * **Bad option**: ask the LLM for offsets directly. Even at
    "low" effort, gpt-5 burns reasoning tokens computing them
    and silently blows the output budget.
  * **Good option**: ask the LLM for the verbatim text only.
    Locate offsets server-side via ``body.find(text)``. The LLM
    job becomes pure pattern-matching; the parser does the math.

  B1.7 shipped option 2. Token usage dropped from 0/1984 to
  459/658 on the same task. Verified real-mode on a 913-char
  transcript: 3 picks, all valid offsets, $0.001 spend.

  **Forward defense**: any future Responses-API caller that
  needs to identify a substring of a longer body should follow
  the "ask for text, locate via find() in the parser" pattern.
  Audit candidates: K6.4 verification (if it ever computes
  citation spans), F6 lineage extractors, any future
  segment-selection pipeline.

  Also: **add a real-mode smoke test for any new gpt-5 caller**.
  Mock-mode tests verify the parser; only real-mode catches the
  reasoning-budget burn. The B1.1 unit tests were comprehensive
  (21 of them) and missed this entirely.

### B-arc landed in a single session — scope-lock pattern is paying off
- **Date:** 2026-05-20
- **Session:** 202
- **Context:** B-1 Transcript Miner — first strategic-axis arc
  after the V-arc UX polish + Asset Library + forward-defense
  audit close-out. Scope-locked at B1.0 (8 contract rules, 7
  slices) and shipped B1.0 through B1.7 in one extended session
  including real-mode dogfood validation.
- **Surface / artefact:** Composition
  ``b4ab9ea6-60b5-4478-85c8-df75595b9ed8`` — Marcus saying
  "They saw it as a necessary act to save the Republic." (the
  52-char highlight the operator approved). $0.25 spend, 19.3s
  wall-time, 1/1 step succeeded. The completion signal
  (load-bearing test of B1.4) flipped highlight status
  APPROVED → RENDERED automatically.
- **AI expectation (before):** Per the SESSION 195 calibration
  ("real-mode finds bugs in EVERY recipe"), at least one bug
  expected during B1.7 dogfood. The B1.7 fix DID surface the
  gpt-5 offset-math bug — but it surfaced cleanly via the
  "empty result" path, not via crash or data corruption.
- **Reality / outcome:** **Single-bug arc.** The
  reasoning-budget burn was the only real-mode finding. Once
  the helper was refactored (B1.7 fix), the entire pipeline ran
  first-try end-to-end: spokesperson reverse-FK lookup worked,
  starter created the right composition shape, execute_composition
  ran, post_save signal fired correctly. The most architecturally
  brittle piece — the completion signal flipping APPROVED →
  RENDERED via a cross-app post_save hook — worked without
  incident.
- **Found by:** Operator UI-driven dogfood of the longest Marcus
  transcript (913 chars, Caesar assassination conversation).
- **Lesson:** **The scope-lock pattern paid for itself again.**
  Eight contract rules + seven sequenced slices + per-slice
  test coverage produced a one-session arc with one surface bug.
  Same shape as the A-arc (Asset Library, SESSIONS 185-192) and
  the R-arc closing fires — careful upfront scoping compresses
  the build phase.

  Also confirmed: **real-mode dogfood is still load-bearing**.
  B-1 had 67 tests across the backend (B1.1 + B1.2 + B1.3 + B1.4)
  + 54 SPA tests (B1.5 + B1.6). Every test passed. Real-mode
  still found a bug the test surface couldn't see (the
  reasoning-budget burn). Mock tests verify the contract; only
  real-mode verifies the provider's interpretation of the
  contract.

  The strategic moat thesis from CONTENT_FORMAT_BACKLOG.md §B-1
  is now demonstrable: per-workspace realtime avatar →
  per-workspace transcripts → per-workspace highlight clips.
  No LLM-video competitor has the same data to mine. Marcus
  saying the Republic quote is structurally unique to this
  stack.

### C-arc landed in one session — scope-lock cadence is now 3-for-3
- **Date:** 2026-05-20
- **Session:** 203
- **Context:** B-3 Personalized Video — second strategic-axis
  arc after the B-1 close. Scope-locked at B3.0 (9 contract
  rules, 10 slices) and shipped B3.0 through B3.9 in one
  extended session including real-mode dogfood validation.
  Same shape as the B-arc (SESSION 202) and the A-arc
  (SESSIONS 185-192).
- **Surface / artefact:** Campaign "B-3 smoke test"
  (workspace admin/spokesperson Marcus). Fan-out of 2
  recipients in one transaction; both compositions completed
  in parallel; campaign auto-rolled up via B3.6's post_save
  signal. $0.50 total spend, 36.2s wall-time. Final assets
  ``463374ed`` + ``ed9e2bd6`` — Marcus saying "Hi Bob, hope
  your day at Acme is going well!" + the Carol/Initech
  variant.
- **AI expectation (before):** Per the SESSION 202 calibration
  ("real-mode finds bugs in EVERY recipe"), at least one bug
  expected during B3.9 dogfood. B-arc shipped clean
  end-to-end; C-arc had more surface (10 slices vs 7), more
  cross-app coupling (campaigns → compositions signal +
  retry path), and a new tier-gate dimension.
- **Reality / outcome:** **One bug surfaced — and only at the
  SPA layer.** The backend (B3.0–B3.6) ran cleanly first
  fire. B3.8's `useParseCsv` mutation didn't invalidate the
  `campaign-forecast` query, leaving the operator with a
  stuck "0 recipients $0.00 total" forecast despite
  recipients persisting server-side. The fix was one line in
  the React Query cache-invalidation set; the backend
  contract was correct end-to-end.
- **Found by:** Operator UI-driven dogfood — pasted CSV,
  forecast panel didn't update. Backend DB query confirmed
  recipients were there; SPA debugging found the missing
  cache key.
- **Lesson:** **Scope-lock cadence is now proven 3-for-3**
  across the A-arc (Asset Library), B-arc (Transcript Miner),
  and C-arc (Personalized Video). Each landed in one extended
  session with a clean real-mode dogfood. The pattern that
  works:
  * 8-10 contract rules locked before code lands.
  * 7-10 sequenced slices, each with per-slice tests.
  * SPA slices delegated to react-web-delivery subagents
    when the backend is already feature-complete.
  * Real-mode dogfood as the closing slice.

  This compounds: subsequent arcs get cheaper because the
  pattern is internalized. Future strategic axes
  (B-14 multi-platform variants, B-1 v2 external transcripts,
  etc.) should plan around the same shape: ½-1 session per
  slice, 6-10 sessions total, scope-lock-first.

### React Query mutation onSuccess must invalidate EVERY dependent query
- **Date:** 2026-05-20
- **Session:** 203
- **Context:** B3.8's `useParseCsv` mutation invalidated
  `["campaign-recipients", id]` and `["campaign", id]` on
  success. The forecast endpoint (separate query key
  `["campaign-forecast", id]`) reads ``campaign.recipients.count()``
  server-side, so its result depends on the recipient list.
  But the mutation didn't invalidate the forecast key —
  React Query kept serving the stale "0 recipients" result.
- **Surface / artefact:** B3.9 dogfood — operator pasted 2
  recipients, forecast panel showed "0 recipients $0.00
  total" and Launch button stayed disabled. DB had the
  recipients; backend GET /forecast/ would have returned
  the correct payload; SPA never re-fetched.
- **AI expectation (before):** The subagent was briefed to
  "invalidate appropriate query keys on mutation success."
  The B-arc subagents got this right because the data shapes
  were simpler (B1.4's approve mutation only had one
  dependent query). C-arc has more inter-query dependencies
  — the forecast depends on the recipient list.
- **Reality / outcome:** Subagent invalidated 2 of the 3
  dependent queries. The miss was structural: the
  ``forecast`` query key wasn't introduced until B3.8 (after
  ``useParseCsv`` was already written in B3.7), so when the
  forecast hook landed nobody backfilled the parse mutation's
  invalidation list. Tests didn't catch it because they
  mocked the API responses directly — no actual cache
  behavior under test.
- **Found by:** Operator dogfood. The DB-level probe was the
  one that pointed at "data exists; SPA isn't seeing it" as
  the diagnosis path.
- **Lesson:** **When a new query depends on a mutation's
  output, audit every existing mutation that affects the
  same underlying data and add the new key to its
  invalidation set.** This is the React Query equivalent of
  the SESSION 200 "forward-defense audit" pattern: when a
  data dependency surfaces, sweep the codebase for callers
  that already write to that data and might need to bust the
  new cache.

  **Forward defense template** for this shape:
  1. New query introduced (e.g. ``useCampaignForecast``).
  2. Grep ``invalidateQueries`` for mutations that affect
     the data the new query reads.
  3. Add the new query key to each one's onSuccess
     invalidation list.
  4. Add at least one test that asserts the mutation
     invalidates the new key (mock both queries; fire
     mutation; assert the second query refetches).

  Step 4 wasn't done for B3.8's forecast hook; that's why
  the bug shipped to dogfood. Worth adding to the
  subagent briefing template for future SPA slices that
  introduce new dependent queries.

### Tier-gated batch caps work as designed — operator validation pre-launch
- **Date:** 2026-05-20
- **Session:** 203
- **Context:** B-3 rule 4 (TWO tier dimensions — per-batch
  cap + per-month videos cap) was a design choice during the
  scope lock. The reasoning was operator-protective: one
  accidental click on a 50-row CSV at Starter tier could
  blow through ⅔ of the monthly quota in one fire.
- **Surface / artefact:** B3.9 dogfood with 2 recipients;
  forecast showed "batch cap: 5 • 8 videos left this month"
  — both gates passed cleanly, Launch enabled. Tests cover
  the over-cap branches (test_launch_over_batch_cap_returns_402
  + test_launch_over_month_cap_returns_402); the dogfood
  exercised the under-cap path.
- **AI expectation (before):** Two-dimension gating felt like
  scope creep at lock time. The simpler design was
  "videos_per_month is the only gate." Operator-protective
  framing prevailed because runaway-batch risk is real for
  B2B sales flows (~$50 batch easy to fat-finger as $500).
- **Reality / outcome:** The two-gate design pays off in the
  forecast modal: operator sees both numbers before
  committing. "batch cap: 5" makes the upper limit visible
  per-batch; "8 videos left this month" makes the cumulative
  remaining visible. Together the operator gets the
  what-can-I-do-RIGHT-now and the what-can-I-do-THIS-MONTH
  signals.
- **Found by:** N/A — design choice that paid off as planned.
- **Lesson:** **Operator-protective gates show their value in
  the surface that displays them, not in the code that
  enforces them.** The cost-forecast modal is the
  load-bearing piece: an operator pasting a 50-row CSV sees
  "batch cap: 5 — would exceed by 45" inline with
  "personalized_batch_too_large" before they click Launch.
  This is the moment the gate's design choice matters.

  Generalizes: any new gate or limit should land with a
  forecast / preview surface that shows the operator the
  current usage AND the limit AND the projected outcome
  before they commit. The R9 cost-ticker pattern, the V18
  duration-mismatch starter warning, and now B-3's forecast
  modal all follow this shape.

### videos_per_month was reading the wrong table
- **Date:** 2026-05-20
- **Session:** 204
- **Context:** B3.5 dogfood (SESSION 203) surfaced a latent
  architectural seam: ``apps.billing.services.get_usage()``
  counted Video shim rows for ``videos_used``, but the V-arc
  (V1-V18), B-arc (transcripts), and C-arc (campaigns) all
  create Compositions directly — bypassing the V6
  backwards-compat shim entirely. The per-month cap was
  effectively disabled for everything except the few
  remaining legacy single-form callers.
- **Surface / artefact:** Dev workspace probe before fix:
  ``videos_used=2`` (counting the 2 legacy Video rows in
  period). Actual work done in period: 72 Compositions.
  Operator at Starter (cap=10) thought they had 8 left;
  reality was 62 OVER.
- **AI expectation (before):** B3.5 punted the migration to
  a follow-up slice and seeded the test against the Video
  shim to validate gate logic without fixing the seam.
  Documented as "architectural debt surfaced" in the
  SESSION 203 close.
- **Reality / outcome:** **Migration was a single-function
  change + test sweep.** Replaced the ``Video.objects.filter
  (...)`` query in ``get_usage`` with
  ``Composition.objects.filter(...).exclude(status=DRAFT)``.
  Updated three test sites that seeded Video rows to
  exercise the cap: ``apps.campaigns.tests.test_launch``
  (2 tests) and ``apps.realtime.tests.test_r7_2_async_tools``
  (1 test). Added ``apps.billing.test_services`` (8 tests)
  pinning the new include/exclude semantics. Real-mode probe
  confirmed: ``videos_used`` jumped from 2 to 72 on the
  dev DB.
- **Found by:** B3.5 dogfood explicitly. The test author
  (me, at B3.5) seeded Video shim rows but noted it was a
  workaround — see the ``test_check_personalized_batch_under_batch_but_over_month_raises``
  docstring at SESSION 203 close.
- **Lesson:** **Note architectural debt when you see it AND
  fix it before the next arc compounds.** SESSION 203
  close-out explicitly suggested SESSION 204 take the
  cleanup before opening B-14. Operator agreed. Total cost:
  one function edit + 9 affected tests + 8 new tests. The
  alternative — pushing through to B-14 — would have made
  the per-month cap math denser (one CSV row → 4 platform
  variants), which would have made the bug harder to
  unwind cleanly later.

  **General pattern**: when a slice surfaces architectural
  debt that's both fixable in ~1 session AND would compound
  with the next planned arc, doing the cleanup first beats
  pushing forward. The "tidy the house" beat between
  strategic arcs pays compound interest.

### Scope-lock cadence is now 4-for-4 — proven across A/B/C/D arcs
- **Date:** 2026-05-20
- **Session:** 205
- **Context:** B-14 Publish Bundle (D-arc) — fourth
  strategic-axis arc opened after Asset Library (A,
  SESSIONS 185-192), Transcript Miner (B-1, SESSION 202),
  and Personalized Video (B-3, SESSION 203). Scope-locked
  at B14.0 (8 contract rules, 7 slices) and shipped B14.0
  through B14.5 in one extended session.
- **Surface / artefact:** Two bundles shipped end-to-end:
  TikTok variant 1.5s ffmpeg wall-time, $0 cost;
  LinkedIn variant same. Both cross-app post_save signal
  flipped variants + rolled up bundles automatically.
- **AI expectation (before):** Per the SESSION 203
  "cadence 3-for-3" calibration, expected one extended
  session. D-arc was smaller scope than C-arc (7 vs 10
  slices; no LLM, no CSV, no template engine).
- **Reality / outcome:** **One extended session; one
  operator-noticed UX limitation (not a bug); zero
  real-mode spend; zero backend regressions.** Pattern
  now 4-for-4. Scope-lock-first discipline compresses
  arc cycles reliably; mid-arc surprises are exceptions.
- **Found by:** D-arc shipping in one day after operator's
  "Lock and open B14.1" decision.
- **Lesson:** Cadence is now load-bearing assumption, not
  aspirational. Strategic arcs ship in 4-10 hours of
  focused work + one dogfood pass. Future arcs (B-2,
  B-1 v2, etc.) should plan around the same shape.

### Aspect-changing crop is a recurring shape — flag pattern + v2 fix
- **Date:** 2026-05-20
- **Session:** 205 (B14.5 dogfood)
- **Context:** Operator fired a B-14 TikTok variant against
  a 16:9 storyboard source. The pipeline ran correctly —
  ``reformat_clip`` scaled + center-cropped to 720×1280 as
  designed. **Output visibly off-center**: source had
  coffee maker on the left of frame + off-center person;
  center-cropping to 9:16 chopped 56% of the horizontal
  frame and lost both subjects.
- **Surface / artefact:** Bundle 89a98aa8 / final asset
  f7586e66. Operator-visible quality issue but
  contract-correct render.
- **AI expectation (before):** B-14 v1 assumed centered
  subjects (Runway avatar talking-head outputs centered by
  default). Cinematic / storyboard sources with
  intentional off-center composition weren't in the v1
  mental model.
- **Reality / outcome:** **The contract held but v1 UX
  hits a quality wall on aspect-changing variants against
  off-center sources.** Avatar bundles work perfectly.
  Cinematic storyboard / scene-composition bundles need
  a way to nudge the crop window.
- **Found by:** Operator real-mode dogfood. Bundle #2
  (LinkedIn at 1280:720, same source) was confirmed
  perfect — only aspect-changing variants
  (Reels/Shorts/TikTok at 9:16) have this problem.
- **Lesson:** **Aspect-changing crop is a recurring shape
  worth a separate v2 axis.** B-14 v1 documents the
  limitation; the v2 fix is well-scoped:

  * Per-variant ``offset_x`` knob on PublishVariant
    (-100 to +100; 0=center, -100=left, +100=right).
  * SPA picker exposes the knob with a crop-window preview.
  * ffmpeg pipeline: parameterize crop position with a
    formula like ``(in_w-out_w)*(50+offset_x)/100``.

  Estimated ½ session. **Pattern**: when a primitive's
  v1 default (center-crop) hits operator UX walls on a
  specific source shape (off-center cinematic), the right
  axis is *parameterize the default*, not *replace the
  primitive*. Same shape as V18's duration-mismatch
  starter warning (parameterize the V8 check, not rewrite
  composite_video).

  Audit candidates for the same pattern when cinematic
  sources arrive: composite_video's pip position,
  intro_outro card placement, music_bed_pass gain math.
  Avatar-only workflows have masked these assumptions
  to date.

### Scope-lock cadence is now 5-for-5
- **Date:** 2026-05-20
- **Session:** 206 (B-2 / E-arc, lock + 5 of 7 slices)
- **Context:** Five consecutive strategic-axis arcs
  (A SESSIONS 185-192, B SESSION 202, C SESSION 203,
  D SESSION 205, E SESSION 206) have opened + landed
  their implementation slices in single-session blocks.
- **AI expectation (before):** SESSION 205 close-out
  noted the cadence as "proven 4-for-4" with a load-
  bearing assumption that future strategic axes would
  hold the same shape. SESSION 206 was the cleanest
  test: a five-slice arc that lifts an existing
  operational pipeline (K6 synthesis) into a new
  persistence layer with its own REST + SPA surfaces.
- **Reality / outcome:** **Cadence held.** Scope lock
  (B2.0) → model (B2.1) → synthesis adapter (B2.2) →
  REST + tier gate + starter (B2.3) → recipe gallery
  (B2.4) → SPA via subagent (B2.5). Six commits;
  Django 1269 → 1320 (+51); SPA vitest 371 → 405
  (+34); zero K6 regressions; $0 real-mode spend.
  Operator pulled B2.6 (dogfood) to a fresh session
  to avoid same-day fatigue on real-mode validation —
  prior arcs all left the dogfood to its own block too,
  so this is the established sub-pattern.
- **Found by:** Six committed slices; full Django suite
  passing after each.
- **Lesson:** **The cadence is no longer aspirational —
  it's the design default for any new strategic axis.**
  Plan around: 8-10 contract rules + 7-10 slices
  (¼ to 1 session each) + real-mode dogfood closing.
  The dogfood is fine to ride into the next session
  when same-day fatigue would degrade real-mode
  validation quality (operator's judgment call). What
  this enables: when an operator says "let's start
  with B-X" on a Tuesday, the AI can confidently
  scope an arc that closes the same Tuesday — modulo
  the dogfood ride-over.

### K6 refactor via adapter pattern preserved zero regressions
- **Date:** 2026-05-20
- **Session:** 206 (B-2 / E-arc, B2.2)
- **Context:** B-2's central technical question was
  "how do we add pre-render Script-row persistence
  without breaking K6's in-primitive synthesis?" K6's
  ``character_os.script_synthesis.build_render_brief``
  has many callers — the legacy V6 shim in
  ``apps.videos.views``, the ``generate_avatar_speech``
  primitive, two large existing test files
  (``test_script_synthesis.py``,
  ``test_claim_verifier.py``), and a mock-patch site in
  ``test_primitive_avatar_speech.py`` that pins the
  exact import path.
- **AI expectation (before):** The two viable shapes
  were *move-and-shim* (move the implementation to the
  new module, leave a thin back-compat re-export at the
  old path) and *adapter-wraps-callable* (add a new
  module that calls the existing function and remaps
  the result shape).
- **Reality / outcome:** **Chose adapter-wraps-callable.
  Result: 1320 Django tests pass with zero K6
  regression.** The new ``apps.scripts.synthesis.draft_script``
  invokes ``build_render_brief`` and remaps the
  ScriptResult fields onto a ScriptDraftResult shape.
  Strict-mode ``ClaimVerifierError`` is caught at the
  adapter layer and persisted as
  ``verification_status='blocked'`` instead of raising
  into the caller. Both paths share the underlying
  machinery via call, not via shared mutable state.
- **Found by:** Full Django suite after B2.2 commit
  (1290 passed, no failures); the K6 mock-patch site
  at ``test_primitive_avatar_speech.py:378`` was the
  load-bearing test that confirmed the legacy import
  path was preserved.
- **Lesson:** **When adding a new persistence layer
  over an existing operational function with many
  callers + a mock-patch test fixture, the
  adapter-wraps-callable shape is strictly safer than
  move-and-shim.** Move-and-shim invites import-path
  drift across the test surface; adapter-wraps-callable
  preserves the original call graph by construction.
  Generalizes to similar future refactors: when the
  motivation is "new feature on top of existing
  function," not "consolidate two equivalent paths
  into one," reach for the adapter pattern first.
