"""SESSION 210 — `sweep_expired_assets` Celery task tests.

Closes the last queued SESSION 209 calibration finding:
expired-asset accumulation. Runway's Cloudfront URLs carry a
24-hour JWT ``exp`` claim; once it's past, the SPA still shows
the Composition row as having a deliverable, but clicking it
404s. The hourly Celery Beat sweep detaches the
``Composition.final_asset`` FK for any row whose final asset
classifies as ``HTTPS_EXPIRED``. The Asset row itself is
preserved (cost provenance + Asset Library expired badge).

Covers:

* Composition with expired final_asset gets detached.
* Composition with live final_asset is untouched.
* Composition with expiring-soon final_asset is untouched
  (sweep is for *expired*, not *almost expired* — the badge
  warns operators ahead of time).
* Composition with no final_asset is untouched.
* Idempotency — running twice leaves the same state.
* Multi-composition mix: live + expired + expiring rows
  in one pass produce the right detach count.
* Asset row itself is preserved (provenance kept).
"""
from __future__ import annotations

import base64
import json
import time

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
)
from apps.compositions.tasks import sweep_expired_assets
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- JWT fixture helpers (mirrors test_storage_health.py) -----------


def _b64url_encode(payload: dict) -> str:
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_jwt(exp_seconds: int) -> str:
    header = _b64url_encode({"alg": "HS256", "typ": "JWT"})
    payload = _b64url_encode(
        {"keyHash": "x", "bucket": "runway-task-artifacts", "exp": exp_seconds}
    )
    return f"{header}.{payload}.fake_signature"


def _cdn_url(exp_seconds: int) -> str:
    return (
        f"https://dnznrvs05pmza.cloudfront.net/abc.mp4?_jwt={_make_jwt(exp_seconds)}"
    )


# ---- workspace / composition helpers --------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_spokesperson(ws: Workspace, name: str = "Sp") -> Spokesperson:
    return Spokesperson.objects.create(workspace=ws, name=name)


def _make_composition_with_asset(
    ws: Workspace,
    sp: Spokesperson,
    file_path: str,
    name: str = "test",
) -> tuple[Composition, Asset]:
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
        mock_mode=True,
    )
    asset = Asset.objects.create(
        workspace=ws,
        composition=comp,
        asset_type=AssetType.CLIP,
        file_path=file_path,
        cost_micros=0,
    )
    comp.final_asset = asset
    comp.save(update_fields=["final_asset", "updated_at"])
    return comp, asset


# ---- tests ----------------------------------------------------------


def test_expired_final_asset_gets_detached() -> None:
    """The headline path: a Composition whose final_asset's JWT
    is in the past should have final_asset SET_NULL after the
    sweep."""
    ws = _make_workspace("sweep-expired@test.local")
    sp = _make_spokesperson(ws)
    past = int(time.time()) - 3600
    comp, _asset = _make_composition_with_asset(ws, sp, _cdn_url(past))

    result = sweep_expired_assets()

    comp.refresh_from_db()
    assert comp.final_asset_id is None
    assert result["expired"] == 1
    assert result["detached"] == 1


def test_live_final_asset_is_untouched() -> None:
    """A Composition with a JWT well into the future shouldn't be
    touched by the sweep — that's a perfectly usable render."""
    ws = _make_workspace("sweep-live@test.local")
    sp = _make_spokesperson(ws)
    future = int(time.time()) + 7 * 24 * 3600
    comp, asset = _make_composition_with_asset(ws, sp, _cdn_url(future))

    result = sweep_expired_assets()

    comp.refresh_from_db()
    assert comp.final_asset_id == asset.id
    assert result["expired"] == 0
    assert result["detached"] == 0


def test_expiring_soon_is_untouched() -> None:
    """expiring_soon (<24h to expiry) is the operator's early-
    warning signal; the sweep targets *already-expired* only."""
    ws = _make_workspace("sweep-soon@test.local")
    sp = _make_spokesperson(ws)
    soon = int(time.time()) + 6 * 3600
    comp, asset = _make_composition_with_asset(ws, sp, _cdn_url(soon))

    result = sweep_expired_assets()

    comp.refresh_from_db()
    assert comp.final_asset_id == asset.id
    assert result["expired"] == 0


