"""URL routing for §19 Step 9.b bootstrap-review (SESSION 249).

Registered under ``/api/`` in ``character_os.urls``.

9.b.0 mounted the health endpoint. 9.b.1 adds:

* ``GET /api/bootstrap-review/runs/``
* ``GET /api/bootstrap-review/runs/<bootstrap_run_id>/``
* ``GET /api/bootstrap-review/runs/<bootstrap_run_id>/fixtures/<fixture_id>/``
* ``GET /api/bootstrap-review/runs/<bootstrap_run_id>/fixtures/<fixture_id>/slots/<reference_kind>/<reference_purpose>/``
* ``GET /api/bootstrap-review/artifacts/<bootstrap_run_id>/<direction>/<provider>/<cell_id>/raw.png``
* ``GET /api/bootstrap-review/artifacts/<bootstrap_run_id>/<direction>/<provider>/<cell_id>/normalized.png``
* ``GET /api/bootstrap-review/artifacts/<bootstrap_run_id>/<direction>/<provider>/<cell_id>/manifest.json``
* ``GET /api/bootstrap-review/artifacts/<bootstrap_run_id>/<direction>/<provider>/<cell_id>/candidate.json``

Every path parameter that could carry user input is validated inside
the view via :mod:`.evidence` — the URL patterns only constrain the
lexical shape.
"""
from __future__ import annotations

from django.urls import path

from .views import (
    approve_fixture_version,
    bootstrap_review_health,
    create_decision,
    list_runs,
    promote_slot,
    retrieve_candidate_json,
    retrieve_fixture,
    retrieve_manifest_artifact,
    retrieve_normalized_artifact,
    retrieve_raw_artifact,
    retrieve_run,
    retrieve_slot,
)

# Path converters: use ``<str:x>`` so the view sees the literal string
# and does its own vocabulary validation. Do NOT use ``<slug:x>``
# because a ``.`` in a filename would prevent matching.

urlpatterns = [
    # 9.b.0 — smoke health endpoint.
    path(
        "bootstrap-review/health/",
        bootstrap_review_health,
        name="bootstrap-review-health",
    ),
    # 9.b.1 — read-only browser.
    path(
        "bootstrap-review/runs/",
        list_runs,
        name="bootstrap-review-runs-list",
    ),
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/",
        retrieve_run,
        name="bootstrap-review-run-detail",
    ),
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/fixtures/<str:fixture_id>/",
        retrieve_fixture,
        name="bootstrap-review-fixture-detail",
    ),
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/fixtures/<str:fixture_id>/"
        "slots/<str:reference_kind>/<str:reference_purpose>/",
        retrieve_slot,
        name="bootstrap-review-slot-detail",
    ),
    path(
        "bootstrap-review/artifacts/<str:bootstrap_run_id>/"
        "<str:direction>/<str:provider>/<str:cell_id>/raw.png",
        retrieve_raw_artifact,
        name="bootstrap-review-artifact-raw",
    ),
    path(
        "bootstrap-review/artifacts/<str:bootstrap_run_id>/"
        "<str:direction>/<str:provider>/<str:cell_id>/normalized.png",
        retrieve_normalized_artifact,
        name="bootstrap-review-artifact-normalized",
    ),
    path(
        "bootstrap-review/artifacts/<str:bootstrap_run_id>/"
        "<str:direction>/<str:provider>/<str:cell_id>/manifest.json",
        retrieve_manifest_artifact,
        name="bootstrap-review-artifact-manifest",
    ),
    path(
        "bootstrap-review/artifacts/<str:bootstrap_run_id>/"
        "<str:direction>/<str:provider>/<str:cell_id>/candidate.json",
        retrieve_candidate_json,
        name="bootstrap-review-artifact-candidate",
    ),
    # 9.b.2 — reviewer decision append.
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/fixtures/<str:fixture_id>/"
        "slots/<str:reference_kind>/<str:reference_purpose>/decisions/",
        create_decision,
        name="bootstrap-review-slot-decisions",
    ),
    # 9.b.3b — promote current terminal decision at slot.
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/fixtures/<str:fixture_id>/"
        "slots/<str:reference_kind>/<str:reference_purpose>/promote/",
        promote_slot,
        name="bootstrap-review-slot-promote",
    ),
    # 9.b.3b — admit fixture identity version.
    path(
        "bootstrap-review/runs/<str:bootstrap_run_id>/fixtures/<str:fixture_id>/"
        "approve-version/",
        approve_fixture_version,
        name="bootstrap-review-fixture-approve-version",
    ),
]
