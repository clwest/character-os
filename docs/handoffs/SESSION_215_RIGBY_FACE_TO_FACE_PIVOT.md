---
title: "Session 215 — Bridge tools pivot: Rigby Face-to-Face moves to u-d-b"
date: 2026-05-21
status: complete
session: 215
previous_handoff: ./SESSION_214_QR2_DOGFOOD_PLUS_EMBED_FIX.md
---

# Session 215 — Bridge tools pivot to u-d-b

## TL;DR

Three slices and an architectural pivot:

1. **Slice A** (consult_engine / query_spider_data / agent_consult
   pre-narration cue + screen-handoff) shipped, then **real-mode
   dogfood proved Runway's LLM ignores "Before invoking, voice X"
   instructions in tool descriptions** — same class of bias as
   `feedback_runway_avatar_greeting_bias`. Bridge tools fired
   successfully, SPA panel rendered the answers, but the avatar
   stayed silent after.
2. **Slice B** (SPA `BridgeAnswerPanel` that renders the answer +
   topic + latency for the operator to read) shipped and works as
   designed. Operator-narrated loop is the v1 reality.
3. **Slice C** — the pre-narration cue was dropped from all three
   bridge descriptions and the contract test inverted (now
   asserts the cue is **absent**). Descriptions are honest about
   what they can and cannot steer.
4. **Architectural pivot.** The bridge tools were trying to make a
   Character OS spokesperson narrate answers from the operator's
   own u-d-b PA. The use case is actually **"talk to Rigby
   face-to-face"** — a u-d-b feature, not a character-os one. End
   customers of Character OS don't have a u-d-b. The bridge tools
   are now operator-only dogfood (soft-deprecated); the real
   product moves to u-d-b.

| Commit | Slice |
|---|---|
| (pending) | feat(realtime): bridge-tool answer panel + pre-narration cue (slice A+B) |
| (pending) | refactor(realtime): drop bridge-tool pre-narration cue — Runway LLM ignores it (slice C) |
| (pending) | docs(realtime): soft-deprecate bridge tools — Rigby F2F moves to u-d-b |

**Test totals at SESSION 215 close**: Django **1436** (1424 →
1436, +12). Media-engine **258** (unchanged). SPA vitest **458**
(456 → 458, +2).

**Real-mode spend**: one verification session ($-tbd). Bridge tools
fired (`consult_engine` + `query_spider_data` both succeeded),
panel rendered, avatar silent after — exactly the symptom the
pivot resolves.

---

## Slice A — Pre-narration cue (shipped, then reverted in C)

### What we tried

Each bridge tool's description got a sentence:
*"Before invoking, voice a brief acknowledgement like "Let me
check with the engine — one moment"; the full answer renders on
screen for the operator."*

The intent: give the avatar a verbal beat to cover the 4-10s
engine round-trip, since Runway's SDK is one-way (avatar → SPA)
and the avatar literally never sees the tool result.

### What happened in real mode

Operator drove a real session. Both `consult_engine` and
`query_spider_data` fired successfully (rows in
`RealtimeToolInvocation` show `succeeded`). SPA panel rendered
the answers. Avatar **did not voice the stall phrase** — went
silent for the round-trip, then stayed silent after the result
arrived.

### Calibration

Runway's avatar LLM reliably uses tool descriptions to gate
**when** a tool fires. It does **not** reliably follow imperative
behavior instructions ("Before invoking, voice X") embedded in
those descriptions. Same class of bias documented at
`feedback_runway_avatar_greeting_bias` (greeting injection
ignored via document / personality edits).

**Fix-shaped finding for memory:** *"Tool descriptions gate
selection, not narration. Pre-narration cues embedded in
descriptions are ignored by Runway's LLM in real mode."*

### What slice C did about it

Dropped the cue from all three descriptions. Added a "no recite"
directive instead: *"the avatar's role is to invoke, not recite."*
Inverted the contract test —
`test_bridge_tool_description_has_no_pre_narration_cue` now
fails if a future refactor re-adds the cue.

Files:
* `shell/apps/realtime/tools/consult_engine.py:104-120` —
  description rewritten (496 → 451 chars).
* `shell/apps/realtime/tools/query_spider_data.py:84-100` —
  description rewritten (428 → 360 chars).
* `shell/apps/realtime/tools/agent_consult.py:87-104` —
  description rewritten (449 → 410 chars).
