---
title: "Voiceover (VO) — post-hoc audio insertion at time offsets"
status: locked
proposed: 2026-05-21 (SESSION 211, slice VO.0)
locked: 2026-05-21 (SESSION 211, slice VO.0)
closed: null
companion_docs:
  - VIDEO_COMPOSITION_V1.md
  - AUTO_SCRIPTING_V1.md
  - CONTENT_FORMAT_BACKLOG.md
  - MEDIA_ENGINE_INTERNAL_API.md
---

# Voiceover — post-hoc audio insertion at time offsets

> **Status: LOCKED (SESSION 211).** Sixth strategic-axis arc
> (the first post-quartet axis). Targets the "different speaker
> reads the CTA" use case the V-arc's 18 recipes don't address:
> generate a voiceover audio clip (text → speech, distinct voice)
> and splice it into an existing render at a specific time offset.
> Nine contract rules; seven slices VO.0-VO.6. Estimated 3-4
> sessions to ship. All nine open questions accepted with
> proposed resolutions at lock. VO.1 (`AssetRole` enum +
> `/internal/audio/tts/` + `synthesize_voiceover_audio` primitive)
> opens next session.

---

## TL;DR

The 18 V-arc recipes bake one voice per render. Every word in a
`talking_head` or `long_form_ad` comes from the
spokesperson-bound voice; there is no way to insert a second
voice for a CTA line, a hand-off (*"and now back to you,
Jessica…"*), or a narrated intro/outro without re-baking the
entire clip against a different spokesperson.

**VO-arc adds two primitives and two recipes that compose into
multi-voice renders without touching `generate_avatar_speech`.**

1. `synthesize_voiceover_audio(text, voice_spec)` — text-to-speech
   only. Returns an `Asset(role=VOICEOVER_AUDIO, asset_type=AUDIO)`
   without firing the avatar-video pipeline. ~$0.01 per call.
2. `overlay_audio_at_offset(base_clip, vo_audio, offset_seconds,
   duck_db?)` — ffmpeg-only. Splices a VO audio clip into a base
   CLIP's audio track at `offset_seconds`, ducks the original
   audio under the VO window, returns a new CLIP. ~$0 marginal.

And two recipes:
* `cta_swap` — `talking_head` → `synthesize_voiceover_audio` →
  `overlay_audio_at_offset`. The CTA line at the end of an ad
  reads in a different voice from the body of the ad.
* `narrated_intro` — `synthesize_voiceover_audio` →
  `talking_head` → `overlay_audio_at_offset(offset=0)`. A
  voiceover hook precedes the main avatar narration.

Out of scope for v1: mid-clip voiceover (multiple offsets in
one render); SFX / Foley layering (B-12 in the backlog); the
operator's own voice clone (B-13); live-mix preview before
rendering; multi-language voiceover (V10's `dub_audio` covers
post-render translation already); cross-spokesperson voiceover
identity reuse (rule 8).

---

## Why now

Five drivers converge:

1. **The use case is concrete and pre-validated.** Real-mode
   dogfood in SESSION 158/173-174/209 surfaced operator-typed
   CTAs of the shape *"Now accepting briefs, email
   jessica@247globalai.com…"* — SESSION 210's intro/outro
   auto-wrap fix shipped because operators were running into
   exactly this pattern. The next obvious step is letting a
   *different* voice deliver that line.
2. **Every primitive needed already half-exists.**
   `audio_extract` (V14) produces AUDIO assets from CLIPs;
   `mix_audio` (V7) layers AUDIO under CLIP via ffmpeg;
   `design_voice` (V10) creates distinct voice ids on
   Runway-via-ElevenLabs. The gap is (a) a TTS primitive that
   doesn't fire the avatar video pipeline, and (b) an
   offset-aware audio overlay that isn't just background music.
3. **TTS-only is structurally cheaper than re-baking.**
   `talking_head` costs ~$0.25; a TTS-only call is ~$0.01.
   Operators who want a 4-second CTA in a different voice
   today have to fire a whole second `talking_head` and
   `audio_extract` from it — a 25× cost waste.
4. **No new persistence.** Two primitives + two recipes; no
   new models, no new tables, no new migrations. The new
   `VOICEOVER_AUDIO` asset role slots into the existing
   `AssetRole` enum (one TextChoices update). Same
   no-persistence pattern as F-arc + V16 + V17.
5. **Sequenced cleanly after the strategic quartet.** B-1/B-2/
   B-3/B-14 (mine → script → personalize → distribute) all
   closed; VO is the first arc that returns to V-arc primitive
   territory after the quartet. The recipe-gallery surface
   from V15 + B2.4 absorbs the two new recipes without
   structural change.

---

## Contract rules (load-bearing)

Nine rules. None overlap V1's existing 22 + B-1's 8 + B-3's 9 +
B-14's 5 + B-2's 10. VO rules become V1 rules 66-74 if a future
V-arc lock merges them; v1 keeps them on this doc.

1. **VO audio is a first-class Asset.** Every
   `synthesize_voiceover_audio` call persists an
   `Asset(asset_type=AUDIO, role=VOICEOVER_AUDIO)` carrying the
   script text + voice_spec + provenance (model, tokens, cost)
   in `source_spec`. Operators can browse VO audio in the
   Asset Library, re-use the same VO clip across multiple
   compositions (a single CTA voice line reused across N ads),
   and lineage works the same as any other Asset. Mirrors
   A-arc rule 1 + V1 rule 5.

2. **VO synthesis is workspace-scoped.** The voice_spec resolves
   against workspace-visible voice ids only. Cross-workspace
   voice_id refs reject at primitive-execute time. If the
   voice_spec references a spokesperson, that spokesperson
   must belong to the composition's workspace. Mirrors V1
   rule 1 + R-arc rule 1.

3. **VO synthesis does not fire the avatar video pipeline.**
   `synthesize_voiceover_audio` calls TTS only; no
   `/v1/avatar_videos`, no Runway poll, no portrait
   conditioning. The cost gap (~$0.01 vs ~$0.25) is the entire
   reason this primitive exists. If a recipe needs the avatar's
   face speaking the words, use `generate_avatar_speech`
   instead.

4. **Overlay preserves the base clip's video stream byte-for-
   byte.** `overlay_audio_at_offset` re-encodes audio only
   (`-c:v copy`). The result CLIP has the same length,
   resolution, codec, and frame count as the base. Diffing the
   video streams of base vs overlaid should yield zero changes
   — only the audio track differs. Mirrors V14's `audio_extract`
   no-re-encode discipline.

5. **Ducking is structural, not a config drift surface.** The
   overlay primitive ducks the base audio by a default
   `duck_db = -18` during the VO window (same shape as
   `mix_audio.music_gain_db`). Operator can override per-call
   via `duck_db` param (range: `-60` to `0`, where `0` = no
   duck, `-60` = effectively silent). Crossfade durations
   default to 300 ms in / 300 ms out and are not user-tunable
   in v1 — adding tuning surfaces invites operator confusion
   about *why* the audio sounds different across renders.
   Mirrors V7 `mix_audio` defaults rationale.

6. **Offset is operator-explicit and validates against base
   duration.** `offset_seconds` is a required positive float;
   `offset_seconds + vo_audio.duration > base_clip.duration`
   raises `PrimitiveError` with an actionable message ("VO
   would extend 2.4s past base clip end; either shorten the VO
   text or extend the base render"). No silent truncation —
   the operator paid for both clips and should not have one
   silently cut. Mirrors V5 `concat_clips` strict-mode
   discipline.

7. **VO audio inherits no transcript / caption ownership.**
   Captions on the resulting CLIP cover the base clip's voice
   audio only, NOT the overlaid VO. Adding caption coverage
   for VO requires running `transcribe` against the VO audio
   separately (a future v2 surface) and either burning a
   second caption track or merging the two transcripts. v1
   skips both — `add_captions` after `overlay_audio_at_offset`
   produces base-only captions; VO text lives on
   `Asset(VOICEOVER_AUDIO).source_spec.script`.

8. **Voice identity is per-call, not persisted on the recipe.**
   Each recipe invocation supplies its own `voice_spec` (one
   of: `{spokesperson_id}` / `{voice_id}` / `{voice_design}`).
   No "default VO voice" persisted on the workspace or
   spokesperson. Rationale: the V-arc + B-arc dogfood pattern
   is to ship recipe configs as data on the Composition row,
   not as ambient defaults. Cross-spokesperson identity reuse
   (e.g. *"every Marcus ad uses Sasha's voice for the CTA"*)
   is a v2 axis that needs a `VoiceoverPreset` model and
   doesn't fit the no-persistence shape.

9. **TTS provider abstraction lives in media-engine.** The VO
   arc adds one provider interface — `TextToSpeechProvider` —
   with a v1 implementation against Runway's
   `eleven_multilingual_ttv_v2`-backed TTS path (or
   ElevenLabs direct if Runway TTS remains gated, per
   `audio_client.py:19`). The shell never imports the provider
   directly; it calls a new `/internal/audio/tts/` endpoint
   and persists the returned AUDIO asset. Mirrors R2's
   `RealtimeProvider` Protocol pattern + R10's drift verifier.

---

## Data model additions

### `AssetRole` extension

One enum addition to `apps.compositions.models.AssetRole`:

```python
class AssetRole(models.TextChoices):
    # ...existing roles...
    VOICEOVER_AUDIO = "voiceover_audio", "Voiceover audio"
```

That's the only schema change. No new tables, no new
migrations beyond the `TextChoices` metadata bump.

### `Asset.source_spec` shape for VO audio

| Key | Type | Notes |
|---|---|---|
| `script` | str | the operator-supplied or starter-supplied VO text |
| `voice_spec` | dict | the resolved spec — one of `{spokesperson_id}`, `{voice_id}`, `{voice_design}`. Persisted resolved (the voice_id used at synthesis time) so re-renders are deterministic. |
| `provider` | str | `"runway_tts"` / `"elevenlabs_direct"` / `"mock"` |
| `model` | str | e.g. `"eleven_multilingual_ttv_v2"` |
| `tokens_input` | int | character count of the input script |
| `duration_seconds` | float | the actual duration of the synthesized clip |
| `cost_micros` | int | per-call cost provenance |

### `Composition.template_kind` extensions

Two new starter recipes register: `cta_swap`, `narrated_intro`.
Both count against `videos_per_month` per the SESSION 204
ruleset — these fire the underlying `talking_head` plus a TTS
call. The TTS portion does not add a separate tier dimension
in v1 (rule 8 deferral).

### No `Composition`, `Asset`, or `Spokesperson` schema change

Beyond the one `AssetRole` enum entry.

---

## New primitives

### `synthesize_voiceover_audio`

| Field | Notes |
|---|---|
| Inputs | none (text-driven) |
| Params | `script` (str, required) · `voice_spec` (dict, required) · `provider` (str, optional; default routed by env) |
| Output | one `Asset(asset_type=AUDIO, role=VOICEOVER_AUDIO)` |
| Cost | ~$0.01 per call (10 000 micros placeholder; refine post-VO.1 dogfood) |
| Mock-mode | `_ffmpeg_silent_mp3` 3 s placeholder via the existing helper from `audio_client.py:172` |

`voice_spec` resolution (in order):
1. `{spokesperson_id: <uuid>}` — looks up the spokesperson in
   the composition's workspace + uses
   `Spokesperson.voice_id`. Cross-workspace rejects (rule 2).
2. `{voice_id: <runway/eleven id>}` — uses the id directly.
   Workspace ownership of the voice id is verified against
   the existing `BrandVoiceResult` cache when present;
   "unknown voice id" voices are accepted with a warning
   logged (matches V10 dub_audio's lenient stance for
   migration paths).
3. `{voice_design: <text prompt>}` — fires
   `design_voice` as a sub-call. Caches the resulting
   voice_id on the resulting AUDIO asset's `source_spec` so
   subsequent calls can reference it directly. Costs the
   `design_voice` price + the TTS call.

The primitive is mock-mode aware (env: `VOICEOVER_TTS_FORCE_MOCK`
mirroring the existing `_FORCE_MOCK` precedent across the
6 R-arc flags + the rest of the V-arc).

### `overlay_audio_at_offset`

| Field | Notes |
|---|---|
| Inputs | slot `base` (CLIP, required) · slot `voiceover` (AUDIO, required) |
| Params | `offset_seconds` (float, required, ≥ 0) · `duck_db` (float, default -18, range [-60, 0]) |
| Output | one `Asset(asset_type=CLIP)` with the original base's role propagated (talking_head stays talking_head) |
| Cost | ~$0 marginal (ffmpeg-only); 100 micros placeholder for cost-tracking consistency |
| Mock-mode | copy-base-to-output (mirrors `dub_output_ad` mock path from `audio_client.py:550`) |

ffmpeg shape (real-mode):
```
ffmpeg -i {base.mp4} -i {voiceover.mp3} \
  -filter_complex "
    [0:a]volume=enable='between(t,{offset},{offset+vo_duration})':volume='{duck_db}dB'[base_ducked];
    [1:a]adelay={offset_ms}|{offset_ms},afade=t=in:st=0:d=0.3,afade=t=out:st={vo_duration-0.3}:d=0.3[vo_delayed];
    [base_ducked][vo_delayed]amix=inputs=2:duration=first[out]
  " \
  -map 0:v -map "[out]" \
  -c:v copy -c:a aac -b:a 192k -movflags +faststart \
  {output.mp4}
```

Duration is preserved via `-map 0:v` (no video transform) +
`amix=duration=first` (output audio matches base length even
if VO extends past — caught by rule 6 first).

---

## New / extended media-engine endpoints

| Method | Path | Status | Purpose |
|---|---|---|---|
| `POST` | `/internal/audio/tts/` | NEW | Body `{text, voice_spec, provider?}`. Returns `{status, audio_url, duration_seconds, voice_id, cost_micros}`. Mock-mode returns silent MP3 + deterministic stub voice_id. |
| `POST` | `/internal/clips/overlay_audio/` | NEW | Body `{base_url, vo_url, offset_seconds, duck_db?}`. Returns `{status, output_url, duration_seconds}`. ffmpeg invocation; no Runway calls. |

Both endpoints follow the V14/V16 stateless internal-API pattern
(no state on the media-engine side; shell persists the resulting
Asset). The TTS endpoint is the only one that touches an
external provider; the overlay endpoint is pure ffmpeg.

---

## New recipes

### `cta_swap`

| Field | Notes |
|---|---|
| `kind` | `cta_swap` |
| `template_kind` on Composition | `cta_swap` |
| Inputs | `script` (str — main body for the spokesperson) · `cta_text` (str — VO line, default ~40 chars / 4s) · `cta_voice_spec` (dict — same shape as `synthesize_voiceover_audio.voice_spec`) · `cta_offset_seconds` (float, default = `talking_head_duration - cta_duration - 0.5`) · `use_knowledge` (bool, default False) |
| Steps | step 0: `generate_avatar_speech` (script) · step 1: `synthesize_voiceover_audio` (cta_text + cta_voice_spec) · step 2: `overlay_audio_at_offset` (base=step0, voiceover=step1, offset=cta_offset_seconds) |
| Cost | base `talking_head` (~$0.25) + TTS (~$0.01) + overlay ($0) = ~$0.26 |

`cta_offset_seconds` defaulting to `base_duration - cta_duration
- 0.5` puts the VO at the end of the clip with a 0.5s tail
buffer — the typical "and now back to you, Jessica" shape from
the start-here doc.

### `narrated_intro`

| Field | Notes |
|---|---|
| `kind` | `narrated_intro` |
| `template_kind` on Composition | `narrated_intro` |
| Inputs | `intro_text` (str, default ~30 chars / 3s) · `intro_voice_spec` (dict) · `script` (str — main body) · `use_knowledge` (bool, default False) |
| Steps | step 0: `synthesize_voiceover_audio` (intro_text + intro_voice_spec) · step 1: `generate_avatar_speech` (script) · step 2: `overlay_audio_at_offset` (base=step1, voiceover=step0, offset=0) |
| Cost | TTS (~$0.01) + base `talking_head` (~$0.25) + overlay ($0) = ~$0.26 |

`offset_seconds=0` puts the VO at the very start; the base
avatar voice ducks under for the intro window, then the
operator's actual spokesperson speaks.

---

## Slice breakdown (7 slices, VO.0-VO.6)

| # | Slice | Effort |
|---|---|---|
| **VO.0** ✓ SHIPPED | This scope-lock doc (SESSION 211, commit `d19b1da`) | ½ session |
| **VO.1** ✓ SHIPPED | `AssetRole.VOICEOVER_AUDIO` enum + migration `0010_vo_1_voiceover_audio_role` + `/internal/audio/tts/` endpoint + `TextToSpeechProvider` Protocol + `RunwayTtsProvider` (auto-falls-through on gated 4xx) + `ElevenLabsTtsProvider` + `MockTtsProvider` + `synthesize_voiceover_audio` shell primitive + `VOICEOVER_TTS_FORCE_MOCK` env flag + role mapping in `asset_roles.PRIMITIVE_TO_ROLE`. Tests: 23 shell + 25 media-engine = +48. Primitive count 21 → 22. Mirrors R2 provider pattern + V3 primitive shape + R10 drift verifier shape. | ½ session |
| **VO.2** | `/internal/clips/overlay_audio/` endpoint (ffmpeg-only) + `overlay_audio_at_offset` shell primitive + rule-6 validation + rule-4 no-video-re-encode test. Mirrors V14 `audio_extract` + V7 `mix_audio` shape. | ½ session |
| **VO.3** | `cta_swap` starter + recipe registry entry + form metadata (new `voice_picker` field type — accepts spokesperson/voice_id/free-form). Tests cover the 3 voice_spec resolution paths from rule 8. | ½ session |
| **VO.4** | `narrated_intro` starter + recipe registry entry. Reuses VO.3's `voice_picker`. Adds a `voiceover_duration_seconds` estimator helper (chars × ~11 cps from `_estimate_avatar_speech_seconds` precedent) so `cta_offset_seconds` default can pre-compute on the SPA side without firing TTS. | ½ session |
| **VO.5** | SPA recipe gallery wiring — `voice_picker` field renders as a 3-tab control (workspace spokesperson / voice id / design prompt). `cta_offset_seconds` shows a "computed" hint with the estimator output. Recipe gallery count goes 20 → 22. | 1 session |
| **VO.6** | Real-mode dogfood + arc close. Fire `cta_swap` against the keeper (24/7 Global AI) with Sasha's voice as the CTA voice; validate audio swap is audible, base video stream is byte-identical pre/post overlay, ducking is at expected -18 dB. Capture calibration. | ½ session |

**Total: ~3-4 sessions.** Smaller than B-2's 5 (no new app, no
new model, no REST surface — just two primitives + two recipes
+ a small SPA field type extension).

---

## In-scope clarifications

* **VO audio assets are workspace-attached** like every other
  Asset. Asset Library SPA lists them under
  `?asset_type=AUDIO&role=voiceover_audio`. The lineage panel
  shows which Compositions referenced each VO audio (one VO
  asset can feed multiple compositions per rule 1).

* **The voice_spec resolves at primitive-execute time, not at
  composition-create time.** If the operator picks a
  spokesperson voice + that spokesperson's `voice_id` is later
  changed (re-bake), subsequent renders use the new voice id;
  prior renders retain their persisted voice_id in
  `source_spec.voice_spec` for audit.

* **The overlay primitive is single-VO-per-call.** A future
  v2 axis could accept N VO clips at N offsets in one call;
  v1 keeps it strict so the implementation + ffmpeg filter
  stays auditable. Chaining `overlay_audio_at_offset` calls
  composes naturally — recipe authors can stack them.

* **Cost estimation is per-primitive.** The shell-side
  `apps/compositions/cost.py` registry gets a
  `synthesize_voiceover_audio` row (10k micros placeholder
  + per-char dial after VO.6 dogfood) and an
  `overlay_audio_at_offset` row (100 micros). The
  `cta_swap` and `narrated_intro` starters sum naturally
  via the existing per-step estimation flow.

* **Mock mode is exhaustive.** Both new endpoints honor
  `VOICEOVER_TTS_FORCE_MOCK=1` and the existing
  `RUNWAY_FORCE_MOCK`. The mock TTS path produces a silent
  MP3 with operator-supplied character-count duration
  (`duration_seconds = chars / 11` per the existing
  `_estimate_avatar_speech_seconds` heuristic).

---

## Out of scope (v1)

* **Mid-clip voiceover** at multiple offsets in one composition.
  Recipe authors can chain `overlay_audio_at_offset` calls but
  no first-class recipe accepts a list of (text, offset) pairs.
  v2 axis with a `multi_vo_layout` recipe.
* **SFX / Foley layering** (whooshes, stings). B-12 in the
  backlog. Same `overlay_audio_at_offset` primitive could
  serve, but the recipe + asset role + UX is a separate axis.
* **Operator's own voice clone** (B-13 in the backlog). The
  `voice_spec.voice_design` path supports designed voices;
  cloning the operator's own recorded voice needs explicit
  consent capture + ElevenLabs IVC integration.
* **Multi-language VO.** V10's `dub_audio` covers post-render
  language swap of the entire clip. VO arc stays single-
  language per call. A future `multi_lang_voiceover` could
  compose `synthesize_voiceover_audio` + `dub_audio`.
* **Live mix preview** before firing the composition. Operators
  cannot scrub the timeline + hear how the VO sits before
  committing the render. v2 axis — needs a media-engine
  preview endpoint that returns a streaming audio
  segment.
* **Cross-spokesperson VO presets** (rule 8 deferral). A
  workspace-level *"always use Sasha's voice for the keeper's
  CTAs"* config needs a `VoiceoverPreset` model.
* **Caption coverage of VO audio** (rule 7). Captions for the
  overlaid VO line need either a second caption track or
  merged transcripts. Skipped in v1.
* **VO trimming / fades beyond defaults.** Crossfade ms (300/
  300) is fixed in v1. Operator-tunable fade is a future
  surface.
* **R7 realtime tool** (avatar invoking `synthesize_voiceover_audio`
  mid-conversation). Composes naturally with R7's tool
  registry but doesn't fit the R7 cost-threshold UX (TTS is
  inline-cheap; no approval gate needed). Deferred until a
  use case surfaces.

