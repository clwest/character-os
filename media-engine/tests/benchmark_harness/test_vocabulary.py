"""Benchmark harness vocabulary — ratified-schema drift tests.

The vocabulary module's enums are Python-side constants. The
scoring / purpose / background YAML files under
``docs/design/visual/portrait_qualification/schemas/`` (and
``.../scoring/``) are the ratified authority. These tests keep
the two in step: if either side drifts, the tests fail loudly
before the mismatch reaches evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.services.benchmark_harness import (
    BRANCH_TO_KIND,
    BRANCH_TO_PURPOSES,
    HumanPortraitReferencePurpose,
    IdentityBranch,
    NonHumanCanonicalReferencePurpose,
    PROVIDER_MOCK,
    PROVIDER_RUNWAY_STILL_PORTRAIT,
    PROVIDER_STABILITY_STILL,
    RATIFIED_FIXTURES,
    RATIFIED_PROVIDERS,
    RATIFIED_SURFACE_PROFILES,
    ReferenceKind,
    RenderingDirectionHypothesis,
    default_schemas_root,
    kind_for_branch,
    purposes_for_branch,
)


_QUAL_ROOT = default_schemas_root().parent  # portrait_qualification/


def _scoring_schema() -> dict:
    return json.loads(
        (_QUAL_ROOT / "scoring" / "scoring.schema.json").read_text(encoding="utf-8")
    )


def _human_purpose_schema() -> dict:
    return yaml.safe_load(
        (_QUAL_ROOT / "schemas" / "purpose_schema_human_v1.yaml").read_text(
            encoding="utf-8"
        )
    )


def _non_human_test_schema() -> dict:
    return yaml.safe_load(
        (_QUAL_ROOT / "schemas" / "non_human_test_schema_v1.yaml").read_text(
            encoding="utf-8"
        )
    )


# ---- Rendering-direction enum -----------------------------------


def test_rendering_direction_matches_scoring_schema_verbatim() -> None:
    """The six ratified rendering-direction values in
    ``scoring.schema.json`` are the sole authority; the enum
    values must match verbatim, including order.
    """
    schema = _scoring_schema()
    schema_directions = tuple(
        schema["definitions"]["immutable_metadata"]["properties"][
            "direction_hypothesis"
        ]["enum"]
    )
    enum_directions = tuple(d.value for d in RenderingDirectionHypothesis)
    assert schema_directions == enum_directions


# ---- Human portrait-reference purposes --------------------------


def test_human_portrait_reference_purposes_match_purpose_schema() -> None:
    """The seven human portrait_reference purposes must match
    the ratified purpose schema exactly. Adding a purpose is
    additive per the schema's own evolution_rules, but the
    Python enum has to be kept in step."""
    schema = _human_purpose_schema()
    ratified_purposes = tuple(
        p["value"]
        for p in schema["kinds"]["portrait_reference"]["purposes"]
    )
    enum_purposes = tuple(p.value for p in HumanPortraitReferencePurpose)
    assert ratified_purposes == enum_purposes


# ---- Non-human canonical-reference purposes ---------------------


def test_non_human_canonical_reference_purposes_match_test_schema() -> None:
    """The non-canonical test schema's single 'front' purpose
    is mirrored by the enum."""
    schema = _non_human_test_schema()
    ratified_purposes = tuple(
        p["value"]
        for p in schema["kinds"]["canonical_reference"]["purposes"]
    )
    enum_purposes = tuple(p.value for p in NonHumanCanonicalReferencePurpose)
    assert ratified_purposes == enum_purposes


# ---- Branch → kind and purposes maps ----------------------------


def test_branch_to_kind_matches_ratified_pairing() -> None:
    assert BRANCH_TO_KIND[IdentityBranch.HUMAN] == ReferenceKind.PORTRAIT_REFERENCE
    assert BRANCH_TO_KIND[IdentityBranch.NON_HUMAN] == ReferenceKind.CANONICAL_REFERENCE


def test_branch_to_purposes_maps_all_ratified_purposes() -> None:
    assert BRANCH_TO_PURPOSES[IdentityBranch.HUMAN] == tuple(
        p.value for p in HumanPortraitReferencePurpose
    )
    assert BRANCH_TO_PURPOSES[IdentityBranch.NON_HUMAN] == tuple(
        p.value for p in NonHumanCanonicalReferencePurpose
    )


def test_helpers_return_frozen_ratified_values() -> None:
    assert kind_for_branch(IdentityBranch.HUMAN) == ReferenceKind.PORTRAIT_REFERENCE
    assert purposes_for_branch(IdentityBranch.HUMAN)[0] == "front"


# ---- Ratified fixtures + providers + profiles -------------------


def test_ratified_fixtures_match_fixture_directory() -> None:
    """The vocabulary's ``RATIFIED_FIXTURES`` list must match
    the fixture directories on disk exactly. Adding a fixture
    requires the adaptive-expansion gate in
    ``FIXTURE_AUTHORING_GUIDE_V1.md``; this test catches a
    disk-side addition that forgot to update the vocabulary
    (or vice versa)."""
    fixtures_dir = _QUAL_ROOT / "fixtures"
    on_disk = sorted(
        p.name for p in fixtures_dir.iterdir()
        if p.is_dir() and p.name.startswith("fixture_")
    )
    assert tuple(sorted(RATIFIED_FIXTURES)) == tuple(on_disk)


def test_ratified_providers_mirror_portrait_provider_registry() -> None:
    """String values must match ``PortraitProviderName``
    verbatim so evidence written by the harness stamps values
    a Django-side consumer can consume by string equality
    (see the portrait_provider package's ratification note on
    duplicate strings vs shared enum imports)."""
    from app.services.portrait_provider import PortraitProviderName

    ratified = {n.value for n in PortraitProviderName}
    assert set(RATIFIED_PROVIDERS) == ratified
    # And the individual name constants are in the ratified set.
    assert PROVIDER_MOCK in ratified
    assert PROVIDER_STABILITY_STILL in ratified
    assert PROVIDER_RUNWAY_STILL_PORTRAIT in ratified


def test_ratified_surface_profiles_match_yaml_directory() -> None:
    """``RATIFIED_SURFACE_PROFILES`` mirrors the ratified
    profile YAMLs on disk."""
    profiles_dir = default_schemas_root() / "surface_profiles"
    on_disk = sorted(
        p.stem for p in profiles_dir.glob("*.yaml") if p.name != "README.md"
    )
    assert tuple(sorted(RATIFIED_SURFACE_PROFILES)) == tuple(on_disk)
