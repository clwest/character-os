---
title: "Session 159 — drift-prevention items 2 + 3 closed in context-kit"
date: 2026-05-15
status: complete
session: 159
previous_handoff: ./SESSION_158_FIRST_MARKETING_VIDEO.md
---

# Session 159 — drift-prevention items 2 + 3 closed

## TL;DR

**SESSION 147 drift audit backlog is closed.** The two deferred
items (re-stamp anchor doc frontmatter at handoff-write time;
audit calibration-entry promotion to `TRUST_CALIBRATION.md`)
shipped this session, in the sibling `context-kit` repo.

The new subcommand:

```bash
context-kit handoff write <N> [--project PATH] [--dry-run] [--date YYYY-MM-DD]
```

**No character-os code changes this session.** Four anchor
docs got their `last_revised:` frontmatter backfilled via the
new subcommand — that's the only character-os deliverable.

## What shipped (context-kit `9590737`)

Commit title: *"Add `context-kit handoff write` for
session-end anchor re-stamp + calibration audit"*.

Repo: `/Users/donkeyking/development/context-kit`, branch
`main`. The commit lands six files / +1374 −76 lines:

* `cli/handoff.py` — new module (~430 lines).
* `tests/test_handoff.py` — 34 new tests.
* `context_kit.py` — new `handoff` group + `write` action.
* `CLAUDE.md` — discipline note pairing `handoff write` with
  session-end handoff commits.
* `docs/handoffs/SESSION_017_HANDOFF_WRITE_SUBCOMMAND.md` —
  context-kit's own handoff.
* `00-START-NEXT-SESSION.md` — context-kit's next-session
  preview.

Two side-effects under a single CLI verb:

* **Re-stamp anchor docs** (drift-prevention item 2).
  Discovers `docs/*_WHAT_IT_IS.md`, `*_PIPELINE.md`,
  `*_BEHAVIOR_LAYER.md`, `*_TRANSLATION_LAYER.md`, and
  `*_SESSION_START.md`. Inserts / updates `last_revised:
  YYYY-MM-DD (SESSION NNN)` for each. Bumps `covers_sessions:`
  upper bound when the field is present. `*_INVENTORY.md`
  excluded — owned by `inventory --write`.

* **Calibration drift detection** (drift-prevention item 3).
  Parses the handoff for `## Calibration moments worth
  carrying` or `## AI Notes`, fuzzy-matches subsection
  headlines against same-date `TRUST_CALIBRATION.md` entries.
  Reports `✓ promoted` / `⚠ MISSING`. **Read-only on
  TRUST_CALIBRATION.** Operator does the actual entry write —
  the prose-to-canonical-format translation is operator
  judgment, not deterministic.

Test totals: context-kit 1042 → **1076** (+34). character-os
unchanged at 659 Django + 108 media-engine + 37 SPA.

## Live target — character-os SESSION 158

Smoke test against this repo as the live target. Dry-run
output:

```
Anchor doc frontmatter:
  unchanged          docs/CHARACTER_OS_WHAT_IT_IS.md (already at 2026-05-15 (SESSION 158))
  would restamp   docs/CHARACTER_OS_PIPELINE.md (last_revised: (missing) → 2026-05-15 (SESSION 158))
  would restamp   docs/CHARACTER_OS_BEHAVIOR_LAYER.md (last_revised: (missing) → 2026-05-15 (SESSION 158))
  would restamp   docs/CHARACTER_OS_TRANSLATION_LAYER.md (last_revised: (missing) → 2026-05-15 (SESSION 158))
  would restamp   docs/CHARACTER_OS_SESSION_START.md (last_revised: (missing) → 2026-05-15 (SESSION 158))

Calibration promotion check (read-only):
  ✓ promoted   1. AI overstated "shipped" before operator viewed the output
  ✓ promoted   2. Avatar voice × lip-sync quality is a real operational axis
  ✓ promoted   3. R9's hardcoded $0.08/min placeholder was accurate enough
```

This validates the original SESSION 147 drift hypothesis:
across this repo's 50+ sessions, only `CHARACTER_OS_WHAT_IT_IS.md`
had ever been re-stamped. Four secondary anchors had been
silently sitting with `generated: 2026-05-13` and no
`last_revised:` field. The live write inserted the field on
all four — committed as the doc-only commit paired with this
handoff.

All 3 of SESSION 158's calibration moments correctly matched
their same-date TRUST_CALIBRATION entries via fuzzy headline
overlap — even though the TRUST_CALIBRATION versions are
rewritten with event-type prefixes (e.g. `AI confidently
wrong (deliverable framing): ...`). No false positives, no
false negatives on this smoke test.

