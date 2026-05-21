---
title: "Session 211 — VO-arc scope lock (sixth strategic-axis arc)"
date: 2026-05-21
status: complete
session: 211
previous_handoff: ./SESSION_210_CALIBRATION_CLOSEOUT.md
---

# Session 211 — Voiceover-arc scope lock

## TL;DR

SESSION 210 closed the calibration-findings queue empty.
SESSION 211 took **Candidate A** per the start-here doc
recommendation: **VO-arc scope lock**. Doc-only ½-slice;
`docs/design/VOICEOVER_V1.md` shipped at ~390 lines following
the AUTO_SCRIPTING_V1 template. All 9 contract rules + 9 open
questions accepted as-proposed at lock.

This is the **sixth strategic-axis arc** locked in the project,
and the **first post-strategic-quartet axis** (B-1 mine / B-2
script / B-3 personalize / B-14 distribute all closed by
SESSION 210). VO returns to V-arc primitive territory after
the quartet detour.

**No code, no real-mode spend, no test deltas this session.**
The deliverable is the design lock that lets VO.1-VO.6 ship
cheaply in subsequent sessions.

## What landed

| Commit | Slice |
|---|---|
| (this commit) | VO.0 — `docs/design/VOICEOVER_V1.md` + 00-START refresh + handoff |

One commit. The whole session.

## The arc shape

| Primitive | Cost | Provider |
|---|---|---|
| `synthesize_voiceover_audio(text, voice_spec)` | ~$0.01 | new `/internal/audio/tts/` endpoint behind a `TextToSpeechProvider` Protocol (Runway-first, ElevenLabs direct fallback) |
| `overlay_audio_at_offset(base, vo, offset_seconds, duck_db?)` | ~$0 marginal | new `/internal/clips/overlay_audio/` ffmpeg endpoint |

| Recipe | Steps | Cost |
|---|---|---|
| `cta_swap` | `talking_head` → `synthesize_voiceover_audio` → `overlay_audio_at_offset` (end of clip) | ~$0.26 |
| `narrated_intro` | `synthesize_voiceover_audio` → `talking_head` → `overlay_audio_at_offset(offset=0)` | ~$0.26 |

**Cost win vs. the workaround**: today an operator wanting a
4-second CTA in a different voice fires a whole second
`talking_head` ($0.25) and `audio_extract`s from it. VO arc
ships the same result for ~$0.01 of TTS — **25× cheaper**.

## Contract rules (9 locked)

1. VO audio is a first-class `Asset(AUDIO, role=VOICEOVER_AUDIO)`.
2. VO synthesis is workspace-scoped (voice_spec resolves against
   workspace-visible voice ids only).
3. VO synthesis does not fire the avatar video pipeline (rule 3
   is the entire reason this arc exists — the cost gap).
4. Overlay preserves the base clip's video stream byte-for-byte
   (`-c:v copy`).
5. Ducking is structural with operator-tunable `duck_db` (default
   -18); crossfade ms fixed at 300/300 in v1.
6. Offset validates against base duration; over-shoot raises
   `PrimitiveError` with an actionable message — no silent
   truncation.
7. VO audio inherits no transcript / caption ownership; captions
   on overlaid CLIP cover base audio only.
8. Voice identity is per-call, not persisted on the recipe (no
   workspace-level "default VO voice" in v1).
9. TTS provider abstraction lives in media-engine; shell never
   imports providers directly. Mirrors R2's `RealtimeProvider`
   Protocol + R10's drift verifier.

## Open questions (all 9 locked as-proposed)

| # | Question | Resolution |
|---|---|---|
| Q-vo-1 | One primitive or two? | TWO (TTS + overlay separable for B-13/upload composability) |
| Q-vo-2 ⭐ | TTS provider? | Runway first; ElevenLabs direct fallback behind `TextToSpeechProvider` Protocol |
| Q-vo-3 | Ducking semantics? | Window-only with crossfade (full-clip duck would break `narrated_intro`) |
| Q-vo-4 | voice_spec shape? | Single dict with exactly-one-of discriminator |
| Q-vo-5 | `cta_swap` default offset? | `base_duration - cta_duration - 0.5` (end of clip + tail buffer) |
| Q-vo-6 | Tier dimension? | Count under `videos_per_month`; no separate `voiceovers_per_month` in v1 |
| Q-vo-7 | Asset Library visibility for VO audio? | BROWSABLE (rule 1 enables cross-composition reuse) |
| Q-vo-8 | VO.6 real-mode validation? | Keeper talking_head + Sasha's voice CTA |
| Q-vo-9 | One recipe or two? | TWO (`cta_swap` + `narrated_intro` — operator-facing labels load-bearing per V15 calibration) |

