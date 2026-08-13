"""§19 Step 9.b.1 substrate-zero-write regression guards (SESSION 249).

After exercising the full 9.b.1 read surface, assert that no
canonical-substrate row has been created in the bootstrap-fixtures
workspace. 9.b.1 is READ-ONLY — any substrate write here would be a
scope violation.

Also assert that the frozen 9.a evidence tree is byte-identical to
the git-tracked state (no read has mutated file mtimes or contents
in a way that would show up in ``git status``).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    NormalizationManifest,
)
from apps.spokespeople.models import Teammate

from apps.bootstrap_review.evidence import FROZEN_EVIDENCE_ROOT, FrozenCandidateId
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
HUMAN_FIXTURES = ["fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"]
HUMAN_PURPOSES = [
    "front",
    "slight_left",
    "slight_right",
    "neutral_rest",
    "listening",
    "consideration",
    "gentle_positive",
]


@pytest.fixture()
def staff_client(db):
    User = get_user_model()
    user = User.objects.create_user(email="staff-reg@example.test", password="pw")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_full_read_surface_writes_zero_substrate_rows(staff_client):
    """Exercise every 9.b.1 GET, then assert canonical-substrate row
    counts under the bootstrap-fixtures workspace remain zero.
    """
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)

    # Baseline: nothing exists.
    assert CharacterIdentity.objects.filter(workspace=workspace).count() == 0
    assert CharacterIdentityVersion.objects.filter(
        identity__workspace=workspace
    ).count() == 0
    assert IdentityReference.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert GenerationRecord.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert NormalizationManifest.objects.filter(
        generation_record__identity_version__identity__workspace=workspace
    ).count() == 0
    assert Teammate.objects.filter(workspace=workspace).count() == 0

    # Exercise the full read surface.
    staff_client.get(reverse("bootstrap-review-health"))
    staff_client.get(reverse("bootstrap-review-runs-list"))
    staff_client.get(reverse("bootstrap-review-run-detail", args=[FROZEN_RUN_ID]))
    for fixture_id in HUMAN_FIXTURES:
        staff_client.get(
            reverse(
                "bootstrap-review-fixture-detail",
                args=[FROZEN_RUN_ID, fixture_id],
            )
        )
        for purpose in HUMAN_PURPOSES:
            staff_client.get(
                reverse(
                    "bootstrap-review-slot-detail",
                    args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
                )
            )

    # Hit at least one artifact endpoint of each kind on a known-good
    # candidate to exercise the streaming path.
    good_fcid = FrozenCandidateId.build(
        run_id=FROZEN_RUN_ID,
        direction="identity_only",
        provider="stability_still",
        cell_id="fixture_h1__portrait_reference__front__compact",
    )
    for url_name in (
        "bootstrap-review-artifact-raw",
        "bootstrap-review-artifact-normalized",
        "bootstrap-review-artifact-manifest",
        "bootstrap-review-artifact-candidate",
    ):
        staff_client.get(
            reverse(
                url_name,
                args=[
                    good_fcid.run_id,
                    good_fcid.direction,
                    good_fcid.provider,
                    good_fcid.cell_id,
                ],
            )
        )

    # After all that browsing: still zero substrate rows.
    assert CharacterIdentity.objects.filter(workspace=workspace).count() == 0
    assert CharacterIdentityVersion.objects.filter(
        identity__workspace=workspace
    ).count() == 0
    assert IdentityReference.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert GenerationRecord.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert NormalizationManifest.objects.filter(
        generation_record__identity_version__identity__workspace=workspace
    ).count() == 0
    assert Teammate.objects.filter(workspace=workspace).count() == 0


def test_frozen_9a_evidence_subtree_is_git_clean(staff_client):
    """After exercising the read surface, the frozen 9.a evidence
    subtree (runs/, _runs/, identity.yaml, rationale.md) must remain
    byte-identical to the committed state.

    Scoped intentionally per SESSION 249 9.b.2: journal writes under
    ``fixtures/<id>/bootstrap/review/`` are legitimate runtime state
    (gitignored) — this test asserts the FROZEN evidence subtree only.
    """
    # Re-exercise a subset. Reading is safe; if reads mutate anything,
    # git notices.
    staff_client.get(reverse("bootstrap-review-runs-list"))
    for fixture_id in HUMAN_FIXTURES:
        for purpose in HUMAN_PURPOSES:
            staff_client.get(
                reverse(
                    "bootstrap-review-slot-detail",
                    args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
                )
            )

    repo_root = Path(settings.BASE_DIR).parent

    # Scope: frozen 9.a subtree, NOT bootstrap/review/.
    frozen_paths = [
        f"docs/design/visual/portrait_qualification/fixtures/_runs/",
    ]
    for fixture_id in HUMAN_FIXTURES + ["fixture_nh1"]:
        frozen_paths.extend(
            [
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/runs/",
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/identity.yaml",
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/rationale.md",
            ]
        )

    result = subprocess.run(
        ["git", "status", "--porcelain", *frozen_paths],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"git not available in this environment: {result.stderr}")
    assert result.stdout == "", (
        f"Frozen 9.a evidence subtree is NOT clean after read exercise. "
        f"git status --porcelain output:\n{result.stdout}"
    )


def test_migrations_match_shipped_slices():
    """Every 9.b sub-slice that lands new models carries exactly one
    migration file. Currently:

      * 9.b.0 — ``0001_bootstrap_fixtures_workspace`` (data-only seed).
      * 9.b.1 — none (read-only).
      * 9.b.2 — none (file-first journal, zero DB).
      * 9.b.3a — ``0002_promotion_audit_and_evidence_index``
        (PromotionAudit + BootstrapEvidenceIndex models).

    Extending this list at 9.b.3b or later requires a companion
    edit here so the migration-count discipline stays visible.
    """
    migrations_dir = (
        Path(settings.BASE_DIR)
        / "apps"
        / "bootstrap_review"
        / "migrations"
    )
    migration_files = sorted(
        f.name
        for f in migrations_dir.iterdir()
        if f.suffix == ".py" and f.name != "__init__.py"
    )
    assert migration_files == [
        "0001_bootstrap_fixtures_workspace.py",
        "0002_promotion_audit_and_evidence_index.py",
    ]


def test_9b1_uses_only_authorized_run(staff_client):
    """Sanity: the runs list returns exactly one entry and it is the
    frozen 9.a run. Prevents accidental exposure of a future run.
    """
    response = staff_client.get(reverse("bootstrap-review-runs-list"))
    body = response.json()
    assert len(body["runs"]) == 1
    assert body["runs"][0]["run_id"] == FROZEN_RUN_ID


def test_no_bootstrap_references_writes_after_exercise(staff_client):
    """Every fixture must have an empty ``bootstrap/references/``
    directory after 9.b.1 exercises the full read surface. The
    directory may not even exist yet; the invariant is: any file
    under ``bootstrap/references/`` would be a scope violation.
    """
    for fixture_id in HUMAN_FIXTURES:
        for purpose in HUMAN_PURPOSES:
            staff_client.get(
                reverse(
                    "bootstrap-review-slot-detail",
                    args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
                )
            )
    for fixture_id in HUMAN_FIXTURES:
        bootstrap_refs = FROZEN_EVIDENCE_ROOT / fixture_id / "bootstrap" / "references"
        if not bootstrap_refs.exists():
            continue
        files = [f for f in bootstrap_refs.rglob("*") if f.is_file()]
        assert files == [], (
            f"bootstrap/references/ for {fixture_id} contains {len(files)} "
            f"file(s); 9.b.1 must write nothing under bootstrap/references/."
        )


def test_no_scores_directory_writes(staff_client):
    """9.b.1 must never touch ``scores/``. That subtree belongs to
    Step 10 territory.
    """
    for fixture_id in HUMAN_FIXTURES:
        for purpose in HUMAN_PURPOSES:
            staff_client.get(
                reverse(
                    "bootstrap-review-slot-detail",
                    args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
                )
            )
    for fixture_id in HUMAN_FIXTURES:
        scores_root = (
            FROZEN_EVIDENCE_ROOT
            / fixture_id
            / "runs"
            / FROZEN_RUN_ID
        )
        for candidate_scores_dir in scores_root.rglob("scores"):
            assert not any(candidate_scores_dir.iterdir()), (
                f"scores/ directory found with content under {candidate_scores_dir}"
            )
