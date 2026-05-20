---
title: "Transcript Miner — realtime conversations → shareable highlight clips"
status: complete
proposed: 2026-05-19 (SESSION 202, slice B1.0)
locked: 2026-05-19 (SESSION 202, slice B1.0)
closed: 2026-05-20 (SESSION 202, slice B1.7)
companion_docs:
  - REALTIME_AVATAR_V1.md
  - VIDEO_COMPOSITION_V1.md
  - ASSET_LIBRARY_V1.md
  - CONTENT_FORMAT_BACKLOG.md
---

# Transcript Miner — realtime conversations → shareable highlights

> **Status: LOCKED (SESSION 202).** First arc opened after the
> V-arc + Asset Library + forward-defense audit close-out. Eight
> contract rules below; seven slices B1.0-B1.7 to ship the arc.
> Locked at SESSION 202 with all 8 proposed resolutions accepted;
> B1.1 (LLM helper) opens immediately after lock commit.

---

## TL;DR

The R-arc lands `Asset(TRANSCRIPT)` for every realtime session
(R5 at session-end, R6.1 widened the query so mid-session
captures via `attach_memory` also flow). After ~10 R-arc dogfood
sessions the workspace has 4 transcripts averaging ~570 chars
each. **Nothing currently mines them.** The realtime spend
already happened; turning each live conversation into 3-5
shareable highlight clips is near-zero marginal cost in
provider $ but high-leverage in workspace value.

This arc ships:

1. **An LLM segment selector.** gpt-5-mini reads a TRANSCRIPT
   asset and returns 3-5 punchy moments with character offsets
   and reasoning.
2. **A `TranscriptHighlight` model** persisting the LLM picks
   with a status field that mirrors R7's approval shape
   (PENDING → APPROVED/REJECTED → RENDERED).
3. **An operator approval gate.** Operator reviews picks before
   any composition fires. Approved highlights enqueue a
   `talking_head_polished` composition automatically; rejected
   stay in the DB for audit.
4. **A workspace SPA surface** for picking a transcript →
   mining it → reviewing the picks → approving / rejecting.

**Strategic positioning.** Per `CONTENT_FORMAT_BACKLOG.md` §B-1
this is the highest-strategic axis remaining because the
per-workspace realtime avatar producing per-workspace
transcripts is structurally unique to this stack — no
LLM-video competitor has the same data to mine. The 18 V-arc
recipes are competitive parity; B-1 is structural moat.

Out of scope for v1: external transcript ingestion (.srt
upload, third-party meeting notes), original-session-audio
extraction (the alternative to re-baking), automatic firing
without operator approval, batch mining (operator picks one
transcript at a time).

---

## Why now

Five drivers converge:

1. **Inventory exists.** R-arc closed SESSION 157; R6.1 widened
   the transcript query SESSION 152; transcripts have been
   accumulating since. 4 in the dev workspace today.
2. **Small-slice backlog is depleted.** Six sessions of polish /
   fix / audit work (194 → 201) exhausted the queued
   small-slice items. SESSION 201 close-out explicitly named
   B-1 Transcript Miner as the top strategic candidate.
3. **All required primitives ship.** `generate_avatar_speech`
   (V3), `add_captions` (V9), `reformat_clip` (V9) are
   stable + real-mode validated. No new ffmpeg work.
4. **R7 approval pattern is proven.** SESSIONS 149-152 shipped
   the AWAITING_APPROVAL state machine + approve/reject REST
   surface for realtime tool dispatch. B-1 reuses the same
   shape for highlight approval — known-good UX pattern.
5. **The realtime spend is already sunk.** Every transcript in
   the workspace cost the operator real $ to produce via R-arc
   sessions. Not mining them is leaving paid-for value on the
   table.

---

## Contract rules (load-bearing)

Eight rules. None overlap V1's existing 22 rules (V1 ×9 +
V17 ×4 as 10-13 + Asset Library ×9 as 14-22). B-1's rules
become V1 rules 23-30 if the V-arc lock merges them later;
v1 keeps them on this doc.

