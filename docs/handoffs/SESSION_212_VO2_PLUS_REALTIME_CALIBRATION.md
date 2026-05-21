---
title: "Session 212 — VO.2 ships + realtime arc real-mode calibration"
date: 2026-05-21
status: complete
session: 212
previous_handoff: ./SESSION_211_VO_SCOPE_LOCK.md
---

# Session 212 — VO.2 + realtime calibration

## TL;DR

Two parallel arcs in one session.

**VO.2** (commit `c788966`) — overlay_audio_at_offset primitive
+ ffmpeg-only splice route. Pairs with VO.1's TTS to unlock the
`cta_swap` (VO.3) and `narrated_intro` (VO.4) recipes. +39 tests
(Django 1387 → 1414; media-engine 246 → 258). Byte-identity
discipline (rule 4) validated via real-mode ffmpeg.

**Realtime calibration** (commit `2b861e6`) — first real-mode
dogfood of the R-arc with the operator-named keeper (Rigby).
Surfaced a structural identity leak in the document composer
(no `## Conversation Style` section), tool-description gaps that
caused `render_video` misfires, and a Runway-side avatar
content-filter constraint on personality format. All addressable
calibration findings landed in code; one (operator-name in
greeting) flagged as v1 limitation. 8 dogfood sessions, ~$0.65
spend, 6 transcripts persisted.

| Commit | Slice |
|---|---|
| `c788966` | feat(VO.2): overlay_audio_at_offset primitive + ffmpeg splice route |
| `2b861e6` | feat(realtime): platform Conversation Style + tightened tool descriptions |

## What landed — VO.2

Per the SESSION 211 handoff queue, VO.2 was the FIRST THING.
The slice broke into 4 stages: route → primitive → tests →
docs.

### Route (`media-engine/app/routers/internal.py`)

`POST /internal/clips/overlay_audio/` — body
`{base_url, vo_url, offset_seconds, duck_db?}`. Cache key
hashed off all four inputs → `data/_internal/overlays/<key>.mp4`.

ffmpeg filter chain:
* `[0:a]volume=enable='between(t,offset,end)':volume=duck_db[base_ducked]`
* `[1:a]adelay,afade=in,afade=out[vo_delayed]`
* `[base_ducked][vo_delayed]amix=duration=first:normalize=0[outa]`
* `-c:v copy -map 0:v -map [outa]` — rule-4 byte-identity.

Defense-in-depth: silent base → 422 pointing at `/audio/mix/`;
rule-6 overflow (offset + vo_duration > base + 50ms tolerance)
→ 422 with actionable message. Mock-mode short-circuit returns
deterministic stub URL.

Routes count: media-engine 138 → 139.

### Primitive (`shell/apps/compositions/primitives/overlay_audio.py`)

`overlay_audio_at_offset` — slot resolver accepts `base` (CLIP)
+ `voiceover` (AUDIO), or unnamed slots resolved by asset_type.
Pre-flight rule-6 check against persisted `Asset.duration_ms`
so operator-facing error fires before HTTP roundtrip. Output
role propagates the base CLIP's role (TALKING_HEAD stays
TALKING_HEAD per VO.0 spec) with COMPOSITE_OUTPUT static
fallback in PRIMITIVE_TO_ROLE.

Cost 100 micros (~$0.0001). Primitive count 22 → 23.

### Tests (39 new)

**Shell side** (`apps/compositions/tests/test_vo2_overlay_audio.py`)
— 27 tests covering registry wiring, cost model, slot
resolution (named + unnamed), validators (offset, duck_db),
rule-6 overflow + exact-fit boundary, mock-mode role
propagation (TALKING_HEAD + COMPOSITE_OUTPUT), real-mode
client invocation, MediaEngineError translation, empty
file_path rejection.

**Media-engine side**
(`media-engine/tests/test_vo2_overlay_audio_endpoint.py`) — 12
tests covering mock-mode stub returns, cache idempotency,
per-offset cache distinctness, Pydantic validation
(negative offset, duck_db out of range, blank URLs), rule-6
overflow via ffprobe, silent-base rejection, **rule-4
byte-identity assertion via `ffmpeg -c:v copy -f md5 -` on
base vs output** (the load-bearing real-ffmpeg test), and
output stream validation (video + audio both present).

Test totals: **Django 1387 → 1414 (+27); media-engine 246
→ 258 (+12).**

### Doc discipline

* `docs/design/VOICEOVER_V1.md` — VO.2 row marked SHIPPED
  with commit ref; change-log entry added.
* `00-START-NEXT-SESSION.md` — slice queue updated.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated (working
  tree dirty annotation expected pre-commit).

## What landed — Realtime calibration

