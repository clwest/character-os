---
title: "Session 211 — VO arc opens (VO.0 scope lock + VO.1 foundation)"
date: 2026-05-21
status: complete
session: 211
previous_handoff: ./SESSION_210_CALIBRATION_CLOSEOUT.md
---

# Session 211 — VO arc opens

## TL;DR

SESSION 210 closed the calibration-findings queue empty.
SESSION 211 took **Candidate A** per the start-here doc:
**VO-arc scope lock**. Then, with the doc-only ½-slice
clean, opened **VO.1** in the same session — the foundation
slice ships the AssetRole enum, the media-engine provider
package, the `/internal/audio/tts/` route, and the
`synthesize_voiceover_audio` shell primitive.

The arc went from "queued" to "infrastructure live"
in one session. Two commits, **+48 tests**, zero real-mode
spend.

| # | Commit | Slice |
|---|---|---|
| 1 | `d19b1da` | VO.0 — `docs/design/VOICEOVER_V1.md` scope lock |
| 2 | (this commit) | VO.1 — TTS provider package + route + shell primitive + tests |

This is the **sixth strategic-axis arc** opened in the
project and the **first post-strategic-quartet axis** (B-1
mine / B-2 script / B-3 personalize / B-14 distribute all
closed by SESSION 210). VO returns to V-arc primitive
territory after the quartet detour.

## Test deltas

| Suite | Pre-session | Post-session | Δ |
|---|---|---|---|
| Django | 1364 | 1387 | +23 (VO.1 voiceover primitive + role enum + isolation whitelist + cost paths) |
| Media-engine | 221 | 246 | +25 (TTS route + dispatch chain + provider drift verifier + mock-mode determinism) |
| SPA vitest | 456 | 456 | 0 (no SPA work this slice) |
| **Total** | **2041** | **2089** | **+48** |

INVENTORY regenerated. Media-engine route count went
137 → 138 (`POST /internal/audio/tts/` added). Primitive
registry 21 → 22 (`synthesize_voiceover_audio`).

## VO.0 — what landed (commit `d19b1da`)

`docs/design/VOICEOVER_V1.md` at ~390 lines following the
AUTO_SCRIPTING_V1 template. All 9 contract rules + 9 open
questions accepted as-proposed at lock.

**The arc shape (locked):**

| Primitive | Cost | Provider |
|---|---|---|
| `synthesize_voiceover_audio(text, voice_spec)` | ~$0.01 | `/internal/audio/tts/` route behind a `TextToSpeechProvider` Protocol |
| `overlay_audio_at_offset(base, vo, offset, duck_db?)` | ~$0 marginal | `/internal/clips/overlay_audio/` ffmpeg route (VO.2) |

| Recipe (VO.3 + VO.4) | Steps | Cost |
|---|---|---|
| `cta_swap` | `talking_head → tts → overlay (end of clip)` | ~$0.26 |
| `narrated_intro` | `tts → talking_head → overlay (offset=0)` | ~$0.26 |

**Cost win vs. workaround**: today an operator wanting a
4-second CTA in a different voice fires a whole second
`talking_head` ($0.25) and `audio_extract`s from it. VO arc
ships the same result for ~$0.01 of TTS — **25× cheaper**.

**Q-vo-2 (load-bearing) resolution**: Runway-first chain with
ElevenLabs direct fallback behind the Protocol. Locked because
`audio_client.py:19` recorded the deferral but the gating
status may have changed; the dispatcher catches gated 4xx
markers and falls through transparently.

## VO.1 — what landed (this commit)

Foundation slice. Everything VO.2 / VO.3 need is now on
the table.

### Model + migration (rule 1)

* **`AssetRole.VOICEOVER_AUDIO`** added to
  `apps/compositions/models.py`. Wire value
  `"voiceover_audio"`. 11th role.
* **Migration `compositions/0010_vo_1_voiceover_audio_role`**
  — `AlterField` on `Asset.role`. TextChoices metadata bump;
  no DDL.
* **`asset_roles.PRIMITIVE_TO_ROLE`** gains
  `"synthesize_voiceover_audio" → VOICEOVER_AUDIO` so the
  contract-rule-20 coverage test passes + the backfill
  command honors the new role.
* **`test_asset_role_enum_has_eleven_values`** replaces the
  ten-value invariant test; renamed for clarity.

### Media-engine `tts_provider` package (rule 9)

New package at `media-engine/app/services/tts_provider/`
mirroring `realtime_provider/`:

