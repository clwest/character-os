---
title: "Session 111 — pyrightconfig + context-kit anchor maintenance"
date: 2026-05-13
status: complete
session: 111
previous_handoff: ./SESSION_110_VOICE_CLONE_ENDPOINT.md
---

# Session 111 — Quiet the noise + populate the narrative anchor

## TL;DR

- **What shipped:** Three small but load-bearing slices.
  `shell/pyrightconfig.json` quiets five sessions of accumulated
  cross-stack noise. The narrative anchor
  `docs/CHARACTER_OS_WHAT_IT_IS.md` is now populated with real
  state instead of a stub. The first entry in
  `docs/TRUST_CALIBRATION.md` records the SESSION 109 Celery
  decision so future sessions inherit that calibration signal.
- **What's blocking next:** Nothing technically. SESSION 112
  decision point is: build the inventory generator (closes the
  last anchor gap) or start Phase 3 (SPA scaffolding). Both are
  scope-locked.
- **What's in a weird state:** Two real drift issues that this
  session surfaced but did **not** fix:
  1. `docs/design/UI_REDESIGN_V2.md` is referenced by `CLAUDE.md`,
     the start-here, and multiple handoffs as the canonical design
     lock — but it doesn't exist at that path. Confirmed via `ls
     docs/design/`. The file is referenced as "Phase 0 done,
     design lock" but nothing matches. **Operator should clarify:
     where does that doc live, or does it need recreating?**
  2. `CHARACTER_OS_INVENTORY.md` is still the scaffolded stub. The
     narrative anchor now documents this explicitly; SESSION 112's
     recommended slice is to land the generator.

---

## What changed (file-by-file)

### `shell/pyrightconfig.json` (new)

Three settings turned down (`reportIncompatibleMethodOverride`,
`reportUnreachable`, and the kept-as-warning `reportMissingImports`)
because all three were generating false-positive noise on every
recent session:

1. `apps.* could not be resolved` — Django adds the project root to
   `sys.path` at boot; pyright analyses files in isolation.
2. `Method get_queryset overrides ... base method returns type
   Never` — DRF stub drift, upstream noise.
3. Post-`sys.exit(1)` "unreachable code" — mathematically correct,
   operationally useless.

`extraPaths: ["."]` + `venv: ".venv"` + `venvPath: "."` so cross-
app imports resolve against the venv's installed packages. Runtime
gates (`manage.py check`) remain the authoritative correctness
check.

### `docs/CHARACTER_OS_WHAT_IT_IS.md` (rewritten)

The whole document. Was the context-kit scaffold stub since SESSION
106. Now populated with:

- TL;DR + scale numbers (~25 Django endpoints, 106 FastAPI routes,
  ~10K LOC).
- Three-layer architecture description (Django shell, FastAPI
  media-engine, SPA placeholder).
- Internal contract summary (the three verbs + their shapes).
- The "unique stuff" section with 6 actual differentiators
  grounded in shipped code.
- Current state honesty section flagging the two drift issues
  (missing UI_REDESIGN_V2.md, stub inventory).
- Real navigation table + glossary with real terms.

Header frontmatter updated to `status: populated` +
`last_revised: 2026-05-13 (SESSION 111)` + `covers_sessions:
"106-110"`. Inventory is still the regenerated authority on
quantities; this doc is the conceptual companion.

### `docs/TRUST_CALIBRATION.md`

First real entry: the SESSION 109 Celery decision. AI proposed
thread-helper middle path; operator pushed back; outcome was
landing Celery + Redis early, which proved to be the right call
for this operator's calibration profile ("right-shape foundations
early"). Format follows the template in the file's preamble.

---

## Verification gates

- `python manage.py check` — 0 issues. (Note: pyrightconfig only
  affects pyright; not the Django check chain.)
- `python manage.py migrate --check` — exit 0.
- FastAPI route count — 106 (unchanged from SESSION 110).
- Hygiene scan — clean.
- `context-kit orient` — still flags 4 cosmetic warnings:
  inventory freshness (known), pyproject version drift (0.0.0;
  cosmetic), SESSION_053 gap (cosmetic), start-vs-handoff
  verification (false-positive — start-here mentions 053 only
  in the "missing handoff" note itself).

---

## Architectural notes worth remembering

### Pyright is advisory, not authoritative

The new `pyrightconfig.json` makes this explicit. Runtime is the
truth — `manage.py check`, the smoke commands, and the test suite
when it exists. Pyright catches real type errors when they happen
(it'll still flag those at `warning` level) but stops drowning
the signal in cross-stack stub drift.

If a future session sees a pyright warning that **isn't** in the
three classes this config suppresses, it's worth investigating.
The config is a noise filter, not a "trust nothing" switch.

### Two-doc anchor pattern is now real

Before SESSION 111, only the **runtime** half of the two-doc
anchor was named correctly — `CHARACTER_OS_INVENTORY.md` exists
as a stub. The **narrative** half was scaffold text. After this
session both docs exist with intent, even though the runtime
half is still waiting on a generator. The pattern only pays off
when both sides exist; one-sided anchors drift fastest.

### Calibration log is a project asset, not a personal one

Future operators (or future versions of this AI assistant) won't
have read this conversation. The `TRUST_CALIBRATION.md` entry on
Celery captures *why* Phase 4-planned scope landed in Phase 2 —
not as a confession ("AI got it wrong") but as a calibration
signal for next session's planning. The lesson encoded ("when
foundation cost is <1 session and saves a retrofit, expand
scope") will only matter if it survives across operator turnover.

### What this session deliberately didn't do

- No Phase 3 SPA work. Multi-session scope; operator wants to
  lock scope explicitly first.
- No inventory generator. ~half-session slice; bumped to SESSION
  112's first-choice recommendation.
- No fix for the missing `UI_REDESIGN_V2.md`. Two options
  (recreate or relocate) both need operator decision first.

---

## SESSION 112 — entry point

See `00-START-NEXT-SESSION.md`. The recommended slice is the
inventory generator — closes the last anchor gap, sets up
Phase 3's mental model on solid runtime ground.

---

## AI notes

- The pyrightconfig slice took 5 minutes. The narrative anchor
  took 25. The calibration entry took 5. Real cost was the
  reading + grounding, not the writing.
- Finding the missing `UI_REDESIGN_V2.md` was a small wake-up
  moment. I (the AI) had been treating it as canonical for five
  sessions because CLAUDE.md said so. The fact that `ls
  docs/design/` returns "empty" until SESSION 108 added the
  internal-API doc suggests the design lock either never got
  copied during the context-kit scaffold, or it was never written
  down at this path in the first place. Worth a quick operator
  clarification next session.
- The narrative anchor structure (TL;DR → core idea → layers →
  unique stuff → state honesty → navigation → glossary) felt
  right for this product. Worth keeping for future
  `_WHAT_IT_IS.md` files on other context-kit projects.
- One open question I noticed but didn't act on: the legacy
  `docs/WHAT_IT_IS_LEGACY.md` (~500 lines, the runway-hackathon
  product narrative) and `docs/INVENTORY_LEGACY.md` (~1800 lines)
  are valuable historical context but are confusingly named —
  they're not stale, they're the *predecessor product*. Consider
  renaming to `RUNWAY_HACKATHON_WHAT_IT_WAS.md` or moving under
  `docs/runway-hackathon/`. Cosmetic; flag for future cleanup.