The operator opened the SPA to test the realtime arc against
Rigby (the keeper, 24/7 Global AI) before script creation.
What followed was a 90-minute dogfood arc that surfaced four
structural findings and a v1 limitation.

### Dogfood sequence (8 sessions, ~$0.65 spend)

| # | Session | Outcome |
|---|---|---|
| 1 | 404c5efc | Identity leak: Rigby self-identified as "Character OS, powered by Runway" |
| 2 | 0a83a0b7 | 50 chars only — STT heard "Rugby" not "Rigby" |
| 3 | 9652d05d | Personality patched → identity solid; render_video misfired on "how would I create an ad?" → user approved → real 23.5s talking_head rendered ($0.25) |
| 4 | 7b716541 | Personality patch tightened → render_video still misfired pre-confirm of topic |
| 5 | f46d7d16 | Tool description tightening + Conversation Style section landed → workflow explanation pattern landed, no false renders |
| 6 | ditto continued | Sessions 6-8 validated platform Conversation Style + tightened tool descriptions held; Q-r-2 loop manifested on thin-knowledge query |
| 7 | 743948c7 | "Admin" in greeting attempt #1 — failed |
| 8 | b1a954ea | "Admin" in greeting attempt #2 (9 mentions + invariant phrasing) — still failed; recall_knowledge tool fired 4x in a loop on `DealFlowTracker` (1-chunk stub) |

### Code landings

**`compose_realtime_document` (`shell/character_os/realtime_document.py`)**
* New `## Conversation Style` section baked into every
  realtime document — platform-wide behavior applies to
  every Character by construction. Section placed first
  (before Voice/About) so it anchors the avatar's LLM
  behavior before persona facts.
* Encodes: no auto-tools on session open, tool invocations
  wait for operator intent + topic, recent-conversation
  lookups only on explicit reference, acknowledge lookup
  latency verbally to mitigate Q-r-2 silent gap.
* New `_resolve_operator_handle(spokesperson)` helper —
  resolves operator name from workspace.owner via
  display_name → first_name → email handle ("admin@..." →
  "Admin") → "the operator" fallback. Future-proofed for
  a User.display_name field without re-touching the doc
  composer.
* Note: operator name does NOT actually appear in
  Rigby's greeting despite 9 mentions in the doc body.
  Runway avatar enforces "Hello. I'm [Name]" first-turn
  shape. See `feedback_runway_avatar_greeting_bias.md`.
  v1 limitation.

**`render_video` tool description**
(`shell/apps/realtime/tools/render_video.py`) — tightened
to require explicit "make/render/produce a video/clip/ad"
verb + named topic. Explicit non-triggers: "walk me
through", "tell me", "explain", "how do I/would I", "yes"
in response to a workflow offer. 455 chars (under the
500-char media-engine cap).

**`recall_recent_conversations` tool description**
(`shell/apps/realtime/tools/recall_recent_conversations.py`)
— tightened to require explicit past-session reference.
Forbids session-open auto-fire and speculative pre-fetch.
475 chars.

**`test_compose_respects_max_chars`** updated for the new
section in the budget math (~900-char header now includes
Conversation Style; small-budget test bumped to 2000
max_chars to fit header + force chunks to drop).

### Personality calibration

