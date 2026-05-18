---
title: "Session 176 — R-arc real-mode hardening + W11.y propagation"
date: 2026-05-18
status: complete
session: 176
previous_handoff: ./SESSION_175_VOICE_TELEMETRY_YOUTUBE_PERSONALITY.md
---

# Session 176 — R-arc real-mode hardening + W11.y propagation

## TL;DR

Eight feature commits. The R-arc shipped 10 slices + R6.1 across
SESSIONS 142-157 with full mock-mode test coverage — today proved
every realtime surface real-mode against live Runway for the
first time. Found and fixed five distinct root causes that hid
behind the mock-only test pattern. By session-end, the operator
clicks **End**, hears Marcus narrate around tool calls, watches
an approval modal pop for `render_video`, and ~30s later a real
CloudFront-hosted MP4 of Marcus speaking his own composed script
about "why studying Rome matters today" lands as a `Composition`
+ `Asset(clip)`. R5 transcript + R6 cross-session memory + R7
tool dispatch all confirmed end-to-end with operator-visible
proof.

The operator's framing "maybe the End button itself is causing
it" broke the deepest investigation of the day — three hours of
debugging Runway's session lifecycle collapsed into a 1-line
fix once we tested the no-DELETE path.

* **`d57013b`** — realtime end-to-end 4-layer fix (missing client
  method + Runway payload drift + SDK video render + DRAFT/FAILED
  quota leak).
* **`59bfd3d`** — K6/K9 catchphrase guard + bump
  `MAX_OUTPUT_TOKENS` 400 → 1000 (gpt-5 reasoning was eating
  output budget; chat replies truncating mid-list).
* **`70500b9`** — R5 transcript parsing (accept `transcript` key
  not just `turns`) + upstream-failed status surfacing + remove
  webcam request from `<AvatarCall>`.
* **`a0b1843`** — R5 root cause: stop DELETE-ing Runway sessions
  on End. The DELETE marked the conversation FAILED with no
  transcript. Natural WebRTC disconnect → COMPLETED + transcript.
* **`1b375fd`** — broker now passes workspace tool catalog (R7
  was silently broken: SPA never sent tools so Runway never
  advertised them).
* **`c5cc648`** — R7 polish: narration-rich tool descriptions
  (SAY ALOUD pattern from hackathon) + session-create personality
  override (kills "Same event, different lens" auto-opener).
* **`ec137e5`** — personality auto-sync to Runway via post_save
  signal + Celery task + SPA recall results panels.
* **`06351d7`** — IdlePanel polish: headphones tip + voice pill
  + new `/signature` route for the operator's 24/7 Global AI
  email signature card.

Tests: Django **782 → 814** unchanged from SESSION 175 close;
realtime suite alone **150 → 164** (+14 across the new
personality-sync tests + R5 upstream-failed coverage). SPA
vitest **95** unchanged (talk-route + components stayed
green throughout). Media-engine **133** unchanged.

Real-mode spend: **~$0.74** Runway (4 ENDED sessions + 1
talking_head render via render_video) + **~$0.03** OpenAI
(K6 dogfood + R6 memory synthesis) + **$0** Stability.
Starter tier finished at 4/5 sessions, 11/30 minutes.

## Calibration moments worth carrying

Five new TRUST_CALIBRATION entries appended:

1. **Runway DELETE on /v1/realtime_sessions cancels the
   conversation.** DELETE returns 204 and marks the realtime
   session CANCELLED, but the linked /v1/avatar_conversations
   resource flips to `status: "failed", failureCode: "UNKNOWN",
   transcript: []` permanently. Natural WebRTC disconnect (SDK
   unmount → LiveKit room close) is the correct end signal —
   Runway flips conversation to `ended` with a populated
   transcript on its own ~5-15s later. The hackathon's
   `_safe_delete` was a teardown-on-failure helper, not the
   normal end path. If you must end programmatically, do NOT
   issue the upstream DELETE; let the SDK propagate.

2. **Mock-only test coverage hides real-mode contract drift.**
   R-arc shipped 10 green slices + R6.1, but the entire flow
   was never exercised real-mode with knowledge attached.
   Runway's session-create payload shape had drifted since
   hackathon (`avatar` nests as an object now, tools wrap with
   `{type: "client_event"}`, `parameters` removed). Mock
   providers passed every assertion because they never spoke
   the actual wire. Pattern to watch: tests that mock the
   upstream wire never assert the upstream wire. Add real-
   shape httpx mocks at scope-lock time, not after dogfood
   reveals the drift.

