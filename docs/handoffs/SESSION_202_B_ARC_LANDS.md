---
title: "Session 202 — B-arc Transcript Miner shipped + real-mode validated"
date: 2026-05-20
status: complete
session: 202
previous_handoff: ./SESSION_201_FORWARD_DEFENSE_AUDIT.md
---

# Session 202 — B-1 Transcript Miner arc landed end-to-end

## TL;DR

First strategic-axis arc after the V-arc + Asset Library +
forward-defense audit close-out. **B-1 Transcript Miner shipped
all eight slices in one extended session** (B1.0 scope-lock
through B1.7 real-mode dogfood). The structural moat thesis
holds: per-workspace realtime avatar → per-workspace transcripts
→ per-workspace highlight clips. Marcus saying
"They saw it as a necessary act to save the Republic." is now a
standalone shareable Asset in the dev workspace, mined from a
prior R-arc conversation about the Caesar assassination.

Total spend: **$0.25** (one full approve-to-render cycle plus
~$0.003 in cumulative LLM calls). Tests at close: Django
**1097**, SPA vitest **188**, media-engine **209**.

## What landed

Eight slices across the day:

### B1.0 — scope lock (`docs/design/TRANSCRIPT_MINER_V1.md`)

Eight contract rules + seven implementation slices. Operator
signed off as-proposed; all eight open questions resolved with
proposed defaults.

### B1.1 — LLM helper (`character_os/transcript_miner.py`)

`select_transcript_highlights(body, *, target_count, max_chars)
-> MiningResult`. gpt-5-mini Responses API, force-mock flag
(seventh in the family), graceful degradation on missing key /
LLM failure. 20 unit tests.

### B1.2 — `TranscriptHighlight` model (`apps.transcripts`)

New Django app. Four-state machine (PENDING / APPROVED /
REJECTED / RENDERED). Three-layer cross-workspace guard:
`clean()` + `pre_save` signal + DB `CheckConstraint`. 12 tests.

### B1.3 — REST mine + list + retrieve

`TranscriptHighlightViewSet` at `/api/transcript_highlights/`.
Workspace isolation at three layers: `get_queryset()` scoping,
`IsWorkspaceMember` permission, explicit membership check in
the mine handler. Q-b-5 cost-telemetry shape: first row holds
the LLM call cost, others zero. 13 tests.

### B1.4 — approve / reject + completion signal

Two viewset actions + a cross-app `post_save` receiver on
Composition. Approve fires `talking_head_polished` via the
recipe registry; the receiver flips APPROVED → RENDERED on
composition completion. Spokesperson resolved via reverse-FK
from `RealtimeSession.transcript_asset` (Q-b-7). 13 tests.

### B1.5 — SPA list + mining trigger (subagent)

`/workspace/transcripts` + `/workspace/transcripts/:id`. The
detail route includes the Mine button + optional knobs
(target_count, max_chars). Read-only highlight list with
status badges. Subagent (react-web-delivery). +30 vitest tests.

### B1.6 — SPA approval UX (subagent)

Per-row Approve / Reject buttons, inline rejection-reason
textarea, composition link on APPROVED/RENDERED rows, LLM
reasoning always visible (rule 3). Char-range hover-highlight
on the transcript body via string-slicing (`pre + <mark>matched
</mark> + post`) — no DOM ranges, preserves `<pre>` whitespace.
Subagent. +24 vitest tests.

### B1.7 — real-mode dogfood + contract reshape

Dogfood surfaced the recurring "gpt-5 reasoning eats output
budget" pattern. The original prompt asked gpt-5-mini to return
each highlight with `text` + `char_start` + `char_end` +
`reasoning`. At `reasoning_effort="low"` the model burned 1984
of 2000 max_output_tokens computing char offsets, then emitted
zero visible output. SPA showed "model ran but found no
shareable highlights."

**Architectural fix** (committed `d69d291`): drop char-offset
math from the LLM contract entirely. The model returns text +
reasoning only; the parser locates each quote via
`body.find(text)`. Hallucinated quotes (not in source) → drop.
Multiple occurrences → first wins (v1 simplification). Rule 3
audit shape preserved end-to-end; the LLM's job is now pure
pattern-matching.

Real-mode verification on a 913-char Marcus transcript:
3 picks returned, all valid offsets, 459 tokens in / 658 out
(under budget by ~3x).

