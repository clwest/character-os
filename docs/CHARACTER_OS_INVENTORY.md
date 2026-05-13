---
title: "Character OS Platform Inventory"
status: regenerated
generator: shell/apps/accounts/management/commands/inventory.py
command: python manage.py inventory
generated_at: 2026-05-13T23:27:43.440074+00:00
git_sha: d805291 (working tree dirty)
git_branch: main
---

# Character OS Platform Inventory

> **This document is regenerated.** Do not hand-edit — run
> ``python manage.py inventory`` (from ``shell/``) to refresh.
> Companion to [`CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) —
> that doc explains *what it is*; this one is *what exists right now*.

Generated **2026-05-13T23:27:43.440074+00:00** against commit **d805291**
on branch **main** (working tree dirty).

Python 3.11.6 · Django 5.2.14 ·
Celery 5.6.3 · httpx 0.28.1.

---

## Executive Summary

| Metric | Value | Source |
|---|---|---|
| Django models (project-owned) | **6** | `apps.get_models()` filtered to first-party apps |
| URL routes (total) | **169** | `get_resolver().url_patterns` walk |
| URL routes (`/api/*`) | **35** | same |
| FastAPI routes | **93** | media-engine `/openapi.json` (reachable) |
| Celery tasks (registered) | **2** | `celery_app.tasks` filter |
| Migrations (applied / total) | **40 / 40** | `MigrationRecorder` ∩ `MigrationLoader` |
| Shell LOC (`*.py`, no venv/migrations) | **4,376** in 80 files | `pathlib.Path.rglob("*.py")` |
| Media-engine LOC (`*.py`, no venv/migrations) | **25,519** in 48 files | same |

---

## Django Models (project-owned)

Total: **6** models across **5** apps.

| App | Model | DB Table | Fields | FKs |
|---|---|---|---|---|
| `accounts` | `Membership` | `accounts_membership` | 5 | 2 |
| `accounts` | `Workspace` | `accounts_workspace` | 6 | 1 |
| `billing` | `Subscription` | `billing_subscription` | 9 | 0 |
| `conversations` | `ConversationThread` | `conversations_conversationthread` | 5 | 1 |
| `spokespeople` | `Spokesperson` | `spokespeople_spokesperson` | 11 | 1 |
| `videos` | `Video` | `videos_video` | 14 | 1 |

---

## URL Routes

Total: **169** resolved patterns.

| Prefix | Count |
|---|---|
| `_allauth/` | 19 |
| `accounts/` | 26 |
| `admin/` | 89 |
| `api/` | 35 |

### Named API + auth routes

- `account_change_password`
- `account_confirm_email`
- `account_confirm_login_code`
- `account_email`
- `account_email_verification_sent`
- `account_inactive`
- `account_login`
- `account_logout`
- `account_reauthenticate`
- `account_reset_password`
- `account_reset_password_done`
- `account_reset_password_from_key`
- `account_reset_password_from_key_done`
- `account_set_password`
- `account_signup`
- `api-root`
- `billing-subscription`
- `billing-tiers`
- `change_password`
- `config`
- `confirm_login_code`
- `conversation-detail`
- `conversation-list`
- `current_session`
- `google_callback`
- `google_login`
- `google_login_by_token`
- `login`
- `manage_email`
- `manage_phone`
- `manage_providers`
- `me`
- `membership-detail`
- `membership-list`
- `provider_signup`
- `provider_token`
- `reauthenticate`
- `redirect_to_provider`
- `request_password_reset`
- `resend_email_verification_code`
- `resend_phone_verification_code`
- `reset_password`
- `signup`
- `socialaccount_connections`
- `socialaccount_login_cancelled`
- `socialaccount_login_error`
- `socialaccount_signup`
- `spokesperson-clone-voice`
- `spokesperson-detail`
- `spokesperson-list`
- `verify_email`
- `verify_phone`
- `video-detail`
- `video-list`
- `workspace-detail`
- `workspace-list`
- `workspace-members`

---

## FastAPI Media-Engine Routes

Probed `http://localhost:8001/openapi.json` — `Character OS API` v0.1.0.

Total: **93** routes.

| Prefix | Count |
|---|---|
| `/api/` | 88 |
| `/internal/` | 4 |
| `other` | 1 |

### `/internal/*` surface (Phase 2 contract)

- `/internal/avatars/`
- `/internal/videos/`
- `/internal/videos/{task_id}/`
- `/internal/voices/`

---

## Celery Tasks

Total: **2** registered tasks (excluding `celery.*` built-ins).

- `apps.videos.tasks.poll_video_until_terminal`
- `character_os.celery.debug_task`

---

## Migrations

**40 of 40** migrations applied.

| App | Applied | Total | Pending |
|---|---|---|---|
| `account` | 9 | 9 | 0 |
| `accounts` | 1 | 1 | 0 |
| `admin` | 3 | 3 | 0 |
| `auth` | 12 | 12 | 0 |
| `billing` | 1 | 1 | 0 |
| `contenttypes` | 2 | 2 | 0 |
| `conversations` | 1 | 1 | 0 |
| `sessions` | 1 | 1 | 0 |
| `sites` | 2 | 2 | 0 |
| `socialaccount` | 6 | 6 | 0 |
| `spokespeople` | 1 | 1 | 0 |
| `videos` | 1 | 1 | 0 |

---

## Infrastructure

| Component | State | Source |
|---|---|---|
| Django runserver | `:8000` (when running) | `python manage.py runserver` |
| FastAPI media-engine | `http://localhost:8001` (reachable) | live probe |
| Redis | `redis://localhost:6381` (Docker) | `infra/docker-compose.yml` |
| Celery broker | `redis://localhost:6381/0` | `settings.CELERY_BROKER_URL` |
| Celery result backend | `redis://localhost:6381/1` | `settings.CELERY_RESULT_BACKEND` |
| Default DB | `sqlite3` | `settings.DATABASES` |

---

## Code Statistics

| Service | Files | Lines |
|---|---|---|
| `media-engine/` | 48 | 25,519 |
| `shell/` | 80 | 4,376 |
| **total** | **128** | **29,895** |

_Excludes `.venv/`, `__pycache__/`, and `migrations/`. Only `*.py` files. Hand-written code, not generated migrations._

---

*Regenerated 2026-05-13T23:27:43.440074+00:00 from commit d805291. Re-run `python manage.py inventory` (from `shell/`) to refresh.*