* `shell/apps/realtime/tests/test_bridge_tool_descriptions.py` —
  module docstring + cue test inverted.

---

## Slice B — Bridge answer panel (shipped, working)

`web/src/routes/spokespeople/talk.tsx` `ToolResultPanel` extended
with `isBridgeAnswer` routing + new `BridgeAnswerPanel`. Renders:

* Heading (Engine / Spiders / *AgentName*) based on
  `result.event`.
* Topic / question (italic, secondary).
* Latency (formatted as Xs).
* Full answer prose (`whitespace-pre-wrap`) — or error message
  in destructive color.
* Engine URL (mono, foot, low-emphasis).

Two new SPA vitest tests cover success + timeout-error render
paths. Existing 15 `talk.test.tsx` tests still pass.

This panel is the operator's reading material. The avatar
doesn't narrate it; the operator reads it and verbally hands
context back to the avatar (the v1 narration story already
documented at `web/src/components/avatar-session-inner.tsx:14-29`).

---

## The pivot — Rigby Face-to-Face → u-d-b

### Why the bridge architecture is wrong here

The bridge tools have a weird product shape:

* A Character OS spokesperson (customer-facing marketing avatar)
* HTTPs over to u-d-b
* Reaches u-d-b's Rigby PA (operator's personal assistant)
* Returns an answer
* The Character OS avatar tries to narrate it

This only makes sense when **you** (the operator) are using a
spokesperson as a face for **your own** engine. End customers of
Character OS don't have a u-d-b. They don't need bridge tools at
all — their spokesperson should know their business via K2 +
business_brief.

### The actual product

"Talk to Rigby face-to-face" belongs **on u-d-b**, not character-os.
And its architecture is fundamentally different from Character OS's
realtime avatar:

| | Character OS | u-d-b Rigby F2F |
|---|---|---|
| LLM lives | Inside Runway session (closed) | u-d-b's PA pipeline (ours) |
| Avatar role | Conversational agent | Lip-sync renderer |
| Provider style | Runway `gwm1_avatars` | Push-to-speak (HeyGen / D-ID / similar) |
| Knowledge | Pre-loaded document at create time | Whatever Rigby's PA can reach live |
| Narration constraint | Avatar can't read tool results | No constraint — TTS is OUR pipeline |

The u-d-b version has the right shape natively: operator speaks
→ STT → Rigby PA (GPT-5.2 + tools + spiders) → TTS → avatar
lip-syncs. No bridge. No narration gap.

### Where Character OS bridge tools land after the pivot

**Soft-deprecated as v1 dogfood seam.** Module-level comments in
all three tools + the SPA panel point to this handoff. They
remain functional so the operator can keep dogfooding their
spokespeople against Rigby until the u-d-b feature ships.

End-customer gating (so the bridge tools don't surface in
customer workspaces) is **NOT** yet implemented. Two simple
levers when needed:

* Bump `tier_required` on each bridge tool from `'starter'` to
  `'agency'` (limits exposure to the highest tier).
* Or add a `dogfood_only=True` ToolSpec field that
  `get_workspace_tools` filters on for non-operator workspaces.

Either is < 1 hour of work; defer until the u-d-b F2F ships and
end customers start onboarding to character-os.

---

## u-d-b F2F implementation outline (for next u-d-b session)

> **CLAUDE.md constraint reminder:** u-d-b is read-only from
> *this* repo. The work below has to happen in a u-d-b Claude
> session.

### Architecture

```
operator mic ──► STT (Whisper / Runway / etc.)
                  │
                  ▼
              Rigby PA (existing u-d-b /api/pa/chat/)
                  │
                  ▼ answer text
              TTS (ElevenLabs / Runway / Cartesia)
                  │
                  ▼ audio
              Avatar lip-sync (HeyGen Streaming / D-ID Live /
                similar push-to-speak)
                  │
                  ▼ video stream
              Operator screen
```

### Provider candidates (push-to-speak avatars)

* **HeyGen Streaming Avatar API** — supports text → live avatar
  with sub-second latency. Has a `speak()` endpoint that takes
  text + voice id. WebRTC streaming. Probably the best fit.
* **D-ID Live Portrait API** — similar shape. Often cheaper but
  less polished lip-sync.
