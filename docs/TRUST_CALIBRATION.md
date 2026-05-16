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