## Drift-prevention backlog — CLOSED

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | Superseded by `doctor` (SESSION 151) |
| 2 | `handoff write` re-stamps anchor frontmatter | **Done** |
| 3 | Promote calibration entries to TRUST_CALIBRATION | **Done** (detect-and-report) |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done (SESSION 151) |
| 5 | Fix INVENTORY's known generator bugs | Celery undercount done SESSION 151; working-tree-dirty flag pending |

Only item 5's working-tree-dirty flag survives, and it's a
cosmetic improvement, not a forgetting surface.

## New session-end workflow

From SESSION 160 onward:

```bash
# After writing docs/handoffs/SESSION_NNN_<slug>.md
# and overwriting 00-START-NEXT-SESSION.md, run:
python3 /Users/donkeyking/development/context-kit/context_kit.py \
    handoff write <NNN> --project .
```

Pair the output with the handoff commit. The re-stamp closes
the per-slice anchor-doc forgetting surface; the calibration
audit catches handoff prose that didn't make it to
`docs/TRUST_CALIBRATION.md`.

`--dry-run` previews; `--date YYYY-MM-DD` overrides the date
from the handoff's `date:` frontmatter (rarely needed).

## Design call — detect-and-report (not auto-append)

The most defensible call this session was making rec 3
*read-only* on `TRUST_CALIBRATION.md`. The alternative —
auto-appending skeleton entries — would have generated
operator work (each stub needs the 5-field canonical shape
applied) without removing the underlying judgment about
event-type classification. Detect-and-report surfaces the
drift; the operator does the write. Same outcome, less
ceremony.

See context-kit's `docs/handoffs/SESSION_017_*.md` AI Notes
section for the longer reasoning. The fuzzy match (≥ 0.4
token overlap with stopword + digit strip) is the most
heuristic part of the module; failure mode is the safe one
(false negative reads as `⚠ MISSING`, prompts manual verify;
no silently-wrong matches).

## Calibration moments worth carrying

### 1. Cross-repo workflow worked

The work happened in `context-kit/` but the live target was
`character-os/`. Two commits in two repos. Done deliberately
so the new functionality lives in the tool, not the project
that consumes it. Generalisation: when a drift-prevention
mechanism originates in a project but is general-purpose,
the right home is the pattern repo, not the project repo.
The project repo records the *trigger* event (this handoff +
the anchor backfill commit); the pattern repo owns the
*solution*.

**Carry-forward**: when an item shows up on a project's
backlog but the right implementation site is the tool /
sibling repo, ship there. The backlog entry closes when the
tool ships, even if the project itself sees no code changes.

### 2. Operator-mediated dogfooding caught the silent staleness

The SESSION 158 dry-run output ("four anchors with no
`last_revised:` at all, across 50+ sessions") was the
strongest validator the design choice was right. Reading it
felt different than reading the SESSION 147 audit summary —
the audit *named* the drift class; the smoke test *showed
the count*. The operator's reflexive question would have
been "is this thing real?"; the smoke output answered it
before the question got asked.

**Carry-forward**: when shipping pattern-level infrastructure,
land it in dry-run mode against the original problem repo
first. The smoke output is the truest test of "does this
catch the thing we said it would catch?" If the dry-run is
boring (all `unchanged`), the abstraction is leaky or the
drift wasn't there. If it's loud (multiple `would restamp`),
the abstraction is doing real work.

## Files changed in this commit (character-os)

* `docs/CHARACTER_OS_PIPELINE.md` — `last_revised:
  2026-05-15 (SESSION 158)` inserted via the new subcommand.
* `docs/CHARACTER_OS_BEHAVIOR_LAYER.md` — same.
* `docs/CHARACTER_OS_TRANSLATION_LAYER.md` — same.
* `docs/CHARACTER_OS_SESSION_START.md` — same.
* `00-START-NEXT-SESSION.md` — overwritten for SESSION 160.
* `docs/handoffs/SESSION_159_DRIFT_PREVENTION_CLOSE.md` —
  this file.

No `feat:` commit on the character-os codebase this session.
The character-os deliverable is documentation; the code
deliverable lives in `context-kit/9590737`.

## What's next (SESSION 160)

Drift-prevention thread fully closed. The remaining backlog
is small + non-realtime. Pick by operator preference:

* **More real-Runway exposure** — re-bake Donny, polished
  Sasha retake (V9 captions + intro/outro), or
  `long_form_ad` end-to-end smoke ($0.50-$2.00).
* **F8.1 — K10 seed corpus** if operator markdown is ready.
* **K7.x — YouTube ingest fix.**
* **K6.3 — Brief length cap (~15 min).**
* **K7.1 — Cost telemetry surface.**
* **W11.1 — Edit-spokesperson modal.**

See `00-START-NEXT-SESSION.md` for the full backlog.

---

*Handoff written end-of-SESSION 159. The new
`context-kit handoff write` subcommand was used to re-stamp
the four anchor docs paired with this commit — that's the
first production use of the very functionality this session
shipped.*
