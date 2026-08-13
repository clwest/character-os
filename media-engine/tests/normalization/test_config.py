"""Tests for the normalization config loaders (pre-7.a).

Coverage:

* All five ratified surface profiles parse cleanly against the
  live ``docs/design/visual/portrait_qualification/schemas/``
  YAMLs — the loader is not tested against synthetic fixtures
  alone. If a ratification edit invalidates one of these, the
  loader test surfaces it before any pipeline slice consumes
  the config.
* Background family parses cleanly with the ratified five
  backgrounds + the tonal_environment_class default map.
* ``schema_hash`` is deterministic (identical bytes → identical
  digest) and content-sensitive (byte diff → digest diff). The
  pipeline versioning downstream leans on this.
* Loaders raise loudly on unknown ids, malformed YAML shapes,
  and inconsistent id references. Silent fallback is refused.
* ``resolve_background_for_profile`` walks the declarative
  mapping without hardcoded knowledge of specific backgrounds.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.normalization import (
    Background,
    BackgroundFamily,
    InvalidBackgroundFamilyError,
    InvalidSurfaceProfileError,
    SurfaceProfile,
    UnknownBackgroundIdError,
    UnknownSurfaceProfileError,
    default_backgrounds_path,
    default_surface_profiles_dir,
    get_background,
    load_background_family,
    load_surface_profile,
    resolve_background_for_profile,
    stable_yaml_hash,
)


# ---- Ratified-YAML load-through ---------------------------------


RATIFIED_PROFILE_IDS = ("compact", "presence", "studio", "conversation", "team_card")


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_ratified_surface_profile_loads(profile_id: str) -> None:
    profile = load_surface_profile(profile_id)
    assert isinstance(profile, SurfaceProfile)
    assert profile.profile_id == profile_id
    assert profile.version >= 1
    assert profile.crop.subject_scale > 0
    assert profile.output.width_px > 0
    assert profile.output.height_px > 0
    assert profile.output.format == "png"
    assert 0.0 < profile.eye_line.position_from_top < 1.0
    assert 0.0 < profile.eye_line.position_from_left < 1.0
    assert profile.margins.min_edge_padding >= 0.0
    assert len(profile.schema_hash) == 64  # sha256 hex


def test_ratified_background_family_loads() -> None:
    family = load_background_family()
    assert isinstance(family, BackgroundFamily)
    assert family.schema_version >= 1
    assert len(family.backgrounds) >= 1
    ids = {b.background_id for b in family.backgrounds}
    # Default must reference a known background — loader enforces
    # this; assertion here is a redundant safety net that would
    # catch a future silent regression.
    assert family.default_background_for_unspecified_profile in ids
    for tec, bg_id in family.tonal_environment_class_default_background.items():
        assert isinstance(tec, str) and tec
        assert bg_id in ids
    assert len(family.schema_hash) == 64


def test_ratified_backgrounds_all_carry_procedural_v1_block() -> None:
    """Every ratified background must expose a ``procedural_v1``
    block per SESSION 246 7.c.a — Step 7's
    BackgroundReplacementStage renders from these values, so the
    loader guarantees they exist. Values are traceable to the
    YAML; Python never invents them.
    """
    family = load_background_family()
    for bg in family.backgrounds:
        assert bg.procedural_v1 is not None
        r, g, b = bg.procedural_v1.fill_rgb
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255
        # Status + purpose exist explicitly so future code cannot
        # mistake these for final aesthetic values.
        assert bg.procedural_v1.status
        assert bg.procedural_v1.purpose


def test_ratified_procedural_v1_matches_operator_ratified_table() -> None:
    """Pin the exact RGB values the operator ratified in SESSION
    246 7.c approval. If a future edit accidentally shifts one of
    these, the test surfaces it before the pipeline silently
    starts rendering a different color.
    """
    family = load_background_family()
    expected: dict[str, tuple[int, int, int]] = {
        "neutral_warm_studio": (214, 205, 194),
        "neutral_cool_studio": (198, 205, 214),
        "warm_material_surround": (204, 190, 172),
        "soft_environmental_depth": (210, 200, 186),
        "conversational_darker_surround": (62, 56, 50),
    }
    got = {bg.background_id: bg.procedural_v1.fill_rgb for bg in family.backgrounds}
    assert got == expected


def test_procedural_v1_missing_block_raises(tmp_path: Path) -> None:
    """The loader must require the ``procedural_v1`` block —
    silent absence would leave the BackgroundReplacementStage
    with no fill to render.
    """
    p = tmp_path / "no_procedural.yaml"
    p.write_text(
        "schema_id: t\nschema_version: 1\nbackgrounds:\n"
        "  - background_id: a\n"
        "    description: d\n"
        "    tonal_direction: warm_neutral\n"
        "    luminance_class: mid\n"
        "    grain: subtle_soft\n"
        "    round_one_role: r\n"
        "tonal_environment_class_default_background: {}\n"
        "default_background_for_unspecified_profile: a\n"
    )
    with pytest.raises(InvalidBackgroundFamilyError, match="procedural_v1"):
        load_background_family(path=p)


@pytest.mark.parametrize(
    "bad_rgb,match",
    [
        ("[300, 128, 128]", "outside"),
        ("[-1, 128, 128]", "outside"),
        ("[128, 128]", "expected 3"),
        ("[128, 128, 128, 128]", "expected 3"),
        ("[128, true, 128]", "bool"),
        ("[128, \"a\", 128]", "expected int"),
    ],
)
def test_procedural_v1_invalid_fill_rgb_raises(
    tmp_path: Path, bad_rgb: str, match: str
) -> None:
    p = tmp_path / f"bad_rgb.yaml"
    p.write_text(
        "schema_id: t\nschema_version: 1\nbackgrounds:\n"
        "  - background_id: a\n"
        "    description: d\n"
        "    tonal_direction: warm_neutral\n"
        "    luminance_class: mid\n"
        "    grain: subtle_soft\n"
        "    round_one_role: r\n"
        "    procedural_v1:\n"
        f"      fill_rgb: {bad_rgb}\n"
        "      status: implementation_provisional\n"
        "      purpose: round_one_normalization_only\n"
        "tonal_environment_class_default_background: {}\n"
        "default_background_for_unspecified_profile: a\n"
    )
    with pytest.raises(InvalidBackgroundFamilyError, match=match):
        load_background_family(path=p)


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_resolve_background_for_every_ratified_profile(profile_id: str) -> None:
    profile = load_surface_profile(profile_id)
    family = load_background_family()
    bg = resolve_background_for_profile(family, profile)
    assert isinstance(bg, Background)
    # Every profile resolves to a background the family owns.
    assert bg.background_id in {b.background_id for b in family.backgrounds}


# ---- Determinism / hashing --------------------------------------


def test_stable_yaml_hash_is_deterministic() -> None:
    payload = b"crop:\n  aspect_ratio: '1:1'\n"
    assert stable_yaml_hash(payload) == stable_yaml_hash(payload)


def test_stable_yaml_hash_bytes_and_str_agree() -> None:
    text = "profile_id: presence\n"
    assert stable_yaml_hash(text) == stable_yaml_hash(text.encode("utf-8"))


def test_stable_yaml_hash_detects_byte_drift() -> None:
    a = b"version: 1\n"
    b = b"version: 2\n"
    assert stable_yaml_hash(a) != stable_yaml_hash(b)


def test_load_surface_profile_is_pure_function_of_yaml_bytes(
    tmp_path: Path,
) -> None:
    """Two loads of the same on-disk file return equal dataclasses
    with identical schema_hash — no timestamps or environmental
    inputs leak into the config.
    """
    yaml_path = tmp_path / "tinyprofile.yaml"
    yaml_path.write_text(_MINIMAL_PROFILE_YAML.format(profile_id="tinyprofile"))
    a = load_surface_profile("tinyprofile", schemas_root=tmp_path)
    b = load_surface_profile("tinyprofile", schemas_root=tmp_path)
    assert a == b
    assert a.schema_hash == b.schema_hash


def test_ratified_profile_schema_hashes_are_pairwise_distinct() -> None:
    """No two ratified profiles have identical schema_hash — proves
    the hash is content-sensitive across real files, not the same
    "hash of empty" for every profile.
    """
    hashes = {
        pid: load_surface_profile(pid).schema_hash for pid in RATIFIED_PROFILE_IDS
    }
    assert len(set(hashes.values())) == len(RATIFIED_PROFILE_IDS), hashes


# ---- Failure paths ----------------------------------------------


def test_unknown_profile_id_raises(tmp_path: Path) -> None:
    with pytest.raises(UnknownSurfaceProfileError):
        load_surface_profile("does_not_exist", schemas_root=tmp_path)


def test_empty_profile_id_raises() -> None:
    with pytest.raises(UnknownSurfaceProfileError):
        load_surface_profile("")


def test_profile_id_mismatch_between_arg_and_file_raises(tmp_path: Path) -> None:
    """A YAML whose in-file profile_id differs from the requested
    identifier must raise. Silent acceptance would let a caller
    ask for ``compact`` and receive whatever another file
    contains, breaking manifest provenance.
    """
    yaml_path = tmp_path / "arg_id.yaml"
    yaml_path.write_text(
        _MINIMAL_PROFILE_YAML.format(profile_id="different_in_file")
    )
    with pytest.raises(InvalidSurfaceProfileError):
        load_surface_profile("arg_id", schemas_root=tmp_path)


def test_missing_required_profile_key_raises(tmp_path: Path) -> None:
    yaml_path = tmp_path / "broken.yaml"
    yaml_path.write_text("profile_id: broken\nversion: 1\n")  # missing framing_family and everything else
    with pytest.raises(InvalidSurfaceProfileError):
        load_surface_profile("broken", schemas_root=tmp_path)


def test_unknown_profile_top_level_key_raises(tmp_path: Path) -> None:
    """A YAML that adds a top-level field the loader doesn't know
    about is rejected — typos never silently discard content.
    """
    yaml_path = tmp_path / "extra.yaml"
    yaml_path.write_text(
        _MINIMAL_PROFILE_YAML.format(profile_id="extra")
        + "unexpected_field: sneaky\n"
    )
    with pytest.raises(InvalidSurfaceProfileError, match="unknown top-level key"):
        load_surface_profile("extra", schemas_root=tmp_path)


def test_wrong_type_in_profile_raises(tmp_path: Path) -> None:
    yaml_path = tmp_path / "wrongtype.yaml"
    yaml_path.write_text(
        "profile_id: wrongtype\n"
        "version: not_an_int\n"
        "framing_family: fam\n"
        "crop:\n  aspect_ratio: '1:1'\n  strategy: subject_relative\n  subject_scale: 1.0\n"
        "eye_line:\n  position_from_top: 0.5\n  position_from_left: 0.5\n"
        "margins:\n  min_edge_padding: 0.05\n"
        "output:\n  width_px: 512\n  height_px: 512\n  format: png\n  color_space: sRGB\n"
        "framing_behavior:\n  includes: [face]\n  excludes: []\n"
    )
    with pytest.raises(InvalidSurfaceProfileError, match="version"):
        load_surface_profile("wrongtype", schemas_root=tmp_path)


def test_background_family_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(InvalidBackgroundFamilyError):
        load_background_family(path=tmp_path / "nope.yaml")


def test_background_family_default_pointing_at_unknown_id_raises(
    tmp_path: Path,
) -> None:
    """Refuse a family whose default points at an id not in the
    ``backgrounds`` list — the loader enforces referential
    consistency before pipeline code ever consumes the config.
    """
    p = tmp_path / "broken_family.yaml"
    p.write_text(_MIN_FAMILY_YAML_HEAD + (
        "  - background_id: a\n"
        "    description: d\n"
        "    tonal_direction: t\n"
        "    luminance_class: mid\n"
        "    grain: subtle_soft\n"
        "    round_one_role: r\n"
        + _PROCEDURAL_V1_BLOCK +
        "tonal_environment_class_default_background: {}\n"
        "default_background_for_unspecified_profile: not_a_real_id\n"
    ))
    with pytest.raises(InvalidBackgroundFamilyError, match="default_background_for_unspecified_profile"):
        load_background_family(path=p)


def test_background_family_tec_map_pointing_at_unknown_id_raises(
    tmp_path: Path,
) -> None:
    p = tmp_path / "broken_tec.yaml"
    p.write_text(_MIN_FAMILY_YAML_HEAD + (
        "  - background_id: a\n"
        "    description: d\n"
        "    tonal_direction: t\n"
        "    luminance_class: mid\n"
        "    grain: subtle_soft\n"
        "    round_one_role: r\n"
        + _PROCEDURAL_V1_BLOCK +
        "tonal_environment_class_default_background:\n"
        "  class_x: not_a_real_id\n"
        "default_background_for_unspecified_profile: a\n"
    ))
    with pytest.raises(InvalidBackgroundFamilyError, match="tonal_environment_class"):
        load_background_family(path=p)


def test_duplicate_background_id_in_family_raises(tmp_path: Path) -> None:
    p = tmp_path / "dup_family.yaml"
    p.write_text(_MIN_FAMILY_YAML_HEAD + (
        "  - background_id: a\n"
        "    description: d\n"
        "    tonal_direction: t\n"
        "    luminance_class: mid\n"
        "    grain: g\n"
        "    round_one_role: r\n"
        + _PROCEDURAL_V1_BLOCK +
        "  - background_id: a\n"
        "    description: d2\n"
        "    tonal_direction: t\n"
        "    luminance_class: mid\n"
        "    grain: g\n"
        "    round_one_role: r\n"
        + _PROCEDURAL_V1_BLOCK +
        "tonal_environment_class_default_background: {}\n"
        "default_background_for_unspecified_profile: a\n"
    ))
    with pytest.raises(InvalidBackgroundFamilyError, match="duplicate"):
        load_background_family(path=p)


# ---- Reusable minimal family YAML fragments ---------------------

_MIN_FAMILY_YAML_HEAD = "schema_id: t\nschema_version: 1\nbackgrounds:\n"

_PROCEDURAL_V1_BLOCK = (
    "    procedural_v1:\n"
    "      fill_rgb: [128, 128, 128]\n"
    "      status: implementation_provisional\n"
    "      purpose: round_one_normalization_only\n"
)


def test_get_background_unknown_id_raises() -> None:
    family = load_background_family()
    with pytest.raises(UnknownBackgroundIdError):
        get_background(family, "definitely_not_a_real_background")


def test_resolve_background_unknown_tec_raises(tmp_path: Path) -> None:
    """A profile that declares a tonal_environment_class not in
    the family's map is a schema-drift bug. Never silently fall
    back to the unspecified-profile default — that would let
    profile edits and family edits drift apart unnoticed.
    """
    profile_yaml = tmp_path / "orphan_tec.yaml"
    profile_yaml.write_text(
        _MINIMAL_PROFILE_YAML.format(profile_id="orphan_tec").rstrip()
        + "\ntonal_environment_class: never_declared\n"
    )
    profile = load_surface_profile("orphan_tec", schemas_root=tmp_path)
    family = load_background_family()
    with pytest.raises(UnknownBackgroundIdError, match="never_declared"):
        resolve_background_for_profile(family, profile)


# ---- Immutability + monorepo boundary ---------------------------


def test_background_family_tec_map_is_read_only() -> None:
    """The loaded background family cannot be mutated in place —
    downstream stages receive an immutable Mapping. Prevents an
    accidental pipeline-time mutation from silently changing
    manifest evidence.
    """
    family = load_background_family()
    with pytest.raises(TypeError):
        family.tonal_environment_class_default_background["x"] = "y"  # type: ignore[index]


def test_default_paths_resolve_to_expected_locations() -> None:
    """The default resolvers point at the ratified schemas
    directory relative to the repo root — proves the four-parents
    walk in ``_repo_root`` still lands on the right file after
    any monorepo restructure.
    """
    assert default_backgrounds_path().is_file()
    surface_dir = default_surface_profiles_dir()
    assert surface_dir.is_dir()
    for pid in RATIFIED_PROFILE_IDS:
        assert (surface_dir / f"{pid}.yaml").is_file()


def test_normalization_package_does_not_import_django() -> None:
    """Media-engine is a peer of the Django shell — monorepo
    convention forbids cross-service imports. If the normalization
    package ever grows an accidental Django import, this test
    catches it at CI time.
    """
    import ast
    import pathlib

    pkg_root = pathlib.Path(__file__).resolve().parents[2] / "app" / "services" / "normalization"
    forbidden_prefixes = ("django", "shell.", "apps.identity")
    offenders: list[tuple[str, str]] = []
    for py in pkg_root.rglob("*.py"):
        tree = ast.parse(py.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in forbidden_prefixes):
                        offenders.append((str(py), alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(mod.startswith(p) for p in forbidden_prefixes):
                    offenders.append((str(py), mod))
    assert offenders == [], f"cross-service imports detected: {offenders}"


# ---- Fixtures ---------------------------------------------------


_MINIMAL_PROFILE_YAML = """\
profile_id: {profile_id}
version: 1
framing_family: fam
crop:
  aspect_ratio: '1:1'
  strategy: subject_relative
  subject_scale: 1.0
eye_line:
  position_from_top: 0.5
  position_from_left: 0.5
margins:
  min_edge_padding: 0.05
output:
  width_px: 512
  height_px: 512
  format: png
  color_space: sRGB
framing_behavior:
  includes:
    - face
  excludes: []
"""
