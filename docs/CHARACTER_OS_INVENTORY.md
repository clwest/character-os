---
title: "Character OS Platform Inventory"
status: regenerated
generator: shell/apps/accounts/management/commands/inventory.py
command: python manage.py inventory
generated_at: 2026-05-14T19:18:22.745309+00:00
git_sha: 7a5ca4a (working tree dirty)
git_branch: main
---

# Character OS Platform Inventory

> **This document is regenerated.** Do not hand-edit — run
> ``python manage.py inventory`` (from ``shell/``) to refresh.
> Companion to [`CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) —
> that doc explains *what it is*; this one is *what exists right now*.

Generated **2026-05-14T19:18:22.745309+00:00** against commit **7a5ca4a**
on branch **main** (working tree dirty).

Python 3.11.6 · Django 5.2.14 ·
Celery 5.6.3 · httpx 0.28.1.

---

## Executive Summary

| Metric | Value | Source |
|---|---|---|
| Django models (project-owned) | **11** | `apps.get_models()` filtered to first-party apps |
| URL routes (total) | **210** | `get_resolver().url_patterns` walk |
| URL routes (`/api/*`) | **52** | same |
| FastAPI routes | **94** | media-engine `/openapi.json` (reachable) |
| Celery tasks (registered) | **2** | `celery_app.tasks` filter |
| Migrations (applied / total) | **46 / 46** | `MigrationRecorder` ∩ `MigrationLoader` |
| Shell LOC (`*.py`, no venv/migrations) | **11,092** in 112 files | `pathlib.Path.rglob("*.py")` |
| Media-engine LOC (`*.py`, no venv/migrations) | **25,676** in 49 files | same |

---

## Django Models (project-owned)

Total: **11** models across **6** apps.

| App | Model | DB Table | Fields | FKs |
|---|---|---|---|---|
| `accounts` | `Membership` | `accounts_membership` | 5 | 2 |
| `accounts` | `User` | `accounts_user` | 8 | 0 |
| `accounts` | `Workspace` | `accounts_workspace` | 6 | 1 |
| `billing` | `Subscription` | `billing_subscription` | 9 | 0 |
| `conversations` | `ConversationEmbedding` | `conversations_conversationembedding` | 8 | 1 |
| `conversations` | `ConversationMessage` | `conversations_conversationmessage` | 5 | 1 |
| `conversations` | `ConversationThread` | `conversations_conversationthread` | 5 | 1 |
| `embeddings` | `KnowledgeChunk` | `embeddings_knowledgechunk` | 12 | 1 |
| `embeddings` | `KnowledgeDocument` | `embeddings_knowledgedocument` | 16 | 2 |
| `spokespeople` | `Spokesperson` | `spokespeople_spokesperson` | 13 | 1 |
| `videos` | `Video` | `videos_video` | 15 | 1 |

---

## URL Routes

Total: **210** resolved patterns.

| Prefix | Count |
|---|---|
| `_allauth/` | 19 |
| `accounts/` | 26 |
| `admin/` | 113 |
| `api/` | 52 |

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
- `knowledge-attach`
- `knowledge-detach`
- `knowledge-detail`
- `knowledge-list`
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
- `spokesperson-generate-portrait`
- `spokesperson-list`
- `spokesperson-templates`
- `spokesperson-voice-presets`
- `suggest-tone`
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

Total: **94** routes.

| Prefix | Count |
|---|---|
| `/api/` | 88 |
| `/internal/` | 5 |
| `other` | 1 |

### `/internal/*` surface (Phase 2 contract)

- `/internal/avatars/`
- `/internal/portrait/`
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

**46 of 46** migrations applied.

| App | Applied | Total | Pending |
|---|---|---|---|
| `account` | 9 | 9 | 0 |
| `accounts` | 1 | 1 | 0 |
| `admin` | 3 | 3 | 0 |
| `auth` | 12 | 12 | 0 |
| `billing` | 1 | 1 | 0 |
| `contenttypes` | 2 | 2 | 0 |
| `conversations` | 2 | 2 | 0 |
| `embeddings` | 2 | 2 | 0 |
| `sessions` | 1 | 1 | 0 |
| `sites` | 2 | 2 | 0 |
| `socialaccount` | 6 | 6 | 0 |
| `spokespeople` | 3 | 3 | 0 |
| `videos` | 2 | 2 | 0 |

---

## Infrastructure

| Component | State | Source |
|---|---|---|
| Django runserver | `:8000` (when running) | `python manage.py runserver` |
| FastAPI media-engine | `http://localhost:8001` (reachable) | live probe |
| Redis | `redis://localhost:6381` (Docker) | `infra/docker-compose.yml` |
| Celery broker | `redis://localhost:6381/0` | `settings.CELERY_BROKER_URL` |
| Celery result backend | `redis://localhost:6381/1` | `settings.CELERY_RESULT_BACKEND` |
| Default DB | `postgresql` | `settings.DATABASES` |

---

## Code Statistics

| Service | Files | Lines |
|---|---|---|
| `media-engine/` | 49 | 25,676 |
| `shell/` | 112 | 11,092 |
| **total** | **161** | **36,768** |

_Excludes `.venv/`, `__pycache__/`, and `migrations/`. Only `*.py` files. Hand-written code, not generated migrations._

---

*Regenerated 2026-05-14T19:18:22.745309+00:00 from commit 7a5ca4a. Re-run `python manage.py inventory` (from `shell/`) to refresh.*
