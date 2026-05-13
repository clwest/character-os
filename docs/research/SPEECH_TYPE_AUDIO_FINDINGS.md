# `speech.type=audio` Long Ad Rewrite — Probe Findings + PR EA Plan

**Status:** Parked. Plumbing landed (PR DZ-b); duration ceiling resolved
(2026-05-12, see "PR DY-2 findings" below); plan now validated end-to-
end; PR EA still paused for other work but has **no remaining open
questions** before it can ship.

**Date:** 2026-05-10 (original), refreshed 2026-05-12 (duration probes
at 60s + 120s). Pick up from here when ready.

---

## TL;DR

- Runway's `/v1/avatar_videos` **accepts `speech.type=audio` at least
  up to 122s** with no truncation and no rate-shift. Three separate
  probes at 42s / 55s / 122s all returned drift of exactly **-0.04s**
  — that's codec rounding, not a Runway cap. The documented "1-15s
  typical" duration in `RUNWAY_AVATAR_API_DEEP_REVIEW.md` §4 only
  applies to the text path. **Net: no practical duration ceiling
  below 2 minutes; chunk-and-stitch is strictly worse than single-pass
  for ads in the 60-120s range.**
- Data URI accepted up to at least **2.5MB** (122s @ 128kbps mono MP3
  base64-encoded). Practical wire-size budget for PR EA is comfortable.
- Runway's `/v1/voices/preview` is **not** a "TTS arbitrary text in
  voice X" endpoint. It's an ElevenLabs voice-DESIGN audition endpoint
  (`{prompt, model: "eleven_ttv_v3"|"eleven_multilingual_ttv_v2"}`).
- **No Runway endpoint TTSes arbitrary text in a specific avatar's
  bound voice.** The whole `/v1/voices` family designs voices, it
  doesn't synthesize scripts.
