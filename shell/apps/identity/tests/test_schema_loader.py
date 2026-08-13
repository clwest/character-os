"""Branch-schema loader tests (2.d slice).

Verifies that the ratified YAML schemas load cleanly and expose
the declarative structure the write-path service consumes. The
loader does not flatten the schema into strings-only helpers per
Correction 5 (SESSION 241 gate) — callers work with the authored
declarative shape (``required_for_identity``,
``surface_requirements``, kind-scoped purpose maps).
"""
from __future__ import annotations

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError

from apps.identity.schema_loader import (
    BranchSchemaNotFound,
    _reset_cache_for_tests,
    get_branch_schema,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    _reset_cache_for_tests()
    yield
    _reset_cache_for_tests()


def _valid_human_spec() -> dict:
    return {
        "spec_schema_version": 1,
        "age_presentation": {"min_years": 30, "max_years": 45},
        "skin_tone": {"descriptor": "medium olive", "undertone": "olive"},
        "hair": {"length": "medium", "texture": "wavy", "color": "dark brown"},
        "eye": {"color": "hazel", "shape": "almond"},
        "face_shape": {"descriptor": "oval"},
        "gender_presentation": {"descriptor": "feminine", "primary_axis": "feminine"},
        "canonical_outfit": {
            "descriptor": "cream linen blazer over a navy tee",
            "formality": "smart_casual",
            "material_family": "linen",
        },
    }


def test_get_branch_schema_human_shape() -> None:
    schema = get_branch_schema("human")
    assert schema.kind == "human"
    assert schema.schema_version == 1
    assert "spec_payload_schema" in schema.__dict__ or hasattr(schema, "spec_payload_schema")
    # Declarative approval floor comes through as authored — the
    # loader does not lower it to a Python-side flat list of a
    # different shape.
    assert "portrait_reference/front" in schema.required_for_identity
    assert "portrait_reference/neutral_rest" in schema.required_for_identity


def test_get_branch_schema_human_surface_requirements_declarative() -> None:
    schema = get_branch_schema("human")
    # Surfaces preserved as authored in the YAML.
    assert "Home" in schema.surface_requirements
    assert "Presence" in schema.surface_requirements
    assert "Live_Conversation" in schema.surface_requirements
    # Each surface's requirement list is the authored list of
    # ``<kind>/<purpose>`` strings — no transformation.
    assert schema.surface_requirements["Home"] == ["portrait_reference/front"]


def test_get_branch_schema_human_purpose_kinds_declarative() -> None:
    schema = get_branch_schema("human")
    portrait_purposes = schema.purpose_kinds.get("portrait_reference", [])
    # All seven round-one purposes must be enumerated.
    for expected in (
        "front",
        "slight_left",
        "slight_right",
        "neutral_rest",
        "listening",
        "consideration",
        "gentle_positive",
    ):
        assert expected in portrait_purposes


def test_human_schema_validates_a_conforming_spec() -> None:
    schema = get_branch_schema("human")
    # Must not raise.
    schema.validate_spec(_valid_human_spec())


def test_human_schema_rejects_missing_required_field() -> None:
    schema = get_branch_schema("human")
    spec = _valid_human_spec()
    del spec["hair"]
    with pytest.raises(JsonSchemaValidationError):
        schema.validate_spec(spec)


def test_human_schema_rejects_wrong_enum_value() -> None:
    schema = get_branch_schema("human")
    spec = _valid_human_spec()
    spec["hair"]["length"] = "not-a-real-length"
    with pytest.raises(JsonSchemaValidationError):
        schema.validate_spec(spec)


def test_human_schema_rejects_additional_properties() -> None:
    schema = get_branch_schema("human")
    spec = _valid_human_spec()
    spec["provider_id"] = "runway_avatar_xyz"  # explicitly forbidden per §17.3.a
    with pytest.raises(JsonSchemaValidationError):
        schema.validate_spec(spec)


def test_validate_purpose_accepts_known_value() -> None:
    schema = get_branch_schema("human")
    assert schema.validate_purpose("portrait_reference", "front") is True
    assert schema.validate_purpose("portrait_reference", "neutral_rest") is True


def test_validate_purpose_rejects_unknown_value() -> None:
    schema = get_branch_schema("human")
    assert schema.validate_purpose("portrait_reference", "some_new_value") is False
    assert schema.validate_purpose("portrait_reference", "") is False


def test_non_human_schema_loads_and_is_non_canonical() -> None:
    """§17.2.a — non-human schema is non-canonical and exists
    solely to exercise substrate branch-neutrality. It still
    loads through the same loader (same runtime contract).
    """
    schema = get_branch_schema("non_human")
    assert schema.kind == "non_human"
    assert schema.spec_payload_schema is not None
    assert isinstance(schema.required_for_identity, list)


def test_unknown_branch_raises() -> None:
    with pytest.raises(BranchSchemaNotFound):
        get_branch_schema("robot")
