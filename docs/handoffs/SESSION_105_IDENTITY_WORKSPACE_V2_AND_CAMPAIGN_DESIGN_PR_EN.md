# SESSION 105 — Identity Workspace v2 + Campaign Workspace v1 (PR EN + EO-a)

**Date:** 2026-05-11 (post-submission, first cleanup arc)
**Author:** Claude (Opus 4.7) for Chris (chris@donkeybetz.com)
**Branch:** `main` — two slices (PR EN + PR EO-a) layered on SESSION 104's `674c308`
**Triggered by:** *"now that it's submitted, I really hate the way the UI
feels... I don't know how I think it should feel but its not the current
way it is"*

> **Session-end state (2026-05-11 night):** PR EN and PR EO-a both
> landed and verified visually in real-mode by the operator. PR EN
> drew warm reaction ("That looks a 1000% better already"). PR EO-a
> drew a mixed reaction: the focused workspace landed cleanly but
> **the campaign creation + tracking flow still feels wrong** —
> operator's words: *"there just seems to be too much going on
> without enough explanation."* Resume point for SESSION 106 is at
> the bottom of this doc under **"Operator feedback on EO-a +
> resume-point for next session."**
>
> **2026-05-12 update (morning, before SESSION 106 coding begins):**
> Operator woke up after a 12-hour crash-out and opened the session
> with research instead of code: *"is there anything we can do to
> broaden the use of the Avatars and things like that?... we might
> take most of this app and merge it into another app."* Produced
> a full survey of parked PRs, unused Runway endpoints, output
> formats, use cases, distribution shapes, platform plays, and
> architecture upgrade paths. Captured in the new research doc
> `docs/research/POST_SUBMISSION_OPPORTUNITY_MAP.md`. The "merge
> into another app" target hasn't been picked yet — the doc's §8
> decision frame is the next conversation prompt.
>
> **2026-05-12 update (afternoon — Tier-1 credit burns shipped):**
> Operator confirmed dashboard balance of 48,623 credits with no
> expiration, then approved firing the Tier-1 probes parked in
> `SPEECH_TYPE_AUDIO_FINDINGS.md`. Three probes ran successfully:
> (1) PR DY-2 60s `speech.type=audio` probe — 55.07s in / -0.04s
> drift / clean lip-sync; (2) PR DY-2 120s probe — 122.10s in /
> -0.04s drift / clean lip-sync; (3) PR EM-h realtime READY cap
> real-mode smoke — session reached `connected` sub-second, WebRTC
> handshake through LiveKit US Central, clean teardown. The -0.04s
> drift being exactly constant across 42s/55s/122s probes proves
> it's codec rounding (ffmpeg → Runway → ffmpeg), not Runway
> truncation. PR EA's last research dependency is resolved — the
> single-pass Long Ad path can ship for ads up to 2 minutes with
> zero remaining unknowns. Total burn ~300 credits; dashboard
> ~48,300 remaining. Probe MP4s saved at `~/Desktop/Donkey Betz
> Videos/probe-{60,120}s-riggs-rally.mp4`. Full writeup in the
> updated `docs/research/SPEECH_TYPE_AUDIO_FINDINGS.md` PR DY-2
> section. Also noticed the WebRTC SDK fires `already connected to
> room ...` 49 times during a normal session — that's a benign
> over-rendering pattern in `RealtimeSpokesperson.jsx` that wants
> a `useMemo`/`useCallback` audit (not blocking, but file as a
> follow-up).
>
> **2026-05-12 update (afternoon — PR EQ/ER/ES shipped on the same
> Tier-2 validation arc; full writeups appended below).** Operator
> continued Tier-2 testing, surfacing two distinct realtime bugs and
> two distinct CampaignWorkspace bugs. Three PRs landed back-to-back.
> Runway's realtime/avatar_conversations pipeline was consistently
> returning `status: failed, failureCode: UNKNOWN` for every new
> session today — a Runway-side instability that blocks end-to-end
> memory-loop validation but does NOT affect avatar_videos or the
> agentic-loop tool catalog itself. Test 2 (`avatar_videos` render
> from inside CampaignWorkspace) was validated after PR ES; Test 3
> (real conversation memory loop) is parked until Runway recovers.
>
> **2026-05-12 update (afternoon — PR EP shipped):** Operator ran
> Tier-2 UI validation and immediately surfaced two real bugs that
> the redesign exposed. PR EP fixes both in one slice:
>
> **Bug 1 — transcripts never auto-fetched on session end.**
> `RealtimeSpokesperson.handleEnd` was calling
> `api.endSpokespersonSession` but never `api.fetchRealtimeTranscript`.
> So every realtime session was closing on the Runway side but
> leaving zero footprint in `campaign.realtime_transcript_history`,
> which broke the entire memory loop downstream: no transcript →
> no PR EM-c auto-ingest → no memory entry → no thread title /
> Resume button when EO-b/c eventually ship. Fix: best-effort
> `fetchRealtimeTranscript` call after `endSpokespersonSession`
> returns, with the same swallow-errors-log-to-console pattern
> PR EM-i uses for the attach_memory_to_campaign chain. Also
> loosened the `ConversationsHistory` filter — previously dropped
> campaigns with zero turns, so even when fetches landed they were
> invisible. Now shows them with the existing "(no turn text
> recorded)" placeholder so the operator can tell a session
> happened even if Runway returned an empty conversation.
>
> **Bug 2 — portrait regen doesn't propagate to the avatar.**
> PR DU shipped a "Rebuild Avatar" button to solve this back in
> 2026-05-10, but PR EN tucked it inside the new `⚙️ Advanced`
> disclosure, making it un-discoverable from outside. Operator
> regenerated Donny, saw the new portrait, then rendered an ad
> that used the OLD face. New `portrait_drift_from_avatar: bool`
> field on the Character model — set to `True` in
> `post_generate_portrait` when an avatar already exists, cleared
> to `False` in `post_create_avatar` after rebuild succeeds.
> Frontend renders an amber banner at the top of the Identity
> panel when drift is true, with its own "Rebuild Avatar" CTA
> wired to the existing `handleCreateAvatar`. The legacy
> CharacterCard inside Advanced is untouched.
>
> **Two polishes after operator missed the banner the first
> time** (was focused on the Advanced disclosure where they'd
> just clicked Regenerate): (1) banner `scrollIntoView` on the
> false→true transition (not on initial mount, so a page refresh
> with drift already true doesn't surprise-scroll); (2) inline
> `⚠️ rebuild needed` amber chip on the closed Advanced
> disclosure summary — visible regardless of which surface the
> operator is looking at.
>
> **Files touched:**
> - `backend/app/models.py` — new `portrait_drift_from_avatar` field
> - `backend/app/routers/characters.py` — set on portrait gen,
>   clear on avatar create
> - `frontend/src/components/RealtimeSpokesperson.jsx` —
>   transcript auto-fetch on End
> - `frontend/src/components/IdentityPanelV2.jsx` — banner,
>   scroll-on-transition, Advanced summary chip
> - `frontend/src/components/ConversationsHistory.jsx` — filter
>   loosened to show 0-turn campaigns
>
> **Backend route count unchanged at 85** (no new routes — both
> APIs already existed). Build delta: lazy chunk +0.5 KB to
> 617.07 KB / 164.05 KB gzip. Initial chunk unchanged. No
> migration needed — existing characters.json records pick up
> the new field as `False` on first read via Pydantic default.
> Servers running in real-mode at session end; backend restarted
> once during the slice to pick up the new model field.

This session is two-thirds **design conversation** + one-third
**shipped code**. The design conversation produced a thesis for what
the v2 workspace should look like; PR EN shipped the first slice of
that thesis (Identity page reorganization). PR EO (campaign workspace
redesign) is scoped + sketched but not yet shipped — captured here so
SESSION 106 can resume without re-deriving the rationale.

---

## The thesis that came out of the design conversation

The operator's complaints across the Identity / Campaigns / Videos /
Conversations tabs converge on one observation: **the Workspace is
organized by *thing type* (Identity / Knowledge / Memory / Campaigns
/ Conversations / Videos), but the operator's actual unit of work is
the *campaign*.**

- Videos belong to campaigns → today they're a flat, ungrouped list at
  the *character* level.
- Conversations belong to campaigns → today they're a log entry at the
  *character* level, with no thread structure.
- Memory entries are conversation-derived → today they're surfaced at
  the *character* level via the Memory tab.
- Dialogue scenes span multiple characters → the current data model
  has no home for them outside the "owning" character.

The reframe: **the campaign is the workspace, not the character.** The
character page becomes a thin identity surface + campaign launcher.
Clicking a campaign opens *its* workspace where conversations, videos,
and memory all live together — colocated with the brief they belong to.

PR EN implements the thin-identity half of that reframe. PR EO (next)
will implement the campaign workspace.

---

## PR EN — Identity Workspace v2 (`<commit pending>`)

### What shipped

- **Backend:** new `IdentityPatchBody` Pydantic model +
  `POST /api/characters/{id}/identity` route in
  `backend/app/routers/characters.py`. Accepts partial updates of
  `personality` (≤600 chars), `voice_preset` (validated against
  `SUPPORTED_VOICE_PRESETS`), `subject` (≤300 chars). Missing keys are
  left alone; empty strings clear `personality` / `subject`. Backend
  route count: **84 → 85**.
- **Frontend:** new `frontend/src/components/IdentityPanelV2.jsx`
  (~440 lines). Replaces the legacy Identity tab body inside
  `SpokespersonWorkspace`.
- **Frontend API:** new `api.patchCharacterIdentity(id, patch)` in
  `frontend/src/api.js`.
- **Workspace integration:** `SpokespersonWorkspace.jsx` got
  `handleCharacterChanged` (merges Character patches back into local
  state without refetch) and `handleResumeConversation` (picks the
  campaign with the most recent transcript history, switches to the
  Conversations tab, arms `pendingAutostart` so the realtime session
  opens automatically).
- **Header CTA:** new emerald `▶ Resume conversation` button next to
  `+ New Campaign` in the workspace header. Disabled (with a tooltip)
  when there's no ready avatar or no campaigns.

### Layout (matches the ASCII sketch from the design conversation)

```
┌──────────────────────────────┬──────────────────────────────────┐
│  contained portrait (96×96)  │  activity strip (chips for       │
│                              │  N campaigns / N conversations / │
│  voice_preset dropdown ▾     │  N renders / last active)        │
│   (editable, save on change) │                                  │
│                              │  campaign grid — 2-up cards,     │
│  personality cue textarea    │  newest first, click → that      │
│   (editable, save on blur)   │  campaign in the Campaigns tab   │
│                              │                                  │
│  📚 Knowledge ▸ (accordion;  │  + New campaign button           │
│   collapsed, expands the     │                                  │
│   existing KnowledgePanel)   │                                  │
└──────────────────────────────┴──────────────────────────────────┘
⚙️ Advanced — portrait regen, avatar create, voice cloning  (details)
🚨 Danger zone — typed-name delete confirmation (unchanged)
```

The full legacy CharacterCard is preserved inside the **⚙️ Advanced**
disclosure — every portrait regen / avatar create / voice clone
action that used to dominate the Identity tab is still reachable, just
one click away.

### Why personality was made editable

It's the single highest-leverage field on a Character: it gets injected
late in the personality string composed by
`_build_session_overrides`, which means it weighs heavily in every
realtime session's system prompt (Runway's `gwm1` model weights later
instructions higher per session-feature-level tuning). Operators
needed a way to revise it without recreating the character.

Voice preset was added for symmetry — same patch route, same UX
pattern, low marginal cost.

### Failure mode handling

- Save errors revert local state to the last-saved value and surface a
  rose-text error message under the form. No save-retry loop — the
  operator retypes if they want to retry.
- Empty personality / subject patches normalize to `None` on the
  backend so an operator can clear them.
- `voice_preset` cannot be cleared — every character must have a
  preset bound. Empty string returns 400.
- New `Character` record is merged back into local state via
  `handleCharacterChanged` so the header pills + the form resync
  without a full `listCharacters` refetch.

### Test status

Pre-PR-EN smoke baseline against clean `main`:
- ✘ Legacy ModeBanner test fails on `Concepts (OpenAI): mock` —
  preexisting drift from `LLM_PROVIDER=ollama` in `.env`. ModeBanner
  still reads `openai_mock` even though Ollama is the active LLM. Not
  in scope for this slice.
- ✘ Spokesperson Library `/spokespeople/this-id-does-not-exist` goto
  times out at 15s waiting for the `load` event. Page snapshot shows
  the not-found state rendered correctly; some XHR is keeping `load`
  pending. **Verified against clean `main` — preexisting.**
- ✓ Top-bar Legacy UI round-trip passes.

Post-PR-EN: same 2 failures, no regressions. Frontend `npm run build`
clean. Backend `python -c "from app.main import app; print(len(app.routes))"`
returns 85 (was 84).

### Build delta

| | Before | After | Delta |
|---|---|---|---|
| Initial JS | 591.27 KB | 561.97 KB | -29.30 KB |
| Lazy JS | — | 602.31 KB | new chunk |
| Gzip (initial + lazy combined) | 158.19 KB | 311.41 KB | +153 KB total served |

