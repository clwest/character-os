---
title: "Session 216 — Bridge tools reframe: engine-bridge is the product pattern"
date: 2026-05-21
status: complete
session: 216
previous_handoff: ./SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md
reverses_framing_in: ./SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md
---

# Session 216 — Bridge tools reframe

## TL;DR

SESSION 215 closed the bridge-tools arc with the wrong product
framing. The operator surfaced the reframe in the next exchange:

> "Rigby is proof we can take a business and connect it to
> Character OS, and that character will have everything it needs."

The bridge tools (`consult_engine` / `query_spider_data` /
`agent_consult`) are **NOT** operator-only dogfood. They are the
v1 instance of an **engine-bridge product pattern** — how *any*
Character OS customer connects their external AI stack (agents,
spiders, knowledge, decision systems) to a customer-facing
spokesperson. Character OS becomes the **face** for the
customer's brain; the brain stays put.

SESSION 215's soft-deprecate banners were reversed. The
character-os work was correct in shape; only the framing was
wrong. SESSION 216 closes that gap and queues the natural
next slice — **per-workspace engine config** — so customer X's
spokesperson can hit customer X's engine instead of the
hardcoded u-d-b URL.

| Commit | Slice |
|---|---|
| (pending) | docs(realtime): SESSION 216 — reframe bridge tools as product pattern, not dogfood |

**Test totals unchanged** — no code shipped, only docstrings +
SPA component comment + handoff docs.

---

## What changed

### Banners on three backend tool files

* `shell/apps/realtime/tools/consult_engine.py:1-24` —
  docstring rewritten: "SESSION 216 — engine-bridge product
  pattern. v1 instance of the hookup pattern." Calls out the
  panel-first narration story as intended UX, not workaround.
* `shell/apps/realtime/tools/query_spider_data.py:1-10` —
  shorter reframe banner pointing to consult_engine's docstring
  for the long version.
* `shell/apps/realtime/tools/agent_consult.py:1-10` — same.

### SPA `BridgeAnswerPanel` comment

* `web/src/routes/spokespeople/talk.tsx` — the comment above
  `BridgeAnswerPanel` now reads "engine-bridge product surface"
  instead of "soft-deprecated alongside the bridge tools."
  Explicit that the panel is **intentionally** the primary
  narration channel for engine answers — the avatar is the
  human anchor, the panel is the data surface.

### Cross-CC handoff card (`RIGBY_F2F_UDB_CROSS_CC_HANDOFF.md`)

Added a SESSION 216 framing-update banner at the top of the
card; the rest of the technical content (F2F.0-F2F.5 slice
queue, push-to-speak provider candidates, what to borrow from
character-os) is unchanged because the **u-d-b F2F architecture
is still correct** — it's just a smaller, lower-priority
feature than SESSION 215 implied.

The receiving u-d-b CC, when they read the card, will see:

* Character-os bridge tools = **product pattern**, stays on
  character-os, already shipped.
* u-d-b F2F = **personal-use feature** for Chris talking to his
  own PA. Push-to-speak avatar + existing `/api/pa/chat/`. Nice
  to have. **Drop priority to queue / reject** by default;
  don't interrupt current u-d-b work.

---

## Why the reframe matters

Two distinct ideas had been collapsed into one in SESSION 215:

| Idea | What it is | Where it lives |
|---|---|---|
| **Engine-bridge pattern** | Customer-facing spokesperson surfaces a customer's external engine via HTTP. Panel renders structured answers. Avatar is the human anchor. | **character-os** (already shipped, SESSION 215 commits) |
| **Talk to my PA face-to-face** | Chris's personal-use feature. Push-to-speak avatar over existing Rigby PA. Audio-in / audio-out / lip-synced video. | **u-d-b** (queued, nice-to-have) |

SESSION 215 misread these as "we're moving the bridge tools'
real product to u-d-b." That conflated two features and led to
soft-deprecating the character-os work — which was actually the
v1 of the right pattern.

The product story the reframe locks in:

> **Character OS isn't a marketing-avatar SaaS. It's the face
> for any business's entire AI stack.** Customers plug their
> engine / agents / spiders / knowledge into a Character OS
> spokesperson via the engine-bridge pattern. The spokesperson
> becomes a customer-facing voice that surfaces live business
> intelligence in real-time conversations. 24/7 Global AI is
> the first customer; u-d-b is what 24/7's engine side looks
> like; Rigby (the spokesperson) is the first instance of the
> hookup.

This is a bigger product narrative than "marketing video
generator with conversational avatars." It explains why the
bridge tools exist, why the SPA panel is core (not workaround),
and what the next slice should be.

---

## Queued next slice — per-workspace engine config

Currently the bridge tools read `UDB_PA_API_URL` and
`UDB_PA_API_TOKEN` from the Django process environment. v1
deployment is hardwired to one customer (24/7 Global AI →
u-d-b). The natural generalisation:

* **Per-workspace `EngineConnection` model**: `workspace_id`,
  `engine_url`, `engine_token` (encrypted), `engine_kind`
  ('udb-pa', 'generic-http', future), `enabled` boolean.
* Bridge tools read connection by `session.workspace_id`
  instead of env vars. Env-var fallback for backward compat
  during the transition.
* SPA admin UI: workspace settings → "Engine connection" panel
  where customer pastes their engine URL + token. Test-ping
  button.
* Tier gate: per-workspace engine config is probably a Pro+
  feature (Starter ships without external-engine support).
* Docs: a customer-facing "How to connect your engine" page
  documenting the API shape the bridge tools expect (so non-
  u-d-b customers can implement compatible engines).

**Effort:** ~1.5 sessions. Backend (model + migration +
service) ≈ 1 session; SPA admin UI ≈ ½ session. Real-mode
dogfood (point 24/7's keeper at a non-u-d-b engine) closes the
arc.

**Not in scope:** the API contract Rigby's PA serves
(`/api/pa/chat/` shape). That stays as-is for now; future
generic-engine work would either standardise on this shape or
add an adapter layer.

---

## Calibration moment worth carrying

**Architectural reframes invalidate handoff docs faster than
they invalidate code.** SESSION 215 shipped the right code
under the wrong framing. The code stayed; the framing didn't.
Whenever a session "moves a feature" to another repo, double-
check the framing isn't conflating two features. If two things
were going to one repo before, they might be going to two
repos now.

Memory update proposed:
`feedback_reframes_invalidate_docs_before_code` — when a
product reframe happens, audit the handoffs / READMEs / module
docstrings for stale framing; code is usually fine. The SESSION
215 → 216 transition is the worked example.

---

## Test counts at SESSION 216 close

Unchanged from SESSION 215:

| Suite | Count |
|---|---|
| Django | **1436** |
| Media-engine | **258** |
| SPA vitest | **458** |

No code shipped this session — only docstrings + comment edits
+ handoff docs.

---

## Next session priorities

**FIRST THING (SESSION 217):**

1. Decide whether per-workspace engine config is the next
   character-os slice or whether the VO-arc (VO.3 `cta_swap`)
   still takes priority. Rigby (this character-os spokesperson)
   already works as a v1 instance — the engine-config slice is
   what unblocks SECOND customer onboarding. VO.3 is what
   completes the voiceover arc. Both fit ~½-1 session each.
2. If proceeding with per-workspace engine config: scope-lock
   doc first (`docs/design/ENGINE_BRIDGE_V1.md`?), then model
   + migration, then admin UI.
3. If proceeding with VO.3: follow VO-arc scope lock as
   already documented.

**Calibration findings to consider memorising:**
- `feedback_reframes_invalidate_docs_before_code` (proposed
  above).
