---
title: "Session 177 — drift sweep + multi-step title disambiguation + K10 menu reframe"
date: 2026-05-18
status: complete
session: 177
previous_handoff: ./SESSION_176_R_ARC_REAL_MODE_HARDENING.md
---

# Session 177 — drift sweep + multi-step title disambiguation + K10 menu reframe

## TL;DR

Short session. Three commits + one data-only fix. Continued
straight from SESSION 176's wrap so the boot sweep cleaned up
SESSION 176's loose ends (commit-count typo across handoff /
start-here / R-arc change log, narrative anchor staleness,
untracked Claude Code lockfile) before opening any slice. Then
two task-board items (#2 voice swap re-investigation, #5
multi-step composition title disambiguation) plus an operator-
driven reframe of K10 in the FIRST THING menu.

* **`f5f49e4`** — SESSION 177 boot drift sweep. Fixed "9
  feature commits" → "8" in three docs, rubber-stamped the
  narrative anchor's `last_revised` to 2026-05-18, added
  `.claude/scheduled_tasks.lock` to `.gitignore`.
* **`bdc6b6c`** — multi-step composition asset titles get
  a per-step `— step N/M (<primitive>)` suffix. W11.6.5.3
  (SESSION 174) auto-titled every step output from the
  parent composition's name; single-step compositions are
  fine but multi-step (long_form_ad chunks, storyboard
  beats) all collapsed to the same title in the SPA
  asset_picker dropdown.
* **`e1caee8`** — fix K10 menu paraphrase + TRUST_CALIBRATION
  entry. Operator caught the SESSION 176 FIRST THING menu
  saying K10 needed "operator-authored markdown" — the
  actual scope lock (KNOWLEDGE_LAYER.md L1253) is
  platform-shipped markdown about Character OS itself
  (`docs/seeds/character_os/*.md`) auto-ingested into every
  new `is_operator=True` workspace.

Plus task #13 (voice swap re-persist): no code change.
SESSION 175 handoff overclaimed Sasha + Donny voice swaps
that never actually fired. Programmatically ran
`change_voice` via shell against both → Sasha=felix and
Donny=vincent now correctly persisted in DB AND Runway.
The `change_voice` endpoint works end-to-end; SESSION 175
just wrote "swapped" without verifying.

Tests: Django **814 → 816** (+2 multi-step title tests).
SPA + media-engine unchanged. No new migrations / models /
Celery tasks / routes.

## Calibration moments worth carrying

One new entry appended (the K10 menu paraphrase one above).
Pattern restatement: FIRST THING menu bullets that paraphrase
slice work can drift from the actual scope-lock wording —
operator reads the menu, not the scope lock, when picking
direction, so menu drift is load-bearing confusion.

Plus three operational notes (no separate entry):

* **SESSION 175 voice-swap handoff overclaimed without
  verification.** Variant of the existing "AI's 'shipped'
  framing belongs to the operator after review" calibration:
  if a handoff says "swapped" or "edited", that should
  reference a verifiable post-action state (DB query
  showing the new value, not just intent). SESSION 175's
  swap claim was caught by SESSION 176 + SESSION 177 roster
  cross-check.
* **The boot drift sweep is paying for itself.** SESSION 147
  codified it. SESSION 176 wrap-then-immediate-boot caught
  three drift items inside 5 minutes — the cost of the
  sweep is sub-1-min, the cost of an uncaught typo
  propagating across handoff + start-here + change log is
  much higher.
* **Multi-step title disambiguation surfaces composition
  shape in the UI.** Before: every step in a long_form_ad
  was "Long-form Ad — Marcus" in the dropdown. After: "—
  step 1/3 (generate_avatar_speech)", "— step 2/3
  (concat_clips)", "— step 3/3 (mix_audio)". The suffix
  doubles as a UX-visible composition diagram.

## What shipped — commit by commit

### `f5f49e4` — SESSION 177 boot drift sweep

`context-kit doctor` at session start surfaced 4 warnings
(0 blocking). Fixed three:

1. "Nine feature commits" → "Eight" in
   `docs/handoffs/SESSION_176_R_ARC_REAL_MODE_HARDENING.md`,
   `00-START-NEXT-SESSION.md`, and
   `docs/design/REALTIME_AVATAR_V1.md`. SESSION 176 had 8
   feature commits + 2 docs commits = 10 total; the
   handoff overcounted.
2. `docs/CHARACTER_OS_WHAT_IT_IS.md` dated 2026-05-17
   (SESSION 175); SESSION 176's work hardened existing
   R-arc surfaces without changing the WHAT-IT-IS product
   narrative, so rubber-stamped `last_revised` to
   2026-05-18 + `covers_sessions` to "106-176".
3. Added `.claude/scheduled_tasks.lock` to `.gitignore` —
   transient lockfile from Claude Code's scheduled-wakeup
   harness that was surfacing as unstaged.

The fourth warning (handoff numbering gap at SESSION_053 +
SESSION_172) is documented as intentional drift elsewhere;
no action.

### `bdc6b6c` — multi-step composition title disambiguation

Carried from SESSION 175's backlog. W11.6.5.3 (SESSION 174)
auto-titled every step output Asset from the parent
composition's name. For single-step compositions that's the
right shape ("Talking-head — Marcus"). For multi-step
compositions (long_form_ad chunks, storyboard_voiced beats,
etc.) every Asset got the same title verbatim — the SPA
asset_picker dropdown couldn't tell intermediate and final
outputs apart.