Approved one highlight → composition
`b4ab9ea6-60b5-4478-85c8-df75595b9ed8`:
- **status: completed** (19.3s wall-time)
- **$0.25 spend** (5s Runway avatar speech)
- final asset `74caca39` (role=TALKING_HEAD)
- **completion signal fired correctly** → highlight status
  flipped APPROVED → RENDERED automatically

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1097** | +59 (1039 → 1098 → 1097 after B1.7 refactor) |
| - compositions | 608 | unchanged |
| - transcripts (new) | **38** | new app (12 model + 13 API + 13 approve) |
| - character_os.test_transcript_miner | **20** | new (was 21 pre-B1.7) |
| Media-engine | 209 | unchanged |
| SPA vitest | **188** | +54 (134 → 188: +30 B1.5 + +24 B1.6) |

`pnpm build` clean. Real-mode spend: **$0.25**.

## Calibration moments worth carrying

**Two new TRUST_CALIBRATION entries (31 total)**:

1. **gpt-5 reasoning eats output budget — char-offset math is
   a recurring trigger.** Asking the model to identify a
   substring + its offsets in a longer body silently blows the
   reasoning budget. The architectural fix beats budget bumps:
   ask for text only; locate offsets server-side via `find()`.
   Forward defense: any future Responses-API caller that needs
   to identify a substring of a larger body should follow this
   pattern. Add real-mode smoke tests to any new gpt-5 caller —
   mock-mode tests don't catch the budget burn.

2. **B-arc landed in a single session — scope-lock pattern
   pays off.** Eight contract rules + seven sequenced slices +
   per-slice test coverage produced a one-session arc with one
   surface bug. Same shape as A-arc (SESSIONS 185-192). Careful
   upfront scoping compresses the build phase.

## What's still queued

V2 candidates explicitly out of scope for B-1 v1:

* External transcript ingestion (.srt upload, third-party
  meeting notes)
* Original-session-audio extraction (clean re-bake vs noisy
  original)
* Auto-fire approve without operator gate (tier-based bypass)
* Batch mining across N transcripts at once
* Highlight chaining / montage (concat N approved highlights)
* Free-form tags on highlights
* Per-platform fan-out on approve

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions) — operator-content
  bottleneck.
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).
* **B-3 Personalized Video** — next strategic-axis arc.
* **B-14 Multi-Platform Variants** — distribution stickiness.

### Recommended next direction

The B-arc landing validates the strategic-axis arc cadence.
Natural next moves:

1. **B-3 Personalized Video** — biggest revenue unlock per the
   CONTENT_FORMAT_BACKLOG. 10+ slices.
2. **Asset upload UI** — operator-content bottleneck; unblocks
   v2 of B-1 (external transcript ingestion).
3. **B-1 v2 slices** — original-audio extraction, batch
   mining, highlight chaining. Each is ~1 session.

## Operational notes for the next session

* Dev-DB now has 3 PENDING + 1 RENDERED `TranscriptHighlight`
  rows from the dogfood. Cleanly browsable via the SPA at
  `/workspace/transcripts`.
* The completed composition `b4ab9ea6` carries the Marcus
  "Republic" highlight as its final_asset — auditable
  end-to-end via the F-arc lineage surfaces.
* No outstanding bugs; no open calibration backlog from the
  B-arc.

## Post-close addition — portrait persistence parity (commit `e4aec74`)

Same-session dogfood follow-up. SESSION 202's "look at the
SPA" moment surfaced 401s on the 5 real spokespeople's
portraits: Runway-signed CloudFront URLs in
`Spokesperson.portrait_path` had JWTs that expired
0.4-0.7 days ago. SESSION 169's `refresh_portraits` command
re-fetches fresh JWT URLs (buys 30 more days);
SESSION 202's bundled fix is the canonical solution —
download the bytes once + persist locally + update
`portrait_path` to the stable local URL.

New surfaces:
* Media-engine endpoint
  `POST /internal/avatars/<id>/persist_portrait/` — refresh
  + download + save + return local URL.
  `data/_internal/avatar_portraits/<avatar_id>.<ext>`.
* `MediaEngineClient.persist_avatar_portrait()` wrapper.
* `python manage.py persist_spokesperson_portraits` —
  idempotent backfill. Already-local rows skip the network.
* Wizard hook in `apps.spokespeople.views` — both
  `create_avatar` + `rebake_avatar` flows attempt persist
  after the Runway URL is assigned. Best effort with logged
  fallback to the JWT-signed URL on persist failure.

Backfill outcome: 5 spokespeople persisted (Marcus, Sasha,
Riggs, Donny, Thruman); 138 mock avatars correctly skipped.
Files verified served end-to-end via the SPA `/data` proxy.

Media-engine tests: 209 → **214 (+5)**. Django suite
unchanged.

**SESSION 169's `refresh_portraits` command stays in the
codebase as a recovery tool** — useful for any spokesperson
whose `portrait_path` somehow regressed to a JWT-signed URL
(e.g. ingested from a backup). For day-to-day operation,
new spokespeople get the local-persist treatment at creation
time; the JWT-churn watch is effectively over.
