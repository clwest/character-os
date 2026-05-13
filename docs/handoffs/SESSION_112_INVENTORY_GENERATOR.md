---
title: "Session 112 — Inventory generator closes the runtime-anchor gap"
date: 2026-05-13
status: complete
session: 112
previous_handoff: ./SESSION_111_PYRIGHT_CONFIG_AND_CONTEXT_KIT_MAINTENANCE.md
---

# Session 112 — `python manage.py inventory`

## TL;DR

- **What shipped:** A Django management command that regenerates
  `docs/CHARACTER_OS_INVENTORY.md` from runtime introspection.
  Closes the seven-session-old gap where the runtime anchor was
  still the `context-kit init` scaffold stub. Walks Django models,
  URL resolver, Celery task registry, migration loader, FastAPI
  via live `/openapi.json` probe (with graceful fallback), and
  source-tree LOC. ~440 LOC; emits ~5 KB Markdown.
- **What's blocking next:** Nothing. The two-doc anchor is now
  complete (narrative + runtime), and the contract surface has
  been feature-complete since SESSION 110.
- **What's in a weird state:** The `docs/design/UI_REDESIGN_V2.md`
  drift surfaced in SESSION 111 still isn't resolved — the file is
  referenced everywhere but doesn't exist at that path. Carried
  forward as the top queued investigation; needs operator input.

---

## What changed (file-by-file)

### `shell/apps/accounts/management/commands/inventory.py` (new)

Lives in `accounts/` because that app holds the multi-tenant root
(Workspace + Membership). The command is project-level — it walks
every installed app — but Django requires management commands to
live inside an `INSTALLED_APP`, and `accounts/` is the closest
thing to a "system root."

Sections collected + rendered:

1. **Metadata** — git sha + branch + dirty flag, generated_at
   timestamp, Python / Django / Celery / httpx versions.
2. **Executive summary** — eight bullets, each citing its source
   of truth.
3. **Django models (project-owned)** — `apps.get_models()`
   filtered to exclude contrib (admin / auth / contenttypes /
   sessions / sites / allauth's `account` + `socialaccount` +
   `usersessions` / dj-stripe). Per-model fields + FK count.
4. **URL routes** — `get_resolver().url_patterns` walk with
   nested-resolver recursion. Buckets by prefix (`api/` /
   `accounts/` / `admin/` / `other`), surfaces named API + auth
   routes.
5. **FastAPI routes** — live `httpx.get(/openapi.json)` probe of
   the media-engine. Graceful fallback to "unreachable" marker
   so the inventory regenerates cleanly without FastAPI running.
   Surfaces the `/internal/*` Phase 2 contract verbs explicitly.
6. **Celery tasks** — `celery_app.tasks` filter excluding
   `celery.*` built-ins.
7. **Migrations** — `MigrationLoader` ∩ `MigrationRecorder`,
   per-app applied/total/pending with a `⚠` marker on pending.
8. **Infrastructure** — Django, FastAPI, Redis, Celery broker +
   result backend, default DB engine. Pulls from `settings`.
9. **Code statistics** — `*.py` file count + line count per
   service, walking the source tree (excludes `.venv/`,
   `__pycache__/`, `migrations/`).

CLI surface:
```bash
python manage.py inventory             # write the file
python manage.py inventory --dry-run   # preview to stdout
python manage.py inventory --json      # machine-readable
python manage.py inventory --media-engine-url=http://...
```

Idempotency: re-running with no code changes produces a byte-
identical file modulo the `generated_at` timestamp + git sha.

### `docs/CHARACTER_OS_INVENTORY.md` (regenerated)

Replaces the seven-session-old scaffold stub. Real numbers:

- **6** project-owned Django models across **5** apps
- **150** total URL routes (35 `/api/*`, 26 `/accounts/*`,
  89 `/admin/*`)
- **93** FastAPI routes (88 legacy `/api/*` + 4 `/internal/*` +
  1 health)
- **2** Celery tasks (`poll_video_until_terminal` +
  `debug_task`)
- **40 / 40** migrations applied
- **~30K LOC** total (~25K media-engine + ~4K shell)

### `docs/CHARACTER_OS_WHAT_IT_IS.md`