* **`__init__.py`** — `TextToSpeechProvider` Protocol +
  `TtsSpec` / `TtsResult` dataclasses + `TtsProviderError` /
  `TtsUnavailableError` + `get_provider(name, settings)`
  registry.
* **`mock.py`** — `MockTtsProvider`. Deterministic
  cache-keyed silent MP3 via `_ffmpeg_silent_mp3` helper.
  Duration heuristic at 11 chars/sec (mirrors
  `_AVATAR_SPEECH_CHARS_PER_SECOND` so VO.2's offset math is
  stable across mock + real modes).
* **`runway.py`** — `RunwayTtsProvider`. Targets
  `POST {runway_api_base}/v1/text_to_speech`. Gated-feature
  detection: 404 + 4xx-with-gated-marker bodies raise
  `TtsUnavailableError` so the dispatcher falls through to
  ElevenLabs. Defensive payload parsing handles fall-back
  keys (`previewUrl` / `preview_url` / `audioUrl` / `url`).
* **`elevenlabs.py`** — `ElevenLabsTtsProvider`. Targets
  `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
  with `xi-api-key` header. Streams audio/mpeg directly to a
  cached MP3 at `data/_internal/voiceovers/<hash>.mp3` keyed
  off `hash(voice_id|model|text)` — idempotent re-calls.
  Duration via `ffprobe`; 25MB-per-call cap.

### Config additions

* `elevenlabs_api_key: str = ""`
* `elevenlabs_api_base: str = "https://api.elevenlabs.io"`
* `voiceover_tts_force_mock: bool = False`
* `voiceover_tts_default_provider: str = "auto"`

### Route — `POST /internal/audio/tts/`

Dispatch chain implements Q-vo-2:

1. `provider="mock"` OR force-mock env OR (auto chain
   with no Runway + no ElevenLabs configured) →
   `MockTtsProvider`.
2. `provider="runway"` → `RunwayTtsProvider`; explicit
   request fails 503 on `TtsUnavailableError` (operator
   asked for runway specifically).
3. `provider="elevenlabs"` → `ElevenLabsTtsProvider`; 503
   if no `ELEVENLABS_API_KEY`.
4. `provider="auto"` (default) → tries Runway first,
   catches `TtsUnavailableError`, falls through to
   ElevenLabs. Returns 503 with both upstream messages if
   the whole chain fails.

Response shape: `{audio_url, voice_id, duration_seconds,
size_bytes, model, provider, cost_micros, mock_mode}`.

### Shell primitive — `synthesize_voiceover_audio`

`shell/apps/compositions/primitives/voiceover.py`. Handles
all three voice_spec discriminators (rule 8 — exactly-one-of):

1. **`{spokesperson_id}`** — workspace-scoped lookup via
   `Spokesperson.objects.get(id=..., workspace_id=
   composition.workspace_id)`. Cross-workspace raises with
   "(rule 2: cross-workspace voice_specs are rejected)"
   in the message.
2. **`{voice_id}`** — used directly. No workspace check
   (operator-supplied ids are accepted on the assumption
   they have access).
3. **`{voice_design}`** — fires `MediaEngineClient.design_voice`
   sub-call to mint a new voice_id, then synthesizes.
   Total cost = TTS (10k micros) + design (100k micros).

Rule 3 (no avatar pipeline) is structural: the primitive only
calls `/internal/audio/tts/`, never `/internal/clips/avatar_speech/`.

Rule 1 provenance: full `source_spec` carries `primitive_kind`,
`script`, `script_chars`, `voice_id`, `model`, `provider`,
`provider_pref`, `voice_spec_discriminator`, and
discriminator-specific extras (spokesperson_name,
voice_design_description, etc.).

### Registry + cost

* `primitives/__init__.py` adds
  `"synthesize_voiceover_audio": SynthesizeVoiceoverAudioPrimitive`.
  Count goes 21 → 22.
* Cost via `estimate_cost(params)` on the primitive class:
  10_000 micros base, +100_000 micros for the voice_design
  path. Same shape as the V14 / V10 cost discipline.

### Tests

* **23 Django tests** in `apps/compositions/tests/test_vo1_voiceover.py`:
  enum coverage (2), registry (1), cost model (2),
  voice_spec resolver happy paths (3) + error paths (6),
  primitive execute mock-mode (3), primitive execute
  validation (2), primitive execute real-mode (3) + zero-
  duration fallback. Plus updates to
  `test_asset_role_enum_has_ten_values` →
  `..._has_eleven_values` and the isolation whitelist for
  the new test file.
* **25 media-engine tests** in `tests/test_vo1_tts_endpoint.py`:
  route happy paths (3), validation errors (3),
  auto-fallback to mock (1), real silent-MP3 generation
  (1), idempotency cache hit (1), Protocol surface drift
  (1), per-provider drift (parametrized × 3 = 3),
  no-NotImplementedError drift (parametrized × 3 = 3),
  registry behavior (5), package directory drift (1),
  mock provider direct exercises (2). Drift verifier
  mirrors R10's shape end-to-end.

## What didn't happen

- **No SPA work** — `voice_picker` form-field type lands in
  VO.5.
- **No real-mode dogfood** — VO.6 fires `cta_swap` against
  the keeper + Sasha's voice; needs VO.2/VO.3/VO.4 first.
- **No `overlay_audio_at_offset`** — VO.2's slice.
- **No new recipes** — VO.3 + VO.4.
- **No subagent dispatched** — VO.0 + VO.1 ran inline.

## Calibration moments worth carrying

- **Two slices in one session is now a proven cadence.**
  SESSION 210 stacked six ½-slices. SESSION 211 stacked two
  (VO.0 doc + VO.1 code) — different size classes (½ + 1)
  but the discipline is the same: well-scoped first slice
  + clean handoff doc keeps the second from re-orienting.
- **Pre-existing test fixtures need careful inventory after
  enum additions.** Three Django tests failed on the first
  run — all about the new role enum entry. None were obvious
  from the diff; all surfaced via the full-suite run. Quick
  fixes (whitelist update, role-mapping entry, count
  invariant rename) but the failures took ~10 minutes to
  triage. Pattern for future enum-adding slices: run
  `pytest --collect-only -q` to enumerate affected tests
  before writing new ones.
- **Provider abstraction pattern repeats well.** Third time
  the project ships `Protocol + Mock + RealImpl(s)` (V2's
  step primitives, R2's realtime providers, VO.1's TTS).
  Each one took less time than the last. The shape is
  canonical: drift verifier + force-mock env flag + lazy
  imports in `get_provider`.
- **Runway TTS may or may not be gated.** Q-vo-2's hedge
  (Runway-first with auto-fallthrough) means VO.1 ships
  without needing to probe Runway's surface during the
  slice. If Runway has opened TTS up since the
  `audio_client.py:19` deferral, the chain just works; if
  not, ElevenLabs takes over. **VO.6 dogfood will surface
  which path is active.**
- **Pyright noise on sibling-module imports is the cost of
  the package-pattern.** Pyright can't resolve
  `from .runway import RunwayTtsProvider`-style siblings
  through `__init__.py` re-exports. Runtime is fine, but
  the IDE warnings stack up. Future provider arcs will hit
  the same noise; we accept it because the runtime tests
  are the source of truth.

## Test counts at SESSION 211 close

| Suite | Count |
|---|---|
| Django | 1387 (+23) |
| Media-engine | 246 (+25) |
| SPA vitest | 456 (unchanged) |

INVENTORY regenerated against the post-VO.1 working tree.
Media-engine routes 137 → 138. Primitive registry 21 → 22.
Migration count: `compositions/0010_vo_1_voiceover_audio_role`
is the new tip.

**Env caveat (unchanged from SESSION 210)**: 3 tests in
`apps/scripts/tests/test_api.py` require
`EMBEDDING_FORCE_MOCK=1`. Running with the flag yields a
clean **1387/1387** result.

## Next session (SESSION 212)

VO.2 opens — `overlay_audio_at_offset` primitive +
`/internal/clips/overlay_audio/` ffmpeg route. ½ session.
Path:

1. **`/internal/clips/overlay_audio/`** route — pure ffmpeg
   filter graph (`amix` + `adelay` + `volume` window with
   `between(t,offset,offset+vo_duration)`).
2. **`overlay_audio_at_offset` shell primitive** — rule 6
   validation (`offset + vo_duration > base_duration` →
   `PrimitiveError`); rule 4 invariant (re-encode audio
   only; `-c:v copy`). Slots: `base` (CLIP) + `voiceover`
   (AUDIO).
3. **Tests** — offset math, duck_db range, base-video-byte-
   identity assertion, validation errors.

After VO.2 lands, VO.3 (`cta_swap` starter + recipe registry +
`voice_picker` field type) opens with both primitives wired.