Added `_step_asset_title(composition, step)` in
`apps/compositions/tasks.py`. Single-step preserves
current behavior. Multi-step appends `— step N/M
(<primitive>)`. Base name truncates first when combined
length would exceed `Asset.title`'s 120-char ceiling.

Tests: 2 new in `test_runtime.py`:
* `test_multi_step_assets_disambiguate_titles` — 3-step
  composition produces three distinct asset titles.
* `test_multi_step_title_respects_120_char_cap` — base
  truncates when long_name + suffix > 120.

22 runtime tests pass total.

### `e1caee8` — K10 menu reframe + calibration

Operator pushback at session boot: "the whole point of the
way we set everything up is that the platform creates the
content, the user provides all of the data, creates the
spokesperson and gives the spokesperson a personality."

Cross-checked: SESSION 176's FIRST THING menu listed K10 as
"draft one piece of seed content … grounds K-arc dogfood in
operator-authored content." The actual scope lock
(KNOWLEDGE_LAYER.md L1253) is "Onboarding seed:
`seed_workspace_knowledge` task. `docs/seeds/character_os/
*.md` corpus. Trigger on `is_operator=True` workspace
creation." — platform-shipped markdown about Character OS
itself, auto-ingested into every new operator's workspace.

Fixed start-here entry to match scope lock wording +
appended TRUST_CALIBRATION entry documenting the drift
pattern.

### #13 voice swap re-persist (no commit)

SESSION 175 handoff claimed Sasha vincent→felix and Donny
drew→vincent swaps; SESSION 176 roster check found neither
persisted (DB + Runway both still original values). Code
path inspection: the `change_voice` viewset action does
both the upstream Runway PATCH AND the local
`spokesperson.save(update_fields=["voice_id", "updated_at"])`
unconditionally. So if it had fired, both would have stuck.

Fired `change_voice` programmatically via `APIRequestFactory`
+ `force_authenticate` against both Sasha and Donny.
Response `{voice_patch: {status: "applied", error: None}}`
for both. Post-action: Sasha DB voice=felix, Runway voice
preset=felix (label "Felix"). Donny DB voice=vincent,
Runway voice preset=vincent. Both `updatedAt` stamps fresh.

Finding: no code bug. SESSION 175's "swapped" claim was
overclaimed — the swap never actually fired from the UI
session. The endpoint works end-to-end when invoked.

## Cast roster (post-swap)

5 cast members in `admins-workspace`:

* Riggs — `06bf999f-...` voice `vincent`
* **Sasha — `79d48883-...` voice `felix`** (re-persisted SESSION 177)
* **Donny — `f30b2980-...` voice `vincent`** (re-persisted SESSION 177)
* Maya — `9410f23f-...` voice `victoria` (note: workspace also has a
  "Thruman" with voice `marcus` at the same UUID prefix — worth
  cleanup in a future session)
* Marcus — `b6a00dd8-...` voice `david`

## Final state — tests + counts

* Django: **816** (+2 from SESSION 176 close: 814)
* SPA vitest: **95** unchanged
* Media-engine: **133** unchanged
* Migrations: **62 / 62** applied (no new migrations)
* Celery tasks (registered): **9** unchanged
* Commits ahead of `origin/main`: 13 (10 from SESSION 176
  + 3 from SESSION 177)

## Operational notes carried forward

* **Push to remote** — operator approved push at SESSION 177
  close. Will run `git push origin main` as the final session
  action before the next session.
* **Branding / name change pending** — operator flagged this
  for immediate attention after the push. Hold further build
  work until the rename direction is clear.

## FIRST THING (SESSION 178): branding / name change

Hold any further build work until the operator's branding
decision is resolved. Likely scope:

1. **Naming change** — operator may rename Character OS to
   another brand (24/7 Global AI surfaced in the email
   signature card built SESSION 176 is one candidate).
   Scope of changes if rename happens: package names,
   repo name (operator decision), README + design lock
   doc titles, SPA UI strings, INVENTORY frontmatter,
   handoff doc titles. Mostly mechanical search + replace
   if the new name is a 1:1 swap; bigger surgery if the
   product framing changes.
2. **Domain / DNS** — if the rename includes a new domain,
   may affect CORS configs, public URLs, email signatures,
   any Runway / OpenAI rate-limit allowlists tied to
   referrer URLs.
3. **Operator-facing copy** — wizard greetings, dashboard
   headings, signature card, conversation defaults — all
   may need pass.

Other queued items if branding lands fast:

4. **F8.1 K10 seed corpus** — author 5-10 platform markdown
   files + wire `seed_workspace_knowledge` task. Half is
   content work, half is code.
5. **R6 memory phrasing polish** — needs real-mode session
   quota (4/5 used pre-push; check quota at session start).
6. **K6.4 v3 architectural fix** — generalize sentence-
   position-aware imperative-verb detection beyond stoplist.
7. **Thruman cleanup** — workspace has a "Thruman" spokesperson
   that may be stale test data; verify + remove.

## Stack-up boilerplate

```bash
cd infra && docker compose up -d
cd media-engine && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
cd shell && source .venv/bin/activate && python manage.py runserver
cd shell && source .venv/bin/activate && celery -A character_os worker --loglevel=info --pool=solo
cd web && pnpm dev
```

Doctor sweep:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

Smoke checks:

```bash
cd shell && python -m pytest -q       # 816 tests
cd media-engine && python -m pytest -q  # 133 tests
cd web && pnpm test                   # 95 vitest tests
cd web && pnpm build                  # full TS check + bundle
```
