---
title: "Session 194 — V18 polish double (SESSION 184 calibrations #2 + #4)"
date: 2026-05-19
status: complete
session: 194
previous_handoff: ./SESSION_193_DOGFOOD_PASS_CELERY_HARD_RULE.md
---

# Session 194 — V18 polish double

## TL;DR

**Quick-wins session as recommended at SESSION 193 close.** Two
SESSION 184 dogfood calibrations that have been queued for 10
sessions ship in one pass:

* **Slice 1 — V18 duration-mismatch starter warning** (#2 from
  SESSION 184). `talking_head_with_backdrop` refuses at creation
  time when the picked `backdrop_clip` is shorter than the
  estimated speech duration. Operator-actionable error names
  both durations + script length + remediation options.
* **Slice 2 — smoke_keyframes `--save-assets` default opt-in**
  (#4 from SESSION 184). Smoke outputs now persist as
  `Asset(role=EXPERIMENT)` rows by default so they land in the
  Asset Library v1 UI instead of becoming orphan URLs. Operators
  who want throwaway smokes pass `--no-save-assets`.

Backend tests **995 → 1006 (+11)** — 5 V18 polish + 6 smoke
helper. SPA **134** unchanged. `pnpm build` not re-run (no SPA
changes; build was clean at SESSION 192 close + slice 1 didn't
touch SPA). No real-mode spend.

## Slice 1 — V18 duration-mismatch starter warning

### Context

SESSION 184 V18 dogfood produced a render where Riggs's speech
got cut off mid-sentence — the operator picked a 5s
`gen3a_turbo` smoke as backdrop_clip for a script that was
~9s of speech, and `composite_video` trimmed the longer input
(speech) down to the shorter input (backdrop). Calibration #2
queued the fix for "V18 polish slice."

### What landed

`apps/compositions/starters.py::talking_head_with_backdrop`
gains a duration-mismatch check inside the existing
`backdrop_clip is not None` validation block, right after the
existing `duration_ms is None` guard. Uses
`_estimate_avatar_speech_seconds(len(script.strip()))` which
adds a 2s safety buffer — the check effectively requires
`backdrop ≥ estimated_speech + 2s`, protecting against Runway
returning a clip slightly longer than the tight estimate.

The error message names both durations, the script's character
count, and the two remediation options (longer backdrop OR
shorter script with a target character count derived from the
inverse of the chars/sec rate).

Example error:

```
backdrop_clip <uuid> is 5s long but the estimated speech
duration is 20s (script: 200 chars). The composite primitive
trims the longer input to the shorter one — with this
combination, the avatar speech would be cut off mid-sentence.
Either pick a backdrop_clip that's at least 20s long or
shorten the script to roughly 55 characters or fewer.
```

### Test changes

* 5 new tests in `test_v8_backdrop.py`:
  * Rejection when backdrop < estimate.
  * Acceptance at the boundary (strict `<` — backdrop exactly
    equal to estimate is fine; the 2s buffer is already baked
    into the estimator).
  * Acceptance with clearly-longer backdrop (happy path).
  * Check doesn't fire on backdrop_prompt path (the V18 check
    is picked-clip specific).
  * Error message includes the character-count remediation
    hint.
* 1 existing test updated:
  `test_v18_picked_clip_skips_use_extend_for_backdrop_flag`
  used a 200-char script + default 15s backdrop. The new
  check would reject (20s estimate vs 15s backdrop) but the
  test's actual assertion is about the extend-flag being
  ignored. Bumped the backdrop duration to 25s with a
  docstring note explaining the bump preserves test intent.

### SPA impact

None. V15 form already surfaces backend ValidationError via
the existing error-message path; the new starter error
flows through unchanged.

## Slice 2 — smoke_keyframes save-assets default

### Context

SESSION 184 calibration #4: *"Smoke commands without
--save-assets produce orphans. Future smokes should default
to backfilling CLIP rows."* The original smoke_keyframes
command (built for V17.3 design exploration) made real Runway
calls and printed URLs but didn't persist anything to the DB.
Operators wanted to see the outputs in the UI, so they
backfilled Asset rows manually via Django shell (the SESSION
184 `c21fdeec` + `89a1ce5f` UUIDs were exactly that — manual
backfills).

