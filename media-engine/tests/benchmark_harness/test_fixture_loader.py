"""Fixture-loader coverage.

The loader validates ratified fixture payloads against the
branch schema, computes an immutable content hash, and refuses
to load fixtures whose schema version disagrees with the ratified
branch schema. These tests exercise the happy path plus the
common misuse cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.services.benchmark_harness import (
    FixtureNotFoundError,
    FixtureSchemaError,
    IdentityBranch,
    RATIFIED_FIXTURES,
    load_branch_schema,
    load_fixture,
    load_ratified_fixtures,
)


# ---- Happy path -----------------------------------------------


def test_load_ratified_fixtures_returns_all_five_in_authoring_order() -> None:
    fixtures = load_ratified_fixtures()
    assert tuple(f.fixture_id for f in fixtures) == RATIFIED_FIXTURES


def test_every_ratified_fixture_validates_against_its_branch_schema() -> None:
    """The load itself is validation — if any fixture fails
    JSON Schema, this test fails."""
    fixtures = load_ratified_fixtures()
    assert len(fixtures) == 5


def test_branch_inference_matches_directory_prefix() -> None:
    fixtures = {f.fixture_id: f for f in load_ratified_fixtures()}
    for hid in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"):
        assert fixtures[hid].branch == IdentityBranch.HUMAN
    assert fixtures["fixture_nh1"].branch == IdentityBranch.NON_HUMAN


# ---- Content hash discipline ----------------------------------


def test_content_hash_stable_across_repeat_loads() -> None:
    """Loading the same fixture twice from unchanged disk must
    produce the same content_hash. Load-bearing for the run
    fingerprint's reproducibility."""
    fx_a = load_fixture("fixture_h1")
    fx_b = load_fixture("fixture_h1")
    assert fx_a.content_hash == fx_b.content_hash
    assert len(fx_a.content_hash) == 64  # sha256 hex


def test_content_hash_differs_across_different_fixtures() -> None:
    fixtures = load_ratified_fixtures()
    hashes = {f.fixture_id: f.content_hash for f in fixtures}
    assert len(set(hashes.values())) == len(fixtures)


# ---- Failure cases via temp-dir overrides ---------------------


def _write_min_human_schema(schemas_root: Path) -> None:
    """Write a minimal valid human_identity_schema_v1.yaml under
    ``schemas_root``. Used by tests that want to override the
    ratified schemas without touching the repo."""
    schemas_root.mkdir(parents=True, exist_ok=True)
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


def test_missing_fixture_directory_raises_not_found(tmp_path: Path) -> None:
    with pytest.raises(FixtureNotFoundError, match="fixture directory not found"):
        load_fixture("fixture_h_never_authored", fixtures_root=tmp_path)


def test_missing_identity_yaml_raises_not_found(tmp_path: Path) -> None:
    (tmp_path / "fixture_h9").mkdir()
    (tmp_path / "fixture_h9" / "rationale.md").write_text("stub")
    with pytest.raises(FixtureNotFoundError, match="identity.yaml missing"):
        load_fixture("fixture_h9", fixtures_root=tmp_path)


def test_missing_rationale_md_raises_not_found(tmp_path: Path) -> None:
    (tmp_path / "fixture_h9").mkdir()
    (tmp_path / "fixture_h9" / "identity.yaml").write_text("spec_schema_version: 1\n")
    with pytest.raises(FixtureNotFoundError, match="rationale.md missing"):
        load_fixture("fixture_h9", fixtures_root=tmp_path)


def test_unknown_branch_prefix_raises_schema_error(tmp_path: Path) -> None:
    (tmp_path / "fixture_x1").mkdir()
    (tmp_path / "fixture_x1" / "identity.yaml").write_text("spec_schema_version: 1\n")
    (tmp_path / "fixture_x1" / "rationale.md").write_text("stub")
    with pytest.raises(FixtureSchemaError, match="unrecognized branch prefix"):
        load_fixture("fixture_x1", fixtures_root=tmp_path)