1. **Source-only ingestion.** Input is exactly one workspace
   `Asset(TRANSCRIPT)` row. The miner reads `inline_content`
   (R5 persists the transcript body inline, not file). No
   external upload, no `.srt` parsing, no third-party
   meeting-tool integration in v1. External ingestion is a
   v2 axis (and v2 has its own privacy + auth surface).

2. **Workspace-scoped end-to-end.** Highlights live in the
   source transcript's workspace. `TranscriptHighlight` FKs
   to Workspace and Asset; cross-workspace asset reads are
   forbidden at clean()+pre_save signal level. Mirrors R-arc
   rule 6 + V1 rule 1.

3. **LLM selection is auditable.** Each persisted highlight
   row carries `text`, `char_start`, `char_end`, and
   `llm_reasoning`. The operator can verify the LLM's pick
   against the source `inline_content` by char-range hover.
   No "black-box" segment picks — if the model returns text
   the operator can't find at the declared offsets, the
   row is flagged invalid before rendering.

4. **Re-bake only in v1.** Approved highlights render via
   `generate_avatar_speech` re-baking the workspace's avatar
   saying the highlight text. The avatar comes from the
   source transcript's `RealtimeSession.spokesperson` (which
   R-arc persists). Original-session-audio extraction (slice
   the original session video, get cleaner authenticity)
   is a v2 axis — needs new ffmpeg primitive + the original
   session video Asset which R-arc doesn't always retain.

5. **Operator approval before render.** Mirrors R7's
   AWAITING_APPROVAL state. LLM picks land as PENDING;
   operator approves/rejects via REST. APPROVED rows
   auto-enqueue a `talking_head_polished` composition (the
   render fires inside the approve handler, like R7.2's
   `render_video` tool dispatch). v1 has no
   approval-threshold bypass — every highlight requires
   manual approval regardless of tier.

6. **No new ffmpeg primitives.** v1's pipeline is
   `generate_avatar_speech` → `add_captions` →
   `reformat_clip`. All three already ship + are real-mode
   validated. The B-1 axis is a *recipe* + a *mining
   pipeline*, not new ffmpeg work.

7. **One composition per approved highlight.** Each highlight
   becomes a standalone `talking_head_polished` composition
   with the highlight text as `script`. Compositions are
   independent + reusable Asset Library citizens. Operator
   chains them later via the SPA (e.g. concat 5 highlights
   into a montage) — chaining is out of scope for v1.

8. **Highlight text length is capped.** v1 caps each
   highlight at ≤ 280 characters. Two reasons:
   * `generate_avatar_speech` cost scales with duration; a
     280-char highlight maps to roughly ~25-30s of speech,
     keeping per-clip cost ≤ $0.10.
   * Social-platform shareable lengths (Reels ≤ 90s, TikTok
     ≤ 60s, X video ≤ 140s) all comfortably accommodate
     280-char highlights. Longer than that and the operator
     should use a longer-form recipe instead.

---

## Data model additions

### `apps.transcripts.models.TranscriptHighlight`

