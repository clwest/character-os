"""bootstrap_review — §19 Step 9.b app skeleton (SESSION 249, 9.b.0).

Bootstrap human-review surface. Reads the frozen 9.a evidence tree
at
``docs/design/visual/portrait_qualification/fixtures/*/runs/bootstrap_20260808T044853Z_7eb392992e0f/``
and (starting 9.b.3) promotes reviewer-selected candidates into the
Canonical Identity substrate.

9.b.0 scope (this app on first landing):

* Data migration provisioning the ``bootstrap-fixtures`` workspace
  (deterministic identity, no memberships, infrastructure only).
* ``IsOperator`` DRF permission gating this app's API surface.
* Placeholder ``GET /api/bootstrap-review/health/`` endpoint that
  proves the operator gate wires end-to-end.
* AST-level boundary test refusing imports from
  ``app.services.portrait_provider.*``,
  ``app.services.benchmark_harness.*``, or ``MediaEngineClient`` —
  9.b code must never regenerate evidence.

Out of scope for 9.b.0 (deferred to 9.b.1+):

* Candidate browsing UI + artifact streaming (9.b.1).
* Reviewer decisions + JSONL journal (9.b.2).
* ``PromotionAudit`` model + promotion service + ``bootstrap/references/``
  materialization + fixture ``CharacterIdentity`` / version creation
  (9.b.3).
* SPA promote/amend flow (9.b.4).
* Closure gate + management command (9.b.5).

See ``docs/SESSION_249_STEP_9B_ARCHITECTURE_PLAN.md`` for the
architecture-anchor references cited above.
"""
from __future__ import annotations

from django.apps import AppConfig


class BootstrapReviewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bootstrap_review"