def test_fixture_id_without_fixture_prefix_raises_schema_error(tmp_path: Path) -> None:
    (tmp_path / "randomdir").mkdir()
    (tmp_path / "randomdir" / "identity.yaml").write_text("spec_schema_version: 1\n")
    (tmp_path / "randomdir" / "rationale.md").write_text("stub")
    with pytest.raises(FixtureSchemaError, match="must start with 'fixture_'"):
        load_fixture("randomdir", fixtures_root=tmp_path)


def test_spec_schema_version_mismatch_raises_schema_error(
    tmp_path: Path,
) -> None:
    """A fixture whose ``spec_schema_version`` disagrees with its
    branch schema's ``schema_version`` must be rejected — never
    silently reinterpreted."""
    schemas_root = tmp_path / "schemas"
    _write_min_human_schema(schemas_root)
    fixtures_root = tmp_path / "fixtures"
    (fixtures_root / "fixture_h1").mkdir(parents=True)
    (fixtures_root / "fixture_h1" / "identity.yaml").write_text(
        yaml.safe_dump({"spec_schema_version": 99, "name": "test"})
    )
    (fixtures_root / "fixture_h1" / "rationale.md").write_text("stub")
    # The version mismatch is detected AFTER JSON Schema validates
    # the payload against the (permissive) test schema — so first
    # the payload passes minimum schema checks, then the version
    # cross-check fires. Match the version-mismatch message.
    with pytest.raises(FixtureSchemaError, match="spec_schema_version"):
        load_fixture(
            "fixture_h1",
            fixtures_root=fixtures_root,
            schemas_root=schemas_root,
        )


def test_missing_required_top_level_field_raises_schema_error(
    tmp_path: Path,
) -> None:
    """Payload missing a required top-level field (e.g.
    ``age_presentation`` for human) must be rejected by the
    JSON Schema validator."""
    schemas_root = tmp_path / "schemas"
    _write_min_human_schema(schemas_root)
    fixtures_root = tmp_path / "fixtures"
    (fixtures_root / "fixture_h1").mkdir(parents=True)
    # Missing 'name' — required by the minimal test schema.
    (fixtures_root / "fixture_h1" / "identity.yaml").write_text(
        yaml.safe_dump({"spec_schema_version": 1})
    )
    (fixtures_root / "fixture_h1" / "rationale.md").write_text("stub")
    with pytest.raises(FixtureSchemaError, match="schema validation"):
        load_fixture(
            "fixture_h1",
            fixtures_root=fixtures_root,
            schemas_root=schemas_root,
        )


# ---- Branch-schema loader --------------------------------------


def test_load_branch_schema_carries_stable_hash() -> None:
    a = load_branch_schema(IdentityBranch.HUMAN)
    b = load_branch_schema(IdentityBranch.HUMAN)
    assert a.schema_hash == b.schema_hash
    assert a.schema_version == 1
    assert a.branch == IdentityBranch.HUMAN


def test_load_branch_schema_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FixtureNotFoundError, match="branch schema not found"):
        load_branch_schema(IdentityBranch.HUMAN, schemas_root=tmp_path)


def test_branch_schema_declared_branch_must_match_requested(
    tmp_path: Path,
) -> None:
    """A schema whose ``branch:`` field disagrees with the
    branch the loader was asked for must be rejected — this
    guards against a rename that forgets to fix the file
    header."""
    schemas_root = tmp_path / "schemas"
    schemas_root.mkdir()
    (schemas_root / "human_identity_schema_v1.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_id": "test",
                "schema_version": 1,
                "branch": "non_human",
                "spec_payload_schema": {"type": "object"},
            }
        )
    )
    with pytest.raises(FixtureSchemaError, match="declares branch"):
        load_branch_schema(IdentityBranch.HUMAN, schemas_root=schemas_root)
