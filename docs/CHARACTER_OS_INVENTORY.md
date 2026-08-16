---
title: "Character OS Platform Inventory"
status: regenerated
generator: shell/apps/accounts/management/commands/inventory.py
command: python manage.py inventory
generated_at: 2026-08-16T20:10:58.356155+00:00
git_sha: d22d8e1 (working tree dirty)
git_branch: public
---

# Character OS Platform Inventory

> **This document is regenerated.** Do not hand-edit — run
> ``python manage.py inventory`` (from ``shell/``) to refresh.
> Companion to [`CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) —
> that doc explains *what it is*; this one is *what exists right now*.

Generated **2026-08-16T20:10:58.356155+00:00** against commit **d22d8e1**
on branch **public** (working tree dirty).

Python 3.11.6 · Django 5.2.16 ·
Celery 5.6.3 · httpx 0.27.2.

---

## Executive Summary

| Metric | Value | Source |
|---|---|---|
| Django models (project-owned) | **37** | `apps.get_models()` filtered to first-party apps |
| URL routes (total) | **418** | `get_resolver().url_patterns` walk |
| URL routes (`/api/*`) | **188** | same |
| FastAPI routes | **125** | media-engine `/openapi.json` (reachable) |
| Celery tasks (registered) | **10** | `celery_app.tasks` filter |
| Migrations (applied / total) | **97 / 97** | `MigrationRecorder` ∩ `MigrationLoader` |
| Shell LOC (`*.py`, no venv/migrations) | **113,478** in 401 files | `pathlib.Path.rglob("*.py")` |
| Media-engine LOC (`*.py`, no venv/migrations) | **63,533** in 156 files | same |

---

## Django Models (project-owned)

Total: **37** models across **14** apps.

| App | Model | DB Table | Fields | FKs |
|---|---|---|---|---|
| `accounts` | `Membership` | `accounts_membership` | 5 | 2 |
| `accounts` | `User` | `accounts_user` | 8 | 0 |
| `accounts` | `Workspace` | `accounts_workspace` | 6 | 1 |
| `billing` | `Subscription` | `billing_subscription` | 9 | 0 |
| `bootstrap_review` | `BootstrapEvidenceIndex` | `bootstrap_review_bootstrapevidenceindex` | 7 | 4 |
| `bootstrap_review` | `PromotionAudit` | `bootstrap_review_promotionaudit` | 22 | 7 |
| `campaigns` | `PersonalizedCampaign` | `campaigns_personalizedcampaign` | 13 | 4 |
| `campaigns` | `PersonalizedRecipient` | `campaigns_personalizedrecipient` | 11 | 2 |
| `compositions` | `Asset` | `compositions_asset` | 25 | 4 |
| `compositions` | `Composition` | `compositions_composition` | 20 | 4 |
| `compositions` | `CompositionStep` | `compositions_compositionstep` | 15 | 2 |
| `conversations` | `ConversationEmbedding` | `conversations_conversationembedding` | 8 | 1 |
| `conversations` | `ConversationMessage` | `conversations_conversationmessage` | 8 | 1 |
| `conversations` | `ConversationThread` | `conversations_conversationthread` | 5 | 1 |
| `embeddings` | `KnowledgeChunk` | `embeddings_knowledgechunk` | 12 | 1 |
| `embeddings` | `KnowledgeDocument` | `embeddings_knowledgedocument` | 16 | 2 |
| `embeddings` | `KnowledgeDocumentSpokesperson` | `embeddings_knowledgedocument_spokespeople` | 3 | 2 |
| `identity` | `ApprovedRepresentationBundle` | `identity_approvedrepresentationbundle` | 8 | 4 |
| `identity` | `CanonicalRealtimeReference` | `identity_canonicalrealtimereference` | 6 | 2 |
| `identity` | `CanonicalVoiceReference` | `identity_canonicalvoicereference` | 6 | 2 |
| `identity` | `CharacterIdentity` | `identity_characteridentity` | 7 | 2 |
| `identity` | `CharacterIdentityVersion` | `identity_characteridentityversion` | 11 | 2 |
| `identity` | `GenerationRecord` | `identity_generationrecord` | 16 | 3 |
| `identity` | `GenerationRecordInput` | `identity_generationrecordinput` | 4 | 2 |
| `identity` | `IdentityReference` | `identity_identityreference` | 9 | 3 |
| `identity` | `ImportProvenance` | `identity_importprovenance` | 8 | 0 |
| `identity` | `NormalizationManifest` | `identity_normalizationmanifest` | 13 | 2 |
| `identity` | `PrequalificationProvenance` | `identity_prequalificationprovenance` | 6 | 1 |
| `publish` | `PublishBundle` | `publish_publishbundle` | 11 | 3 |
| `publish` | `PublishVariant` | `publish_publishvariant` | 10 | 2 |
| `realtime` | `EngineConnection` | `realtime_engineconnection` | 11 | 1 |
| `realtime` | `RealtimeSession` | `realtime_realtimesession` | 23 | 5 |
| `realtime` | `RealtimeToolInvocation` | `realtime_realtimetoolinvocation` | 10 | 3 |
| `scripts` | `Script` | `scripts_script` | 20 | 3 |
| `spokespeople` | `Teammate` | `spokespeople_spokesperson` | 26 | 1 |
| `transcripts` | `TranscriptHighlight` | `transcripts_transcripthighlight` | 16 | 3 |
| `videos` | `Video` | `videos_video` | 16 | 2 |

---

## URL Routes

Total: **418** resolved patterns.

| Prefix | Count |
|---|---|
| `_allauth/` | 19 |
| `accounts/` | 26 |
| `admin/` | 185 |
| `api/` | 188 |

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
- `asset-list`
- `billing-subscription`
- `billing-tiers`
- `bootstrap-review-artifact-candidate`
- `bootstrap-review-artifact-manifest`
- `bootstrap-review-artifact-normalized`
- `bootstrap-review-artifact-raw`
- `bootstrap-review-fixture-approve-version`
- `bootstrap-review-fixture-detail`
- `bootstrap-review-health`
- `bootstrap-review-run-detail`
- `bootstrap-review-runs-list`
- `bootstrap-review-slot-decisions`
- `bootstrap-review-slot-detail`
- `bootstrap-review-slot-promote`
- `campaign-detail`
- `campaign-forecast`
- `campaign-launch`
- `campaign-list`
- `campaign-parse-csv-action`
- `campaign-recipients-action`
- `campaign-retry-recipient-action`
- `change_password`
- `composition-detail`
- `composition-lineage`
- `composition-list`
- `config`
- `confirm_login_code`
- `conversation-detail`
- `conversation-list`
- `conversation-messages`
- `current_session`
- `engine-connection-detail`
- `engine-connection-list`
- `engine-connection-test-ping`
- `google_callback`
- `google_login`
- `google_login_by_token`
- `image-detail`
- `image-list`
- `knowledge-attach`
- `knowledge-compositions`
- `knowledge-detach`
- `knowledge-detail`
- `knowledge-list`
- `knowledge-preview`
- `knowledge-search`
- `login`
- `manage_email`
- `manage_phone`
- `manage_providers`
- `me`
- `membership-detail`
- `membership-list`
- `provider-health`
- `provider_signup`
- `provider_token`
- `publish-bundle-detail`
- `publish-bundle-forecast`
- `publish-bundle-launch`
- `publish-bundle-list`
- `publish-bundle-retry-variant-action`
- `publish-bundle-variants-action`
- `realtime-session-cost-estimate`
- `realtime-session-detail`
- `realtime-session-end`
- `realtime-session-invoke-tool`
- `realtime-session-list`
- `realtime-tool-invocation-approve`
- `realtime-tool-invocation-detail`
- `realtime-tool-invocation-list`
- `realtime-tool-invocation-reject`
- `reauthenticate`
- `recipe-detail`
- `recipe-list`
- `redirect_to_provider`
- `request_password_reset`
- `resend_email_verification_code`
- `resend_phone_verification_code`
- `reset_password`
- `script-approve`
- `script-clone`
- `script-derived-campaigns`
- `script-detail`
- `script-list`
- `script-regenerate`
- `script-render`
- `signup`
- `socialaccount_connections`
- `socialaccount_login_cancelled`
- `socialaccount_login_error`
- `socialaccount_signup`
- `spokesperson-ask`
- `spokesperson-change-voice`
- `spokesperson-clone-voice`
- `spokesperson-detail`
- `spokesperson-generate-portrait`
- `spokesperson-list`
- `spokesperson-rebake-avatar`
- `spokesperson-refresh-portrait`
- `spokesperson-templates`
- `spokesperson-voice-presets`
- `style-list`
- `suggest-tone`
- `transcript-highlight-approve`
- `transcript-highlight-detail`
- `transcript-highlight-list`
- `transcript-highlight-mine`
- `transcript-highlight-reject`
- `verify_email`
- `verify_phone`
- `video-detail`
- `video-list`
- `workspace-asset-detail`
- `workspace-asset-list`
- `workspace-detail`
- `workspace-list`
- `workspace-members`
- `workspace-overview`

---

## FastAPI Media-Engine Routes

Probed `http://localhost:8001/openapi.json` — `Character OS API` v0.1.0.

Total: **125** routes.

| Prefix | Count |
|---|---|
| `/api/` | 88 |
| `/internal/` | 36 |
| `other` | 1 |

### `/internal/*` surface (Phase 2 contract)

- `/internal/audio/dub/`
- `/internal/audio/extract/`
- `/internal/audio/mix/`
- `/internal/audio/tts/`
- `/internal/avatars/`
- `/internal/avatars/{avatar_id}/change-personality/`
- `/internal/avatars/{avatar_id}/change-voice/`
- `/internal/avatars/{avatar_id}/persist_portrait/`
- `/internal/avatars/{avatar_id}/refresh/`
- `/internal/clips/avatar_speech/`
- `/internal/clips/captions/`
- `/internal/clips/composite/`
- `/internal/clips/concat/`
- `/internal/clips/extend/`
- `/internal/clips/image_overlay/`
- `/internal/clips/intro_outro/`
- `/internal/clips/overlay_audio/`
- `/internal/clips/reformat/`
- `/internal/clips/remove_background/`
- `/internal/clips/style_remix/`
- `/internal/clips/trim/`
- `/internal/clips/visual/`
- `/internal/image_stability/`
- `/internal/images/`
- `/internal/portrait/`
- `/internal/realtime_documents/`
- `/internal/realtime_sessions/`
- `/internal/realtime_sessions/{session_id}/`
- `/internal/realtime_sessions/{session_id}/transcript/`
- `/internal/styles/`
- `/internal/tasks/{task_id}/`
- `/internal/transcribe/`
- `/internal/videos/`
- `/internal/videos/{task_id}/`
- `/internal/voices/`
- `/internal/voices/design/`

---

## Celery Tasks

Total: **10** registered tasks (excluding `celery.*` built-ins).

- `apps.compositions.tasks.execute_composition`
- `apps.compositions.tasks.retry_step`
- `apps.compositions.tasks.sweep_expired_assets`
- `apps.videos.tasks.poll_video_until_terminal`
- `character_os.celery.debug_task`
- `conversations.embed_message`
- `embeddings.embed_document`
- `realtime.execute_tool_invocation`
- `realtime.fetch_transcript_for_session`
- `spokespeople.sync_personality_to_runway`

---

## Migrations

**97 of 97** migrations applied.

| App | Applied | Total | Pending |
|---|---|---|---|
| `account` | 9 | 9 | 0 |
| `accounts` | 1 | 1 | 0 |
| `admin` | 3 | 3 | 0 |
| `auth` | 12 | 12 | 0 |
| `billing` | 1 | 1 | 0 |
| `bootstrap_review` | 2 | 2 | 0 |
| `campaigns` | 3 | 3 | 0 |
| `compositions` | 13 | 13 | 0 |
| `contenttypes` | 2 | 2 | 0 |
| `conversations` | 5 | 5 | 0 |
| `embeddings` | 4 | 4 | 0 |
| `identity` | 9 | 9 | 0 |
| `publish` | 1 | 1 | 0 |
| `realtime` | 5 | 5 | 0 |
| `scripts` | 2 | 2 | 0 |
| `sessions` | 1 | 1 | 0 |
| `sites` | 2 | 2 | 0 |
| `socialaccount` | 6 | 6 | 0 |
| `spokespeople` | 11 | 11 | 0 |
| `transcripts` | 1 | 1 | 0 |
| `videos` | 4 | 4 | 0 |

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
| `media-engine/` | 156 | 63,533 |
| `shell/` | 401 | 113,478 |
| **total** | **557** | **177,011** |

_Excludes `.venv/`, `__pycache__/`, and `migrations/`. Only `*.py` files. Hand-written code, not generated migrations._

---

*Regenerated 2026-08-16T20:10:58.356155+00:00 from commit d22d8e1. Re-run `python manage.py inventory` (from `shell/`) to refresh.*
