"""§19 Step 4.e — Read-only regression + management-command tests.

The verifier is required by §17.10.a Amendment 4 to be strictly
read-only. This module locks that discipline via two independent
mechanisms:

1. **Behavioral snapshots** — dump every relevant row's state before
   the verifier runs, invoke the verifier, dump again, and assert
   byte-equivalent state afterward.
2. **Structural AST inspection** — walk ``apps.identity.compat``'s
   verifier code and assert no ``.save`` / ``.objects.create`` /
   ``.objects.update`` / ``.objects.delete`` / ``.objects.bulk_*``
   calls appear.

Plus management-command tests covering:

* Default human-readable output.
* ``--json`` produces the ratified stable JSON shape.
* ``--workspace <UUID>`` filters correctly.
* ``--fail-on-drift`` exits ``1`` on drift, ``0`` on clean +
  N/A-only.
* Invalid workspace UUID raises ``CommandError``.
"""
from __future__ import annotations

import ast
import inspect
import io
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import compat, services
from apps.identity.models import (
    ApprovedRepresentationBundle,
    CanonicalRealtimeReference,
    CanonicalVoiceReference,
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ImportProvenance,
    PrequalificationSourceCall,
    ReferenceState,
)
from apps.identity.prequalification import (
    PortraitRepresentation,
    RealtimeRepresentation,
    VoiceRepresentation,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# =====================================================================
# Fixtures
# =====================================================================


def _make_teammate(email: str, *, name: str = "Ruby"):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    teammate = Teammate.objects.create(workspace=ws, name=name)
    return teammate, user


def _seed_full_authoring(teammate: Teammate, user) -> None:
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=PortraitRepresentation(
            portrait_uri="https://prov/p.png",
            provider=GenerationProvider.MOCK,
            provider_model="mock-1",
            execution_mode=ExecutionMode.FORCED_MOCK,
            execution_mode_actual=ExecutionModeActual.MOCK,
            mock_mode=True,
            provider_response={},
        ),
        voice=VoiceRepresentation(
            provider_voice_id="vincent",
            provider=GenerationProvider.RUNWAY_TTS,
            provider_model="",
            execution_mode=ExecutionMode.REAL_REQUIRED,
            execution_mode_actual=ExecutionModeActual.REAL,
            mock_mode=False,
            voice_kind="preset",
            provider_response={},
        ),
        realtime=RealtimeRepresentation(
            provider_realtime_id="avatar_v1",
            provider=GenerationProvider.RUNWAY_AVATAR,
            provider_model="",
            execution_mode=ExecutionMode.REAL_REQUIRED,
            execution_mode_actual=ExecutionModeActual.REAL,
            mock_mode=False,
            provider_response={},
        ),
    )
    teammate.refresh_from_db()


def _snapshot_state():
    """Snapshot every row's mirror-relevant fields for read-only
    regression comparison. Ordered dicts so the comparison is
    deterministic.
    """
    return {
        "teammates": [
            {
                "id": str(t.id),
                "portrait_path": t.portrait_path,
                "voice_id": t.voice_id,
                "runway_avatar_id": t.runway_avatar_id,
                "runway_avatar_status": t.runway_avatar_status,
                "status": t.status,
                "updated_at": t.updated_at.isoformat(),
            }
            for t in Teammate.objects.all().order_by("id")
        ],
        "identities": [
            {
                "id": str(i.id),
                "teammate_id": str(i.teammate_id) if i.teammate_id else None,
                "workspace_id": str(i.workspace_id),
                "kind": i.kind,
                "name": i.name,
                "archived_at": i.archived_at.isoformat() if i.archived_at else None,
            }
            for i in CharacterIdentity.objects.all().order_by("id")
        ],
        "versions": [
            {
                "id": str(v.id),
                "identity_id": str(v.identity_id),
                "revision": v.revision,
                "state": v.state,
                "spec": v.spec,
                "spec_schema_version": v.spec_schema_version,
                "approved_at": v.approved_at.isoformat() if v.approved_at else None,
                "superseded_at": (
                    v.superseded_at.isoformat() if v.superseded_at else None
                ),
            }
            for v in CharacterIdentityVersion.objects.all().order_by("id")
        ],
        "references": [
            {
                "id": str(r.id),
                "identity_version_id": str(r.identity_version_id),
                "asset_id": str(r.asset_id),
                "kind": r.kind,
                "purpose": r.purpose,
                "state": r.state,
            }
            for r in IdentityReference.objects.all().order_by("id")
        ],
        "voice_refs": [
            {
                "id": str(r.id),
                "identity_version_id": str(r.identity_version_id),
                "state": r.state,
            }
            for r in CanonicalVoiceReference.objects.all().order_by("id")
        ],
        "realtime_refs": [
            {
                "id": str(r.id),
                "identity_version_id": str(r.identity_version_id),
                "state": r.state,
            }
            for r in CanonicalRealtimeReference.objects.all().order_by("id")
        ],
        "bundles": [
            {
                "id": str(b.id),
                "identity_version_id": str(b.identity_version_id),
                "approved_voice_id": (
                    str(b.approved_voice_id) if b.approved_voice_id else None
                ),
                "approved_realtime_id": (
                    str(b.approved_realtime_id)
                    if b.approved_realtime_id else None
                ),
                "state": b.state,
                "approved_at": (
                    b.approved_at.isoformat() if b.approved_at else None
                ),
            }
            for b in ApprovedRepresentationBundle.objects.all().order_by("id")
        ],
        "generation_records": [
            {
                "id": str(r.id),
                "identity_version_id": str(r.identity_version_id),
                "provider": r.provider,
                "approval_state": r.approval_state,
            }
            for r in GenerationRecord.objects.all().order_by("id")
        ],
    }