Updated to defer to the inventory for hard numbers rather than
hardcoding them. The narrative anchor now says "see inventory" in
the scale section and the architectural tables, with examples
inline. Closed the "inventory is still a stub" drift entry in
the state-honesty section. Updated frontmatter:
`last_revised: 2026-05-13 (SESSION 112)`,
`covers_sessions: "106-112"`.

The inventory carrying authoritative counts means the narrative
can stay shorter without lying.

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — exit 0.
- `python manage.py inventory --dry-run` — outputs ~185 lines of
  Markdown, no errors.
- `python manage.py inventory` (with media-engine running) — writes
  4,925 bytes, FastAPI section populated with 93 routes including
  the `/internal/*` enumeration.
- `python manage.py inventory` (with media-engine stopped) —
  writes successfully with a "⚠ unreachable" marker in the FastAPI
  section. Operator gets a useful hint instead of a crash.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### A real surprise: 106 was wrong

The narrative anchor written in SESSION 111 said the media-engine
had "106 routes." That came from
`python -c "from app.main import app; print(len(app.routes))"`,
which counts **all** routes — including framework-added entries
(`/docs`, `/redoc`, `/openapi.json`, plus the dual trailing-slash
entries FastAPI auto-generates). The inventory's `/openapi.json`
probe counts **user-defined paths only** — 93.

Both numbers are technically correct for what they measure. But
the narrative was implicitly claiming the 106 was the customer-
facing surface, which it wasn't. The inventory now carries the
right number and the narrative defers to it. The drift only
existed because the runtime anchor was a stub; the moment it
landed, the drift surfaced.

This is the entire point of the two-doc pattern. The narrative is
what humans want to hear; the inventory is what's actually there.
When they disagree, the inventory wins, and the narrative gets
updated.

### `/openapi.json` is free introspection

We didn't need to add a `/internal/_meta/routes` endpoint on the
media-engine — FastAPI exposes the full schema at `/openapi.json`
by default. The inventory just probes that. No media-engine code
changes were needed for SESSION 112's slice; the command lives
entirely on the Django side.

### Idempotency matters more than pretty output

The first cut had the executive-summary numbers reformatted on
each run because of how I was ordering the `by_app` dict. Switched
everything to `sorted(...)` so re-runs produce byte-identical
output (modulo timestamp + git sha). Future drift verifier
(`verify_doc_claims --only-drift`) will diff this output across
commits; reordering would create false positives.

### Pyright warning that stayed

One pyright warning persists despite the pyrightconfig:
`Import "character_os.celery" could not be resolved`. It comes
from a lazy import inside `_collect_celery_tasks`. The pyrightconfig
is being respected (other warnings are silenced), this one is just
in the residual `reportMissingImports: "warning"` set. It's at
warning level (not error) and runtime works fine. Acceptable.

---

## SESSION 113 — entry point

See `00-START-NEXT-SESSION.md`. Two natural directions:

1. **Resolve the UI_REDESIGN_V2.md drift** — operator decision
   needed. Bumped from "queued" to "first thing to triage."
2. **Phase 3 SPA kickoff** — multi-session, needs scope lock,
   likely blocked on (1) since the SPA design lock is the missing
   doc.

Or, smaller alternatives still queued: the stuck-row janitor,
additional video kinds, legacy doc renaming.

---

## AI notes

- The first pass had two real bugs (URL prefix bucketing + the
  allauth `account` label slipping through). Both surfaced via
  eyeballing the dry-run output. Confirms the smoke-by-eyeball
  approach is enough here — no separate test needed.
- The "media-engine 106 routes" → "actually 93" correction is the
  most concrete demonstration so far of why the two-doc anchor
  pattern earns its keep. SESSION 111 documented 106 as fact;
  SESSION 112's runtime probe disagreed. Without the inventory,
  the 106 would have propagated into Phase 3.
- Future drift verifier note: the inventory's structure is
  deliberately stable (section order, table column order). When
  the drift verifier lands, diffing this file across commits
  should produce useful signal: "models went from 6 to 7" is
  interesting; "the table reordered itself" is not.
- The pyrightconfig from SESSION 111 is partially helping —
  `reportIncompatibleMethodOverride` and `reportUnreachable` are
  silent, `reportMissingImports` is now at "warning." The
  residual `character_os.celery` warning is a fair trade for
  catching real missing-import bugs.
