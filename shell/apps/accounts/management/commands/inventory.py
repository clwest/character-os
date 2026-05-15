"""Regenerate ``docs/CHARACTER_OS_INVENTORY.md`` from runtime truth.

The runtime anchor of the two-doc context-kit pattern. Closes the
gap that's been flagged every session since SESSION 106
(``CHARACTER_OS_INVENTORY.md`` was a scaffolded stub waiting for
this generator).

What gets introspected:

    - Django models (count, names, FK density) via ``apps.get_models``
    - URL routes (count + paths) via Django's URL resolver
    - Celery registered tasks via ``celery_app.tasks``
    - Migrations (applied vs pending) via Django's migration loader
    - FastAPI routes (count + by-prefix breakdown) via a live HTTP
      call to the media-engine's ``/openapi.json``. Falls back to a
      "media-engine unreachable" warning so the inventory still
      regenerates without the FastAPI service running.
    - LOC stats per service, walking the source tree.
    - Git commit + branch + timestamp metadata.

Output: writes ``docs/CHARACTER_OS_INVENTORY.md`` in place.
``--dry-run`` prints to stdout without writing. ``--json`` emits
the raw inventory dict for downstream consumers.

Usage:
    python manage.py inventory
    python manage.py inventory --dry-run
    python manage.py inventory --json > inventory.json

This command must stay **idempotent** (re-running with no code
changes produces a byte-identical file modulo the timestamp +
git sha) and must **never invent numbers** — every value cites
the source of truth in the rendered table.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.urls import get_resolver

# Repo root = parent of the shell dir (the dir holding `manage.py`).
# BASE_DIR is the shell dir; its parent is the monorepo root that
# contains shell/, media-engine/, docs/, etc.
_REPO_ROOT = Path(settings.BASE_DIR).resolve().parent
_INVENTORY_PATH = _REPO_ROOT / "docs" / "CHARACTER_OS_INVENTORY.md"


class Command(BaseCommand):
    help = "Regenerate docs/CHARACTER_OS_INVENTORY.md from runtime truth."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print to stdout; don't write the file.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the inventory as JSON instead of Markdown.",
        )
        parser.add_argument(
            "--media-engine-url",
            default=None,
            help=(
                "Override the media-engine base URL probed for FastAPI "
                "routes. Defaults to settings.MEDIA_ENGINE_BASE_URL."
            ),
        )

    def handle(self, *_, **opts: Any) -> None:
        inv = self._collect(opts["media_engine_url"])

        if opts["json"]:
            self.stdout.write(json.dumps(inv, indent=2, default=str))
            return

        markdown = _render_markdown(inv)

        if opts["dry_run"]:
            self.stdout.write(markdown)
            return

        _INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _INVENTORY_PATH.write_text(markdown)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ wrote {_INVENTORY_PATH.relative_to(_REPO_ROOT)} "
                f"({len(markdown):,} bytes)"
            )
        )

    # ---- collection ------------------------------------------------

    def _collect(self, media_engine_url: str | None) -> dict:
        return {
            "metadata": _collect_metadata(),
            "models": _collect_models(),
            "endpoints": _collect_endpoints(),
            "tasks": _collect_celery_tasks(),
            "migrations": _collect_migrations(),
            "fastapi": _collect_fastapi(media_engine_url),
            "loc": _collect_loc(),
        }


# ---- collectors ----------------------------------------------------


def _collect_metadata() -> dict:
    """Git + timestamp + Python version. The minimum context for
    "when was this snapshot taken, against what commit?" that the
    rendered file needs in its frontmatter."""
    sha = _shell("git rev-parse --short HEAD") or "(no git)"
    branch = _shell("git rev-parse --abbrev-ref HEAD") or "(no git)"
    dirty_files = _shell("git diff --shortstat") or ""
    is_dirty = bool(dirty_files.strip())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "git_branch": branch,
        "git_dirty": is_dirty,
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "django_version": _module_version("django"),
        "celery_version": _module_version("celery"),
        "httpx_version": _module_version("httpx"),
    }


def _collect_models() -> dict:
    """Walk every Django model installed under apps.*. Records FK
    fan-out + per-app counts so the rendered table can show where
    state actually concentrates."""
    models = django_apps.get_models()
    by_app: dict[str, list[dict]] = defaultdict(list)
    # Apps we don't own — Django built-ins + auth plumbing. Their
    # tables exist but they're not part of "what character-os is."
    _CONTRIB_APPS = {
        "admin", "auth", "contenttypes", "sessions", "sites",
        # allauth registers under app_label="account" (singular) +
        # "socialaccount" + "usersessions". The package name starts
        # with "allauth" but the labels don't.
        "account", "socialaccount", "usersessions",
    }
    for model in models:
        label = model._meta.app_label
        if label in _CONTRIB_APPS:
            continue
        if label.startswith(("allauth", "djstripe", "stripe")):
            continue
        fk_count = sum(
            1 for f in model._meta.get_fields()
            if f.is_relation and f.many_to_one
        )
        by_app[label].append({
            "name": model.__name__,
            "table": model._meta.db_table,
            "fk_count": fk_count,
            "fields": len([f for f in model._meta.get_fields() if not f.is_relation or f.many_to_one]),
        })
    total = sum(len(v) for v in by_app.values())
    return {
        "total": total,
        "by_app": dict(by_app),
    }


def _collect_endpoints() -> dict:
    """Walk Django's URL resolver. Returns paths + names so the
    rendered table can show the actual API surface, not a hand-
    maintained count."""
    resolver = get_resolver()
    routes: list[dict] = []

    def _walk(url_patterns, prefix=""):
        for pattern in url_patterns:
            if hasattr(pattern, "url_patterns"):
                # Nested resolver — recurse.
                new_prefix = prefix + str(pattern.pattern)
                _walk(pattern.url_patterns, new_prefix)
            else:
                routes.append({
                    "path": prefix + str(pattern.pattern),
                    "name": getattr(pattern, "name", "") or "",
                })

    _walk(resolver.url_patterns)

    # Bucket by prefix. Django mixes regex (`^`) and path-converter
    # patterns, plus nested resolvers prepend the outer prefix —
    # strip leading `^` and look for substring matches so we catch
    # `api/...` and `^api/...` alike.
    def _normalise(path: str) -> str:
        # Strip outermost `^` markers introduced by re_path; nested
        # resolvers stack these so `^api/^spokespeople/` is real.
        return path.replace("^", "")

    buckets: Counter[str] = Counter()
    for r in routes:
        p = _normalise(r["path"])
        if p.startswith("api/"):
            buckets["api/"] += 1
        elif p.startswith("accounts/"):
            buckets["accounts/"] += 1
        elif p.startswith("admin/"):
            buckets["admin/"] += 1
        elif p.startswith("_allauth/"):
            buckets["_allauth/"] += 1
        else:
            buckets["other"] += 1

    return {
        "total": len(routes),
        "by_prefix": dict(buckets),
        # Surface just the named /api/* + /accounts/* + /_allauth/*
        # routes — admin is too noisy to render.
        "named_api": sorted({
            r["name"] for r in routes
            if r["name"]
            and _normalise(r["path"]).startswith(("api/", "accounts/", "_allauth/"))
        }),
    }


def _collect_celery_tasks() -> dict:
    """Pull registered tasks from the Celery app. Filters out
    Celery's built-in ``celery.*`` plumbing so only our tasks land
    in the inventory.

    SESSION 151 — fix for the SESSION 147-noted undercount. Celery's
    autodiscovery is lazy: at management-command start the
    ``celery_app.tasks`` registry only contains tasks imported via
    direct top-level imports (the celery module's own ``debug_task``
    + whatever else has already been imported). Tasks defined in
    ``apps/*/tasks.py`` don't appear until something forces the
    module import.

    ``celery_app.loader.import_default_modules()`` walks every
    installed Django app + imports its ``tasks`` module if it
    exists — same shape that ``celery worker`` startup does. After
    this call the registry contains every ``@shared_task``-decorated
    function in the codebase.
    """
    try:
        from character_os.celery import app as celery_app
    except Exception as exc:  # pragma: no cover — defensive
        return {"total": 0, "tasks": [], "error": f"celery import: {exc}"}

    # Force autodiscovery before reading the registry. Mirrors
    # what the worker does at boot; the management-command path
    # skips this step otherwise.
    try:
        celery_app.loader.import_default_modules()
    except Exception:  # pragma: no cover — defensive
        # If autodiscovery fails (a tasks.py with an import error
        # somewhere), we still return what we have rather than
        # crash the inventory regen.
        pass

    tasks = sorted(
        name for name in celery_app.tasks
        if not name.startswith("celery.")
    )
    return {"total": len(tasks), "tasks": tasks}


def _collect_migrations() -> dict:
    """Migration loader + recorder reconciliation. Counts applied
    vs total per app — the gap surfaces pending migrations the
    operator forgot to apply.

    Best-effort; if the migrations recorder table doesn't exist
    (fresh DB never migrated) we fall back to total-only counts.
    """
    loader = MigrationLoader(None, ignore_no_migrations=True)
    by_app: Counter[str] = Counter()
    for key in loader.disk_migrations:
        by_app[key[0]] += 1
    try:
        from django.db import connection
        recorder = MigrationRecorder(connection)
        applied: Counter[str] = Counter()
        for key in recorder.applied_migrations():
            applied[key[0]] += 1
    except Exception:
        applied = Counter()

    return {
        "total": sum(by_app.values()),
        "applied_total": sum(applied.values()),
        "by_app": {
            app: {
                "total": by_app[app],
                "applied": applied.get(app, 0),
                "pending": by_app[app] - applied.get(app, 0),
            }
            for app in sorted(by_app)
        },
    }


def _collect_fastapi(media_engine_url: str | None) -> dict:
    """Probe the live media-engine for its OpenAPI schema. Falls
    back to a "not reachable" marker so the inventory regenerates
    cleanly even without the FastAPI service running. The marker
    in the output makes it visually obvious that this section is
    stale."""
    base = (media_engine_url or settings.MEDIA_ENGINE_BASE_URL).rstrip("/")
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{base}/openapi.json")
        resp.raise_for_status()
        spec = resp.json()
    except httpx.HTTPError as exc:
        return {
            "reachable": False,
            "base_url": base,
            "error": str(exc)[:200],
            "total": None,
            "by_prefix": {},
        }
    except (ValueError, KeyError):
        return {
            "reachable": False,
            "base_url": base,
            "error": "openapi.json was not JSON-shaped",
            "total": None,
            "by_prefix": {},
        }

    paths = spec.get("paths") or {}
    by_prefix: Counter[str] = Counter()
    for raw_path in paths:
        if raw_path.startswith("/internal/"):
            by_prefix["/internal/"] += 1
        elif raw_path.startswith("/api/"):
            by_prefix["/api/"] += 1
        else:
            by_prefix["other"] += 1
    return {
        "reachable": True,
        "base_url": base,
        "openapi_title": spec.get("info", {}).get("title"),
        "openapi_version": spec.get("info", {}).get("version"),
        "total": len(paths),
        "by_prefix": dict(by_prefix),
        "internal_endpoints": sorted(
            p for p in paths if p.startswith("/internal/")
        ),
    }


def _collect_loc() -> dict:
    """LOC per service via a simple walk over *.py files. Excludes
    venv, migrations, __pycache__ — anything not hand-written.

    Single-pass; we don't shell out to ``wc -l`` because the
    venv handling is fiddly and Python can count newlines just
    fine.
    """
    services = {
        "shell": _REPO_ROOT / "shell",
        "media-engine": _REPO_ROOT / "media-engine",
    }
    result: dict = {}
    for label, path in services.items():
        if not path.exists():
            result[label] = {"files": 0, "lines": 0}
            continue
        files, lines = 0, 0
        for py in path.rglob("*.py"):
            if any(part in py.parts for part in (".venv", "__pycache__", "migrations")):
                continue
            try:
                lines += len(py.read_text(errors="replace").splitlines())
                files += 1
            except OSError:
                continue
        result[label] = {"files": files, "lines": lines}
    return result


# ---- rendering -----------------------------------------------------


def _render_markdown(inv: dict) -> str:
    """Render the inventory dict into the runtime-anchor Markdown.

    Keep the structure stable across runs — the docs-pattern
    drift-verifier (eventual) will diff this output across commits,
    and section reordering would produce noisy diffs.
    """
    meta = inv["metadata"]
    models = inv["models"]
    endpoints = inv["endpoints"]
    tasks = inv["tasks"]
    migrations = inv["migrations"]
    fastapi = inv["fastapi"]
    loc = inv["loc"]

    dirty_marker = " (working tree dirty)" if meta["git_dirty"] else ""

    sections: list[str] = []

    sections.append(f"""---
title: "Character OS Platform Inventory"
status: regenerated
generator: shell/apps/accounts/management/commands/inventory.py
command: python manage.py inventory
generated_at: {meta["generated_at"]}
git_sha: {meta["git_sha"]}{dirty_marker}
git_branch: {meta["git_branch"]}
---

# Character OS Platform Inventory

> **This document is regenerated.** Do not hand-edit — run
> ``python manage.py inventory`` (from ``shell/``) to refresh.
> Companion to [`CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) —
> that doc explains *what it is*; this one is *what exists right now*.

Generated **{meta["generated_at"]}** against commit **{meta["git_sha"]}**
on branch **{meta["git_branch"]}**{dirty_marker}.

Python {meta["python_version"]} · Django {meta["django_version"]} ·
Celery {meta["celery_version"]} · httpx {meta["httpx_version"]}.
""")

    # ---- Executive Summary -------------------------------------
    fastapi_total = fastapi["total"] if fastapi["reachable"] else "—"
    sections.append(f"""---

## Executive Summary

| Metric | Value | Source |
|---|---|---|
| Django models (project-owned) | **{models["total"]}** | `apps.get_models()` filtered to first-party apps |
| URL routes (total) | **{endpoints["total"]}** | `get_resolver().url_patterns` walk |
| URL routes (`/api/*`) | **{endpoints["by_prefix"].get("api/", 0)}** | same |
| FastAPI routes | **{fastapi_total}** | media-engine `/openapi.json` ({"reachable" if fastapi["reachable"] else "**UNREACHABLE — see FastAPI section**"}) |
| Celery tasks (registered) | **{tasks["total"]}** | `celery_app.tasks` filter |
| Migrations (applied / total) | **{migrations["applied_total"]} / {migrations["total"]}** | `MigrationRecorder` ∩ `MigrationLoader` |
| Shell LOC (`*.py`, no venv/migrations) | **{loc["shell"]["lines"]:,}** in {loc["shell"]["files"]:,} files | `pathlib.Path.rglob("*.py")` |
| Media-engine LOC (`*.py`, no venv/migrations) | **{loc["media-engine"]["lines"]:,}** in {loc["media-engine"]["files"]:,} files | same |
""")

    # ---- Django Models -----------------------------------------
    section = ["---", "", "## Django Models (project-owned)", ""]
    section.append(f"Total: **{models['total']}** models across **{len(models['by_app'])}** apps.")
    section.append("")
    section.append("| App | Model | DB Table | Fields | FKs |")
    section.append("|---|---|---|---|---|")
    for app in sorted(models["by_app"]):
        for m in sorted(models["by_app"][app], key=lambda x: x["name"]):
            section.append(
                f"| `{app}` | `{m['name']}` | `{m['table']}` | {m['fields']} | {m['fk_count']} |"
            )
    section.append("")
    sections.append("\n".join(section))

    # ---- URL routes --------------------------------------------
    section = ["---", "", "## URL Routes", ""]
    section.append(f"Total: **{endpoints['total']}** resolved patterns.")
    section.append("")
    section.append("| Prefix | Count |")
    section.append("|---|---|")
    for prefix in sorted(endpoints["by_prefix"]):
        section.append(f"| `{prefix}` | {endpoints['by_prefix'][prefix]} |")
    section.append("")
    section.append("### Named API + auth routes")
    section.append("")
    if endpoints["named_api"]:
        for name in endpoints["named_api"]:
            section.append(f"- `{name}`")
    else:
        section.append("_(none)_")
    section.append("")
    sections.append("\n".join(section))

    # ---- FastAPI routes ----------------------------------------
    section = ["---", "", "## FastAPI Media-Engine Routes", ""]
    if not fastapi["reachable"]:
        section.append(
            f"> **⚠ media-engine unreachable at `{fastapi['base_url']}`.** "
            f"Error: `{fastapi.get('error', 'unknown')}`. "
            f"Start it with `cd media-engine && uvicorn app.main:app --port 8001` "
            f"and re-run `python manage.py inventory` to refresh."
        )
    else:
        section.append(
            f"Probed `{fastapi['base_url']}/openapi.json` — "
            f"`{fastapi.get('openapi_title')}` v{fastapi.get('openapi_version')}."
        )
        section.append("")
        section.append(f"Total: **{fastapi['total']}** routes.")
        section.append("")
        section.append("| Prefix | Count |")
        section.append("|---|---|")
        for prefix in sorted(fastapi["by_prefix"]):
            section.append(f"| `{prefix}` | {fastapi['by_prefix'][prefix]} |")
        section.append("")
        if fastapi.get("internal_endpoints"):
            section.append("### `/internal/*` surface (Phase 2 contract)")
            section.append("")
            for path in fastapi["internal_endpoints"]:
                section.append(f"- `{path}`")
            section.append("")
    sections.append("\n".join(section))

    # ---- Celery tasks ------------------------------------------
    section = ["---", "", "## Celery Tasks", ""]
    section.append(f"Total: **{tasks['total']}** registered tasks (excluding `celery.*` built-ins).")
    section.append("")
    if tasks["tasks"]:
        for name in tasks["tasks"]:
            section.append(f"- `{name}`")
    elif "error" in tasks:
        section.append(f"_(error: {tasks['error']})_")
    else:
        section.append("_(no tasks registered)_")
    section.append("")
    sections.append("\n".join(section))

    # ---- Migrations --------------------------------------------
    section = ["---", "", "## Migrations", ""]
    section.append(
        f"**{migrations['applied_total']} of {migrations['total']}** migrations applied."
    )
    section.append("")
    section.append("| App | Applied | Total | Pending |")
    section.append("|---|---|---|---|")
    for app in sorted(migrations["by_app"]):
        row = migrations["by_app"][app]
        pending_marker = (
            f"**{row['pending']} ⚠**" if row["pending"] else "0"
        )
        section.append(
            f"| `{app}` | {row['applied']} | {row['total']} | {pending_marker} |"
        )
    section.append("")
    sections.append("\n".join(section))

    # ---- Infrastructure ----------------------------------------
    section = ["---", "", "## Infrastructure", ""]
    section.append("| Component | State | Source |")
    section.append("|---|---|---|")
    section.append("| Django runserver | `:8000` (when running) | `python manage.py runserver` |")
    section.append(f"| FastAPI media-engine | `{fastapi['base_url']}` ({'reachable' if fastapi['reachable'] else 'unreachable'}) | live probe |")
    section.append("| Redis | `redis://localhost:6381` (Docker) | `infra/docker-compose.yml` |")
    section.append(f"| Celery broker | `{settings.CELERY_BROKER_URL}` | `settings.CELERY_BROKER_URL` |")
    section.append(f"| Celery result backend | `{settings.CELERY_RESULT_BACKEND}` | `settings.CELERY_RESULT_BACKEND` |")
    db_engine = settings.DATABASES["default"]["ENGINE"].split(".")[-1]
    section.append(f"| Default DB | `{db_engine}` | `settings.DATABASES` |")
    section.append("")
    sections.append("\n".join(section))

    # ---- LOC stats ---------------------------------------------
    section = ["---", "", "## Code Statistics", ""]
    section.append("| Service | Files | Lines |")
    section.append("|---|---|---|")
    total_files = total_lines = 0
    for label in sorted(loc):
        stats = loc[label]
        section.append(f"| `{label}/` | {stats['files']:,} | {stats['lines']:,} |")
        total_files += stats["files"]
        total_lines += stats["lines"]
    section.append(f"| **total** | **{total_files:,}** | **{total_lines:,}** |")
    section.append("")
    section.append(
        "_Excludes `.venv/`, `__pycache__/`, and `migrations/`. "
        "Only `*.py` files. Hand-written code, not generated migrations._"
    )
    section.append("")
    sections.append("\n".join(section))

    # ---- Footer ------------------------------------------------
    sections.append(
        f"---\n\n*Regenerated {meta['generated_at']} from commit "
        f"{meta['git_sha']}. Re-run `python manage.py inventory` "
        f"(from `shell/`) to refresh.*\n"
    )

    return "\n".join(sections)


# ---- helpers -------------------------------------------------------


def _shell(cmd: str) -> str:
    """Run a shell command, return stdout stripped, swallow errors."""
    try:
        out = subprocess.run(
            cmd.split(),
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _module_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "?"