Note: Vite split the bundle differently after IdentityPanelV2 was
added (the new component's import graph nudged a code-split boundary).
The combined download is larger but Vite now lazy-loads the second
chunk per route. For the Identity-tab-first paint the served bytes are
slightly smaller. Sanity-check this next session with a network panel
recording.

---

## PR EO — Campaign Workspace (designed, not shipped)

### Scoped layout (from the design conversation sketch)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Donny Sparks    CEO Buzz       [ ▶ Resume conversation ]         │
│ AI Spokesperson Infra · 12 outputs · 4 conversations               │
├────────────────────────────────────────────────────────────────────┤
│ WHAT DO YOU WANT TO MAKE?                                          │
│ [ Spokesperson Ad ]  [ Dialogue Scene ]  [ Cinematic Commercial ]  │
├──────────────────────────────────┬─────────────────────────────────┤
│ CONVERSATIONS                    │ OUTPUTS                         │
│ ┌──────────────────────────────┐ │ Spokesperson Ads (5)            │
│ │ "Walking through demo flow"  │ │ [ ▶︎8s ] [ ▶︎32s ] [ ▶︎45s ]      │
│ │ 12 turns · 4 min · 2h ago    │ │                                 │
│ │ 🧠 saved · attached as RAG   │ │ Dialogue Scenes (2)             │
│ │      [ resume ] [ review ]   │ │ [ Donny·Riggs ] [ Miles·Donny ] │
│ └──────────────────────────────┘ │                                 │
│ (more threads, newest first)     │ Cinematic (3) / Storyboard (1)  │
├──────────────────────────────────┴─────────────────────────────────┤
│ 📋 Brief ▸     business · product · audience · tone · script       │
│ 🧠 Memory ▸    8 entries · attached doc (12k / 40k chars)          │
└────────────────────────────────────────────────────────────────────┘
```

### Backend data-model additions PR EO needs

1. **Threads** — add two fields to `TranscriptHistoryEntry`:
   - `title: Optional[str]` — Llama-generated, ~60 chars, noun-phrase
     prompt. Fired in the background after every successful
     `POST /realtime-transcript` (same hook the PR EM-c auto-ingest
     uses). Operator can click to edit inline.
   - `memory_status: Literal["captured", None]` — set to `"captured"`
     after `attach_memory_to_campaign` runs ingest for this thread.
     Decoupled from campaign-level `runway_document_id` so the two
     concerns stay independent.
2. **Dialogue cast** — add `character_ids: list[str]` to OutputRecord
   for dialogue scenes so the UI can render a "Donny+Riggs" badge.
   Backfill: read from `campaign.dialogue_lines[].character_id` on
   render so existing scenes don't need migration.
3. **Resume endpoint** — `POST /api/campaigns/{id}/realtime-session`
   accepts `resume_thread_id: <conversation_id>`. Handler:
   - Look up the thread in `campaign.realtime_transcript_history`.
   - If `memory_status` is null, run the four-step capture chain
     synchronously (ingest → compose → republish → attach).
   - Inject a `RESUMING: your last conversation was about <title>` cue
     into the personality late in the prompt.
   - Hand off to `realtime_avatar_client.create_session` as today.

### Frontend changes PR EO needs

- New route `/spokespeople/:id/campaigns/:campaign_id` OR a new
  in-place "Campaign Workspace" view inside the Campaigns tab when a
  campaign is selected. **Open question:** route or in-place?
  - Route: shareable URL, browser back/forward works, cleaner mental
    model. Cost: navigation overhead, more router config.
  - In-place: zero router work, faster swap. Cost: URL doesn't encode
    state, refresh loses the campaign focus.
  - **Lean: route.** State-encodes well, makes "share a campaign link"
    a real thing, fits the campaign-is-the-unit reframe.
- Mode picker as the primary action surface (kills the scattered
  "Generate this / Render that" buttons across current lanes).
- Conversations column as a thread list, newest first. Read-only
  initially (no Resume button) until the backend resume endpoint
  lands; Review button opens the existing PR AJ replay modal.
- Outputs column grouped by `OutputRecord.kind` with count badges.
  Dialogue scene tiles wider to fit the cast badge.
- Brief + Memory as collapsed accordions at the bottom.

### Failure modes to handle in PR EO

- **Thread older than Runway's retention window** — Resume falls back
  to "start fresh on this campaign" with the warm-return opener, no
  resume cue. Toast: *"Couldn't load original thread context — starting
  fresh with full memory."*
- **Mid-session transcript fetch 4xx during capture chain** — already
  handled by PR EM-i (best-effort, swallowed). Same behaviour applies
  to the synchronous capture-on-resume path.
- **No transcripts yet** — Resume button stays disabled or falls
  through to a fresh start.

### PR EO sub-slicing

To keep each sub-slice reactable:

1. **PR EO-a ✅ SHIPPED THIS SESSION** — Frontend-only campaign
   workspace shell. See "PR EO-a — Campaign Workspace v1" section
   below for the landed-state writeup.
2. **PR EO-a-2** — Reorganize the campaign workspace so the mode
   picker is the prominent first action (rather than buried inside
   the embedded `<CampaignLanes>`). Requires restructuring how
   CampaignLanes presents itself or extracting a mode-pick surface.
3. **PR EO-b** — Backend: thread titles via Llama background fire after
   transcript fetch. UI shows titles when present.
4. **PR EO-c** — Backend + frontend: `memory_status` on thread +
   Resume button + resume endpoint.
5. **PR EO-d** — Backend + frontend: `character_ids` on OutputRecord +
   cast badge on dialogue tiles.

EO-a lands the *layout* so the operator can react to it without
waiting on backend work. Subsequent sub-slices fill in the data-model
gaps as separate, reviewable changes.

---

## PR EO-a — Campaign Workspace v1 (shipped this session)

### What shipped

- **New route** `/spokespeople/:id/campaigns/:campaign_id` registered
  in `frontend/src/App.jsx`.
- **New component** `frontend/src/components/CampaignWorkspace.jsx`
  (~440 lines). Layout: header strip (back link to spokesperson,
  campaign title, render + conversation counts, Resume CTA) → 2-col
  split (conversations list on left, outputs grouped by mode on
  right) → live conversation panel (mounts existing
  `<RealtimeSpokesperson>` — Resume CTA scrolls here + autostarts) →
  editing surface (mounts existing `<CampaignLanes>` unchanged for
  brief / script / generation) → collapsed Memory accordion.
- **Outputs grouped by mode** — 🎤 Spokesperson Ads, 🎭 Dialogue
  Scenes, 🎬 Cinematic, 📦 Storyboard, 📱 Reels. Empty groups hide
  themselves. Tiles render inline `<video>` previews with duration +
  ratio + relative-time chips.
- **Identity panel cards now navigate to the new route** (previously
  they switched to the Campaigns tab + selected the campaign there).
- **Campaigns tab is now a card-only index** — per option 2 of the
  three-option choice the operator made earlier this session. 2-up
  grid showing business · product · render count · convo count ·
  `open →` affordance. Click navigates to the campaign workspace.
  Inline lane editing is gone from this tab. `+ New Campaign` still
  opens the mode modal as before; the lane mounts internally to
  handle the creation flow, after which the new card appears in the
  grid above.

### What did NOT change (deferred to later sub-slices)

- Conversations column shows raw transcript history (no titles, no
  Resume button per thread). EO-b adds titles; EO-c adds the
  per-thread Resume.
- Dialogue scene tiles don't show cast badges. EO-d adds that with a
  backend `character_ids: list[str]` field on `OutputRecord`.
- The mode picker is still buried inside the embedded
  `<CampaignLanes>` rather than being the prominent first action.
  EO-a-2 fixes that.

### Build delta

```
dist/assets/index-C1LJil20.js   561.97 kB │ gzip: 150.69 kB   (initial — unchanged)
dist/assets/index-BNIg89uW.js   615.23 kB │ gzip: 163.61 kB   (lazy chunk +13 KB)
```

### Backend touchpoint

None. EO-a is pure frontend. Vite HMR picked up the new route +
component without a server restart. Backend route count stays at 85.

### Test status

No smoke run after EO-a shipped (operator was ready to wrap for the
night). Build clean. Manual visual verification confirmed by
operator in real-mode browser session. Smoke run is recommended in
the SESSION 106 opening to catch any regression in the
SpokespersonWorkspace assertions (the Campaigns tab list now uses a
grid layout — testids `spokesperson-workspace-campaigns-row` and
`spokesperson-workspace-campaigns-delete` are preserved).

---

## Operator feedback on EO-a + resume-point for next session

The operator's reaction to EO-a was mixed. Layout shape OK; **the
campaign creation + tracking flow itself still feels wrong**:

> *"I still don't like how the Campaigns are created and tracked,
> there just seems to be too much going on without enough
> explanation."*

Two distinct threads embedded in that complaint:

### Thread 1 — "How they're created"

Current flow: click `+ New Campaign` → opens mode picker modal
(pick Spokesperson / Dialogue / Cinematic) → mode-specific lane
mounts → fill brief in Step 1 → save → new campaign exists.

**Hypothesis:** the wrong step is leading. Mode-pick-first forces the
operator to decide *what to make* before they've told the system
*what the campaign IS*. Cleaner reframe: `+ New Campaign` opens a
small "name + brief" modal (business, product, audience, tone —
that's it), saves, and lands the operator inside the campaign
workspace. *Inside* the workspace, the mode picker is the next
prominent question — "What do you want to make?" — and choosing it
surfaces the lane. Same total clicks, different mental model: create
the *container* first, fill it second.

### Thread 2 — "How they're tracked"

Current card content: `business · product · N renders · N convos ·
open →`. A lot of glyphs with no framing.

**Three possible directions:**

1. **State pill** — replace "draft / N renders" with a visual
   lifecycle pill: `brief only` → `script written` → `1+ rendered`
   → `published`. A glance tells you where each campaign is.
2. **Plain-language status** — instead of `2 renders · 4 convos ·
   open →`, write `"2 ads, 4 conversations · last touched 2h ago"`.
3. **Inline guidance** — empty states + new-campaign cards say what
   to do next ("No script yet — open this campaign to write one").

### The three triangulation questions left open at session end

1. **Created** — is it the *mode-pick-first* step that's wrong, or
   something else about the creation modal (too many fields, no
   inline explanation of what business / product / audience / tone
   actually do, etc.)?
2. **Tracked** — is it the *cards specifically*, or is it broader
   (no sense of which campaign needs attention, no "this one is
   ready to demo" concept)?
3. **Explanation** — do you want more inline helper text on existing
   surfaces, or a one-time onboarding that explains what a campaign
   *is* in the first place?

Operator went to bed before answering. SESSION 106 should re-pose
these questions, pick one, and execute.

### Suggested SESSION 106 opening sequence

1. Refresh the operator on the three threads above.
2. Get a pick on which thread to pull (or all three).
3. If **Created** (mode-pick-first) is the pick → propose a thin
   `+ New Campaign` modal that just collects business + product
   (rest optional), saves immediately, navigates to the new
   workspace. Mode picker then becomes the prominent action surface
   in the workspace (which conveniently is also PR EO-a-2's scope —
   ship them together).
4. If **Tracked** is the pick → instrument the lifecycle states
   (state pill or plain-language status). This is purely frontend
   and doesn't need any of EO-b/c/d's backend work.
5. If **Explanation** is the pick → audit every campaign surface
   (Identity grid, Campaigns tab, CampaignWorkspace header) for
   missing inline helper text. Consider a small "what is a
   campaign" disclosure on the empty Campaigns tab.

Best bet: **Created + Mode picker reorganization (EO-a-2)** together.
That's the highest-leverage move — it fixes the creation flow AND
the workspace's primary-action surface in one slice.

---

## Verification gates run (full session)

```bash
# Frontend build (PR EN + EO-a combined)
cd frontend && npm run build
# → dist/assets/index-C1LJil20.js   561.97 kB │ gzip: 150.69 kB
# → dist/assets/index-BNIg89uW.js   615.23 kB │ gzip: 163.61 kB

# Backend route count
cd backend && source .venv/bin/activate
python -c "from app.main import app; print(len(app.routes))"
# → 85   (was 84 at SESSION 104; +1 for /identity, no new routes in EO-a)

# Real-mode boot left running at session end
bash scripts/start-local-real.sh
# → Backend: http://localhost:8000  Frontend: http://localhost:5173
# → runway_mock=false, openai_mock=false, llm_provider=ollama
```

Servers were left running so the operator can pick up tomorrow
without a fresh boot. No automated generation fired during the
session — manual visual inspection only.

---

## Hold-over items the operator flagged but didn't push on yet

These came up in conversation but weren't explicitly scoped — capture
them so SESSION 106 doesn't lose them:

- **"The Campaigns stack makes no sense at all."** Partially addressed
  by PR EN (campaign cards on the right canvas of the Identity page),
  but the *Campaigns tab itself* still uses the old single-column row
  list. PR EO will replace that tab with the new campaign workspace.
- **"The videos have no real order to them."** Today the Videos tab
  is a flat OutputsGallery. PR EO groups by mode (Spokesperson /
  Dialogue / Cinematic / Storyboard) inside the campaign workspace.
  Cross-campaign Videos tab at the character level can either be
  removed or repurposed as an aggregated view; deferred decision.
- **Editing personality affects future sessions only.** Already noted
  in the IdentityPanelV2 inline helper text. Worth a "Regenerate
  memory document with new framing" button if operators dramatically
  rewrite the personality — flagged for post-PR-EO consideration.
- **PgVectorMemoryStore.** Phase 3 of the memory architecture is still
  one-new-class away. Documented in `00-START-NEXT-SESSION.md`. Not on
  the critical path for any UI redesign.

---

## Verification gates run

```bash
# Frontend build
cd frontend && npm run build
# → dist/assets/index-cnl3Ndpq.css   44.81 kB │ gzip:   8.18 kB
# → dist/assets/index-B07tG7oT.js   561.97 kB │ gzip: 150.69 kB
# → dist/assets/index-CmhYvB0B.js   602.31 kB │ gzip: 160.72 kB

# Backend route count
cd backend && source .venv/bin/activate
python -c "from app.main import app; print(len(app.routes))"
# → 85   (was 84 at SESSION 104)

# Backend identity route registered
python -c "from app.main import app; print('/api/characters/{character_id}/identity' in [r.path for r in app.routes if hasattr(r,'path')])"
# → True

# Mock-mode boot
bash scripts/start-local-mock.sh
# → ✅ booted, openai_mock=false, runway_mock=true, image_gen_mock=true,
#    llm_provider=ollama, llm_model=llama3:latest

# Mock-mode Playwright smoke (pre-existing failures only)
(cd frontend && npm run test:e2e)
# → 1 passed (Top-bar Legacy UI round-trip)
# → 2 failed (legacy ModeBanner, Library not-found goto)
# → BOTH failures reproduce against clean main. Not introduced by PR EN.
```

Real-mode boot was used at end of slice for manual visual inspection;
no Runway calls fired (operator clicked into the new Identity page
only).

---

## Next session

Pick up PR EO-a — campaign workspace frontend shell. The user is
visual; ship the smallest meaningful layout slice they can react to,
then triangulate. Don't lump EO-b/c/d into the same change.

If the operator drifts to a different thread of the UI redesign, the
hold-over items list above is the place to look for what else they
flagged but hasn't been scoped yet.

---

## PR EQ — Tool description rewrite + handleEnd retry-on-empty (shipped 2026-05-12 afternoon)

**Triggered by:** Operator ran Test 1 from Tier-2, surfaced two
distinct realtime issues: (1) the `attach_memory_to_campaign` tool
wasn't firing on the trigger phrase *"save our conversation"* —
avatar said *"the conversation is being recorded by the platform"*
and *"I don't have access to do that,"* both wrong. (2) The previous
PR EP transcript fetch was firing too eagerly — same conv_id was
fetched twice within 200ms, suggesting `handleEnd` was being
double-invoked by the simultaneous `<RealtimeOverlay onEnd>` and
`<AvatarCall onEnd>` callbacks.

**Backend** — `realtime_avatar_client.py:513` `attach_memory_to_campaign`
tool description rewritten with the PR EM-g MANDATORY INVOCATION
TRIGGERS + CONSEQUENCE pattern. Trigger phrase list expanded from 3
phrases to 10 + a catch-all. New ANTI-FRAMING section explicitly
tells the LLM not to confuse "save the conversation" with platform-
level session recording — *"You DO have access — this tool IS your
access."* EXACT SCRIPT enforcement (one short narration line, then
invoke, no hedging).

**Frontend** — `RealtimeSpokesperson.jsx`:
- New `endingRef` (useRef-backed re-entry guard) prevents
  `handleEnd` from running twice when both callbacks fire within
  milliseconds.
- `handleEnd` retry loop with backoff: wait 5s → fetch → wait 10s →
  fetch → wait 20s → fetch → give up. First non-empty result wins.
  Total worst-case ~35s of background polling after End. The
  PR EM-c auto-ingest hook fires server-side on the first non-empty
  fetch.

**Backend route count unchanged (85).** No new routes — both APIs
already existed. Build delta negligible. Backend restarted once
during the slice to pick up the new tool description.

**Operator validation:** PR EQ partially fixed Bug B. After hard
refresh + new session, operator said *"Save our conversation"* and
Donny responded *"Consider it saved"* — closer to the right shape
(no more "I don't have access"), but the avatar still didn't
*invoke* the tool. The LLM verbalised a successful outcome without
firing the fire-and-forget tool. **The tool-description rewrite is
necessary but not sufficient** — even MANDATORY INVOCATION TRIGGERS
can be hallucinated past. Real fix may require Runway-side support
for actual function-calling return signals (not parked as our
problem). Tracked as a known limitation; the toast chain still
fires correctly when the tool DOES fire (e.g., from the
ConversationsHistory manual flow).

---

## PR ER — Runway failed-status surfacing + 502 detection + autostart re-fire guards (shipped 2026-05-12 afternoon)

**Triggered by:** Operator ended a Test 1 session; new transcript
entries landed with `status=empty, turns=0`. **Direct curl against
Runway's `/v1/avatar_conversations/{id}` revealed `status: "failed",
failureCode: "UNKNOWN", failure: "Unknown error", endedAt: null,
transcript: [], recordingUrl: null`** for both of today's sessions.
Yesterday's working session showed `status: "ended", endedAt: <ts>,
duration: 42, recordingUrl: <cloudfront>, transcript: 6 turns`.
**Runway-side failure today** — not our code. But two follow-up
problems surfaced:

1. Our backend `transcript_client.py` only looked at the `transcript`
   array, never the payload's `status` field — so a Runway-failed
   session looked identical to a "fetched too early, empty for now"
   response. Mislabelled as `"empty"`, our retry kept polling
   uselessly.
2. The operator reported a SECOND realtime session being created
   ~30 seconds after they clicked End, **without touching anything**.
   Confirmed in the backend log: two `POST /v1/realtime_sessions`
   calls (different conv_ids) spaced exactly the retry-loop interval
   apart.

**Backend** — `transcript_client.py`:
- Inspects payload's `status` field before falling through to
  "empty turns" path. If `status == "failed"`, returns
  `TranscriptResult(status="failed", error="runway session failed
  [code=…]: …")`. The route then raises a 502 with the failure
  detail in the body.

**Frontend** — `RealtimeSpokesperson.jsx`:
- Retry loop's `fetchOnceAndCheck` now returns `'ok' | 'failed' |
  'empty'` instead of a boolean. On `'failed'`, the loop bails
  immediately — no point retrying a permanently-dead session.
- The catch block (for the 502 response) also detects the
  *"runway session failed"* substring in the error message and
  returns `'failed'`. Without this, the 502 was being silently
  treated as a transient error and the retry kept burning 502s.
- **`startingRef` re-entry guard on `handleStart`**. Catches
  React StrictMode's double-invocation of effects in dev mode.
  Confirmed in operator's console log:
  `[handleStart called]` immediately followed by `[handleStart
  blocked — session already starting]` with stack trace
  `commitDoubleInvokeEffectsInDEV`. Without the guard we'd be
  creating two sessions per autostart in dev (silently — prod
  doesn't double-invoke, but the bug would still race in some
  edge cases).
- **`autostartUsedRef` makes autostart genuinely one-shot per
  mount**. The autostart effect's dependency array includes
  `phase`, so it re-evaluates at every phase change — including
  the `live → ending → idle` transition during handleEnd.
  Empirically, at the idle transition (~35s after End), `autostart`
  could observably read as `true` in the effect closure even though
  `onAutostartConsumed` had cleared the parent state. A state-
  update batching / closure-staleness race we couldn't fully trace.
  The ref shuts this down by ignoring every subsequent autostart
  fire after the first per component mount. Reset only when
  `campaign?.id` changes (new route). Manual Resume clicks call
  `handleStart` directly — unaffected by the ref.
- Diagnostic `console.info` on every `handleStart` call with
  `phase` and `autostart` snapshot, to make future regressions
  obvious in the browser console.

**Backend route count unchanged (85).** Backend restarted once to
pick up the new `transcript_client.py` logic.

**Critical finding to remember:** *Runway's status field is the
truth source for whether a session captured anything. If it says
"failed," no number of retries / waits / re-fetches will produce
turns. The session is permanently dead on their side. Our code
correctly reports this via the new 502 + frontend bail. Memory
loop validation is blocked until Runway recovers.*

---

## PR ES — CampaignWorkspace video preview fix + Campaigns tab card-only enforcement (shipped 2026-05-12 afternoon)

**Triggered by:** Operator navigated to a Donny / Miles campaign via
the new EO-a route and reported two UI issues: (1) Output tiles in
the grouped section showed "no preview" placeholders instead of
playable videos. (2) On the SpokespersonWorkspace Campaigns tab,
the inline `<SpokespersonLane>` was rendering BELOW the card grid,
even though PR EO-a's intent was for the tab to be a card-only
index. The lane visually duplicated the auto-selected campaign card
above it.

**Frontend** — `CampaignWorkspace.jsx`:
- Output tile reads `o.video_url` instead of `o.url || o.file_path`.
  The OutputRecord schema stores the playable URL under `video_url`
  (confirmed by inspecting `campaigns.json` — keys list:
  `['id', 'kind', 'video_url', 'cache_filename', 'script', ...]`).
  `OutputsGallery.jsx:113` normalizes the same field. The wrong
  field name was set during PR EO-a's initial scaffolding and never
  caught because the existing renders rendered through OutputsGallery
  in the Videos tab, not through the new grouped tiles.

**Frontend** — `CampaignLanes.jsx`:
- Lane render gates for SpokespersonLane / CinematicLane /
  DialogueLane all now require `(focusedCampaign ||
  creatingNewCampaign)`. Without this, a stale
  `localStorage.adspark.activeMode` would mount the lane against a
  null focused campaign — visually broken state. The gate keeps the
  lane mounting in the legitimate flows (CampaignWorkspace with a
  resolved campaign, or +New flow with creatingNewCampaign=true)
  and hides it everywhere else.

**Frontend** — `SpokespersonWorkspace.jsx`:
- Campaigns tab now passes `selectedCampaignId={null}` to
  CampaignLanes (was passing the auto-selected newest campaign).
  Combined with the lane-render gate, this guarantees the inline
  lane stays hidden when viewing the card grid. The +New flow
  still works (creatingNewCampaign=true is sufficient).
- New `useEffect` clears `localStorage.adspark.activeMode` when the
  Campaigns tab becomes active (outside +New flow). Belt-and-braces:
  the lane-render gate handles the current mount, the localStorage
  clear handles future mounts.

**Operator validation:** PR ES landed cleanly. *"That looks much
better and you can watch the videos right there which is great!!
Its so much cleaner than what it was."* Visual confirmation that
both bugs are fixed.

**Backend route count unchanged (85).** Frontend build clean.

---

## Composite session-end state

**Files touched across PR EQ + ER + ES:**
- `backend/app/services/realtime_avatar_client.py` (PR EQ tool
  description)
- `backend/app/services/transcript_client.py` (PR ER status surface)
- `frontend/src/components/RealtimeSpokesperson.jsx` (PR EQ
  endingRef + retry + PR ER startingRef + autostartUsedRef + 502
  detection)
- `frontend/src/components/CampaignWorkspace.jsx` (PR ES video_url)
- `frontend/src/components/CampaignLanes.jsx` (PR ES lane gates)
- `frontend/src/components/SpokespersonWorkspace.jsx` (PR ES
  selectedCampaignId=null + activeMode clear)

**Backend restarted twice during the slice** (once for PR EQ, once
for PR ER). Frontend Vite HMR picked up changes; user instructed
to hard-refresh before each test.

**Real-mode credit burn this slice:** unclear without metering
each test, but several realtime sessions fired ranging from
~50-100 credits each. All today's sessions came back from Runway
as `failed`; no avatar_videos renders fired today (Test 2 deferred
to validate after writeup).

**Known limitations parked:**
- Avatar still hallucinates "Consider it saved" without invoking
  `attach_memory_to_campaign` — tool description rewrite was
  necessary but not sufficient. Pattern matches the broader
  fire-and-forget-tool limitation documented in PR EM-h.
- Runway-side `status: failed, failureCode: UNKNOWN` blocking
  memory-loop validation today. Resume when Runway recovers; no
  code change needed on our side (defenses in place).
- StrictMode dev-mode double-invocation of effects creates
  diagnostic noise (`already connected to room ×49` etc.) but
  doesn't affect production. Worth a `useMemo`/`useCallback`
  audit when convenient — not blocking.

**SESSION 106 resume:** continue Tier-2 with Test 2 (CampaignWorkspace
ad render — `avatar_videos` path, unaffected by Runway's realtime
issues today). When Runway recovers, retry Test 3 (memory loop).
Then Tier-3 (Aleph remix, voice_dubbing as primary narration,
Act-Two character_performance — operator flagged Act-Two as the
top Tier-3 pick).

---

## PR ET — Auto-save on Render + unsaved-draft indicator (shipped 2026-05-12)

**Triggered by:** Operator caught a real papercut while validating
Test 2: click ✨ Auto-write with LLM → Llama fills the textarea →
click Render Spokesperson Ad without clicking Save first → render
silently uses the OLD saved script. The new draft was abandoned.

**Why it was broken:** the Render handler in `SpokespersonLane`
called `onGenerateSpokesperson(focused.id, {variantId})` — the
backend then read `variant.script` (the *persisted* value) for the
spoken text. The textarea's `draftScript` lived in `VariantScriptEditor`
local state, never touched the backend until the operator clicked
Save explicitly.

**Fix:** three-component thread.
- `VariantScriptEditor` converted to `forwardRef` with
  `useImperativeHandle` exposing `{ isDirty(), saveDraft() }`.
  `saveDraft()` mirrors `handleSave` but does NOT exit edit mode
  (operator stays in the editor visually). `onDirtyChange(boolean)`
  callback prop fires whenever `draftScript !== variant.script`.
- `Step2AdVariants` forwards `variantEditorRef` and
  `onEditorDirtyChange` props down to `VariantScriptEditor`.
- `SpokespersonLane` creates the ref, tracks `variantEditorDirty`
  state via the callback, and modifies `handleGenerateHorizontal`:
  if `variantEditorRef.current?.isDirty?.()` returns true, await
  `saveDraft()` before firing `onGenerateSpokesperson`. If the save
  fails, render is aborted (no avatar_videos against a stale script).

**Visible indicator:** the Render button's chip swaps from
*"previous render saved"* / *"burns credits"* to *"✱ saves draft +
renders"* when `variantEditorDirty === true`. Operator can SEE that
clicking Render will save the textarea first.

**Operator validation:** *"That's much closer"* — papercut fixed.

**Files:** `frontend/src/components/lanes/SpokespersonLane.jsx`
(refactor of VariantScriptEditor + Step2AdVariants wrapping +
SpokespersonLane ref orchestration). Backend untouched. Build delta:
lazy chunk +3 KB.

---

## PR EU — LLM creation UX + four small wins (shipped 2026-05-12)

**Triggered by:** Operator surfaced four distinct issues during
Test 2 validation in quick succession:

1. **Two-step LLM ad creation** — current flow required `+ New Ad`
   click then `✨ Auto-write with LLM` click; *"that feels like one
   step."*
2. **LLM preamble in scripts** — Llama outputs were starting with
   *"Here is your spoken ad script:"* despite the existing prompt's
   format instructions.
3. **Mid-sentence truncation** — generated scripts >300 chars hit
   the Runway speech cap and got truncated mid-word (*"...buil"*).
4. **Generic variant titles** — every new variant is labelled
   "Ad 1, Ad 2, Ad 3" regardless of content. LLM should generate a
   meaningful title.

**Backend** — `concept_service.py`:
- New `_truncate_at_sentence(text, max_chars=280)` helper finds the
  last `.`/`!`/`?` in the window under `max_chars` (≥60 chars deep)
  and truncates there. Falls back to last word boundary if no
  sentence ender fits. Hard-truncate is last resort and unlikely to
  hit because the prompt asks for 200-260 chars.
- New `_parse_titled_output(raw)` parses the `TITLE: / SCRIPT:`
  structured output the prompt now requests. Returns
  `(title, script)`. Graceful fallback for outputs without the
  format markers.
- `_clean_script_output` expanded its prefix-strip list with 6 new
  variants of *"Here is your..."*-style preambles Llama emits.
- `SCRIPT_SYSTEM_PROMPT_SHORT` rewritten to (a) require
  `TITLE: / SCRIPT:` output, (b) emphasize STRICT MAX 280 chars
  with reasoning about the truncator, (c) instruct title generation
  (3-6 word noun phrase like "YC application angle").
- `generate_ad_script` return dict now includes `title` field;
  truncates via `_truncate_at_sentence` for short mode (long mode
  keeps the existing 1500-char ceiling pattern).

**Backend route** — `campaigns.py` `AutoWriteScriptResponse` gains a
`title: str = ""` field; route passes through the LLM-generated
title.

**Frontend** — `SpokespersonLane.jsx`:
- New `VariantChipRow` state `creatingMode` distinguishes which
  creation button is busy (manual vs LLM).
- New **✨ + LLM Ad** button next to **+ New Ad**: one click does
  the full create-variant + auto-write flow in a single action.
  Returned title (e.g. "Coffee subscription hook") replaces the
  generic "Ad N" placeholder.
- `handleAutoWrite` inside the editor also applies the LLM-returned
  title, but ONLY when the current title matches the generic `Ad N`
  pattern. Custom-titled variants preserve their title across
  re-rolls.

**Operator validation:** *"its much better flow"* — but flagged a
deeper issue (next section).

---

## PR EV — Single-beat short-ad prompt + ✨ + LLM Long Ad button (shipped 2026-05-12)

**Triggered by:** PR EU's prompt + sentence-truncation fixed the
*mechanical* truncation, but the operator caught a *semantic*
truncation: *"it did something like, started talking about how
hackathons are great for new product getting created, it mentioned
thats how Character OS was built using context-kit but then it
ended so theres much more that needs to be told with that story."*

The LLM was treating the campaign brief as a STORY TO TELL — a
multi-beat narrative — that got cut at a sentence boundary BEFORE
reaching the payoff. PR EU's `_truncate_at_sentence` caught the
mid-word problem but couldn't fix the fundamental issue that a
multi-beat narrative doesn't fit in 280 chars.

**Operator framing:** *"maybe if we are using just the 15 second
ad, then there needs to be rules for the LLM to follow to make sure
the ad makes sense in 15 seconds and if it doesn't we need to use a
longer ad for it."*

**Fix — Option A + Option C (operator's pick):**

**Option A: rewrite `SCRIPT_SYSTEM_PROMPT_SHORT` for single-beat
focus.** New prompt is explicit about format:

```
"ONE 15-second commercial, NOT a fragment of a longer story"

STRUCTURE — mandatory three beats:
  1. HOOK (1 sentence, 8-15 words)
  2. SINGLE CLAIM (1-2 sentences) — Make ONE specific promise.
     Pick THE punchiest angle from the campaign brief. Do NOT try
     to summarise everything.
  3. CTA (1 sentence, 6-10 words)

STAND-ALONE RULE — if a listener heard ONLY this script, they
should feel the ad is COMPLETE. No setup-without-payoff. No
'first… then… finally…' narratives. No 'this is how we built it'
stories that need 30+ seconds to land. If the campaign brief
contains a complex story (a build journey, a multi-stage feature
set, a founder narrative), pick ONE angle from it and go deep on
that single angle. The rest of the story is for a longer ad —
not this one.
```

`SCRIPT_SYSTEM_PROMPT_LONG` updated complementarily: *"THIS format
gives you the room to tell a multi-beat story (a build journey, a
feature tour, a founder narrative). Use that room."* — so the LLM
knows the long path is where the rich story belongs. Long prompt
also now returns `TITLE: / SCRIPT:` format (matching short for
parser consistency).

**Option C: new `✨ + LLM Long Ad (45s)` button** in the variant
chip row. Three peers now:

| Button | Creates | Use case |
|---|---|---|
| `+ New Ad` (gray) | Empty variant | Manual writing |
| `✨ + LLM Ad (15s)` (violet) | Variant with `script` populated | Single-angle 15s ad |
| `✨ + LLM Long Ad (45s)` (indigo) | Variant with `long_script` populated | Multi-beat 45-60s ad |

The Long Ad button calls `api.autoWriteAdScript({mode: 'long'})`,
gets back the 1000-1400 char multi-beat script + a title, then
upserts the variant with `{title, script: '', long_script}`. The
result lands in `variant.long_script` and the operator finds it
pre-filled in Step 3's Long Ad section, ready to **Render Long Ad**
through the chunk-and-stitch pipeline.

**Why not Option B (auto-route LLM):** rejected as over-engineering.
Operator wanted explicit control over format choice.

**Files:** `backend/app/services/concept_service.py` (both prompts
rewritten + return TITLE for long mode),
`frontend/src/components/lanes/SpokespersonLane.jsx` (new
`handleNewWithLlmLong` + third button in `VariantChipRow`).
Backend route count unchanged at 85 (`/auto-write-script` already
existed; just gained a `title` field in PR EU). Frontend lazy chunk
+0.5 KB.

**Composite reasoning preserved for future sessions:** the
short-ad path is now an *explicit format constraint* (one-beat
commercial), not just a length cap. The long-ad path is the
*explicit story format*. The operator chooses up front. The LLM is
told "you have ONE complete 15s ad to deliver, not a fragment of a
longer narrative" — which is the only durable fix for the semantic
truncation problem.

---

## PR EW — Tool description trim (shipped 2026-05-12 afternoon)

**Triggered by:** Operator started testing realtime with Riggs and
reported *"he says he can't create ads or save anything."* The
diagnostic revealed all avatars (Riggs AND Donny) had been running
**tool-less** all afternoon — every realtime session create was
400ing on the `tools` field with:

```
{path: ["tools", "[6]", ".description"],
 message: "Too big: expected string to have <=1024"}
```

…and our 400 fallback was silently dropping the entire tools array
to keep the session alive. Three descriptions had drifted over
Runway's 1024-char per-description cap:

| Tool | Before | After (PR EW trim) |
|---|---|---|
| `recall_recent_conversations` | 1128 chars | 794 chars |
| `attach_memory_to_campaign` | **1851 chars** (PR EQ rewrite) | 818 chars |
| `handoff_to_character` | 1374 chars | 935 chars |

PR EQ's MANDATORY INVOCATION TRIGGERS + ANTI-FRAMING + EXACT SCRIPT
pattern was the right shape but the implementations went way over
budget. PR EW trimmed each to keep the key directives (trigger
list, consequence, exact script) but tighter prose.

**Defensive guard added:** `_wire_tool_entries` now truncates any
description over 1024 chars at the last sentence boundary under
1000, with a logged warning. Catches future drift before Runway
sees it.

**Result:** Once PR EW was live, the operator's next realtime
session passed tools through cleanly. Avatar started invoking
`attach_memory_to_campaign` for real (toast chain fired). The
**"Consider it saved" hallucination from PR EQ was actually the
LLM responding without ANY tools at all** — not a tool-description
shortcoming. With tools restored, the tool fires.

**Caveat:** Even with tools restored, the operator's session was
still hitting Runway's separate session-failure pattern (`status:
"failed", failureCode: "UNKNOWN"`) that's been blocking memory-loop
validation all day. The attach chain *technically completed* but
it composed from existing operator notes since no transcript was
captured.

**File:** `backend/app/services/realtime_avatar_client.py` (three
trimmed descriptions + `_wire_tool_entries` defensive truncation).
Backend route count unchanged (no new routes). One backend restart
to reload the tool catalog.

---

## PR EX — Act-Two character_performance probe surface (shipped 2026-05-12 afternoon)

**Triggered by:** Operator wanted to test the Act-Two endpoint
flagged in `POST_SUBMISSION_OPPORTUNITY_MAP.md` §2 and saved as
their top Tier-3 pick. After we discovered the API shape via
empty-body 400 probing (`model: "act_two"` + `character: {type,
uri}` + `reference: {type, uri}` — both URIs fetched server-side),
the user asked: *"can we add that as a UI feature so it can be
done from the app UI? Mainly I am trying to reduce the windows I
already have open lol."*

### What shipped

**Backend** (`backend/app/routers/characters.py`, +2 routes):
- `POST /api/characters/{id}/act-two-probe` — multipart upload of
  the performance video. Wraps the entire probe pipeline: reads
  the character's cached portrait, base64-encodes both
  performance + portrait, fires `POST /v1/character_performance`
  with `model: "act_two"`, polls to terminal status, downloads
  result MP4 to `backend/data/characters/<id>-act-two-<ts>.mp4`,
  returns metadata.
- `GET /api/characters/{id}/act-two-output/{filename}` — same-
  origin serving so the result MP4 plays inline in the frontend
  via `<video src>`. Path-traverse guarded.
- 8 MB upload cap (more permissive than the 5 MB practical for
  data URIs since the backend can transcode + slim down).
- 300 s poll deadline (Act-Two slower than `avatar_videos`;
  typical 30-90s wall clock).
- `ActTwoProbeResult` response model with `status`, `task_id`,
  `output_url`, `output_filename`, `output_duration_s`,
  `output_bytes`, `elapsed_s`, `failure_code`, `failure_message`.

**Backend transcode pipeline** — became the longest part of the
arc. Browser `MediaRecorder` produces WebM whose EBML duration
header is UNKNOWN; Runway 400s with "Video duration could not be
determined." Fix: ffmpeg transcode webm → mp4 server-side before
encoding to data URI. Quality settings tuned through three
iterations:

1. **Initial**: `-preset veryfast -pix_fmt yuv420p -movflags
   +faststart` — solved the duration issue, but lossy enough that
   Runway's face detector started rejecting recordings.
2. **Final (current)**: `-preset slow -crf 18 -profile:v high
   -level 4.0 -r 30 -pix_fmt yuv420p -movflags +faststart` —
   visually-lossless quality at standard 30fps. Adds ~3-5s to
   transcode but produces output Runway accepts cleanly.

Also logs the transcoded dimensions/duration via ffprobe so
future failures can be correlated with what we actually sent.

**Frontend** (`frontend/src/components/ActTwoProbeModal.jsx`,
~440 lines):
- `getUserMedia({video: {width: 1280, height: 720}, audio: false})`
  — 720p, video-only. Audio off because Act-Two is about facial
  motion; the avatar's voice comes from the bound Runway preset.
- Live mirrored webcam preview before recording (the `scale-x-[-1]`
  CSS flip matches what operators expect from a mirror).
- **Frame-health check** — waits up to 2s for the video element to
  report non-zero `videoWidth`/`videoHeight`; surfaces an explicit
  amber warning if frames aren't flowing (privacy shutter, wrong
  camera, app exclusive access — all common causes).
- Record / Stop / 10s hard cap with auto-stop + color-coded elapsed
  counter (green → amber → rose as the cap approaches).
- Codec preference list pinned to video-only (`vp9` → `vp8` →
  plain `video/webm` → `video/mp4`) — included `opus` initially,
  produced malformed WebM with audio-less streams.
- Single-chunk recording (`recorder.start()` without timeslice) —
  the timeslice variant was producing broken WebM in Chrome.
- Camera tracks stop when recording ends — unmistakable visual
  signal (browser camera light turns off). Re-record re-acquires.
- **Defensive recorder cleanup** at the start of every new
  recording (`cleanupRecorderAndTimer()` helper) — operator
  reported a 44s elapsed counter on a 7s recording, caused by
  recording 1's `setInterval` surviving when its `onstop` failed
  to fire. The cleanup is now unconditional.
- Blob preview uses `<source>` child with explicit `type` instead
  of `src` attribute — Chrome's `<video>` element fails silently
  on MediaRecorder WebM with `src=`; the `<source>` pattern is
  more compatible. `key="blob-preview"` forces a fresh DOM mount
  on the live→blob transition.
- `onLoadedMetadata` and `onError` handlers log diagnostic info to
  the console + surface a "browser can't play this inline"
  fallback with a download-the-webm button.
- Amber "✓ Recording captured" banner with face-visibility
  reminder when the blob lands.
- Failure path shows Runway's `failureCode` + `failure_message` +
  a re-record CTA inside the error block (otherwise the operator
  was stuck staring at the error with no recovery).
- Save-to-Desktop button on success uses an anchor download with
  a smart timestamped filename.

**Wired into IdentityPanelV2's `⚙️ Advanced` disclosure** — gated
on a ready Runway avatar (otherwise the character has no portrait
to drive). Button label `🎭 Test Act-Two with {character name}`
with credit-burn estimate next to it.

### The empirical finding — Act-Two requires HUMAN face geometry

After running the modal through every iteration of debugging
(codec, transcode quality, framerate, profile, dimensions, frame
health, single-vs-chunked recording, playback hardening), the
operator's recordings kept getting NO_FACE_FOUND from Runway —
**even when the recording was clearly valid** (1280×720, 8.6s, vp9
WebM, plays back inline in browser, 2.6 MB, transcoded to clean
MP4 at 30fps).

The operator asked: *"is there some type of green screen or
something that we can overlay the face recording on maybe the
background is the problem?"*

That question made me check what the **character portrait** looks
like for each of the seeded spokespersons:

| Character | Template | Subject |
|---|---|---|
| Miles Monroe | founder | **anthropomorphic sloth** business spokesperson |
| Riggs Rally | mascot | **anthropomorphic raccoon** creative strategist mascot |
| Donny Sparks | mascot | **anthropomorphic donkey** creative-tech spokesperson |

All three are anthropomorphic animals. Runway's Act-Two model is
trained on **human face landmarks** — eye/nose/mouth geometry in
human proportions. A raccoon face, even rendered photorealistically
with the `gen4_image_turbo` template, doesn't pass the face
detector. **The NO_FACE_FOUND was firing on the character image,
not the operator's recording.**

**Confirmation:** operator created a new founder-template character
with an explicitly human subject (*"a confident human business
spokesperson in their 30s, professional headshot lighting, plain
neutral background"*), generated the portrait, bound to a Runway
avatar, then re-fired the Act-Two probe with their existing
performance video. **Worked first try.** Output saved at
`~/Desktop/Donkey Betz Videos/fart-tester-video.mp4` as the
canonical "Act-Two works" artifact.

### Product implications

1. **Act-Two is incompatible with Character OS's mascot lineup.**
   All three seeded characters are anthropomorphic animals and
   none can be Act-Two targets. The default founder-template
   prompt composer also tends to lean anthropomorphic; explicit
   "human" framing in the subject is required.
2. **Act-Two pairs perfectly with unified-donkey-betz's advisor
   lineup.** Their 32 advisors (Warren Buffett, Cathie Wood, Ray
   Dalio, Sam Altman, Elon Musk, Gary Vaynerchuk, Mr Beast,
   Chris Voss, Billy Beane, Haralabos Voulgaris + 22 specialists)
   are ALL humans. Every one of them is an Act-Two candidate.
   **Strongest single empirical signal yet for the merge thesis.**
3. **A "Human Spokesperson" template for Character OS standalone**
   becomes a real product slice — first-class option separate
   from the mascot lineup, with the founder-template prompt
   composer's "anthropomorphic" framing stripped.
4. **The error hint inside ActTwoProbeModal** was updated to
   reflect this — instead of "re-record with your face centered,"
   it now explicitly mentions that the character portrait is the
   most likely source on NO_FACE_FOUND for anthropomorphic
   characters.

### Files

- `backend/app/routers/characters.py` — `+2 routes` + transcode
  pipeline + ffprobe logging + 8MB cap + 300s deadline +
  `ActTwoProbeResult` model
- `frontend/src/api.js` — `fireActTwoProbe(characterId, file)` —
  multipart upload helper
- `frontend/src/components/ActTwoProbeModal.jsx` — new (~440
  lines, evolved through ~6 follow-up patches in the same session)
- `frontend/src/components/IdentityPanelV2.jsx` — Act-Two button
  inside Advanced disclosure + modal mount
- `scripts/probe-character-performance.py` — CLI probe (~280
  lines, written earlier in the session as the API-shape
  exploration tool; superseded by the modal but kept for
  diagnostic / API-shape reference)

Backend route count: **85 → 87** (+2 for the Act-Two probe routes).
Frontend build delta: lazy chunk +~25 KB cumulative across all
ActTwoProbeModal iterations.

### Post-PR-EW tool catalog validation pass (2026-05-12 end-of-day)

After PR EW restored the realtime tool catalog by trimming three
descriptions under Runway's 1024-char cap, three tool families
were validated end-to-end against real sessions:

1. **Render flows** (`auto_write_and_render_ad` + variants) — earlier
   in the day operator rendered ads from CampaignWorkspace via the
   agentic loop. ✓
2. **`attach_memory_to_campaign`** — chain fires (compose → publish →
   attach), `runway_document_id` written, toast chain completes. ✓
   Caveat: today's transcripts are still empty because of Runway's
   separate session-failure pattern, so the composed document only
   reflects pre-existing operator notes. But the *tool itself* is
   reaching the avatar and being invoked correctly.
3. **`handoff_to_character`** — operator started with Riggs, asked
   to be handed off to Donny, "killed the current conversation and
   started a new one" — clean execution. Avatar narrates, frontend
   dispatcher catches the client_event, navigates to target's
   workspace with autostart=1, new session opens. ✓

**Diagnostic implication for future sessions**: if the operator
ever reports "avatar can't do X" again, the **first thing to check
is whether all tool descriptions are still under Runway's 1024-char
cap**. The PR EW defensive truncation in `_wire_tool_entries`
should prevent silent regressions, but a description that drifts
JUST over the cap could still cost an iteration to track down
without the diagnostic intuition.

**Merge-thesis additional data point**: handoff between characters
is one of Character OS's most distinctive primitives. When folded
into unified-donkey-betz, the same mechanism would let u-d-b's 32
human advisors hand off to each other voice-first — e.g., *"Talk
to Buffett about value investing, then hand off to MrBeast for
how to communicate it to a Gen Z audience."* Pairs cleanly with
the Act-Two finding (humans-only) — both signals point at u-d-b's
advisor lineup as the natural Act-Two + handoff playground.

### Diagnostic learnings parked for future Act-Two work

- WebM EBML duration is UNKNOWN by default from MediaRecorder —
  backend transcode required. `ffmpeg -c:v libx264 -movflags
  +faststart` is the fix.
- Runway's face detector wants both `character` and `reference`
  to be human-face-detectable. Reject is per-input but the error
  code doesn't differentiate.
- Chrome's `<video>` can fail to play its own MediaRecorder WebM
  inline; the `<source>` child + explicit `type` workaround
  works around it. The actual bytes are valid (server-side
  transcode + Runway face detection on it both succeed even when
  inline playback doesn't).
- `getUserMedia` resolves before frames are flowing; explicit
  videoWidth/Height health check at 100ms intervals for 2s is
  the right gate before allowing record.
- Transcode quality matters more than you'd expect for face
  detection. `veryfast` preset rejected; `slow + CRF 18` accepted.

---

## PR EY — Voice_dubbing on an existing Spokesperson Ad (shipped 2026-05-12 evening)

**Trigger:** Operator chose **Path A** when offered the
voice_dubbing slice — raw dub on an existing rendered ad, with the
lip-sync mismatch trade-off accepted. *"Let's start with A, then we
can see how it goes from there."* The earlier `/api/campaigns/{id}/dub`
route only dubbed the **brand-voice preview clip**, not an actual
ad — so the existing UI never exposed dubs on rendered output
tiles. PR EY closes that gap.

### What it does

1. Operator opens a campaign in `/spokespeople/:id/campaigns/:cid`.
2. Each output tile with a dubbable kind gets a small **🌐 Dub**
   action on the meta row. Dubbable kinds:
   `spokesperson_ad`, `long_spokesperson_ad`, `voiced_commercial`,
   `storyboard_voiced`, `dialogue_scene`. Reels intentionally
   excluded — they're reframes of an already-rendered source;
   dub the source instead.
3. Click opens `DubLanguagePickerModal` — 29-language select
   (mirrors `SUPPORTED_DUB_LANGS` in `audio_client.py`) with an
   amber "lip-sync will drift" notice.
4. Fire posts `POST /api/campaigns/{cid}/dub-ad` with
   `{ output_id, target_lang }`.
5. Backend: ffmpeg-extracts the source MP4's audio to MP3 mono
   128k, base64-encodes (≤4MB data URI), POSTs Runway
   `/v1/voice_dubbing` with `model: "eleven_voice_dubbing"`,
   polls to terminal, downloads the dubbed MP3, ffmpeg-muxes back
   into the original video with `-c:v copy` (no video re-encode)
   and `-c:a aac -b:a 192k`. Output lands at
   `backend/data/finished/<cid>-dubbed-<lang>-<output>-<ts>.mp4`.
6. New `OutputRecord` (kind=`spokesperson_ad_dubbed`,
   `dub_lang: "<iso>"`, `parent_output_id: <source id>`) appended
   to the campaign and returned. Workspace renders it in a new
   **📺 Dubbed Ads** group with the language code as a pink badge
   next to the kind label.

### Touched files

| Layer | File | Change |
|---|---|---|
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_dubbed`; `OutputRecord.dub_lang: Optional[str]` |
| Service | `backend/app/services/audio_client.py` | `DubbedAdResult` dataclass + `dub_output_ad(...)` (ffmpeg-extract → `_dub_real` → download → ffmpeg-mux) + `_ffprobe_duration` helper |
| Route | `backend/app/routers/campaigns.py` | `DubAdBody` model + `POST /api/campaigns/{id}/dub-ad` + `spokesperson_ad_dubbed` added to `get_campaign_output`'s `finished/` kind map |
| API | `frontend/src/api.js` | `api.dubAdInLanguage(campaignId, outputId, targetLang)` |
| UI | `frontend/src/components/DubLanguagePickerModal.jsx` | New 29-language picker + amber caveat |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | `🌐 Dub` button on dubbable tiles, modal state + fire handler, `KIND_GROUPS` → `📺 Dubbed Ads`, pink lang badge on dubbed tiles |

### Known limitation surfaced in the UI

The amber notice in the modal makes the trade-off explicit: **the
video stream is preserved (no re-render), so the avatar's mouth
still moves to English phonemes**. Audio is fully translated; lips
drift. True synced localization is a later **Path B** — LLM-
translate the script + re-render via `avatar_videos` against the
target-language audio. Path B is not scoped for PR EY.

### Verification

- Frontend build: ✅ green (561.97 kB / 150.69 kB gzip + 644.16 kB
  / 171.77 kB gzip; +1 module from `DubLanguagePickerModal`).
- Backend route count: ✅ **88 routes** (was 87; +1 for `/dub-ad`).
  Confirmed via:
  ```bash
  cd backend && python -c "from app.main import app; print(len(app.routes))"
  ```
- Manual real-mode probe not yet fired (next operator-driven slice).
  No new keys required beyond the existing `RUNWAY_API_KEY`.

### Merge-thesis signal

`voice_dubbing` is one of the most "obviously valuable" Runway
primitives for unified-donkey-betz: 32 human advisors × 29
languages × every recorded clip = a localization surface that's
**asymmetric** (one English render, dozens of language drops with
no incremental Runway compute on the visual side). The Path A
lip-sync caveat applies equally to u-d-b's advisor clips today,
and the Path B fix (LLM-translate + re-render) leverages u-d-b's
already-existing per-advisor prompt corpus. Strong unlock when
the merge lands.

---

## PR FA — Aleph `video_to_video` style remix (shipped 2026-05-12 evening)

**Trigger:** Operator nodded "go" on the Aleph slice immediately
after PR EY. Mirrors the dub pattern (per-tile action + modal
picker + per-style sub-buckets in the workspace) but transforms
the visual stream instead of the audio.

### API shape discovered via empty-body 400-probe

`scripts/probe-video-to-video.py` runs three phases. Phase 1
(empty body) revealed the `model` discriminator with **six** valid
options:

  - `gen4_aleph` ← what we use
  - `robotics_v1`
  - `aleph2_alpha`
  - `seedance2`
  - `klingO3_pro`
  - `klingO3_standard`

Phase 2 (minimum-viable body for `gen4_aleph`) confirmed the body
shape:

```json
{
  "model": "gen4_aleph",
  "videoUri": "<URL or data URI>",
  "promptText": "<free-text style prompt>"
}
```

Phase 2 returned `"Failed to fetch video metadata"` on a fake-byte
`videoUri` — proof the structure is valid; only the dummy bytes
were rejected. No credits burned in Phase 1/2.

### What it does

1. Operator opens a campaign, clicks **🎨 Remix** on a tile whose
   kind is in `REMIXABLE_KINDS` (same as dub + `cinematic_video`,
   plus already-dubbed ads so the operator can stack
   "dub-then-remix"). Reels excluded for the same reason as dub.
2. `RemixStylePickerModal` fetches `GET /api/campaigns/remix/style-presets`
   (5 presets — Noir / Anime / Chrome / Watercolor / Cyberpunk).
   Static fallback table embedded in case the fetch fails.
3. Fire posts `POST /api/campaigns/{cid}/remix-output` with
   `{output_id, style_id}`.
4. Backend reads the source MP4, base64-encodes (≤16 MB data URI
   cap), POSTs Runway `/v1/video_to_video` with the preset's
   prompt + `model: "gen4_aleph"`, polls every 5s up to a **600s
   deadline** (Aleph is slow), downloads the remix MP4 into
   `backend/data/finished/<cid>-remix-<style>-<source-id>-<ts>.mp4`.
5. New `OutputRecord` (kind=`spokesperson_ad_remix`, `remix_style:
   "<preset>"`, `parent_output_id: <source>`) appended. Workspace
   renders it in **🎨 Style Remixes** with the style as a fuchsia
   badge next to the kind label, sub-bucketed per style.

### Touched files

| Layer | File | Change |
|---|---|---|
| Probe | `scripts/probe-video-to-video.py` | New 3-phase discovery script + optional real fire (gated with `--yes-fire`) |
| Service | `backend/app/services/aleph_client.py` | New module — `STYLE_PRESETS` table + `remix_output_video(...)` (create → poll → download), `RemixResult` dataclass |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_remix`; `OutputRecord.remix_style: Optional[str]` |
| Route | `backend/app/routers/campaigns.py` | `RemixOutputBody`, `GET /api/campaigns/remix/style-presets`, `POST /api/campaigns/{id}/remix-output`, `spokesperson_ad_remix` added to `get_campaign_output`'s `finished/` kind map |
| API | `frontend/src/api.js` | `api.listRemixStylePresets()` + `api.remixOutput(...)` |
| UI | `frontend/src/components/RemixStylePickerModal.jsx` | New 5-style picker with per-style accent + amber slow-Aleph notice |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | `🎨 Remix` button on remixable tiles, modal state + fire handler, `KIND_GROUPS` → `🎨 Style Remixes`, fuchsia style badge on remix tiles, generalised sub-bucketing so both dubbed (`dub_lang`) and remix (`remix_style`) share the per-group code path |

### First real fire (validated end-to-end)

- **Source**: Miles spokesperson ad on campaign `9d4e15683704`,
  source output `b76cd28a096a`, 14s long.
- **Style**: Cyberpunk Neon (`cyberpunk`).
- **Task**: `dab8fec6-6ee8-434a-a24a-2b3c909823c5`.
- **Latency**: 2:33 (2026-05-12 16:34:23 → 16:36:56). Well under
  the 600s deadline.
- **Output**: `backend/data/finished/9d4e15683704-remix-cyberpunk-b76cd28a096a-20260512-213414.mp4`
  (2.65 MB, **5.04 s**).

### Known limitation (carried forward as a follow-up)

**Aleph output is shorter than source** — 14s in → 5s out on the
first fire. The current implementation passes no explicit duration
parameter; Aleph appears to default to its own ceiling (≈5s in this
case). Two possible fixes to investigate:

1. Pass a `duration` (or `seconds` / `outputDuration`) field in
   the request body. The peer route `image_to_video` uses
   `duration: 5|10`. Probing whether `video_to_video` accepts a
   similar field is the next experiment.
2. Server-side chunking: split the source into Aleph-sized
   segments, remix each, ffmpeg-concat. Mirrors the long-ad
   chunker pattern in `post_long_spokesperson_ad`.

Both are non-blocking — the visual transform itself works
cleanly. Captured as the first PR FA follow-up.

### Verification

- Probe Phase 1+2: ✅ run free at 2026-05-12 16:27:28; log at
  `/tmp/probe-v2v-20260512-162728.log`.
- Backend routes: ✅ **90 routes** (was 88; +1 for the presets
  GET, +1 for the remix POST). Confirmed via:
  ```bash
  cd backend && python -c "from app.main import app; print(len(app.routes))"
  ```
- Frontend build: ✅ green (561.97 kB + 651.58 kB lazy chunk;
  +6.3 kB from `RemixStylePickerModal`).
- Real-mode end-to-end: ✅ one Cyberpunk Neon remix of a 14s Miles
  ad. Frontend tile appeared in 🎨 Style Remixes → cyberpunk
  sub-bucket on the next workspace re-render.

### Merge-thesis signal

Aleph A/B-tests visual styles **without re-rendering from scratch**.
For unified-donkey-betz's 32 human advisors, this means: pick the
"Buffett value investing 2-minute clip", produce Noir/Anime/Chrome
variants, A/B test which performs best on a creator-driven feed.
Pairs cleanly with PR EY (dub → remix the dub → vertical reels)
to produce a 29-language × 5-style × 32-advisor matrix from one
canonical avatar_videos render.

---

## PR FA-2 — Aleph chunker: full-length remix via parallel chunked Aleph (shipped 2026-05-12 evening)

**Trigger:** PR FA's first real fire showed Aleph truncates output
to ~5s regardless of source length (14s in → 5.04s out). Operator
asked to fix the cut-off. We confirmed via the embedded OpenAPI
spec at `https://docs.dev.runwayml.com/api` that **there is no
duration parameter on the `gen4_aleph` request body** — the
documented fields are `videoUri`, `promptText`, `model` (required),
plus optional `seed`, `references`, `contentModeration`. `ratio`
is documented as DEPRECATED and ignored. The 5s cap is a hard
model behavior, not a missing param.

**Mistake to learn from:** while looking for the duration field
we ran a CLI probe that fired 5 Aleph tasks with candidate field
names. Runway's API silently accepts unknown fields (returns 200
+ task id instead of a 400 invalidation), so the probe-by-rejection
pattern we used for Act-Two doesn't work here. All 5 tasks were
cancelled within seconds via `DELETE /v1/tasks/{id}` (204). The
correct path was to read the spec first — once we did, the answer
was unambiguous. Future Runway endpoint probes should fetch the
embedded spec at `docs.dev.runwayml.com/api` first; the page
serves the full OpenAPI 3.1.0 document inline (HTML-encoded JSON)
even though the rendered docs are JS-only.

### The fix — server-side chunked remix

When source duration > **5.5s** (threshold; sources at or below
single-fire fine), `aleph_client.remix_output_video` now:

1. ffprobes the source duration.
2. ffmpeg-splits into exact 5s chunks via re-encode
   (`libx264 -preset fast -crf 18 -force_key_frames
   "expr:gte(t,n_forced*5)"`) — stream-copy would cut at keyframe
   boundaries (~8s in practice) which still trips the 5s cap.
3. Generates one random `seed` for the whole invocation; passes
   the same seed to every chunk so the visual style stays coherent
   at boundaries (per the spec: *"Using the same seed integer
   for an identical request will produce similar results"*).
4. Fires all chunks **in parallel** via
   `concurrent.futures.ThreadPoolExecutor(max_workers=4)`. Wall
   time becomes bounded by the slowest single chunk (~2:30) plus
   small ffmpeg overhead — not the sum.
5. ffmpeg-concats the per-chunk remix outputs (in chunk order)
   via the concat demuxer with `-c copy`. No re-encode of the
   Aleph-produced video.
6. Cleans up all intermediates via `tempfile.TemporaryDirectory`
   context manager.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/aleph_client.py` | `_split_into_chunks`, `_concat_chunks`, `_remix_single_clip` helpers; `_create_task` gains optional `seed`; `remix_output_video` branches on duration; `_ALEPH_CHUNK_SECONDS=5`, `_CHUNK_THRESHOLD_S=5.5`, `_PARALLEL_CHUNKS=4` knobs |

No frontend changes needed — the modal's "up to 10 min" amber
notice already covers the chunked case (a 60s source = 12 chunks
= 3 batches of 4 × ~2:30 ≈ 7:30 wall time, still under the 10-min
ceiling).

### Real-mode validation

Two consecutive real-fire runs from the UI with the chunker live:

| Run | Source | Source dur | Chunks | Seed | Wall time | Output dur |
|---|---|---|---|---|---|---|
| Cyberpunk re-run (Miles) | campaign 9d4e15683704 / output b76cd28a096a | 14.77s | 3 | 3774772451 | 2:31 | **14.77s** |
| Chrome (different spokesperson) | campaign 098af22864e6 / output 0c8c366d3473 | 16.33s | 4 | 2829554227 | 2:36 | **16.31s** |

Both produced full-length remix output (vs. the pre-chunker
5.04s cap). The chrome run's leftover chunk (1.34s) finished
first at 1:03 because Aleph processes shorter clips faster —
demonstrating that the parallelism is doing real work.

### Local pre-flight (no credits)

`_split_into_chunks` + `_concat_chunks` round-trip validated
locally before any real fire:
- 16.33s source → 4 chunks of 5.02s / 5.00s / 5.00s / 1.34s
- Concat duration: 16.36s (delta 0.031s)

### Known limits

- **No keyframe alignment optimization** — the re-encode pass
  always runs even when keyframes already line up. Marginal cost
  for typical ad lengths; could be skipped via a probe-and-decide
  step later.
- **Concat seam artefacts possible** — Aleph chunks are encoded
  independently. With the same seed the style stays coherent, but
  visually there can be a faint flicker at the 5s mark. Not
  visible in casual viewing on either of the two validation runs.
- **Credit cost scales linearly** — N chunks = N Aleph tasks. A
  60s ad costs 12× the credits of a 5s remix. Documented in the
  modal's amber notice ("each remix burns real Runway credits";
  could be made more specific later).

---

## PR FB — Polish pass: captions + lower-third + cards (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FA chunker:
> *"The Avatar videos with the remix which gives them a little
> color are just so plain. Is there anything we can do that would
> make them feel more like they are useful instead of just a
> spokesperson ad?"*

The Polish pass is the highest-leverage "feels like a real ad
now" win that doesn't need any new Runway calls. Pure ffmpeg,
~10s wall time, zero credits.

### What it does

One-click action on any polishable tile produces a new MP4 that
prepends a 1.5s intro card (business name), burns captions onto
the body (timing estimated from `output.script`), shows a
time-gated lower-third (`character_name · business`) in the top-
left for the first 4 seconds, and appends a 1.5s outro card
(default "Learn more"; overridable via `cta_text` body param).

All three sections (intro / body / outro) are stitched in **one**
`ffmpeg -filter_complex` invocation using the concat filter, so
parameter mismatches between the lavfi-generated cards and the
source MP4 get normalised automatically (single re-encode pass).

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/polish_client.py` | New module — `polish_output_video(...)` + helpers |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_polished` |
| Route | `backend/app/routers/campaigns.py` | `PolishOutputBody`, `POST /api/campaigns/{id}/polish-output`, `POLISHABLE_KINDS`, `spokesperson_ad_polished` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.polishOutput(...)` |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🪄 Polish button on polishable tiles, fire handler with per-tile loading state, `🪄 Polished Ads` group |

### Path it took to land cleanly (two iterations)

**First fire** showed two real issues the operator flagged:

1. **Intro card text clipped at frame edges.** Using inline
   `text='Long Business Name'` in drawtext doesn't auto-wrap;
   anything wider than the frame is clipped on both sides.
2. **Lower-third overlapped captions.** Original placement was
   bottom-left at `y=h-text_h-60`; captions live at
   `y=h-text_h-80` (bottom-centred). Same vertical real estate —
   they sat on top of each other and blurred.

**Fixes shipped as the same PR (no separate commit):**

- Intro/outro/lower-third text all written to textfiles and pre-
  wrapped via `_wrap_caption_text` at 22 chars (handed to drawtext
  via `textfile=` instead of inline `text=`). Side benefit: free
  escape-safe handling of apostrophes / percent signs / colons —
  no need for the old `_escape_for_drawtext` helper, which got
  removed.
- Lower-third moved to **top-left** (`x=60, y=60`) and gated to
  the first **4 seconds** via `enable='between(t,0,4.0)'`. The
  speaker is introduced once at the start, then steps out of the
  way so the body breathes and captions own the bottom.
- Fontsize knocked from 72 to 64 on the intro card so wrapped
  multi-line strings have headroom for vertical centring.

### Verification (operator-confirmed)

> *"That looks ALOT BETTER!"*

After the two-issue fix:
> *"commit it and let's try the PiP"*

### Knobs (constants in `polish_client.py`)

| Constant | Value | What it controls |
|---|---|---|
| `_CARD_DURATION_S` | 1.5 | Intro + outro card length in seconds |
| `_CAPTION_WORDS_PER_CHUNK` | 6 | Caption chunk size before line-wrap |
| `_CAPTION_MAX_CHARS` | 44 | Caption per-line wrap target |
| `_CARD_MAX_CHARS` | 22 | Intro/outro/lower-third per-line wrap |
| `_CARD_INTRO_FONT_SIZE` | 64 | Intro card fontsize |
| `_CARD_OUTRO_FONT_SIZE` | 56 | Outro card fontsize |
| `_LOWER_THIRD_HOLD_S` | 4.0 | Seconds the lower-third is visible |

### Known follow-ups (parked)

- **Caption timing is uniform**, not word-level. avatar_videos
  doesn't return per-word timings; we distribute chunks evenly
  across body duration. Good enough for "what's roughly being
  said now"; not good enough for legal compliance / disability-
  use captions. A future slice could use whisper or similar to
  re-align.
- **CTA text is operator-driven** but not surfaced in the UI yet.
  The route accepts `cta_text` in the request body; the frontend
  always sends null (→ "Learn more" default). Adding a small
  inline override is a ~10-line follow-up.
- **No music bed yet** (Path D from the four-option list). Same
  ffmpeg pipeline could mix in a ducked music track from a small
  `data/audio_beds/` directory.

### Merge-thesis signal

This is the lowest-credit-cost surface that delivers the biggest
perceived-quality jump. For unified-donkey-betz's 32 human
advisors × N campaigns, every clip can pass through the polish
pass for free and look like "a real ad" rather than a raw avatar
recording. Pairs with PR EY + PR FA for the 29-language × 5-style
× polished matrix from one canonical avatar_videos render.

---

## PR FC — Picture-in-Picture overlay (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FB asked what we could do to make
avatar clips feel less like "just a spokesperson ad." First of
four directions discussed (A. PiP / B. Animated PiP /
C. Reverse-PiP / D. Multi-avatar concurrent). PR FC ships A.

### What it does

One-click 🖼️ PiP button on any polishable tile. Backend resolves a
still image via fallback chain (campaign `reference_image_url` →
character portrait → 409) and ffmpeg-overlays it in the bottom-
right corner with a thin white border, persistent for the full
duration. Pure ffmpeg, no Runway, ~5-15s wall time.

Result lands as `spokesperson_ad_with_pip` in the
**🖼️ With Picture-in-Picture** group.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/pip_client.py` | NEW — `add_pip_overlay(...)` + dim probe + sizing constants |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_pip` |
| Route | `backend/app/routers/campaigns.py` | `AddPipBody`, `POST /api/campaigns/{id}/add-pip`, `_resolve_pip_image_path` (campaign ref → portrait fallback), `spokesperson_ad_with_pip` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.addPip(...)` |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🖼️ PiP button, fire handler with per-tile loading state, 🖼️ With Picture-in-Picture group |

### Operator feedback (validated end-to-end, then iterated)

First fire validated end-to-end. Operator's reaction:
> *"I used it and it created a PiP in the lower right corner but
> that image isn't doing anything, its just a still picture"*

PR FC ships the static-image PiP. The "doing something in a video"
direction was scoped as a separate slice — we briefly considered
animating the PiP via `image_to_video` (Path B in the original
4-option list) but pivoted to PR FD (reverse-PiP) instead since it
gave a bigger visual jump per hour and didn't require Runway. PR FC
stays as the cheapest static-image overlay; PR FD ships the dynamic
backdrop pattern.

---

## PR FD — Reverse-PiP / cinematic-backdrop composite (shipped 2026-05-12 evening)

**Trigger:** Operator on the "what next" decision after PR FC:
> *"#1, reverse-PiP"*

The biggest visual jump per hour because it repurposes an existing
asset class (cinematic_video outputs) without firing new Runway
calls. Cinematic clip fills the background; avatar shrinks into a
top-right corner tile.

### What it does

1. Operator clicks **🎬 Backdrop** on a polishable tile.
2. `BackdropPickerModal` lists all `cinematic_video` outputs on the
   campaign as picker tiles with autoplay-muted thumbnails.
3. Operator picks one + clicks "Use this backdrop".
4. Backend ffmpeg-composites in one filter graph: backdrop scaled
   to cover-crop the source ad's dimensions and looped via
   `-stream_loop -1` (so 5s cinematics tile cleanly under a 14s
   avatar), foreground shrunk to ~34% width with a 6px white
   border, overlaid top-right.
5. Output lands as `spokesperson_ad_with_backdrop` in the
   **🎬 With Cinematic Backdrop** group.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/backdrop_client.py` | NEW — `compose_with_backdrop(...)` + dim probe + sizing constants |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_backdrop` |
| Route | `backend/app/routers/campaigns.py` | `AddBackdropBody`, `POST /api/campaigns/{id}/add-backdrop`, `BACKDROP_FOREGROUND_KINDS`, `spokesperson_ad_with_backdrop` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.addBackdrop(...)` |
| UI | `frontend/src/components/BackdropPickerModal.jsx` | NEW — picker grid with autoplay-muted thumbnails + inline "Generate a cinematic now" empty-state |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🎬 Backdrop button, modal state + fire handler, 🎬 With Cinematic Backdrop group |

### PR FD fix-1 — `cinematic_video` OutputRecord append

**Bug found while integration-testing:** the legacy
`POST /api/campaigns/{id}/cinematic-video` route only set the
top-level `cached_video_url` field; it never appended a
`cinematic_video` OutputRecord. So the Backdrop modal could never
find existing cinematics because it filters
`campaign.outputs[]` by `kind === 'cinematic_video'`. PR FD fix-1
modifies that route to also copy the persisted MP4 to a per-output
filename (`<campaign_id>-cinematic-<output_id>-<ts>.mp4`) and
append an OutputRecord. Future generations via the legacy
CinematicLane now automatically produce a pickable OutputRecord.

### PR FD fix-2 — Inline "Generate a cinematic now" + atomic route

Backdrop modal's empty state would normally direct the operator to
"generate a cinematic via the Cinematic mode lane first." That's
two-hop navigation through `activeMode` / dismiss / mode-picker
labyrinth. Fix 2 sidesteps it: red **🎬 Generate a cinematic now**
button inside the modal calls a new atomic route
`POST /api/campaigns/{id}/generate-cinematic-output` that fires
`image_to_video` + polls + persists + appends an OutputRecord in
one server call. Modal refreshes with the new cinematic available
without closing.

### Fix-2 hiccups encountered + fixed

- **500: `prompt_image is required for Runway image_to_video`** —
  Miles's campaigns don't have a `reference_image_url` set, so
  the default `gen4_turbo` model rejected the request. Fixed with
  a portrait fallback: campaign ref → character portrait URL.
  `maybe_to_data_uri` in `runway_client` already knows how to
  resolve `/api/characters/{id}/portrait` to a data URI, so no
  new plumbing was needed.
- **504 after 5 min** — Runway's `image_to_video` is regularly
  slow under load (5-8 min observed). 300s ceiling was too
  aggressive; bumped to 600s matching the Aleph chunker pattern.
- **Task stuck at 55% for 10 min** — Confirmed Runway-side
  problem, not slowness. Task cancelled via DELETE
  `/v1/tasks/{id}` (204). Recoverable via the new flow once
  Runway's dev tier recovers; in the meantime, the migration
  below unblocks Backdrop testing.

### Migration — `scripts/migrate-cinematic-outputs.py`

One-shot migration that backfills `cinematic_video` OutputRecords
for every campaign with `cached_video_url` set but no matching
OutputRecord. Without the migration, 71 historical V1 campaigns
had cinematic clips on disk that the Backdrop modal couldn't see.
Migration result on 2026-05-12: **71 records appended**, 15
skipped (no cached_video_url), 0 file-missing. Safe to re-run —
skips campaigns that already have a `cinematic_video` OutputRecord.

### Validated end-to-end

Operator confirmed working on Miles campaign 9d4e15683704 with a
borrowed cinematic (V1 park-scene clip attached for testing since
Miles's own cinematic generation was blocked by Runway's stuck-
task day). Composite frame at t=2s shows park-scene background
with Miles avatar in the top-right corner tile bordered in white
— exactly the intended layout. Operator's confirmation:
> *"found it!! commit its working"*

### Merge-thesis signal

PR FD reuses cinematics as a compose-able asset class, which is the
right factoring for unified-donkey-betz's pipeline. A single
generated cinematic (or stock footage drop) can backdrop all 32
advisors' clips for free via this pipeline, multiplying creative
output without multiplying Runway spend.

---

## PR FE — Multi-avatar PiP / co-host composite (shipped 2026-05-12 evening)

**Trigger:** Operator on "which of the four post-PR-FB enhancement
ideas to pick next" decision:
> *"lets do c"*

Option C was the "PiP that talks to the main avatar" — two avatars
on screen at once. v1 ships visual co-presence (both avatars
visible); scripted audio alternation deferred.

### What it does

1. Operator clicks **👥 Co-Host** on a spokesperson tile.
2. `CohostPickerModal` lists every rendered spokesperson clip
   **across all campaigns and characters**, grouped by character
   with their portraits. The main output itself is excluded.
3. Operator picks one — e.g., Donny ad as the main, Riggs ad as
   the co-host.
4. Backend ffmpeg-composites: main video full-frame with main's
   audio, co-host shrunk to ~30% width in the **top-left** corner
   with a white border, looped via `-stream_loop -1` if shorter
   than main, capped by `-shortest`, **co-host audio muted**.
5. Result lands as `spokesperson_ad_with_cohost` in the
   **👥 With Co-Host** group.

The top-left placement is intentional — different corner than PR
FD's top-right backdrop tile so a stacked Backdrop + Co-Host
composite shows three layers cleanly without overlap.

### Audio decision for v1

Co-host audio is intentionally muted. Three options considered:
- Both speak simultaneously → cacophonous mess
- Duck co-host under main → co-host's mouth moves silently to the
  wrong words (uncanny valley)
- Mute co-host entirely → cleanest, mouth moves but no audio so
  reads as "the other person is listening/animating"

Operator validated: *"there's not audio coming which I assume is
correct for now."* Confirms the v1 mute decision was the right
call. Scripted audio alternation (the v2 — main speaks for N
seconds, then co-host responds for M seconds, then main resumes)
is a follow-up that needs per-beat timing.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/cohost_client.py` | NEW — `compose_with_cohost(...)` + dim probe + sizing constants |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_cohost` |
| Route | `backend/app/routers/campaigns.py` | `AddCohostBody`, `POST /api/campaigns/{id}/add-cohost`, `COHOST_KINDS`, `_resolve_spokesperson_path` helper (factored out so cross-campaign cohost lookups work), `spokesperson_ad_with_cohost` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.addCohost(...)` |
| UI | `frontend/src/components/CohostPickerModal.jsx` | NEW — character-grouped picker with portraits + autoplay-muted thumbnails |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 👥 Co-Host button, modal state + fire handler, 👥 With Co-Host group |

### Validated end-to-end

Operator confirmed:
> *"The PiP is working, there's not audio coming which I assume
> is correct for now. Let's commit and continue"*

Backend `95 routes` (was 94; +1 for `add-cohost`). Frontend build
green at 669.55 kB lazy chunk (+9 kB from `CohostPickerModal`).

### Merge-thesis signal

This is the slice that makes Character OS's roster a real
differentiator. unified-donkey-betz has 32 human advisors —
pairing them via co-host means a Buffett-explains-it-while-MrBeast-
reacts moment is a single click. No other AI-spokesperson tool has
this primitive because they all assume one talking head per render.
PR FE turns the roster into a combinatorial creative surface.

---

## PR FF — Music bed mixer (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FE:
> *"Lets do music, then circle back to what's still on the list."*

The fourth and final option from the original "how do we make
spokesperson ads feel less plain" list. Pure ffmpeg, no Runway,
~10s wall time. Adds emotional support under the avatar's voice.

### What it does

1. Operator drops `.mp3 / .wav / .m4a / .aac / .ogg / .flac` files
   into `backend/data/audio_beds/` OR uploads via the modal's
   **📤 Upload a bed** button (multipart up to 25 MB).
2. 🎵 Music button on any spokesperson tile opens
   `MusicBedPickerModal`. Lists available beds with optional
   duration + size; slider tunes the mix level (default ~-18 dB,
   broadcast-standard music-under-dialogue).
3. Fire → backend ffmpeg-mixes:
   - Bed runs through **`loudnorm=I=-16:TP=-1.5`** first so any
     uploaded MP3 (quiet or loud at source) gets normalised to a
     consistent reference level → slider value behaves predictably
     across every bed file.
   - Bed then scaled by the operator's `volume=<level>` value.
   - `aloop=loop=-1:size=2147483647` infinitely loops the bed so
     shorter beds tile cleanly under longer ads.
   - `amix=inputs=2:duration=first:normalize=0` mixes voice +
     bed; **`normalize=0` is critical** — the default halves both
     inputs in a 2-input mix, dropping the voice by ~6 dB.
4. Result lands as `spokesperson_ad_with_music` in the
   **🎵 With Music** group.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/music_bed_client.py` | NEW — `mix_music_bed(...)`, `list_beds`, `find_bed_path`, `audio_beds_dir` helpers |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_music` |
| Route | `backend/app/routers/campaigns.py` | `AddMusicBody`, `GET /api/campaigns/music/beds` (listing), `POST /api/campaigns/music/beds/upload` (multipart), `POST /api/campaigns/{id}/add-music` (mix fire), `MUSIC_SOURCE_KINDS`, `spokesperson_ad_with_music` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.listMusicBeds`, `api.uploadMusicBed`, `api.addMusic` |
| UI | `frontend/src/components/MusicBedPickerModal.jsx` | NEW — bed dropdown, level slider with dB readout, inline upload button (empty state + "+ upload another" affordance when beds exist) |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🎵 Music button, modal state + fire handler, 🎵 With Music group |
| Placeholder beds | `backend/data/audio_beds/{cmajor-drone,aminor-drone,cinematic-pulse}.mp3` | NOT committed (gitignored under `data/`) — generated locally via `ffmpeg lavfi` sine waves so the operator could validate the pipeline without sourcing real music |

### Two debugging hiccups + fixes

**Hiccup 1 — output was QUIETER than source.** First fire showed
the mixed output had identical mean loudness to the source minus
~6 dB (-26.6 dB vs -20.6 dB). Root cause: ffmpeg's `amix` defaults
to `normalize=1` which divides each input by the number of inputs
(`-6 dB drop` on a 2-input mix). Fixed by adding
`amix=inputs=2:duration=first:normalize=0` so the avatar voice
stays at its full source level and the ducked bed adds on top.

**Hiccup 2 — bed inaudible even at max slider (0.4).** After
hiccup 1's fix, output and source loudness matched but the bed
still wasn't audible. Root cause: the placeholder beds had been
generated at `volume=0.4` (≈ -34 dB at source) — the slider then
scaled them further down. At slider 0.4 the bed sat at ~-42 dB
while the voice was at -20 dB — voice 22 dB louder, drowned the
bed completely.

Two-part fix:
1. Regenerated placeholder beds at higher base volume (~-20 dB).
2. **Added `loudnorm=I=-16:TP=-1.5` to the bed BEFORE the volume
   scaling** so any uploaded MP3 (loud or quiet at source) gets
   normalised to -16 LUFS (broadcast reference) first. Slider
   values now behave consistently across every bed.

Operator validated after both fixes:
> *"it worked commit it!"*

### Stack signals

Music stacks cleanly on top of every other composite. The
`MUSIC_SOURCE_KINDS` set explicitly includes
`spokesperson_ad_with_pip`, `spokesperson_ad_with_backdrop`,
`spokesperson_ad_with_cohost` so the operator can chain
`Polish → Cohost → Backdrop → Music` for a fully-finished ad with
all six finishing layers applied.

### Merge-thesis signal

Music is the lowest-effort finishing step that delivers the
biggest perceived-quality jump for ad-style spokesperson content.
For unified-donkey-betz, a small curated library of bedded music
(public-domain, AI-generated via Suno/Udio, or stock licensed)
becomes a shared resource that improves every clip's perceived
production value without per-clip Runway spend. The `loudnorm`
normalisation in particular means any operator-curated bed
behaves consistently regardless of mastering — a real "drop in
a folder and it works" experience.

---

## PR FG — B-roll cutaway composite (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FF:
> *"let's do b-roll cutaway and get this section 100% completed
> then lets move on to Animated PiP"*

Closes the "make spokesperson ads feel less plain" exploration
arc — every option from the original four-option list (plus the
multi-avatar coda) is now shipped.

### What it does

1. Operator clicks **🎞️ B-Roll** on any spokesperson tile.
2. `BrollPickerModal` lists every `cinematic_video` output across
   all campaigns + all characters, grouped by character. Same
   cross-campaign factoring as PR FE Cohost.
3. Operator picks one → "Splice it in" → backend ffmpeg-composites:
   - Avatar video plays for the first **30%** of duration
   - Cinematic clip fills the middle **~40%** (capped at
     `min(broll_natural_dur, source_dur * 0.4)`)
   - Avatar video resumes for the final **30%**
   - **Avatar audio plays continuously across all three segments**
     so it reads as the avatar narrating an inset scene
4. Result lands as `spokesperson_ad_with_broll` in the
   **🎞️ With B-Roll Cutaway** group.

### Implementation note — filter graph

Single `ffmpeg -filter_complex` call with three trimmed video
segments concatenated, source audio mapped whole:

```
[0:v]trim=start=0:end={start},setpts=PTS-STARTPTS[v_pre];
[1:v]trim=start=0:end={cut_dur},setpts=PTS-STARTPTS,
     scale={W}:{H}:force_original_aspect_ratio=increase,
     crop={W}:{H},setsar=1[v_cut];
[0:v]trim=start={end}:end={source_dur},
     setpts=PTS-STARTPTS[v_post];
[v_pre][v_cut][v_post]concat=n=3:v=1:a=0[outv]
```

`-map "0:a?"` keeps the avatar's full audio track. The cutaway
window is computed server-side from sensible defaults
(`insert_start_s = source_dur * 0.3`, `broll_duration_s =
min(broll_natural_dur, source_dur * 0.4)`) with optional body
fields for operator override.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/broll_client.py` | NEW — `compose_with_broll_cutaway(...)` + dim/duration probes + sensible timing defaults |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_broll` |
| Route | `backend/app/routers/campaigns.py` | `AddBrollBody`, `POST /api/campaigns/{id}/add-broll`, `BROLL_FOREGROUND_KINDS`, `spokesperson_ad_with_broll` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.addBrollCutaway(...)` |
| UI | `frontend/src/components/BrollPickerModal.jsx` | NEW — character-grouped cross-campaign cinematic picker with autoplay-muted thumbnails |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🎞️ B-Roll button, modal state + fire handler, 🎞️ With B-Roll Cutaway group, music kind set updated to include `spokesperson_ad_with_broll` so the stack chain stays unbroken |

### Validated end-to-end

Operator confirmed: *"it worked commit it"*. Backend `99 routes`
(was 98; +1 for `add-broll`). Frontend vite build green
(685.68 kB lazy chunk, +8 kB from `BrollPickerModal`).

### "Make ads feel less plain" section — COMPLETE

All four directions from the original Polish-pass-follow-up
brainstorm now shipped, plus the multi-avatar coda:

| PR | Direction | What it does |
|---|---|---|
| FB | A. Polish | Captions + lower-third + intro/outro cards |
| FC | (static PiP precursor) | Reference image overlay in bottom-right |
| FD | Reverse-PiP | Cinematic backdrop with avatar in corner |
| FE | Multi-avatar co-host | Two avatars on screen, audio v1 muted |
| FF | D. Music bed | Music ducked under voice |
| **FG** | B. B-roll cutaway | Cinematic spliced into avatar mid-roll |

Eight finishing buttons total on every spokesperson tile (Dub /
Remix / Polish / PiP / Backdrop / Co-Host / Music / B-Roll) — and
**every composite stacks on every other** via the kind sets so
operators can chain e.g. `Polish → Backdrop → Music → B-Roll` for
a single ad with all four layers applied.

Next direction up next: **Animated PiP** (use `image_to_video` on
the campaign's reference image to generate a looping animated PiP
source, replacing PR FC's static image overlay with motion).

---

## PR FH — Animated PiP (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FG: *"lets start with B if that's
your instincts!"* — chose the motion-preset path over hardcoded
or free-prompt versions for the first animated-PiP slice.

### What it does

Atomic `image_to_video` + ffmpeg overlay in one call:

1. Operator clicks **✨ Anim PiP** on any spokesperson tile.
2. `AnimatedPipMotionModal` lists 5 motion presets (Slow Push-In /
   Pan Left / Pan Right / Parallax Depth / Zoom Out). Server-side
   prompts live in `MOTION_PRESETS` so they can be tuned without
   an SPA redeploy.
3. Fire → backend resolves source image (campaign reference →
   character portrait fallback, same chain as PR FC), fires
   Runway `image_to_video` with the preset's prompt, polls (600s
   deadline), downloads the result to `data/animated_pip/`, then
   ffmpeg-overlays the looped clip in the bottom-right corner of
   the avatar ad with a 6px white border.
4. Lands as `spokesperson_ad_with_animated_pip` in the
   **✨ With Animated PiP** group, with motion preset as a cyan
   badge.

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/animated_pip_client.py` | NEW — `animate_and_compose(...)`, `MOTION_PRESETS` table, image_to_video helpers |
| Models | `backend/app/models.py` | `OutputKind` += `spokesperson_ad_with_animated_pip`; `OutputRecord.motion_id` field |
| Route | `backend/app/routers/campaigns.py` | `AddAnimatedPipBody`, `GET /animated-pip/motion-presets`, `POST /add-animated-pip`, `ANIMATED_PIP_SOURCE_KINDS`, `spokesperson_ad_with_animated_pip` added to `get_campaign_output`'s `finished/` map |
| API | `frontend/src/api.js` | `api.listAnimatedPipMotions`, `api.addAnimatedPip` |
| UI | `frontend/src/components/AnimatedPipMotionModal.jsx` | NEW — 5-preset picker with per-motion accent + amber slow-Runway notice |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | ✨ Anim PiP button, modal state, ✨ With Animated PiP group, motion badge on tiles |

### Operator-discovered limitation

Operator validated the slice on a Miles spokesperson ad. The
resulting composite showed two copies of Miles — the original
avatar in the main frame talking, and a fresh image_to_video
output of Miles's portrait moving subtly in the corner. Operator
flagged this as visually redundant:

> *"it just seems like there's a PiP of the exact same ad in the
> bottom right that's mouth is just moving to whats being said.
> There's gotta be better use cases for this feature and we just
> aren't using them properly"*

Root cause: when the campaign has no `reference_image_url`, the
PR FC fallback chain points at the avatar's portrait — same as
the main frame. image_to_video on the same face = duplicate face.

This insight became the spark for PR FI (Scene Composite) — see
the next section. PR FH stays useful when the operator supplies
an actual product/scene image; the redundancy issue only manifests
on portrait fallback.

### Merge-thesis signal

The static-PiP-with-motion direction is most valuable when the
PiP source is a PRODUCT shot, LOGO, or brand visual — not when
it's the same avatar. unified-donkey-betz's advisor clips will
benefit from this in the form of "Buffett talks, brand logo
pulses in the corner."

---

## PR FI — Scene composite generator (shipped 2026-05-12 evening)

**Trigger:** Operator after PR FH's discovery: *"What we need is
a way to create a video that either the Avatar is in or something
else like that, then have the avatar speaking in the PiP frame,
like they are explaining what's going on."*

The breakthrough slice. Combines on-demand `image_to_video`
generation with the PR FD Backdrop compositing pattern so the
operator can describe a SCENE PROMPT, fire once, and get a fully-
composed deliverable.

### What it does

1. Operator clicks **🎭 Scene** on any spokesperson tile.
2. `SceneCompositeModal` opens with:
   - Scene prompt textarea + 5 starter suggestion chips
   - Image source radio: "Use avatar in scene" (default) /
     "Use campaign reference image" / "Upload a fresh image"
   - Motion preset dropdown (optional cinematography cue —
     reuses PR FH's MOTION_PRESETS)
3. Fire → backend:
   - Resolves image source per operator's pick
   - Composes the full prompt: `<scene prompt>. <motion suffix>`
   - Fires Runway `image_to_video` with prompt + source
   - Polls 600s, downloads to `data/videos/<campaign>-scene-<id>-<ts>.mp4`
   - Reuses `backdrop_client.compose_with_backdrop` to composite
     the generated scene as the backdrop + avatar in top-right
     corner tile + avatar audio kept whole
4. **Lands TWO OutputRecords:**
   - `cinematic_video` for the generated scene (reusable as a
     Backdrop / B-Roll source on future composites without re-
     firing image_to_video)
   - `spokesperson_ad_with_backdrop` for the final composite
     (shows up in PR FD's existing 🎬 With Cinematic Backdrop group)

### Touched files

| Layer | File | Change |
|---|---|---|
| Service | `backend/app/services/scene_composite_client.py` | NEW — `generate_scene_and_composite(...)` (image_to_video → download → call backdrop_client.compose_with_backdrop) |
| Route | `backend/app/routers/campaigns.py` | `SceneCompositeBody`, `POST /scene-composite`, `SCENE_FOREGROUND_KINDS`, `_resolve_scene_source_image` helper for the 3-way image picker logic |
| API | `frontend/src/api.js` | `api.sceneComposite` |
| UI | `frontend/src/components/SceneCompositeModal.jsx` | NEW — prompt textarea with 5 starter chips + 3-way image source radios + motion preset dropdown + inline upload (reuses /api/runway/upload-image) |
| UI | `frontend/src/components/CampaignWorkspace.jsx` | 🎭 Scene button, modal state + fire handler |

### Operator's emergent discovery

First fire on Miles with "coffee pouring + mountain view panning"
prompt + avatar-in-scene mode:

> *"Okay we need to stop right here! There's so much cool shit
> we can do with what just happened! I used a video that has
> coffee pouring and it has a mountain view panning in the
> background"*

> *"No it's only appearing once, it's like the normal avatar
> videos but it has things going on which is what I have been
> wanting to happen!!"*

The key insight: when `image_source='avatar'`, Runway uses the
character portrait as the source frame and the avatar IS the
focal point of the generated scene. The composite is the avatar
narrating a corner version of themselves OVER the bigger version
of themselves in the cinematic scene. Despite the duplication
the operator's read is "one cohesive video" — environment motion
reads as "things going on around the spokesperson."

This is the slice that turns Character OS from "talking-head ad
generator" into "spokesperson in any context, narrating their own
scene." Every existing finishing layer (Polish / Music / Dub /
Remix / B-Roll / Co-Host) stacks cleanly on top.

### Combinatorial space unlocked

With one character + N scene prompts + the eight existing finishing
layers, the operator can produce:

- 5+ scene variants per script (e.g. coffee shop / mountain cabin /
  city skyline / beach / office) × 5 Aleph style remixes × 29
  dub languages × music bed × captions = thousands of unique
  deliverables from a single original avatar_videos render
- Saved scenes accumulate as reusable `cinematic_video` outputs —
  pickable in Backdrop and B-Roll modals for future composites
  without re-firing Runway

### Merge-thesis signal

This is the strongest creative primitive yet. For
unified-donkey-betz's 32 advisors, each could have a personal
scene library — "Buffett in his Omaha office", "Buffett on the
golf course", "Buffett at the airport" — generated once, reused
across hundreds of pitch scripts. Per-advisor scene libraries +
per-clip composability = a content factory.

Operator's reaction confirms: *"Yes commit PR FI first then we
can move on"*.
