---
title: "Session 180 — V-arc real-mode dogfood: talking_head_polished + V9 polish fixes"
date: 2026-05-18
status: complete
session: 180
previous_handoff: ./SESSION_179_V_ARC_REAL_MODE_DOGFOOD_V16.md
---

# Session 180 — V-arc real-mode dogfood: talking_head_polished

## TL;DR

Three commits, single-recipe dogfood. SESSION 179 closed
flagging 14 V-arc recipes still real-mode unvalidated and
the polish family as the lowest-friction next-pick.
SESSION 180 took `talking_head_polished` end-to-end and
surfaced **six** production bugs along the way — extending
the "real-mode dogfood finds bugs in every recipe it
touches" pattern from four-for-four (SESSION 179) to
ten-for-five.

By session-end:
* `talking_head_polished` produces real-mode finished
  composites at `/data/_internal/intro_outros/*.mp4`
  with a black title intro card, burnt-in subtitles
  over the avatar speech, and a black title outro card
* All four polish primitives
  (`generate_avatar_speech` + `add_captions` +
  `add_intro_outro` + the V9 helpers behind them) now
  hold up real-mode end-to-end on apostrophe-bearing
  text + non-default-aspect-ratio body clips
* Three new TRUST_CALIBRATION entries captured (silent-
  blank-render footgun, uvicorn-reload stale window,
  drawtext text= vs textfile= choice)

Tests: Django **428** (420 → 428, +8 — V9 polish form
shorthand kwargs). Media-engine **156** (143 → 156, +13 —
intro_outro endpoint tests). SPA vitest **95** unchanged.

Real-mode spend this session: **~$0.25** (one polished
composition, then five re-fires of the intro_outro step
only via `retry_step` — backdrop + speech assets reused
from cache).

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended (full text
in `docs/TRUST_CALIBRATION.md`):

1. **"200 OK + plausible byte count" doesn't mean correct
   output.** SESSION 180's intro_outro fixes shipped
   through four iterations of "endpoint returns 200, mp4
   is the right size, ship it" — and every single one
   produced pure-black rendered intro frames. Only the
   visible-pixel regression test (extract a frame, count
   bright pixels) caught the truth. Status code +
   reasonable byte count is necessary but vastly
   insufficient for any rendering pipeline. Pattern: for
   any endpoint that produces visual output, the
   regression test MUST probe the actual rendered output
   — not just the request/response surface.

2. **Uvicorn `--reload` has a stale-during-restart
   window.** Mid-session, I made rapid edits to
   `internal.py` and re-fired compositions immediately
   after. Several re-fires landed during the `WatchFiles
   detected changes... Reloading...` window — the in-
   flight POST got served by the OLD module before the
   reloader swapped processes. The signal was a
   regenerated mp4 with byte-identical content (same
   md5) to the broken version — same code path produced
   the same output. Once I killed + restarted uvicorn
   without --reload, the next regeneration produced
   different bytes + visible text. Pattern: when iterating
   on a media-engine endpoint with --reload, wait for
   the "Application startup complete" log line between
   edits, or kill + restart cleanly to eliminate the
   ambiguity.

3. **drawtext `text=` is a footgun once `fontfile=`
   joins the filter.** Four successive text-escape
   attempts (POSIX close-escape-reopen / octal `\047`
   / backslash / plain) — each looked correct in
   isolation and worked on a standalone test — all
   silently rendered blank cards as soon as the same
   filter carried `fontfile=`. The combination of two
   quoted arguments confuses ffmpeg's in-filter
   tokenizer in ways that don't surface as errors.
   `textfile='/path/to/file.txt'` sidesteps the whole
   problem: drawtext reads literal bytes from disk,
   no in-filter escape rules apply. Pattern: any
   drawtext invocation that's been touched once
   should use textfile= for the text argument, not
   text=. The endpoint maintains the temp text files
   alongside the cached output, keyed off the same
   cache hash so they're idempotent.

## What shipped — commit by commit

### `65fb165` — V9 polish form shorthands