# =====================================================================
# Behavioral read-only regression — verify_teammate_mirrors
# =====================================================================


def test_verify_teammate_mirrors_does_not_mutate_state() -> None:
    teammate, user = _make_teammate("ro-single@t")
    _seed_full_authoring(teammate, user)
    before = _snapshot_state()
    compat.verify_teammate_mirrors(teammate)
    after = _snapshot_state()
    assert before == after, (
        "verify_teammate_mirrors mutated state. Read-only invariant "
        "violated. Diff:\n"
        + _describe_diff(before, after)
    )


def test_verify_teammate_mirrors_on_no_identity_teammate_does_not_mutate() -> None:
    teammate, _ = _make_teammate("ro-no-id@t")
    teammate.portrait_path = "https://x/p.png"
    teammate.voice_id = "vincent"
    teammate.runway_avatar_id = "avatar_x"
    teammate.save(
        update_fields=["portrait_path", "voice_id", "runway_avatar_id"],
    )
    before = _snapshot_state()
    result = compat.verify_teammate_mirrors(teammate)
    after = _snapshot_state()
    assert result.canonical_backfill_required is True  # sanity
    assert before == after, (
        "verify_teammate_mirrors mutated state on a no-identity "
        "teammate (a scenario where a naive impl could accidentally "
        "manufacture canonical state). Diff:\n"
        + _describe_diff(before, after)
    )


# =====================================================================
# Behavioral read-only regression — verify_all_mirrors
# =====================================================================


def test_verify_all_mirrors_does_not_mutate_state() -> None:
    tm_a, _ = _make_teammate("ro-all-a@t", name="A")
    tm_b, user_b = _make_teammate("ro-all-b@t", name="B")
    _seed_full_authoring(tm_b, user_b)
    tm_a.portrait_path = "https://a/p.png"
    tm_a.save(update_fields=["portrait_path"])

    before = _snapshot_state()
    compat.verify_all_mirrors()
    after = _snapshot_state()
    assert before == after, (
        "verify_all_mirrors mutated state. Diff:\n"
        + _describe_diff(before, after)
    )


# =====================================================================
# Structural AST inspection — verifier code contains no writes
# =====================================================================


_VERIFIER_FUNCTIONS = frozenset({
    "verify_teammate_mirrors",
    "verify_all_mirrors",
    "_compare_field",
    "_build_no_identity_result",
    "_classify_identity_version",
})

_FORBIDDEN_MANAGER_METHODS = frozenset({
    "create",
    "update",
    "update_or_create",
    "get_or_create",
    "bulk_create",
    "bulk_update",
    "delete",
})


def test_verifier_source_contains_no_mutation_calls() -> None:
    """AST-walk the verifier functions and assert no calls to
    ``.objects.<mutation>`` or ``.save()`` appear.
    """
    tree = ast.parse(inspect.getsource(compat))
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in _VERIFIER_FUNCTIONS:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if isinstance(func, ast.Attribute):
                # Direct ``.save`` / ``.delete`` on an instance.
                if func.attr in {"save", "delete"}:
                    offenders.append(
                        f"{node.name}:{inner.lineno} — .{func.attr}()"
                    )
                # ``.objects.<mutation>``
                if (
                    func.attr in _FORBIDDEN_MANAGER_METHODS
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "objects"
                ):
                    offenders.append(
                        f"{node.name}:{inner.lineno} — .objects.{func.attr}()"
                    )
    assert not offenders, (
        "Verifier code contains mutation calls — §17.10.a "
        "Amendment 4 requires the verifier be strictly read-only. "
        "Offenders:\n" + "\n".join(offenders)
    )


# =====================================================================
# Management command — human-readable default
# =====================================================================


def test_command_human_readable_default_output() -> None:
    tm_clean, user_clean = _make_teammate("cmd-clean@t")
    _seed_full_authoring(tm_clean, user_clean)
    tm_debt, _ = _make_teammate("cmd-debt@t")
    tm_debt.portrait_path = "https://debt/p.png"
    tm_debt.save(update_fields=["portrait_path"])

    buf = io.StringIO()
    call_command("verify_identity_mirrors", stdout=buf)
    output = buf.getvalue()
    assert "Total Teammates inspected: 2" in output
    assert "Canonical backfill required:      1" in output
    assert "canonical_identity_required" in output
    assert "backfill_identity_substrate" in output  # remediation hint


