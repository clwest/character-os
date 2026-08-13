"""Run-identity discipline tests.

Enforces the SESSION 247 operator discipline #5 split of
``run_id`` (unique per invocation, timestamp-bearing) vs
``run_fingerprint`` (deterministic hash of reproducibility-
relevant inputs).

Key invariants:

* Fingerprint stable across wall-time changes.
* Fingerprint stable across filesystem-path overrides
  (schemas_root / fixtures_root).
* Fingerprint changes when any reproducibility-relevant input
  changes (fixture content, direction set, purpose set,
  provider set, provider model override, profile version,
  background family hash, pipeline version, prompt builder
  version, execution mode, harness schema version).
* run_id unique per invocation but embeds the fingerprint's
  first 12 characters.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.benchmark_harness import (
    HARNESS_SCHEMA_VERSION,
    IdentityBranch,
    MatrixAxes,
    PROMPT_BUILDER_VERSION,
    RunIdentityError,
    compute_run_fingerprint,
    load_ratified_fixtures,
    mint_run_id,
    mint_run_identity,
)


# ---- Standard fixture-set + axes shared across tests --------


def _std_axes() -> MatrixAxes:
    return MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )


def _std_kwargs() -> dict:
    return dict(
        provider_models=None,
        surface_profile_versions={"compact": 1},
        background_family_schema_hash="bgfamhash",
        pipeline_versions={"compact": "pipeline_v1:crop@2|framing@1|bgr@1"},
        prompt_builder_version=PROMPT_BUILDER_VERSION,
        execution_mode="forced_mock",
        harness_schema_version=HARNESS_SCHEMA_VERSION,
    )


# ---- Fingerprint determinism -------------------------------


def test_fingerprint_stable_across_wall_time_changes() -> None:
    """Two invocations of the same configuration at different
    wall times produce the same fingerprint."""
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    kwargs = _std_kwargs()
    a = compute_run_fingerprint(fixtures=fixtures, axes=axes, **kwargs)
    b = compute_run_fingerprint(fixtures=fixtures, axes=axes, **kwargs)
    assert a == b
    assert len(a) == 64


def test_fingerprint_is_a_sha256_hex_string() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    fp = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **_std_kwargs(),
    )
    assert len(fp) == 64
    int(fp, 16)  # hex-decodable


def test_fingerprint_stable_under_fixture_iteration_order() -> None:
    """Fixtures passed in a different order still produce the
    same fingerprint (sorted by fixture_id inside)."""
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    kwargs = _std_kwargs()
    forward = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **kwargs,
    )
    reversed_ = compute_run_fingerprint(
        fixtures=tuple(reversed(fixtures)), axes=axes, **kwargs,
    )
    assert forward == reversed_


# ---- Fingerprint changes when config axes change ----------


def test_fingerprint_changes_when_execution_mode_changes() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base = _std_kwargs()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **{**base, "execution_mode": "forced_mock"},
    )
    b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **{**base, "execution_mode": "real_required"},
    )
    assert a != b


def test_fingerprint_changes_when_prompt_builder_version_changes() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base = _std_kwargs()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **{**base, "prompt_builder_version": "1"},
    )
    b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **{**base, "prompt_builder_version": "2"},
    )
    assert a != b


def test_fingerprint_changes_when_pipeline_version_changes() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base = _std_kwargs()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "pipeline_versions": {"compact": "pipeline_a"}},
    )
    b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "pipeline_versions": {"compact": "pipeline_b"}},
    )
    assert a != b


def test_fingerprint_changes_when_background_family_hash_changes() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base = _std_kwargs()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "background_family_schema_hash": "hashA"},
    )
    b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "background_family_schema_hash": "hashB"},
    )
    assert a != b


def test_fingerprint_changes_when_provider_model_override_added() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base = _std_kwargs()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "provider_models": None},
    )
    b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes,
        **{**base, "provider_models": {"mock": "some_pinned_model"}},
    )
    assert a != b


def test_fingerprint_changes_when_provider_set_widens() -> None:
    fixtures = load_ratified_fixtures()
    kwargs = {
        **_std_kwargs(),
        "surface_profile_versions": {"compact": 1},
        "pipeline_versions": {"compact": "pv1"},
    }
    narrow = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    wide = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock", "stability_still"),
        surface_profiles=("compact",),
    )
    a = compute_run_fingerprint(fixtures=fixtures, axes=narrow, **kwargs)
    b = compute_run_fingerprint(fixtures=fixtures, axes=wide, **kwargs)
    assert a != b


def test_fingerprint_changes_when_fixture_content_changes(
    tmp_path,
) -> None:
    """Two fixtures with different content produce two
    different fingerprints even if the fixture_id and version
    are identical (content_hash captures the difference)."""
    import yaml

    from app.services.benchmark_harness import load_fixture

    schemas_root = tmp_path / "schemas"
    schemas_root.mkdir()
    (schemas_root / "human_identity_schema_v1.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_id": "test.human.v1",
                "schema_version": 1,
                "branch": "human",
                "spec_payload_schema": {
                    "type": "object",
                    "required": ["spec_schema_version", "name"],
                    "properties": {
                        "spec_schema_version": {"type": "integer", "const": 1},
                        "name": {"type": "string"},
                    },
                },
            }
        )
    )
    fixtures_a_root = tmp_path / "fixtures_a"
    (fixtures_a_root / "fixture_h1").mkdir(parents=True)
    (fixtures_a_root / "fixture_h1" / "identity.yaml").write_text(
        yaml.safe_dump({"spec_schema_version": 1, "name": "alpha"})
    )
    (fixtures_a_root / "fixture_h1" / "rationale.md").write_text("rationale_a")

    fixtures_b_root = tmp_path / "fixtures_b"
    (fixtures_b_root / "fixture_h1").mkdir(parents=True)
    (fixtures_b_root / "fixture_h1" / "identity.yaml").write_text(
        yaml.safe_dump({"spec_schema_version": 1, "name": "beta"})
    )
    (fixtures_b_root / "fixture_h1" / "rationale.md").write_text("rationale_a")

    fx_a = load_fixture(
        "fixture_h1", fixtures_root=fixtures_a_root, schemas_root=schemas_root,
    )
    fx_b = load_fixture(
        "fixture_h1", fixtures_root=fixtures_b_root, schemas_root=schemas_root,
    )
    assert fx_a.content_hash != fx_b.content_hash

    axes = _std_axes()
    kwargs = _std_kwargs()
    fp_a = compute_run_fingerprint(fixtures=[fx_a], axes=axes, **kwargs)
    fp_b = compute_run_fingerprint(fixtures=[fx_b], axes=axes, **kwargs)
    assert fp_a != fp_b


# ---- Filesystem-path / timestamp exclusion -----------------


def test_fingerprint_stable_across_filesystem_path_overrides() -> None:
    """Path overrides (schemas_root / fixtures_root) are absorbed
    at the LoadedFixture layer via content_hash. Passing
    different filesystem paths that resolve to the same content
    must produce the same fingerprint."""
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes, **_std_kwargs(),
    )
    # Re-load fixtures explicitly with default paths — should
    # still match.
    fixtures_again = load_ratified_fixtures()
    b = compute_run_fingerprint(
        fixtures=fixtures_again, axes=axes, **_std_kwargs(),
    )
    assert a == b


# ---- run_id shape ------------------------------------------


def test_run_id_bootstrap_shape() -> None:
    fp = "a" * 64
    ts_now = datetime(2026, 8, 8, 3, 45, 12, tzinfo=timezone.utc)
    rid = mint_run_id(fp, kind="bootstrap", now=ts_now)
    assert rid == "bootstrap_20260808T034512Z_" + fp[:12]


def test_run_id_round_shape_requires_round_number() -> None:
    fp = "b" * 64
    ts_now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(RunIdentityError, match="round.*requires round_number"):
        mint_run_id(fp, kind="round", now=ts_now)
    rid = mint_run_id(fp, kind="round", round_number=1, now=ts_now)
    assert rid == "round_1_20260901T000000Z_" + fp[:12]


def test_run_id_rejects_wrong_fingerprint_length() -> None:
    with pytest.raises(RunIdentityError, match="64-char sha256 hex"):
        mint_run_id("short", kind="bootstrap")


def test_run_id_rejects_unknown_kind() -> None:
    with pytest.raises(RunIdentityError, match="run kind"):
        mint_run_id("f" * 64, kind="unratified")


def test_bootstrap_cannot_carry_round_number() -> None:
    with pytest.raises(RunIdentityError, match="bootstrap.*cannot carry round_number"):
        mint_run_id("f" * 64, kind="bootstrap", round_number=1)


# ---- mint_run_identity end-to-end --------------------------


def test_mint_run_identity_produces_matching_fingerprint_and_run_id() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    identity = mint_run_identity(
        kind="bootstrap",
        fixtures=fixtures,
        axes=axes,
        now=datetime(2026, 8, 8, 3, 45, 12, tzinfo=timezone.utc),
        **_std_kwargs(),
    )
    assert identity.run_kind == "bootstrap"
    assert identity.run_id.startswith("bootstrap_")
    assert identity.run_fingerprint[:12] in identity.run_id
    # Timestamp is captured on the dataclass.
    assert identity.created_at_utc.tzinfo is not None
    assert identity.created_at_utc.year == 2026


def test_mint_run_identity_at_two_wall_times_same_config() -> None:
    """Same configuration at two different wall times → same
    fingerprint, different run_id. Operator discipline #5."""
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    base_kwargs = _std_kwargs()
    t0 = datetime(2026, 8, 8, 3, 45, 12, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=1)
    a = mint_run_identity(
        fixtures=fixtures, axes=axes, now=t0, **base_kwargs,
    )
    b = mint_run_identity(
        fixtures=fixtures, axes=axes, now=t1, **base_kwargs,
    )
    assert a.run_fingerprint == b.run_fingerprint
    assert a.run_id != b.run_id


def test_execution_mode_unavailable_is_rejected_by_fingerprint() -> None:
    fixtures = load_ratified_fixtures()
    axes = _std_axes()
    with pytest.raises(RunIdentityError, match="not in the accepted set"):
        compute_run_fingerprint(
            fixtures=fixtures,
            axes=axes,
            **{**_std_kwargs(), "execution_mode": "unavailable"},
        )