Found while inspecting the recipe form: the V15-era
`talking_head_polished` recipe only exposed spokesperson
+ script + use_knowledge + opener, with a comment
deferring captions / intro / outro as "JSON-shaped; v1
leaves them null." Net effect: firing the recipe from the
SPA produced a 1-step composition functionally identical
to plain `talking_head` — no captions, no title cards.

Slice closed the gap with three operator-friendly
shorthand kwargs on the starter:

* `intro_text: str | None = None` — plain string,
  builds default-styled title card when supplied
* `outro_text: str | None = None` — same shape, appended
* `burn_captions: bool = False` — auto-times captions
  from the script by splitting on sentence boundaries
  and distributing time at ~11 chars/sec (same rate V8
  uses for the backdrop chain math)

Explicit dict-form kwargs (`captions=`, `intro=`,
`outro=`) still win over the shorthands — no surprise
override for programmatic callers. Matching `RecipeField`
entries on the form so the SPA gallery renders the new
inputs.

Eight new V9 polish tests covering each shorthand
individually, both-on case, explicit-wins precedence,
full 3-step polish chain via shorthands, auto-caption
chunking (3-sentence script → 3 non-overlapping
segments), and whitespace-only intro_text → skip-step
edge case.

### `41fbbe4` — intro_outro endpoint triple fix

