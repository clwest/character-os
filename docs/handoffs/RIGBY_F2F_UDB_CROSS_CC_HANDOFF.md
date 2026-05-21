---
title: "Rigby Face-to-Face — cross-CC handoff card (u-d-b)"
date: 2026-05-21
status: cross-cc-handoff
purpose: Coordination card for the existing Claude Code session running on u-d-b. NOT a fresh-session opener — paste this as a status message TO the running u-d-b CC so they can decide whether to interrupt their current work or queue F2F for next session.
source_handoff: ./SESSION_216_BRIDGE_TOOLS_REFRAME.md
supersedes_framing_in: ./SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md
---

# Rigby Face-to-Face — cross-CC handoff card

> **SESSION 216 framing update.** SESSION 215 originally framed
> F2F as "the real product moving off character-os." SESSION 216
> reframed it: the **character-os bridge tools are a product
> pattern** (any customer wires their engine to a customer-facing
> spokesperson) — **NOT** dogfood. The u-d-b F2F feature is now a
> **separate, smaller** thing — Chris's personal use ("talk to
> his own PA with a face") — not the entire product. **Scope
> reduces; priority drops.**

> **Context:** there is already a Claude Code session running on
> `/Users/donkeyking/development/unified-donkey-betz/`. This card
> is a **status message TO that CC**, mirroring the SESSION 214
> parallel-CC embed-cache fix-shaped flag pattern. Paste
> everything between the `--- CARD ---` lines into your existing
> u-d-b session as a status message. The receiving CC decides:
> interrupt current work, queue for next session, or reject.

---

## --- CARD ---

**Fix-shaped finding from sibling CC on character-os.** Same
coordination shape as the SESSION 214 embed-cache flag — read,
decide whether to act, respond. **SESSION 216 reframe inside:
this is now a SMALLER ask than SESSION 215 implied.**

### TL;DR (updated SESSION 216)

Two ideas were being conflated:

1. **The engine-bridge pattern on character-os** — how *any*
   Character OS customer hooks their external engine (agents,
   spiders, knowledge) into a customer-facing spokesperson.
   **Stays on character-os.** Already shipped (bridge tools +
   panel + tests, SESSION 215 commits 77150aa + 00c2586). The
   next slice there is "per-workspace engine config" so customer
   X's spokesperson calls customer X's engine, not the hardcoded
   u-d-b URL.

2. **Chris talking to Rigby (his own PA) face-to-face** —
   personal-use feature for the operator. Push-to-speak avatar
   (HeyGen / D-ID / similar) wraps the existing u-d-b
   `/api/pa/chat/` so Chris can audio-in / audio-out with Rigby.
   **This is what belongs on u-d-b.**

SESSION 215 conflated these and treated #2 as "the real product
moving off character-os." That framing was wrong. #1 is the
product; #2 is a nice-to-have personal feature for Chris's
workflow. **Drop priority on #2 accordingly.**

### Decision you need to make