def test_composition_with_no_final_asset_is_untouched() -> None:
    """Compositions without a final_asset (DRAFT / FAILED on
    step 0) don't appear in the scan at all."""
    ws = _make_workspace("sweep-empty@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="no-asset",
        mock_mode=True,
    )

    result = sweep_expired_assets()

    comp.refresh_from_db()
    assert comp.final_asset_id is None
    assert result["detached"] == 0


def test_local_path_asset_is_untouched() -> None:
    """Local-file assets (`/data/...`) can never be HTTPS_EXPIRED;
    the sweep's HTTPS-prefix filter excludes them at the DB
    level. Confirms we don't accidentally scan or detach them."""
    ws = _make_workspace("sweep-local@test.local")
    sp = _make_spokesperson(ws)
    comp, asset = _make_composition_with_asset(
        ws, sp, "/data/_internal/concats/sweep_local.mp4",
    )

    result = sweep_expired_assets()

    comp.refresh_from_db()
    assert comp.final_asset_id == asset.id
    # Local file_path doesn't match the https:// startswith filter,
    # so it isn't even scanned.
    assert result["scanned"] == 0


def test_idempotent_on_second_run() -> None:
    """Running the sweep twice leaves the same end state — the
    second pass has nothing left to detach."""
    ws = _make_workspace("sweep-idem@test.local")
    sp = _make_spokesperson(ws)
    past = int(time.time()) - 3600
    comp, asset = _make_composition_with_asset(ws, sp, _cdn_url(past))

    first = sweep_expired_assets()
    assert first["detached"] == 1

    second = sweep_expired_assets()
    # Asset row still exists with the same file_path, so the
    # scan still counts it as expired — but no Composition
    # points at it anymore, so nothing gets detached.
    assert second["expired"] == 1
    assert second["detached"] == 0

    comp.refresh_from_db()
    assert comp.final_asset_id is None


def test_mixed_compositions_in_one_pass() -> None:
    """One sweep across a workspace with live + expired + soon +
    no-asset compositions detaches exactly the expired one."""
    ws = _make_workspace("sweep-mix@test.local")
    sp = _make_spokesperson(ws)
    past = int(time.time()) - 3600
    soon = int(time.time()) + 6 * 3600
    future = int(time.time()) + 7 * 24 * 3600

    comp_live, _ = _make_composition_with_asset(
        ws, sp, _cdn_url(future), name="live",
    )
    comp_expired, _ = _make_composition_with_asset(
        ws, sp, _cdn_url(past), name="expired",
    )
    comp_soon, _ = _make_composition_with_asset(
        ws, sp, _cdn_url(soon), name="soon",
    )
    comp_empty = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="empty", mock_mode=True,
    )

    result = sweep_expired_assets()

    comp_live.refresh_from_db()
    comp_expired.refresh_from_db()
    comp_soon.refresh_from_db()
    comp_empty.refresh_from_db()

    assert comp_live.final_asset_id is not None
    assert comp_expired.final_asset_id is None
    assert comp_soon.final_asset_id is not None
    assert comp_empty.final_asset_id is None

    assert result["scanned"] == 3  # three HTTPS URLs
    assert result["expired"] == 1
    assert result["detached"] == 1


def test_asset_row_preserved_after_detach() -> None:
    """The Asset row itself isn't deleted — the operator sees
    the expired Asset Library entry (with the expired badge)
    so the cost provenance is preserved."""
    ws = _make_workspace("sweep-preserve@test.local")
    sp = _make_spokesperson(ws)
    past = int(time.time()) - 3600
    _comp, asset = _make_composition_with_asset(ws, sp, _cdn_url(past))

    sweep_expired_assets()

    # Asset row still exists with the same file_path.
    assert Asset.objects.filter(pk=asset.pk).exists()
    asset.refresh_from_db()
    assert asset.file_path.startswith("https://")