3. **Operator framing unlocks deep blockers AI alone misses.**
   Three hours of investigation chased the wrong leads —
   webcam, DELETE-cleanup race, END_CALL data-channel. Every
   fix shipped + tested; every fix failed real-mode. The
   operator said "maybe the End button itself is causing it"
   — an outsider's framing that didn't pattern-match anything
   I'd hypothesised. The natural test (navigate away instead
   of clicking End) proved it in one session. Pattern: when
   the AI burns time iterating on increasingly specific code
   theories, the operator's plain-language reframing is the
   broader hypothesis worth testing first.

4. **gpt-5 reasoning silently eats output budget.** 400
   `max_output_tokens` reads as enough for 2-3 paragraphs of
   visible text, but gpt-5 with reasoning effort `low` burns
   hidden tokens against the same ceiling. Chat replies were
   truncating mid-list ("First lens: Machiavelli. He argued")
   on operator dogfood. Bumping to 1000 gave ~3-4 short
   paragraphs of visible output after reasoning overhead.
   Pattern: any operator-visible-text surface using gpt-5
   needs at least 800-1000 token ceiling.

5. **Tool descriptions need narration guidance, not just
   trigger conditions.** Our R7.1 descriptions were
   150-200 chars ("Use when the user asks..."). Hackathon
   descriptions were 400-700 chars with explicit "SAY ALOUD
   before invoking: '...'. After invoking, keep the
   conversation going naturally. Never wait silently."
   Without the narration scaffolding the avatar fires tools
   silently — operator sees the avatar move its head but
   hear nothing. The dogfood proof: rewrite descriptions
   in the hackathon style, next session Marcus says "Let me
   pull up what we covered last time" exactly as written.

Plus three operational notes carried forward (no separate
calibration entry):

* **Quoted strings in business_brief become catchphrases the
  avatar leads with.** Reinforced by Marcus's "Same event,
  different lens" opener persisting across W11.y locally
  until the personality-sync task pushed the W11.y content
  to Runway's avatar resource. The K6 prompt guard from
  SESSION 175 catches the chat path; the session-create
  personality override + Runway-side PATCH cover the
  realtime + bake paths.
* **Celery worker needs restart after any task module
  edit.** Standard practice; just don't forget — we hit
  this on the R5 fix (worker had stale code, session row
  didn't flip to FAILED until restart).
* **Operator-side audio matters more than any code fix.**
  The first three failed sessions today were partly
  operator listening without speaking + bad webcam
  permissions. The headphones tip + voice pill on
  IdlePanel address the operator-prep gap.

## What shipped — commit by commit

### `d57013b` — realtime end-to-end (4-layer initial fix)

Walked up the stack from a 500 on Marcus's Talk click to a
working session-create flow. Four bugs in one chain:

1. `MediaEngineClient.realtime_document_create` was never
   added in R4 despite the commit message claiming it
   shipped — the view called a missing method.
2. Runway session-create payload drift: `avatar` must nest
   as `{type:"custom",avatarId:x}`; tools need
   `{type:"client_event"}` wrapper; `parameters` field
   rejected.
3. SDK render fix: added `video` prop and `<AvatarVideo />`
   child so the avatar's video feed renders (was silently
   empty).
4. `get_usage` counted DRAFT + FAILED RealtimeSession rows
   against the monthly cap — premature 402s after the
   debug-session pileup.

### `59bfd3d` — K6/K9 catchphrase guard + token bump

