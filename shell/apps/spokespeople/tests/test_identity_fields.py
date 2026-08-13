"""Identity surface — five new Teammate fields (SESSION 232).

Locks the contract for the ``/spokespeople/{id}/identity`` page:

* The five new identity fields (``who_you_help``,
  ``what_you_sell``, ``always_emphasize``, ``never_say``,
  ``desired_feeling``) all default empty, all accept PATCH,
  neither create nor edit requires them.
* ``business_brief`` remains the sole server-required identity
  slot (unchanged from wizard v1-floor per the wizard scope-lock).
* ``identity_fields_filled_count()`` on the model + the
  serializer's ``identity_fields_filled`` derived field agree,
  count 0-6, treat whitespace as empty. The SPA reads this to
  drive the ``Define {name}`` → ``Identity`` masthead button
  transition (threshold: >= 4) and the ``N of 6 filled`` progress
  signal on the identity page.
* Cross-workspace isolation continues to hold — a user in
  workspace A cannot PATCH a spokesperson in workspace B via any
  identity field.

Full design lock at ``docs/design/CUSTOMER_JOURNEY_V1.md``
§"The spokesperson detail page — where identity gets defined".
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_teammate(ws: Workspace, *, name: str = "Ruby", **extras) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief=extras.pop("business_brief", "small-batch coffee roaster in Boulder."),
        **extras,
    )


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---- model: identity_fields_filled_count ---------------------------


def test_identity_count_zero_when_all_empty() -> None:
    ws, _ = _make_workspace("id-count-empty@t")
    sp = Teammate.objects.create(
        workspace=ws, name="Blank", business_brief="",
    )
    assert sp.identity_fields_filled_count() == 0


def test_identity_count_one_when_only_business_brief_set() -> None:
    """Post-wizard state — business_brief filled, others empty.
    The v1-floor case. Should read as 1 of 6, well below the >= 4
    threshold that flips the masthead to plain "Identity"."""
    ws, _ = _make_workspace("id-count-brief-only@t")
    sp = _make_teammate(ws)
    assert sp.identity_fields_filled_count() == 1


def test_identity_count_six_when_all_filled() -> None:
    ws, _ = _make_workspace("id-count-all@t")
    sp = Teammate.objects.create(
        workspace=ws,
        name="Full",
        business_brief="A",
        who_you_help="B",
        what_you_sell="C",
        always_emphasize="D",
        never_say="E",
        desired_feeling="F",
    )
    assert sp.identity_fields_filled_count() == 6


def test_identity_count_whitespace_only_reads_as_empty() -> None:
    """Whitespace-only content must NOT tick a slot filled — the
    button state must reflect meaningful text, not a stray space
    from copy-paste."""
    ws, _ = _make_workspace("id-count-ws@t")
    sp = Teammate.objects.create(
        workspace=ws,
        name="Whitespace",
        business_brief="real content",
        who_you_help="   ",
        what_you_sell="\n\t  \n",
        always_emphasize="",
    )
    # Only business_brief has real content.
    assert sp.identity_fields_filled_count() == 1


def test_identity_count_threshold_transition() -> None:
    """The design lock says the masthead button flips from
    "Define {name}" to plain "Identity" once >= 4 of 6 are
    non-empty. This test exercises the threshold boundary — the
    count itself is server-derived so the SPA has one source."""
    ws, _ = _make_workspace("id-count-thresh@t")
    sp = _make_teammate(ws)  # 1 filled (business_brief)
    assert sp.identity_fields_filled_count() == 1
    sp.who_you_help = "small business owners"
    sp.what_you_sell = "coffee subscription boxes"
    sp.save()
    assert sp.identity_fields_filled_count() == 3  # under threshold
    sp.always_emphasize = "small-batch, ethically sourced"
    sp.save()
    assert sp.identity_fields_filled_count() == 4  # at threshold


# ---- serializer: identity_fields_filled derived field --------------


def test_serializer_exposes_identity_fields_filled_read_only() -> None:
    ws, user = _make_workspace("id-ser-ro@t")
    sp = _make_teammate(ws)  # 1 filled
    client = _auth_client(user)
    resp = client.get(f"/api/spokespeople/{sp.pk}/")
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["identity_fields_filled"] == 1
    # All five new fields present in the response, defaulting to
    # empty strings — the SPA form pre-fills from these.
    for field in ("who_you_help", "what_you_sell", "always_emphasize", "never_say", "desired_feeling"):
        assert resp.data[field] == ""


def test_serializer_identity_fields_filled_ignores_client_overrides() -> None:
    """identity_fields_filled is server-derived — a PATCH body
    that tries to set it directly must not corrupt the truth.
    Serializer read_only_fields already covers this, but the test
    locks it explicitly so a future serializer refactor can't
    silently open the field to writes."""
    ws, user = _make_workspace("id-ser-ro-override@t")
    sp = _make_teammate(ws)
    client = _auth_client(user)
    resp = client.patch(
        f"/api/spokespeople/{sp.pk}/",
        data={"identity_fields_filled": 99, "who_you_help": "cafe owners"},
        format="json",
    )
    assert resp.status_code == http.HTTP_200_OK
    # Read-only field ignored on write; new value reflects the
    # real count (business_brief + who_you_help = 2).
    assert resp.data["identity_fields_filled"] == 2


# ---- API: PATCH individual identity fields -------------------------


def test_patch_single_identity_field() -> None:
    ws, user = _make_workspace("id-patch-one@t")
    sp = _make_teammate(ws)
    client = _auth_client(user)
    resp = client.patch(
        f"/api/spokespeople/{sp.pk}/",
        data={"who_you_help": "small business owners in the mountain west"},
        format="json",
    )
    assert resp.status_code == http.HTTP_200_OK
    sp.refresh_from_db()
    assert sp.who_you_help == "small business owners in the mountain west"
    # Other identity fields untouched.
    assert sp.what_you_sell == ""
    assert sp.always_emphasize == ""
    assert sp.never_say == ""
    assert sp.desired_feeling == ""


def test_patch_all_identity_fields_at_once() -> None:
    """The Identity form's Save button PATCHes all six fields in
    one request. All five new + business_brief must land in the
    same transaction."""
    ws, user = _make_workspace("id-patch-all@t")
    sp = _make_teammate(ws)
    client = _auth_client(user)
    payload = {
        "business_brief": "small-batch coffee roaster.",
        "who_you_help": "coffee enthusiasts + specialty shops.",
        "what_you_sell": "single-origin beans + subscriptions.",
        "always_emphasize": "small-batch, ethically sourced, floral notes.",
        "never_say": "never claim organic without certification.",
        "desired_feeling": "trusted, curated, unhurried.",
    }
    resp = client.patch(
        f"/api/spokespeople/{sp.pk}/",
        data=payload,
        format="json",
    )
    assert resp.status_code == http.HTTP_200_OK
    sp.refresh_from_db()
    for field, expected in payload.items():
        assert getattr(sp, field) == expected
    assert resp.data["identity_fields_filled"] == 6


def test_patch_accepts_empty_string_for_new_identity_fields() -> None:
    """The 5 new identity fields explicitly accept empty. The
    customer may clear a slot to return to "coming back to this
    later" state; the API must not reject an empty submission."""
    ws, user = _make_workspace("id-patch-empty@t")
    sp = _make_teammate(
        ws,
        who_you_help="old content",
        what_you_sell="old content",
    )
    client = _auth_client(user)
    resp = client.patch(
        f"/api/spokespeople/{sp.pk}/",
        data={"who_you_help": "", "what_you_sell": ""},
        format="json",
    )
    assert resp.status_code == http.HTTP_200_OK
    sp.refresh_from_db()
    assert sp.who_you_help == ""
    assert sp.what_you_sell == ""


