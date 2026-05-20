---
title: "Session 203 — C-arc Personalized Video shipped + real-mode validated"
date: 2026-05-20
status: complete
session: 203
previous_handoff: ./SESSION_202_B_ARC_LANDS.md
---

# Session 203 — B-3 Personalized Video arc landed end-to-end

## TL;DR

Third strategic-axis arc in three consecutive sessions. The
scope-lock cadence (A-arc SESSIONS 185–192 → B-arc SESSION 202
→ C-arc SESSION 203) is now proven 3-for-3: 8-10 contract
rules + 7-10 slices + real-mode dogfood closing all land in
one extended session.

**B-3 Personalized Video shipped all ten slices** (B3.0 scope
lock through B3.9 real-mode dogfood). Operator can write a
script template with `{variable}` placeholders, paste a CSV of
recipients, see a tier-gated cost forecast, launch a batch
of N talking_head_polished compositions, watch progress live
via 5s polling, and retry FAILED recipients individually. The
structural moat: per-workspace avatars are necessary to render
personalized B2B videos at scale — competitors with generic
LLM video can't deliver "Hi {firstName}, saw {company}…" with
on-brand spokesperson identity.

Total spend: **$0.50** (B3.9 dogfood — 2 recipients, $0.25
each, exactly the B-arc baseline). Tests at close: Django
**1207**, SPA vitest **284**, media-engine **214**.

## What landed

Ten slices across the day:

### B3.0 — scope lock (`docs/design/PERSONALIZED_VIDEO_V1.md`)

Nine contract rules + ten implementation slices. All nine
open questions resolved with proposed defaults; operator
accepted as-proposed.

### B3.1 — `template_renderer` helper (`character_os/template_renderer.py`)

`parse_placeholders()` + `render_template()` + typed
`TemplateError(kind="syntax"|"missing")`. Doubled-brace
escape per Q-c-7. Rejects positional / attribute / index /
format-spec shapes — bare `{name}` only for clean 1:1 CSV
mapping. 24 tests.

### B3.2 — `PersonalizedCampaign` + `PersonalizedRecipient` models

New `apps.campaigns` Django app. 6-state campaign machine + 5-
state recipient machine. Cross-workspace guard at 2 layers
(`clean()` + `pre_save` signal). Q-c-1 TIER_LIMITS extended
with `personalized_batch_max`: Starter=5, Pro=30, Agency=200.
11 tests; migration 0001.

### B3.3 — CSV parser (`character_os/csv_recipients.py`)

`parse_csv()` + `derive_label()`. Three result states:
header_error (top-level reject), valid_rows + rejected_rows
(happy path), header-only (valid but empty). Handles
operator-paste quirks: BOM, quoted commas, whitespace rows,
short/long rows, trailing blanks. 20 tests.

### B3.4 — `CampaignViewSet` read + draft-edit surface

REST endpoints at `/api/campaigns/`: create / list / retrieve
/ destroy / parse_csv (REPLACE semantics, DRAFT-only) /
recipients sub-list. Q-c-9 delete behavior: DRAFT/terminal
cascade; LAUNCHING/IN_FLIGHT refuses (409). 20 tests.

### B3.5 — `forecast` + `launch` actions (load-bearing slice)

`GET /forecast/` returns structured payload with
`ready_to_launch` + `blocking_reason` (codes:
`no_recipients`, `campaign_not_draft`,
`personalized_batch_too_large`, `video_limit_reached`).

`POST /launch/` runs both tier gates (rule 4 — per-batch cap
+ per-month videos cap), atomically fans out N
`talking_head_polished` compositions, enqueues Celery after
commit. Per-recipient render failures flip that row to FAILED
with the TemplateError message (rule 8). All-fail short-
circuits campaign to FAILED. 19 tests.

### B3.6 — completion signal + per-recipient retry

Cross-app `post_save` receiver on Composition: terminal
status flips the linked recipient + rolls up the campaign
status via `rollup_campaign_status` helper.
`POST /retry_recipient/` creates a NEW composition (failed
one stays for audit per Q-c-6), re-flips campaign to
IN_FLIGHT from any terminal state. 16 tests.

### B3.7 — SPA list + create + paste-CSV (subagent)

Three new routes: `/workspace/campaigns` (list with status
filter chips), `/workspace/campaigns/new` (create form with
live placeholder detection), `/workspace/campaigns/<id>`
(minimal detail with CSV paste). `web/src/lib/api/campaigns.ts`
with 6 hooks. Subagent (react-web-delivery). +56 vitest tests.

### B3.8 — SPA launch + forecast + recipient grid + retry +
polling (subagent)

Layered four new panels onto B3.7's detail route, gated by
campaign.status:

* **ForecastPanel** — cost preview, batch_cap, videos
  remaining, ready_to_launch indicator + structured
  `blocking_reason` rendering.
* **LaunchModal** — inline fixed-position overlay (no Radix
  dep), Cancel + "Yes, launch" actions.
* **RecipientGrid** — color-coded status badges, label,
  variables preview, composition link, inline error_message.
* **TerminalBanner** — summary banner for COMPLETED /
  PARTIAL / FAILED; "Browse produced assets" link.

5s `refetchInterval` while LAUNCHING/IN_FLIGHT; stops
automatically at terminal status. 402 tier errors surfaced
via structured `payload.message`. Subagent. +40 vitest tests.

### B3.9 — real-mode dogfood + arc close