---

## Open questions (resolve at lock)

* **Q-vo-1**: One primitive or two (TTS + overlay)?
  **Proposed**: TWO. Composability — operators may want to
  overlay a VO audio they generated themselves (B-13 future
  voice clone), extracted from another render (`audio_extract`),
  or uploaded directly (future asset-upload axis). Splitting
  generate from overlay lets each be independently invokable.
  Resolve at VO.0.

* **Q-vo-2**: TTS provider — Runway's gated TTS path, or
  ElevenLabs direct? **Proposed**: try Runway first; if the
  `/v1/text_to_speech` endpoint is still gated per
  `audio_client.py:19`, fall through to ElevenLabs direct
  using the same voice ids (Runway voices are
  ElevenLabs-backed). VO.1 ships the provider abstraction
  with both implementations; env flag picks the active one.
  This is the most load-bearing open question — operator
  should confirm.
  Resolve at VO.0.

* **Q-vo-3**: Ducking semantics — apply to a window or
  full-clip during VO? **Proposed**: window only. Duck only
  while the VO plays, restore base gain after. Mirrors how
  professional audio editors handle voice-over-music; the
  alternative (duck the whole clip) is broken for
  `narrated_intro` because the spokesperson's voice would
  stay quiet for the rest of the clip. Resolve at VO.0.