Q-vo-2 was the load-bearing one — Runway's `/v1/text_to_speech`
was deferred per `audio_client.py:19` ("voice.type discriminator
gated by Runway and could not be unlocked via probing"). VO.1
will try Runway again first; if still gated, ElevenLabs direct
takes over using the same `voice_id` (Runway voices are
ElevenLabs-backed so the ids transfer).

## Slice queue (7 slices, VO.0-VO.6)

| # | Slice | Status | Effort |
|---|---|---|---|
| VO.0 | This scope-lock doc | ✓ SHIPPED SESSION 211 | ½ session |
| VO.1 | `AssetRole` enum + `/internal/audio/tts/` + `TextToSpeechProvider` + `synthesize_voiceover_audio` primitive + force-mock flag | Next | ½ session |
| VO.2 | `/internal/clips/overlay_audio/` + `overlay_audio_at_offset` primitive | Queued | ½ session |
| VO.3 | `cta_swap` starter + recipe registry + `voice_picker` field type | Queued | ½ session |
| VO.4 | `narrated_intro` starter + duration estimator helper | Queued | ½ session |
| VO.5 | SPA recipe gallery `voice_picker` wiring (3-tab control) | Queued | 1 session |
| VO.6 | Real-mode dogfood (keeper + Sasha CTA) + arc close | Queued | ½ session |

**Total remaining: ~3-4 sessions.** Smaller than B-2's 5
because there's no new Django app, no new model, no REST
surface — just two primitives + two recipes + a small SPA
field-type extension.

## What didn't happen

- **No code.** Pure design slice. The scope-lock pattern is
  doc-before-code by V/R/B-arc precedent.
- **No real-mode spend.** No Runway calls, no Asset rows,
  no Composition rows. Zero $.
- **No subagent dispatched.** Single-session inline work.
- **No test deltas.** Django still **1364**, media-engine
  still **221**, SPA vitest still **456** = **2041 total**.
- **No INVENTORY regen needed.** Doctor warned `git_sha
  000dd94 vs HEAD b2b88f4` at session start; that's still
  doc-only drift (b2b88f4 was the SESSION 210 close docs
  commit). No runtime change this session either, so the
  same drift persists — non-blocking.

## Calibration moments worth carrying

- **Scope-lock cadence is now 6-for-6** across all six
  strategic-axis arcs (V / R / F / A-arc + B-1/B-2/B-3/
  B-14 strategic quartet + VO). Pattern: write the lock
  doc, propose answers to every open question, operator
  signs off as-proposed almost every time. The "operator
  reviews + corrects" path has been the exception, not the
  rule. Five of six locks landed as-proposed; the
  exception (R7 sub-slicing under SESSION 148's calibration)
  was a structural change, not a resolution change.

- **Provider abstraction pattern is now canonical.** R2's
  `RealtimeProvider` Protocol shape repeats here as
  `TextToSpeechProvider`. Same pattern: Protocol +
  concrete-provider classes + mock variant + drift
  verifier test + env-flag selection. Future external-API
  integrations should default to this shape.

- **The "two primitives + two recipes + one enum entry"
  shape is the cheapest possible arc.** AUTO_SCRIPTING (B-2)
  was the previous floor at ~5 sessions; VO comes in
  smaller because there's no new persistence at all. When
  a future arc proposal can be expressed as "N primitives
  + M recipes + zero schema change," it should ship faster
  than 5 sessions.

- **Doc-only sessions still produce a handoff.** The
  context-kit pattern requires it whether or not code
  shipped. This handoff exists so SESSION 212 can open VO.1
  cold and have the full design context cached.

- **Real-mode dogfood streak holds at 10-for-10 entering
  SESSION 212.** SESSION 211 doesn't reset it (no real-mode
  fired). VO.6's keeper + Sasha CTA dogfood will be the
  next test.

## Test counts at SESSION 211 close

| Suite | Count | Δ |
|---|---|---|
| Django | 1364 | 0 |
| Media-engine | 221 | 0 |
| SPA vitest | 456 | 0 |
| **Total** | **2041** | **0** |

Pre-existing env-shape caveat (3 tests in
`apps/scripts/tests/test_api.py` require `EMBEDDING_FORCE_MOCK=1`)
unchanged.