New Django app: `apps.transcripts`. Single model in v1.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace` | FK Workspace | V1 rule 1 isolation |
| `source_transcript` | FK Asset | constrained to `asset_type=TRANSCRIPT` via clean() |
| `text` | TextField | the highlight text the LLM returned |
| `char_start` | PositiveIntegerField | offset into source `inline_content` |
| `char_end` | PositiveIntegerField | char_end > char_start enforced |
| `llm_reasoning` | TextField | rationale string from the LLM for audit |
| `status` | TextChoices | PENDING / APPROVED / REJECTED / RENDERED (mirrors R7 shape) |
| `produced_composition` | FK Composition, nullable | set when APPROVED → render enqueued |
| `rejection_reason` | TextField, blank | optional operator note on REJECTED |
| `mined_at` | DateTimeField auto_now_add | |
| `decided_at` | DateTimeField, nullable | timestamp of approve/reject |
| `llm_model_id` | CharField | e.g. `gpt-5-mini`, for cost telemetry |
| `llm_cost_micros` | PositiveIntegerField | aggregate over all picks in one mining call divided per-row, or single row holds the call cost — see Q-b-5 |

Indexes: `(workspace, status)` for the approval queue, and
`(source_transcript)` for "what did this transcript produce."

Cross-workspace signal: `apps/transcripts/signals.py`
post_save guard like R-arc has — refuses to save if
`workspace_id != source_transcript.workspace_id`.

### No `Asset` schema change

Highlights are a workspace-level concept; the produced
clips become `Asset(role=TALKING_HEAD)` via the existing
`generate_avatar_speech` primitive (Asset Library A2 stamps
the role at emit time). No new Asset role needed; the
A8 cross-link surface already shows "what did this
composition produce." Highlight → composition → asset
chain is browsable without new Asset infrastructure.

---

## New / extended endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/transcript_highlights/mine/` | Body: `{transcript_asset_id, target_count?, max_chars?}`. Calls the LLM helper; persists N rows as PENDING; returns the list. |
| `GET` | `/api/transcript_highlights/` | Lists highlights filterable by `workspace` (implicit) + `status` + `source_transcript_id`. Paginated. |
| `GET` | `/api/transcript_highlights/<id>/` | Detail with `source_transcript_id`, full reasoning, and (when applicable) `produced_composition_id`. |
| `POST` | `/api/transcript_highlights/<id>/approve/` | Flips to APPROVED, enqueues `talking_head_polished` composition synchronously (the Celery task itself starts async); links the composition FK. Returns the highlight + the composition shape. |
| `POST` | `/api/transcript_highlights/<id>/reject/` | Body: `{rejection_reason?}`. Flips to REJECTED. |

Non-state-changing list/detail are read-only. Approve/reject
follow R7's REST shape exactly so the SPA pattern carries
over.

---

## Slice breakdown (7 slices, B1.0-B1.7)