* **Q-vo-4**: Voice spec discriminator — single `voice_spec`
  dict with one-of keys, or separate optional params
  (`spokesperson_id`, `voice_id`, `voice_design`)? **Proposed**:
  single `voice_spec` dict with exactly-one-of validation.
  Tighter shape, fewer ways to misuse. Same pattern as
  R4's `compose_realtime_document` which uses an explicit
  shape. Resolve at VO.0.

* **Q-vo-5**: Should the `cta_swap` recipe default
  `cta_offset_seconds` to end-of-clip, or require operator
  to pick? **Proposed**: default to
  `talking_head_duration - cta_duration - 0.5` (end of clip
  + 0.5s tail). The "and now back to you, Jessica" use case
  is the dominant one; making the operator compute the offset
  is friction. Resolve at VO.0.

* **Q-vo-6**: Tier gating — count VO renders against
  `videos_per_month`? **Proposed**: YES (the underlying
  `talking_head` already counts). No separate
  `voiceovers_per_month` dimension — TTS-only is cheap and
  the VO arc never produces a TTS asset standalone for
  operator-facing flows; the recipes always pair it with a
  `talking_head`. Asset Library shows the VO audio as a
  by-product. If a future v2 ships standalone-TTS as an
  operator-facing recipe, add the dimension then. Resolve at
  VO.0.