def test_new_spokesperson_defaults_all_five_identity_fields_empty() -> None:
    """The wizard flow doesn't send the 5 new identity fields; they
    must land in the DB as empty strings so the Identity form's
    pre-fill is deterministic."""
    ws, _ = _make_workspace("id-defaults@t")
    sp = _make_teammate(ws)
    assert sp.who_you_help == ""
    assert sp.what_you_sell == ""
    assert sp.always_emphasize == ""
    assert sp.never_say == ""
    assert sp.desired_feeling == ""


# ---- Cross-workspace isolation -------------------------------------


def test_cross_workspace_patch_blocked() -> None:
    """A user in workspace A must not be able to PATCH identity
    fields on a spokesperson in workspace B. The existing
    workspace-membership guard on the viewset covers this; the
    test locks the surface so a future auth refactor can't
    silently open it."""
    ws_a, user_a = _make_workspace("id-iso-a@t")
    ws_b, _ = _make_workspace("id-iso-b@t")
    sp_b = _make_teammate(ws_b, name="B-spokesperson")
    client = _auth_client(user_a)  # authenticated as A's user
    resp = client.patch(
        f"/api/spokespeople/{sp_b.pk}/",
        data={"who_you_help": "attempted cross-workspace write"},
        format="json",
    )
    # Viewset filters spokespeople to the user's workspaces; a
    # foreign row is invisible → 404, not 403.
    assert resp.status_code in (http.HTTP_404_NOT_FOUND, http.HTTP_403_FORBIDDEN)
    sp_b.refresh_from_db()
    assert sp_b.who_you_help == ""