- PR EA Long Ad rewrite needs an **external TTS source**. Build body
  is already audio-ready (PR DZ-b's `build_avatar_video_body`).
  Plumbing the orchestrator + adding a per-character TTS voice field
  + wiring an external TTS provider is what remains.
- **Lip-sync quality on `say`-generated audio holds at 60s AND 120s**
  (operator-confirmed eyeball pass 2026-05-12). External TTS upgrade
  (OpenAI `tts-1-hd`) is "polish" not "required" — `say`-quality
  prosody already lip-syncs cleanly. If the prosody-quality bump is
  worth the dependency, ship it; if not, even macOS `say` works.

---

## What's already shipped

| PR | Status | Files |
|---|---|---|
| **DY** | merged | `scripts/probe-avatar-videos-audio.py` (one-shot Runway probe) |
| **DZ-a** | merged | `scripts/probe-voices-preview.py` (one-shot voices/preview probe) |
| **DZ-b** | merged | `backend/app/services/long_ad_service.py` — extracted `build_avatar_video_body(avatar_id, *, chunk_text, audio_source)` pure helper; orchestrator still passes `chunk_text` so behaviour unchanged. 3 unit tests cover both branches + invalid combos. |

`_render_chunk_real` in `long_ad_service.py` is the wire-up point: it
already accepts `audio_source` as a keyword. PR EA wires the
orchestrator to pass `audio_source` instead of `chunk_text`.

---

## PR DY findings — `speech.type=audio` works at scale

Probe: 42.11s macOS `say`-generated MP3 → data URI → single
`POST /v1/avatar_videos` call against Riggs's avatar
(`992b4dc1-b0c4-4bf6-a06c-d26bd9fb2a9a`).

```
audio in:    42.11s          (~3× the documented 15s text-typical)
video out:   42.07s
drift:       -0.04s          (no silent truncation)
HTTP:        200             (accepted the data URI at 878 KB)
render:      61.1s wallclock
output:      18.9 MB MP4, h264 1088×704
```

Lip-sync was visually clean against macOS `say` audio — and macOS `say`
is NOT Riggs's bound Runway voice. **Lip-sync is phoneme-driven, not
voice-keyed.** Any clean audio source → clean lip-sync.

## PR DY-2 findings — duration ceiling probe at 60s + 120s (2026-05-12)

Two follow-up probes against the same avatar to settle whether the
42s success was near a hidden cap or whether `gwm1_avatars` actually
handles long inputs cleanly. Same script-shape, longer text fed to
macOS `say`.

| Probe | Audio in | Video out | Drift | Wall clock | Data URI | Output | Status |
|---|---|---|---|---|---|---|---|
| PR DY (baseline) | 42.11s | 42.07s | **-0.04s** | 61.1s | 878 KB | 18.9 MB | ✅ |
| PR DY-2 60s | 55.07s | 55.03s | **-0.04s** | 71.1s | 1.15 MB | 22 MB | ✅ |
| PR DY-2 120s | 122.10s | 122.06s | **-0.04s** | 141.3s | 2.54 MB | 51 MB | ✅ |

**The -0.04s drift is exactly constant across all three probes.** That
proves the drift is codec rounding (ffmpeg encode → Runway decode →
Runway encode → our ffmpeg probe), not Runway-side truncation. A
real cap would show progressive widening — drift growing to -5s,
-15s, etc. as we approach the limit. Instead, drift stays pinned to
the encoder-precision floor.

**Lip-sync at 122s:** operator visually confirmed both 60s and 120s
outputs track the audio cleanly end-to-end. Outputs saved at
`~/Desktop/Donkey Betz Videos/probe-60s-riggs-rally.mp4` and
`~/Desktop/Donkey Betz Videos/probe-120s-riggs-rally.mp4` for future
reference / before-and-after comparison once external TTS lands.

**Implications:**

1. **No practical duration cap below 2 minutes.** PR EA can ship as
   "single-pass for any ad up to 2 minutes" with confidence. We don't
   need a probe at 180s for v1 — 120s covers virtually every
   spokesperson-ad use case.
2. **Chunk-and-stitch (current Long Ad PR DO path) is strictly worse
   for 60s+ ads.** Single-pass: 1 API call, no concat overhead, no
   chunk-boundary seams in lip-sync. Multi-chunk: N API calls (each
   with its own polling roundtrip), ffmpeg concat overhead, sentence-
   boundary speech pauses between chunks. Chunk-and-stitch stays
   useful only when no external TTS is available (current mock-mode
   default).
3. **macOS `say` is good enough as an interim TTS.** Lip-sync tracks
   cleanly at 122s on flat `say` prosody. External TTS (OpenAI
   tts-1-hd) is "voice character" polish, not lip-sync-correctness.
4. **Data URI ceiling sits ≥2.5MB.** Means a 3-minute ad at 128kbps
   mono would be ~3.7MB — still under the practical 5MB cap. We
   don't need `/v1/uploads` for ads up to ~3.5 minutes.

**Credit burn:** approximately **300 credits** for both live fires
(rough heuristic: ~1.5 credits/sec output). Combined with the
original PR DY 42s probe, total experimental credit spend on this
research is under 500 credits.

## PR DZ-a findings — `/v1/voices/preview` is not TTS

Probe body: `{voice: {type: "runway-live-preset", presetId: "max"},
text: "..."}`. Runway responded 400 with:

```
issues:
  - path: ["prompt"]  expected: string  received: undefined
  - path: ["model"]   must be: "eleven_ttv_v3" | "eleven_multilingual_ttv_v2"
```

Interpretation: the endpoint takes `{prompt: "<voice description>",
model: "<elevenlabs-design-model>"}` and returns a sample of that
*designed* voice. The "audition before committing" doc note is
literal. You can't pass a `text` field and get TTS back. The whole
`/v1/voices` family is for designing voices, not synthesizing scripts.

This was decisive — we didn't probe the other three shapes
(`custom-block-pr-dv`, `flat-voiceId`, `from-text-design`) because the
validation error already explained the endpoint's purpose. Re-running
with `--custom-voice-id` would just produce another 400 about
`prompt`/`model`.

---

## What remains — PR EA Long Ad rewrite plan

### The TTS-source decision

Runway can't TTS arbitrary text in a specific voice. The audio source
must come from somewhere else. Three real options:

1. **OpenAI TTS** (`tts-1-hd`)
   - 6 voices: alloy, echo, fable, onyx, nova, shimmer
   - Already have OpenAI key plumbing in `audio_client.py`
   - ~$0.015 per Long Ad (30s × 1¢/1k chars)
   - Voice quality is good but doesn't match Runway preset character
2. **ElevenLabs** (their actual TTS endpoint, not Runway's
   `/v1/voices/preview` shim — Runway proxies their voice-design model
   but not their TTS endpoint)
   - 100s of voices, can match Riggs's `max`-like timbre
   - New API key required, new HTTP client wrapper
   - ~$0.06 per Long Ad
3. **Runway round-trip** (chunked text → extract audio → concat →
   re-render via audio)
   - In-vocabulary but burns 2× credits per Long Ad
   - Defeats the simplification PR EA is trying to deliver
   - Don't do this

**Recommendation: OpenAI TTS.** Smallest dependency surface, cheapest,
operator-explainable as "long-form ads use a different voice than
short ads." Per-character `tts_voice` field lets the operator pick
which OpenAI voice each spokesperson uses.

### PR EA implementation sketch

| Change | Lines | Notes |
|---|---|---|
| `Character.tts_voice: Optional[str]` (model + storage) | ~10 | Maps to `'alloy' \| 'echo' \| 'fable' \| 'onyx' \| 'nova' \| 'shimmer'`. Default `'onyx'`. |
| `services/openai_tts_client.py` (new) | ~80 | `tts_to_data_uri(text, voice)` returns `data:audio/mpeg;base64,…`. Mirrors `voice_clone_client._data_uri`. Mock path returns a deterministic silent placeholder. |
| `long_ad_service.generate_long_ad_v2` (new) | ~60 | Whole script → OpenAI TTS → single `_render_chunk_real(audio_source=…)`. No chunking. Replaces current per-chunk loop when v2 is enabled. |
| `long_ad_service` v1 ↔ v2 feature flag | ~10 | Settings field `long_ad_mode = 'chunked-text' \| 'single-pass-audio'`. Default `'chunked-text'` until proven on real campaigns. |
| Frontend Identity card — `tts_voice` picker | ~30 | Dropdown next to Voice Preset on `CharacterCard.jsx`. |
| Frontend Long Ad form — mode badge | ~10 | Shows "v2 · single-pass · OpenAI {voice}" when enabled. |
| Backend tests — mock TTS, v2 orchestrator path | ~50 | New `test_long_ad_v2_*` cluster. |

Approx 250 LoC across ~6 files. No more `chunk_script` or
`stitch_chunks` calls in the v2 path — both stay in v1 for the feature
flag's life. When v2 is the default we can deprecate v1.

### Risks to confirm during PR EA

1. **OpenAI TTS rate limits.** 50 RPM on `tts-1-hd` default tier.
   Long Ad volume is low (operator-triggered, not automated). Safe.
2. **MP3 size for ~60s audio.** 60s × 128kbps mono = ~960 KB raw,
   ~1.28 MB as data URI. Within the empirical 5 MB cap. PR DY-2
   confirmed ≥2.5 MB works at 122s.
3. ~~**`gwm1_avatars` duration cap above 42s.**~~ **RESOLVED 2026-05-12
   by PR DY-2.** No cap below 122s; drift stays constant -0.04s
   across 42s/55s/122s. PR EA can ship for ads up to 2 minutes
   without a chunk-size guess.
4. **Lip-sync quality on OpenAI voices.** PR DY-2 confirmed lip-sync
   works on `say`-quality prosody at 122s. Empirically verify on
   OpenAI `tts-1-hd` output during the PR EA real-mode smoke — but
   the expectation is "equal or better" since `tts-1-hd` has
   richer prosody.

### Things explicitly NOT in PR EA scope

- Music bed mixing — defer to PR EB
- Multi-language dub via `/v1/voice_dubbing` → audio input — defer to PR EC
- Dialogue Scene + Spokesperson Ad audio-mode — separate PR, not Long Ad

---

## Quick-start when resuming

1. Read this doc + the head-pointer entry in `00-START-NEXT-SESSION.md`
2. Skim `build_avatar_video_body` and its 3 tests
3. Decide: OpenAI TTS now, or ElevenLabs for better voice match?
4. Run the duration probe at 60s + 120s before committing to v2 default:
   ```bash
   python3 scripts/probe-avatar-videos-audio.py \
       --character-id <id> --target-duration 60 --yes-fire
   ```
5. Ship PR EA per the sketch above.

## File breadcrumbs

- `scripts/probe-avatar-videos-audio.py` — proven probe, rerun anytime
- `scripts/probe-voices-preview.py` — proven probe; conclusion documented
- `backend/app/services/long_ad_service.py:build_avatar_video_body` —
  the audio-ready helper PR EA needs
- `backend/app/services/audio_client.py` — patterns for HTTP client +
  data URI + mock fallback that PR EA's OpenAI TTS client should mirror
- `frontend/src/components/CharacterCard.jsx` — where the `tts_voice`
  picker lands

## Open questions parked for resumption

- ~~Does `gwm1_avatars` accept >60s audio?~~ **RESOLVED 2026-05-12
  by PR DY-2.** Yes, ≥122s. No probe required before shipping PR EA.
- Should `tts_voice` be on the `Character` (one voice per spokesperson)
  or on the `AdVariant` (one voice per script)?  Probably Character —
  voice = identity.
- Do we want a "Riggs sounds different in Long Ad" disclaimer in the
  UI, or is that operator-internal trivia? *(Note: PR DY-2 lip-sync
  results suggest the bound voice mismatch is largely invisible to
  viewers — phoneme-driven lip-sync hides the voice swap. Disclaimer
  is probably operator-internal.)*

**Net status:** PR EA has no remaining external-research-dependencies.
Ship when the operator decides Long Ad polish is the priority.