Rigby's personality went through 4 versions before landing
clean. Saved as a memory finding
(`feedback_runway_content_filter_rejects_imperative.md`):
**Runway's avatar content filter rejects imperative
personality patterns** (`"You are..."`, `"You never..."`,
`"When asked X, do Y"`) with `400 "This text cannot be
used for an avatar"`. Third-person descriptive form
("Rigby is..." / "Rigby walks users through workflows
verbally") passes.

Final Rigby personality at session end: 1183 chars,
descriptive third-person, no hard-coded opener (the
platform Style block now drives greeting structure).

### Tool description cap finding

Saved as `feedback_runway_tool_description_500_char_limit.md`.
The media-engine's Pydantic schema has
`description: str = Field(..., max_length=500)` on
`InternalRealtimeToolDef`. Overflow returns 422 from
`/internal/realtime_sessions/`, which Django broker translates
to 502 "realtime backend unavailable" — confusingly worded
since the fix is on the shell side, not the backend. Hit
this twice during description tightening before adding the
length-check one-liner.

### Q-r-2 silent gap calibration

Saved as `feedback_qr2_mitigated_by_document_context.md`.
The naive read of Q-r-2 ("tool calls always cause a silent
gap") was incomplete. The gap is **conditional on whether
the answer is in the loaded document**.

Session 6 turn 2 (good case): User asks "what does 24/7
offer?" → recall_knowledge fires → avatar narrates
**directly** from the document's `## About` section
listing all 6 products. No silent gap.

Session 8 (bad case): User asks "tell me about
DealFlowTracker" → recall_knowledge fires → DealFlowTracker
has 1 chunk (stub) → document barely covers it → avatar
has nothing to fall back on → avatar fires tool again →
loop.

This is the worst-case Q-r-2 — fixable next session via
Fix 2 (A+C) + Fix 3 (B).

### Tool description as the real lever

Saved as `feedback_tool_descriptions_drive_selection.md`.
After three rounds of trying to fix `render_video`
misfires via personality patches and document content,
the actual lever was the tool's `description` arg.

Runway's avatar LLM has a tool-selection layer that reads
tool descriptions and decides when to fire. That layer
doesn't consult personality. Tool descriptions are the
load-bearing surface for tool gating. Going forward,
treat them as a living surface: every misfire surfaces a
new "Do NOT" non-trigger entry.

## Calibration moments worth carrying

1. **Two parallel arcs in one session is sustainable** when
   the second is operator-driven rather than slice-driven.
   VO.2 was a queued ½-slice; realtime calibration was an
   emergent dogfood arc surfaced by the operator opening
   the SPA. Both shipped clean commits.

2. **Real-mode dogfood is invaluable for the realtime arc**
   in particular. Mock-mode tests covered the state machine
   and document composition; they couldn't have surfaced
   the identity leak ("I'm Character OS, powered by
   Runway"), the Runway content-filter constraint on
   personality, or the operator-name-in-greeting
   limitation. SESSION 158 + 173-174 calibration carries
   to this session: real-mode finds bugs in every arc.
   Streak now 11-for-11.

3. **The doc-composer + tool-description duality** —
   document content and tool descriptions are two
   independent levers in the realtime arc. Document
   shapes WHAT the avatar says; tool descriptions shape
   WHEN tools fire. Don't conflate; don't try to fix
   one via the other.

4. **Runway's avatar has structural constraints** that
   don't surface in API docs:
   * Personality format filter rejects imperative
     patterns
   * First-turn greeting bias enforces "Hello. I'm
     [Name]"
   * SDK has no `sendClientEvent` for tool-result
     return (R8.2 Q-r-2)
   Each of these is a v1 limitation requiring upstream
   fixes. Document them; don't keep relitigating.

5. **Tight test budgets + small max_chars tests + a
   mandatory header section** = the existing budget
   test broke when I added Conversation Style. Updated
   the test (max_chars 400 → 2000) rather than making
   the new section droppable. Conversation Style is
   load-bearing infra, not a budget casualty.

6. **The Q-r-2 loop is its own UX bug class.** Single-
   fire-then-silent (sessions 4-5) was annoying. 4x-fire
   loop (session 8) was operator-visibly broken
   ("Are you feeling all right, Big Jake?" — STT
   misheard but operator noticed). Server-side retry
   suppression (Fix 2A) is now a P1 next-session item.

## Test counts at SESSION 212 close

| Suite | Count | Δ |
|---|---|---|
| Django | **1414** | +27 |
| Media-engine | **258** | +12 |
| SPA vitest | **456** | unchanged |

## Where we are after SESSION 212

| Surface | Status |
|---|---|
| VO.0 + VO.1 + VO.2 | DONE |
| VO.3-VO.6 (recipes + SPA + dogfood) | Queued (~2 sessions) |
| R-arc Conversation Style block | DONE + DOGFOOD-VALIDATED |
| R-arc tool description hardening | PARTIAL — recall_knowledge tightening + retry suppression next session |
| R-arc operator-name-in-greeting | BLOCKED — Runway upstream lever needed (v1 limitation documented) |
| Rigby keeper profile | RIGBY NAMED + brief + personality + voice (`david`) set + dogfood-validated |

## Next session — SESSION 213

**FIRST THING**: Fix 2 (A+C) + Fix 3 (B) — kill the
recall_knowledge loop + reduce its fire rate via
document boost. Three layered changes documented in
`00-START-NEXT-SESSION.md`:

* **2A**: server-side retry suppression in
  `apps/realtime/dispatch.py` — dedup
  `(tool_name, args)` within a 10s window.
* **2C**: tighten `recall_knowledge` description with
  "Do NOT invoke when the answer is in document
  memory" non-trigger.
* **3B**: bump `DEFAULT_TOP_K` from 30 → 50 in
  `realtime_document.py` so more answers are baked
  into the document at session-create.

Acceptance: replay the SESSION 212 "tell me about
DealFlowTracker" scenario with the fixes in place.
Rigby should either answer from boosted document
context without firing the tool, or fire once + get
"already_returned" hint + bridge verbally.

After fixes land: real-mode dogfood with Rigby on a
mix of well-grounded products (Character OS) and
thin-grounded products (DealFlowTracker) to confirm
the loop is dead. Then move to script creation —
the original SESSION 212 goal before realtime
calibration ate the second half.
