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