* **Runway again** — only if Runway ships a `speak()` API. Worth
  checking when the u-d-b work starts; might have moved since
  SESSION 215. As of right now no such API in
  `@runwayml/avatars@0.16.0` (verified by reading
  `node_modules/.pnpm/@runwayml+avatars@0.16.0_.../dist/index.d.cts:163`
  — `AvatarSession` class has no `speak` / `say` / `sendText` /
  `publishText`).

### v1 slices for u-d-b F2F

1. **F2F.0 — Scope lock.** Pick provider, document architecture,
   confirm cost model. ½ session.
2. **F2F.1 — Provider abstraction + first impl.** Parallel to
   `RealtimeProvider` Protocol pattern from character-os R2.
   Single named adapter; one v1 provider; mock for tests. 1
   session.
3. **F2F.2 — `/api/pa/voice_session/` broker.** New endpoint on
   u-d-b's Django that creates a streaming session and returns
   SDK-safe payload. Mirrors character-os `RealtimeSession`
   broker but with a push-to-speak shape. 1 session.
4. **F2F.3 — STT → Rigby → TTS pipeline.** Wire operator mic
   stream through STT (Whisper Realtime API?), pipe text into
   existing `/api/pa/chat/` endpoint (existing!), pipe answer
   into TTS, stream audio back to avatar. 1-2 sessions.
5. **F2F.4 — u-d-b SPA route.** New page on u-d-b's UI (or admin
   surface) — `/rigby/talk`. Mirrors character-os
   `/spokespeople/:id/talk` but simpler (one Rigby, no
   spokesperson picker). 1 session.
6. **F2F.5 — Real-mode dogfood.** End-to-end with real provider.
   Cost cap $1. ½ session.

Total: ~5 sessions if everything lands clean.

### What u-d-b can borrow from character-os

* `apps.realtime` model shape (RealtimeSession, RealtimeToolInvocation).
* `RealtimeProvider` Protocol + mock provider pattern.
* `compose_realtime_document` idea (but inverted — Rigby's PA
  pipeline already has knowledge access, so the doc step is
  redundant; just use Rigby's existing system prompt).
* Cost ticker UI from `web/src/components/cost-ticker.tsx`.
* `AvatarCall` lifecycle pattern from `talk.tsx`.

Don't borrow:
* Tool dispatch surface — Rigby already has tools; no need to
  re-implement.
* R6 session memory — Rigby already has conversation history.

---

## Test counts at SESSION 215 close

| Suite | Count | Δ |
|---|---|---|
| Django | **1436** | +12 (bridge description contract tests) |
| Media-engine | **258** | unchanged |
| SPA vitest | **458** | +2 (bridge answer panel render tests) |

All green. `EMBEDDING_FORCE_MOCK=1 pytest apps/realtime` reports
172 passed locally (subset for the realtime arc).

---

## Calibration moments worth carrying

1. **Tool descriptions gate selection, not narration.** Runway's
   LLM uses descriptions to decide WHEN to fire, but ignores
   imperative behavior instructions ("Before invoking, voice X")
   embedded in them. Same class of bias as
   `feedback_runway_avatar_greeting_bias`. Memory update
   warranted — proposed key:
   `feedback_runway_tool_descriptions_gate_selection_not_narration`.
2. **Architectural smell: bridge tools.** When a feature on one
   repo needs to bridge into another repo to be useful, the
   feature usually belongs on the OTHER repo. The bridge shape
   solves access but doesn't solve product fit. Memory update
   warranted — proposed key:
   `feedback_bridge_tools_signal_wrong_repo`.
3. **Runway's realtime avatar ≠ push-to-speak avatar.**
   Conversational LLM-driven avatars (Runway gwm1_avatars,
   probably others) own the LLM server-side; you can't push text
   at them. Push-to-speak avatars (HeyGen, D-ID) take text +
   voice and render lip-sync. They look the same to users but
   require completely different product architectures. Pick on
   the use case, not the visual quality. Memory update
   warranted — proposed key:
   `feedback_avatar_architecture_split_conversational_vs_push_to_speak`.

---

## Next session priorities

**FIRST THING:** Continue with the queued VO-arc work (VO.3
`cta_swap`) — the bridge-tools arc is closed on character-os.

**If returning to F2F:** open a u-d-b Claude session and start
with the F2F.0 scope-lock outlined above. This handoff is the
inheritance for that session — link to it from the u-d-b session
opener.

**Memory updates:** the three calibration findings above are
worth proposing as new memory entries.