| # | Slice | Effort |
|---|---|---|
| **B1.0** | This scope-lock doc | ½ session (current) |
| **B1.1** | `select_transcript_highlights` LLM helper | ½ session — `character_os/transcript_miner.py` with gpt-5-mini Responses-API call returning structured `list[HighlightCandidate]`. Mock-mode flag (`TRANSCRIPT_MINER_FORCE_MOCK`). Tests cover mock + structured-output parsing edge cases. |
| **B1.2** | `TranscriptHighlight` model + migration + admin | ½ session — Django app + model + migration + signals.py cross-workspace guard + admin registration. |
| **B1.3** | REST: mine endpoint | ½ session — `POST /api/transcript_highlights/mine/` with auth, workspace scoping, LLM helper integration, PENDING row persistence. Tests cover happy path + workspace isolation + LLM mock. |
| **B1.4** | REST: approve / reject + render dispatch | 1 session — approve handler enqueues `talking_head_polished` composition (via the recipe registry, passing the spokesperson + highlight text), links the composition FK; reject flips status. Signal on composition completion flips APPROVED → RENDERED. Tests cover both branches + the dispatch shape. |
| **B1.5** | SPA: transcript list + mining trigger | 1 session — new route `/workspace/transcripts` (or extend A5's `/workspace/assets` with a transcript-only filter chip — Q-b-6 to resolve at slice). Click into a transcript → `/workspace/transcripts/:id` shows the body + "Mine highlights" button + the mining-in-flight state. Subagent-delivered (react-web-delivery). |
| **B1.6** | SPA: approval UX | 1 session — highlights list with char-range hover-highlight on the transcript body, per-highlight Approve / Reject buttons + rejection reason textarea, approved highlights link to their composition. Subagent-delivered. |
| **B1.7** | Real-mode dogfood + close | ½ session — fire B-1 against one of the 4 existing Marcus transcripts. Validate end-to-end. Capture calibration entries. Close the arc. |

Total: ~5-6 sessions if the SPA subagent slices fit in one
session each (the prior A5+A6 SPA slices took 1 session each).
The backlog estimate said 6-8.

---

## In-scope clarifications

* **gpt-5-mini structured outputs.** The LLM call uses the
  Responses API with a JSON schema constraining the output
  shape. Per the `feedback_openai_gpt5_responses_api.md`
  memory: default to `gpt-5-mini` via `responses.create`,
  not `gpt-4o-mini` + `chat.completions`. The schema lives
  in `transcript_miner.py` alongside the helper.

* **Avatar selection for the re-bake.** The composition uses
  the spokesperson from `RealtimeSession.spokesperson` —
  the avatar who originally spoke the transcript. This
  preserves voice + persona continuity. Q-b-7 resolves how
  to find the RealtimeSession from the transcript_asset
  (the FK exists on RealtimeSession; reverse it).

* **Approval-cancel symmetry.** Once APPROVED a composition
  is enqueued. The operator can cancel the resulting
  composition via the existing composition delete surface
  (not part of B-1); the highlight row stays APPROVED with
  a dangling produced_composition FK that resolves to None
  if deleted. No special handling.

* **Mining the same transcript twice.** v1 allows re-mining
  — useful if the operator wants a fresh set of picks or
  tweaks the `target_count`. Each mining call creates new
  PENDING rows; prior rows keep their status. Q-b-8 covers
  whether to de-dupe overlapping char ranges automatically.

---

## Out of scope (v1)

* **External transcript ingestion.** `.srt` upload, paste-
  text-as-transcript, third-party meeting tool integration.
  v2 axis with its own auth + privacy surface.
* **Original-session-audio extraction.** Slicing the
  original session video by char_start/char_end via
  per-token timestamps. R-arc doesn't always retain the
  session video; needs new schema + new ffmpeg primitive.
* **Auto-fire without approval.** Approval gate is
  load-bearing in v1 per rule 5. Tier-based bypass is a v2
  axis (Agency might want auto-fire with confidence
  threshold).
* **Batch mining.** Mine across N transcripts at once. v1
  is one-at-a-time per the UI pattern.
* **Highlight chaining (montage).** Concat N approved
  highlights into one clip. Operator can do this manually
  via the existing `concat_clips`-based recipes; B-1
  doesn't ship a one-button montage.
* **Free-form tags on highlights.** Same reasoning as Asset
  Library rule 1 — closed surface in v1, tags after if
  needed.
* **Per-highlight platform targeting.** Each highlight
  becomes a `talking_head_polished` at 1280:720; the
  operator runs `reformat_clip` separately for Reels /
  TikTok via the existing V9 recipe. v2 might bake
  per-platform fan-out into the approve action.

---

## Open questions (resolve in slices)

* **Q-b-1**: How many highlights should the LLM return by
  default? Backlog says 3-5. **Proposed default**: 5.
  Operator-overridable via `target_count` (clamped 1-10).
  Resolve at B1.1.

* **Q-b-2**: Should REJECTED highlights stay in DB for
  audit, or be deleted? **Proposed**: stay. Mirrors R7's
  treatment of REJECTED invocations. Cheap; auditable.
  Resolve at B1.2.

* **Q-b-3**: Highlight text length cap. **Proposed**: hard
  cap 280 chars per rule 8. Resolve at B1.1 (the LLM prompt
  needs the cap baked in).

* **Q-b-4**: Approve = auto-fire vs stage-as-draft.
  **Proposed**: auto-fire (matches R7.2 `render_video`
  flow). Operator can cancel via composition delete.
  Resolve at B1.4.

* **Q-b-5**: LLM cost telemetry shape. The mining call
  picks N highlights in one Responses-API call; cost is
  per-call. Should we (a) divide the call cost across the
  N rows for per-row accounting, or (b) store the full
  call cost on the *first* row + 0 on the rest? Or (c)
  add a separate `MiningCall` model? **Proposed**: option
  (b) — first row holds the call cost; other rows hold 0;
  add a docstring note. (c) is overkill for a single LLM
  call; (a) is misleading. Resolve at B1.2.

* **Q-b-6**: Standalone `/workspace/transcripts` route vs
  extend A5's `/workspace/assets` with a transcript filter.
  **Proposed**: standalone. The miner workflow is
  transcript-centric (browse → pick → mine → approve);
  A5's asset list is workspace-wide. Resolve at B1.5
  (subagent can argue either way based on UX coherence).

* **Q-b-7**: Finding the spokesperson for the re-bake.
  `RealtimeSession.transcript_asset` is the existing FK;
  reverse-lookup
  `Asset.realtimesession_set.first().spokesperson`. What
  if the transcript was created via `attach_memory` tool
  (R7.3) mid-session — same RealtimeSession; same
  spokesperson? Yes, the tool helper persists the same
  workspace anchor. **Resolved**: reverse FK; fail loudly
  if absent (B1.4 raises a clear error in the approve
  handler).

* **Q-b-8**: Re-mining the same transcript — should
  overlapping char ranges be de-duplicated automatically?
  **Proposed**: no automatic de-dupe in v1. Each mining
  call is independent; the operator can reject duplicates
  manually. Cheap to revisit if it becomes a UX problem.
  Resolve at B1.3.

---

## Change log

* **2026-05-19 (SESSION 202, slice B1.0)** — Initial scope
  proposal. Triggered by SESSION 201's close-out naming B-1
  as the top strategic axis remaining after the V-arc UX
  polish + forward-defense audit exhausted the small-slice
  backlog. Eight contract rules; seven slices B1.0-B1.7
  sequenced.

* **2026-05-19 (SESSION 202, slice B1.0 LOCKED)** — Operator
  signed off as-proposed. All 8 contract rules accepted
  without revision. All 8 open questions accepted with
  proposed resolutions (Q-b-1: default 5 highlights; Q-b-2:
  keep REJECTED rows; Q-b-3: 280-char cap; Q-b-4: approve
  auto-fires render; Q-b-5: first row holds full LLM call
  cost; Q-b-6: standalone `/workspace/transcripts` route;
  Q-b-7: reverse-FK from RealtimeSession; Q-b-8: no
  auto-dedupe on re-mining). Status flips proposed →
  locked. B1.1 (LLM helper) opens immediately.

* **2026-05-20 (SESSION 202, B1.7 — ARC CLOSED).** Eight slices
  (B1.0–B1.7) shipped in one extended session. Real-mode
  dogfood validated end-to-end against a 913-char Marcus
  transcript (Caesar assassination conversation):
  3 highlights mined ($0.001 LLM), 1 approved + rendered
  ($0.25 Runway), composition completed in 19.3s, completion
  signal flipped APPROVED → RENDERED automatically.

  **Mid-arc contract reshape**: B1.7 dogfood surfaced the
  recurring "gpt-5 reasoning eats output budget" pattern when
  asked to compute char offsets alongside content selection.
  Rule 3 (auditable LLM selection) is preserved but the
  mechanism shifted: the LLM returns text + reasoning only;
  the parser locates offsets via ``body.find(text)``. Functional
  contract unchanged; the LLM's job is now pure pattern-matching.

  Tests at close: Django **1098 → 1097 (net -1 from B1.7
  refactor)**; SPA vitest **134 → 188 (+54)**; media-engine
  unchanged at 209. Real-mode spend: **$0.25** (one full
  approve-to-render cycle).

  Status: **complete**. Outstanding v2 candidates (not in v1
  scope): external transcript ingestion, original-session-audio
  extraction, auto-fire without approval, batch mining,
  highlight chaining/montage.