### What landed

`apps/compositions/management/commands/smoke_keyframes.py`:

* New `persist_smoke_asset(*, workspace, model, output_url,
  task_id, prompt, duration_seconds, width, height) -> Asset`
  helper. Pure DB write, no network — testable in isolation.
  Stamps `role=AssetRole.EXPERIMENT.value` (matches SESSION 185
  A1 backfill heuristic for smoke outputs; keeps them out of
  the A7 role-filtered backdrop picker per the SESSION 184
  dogfood #6 calibration "re-using smoke outputs as backdrops
  drags drift into production renders").
* `--save-assets` flag added (default **True**).
* `--no-save-assets` opt-out for explicit throwaway runs.
* `--workspace NAME` flag — required when `--save-assets`
  is on. Fails fast with `CommandError` before any Runway
  credit gets spent if the operator forgot.
* `handle()` resolves the workspace upfront (right after the
  `RUNWAY_FORCE_MOCK` guard, before any XOR validation). The
  success branch in the per-model loop now calls
  `persist_smoke_asset` after a SUCCEEDED Runway poll. Failures
  wrapped in `try/except` so a DB write error doesn't kill
  the smoke output the operator already paid for.

### Test changes

* 6 new tests in new file `test_smoke_keyframes.py`. Tests
  exercise the `persist_smoke_asset` helper directly because
  the command itself makes real Runway calls (and refuses
  `RUNWAY_FORCE_MOCK`), making the full-command path hard to
  mock without major refactoring.
* `test_isolation.py` ALLOWED_FILES gains two entries: the
  command (sanctioned writer — Asset persistence is the
  point of slice 2) and the test file (constructs Asset rows
  for the helper exercise).

### Breaking change for existing operators

The flip to save-by-default means operators running
`smoke_keyframes` without `--workspace` now get a
`CommandError`. The wording is operator-actionable:
*"--workspace NAME is required when --save-assets is on (the
default). Either pass --workspace, or pass --no-save-assets
to skip Asset persistence."* Documented in the handoff so
future invocations don't get confused.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1006** | +11 (995 → 1006) |
| - compositions | **575** | +11 (564 → 575) |
| Media-engine | 194 | unchanged |
| SPA vitest | 134 | unchanged |

Real-mode spend SESSION 194: **$0**.

## Calibration moments worth carrying

No new TRUST_CALIBRATION entries. Slice 1 + 2 both fix
existing calibrations (SESSION 184 #2 + #4); the fixes
themselves were straightforward applications of the existing
estimator + the SESSION 185 EXPERIMENT-role pattern.

One implicit reinforcement of the "quick-wins double" framing
from SESSION 193 close: bundling two related calibration
fixes in one session is a clean shape — they share context
(both from SESSION 184 V18 dogfood), both small enough to
ship + verify + commit in one pass, and the resulting
backlog drag at the next session opens is one item lighter
than it would be otherwise.

## Operational notes for SESSION 195

* **Live services from SESSION 193 dogfood pass remain up**
  (Django :8000, SPA :5174, Celery worker). All still
  responsive. Nothing to clean up unless the operator wants
  to reset the stack.
* **No arc in flight.** Same backlog as SESSION 193 minus
  the two shipped items:
  * Real-mode validation for `storyboard_voiced` +
    `dialogue_scene` (1 session, ~$1-2 spend).
  * F8.1 K10 seed corpus (blocked on operator markdown).
  * V17.3 keyframes (blocked on Runway adding keyframes to
    gen-4 family).
  * Asset upload UI (1-2 sessions; unblocks the 8 legacy
    needs-review rows).
  * K7.x v3 YouTube oEmbed (½ session).
  * K6.4 v3 architectural fix (1 session).
  * W12 legacy form retirement (1 session).
  * Thruman cleanup (½ session).
  * B6-B10 brand arc resumption (multi-session, deferred
    SESSION 178).
  * New-arc candidates from `CONTENT_FORMAT_BACKLOG.md`:
    B-1 transcript miner, B-3 personalized video, B-14
    multi-platform variants.
* **smoke_keyframes is now usable in the dogfood workflow.**
  When operator wants to run a V17.3-style A/B comparison,
  the outputs will land in the Asset Library automatically —
  no shell-backfill ritual required.