* **Q-vo-7**: Should `Asset(VOICEOVER_AUDIO)` rows be
  workspace-browsable in the existing Asset Library, or
  hidden as "internal" by-products? **Proposed**: BROWSABLE.
  Operators may want to reuse a designed VO line across
  multiple ads (rule 1). The Asset Library role-filter UI
  picks them up without code change. Resolve at VO.0.

* **Q-vo-8**: Real-mode validation target for VO.6 — the
  keeper (24/7 Global AI) talking_head as base + Sasha's
  voice for the CTA, or two operator-named voices in mock
  mode then real-mode after? **Proposed**: keeper + Sasha
  in real mode. The keeper is the sole active spokesperson;
  Sasha's voice is operator-validated from SESSION 158.
  ~$0.26 spend per dogfood fire — within the SESSION 158/
  173-174/209 dogfood envelope. Resolve at VO.6.

* **Q-vo-9**: Should `narrated_intro` be a separate recipe
  from `cta_swap`, or one parameterized `voiceover_overlay`
  recipe with a `position: "intro" | "outro"` param?
  **Proposed**: TWO. Recipe gallery cards stay legible
  ("CTA Swap" vs "Narrated Intro" are clearer than "Voiceover
  Overlay (intro/outro)"). Operator-facing labels are
  load-bearing per V15 calibration. Internally the starters
  compose the same primitives, so duplication is shallow.
  Resolve at VO.0.

---

## References

* `docs/design/VIDEO_COMPOSITION_V1.md` — V-arc scope lock
  + primitive registry pattern + recipe shape.
* `docs/design/AUTO_SCRIPTING_V1.md` — most recent
  arc-shaped scope lock; this doc follows its structure.
* `docs/design/REALTIME_AVATAR_V1.md` — R2 provider
  abstraction + R10 drift verifier; the
  `TextToSpeechProvider` Protocol mirrors `RealtimeProvider`.
* `docs/design/CONTENT_FORMAT_BACKLOG.md` — does not list
  VO as a backlog item; the operator surfaced this directly
  in the SESSION 210 closeout. Worth appending a §B-21 entry
  after VO.0 locks.
* `media-engine/app/services/audio_client.py` — existing
  `design_voice` + `dub_audio` + `dub_output_ad` patterns;
  the new TTS endpoint shares helpers (`_audio_dir`,
  `_download`, `_ffmpeg_silent_mp3`, `_runway_headers`).
* `shell/apps/compositions/primitives/avatar_speech.py` —
  shape `synthesize_voiceover_audio` follows (sans the
  Runway-task polling, since TTS is synchronous).

---

## Change log

* **2026-05-21 (SESSION 211, slice VO.0)** — Initial scope
  proposal. Sixth strategic-axis arc (the first post-quartet
  axis). Targets the "different speaker reads the CTA" use
  case surfaced repeatedly in real-mode dogfood. Nine
  contract rules; seven slices VO.0-VO.6. Nine open
  questions all proposed with default resolutions; awaiting
  operator sign-off to lock.

* **2026-05-21 (SESSION 211, VO.0 LOCKED)** — Operator signed
  off as-proposed. All 9 contract rules accepted without
  revision. All 9 open questions accepted with proposed
  resolutions:
  * Q-vo-1: two primitives (TTS + overlay) — locked.
  * Q-vo-2: Runway TTS first, ElevenLabs direct fallback
    behind a `TextToSpeechProvider` Protocol — locked.
    Provider-active env flag picks at runtime.
  * Q-vo-3: window-only ducking with crossfade — locked.
  * Q-vo-4: single `voice_spec` dict with exactly-one-of
    discriminator — locked.
  * Q-vo-5: `cta_swap` default offset =
    `base_duration - cta_duration - 0.5` — locked.
  * Q-vo-6: count under `videos_per_month`; no separate
    `voiceovers_per_month` dimension in v1 — locked.
  * Q-vo-7: `Asset(VOICEOVER_AUDIO)` rows browsable in
    Asset Library (role-filter UX absorbs them) — locked.
  * Q-vo-8: VO.6 real-mode dogfood = keeper talking_head
    + Sasha's voice for the CTA — locked.
  * Q-vo-9: `cta_swap` and `narrated_intro` ship as two
    separate recipes — locked.

  Status flips proposed → locked. VO.1 (`AssetRole`
  enum + `/internal/audio/tts/` endpoint +
  `TextToSpeechProvider` Protocol + `RunwayTtsProvider`
  + `ElevenLabsTtsProvider` fallback + `MockTtsProvider`
  + `synthesize_voiceover_audio` shell primitive +
  `VOICEOVER_TTS_FORCE_MOCK` flag) opens next session.

* **2026-05-21 (SESSION 211, VO.1 SHIPPED)** —
  Foundation slice lands. Everything VO.2/VO.3 need is
  now on the table:

  * **`AssetRole.VOICEOVER_AUDIO` enum + migration
    `compositions/0010_vo_1_voiceover_audio_role`** — 11th
    role value; `Asset.role` field choices + help_text
    updated; backfill mapping in
    `asset_roles.PRIMITIVE_TO_ROLE` so the existing
    coverage test honors rule 1.
  * **Media-engine `tts_provider` package**
    (`media-engine/app/services/tts_provider/`) — Protocol +
    `TtsSpec` / `TtsResult` dataclasses + `TtsProviderError`
    / `TtsUnavailableError`. Three concrete providers:
    `RunwayTtsProvider` (tries `/v1/text_to_speech`; raises
    `TtsUnavailableError` on 404 / gated 4xx markers like
    "voice.type" / "not enabled" so the dispatcher falls
    through to ElevenLabs), `ElevenLabsTtsProvider`
    (hits `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
    with `ELEVENLABS_API_KEY`; caches MP3 to
    `data/_internal/voiceovers/<hash>.mp3`; idempotent),
    `MockTtsProvider` (silent MP3 via the existing
    `_ffmpeg_silent_mp3` helper; deterministic cache key).
  * **Config**: `elevenlabs_api_key`,
    `elevenlabs_api_base`, `voiceover_tts_force_mock`,
    `voiceover_tts_default_provider` added to
    `media-engine/app/config.Settings`.
  * **`POST /internal/audio/tts/`** route ships the auto
    chain (Q-vo-2): mock-first if force-mock or
    no-providers; explicit `runway` / `elevenlabs` / `mock`
    bypasses chain; default `auto` tries Runway then
    ElevenLabs. Media-engine route count 137 → 138.
  * **`MediaEngineClient.tts(...)`** + `TtsResult` shell-
    side wrapper.
  * **`synthesize_voiceover_audio` shell primitive**
    (`apps/compositions/primitives/voiceover.py`) +
    registry entry — primitive count 21 → 22. Handles
    all three voice_spec discriminators (rule 8); enforces
    rule 2 (workspace-scoped) at the spokesperson-id
    lookup; enforces rule 3 (no avatar pipeline) by
    construction (only calls `/internal/audio/tts/`, never
    `/internal/clips/avatar_speech/`); persists rule 1
    provenance (script, voice_id, model, provider,
    discriminator-specific metadata) in
    `Asset.source_spec`.
  * **Tests**: 23 shell + 25 media-engine. Drift
    verifier mirrors R10's pattern — Protocol-method
    coverage + no-NotImplementedError-stub guard + new-
    provider-detection sentinel via package directory
    scan. **Django 1364 → 1387 (+23); media-engine
    221 → 246 (+25).**
  * **Inventory regenerated** against the working tree.

  VO.2 (`/internal/clips/overlay_audio/` route +
  `overlay_audio_at_offset` ffmpeg-only primitive) opens
  next session.