**You are mid-session on u-d-b. Default to queue or reject** —
F2F (idea #2) is no longer urgent. Options:

1. **Queue at low priority.** Note in your end-of-session handoff
   that there's a personal-use F2F feature kicking around for
   Chris. Pick it up when nothing more important is in flight.
   **Most likely the right call.**
2. **Reject.** If your current arc + the existing u-d-b backlog
   already keep you booked for many sessions, F2F is fine to
   defer indefinitely. Chris will reopen the topic when he
   actually wants the feature.
3. **Interrupt.** Only if Chris (via Rigby) explicitly says so.
   Don't pick this on your own — the SESSION 216 reframe took
   the urgency off.

If you don't know which fits, **route via Rigby**
(`tools/pa_chat.py`) to ask Chris before committing.

### Cross-repo inheritance from character-os SESSION 215

I (Chris) was working on `/Users/donkeyking/development/character-os/`
in a sibling Claude session. That session shipped + then closed
the bridge-tools arc and wrote a handoff document specifically
for the next u-d-b session. **Read it first** before you start
planning here:

```
/Users/donkeyking/development/character-os/docs/handoffs/SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md
```

Key takeaways from that doc:

* **Runway's realtime avatar API is conversational** — the LLM
  lives server-side inside the Runway session; we can't push
  text at it. Verified by inspecting
  `@runwayml/avatars@0.16.0` type defs at
  `node_modules/.pnpm/@runwayml+avatars@0.16.0_*/dist/index.d.cts:163`.
  No `speak()`, `say()`, `sendText()`, or `publishText()` on
  `AvatarSession`.
* **Push-to-speak avatars are the right fit for Rigby F2F.**
  HeyGen Streaming Avatar, D-ID Live Portrait, and similar
  providers take text + voice ID and lip-sync whatever we hand
  them. The LLM stays ours (Rigby's PA pipeline).
* **Two architectures, look identical to users, completely
  different product shape.** Conversational closes the LLM off;
  push-to-speak gives full control. Don't try to emulate one as
  the other.

### What we're building on u-d-b

```
operator mic ──► STT (Whisper Realtime / similar)
                  │
                  ▼
              Rigby PA  (existing /api/pa/chat/ — DO NOT rebuild)
                  │
                  ▼ answer text
              TTS (ElevenLabs / Cartesia / similar)
                  │
                  ▼ audio
              Push-to-speak avatar (HeyGen / D-ID / similar)
                  │
                  ▼ video stream
              Operator's browser
```

The work is mostly wiring. **Rigby's brain already exists**
(your `/api/pa/chat/` endpoint + GPT-5.2 function calling +
tool catalog + spider network). We are not changing Rigby; we
are giving Rigby a face.

### v1 slice queue

The character-os handoff sketched F2F.0–F2F.5. Start with **F2F.0**:

* **F2F.0 — Scope lock.** Pick the push-to-speak provider, write
  a scope-lock doc (mirror character-os's
  `docs/design/REALTIME_AVATAR_V1.md` pattern), confirm cost
  model, decide on the SPA / UI surface (new u-d-b admin page?
  new AI Studio route?). **~½ session.** This is your first
  thing — don't start coding yet.

After F2F.0:

* **F2F.1** — Provider abstraction + first impl + mock provider
  (Protocol-shaped, parallel to character-os R2's
  `RealtimeProvider`). 1 session.
* **F2F.2** — `/api/pa/voice_session/` broker (creates streaming
  session, returns SDK-safe payload). 1 session.
* **F2F.3** — STT → existing `/api/pa/chat/` → TTS → avatar wiring.
  1-2 sessions.
* **F2F.4** — UI route (`/rigby/talk` or similar). 1 session.
* **F2F.5** — Real-mode dogfood + arc close. ½ session.

Total budget: ~5 u-d-b sessions if everything lands clean.

### Provider research before F2F.0 commits

Confirm latency + cost + API shape for at least:

* **HeyGen Streaming Avatar API** — the leading candidate
  (push-to-speak via WebRTC, sub-second latency, has a `speak()`
  endpoint that takes text + voice id). Check current pricing.
* **D-ID Live Portrait API** — alternative.
* **Tavus** — newer entrant, check positioning.
* **Recheck Runway** — they may have shipped a `speak()` API
  since SESSION 215; if they have, that's a bonus path. As of
  the character-os SESSION 215 inspection: no.

Don't pick a provider in your first message. Frame F2F.0 as
research → recommendation → scope-lock doc, then circle back
to Chris (via Rigby) before committing.

### What u-d-b can borrow from character-os (file references)

> All paths below are character-os paths — read-only inspection
> from u-d-b. Copy patterns into u-d-b, do not import.

* **Model shape:** `shell/apps/realtime/models.py` —
  `RealtimeSession` + `RealtimeToolInvocation`. Adapt to u-d-b's
  app conventions; keep the workspace + status state-machine.
* **Provider Protocol pattern:** `media-engine/app/services/realtime_provider/__init__.py`
  + `runway.py` + `mock.py`. Same shape will work for HeyGen /
  D-ID — Protocol + named adapter + mock.
* **Cost ticker:** `web/src/components/cost-ticker.tsx`. Visual
  cost feedback during a live session.
* **Avatar call lifecycle:** `web/src/routes/spokespeople/talk.tsx`.
  State machine: `idle → creating → ready → live → ended → error`.
  Useful skeleton; the push-to-speak shape is simpler.

### What NOT to borrow

* **Tool dispatch surface** (`shell/apps/realtime/dispatch.py` +
  `shell/apps/realtime/tools/`) — Rigby already has tools. Don't
  re-implement; let Rigby's existing pipeline handle them.
* **R4 knowledge-document composer**
  (`shell/character_os/realtime_document.py`) — Rigby has
  knowledge access live via its tool catalog. The document step
  is character-os-specific because Runway's conversational LLM
  needs static document context at session-create.
* **R6 session memory composer**
  (`shell/character_os/realtime_memory.py`) — Rigby already has
  conversation history. Use it.

### Carry-forward calibration findings

* `feedback_runway_tool_descriptions_gate_selection_not_narration` —
  description-embedded narration cues are ignored. Real-mode
  dogfood confirmed.
* `feedback_avatar_architecture_conversational_vs_push_to_speak` —
  pick by use case, not visual quality.
* `feedback_real_mode_dogfood_after_operator_slices` — every
  operator-facing slice gets real-mode validation. Plan dogfood
  into F2F.5 with a $1-$2 budget cap.

### Suggested first action (whenever you take this on)

Whether you act now or queue, the first action when F2F.0 starts
is to coordinate with Rigby (via `tools/pa_chat.py`) to confirm:

1. Whether u-d-b already has any push-to-speak avatar work
   started or scoped (search `docs/handoffs/` + `docs/design/`
   for "avatar", "streaming", "TTS", "HeyGen", "D-ID"). If
   there's prior work, this card may be a duplicate — say so.
2. Whether Chris wants to commit a budget for provider research
   ($0 if just reading docs; up to ~$50 if doing real API
   probes during F2F.0).

Then write the F2F.0 scope-lock doc as
`docs/design/RIGBY_FACE_TO_FACE_V1.md`, mirroring
character-os's `REALTIME_AVATAR_V1.md` pattern (contract rules,
slice list F2F.0-F2F.5, cost model, mock policy).

Do not touch character-os from your session. Bridge tools there
are operator-only dogfood now; character-os will gate them to
operator-tier (or remove them) once F2F ships on u-d-b.

### How to respond

Per `feedback_fix_shaped_handoff_compounds`, reply with a
**fix-shaped acknowledgement**:

* What you're going to do (interrupt / queue / reject).
* If queue: when you'll pick it up (next session? after current
  arc closes? specific session number?).
* If reject: what would change your mind.
* Anything character-os should do differently as a result.

The sibling CC on character-os has committed and closed
SESSION 215 there. Your response can come whenever — there's no
timer.

## --- END CARD ---