First real-mode dogfood with the form shorthands
("Riggs's Rules." intro + "Don't blink." outro over
Riggs's avatar speech) blew up step 2 with a 500.
Standalone repro surfaced three latent-since-V9 bugs:

* **drawtext apostrophe escape** — the prior `\\'`
  escape closed the single-quoted ffmpeg filter
  argument prematurely. Replaced with POSIX-style
  close-escape-reopen pattern `'\''`. (Later supplanted
  by the textfile= refactor in `bcc9178` once we
  discovered that pattern doesn't survive when
  fontfile= joins the filter.)
* **input indexing math** — `len(ffmpeg_inputs) // 2`
  counted argument pairs, not actual `-i` occurrences
  (`-f lavfi -i X` is 4 args but a single input).
  Replaced with an explicit `input_count` counter. The
  result: no `add_intro_outro` call with both intro AND
  outro had ever succeeded in real mode since V9 shipped
  (SESSION 143).
* **hardcoded canvas dims** — `canvas_w, canvas_h =
  1280, 720` broke concat against Runway gwm1_avatars'
  1088x704 output. New `_probe_dimensions()` helper
  reads the body clip's actual dims.

Eight new media-engine intro_outro tests cover all three
fixes against real ffmpeg/ffprobe on lavfi-generated
tiny fixtures.

### `bcc9178` — drawtext textfile + fontfile resolver

Operator played the post-41fbbe4 output and reported
pure-black intro / outro frames. Investigation showed
two more stacked bugs:

* **missing fontfile=** — Homebrew ffmpeg ships with
  libfreetype + libfontconfig + libharfbuzz but
  fontconfig's default-font lookup silently renders
  nothing when no fontfile= is supplied. New
  `_resolve_drawtext_font()` helper probes a candidate
  list (operator env override → macOS Helvetica → Linux
  DejaVu paths) and raises `RuntimeError` when nothing
  matches — fail loud instead of silently rendering
  blank.
* **drawtext text= can't carry apostrophes when
  fontfile= is in the same filter.** Four iterations of
  text-escape variants all rendered blank as soon as
  fontfile= joined the filter. Pivoted to drawtext's
  `textfile=` option — reads literal bytes from disk,
  no in-filter escape rules apply. Endpoint writes
  intro/outro card text to
  `<cache_key>-{intro,outro}.txt` alongside the cached
  output mp4, keyed off the same cache hash so the
  files are idempotent across reruns.

Test coverage: 13 new media-engine intro_outro tests
total. The visible-pixel regression test fires the
endpoint with the EXACT operator payload that produced
the bug ("Riggs's Rules." + "Don't blink." on a
1088x704 body clip) and asserts the rendered intro
frame contains > 500 bright pixels — the only test
shape that would have caught the blank-frame failure
mode the earlier status-code-checking tests missed.

## State at session-end

**Registry counts (unchanged since SESSION 179):**

```
starters.py:    18 starter functions
recipes.py:     18 RECIPES entries
primitives:     14 (mock × 3 + real × 11)
media-engine:   124 routes
```

**Tests:**

```
Django:        428 compositions tests pass (420 → 428, +8)
Media-engine:  156 (143 → 156, +13)
SPA vitest:     95 (unchanged)
```

**V-arc real-mode validation status:**

* ✓ `talking_head` — SESSION 158
* ✓ `long_form_ad` — SESSION 179
* ✓ `cinematic_visual` — SESSION 179
* ✓ `talking_head_with_backdrop` — SESSION 179 (single-
  backdrop + multi-backdrop chain + V16 matting)
* ✓ `talking_head_polished` — SESSION 180 (full 3-step
  chain: speech + auto-captions + intro/outro cards)
* **13 recipes remain unvalidated.** SESSION 181 priority.

**Running processes at session-close (operator's box):**

```
Django runserver:   pid 14769 (auto-reloads on .py changes)
Media-engine:       pid 21694 (uvicorn --reload, restarted
                    SESSION 180 after the textfile= edit)
Celery worker:      pid 18279 (still running with the
                    SESSION 179 V16 primitive registry —
                    SESSION 180 added no new primitives,
                    no restart needed)
```

**Operator-visible UI state**: `talking_head_polished`
recipe form now exposes three new fields below "Use
workspace knowledge":
* Intro card text (optional)
* Outro card text (optional)
* Burn captions from script (checkbox)

**Workspace artifacts from SESSION 180**:

* 1 `Composition` (`c241a39a-...`, `talking_head_polished`,
  completed) — Riggs delivering "Three rules. Don't blink.
  Don't fold. Don't apologize." with "Riggs's Rules."
  intro + "Don't blink." outro cards
* Final asset:
  `/data/_internal/intro_outros/019cf3803c177062.mp4`
  (~503KB, 11s)
* Two card text files at `019cf3803c177062-intro.txt` and
  `019cf3803c177062-outro.txt`

## Next session priorities — SESSION 181

Continuing the V-arc real-mode dogfood. 13 recipes
remain unvalidated. The polish family is now done; next
candidates in increasing complexity:

1. **`reels_format`** — 2-step (avatar speech →
   reformat_clip to 720:1280 vertical). ~$0.35 + ~2 min.
   First real-mode validation of `reformat_clip`.
2. **`pip_layout`** — picture-in-picture composite of
   two existing CLIPs. Needs two pre-existing CLIP
   Assets in workspace. No Runway spend (pure ffmpeg).
3. **`cohost_layout`** — same shape as pip_layout,
   different ffmpeg overlay layout kind.
4. **`broll_splice`** — base avatar + cinematic cutaway
   spliced into a time window. 3-step.
5. **`music_bed_pass`** — base clip + audio mix-down.
   First real-mode validation of `mix_audio`.
6. **`voice_design`** — one-shot custom voice generation.
   No composition steps; pure media-engine call. ~$0
   (Runway voice design is free-tier).
7. **`multi_lang_dub`** — voice-clone across 29
   languages. Heaviest real-mode call.
8. **`style_remix_pass`** — Aleph gen4_aleph style
   transfer on an existing CLIP. ~$1.50.
9. **`storyboard_ad`** — 7-step Hook/Action/Payoff
   composition. Heavy spend (~$2.00).
10. **`recut_teaser`** — first real-mode `transcribe`.
11. **`storyboard_voiced`** — V15.4 bonus 10-step recipe.
    Heaviest spend.
12. **`dialogue_scene`** — multi-spokesperson scripted
    scene. Needs ≥2 cast members.
13. **`backdrop_layout`** — standalone starter, distinct
    from V8's full `talking_head_with_backdrop` flow.

Expected class of bugs (priors from SESSION 179 + 180
ten-for-five hit rate):
* Form gaps where the recipe form doesn't expose the
  starter's full capability surface (SESSION 180 V9
  shorthands pattern)
* Silent visual-output failures that pass status-code
  checks but produce wrong frames
* ffmpeg filter / muxer edge cases triggered by
  operator-realistic inputs (non-default sizes,
  apostrophes, special characters)
* Hardcoded defaults that match one common shape and
  silently break for others