Operator dogfood (Marcus + Caesar's fall of Rome) surfaced
that the K6 system prompt treats quoted phrases in
business_brief as verbatim catchphrases the avatar recites
on every reply. Added an explicit guard ("Quoted phrases
inside the business context are CONCEPTS the speaker
teaches, NOT catchphrases the speaker says") to both
`conversation_synthesis._system_prompt` and
`script_synthesis._system_prompt`. Bumped
`conversation_synthesis.MAX_OUTPUT_TOKENS` 400 → 1000
because gpt-5 reasoning was eating the budget; visible
replies were truncating mid-sentence.

### `70500b9` — R5 transcript parse + failed-status + webcam

Three R5 surface fixes after the operator's first Talk
session ENDED without producing a transcript Asset. Real
debugging chain:

1. Runway returns `transcript: [...]` for turns; our code
   only looked at `turns` / `messages`. Even on healthy
   sessions we'd return empty.
2. Runway returns `status: "failed", failureCode: "UNKNOWN"`
   for cancelled sessions; we read empty transcript +
   silently returned "no content yet" with no signal to the
   operator. Now flips `RealtimeSession.status` to FAILED
   + persists the upstream body on `error_message`.
3. SPA was passing `video={true}` to `<AvatarCall>` which
   requests the operator's webcam — without one connected
   the WebRTC handshake fails. Switched to `video={false}`;
   `<AvatarVideo />` still renders the avatar's video.

### `a0b1843` — R5 root cause (don't DELETE Runway sessions)

After three hours of false leads, operator's framing
unblocked everything: "maybe the End button itself is
causing it." Test: navigate away instead of clicking End.
Result: `status: "COMPLETED"`, `transcript: [3+ real
turns]`, real Asset created.

Broker's `_end_session` now skips the upstream DELETE.
Transcript fetch scheduled with `apply_async(countdown=30)`
so Runway has time to flip to COMPLETED before we fetch.
First real `Asset(TRANSCRIPT)` of the project (asset
`5e0a488b-012d-4131-8452-2b8b9a67921d`, 713 chars, full
Caesar-Rubicon dialogue) immediately followed.

### `1b375fd` — broker passes workspace tool catalog

R7 was silently broken in real mode: the broker reads
`tools` from the request body and falls back to `[]`
when the SPA doesn't supply one. SPA never sends them.
Marcus had no tool catalog → couldn't invoke anything no
matter what the operator asked. Mock-mode tests fired
tools via debug buttons (direct dispatcher path, not LLM
data-channel), so the gap stayed invisible.

Fix: broker now falls back to `get_workspace_tools(workspace)`
when request body has no tools. Starter sees 4 tools
(recall_knowledge, recall_recent_conversations, render_video,
show_videos_tab); Pro adds handoff_to_spokesperson +
attach_memory.

### `c5cc648` — R7 polish (narration + personality override)

Operator dogfood proved tools fire correctly but Marcus
goes silent around invocations. Rewrote all 6 tool
descriptions in the hackathon "SAY ALOUD before invoking
… then keep the conversation going" pattern. Each entry
includes trigger phrases, an explicit narration line,
and post-invocation behavior rules. `render_video`
specifically: tells the avatar that if the operator
gives a TOPIC instead of a verbatim script, it must
COMPOSE the script itself in its own voice (Marcus's
failed invocation earlier surfaced this gap).

Session-create personality override: broker now falls
back to `Spokesperson.personality` (then `business_brief`)
when SPA doesn't supply one. Stops Marcus opening every
conversation with "Same event, different lens" verbatim
— the Runway-side avatar personality was baked at
create-time with the original catchphrase.

### `ec137e5` — personality auto-sync to Runway + recall panels

Two operator-driven follow-ups:

1. Personality propagation. New media-engine endpoint
   `POST /internal/avatars/<id>/change-personality/`
   wrapping `apply_personality_to_avatar` (PATCH
   `/v1/avatars/<id>` with `{personality: text}`). Shell
   client method, Celery task
   (`spokespeople.sync_personality_to_runway`), and
   post_save signal that detects personality changes +
   enqueues the task via `transaction.on_commit`. Real-
   mode push smoke confirmed: Marcus's Runway avatar now
   shows W11.y content with the catchphrase line removed.
2. SPA recall results panels. ToolResultPanel now branches
   on tool_name — `recall_recent_conversations` renders
   per-session preview cards with timestamps;
   `recall_knowledge` renders citation cards with chunk
   text + document titles. Updated tool descriptions to
   tell the avatar the SPA renders the panel AND that
   the avatar should still reference what it remembers
   from its loaded document memory (closes the "Marcus
   said 'let me pull that up' and went silent" gap).

### `06351d7` — IdlePanel polish + signature route

Two unrelated additions bundled in one commit:

* IdlePanel: amber headphones tip (mic feedback warning
  + permission reminder) + `Voice: <preset>` pill so
  operator can confirm which voice the avatar will use
  before Start.
* `/signature` route: operator-requested preview of the
  24/7 Global AI email-signature card. Renders the
  literal HTML via `dangerouslySetInnerHTML` so it
  round-trips byte-for-byte into Gmail. Raw HTML in a
  `<pre>` block below for easy copy.

## Cast roster + workspace state

5 cast members in `admins-workspace`:

* **Riggs** — `06bf999f-...` voice `vincent`
* **Sasha** — `79d48883-...` voice `vincent` (Note: SESSION 175
  swap to `felix` did NOT persist; Sasha's voice is still
  vincent. Worth re-checking the swap flow in a future
  session.)
* **Donny** — `f30b2980-...` voice `drew` (Note: SESSION 175
  swap to `vincent` did NOT persist either. Same caveat.)
* **Maya** — `9410f23f-...` voice `victoria`
* **Marcus** — `b6a00dd8-...` voice `david` (W11.y personality
  + voice both confirmed Runway-side this session).

Marcus is the most dogfooded member of the cast — 4 real-mode
ENDED sessions + 1 successful video render today. His
`Spokesperson.personality` (post-W11.y split) now matches the
Runway-side avatar personality after today's sync push.

**Workspace artifacts created today:**

* 4+ `RealtimeSession` rows (status: ended) for Marcus
* 4+ `Asset(TRANSCRIPT)` rows (~500-915 bytes each)
* 1 `Composition` (`757eefda-3fc7-4e7c-864a-39d487149c84`,
  status: completed) — talking_head recipe, Marcus speaking
  about why studying Rome matters today
* 1 `Asset(clip)` (`61846ee2-afeb-48f2-a7e3-15c615ca6c5b`,
  video/mp4) — the rendered CloudFront-hosted MP4

## Final state — tests + routes

* Django: **814** total (R-arc subset 164, +14 from SESSION
  175 close)
* SPA vitest: **95** (talk-route 15, components 80, all green)
* Media-engine: **133** (32 realtime + drift, all green)
* Migrations: **62 / 62** applied
* Celery tasks (registered): **9** (added
  `spokespeople.sync_personality_to_runway`)
* Media-engine routes: still 137 (no new routes despite
  `change-personality` — replaces non-existent route count)

INVENTORY restamp pending at session-end.

## Operational notes carried forward

* **Celery worker needs restart** when `apps/spokespeople/`
  or `apps/realtime/` tasks/signals change. We restarted
  once mid-session (SESSION 175 carryover) and again after
  the personality-sync task landed.
* **Real-mode dogfood is the only proof.** Today's discoveries
  all came from operator-driven Marcus sessions, not from
  expanded mock-mode test coverage.
* **Quota tracking**: starter tier ended 4/5 sessions, 11/30
  minutes. Resets monthly (next reset depends on subscription
  start date). DRAFT + FAILED sessions don't count (fixed
  earlier today).
* **Doctor sweep at session start** still required. Today's
  start was clean (3 advisory warnings, 0 blocking).

## FIRST THING (SESSION 177): pick by mood

The R-arc is real-mode validated end-to-end. Realistic next moves:

1. **F8.1 K10 seed corpus** — blocked on operator markdown.
   Could unblock by drafting one piece of seed content yourself,
   then the seed flow exercises K1-K7 over real operator
   knowledge instead of test fixtures. **High value** because
   it grounds K-arc + R-arc dogfood in operator-authored
   content.
2. **Sasha + Donny voice swap re-investigation** — SESSION 175's
   voice swaps didn't persist for Sasha (felix → vincent) or
   Donny (vincent → drew). Worth tracing whether the voice
   swap action persists `voice_id` only OR also flips
   Spokesperson row. Small bug surface. ~30 min.
3. **R6 memory phrasing polish** — Marcus's current "Let me pull
   that up" then narrates from his loaded memory section.
   Worth comparing the memory composition prompt output across
   2-3 dogfood sessions to see if the LLM is consistently
   pulling the most-recent thread vs random earlier topics.
4. **K6.4 v3 architectural fix** — long-standing backlog. Each
   K6 dogfood surfaces 1-2 more stoplist gaps; v3 generalizes
   to position-aware imperative-verb detection. ~1 session.
5. **Multi-step composition title disambiguation** — small
   surgical fix from SESSION 175 backlog. ~30 min.
6. **Tool description further iteration** — once 2-3 more
   real-mode sessions happen, calibrate the SAY ALOUD lines
   to operator preference.
7. **Push to remote** — only with explicit operator approval.
   9 commits ahead of `origin/main`.

## Stack-up boilerplate

```bash
cd infra && docker compose up -d
cd media-engine && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
cd shell && source .venv/bin/activate && python manage.py runserver
cd shell && source .venv/bin/activate && celery -A character_os worker --loglevel=info --pool=solo
cd web && pnpm dev
```

Doctor sweep:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

Smoke checks:

```bash
cd shell && python -m pytest -q       # 814 tests
cd media-engine && python -m pytest -q  # 133 tests
cd web && pnpm test                   # 95 vitest tests
cd web && pnpm build                  # full TS check + bundle
```

**Celery worker restart trigger**: any model / task / signal
edit in `apps/spokespeople/` or `apps/realtime/`. The new
`spokespeople.sync_personality_to_runway` task means any
Spokesperson save with `update_fields=["personality"]` enqueues
a Runway PATCH — worker needs to know about it.