Campaign "B-3 smoke test" against Marcus + 2 recipients
(Bob @ Acme, Carol @ Initech). Both compositions completed in
parallel; campaign auto-rolled up to COMPLETED via B3.6
signal. Total: 36.2s wall-time, **$0.50 spend**.

### B3.8 post-close hotfix (`ffabde1`)

Dogfood found that `useParseCsv` didn't invalidate the
`campaign-forecast` query on success. Operator pasted a CSV,
recipients persisted server-side, but the forecast panel
kept showing "0 recipients $0.00 total" — Launch button
stuck disabled. One-line fix; new calibration entry
documents the "every dependent query must be invalidated"
pattern.

## Real-mode validation

Campaign `158dbe3f-...` ("B-3 smoke test"):

- **status: completed** ✓
- 36.2s wall-time, **$0.50 spend** (2 × $0.25)
- 2 recipients, both COMPLETED
- Recipient labels: Bob, Carol (Q-c-5 derivation: first_name → label)
- Final assets `463374ed` + `ed9e2bd6` (TALKING_HEAD role)
- Composition names: "B-3 smoke test — Bob" + "B-3 smoke test — Carol" (rule 9 provenance)
- **B3.6 completion signal fired correctly** for both recipients; campaign auto-rolled up to COMPLETED with `completed_at` set

## Tests at session close

| Suite | Count | Delta vs SESSION 202 close |
|---|---|---|
| Django | **1207** | +110 (1097 → 1207) |
| - campaigns (new) | **66** | new app (11 model + 20 API + 19 launch + 16 completion) |
| - character_os.test_template_renderer | **24** | new |
| - character_os.test_csv_recipients | **20** | new |
| Media-engine | 214 | unchanged |
| SPA vitest | **284** | +96 (188 → 284) |

`pnpm build` clean. Real-mode spend: **$0.50**.

## Calibration moments worth carrying

**Three new TRUST_CALIBRATION entries (34 total)**:

1. **C-arc landed in one session — scope-lock cadence is now
   3-for-3.** Same shape as A-arc (SESSIONS 185-192) and
   B-arc (SESSION 202). 9 contract rules + 10 slices + one
   bug + same-session fix. Future strategic axes (B-14, B-1
   v2) should plan around the same shape: ½-1 session per
   slice, 6-10 sessions total, scope-lock-first.

2. **React Query mutation onSuccess must invalidate EVERY
   dependent query.** B3.8 added `campaign-forecast` as a
   new query key after B3.7's `useParseCsv` was already
   written; nobody backfilled the parse mutation's
   invalidation list. The forecast depends on the recipient
   list server-side, but React Query had no way to know
   that. Forward-defense template added: when a new query
   depends on a mutation's output, grep
   `invalidateQueries` for mutations that affect the same
   underlying data and add the new key. Add at least one
   test asserting the new invalidation.

3. **Tier-gated batch caps work as designed — operator
   validation pre-launch.** Rule 4's two-dimension gating
   (per-batch + per-month) pays off in the forecast modal:
   operator sees "batch cap: 5 • 8 videos left this month"
   inline before clicking Launch. Generalizes: any new gate
   should land with a forecast / preview surface. Same
   pattern as R9's cost-ticker + V18's duration-mismatch
   warning + now B-3's forecast modal.

## What's still queued

V2 candidates explicitly out of scope for B-3 v1 (from the
scope-lock):

* File upload for CSV (paste-only v1)
* CRM webhook integration
* Email validation / format checking
* Email send / SMS delivery
* Per-recipient analytics
* Template versioning
* A/B variants (separate B-18 axis)
* Per-platform fan-out (compose with B-14 in v2)
* Live preview of substituted script

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions) — operator-content
  bottleneck; unblocks B-1 v2 external transcript ingestion.
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).
* **B-14 Multi-Platform Variants** — next strategic-axis
  candidate.
* **B-1 v2 slices** — external transcripts, batch mining,
  highlight chaining.

### Architectural debt surfaced (not in scope for this arc)

* `videos_per_month` cap reads from the legacy V6 `Video`
  shim, not from Composition rows. Test seeded against
  Video.objects to validate the gate logic correctly. The
  structural fix — making `get_usage()` count Composition
  rows — is a separate slice and was deferred at B3.5.
  Worth a follow-up when an operator complains "I rendered
  10 videos via the C-arc but the meter only shows 0".

### Recommended next direction

Three consecutive strategic-axis arcs landed cleanly. The
backlog now splits between:

1. **B-14 Multi-Platform Variants** — next strategic axis
   (composes with B-3 and B-1 in v2; ~5-6 slices).
2. **Asset upload UI** — operator-content bottleneck; needed
   for B-1 v2 external transcript ingestion.
3. **Architectural debt cleanup** — `videos_per_month` count
   migration (B3.5 finding); W12 legacy form retirement;
   K6.4 v3.

## Operational notes for the next session

* Dev DB now has 1 COMPLETED campaign + 2 COMPLETED
  recipients from the dogfood. Browseable via
  `/workspace/campaigns`.
* Marcus's avatar produced two new TALKING_HEAD assets
  (`463374ed`, `ed9e2bd6`) — visible in `/workspace/assets`.
* `apps.campaigns` carries 66 backend tests + 96 SPA tests;
  the cross-app post_save signal makes the test_isolation
  allowlist load-bearing for future test files in the app.
* Pre-fire check (SESSION 200) still load-bearing — Celery
  worker must be newer than any commit touching
  `apps/campaigns/signals.py` or
  `apps/compositions/primitives/`.