# =====================================================================
# Management command — --json shape
# =====================================================================


def test_command_json_output_is_stable_shape() -> None:
    tm, user = _make_teammate("cmd-json@t")
    _seed_full_authoring(tm, user)

    buf = io.StringIO()
    call_command("verify_identity_mirrors", "--json", stdout=buf)
    payload = json.loads(buf.getvalue())

    # Top-level shape
    assert set(payload.keys()) == {"summary", "teammates"}
    # Summary shape
    summary = payload["summary"]
    for key in {
        "total_inspected",
        "identity_class_counts",
        "clean_match_count",
        "drift_count",
        "canonical_backfill_required_count",
        "drift_by_field",
        "drift_by_reason",
        "na_by_reason",
    }:
        assert key in summary, f"summary missing key {key!r}"
    # Per-teammate shape
    assert len(payload["teammates"]) == 1
    tm_payload = payload["teammates"][0]
    for key in {
        "teammate_id",
        "workspace_id",
        "identity_class",
        "has_drift",
        "canonical_backfill_required",
        "fields",
    }:
        assert key in tm_payload, f"teammate payload missing key {key!r}"
    # Field shape
    for field_name in {"portrait_path", "voice_id", "runway_avatar_id"}:
        assert field_name in tm_payload["fields"]
        f = tm_payload["fields"][field_name]
        for key in {"mirror_value", "canonical_value", "status", "reason"}:
            assert key in f, f"field {field_name} missing key {key!r}"


# =====================================================================
# Management command — --workspace filter
# =====================================================================


def test_command_workspace_filter() -> None:
    tm_a, _ = _make_teammate("cmd-ws-a@t", name="A")
    tm_b, _ = _make_teammate("cmd-ws-b@t", name="B")

    buf = io.StringIO()
    call_command(
        "verify_identity_mirrors",
        "--workspace", str(tm_a.workspace_id),
        "--json",
        stdout=buf,
    )
    payload = json.loads(buf.getvalue())
    assert payload["summary"]["total_inspected"] == 1
    assert payload["teammates"][0]["teammate_id"] == str(tm_a.id)


def test_command_invalid_workspace_uuid_raises_command_error() -> None:
    with pytest.raises(CommandError, match="must be a UUID"):
        call_command("verify_identity_mirrors", "--workspace", "not-a-uuid")


# =====================================================================
# Management command — --fail-on-drift
# =====================================================================


def test_command_fail_on_drift_exits_nonzero_when_drift_present() -> None:
    tm, _ = _make_teammate("cmd-fail-drift@t")
    tm.portrait_path = "https://drift/p.png"
    tm.save(update_fields=["portrait_path"])

    with pytest.raises(SystemExit) as ei:
        call_command("verify_identity_mirrors", "--fail-on-drift")
    assert ei.value.code == 1


def test_command_fail_on_drift_exits_zero_when_only_na() -> None:
    _make_teammate("cmd-na-only@t")  # no mirrors, no identity
    # N/A-only — should NOT fail --fail-on-drift.
    buf = io.StringIO()
    call_command("verify_identity_mirrors", "--fail-on-drift", stdout=buf)
    # No SystemExit raised → the command completed with implicit 0.


def test_command_fail_on_drift_exits_zero_on_clean_matches() -> None:
    tm, user = _make_teammate("cmd-clean-pass@t")
    _seed_full_authoring(tm, user)

    buf = io.StringIO()
    call_command("verify_identity_mirrors", "--fail-on-drift", stdout=buf)


# =====================================================================
# Management command is genuinely read-only (behavioral)
# =====================================================================


def test_command_run_does_not_mutate_state() -> None:
    tm_a, _ = _make_teammate("cmd-ro-a@t", name="A")
    tm_b, user_b = _make_teammate("cmd-ro-b@t", name="B")
    _seed_full_authoring(tm_b, user_b)
    tm_a.portrait_path = "https://a/p.png"
    tm_a.save(update_fields=["portrait_path"])

    before = _snapshot_state()
    buf = io.StringIO()
    call_command("verify_identity_mirrors", "--json", stdout=buf)
    after = _snapshot_state()
    assert before == after, (
        "verify_identity_mirrors command mutated state.\n"
        + _describe_diff(before, after)
    )


# =====================================================================
# Helpers
# =====================================================================


def _describe_diff(before: dict, after: dict) -> str:
    lines = []
    for key in set(before.keys()) | set(after.keys()):
        b = before.get(key)
        a = after.get(key)
        if b != a:
            lines.append(f"[{key}]")
            lines.append(f"  before: {b!r}")
            lines.append(f"  after:  {a!r}")
    return "\n".join(lines) if lines else "(unable to describe diff)"
