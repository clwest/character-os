"""Declarative configuration for the normalization pipeline.

Loads the ratified surface-profile and background-family YAMLs
from ``docs/design/visual/portrait_qualification/schemas/`` into
frozen dataclasses, computes stable SHA-256 hashes over the
YAML file contents (so downstream pipeline versioning can
detect schema drift), and offers the two accessors the pipeline
consumes at run time — ``load_surface_profile(profile_id)`` and
``load_background_family()``.

Design lock references:

* §10.8 — "surface profiles are data, not code"; live under
  ``schemas/`` alongside the identity branch schema.
* §17.5.b — declarative discipline for approval floor +
  surface requirements; extended by §17.6.a to surface
  profiles themselves.
* §17.6.a — normalization scope (crop + framing + eye-line +
  background), manifest requirement, determinism constraint,
  stage architecture, surface-profile-as-data.
* ``schemas/background_family_v1.yaml`` — the ratified round-
  one background set; the ``assets_authored_separately`` rule
  in that file explicitly defers real background asset
  authoring, which is why round-one background replacement
  uses procedural fills (Step 7.c) rather than PNG assets.

Boundary discipline:

* This module owns YAML → dataclass parsing and stable
  hashing. It does not touch pixel bytes; that is
  ``stages/`` (7.a onward).
* No Django imports (media-engine is a peer service; the
  monorepo boundary is enforced in CLAUDE.md).
* Loaders accept an optional ``schemas_root`` path so tests
  can point at fixture directories without touching the
  ratified files on disk.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml


# ---- Errors -----------------------------------------------------


class NormalizationConfigError(Exception):
    """Base for configuration-load errors."""


class UnknownSurfaceProfileError(NormalizationConfigError):
    """``load_surface_profile`` was called with a profile_id that
    does not resolve to a YAML file under the surface-profiles
    directory. Raised loudly rather than falling back — the
    caller must not silently substitute a default surface.
    """


class InvalidSurfaceProfileError(NormalizationConfigError):
    """The YAML at the resolved path parsed but did not conform
    to the ratified surface-profile shape (missing required
    key, unexpected type, unknown top-level field, etc.).
    """


class UnknownBackgroundIdError(NormalizationConfigError):
    """``get_background`` or ``resolve_background_for_profile``
    was asked for a ``background_id`` that is not in the
    background family. Raised rather than silently falling back
    so background provenance stays honest on every manifest.
    """


class InvalidBackgroundFamilyError(NormalizationConfigError):
    """The background-family YAML parsed but did not conform to
    the ratified shape.
    """


# ---- Frozen dataclasses (mirror ratified YAML shape) ------------


@dataclass(frozen=True, slots=True)
class SurfaceProfileCrop:
    aspect_ratio: str
    strategy: str
    subject_scale: float


@dataclass(frozen=True, slots=True)
class SurfaceProfileEyeLine:
    position_from_top: float
    position_from_left: float


@dataclass(frozen=True, slots=True)
class SurfaceProfileMargins:
    min_edge_padding: float


@dataclass(frozen=True, slots=True)
class SurfaceProfileOutput:
    width_px: int
    height_px: int
    format: str
    color_space: str


@dataclass(frozen=True, slots=True)
class SurfaceProfileFramingBehavior:
    # Ratified YAMLs use lists; we freeze to tuples so the dataclass
    # is hashable and cannot mutate under a caller.
    includes: tuple[str, ...]
    excludes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SurfaceProfile:
    """One ratified surface profile.

    ``schema_hash`` is a stable SHA-256 hex digest over the
    raw YAML file bytes as loaded. It's included so the pipeline
    version recorded on a ``NormalizationManifest`` can prove
    which YAML content produced a given normalized artifact,
    even if a later profile edit forgets to bump ``version``.
    """

    profile_id: str
    version: int
    framing_family: str
    crop: SurfaceProfileCrop
    eye_line: SurfaceProfileEyeLine
    margins: SurfaceProfileMargins
    output: SurfaceProfileOutput
    framing_behavior: SurfaceProfileFramingBehavior
    tonal_environment_class: str | None
    schema_hash: str


@dataclass(frozen=True, slots=True)
class ProceduralV1:
    """Concrete round-one rendering values for a background.

    Ratified in ``background_family_v1.yaml`` at SESSION 246
    7.c.a. Every background carries one. The values are
    **implementation_provisional** — they exist to make the
    round-one benchmark pipeline runnable, NOT as a Color and
    Light V1 palette selection.

    Fields:

    * ``fill_rgb`` — the deterministic RGB tuple that Step 7's
      ``BackgroundReplacementStage`` composites the matted
      foreground over.
    * ``status`` — e.g. ``"implementation_provisional"``.
    * ``purpose`` — e.g. ``"round_one_normalization_only"``.

    ``status`` and ``purpose`` exist so a future reader (or a
    tool auditing the YAML) cannot mistake these for final
    aesthetic values.
    """

    fill_rgb: tuple[int, int, int]
    status: str
    purpose: str


@dataclass(frozen=True, slots=True)
class Background:
    background_id: str
    description: str
    tonal_direction: str
    luminance_class: str
    grain: str
    round_one_role: str
    procedural_v1: ProceduralV1


@dataclass(frozen=True, slots=True)
class BackgroundFamily:
    """The ratified controlled background family plus the tonal-
    environment-class → background_id mapping the pipeline
    consumes to select a background per surface profile.

    ``tonal_environment_class_default_background`` is stored as
    an immutable Mapping so callers cannot mutate the loaded
    config in place.
    """

    schema_id: str
    schema_version: int
    backgrounds: tuple[Background, ...]
    tonal_environment_class_default_background: Mapping[str, str]
    default_background_for_unspecified_profile: str
    schema_hash: str


# ---- Path resolution --------------------------------------------


def _repo_root() -> Path:
    """Resolve the character-os repo root from this file's location.

    ``config.py`` lives at
    ``media-engine/app/services/normalization/config.py`` — four
    parents up is the repo root. Kept as a helper so tests can
    monkeypatch it if the surrounding layout ever changes.
    """
    return Path(__file__).resolve().parents[4]


def default_surface_profiles_dir() -> Path:
    """Default filesystem path to the ratified surface-profile
    YAMLs.
    """
    return (
        _repo_root()
        / "docs"
        / "design"
        / "visual"
        / "portrait_qualification"
        / "schemas"
        / "surface_profiles"
    )


def default_backgrounds_path() -> Path:
    """Default filesystem path to the ratified background family
    YAML.
    """
    return (
        _repo_root()
        / "docs"
        / "design"
        / "visual"
        / "portrait_qualification"
        / "schemas"
        / "background_family_v1.yaml"
    )


# ---- Stable-hash helper -----------------------------------------


def stable_yaml_hash(source: bytes | str) -> str:
    """SHA-256 hex digest of the ratified YAML content as loaded.

    The pipeline uses this to prove that a normalized artifact
    was produced against a specific frozen version of the source
    YAML. String inputs are UTF-8-encoded first; byte inputs are
    hashed verbatim. Determinism is inherent — SHA-256 is a pure
    function — so the same YAML file always yields the same hex
    digest regardless of when the process ran.
    """
    if isinstance(source, str):
        source = source.encode("utf-8")
    return hashlib.sha256(source).hexdigest()


# ---- Internal parse helpers -------------------------------------


def _require_key(
    d: Mapping[str, Any], key: str, context: str, exc_type: type[NormalizationConfigError]
) -> Any:
    if key not in d:
        raise exc_type(f"{context}: missing required key {key!r}")
    return d[key]


def _require_type(
    value: Any,
    expected: type | tuple[type, ...],
    context: str,
    exc_type: type[NormalizationConfigError],
) -> Any:
    if not isinstance(value, expected):
        exp_name = (
            expected.__name__ if isinstance(expected, type)
            else "|".join(t.__name__ for t in expected)
        )
        raise exc_type(
            f"{context}: expected {exp_name}, got {type(value).__name__}"
        )
    return value


def _require_string_list(
    value: Any, context: str, exc_type: type[NormalizationConfigError]
) -> tuple[str, ...]:
    _require_type(value, list, context, exc_type)
    for item in value:
        _require_type(item, str, f"{context} item", exc_type)
    return tuple(value)


_ALLOWED_PROFILE_KEYS = frozenset({
    "profile_id",
    "version",
    "framing_family",
    "crop",
    "eye_line",
    "margins",
    "output",
    "framing_behavior",
    "tonal_environment_class",
})


def _parse_surface_profile(
    parsed: Any, schema_hash: str, source_context: str
) -> SurfaceProfile:
    _require_type(parsed, dict, source_context, InvalidSurfaceProfileError)

    unknown = set(parsed.keys()) - _ALLOWED_PROFILE_KEYS
    if unknown:
        raise InvalidSurfaceProfileError(
            f"{source_context}: unknown top-level key(s) "
            f"{sorted(unknown)}; allowed = {sorted(_ALLOWED_PROFILE_KEYS)}"
        )

    profile_id = _require_type(
        _require_key(parsed, "profile_id", source_context, InvalidSurfaceProfileError),
        str, f"{source_context}.profile_id", InvalidSurfaceProfileError,
    )
    version = _require_type(
        _require_key(parsed, "version", source_context, InvalidSurfaceProfileError),
        int, f"{source_context}.version", InvalidSurfaceProfileError,
    )
    framing_family = _require_type(
        _require_key(parsed, "framing_family", source_context, InvalidSurfaceProfileError),
        str, f"{source_context}.framing_family", InvalidSurfaceProfileError,
    )

    crop_raw = _require_key(parsed, "crop", source_context, InvalidSurfaceProfileError)
    _require_type(crop_raw, dict, f"{source_context}.crop", InvalidSurfaceProfileError)
    crop = SurfaceProfileCrop(
        aspect_ratio=_require_type(
            _require_key(crop_raw, "aspect_ratio", f"{source_context}.crop", InvalidSurfaceProfileError),
            str, f"{source_context}.crop.aspect_ratio", InvalidSurfaceProfileError,
        ),
        strategy=_require_type(
            _require_key(crop_raw, "strategy", f"{source_context}.crop", InvalidSurfaceProfileError),
            str, f"{source_context}.crop.strategy", InvalidSurfaceProfileError,
        ),
        subject_scale=float(_require_type(
            _require_key(crop_raw, "subject_scale", f"{source_context}.crop", InvalidSurfaceProfileError),
            (int, float), f"{source_context}.crop.subject_scale", InvalidSurfaceProfileError,
        )),
    )

    eye_raw = _require_key(parsed, "eye_line", source_context, InvalidSurfaceProfileError)
    _require_type(eye_raw, dict, f"{source_context}.eye_line", InvalidSurfaceProfileError)
    eye_line = SurfaceProfileEyeLine(
        position_from_top=float(_require_type(
            _require_key(eye_raw, "position_from_top", f"{source_context}.eye_line", InvalidSurfaceProfileError),
            (int, float), f"{source_context}.eye_line.position_from_top", InvalidSurfaceProfileError,
        )),
        position_from_left=float(_require_type(
            _require_key(eye_raw, "position_from_left", f"{source_context}.eye_line", InvalidSurfaceProfileError),
            (int, float), f"{source_context}.eye_line.position_from_left", InvalidSurfaceProfileError,
        )),
    )

    margins_raw = _require_key(parsed, "margins", source_context, InvalidSurfaceProfileError)
    _require_type(margins_raw, dict, f"{source_context}.margins", InvalidSurfaceProfileError)
    margins = SurfaceProfileMargins(
        min_edge_padding=float(_require_type(
            _require_key(margins_raw, "min_edge_padding", f"{source_context}.margins", InvalidSurfaceProfileError),
            (int, float), f"{source_context}.margins.min_edge_padding", InvalidSurfaceProfileError,
        )),
    )

    output_raw = _require_key(parsed, "output", source_context, InvalidSurfaceProfileError)
    _require_type(output_raw, dict, f"{source_context}.output", InvalidSurfaceProfileError)
    output = SurfaceProfileOutput(
        width_px=_require_type(
            _require_key(output_raw, "width_px", f"{source_context}.output", InvalidSurfaceProfileError),
            int, f"{source_context}.output.width_px", InvalidSurfaceProfileError,
        ),
        height_px=_require_type(
            _require_key(output_raw, "height_px", f"{source_context}.output", InvalidSurfaceProfileError),
            int, f"{source_context}.output.height_px", InvalidSurfaceProfileError,
        ),
        format=_require_type(
            _require_key(output_raw, "format", f"{source_context}.output", InvalidSurfaceProfileError),
            str, f"{source_context}.output.format", InvalidSurfaceProfileError,
        ),
        color_space=_require_type(
            _require_key(output_raw, "color_space", f"{source_context}.output", InvalidSurfaceProfileError),
            str, f"{source_context}.output.color_space", InvalidSurfaceProfileError,
        ),
    )

    fb_raw = _require_key(parsed, "framing_behavior", source_context, InvalidSurfaceProfileError)
    _require_type(fb_raw, dict, f"{source_context}.framing_behavior", InvalidSurfaceProfileError)
    framing_behavior = SurfaceProfileFramingBehavior(
        includes=_require_string_list(
            _require_key(fb_raw, "includes", f"{source_context}.framing_behavior", InvalidSurfaceProfileError),
            f"{source_context}.framing_behavior.includes", InvalidSurfaceProfileError,
        ),
        excludes=_require_string_list(
            _require_key(fb_raw, "excludes", f"{source_context}.framing_behavior", InvalidSurfaceProfileError),
            f"{source_context}.framing_behavior.excludes", InvalidSurfaceProfileError,
        ),
    )

    tec = parsed.get("tonal_environment_class")
    if tec is not None:
        _require_type(
            tec, str, f"{source_context}.tonal_environment_class",
            InvalidSurfaceProfileError,
        )

    return SurfaceProfile(
        profile_id=profile_id,
        version=version,
        framing_family=framing_family,
        crop=crop,
        eye_line=eye_line,
        margins=margins,
        output=output,
        framing_behavior=framing_behavior,
        tonal_environment_class=tec,
        schema_hash=schema_hash,
    )


_ALLOWED_BACKGROUND_KEYS = frozenset({
    "background_id",
    "description",
    "tonal_direction",
    "luminance_class",
    "grain",
    "round_one_role",
    "procedural_v1",
})


_ALLOWED_PROCEDURAL_V1_KEYS = frozenset({
    "fill_rgb",
    "status",
    "purpose",
})


def _parse_procedural_v1(raw: Any, context: str) -> ProceduralV1:
    _require_type(raw, dict, context, InvalidBackgroundFamilyError)
    unknown = set(raw.keys()) - _ALLOWED_PROCEDURAL_V1_KEYS
    if unknown:
        raise InvalidBackgroundFamilyError(
            f"{context}: unknown procedural_v1 key(s) {sorted(unknown)}; "
            f"allowed = {sorted(_ALLOWED_PROCEDURAL_V1_KEYS)}"
        )
    fill_raw = _require_key(raw, "fill_rgb", context, InvalidBackgroundFamilyError)
    _require_type(
        fill_raw, list, f"{context}.fill_rgb", InvalidBackgroundFamilyError,
    )
    if len(fill_raw) != 3:
        raise InvalidBackgroundFamilyError(
            f"{context}.fill_rgb: expected 3 integer channels, got "
            f"{len(fill_raw)}"
        )
    channels: list[int] = []
    for i, ch in enumerate(fill_raw):
        _require_type(
            ch, int, f"{context}.fill_rgb[{i}]", InvalidBackgroundFamilyError,
        )
        if isinstance(ch, bool):
            # ``bool`` is a subclass of ``int`` in Python — reject
            # explicitly so ``[true, false, 128]`` doesn't sneak
            # through as a valid channel triple.
            raise InvalidBackgroundFamilyError(
                f"{context}.fill_rgb[{i}]: expected int, got bool"
            )
        if ch < 0 or ch > 255:
            raise InvalidBackgroundFamilyError(
                f"{context}.fill_rgb[{i}]: channel value {ch} outside [0, 255]"
            )
        channels.append(int(ch))
    status = _require_type(
        _require_key(raw, "status", context, InvalidBackgroundFamilyError),
        str, f"{context}.status", InvalidBackgroundFamilyError,
    )
    purpose = _require_type(
        _require_key(raw, "purpose", context, InvalidBackgroundFamilyError),
        str, f"{context}.purpose", InvalidBackgroundFamilyError,
    )
    return ProceduralV1(
        fill_rgb=(channels[0], channels[1], channels[2]),
        status=status,
        purpose=purpose,
    )

_ALLOWED_FAMILY_KEYS = frozenset({
    "schema_id",
    "schema_version",
    "generated",
    "backgrounds",
    "tonal_environment_class_default_background",
    "default_background_for_unspecified_profile",
    "reviewer_override",
    "rules",
})


def _parse_background(raw: Any, context: str) -> Background:
    _require_type(raw, dict, context, InvalidBackgroundFamilyError)
    unknown = set(raw.keys()) - _ALLOWED_BACKGROUND_KEYS
    if unknown:
        raise InvalidBackgroundFamilyError(
            f"{context}: unknown background key(s) {sorted(unknown)}; "
            f"allowed = {sorted(_ALLOWED_BACKGROUND_KEYS)}"
        )
    procedural_v1_raw = _require_key(
        raw, "procedural_v1", context, InvalidBackgroundFamilyError,
    )
    procedural_v1 = _parse_procedural_v1(
        procedural_v1_raw, f"{context}.procedural_v1",
    )
    return Background(
        background_id=_require_type(
            _require_key(raw, "background_id", context, InvalidBackgroundFamilyError),
            str, f"{context}.background_id", InvalidBackgroundFamilyError,
        ),
        description=_require_type(
            _require_key(raw, "description", context, InvalidBackgroundFamilyError),
            str, f"{context}.description", InvalidBackgroundFamilyError,
        ),
        tonal_direction=_require_type(
            _require_key(raw, "tonal_direction", context, InvalidBackgroundFamilyError),
            str, f"{context}.tonal_direction", InvalidBackgroundFamilyError,
        ),
        luminance_class=_require_type(
            _require_key(raw, "luminance_class", context, InvalidBackgroundFamilyError),
            str, f"{context}.luminance_class", InvalidBackgroundFamilyError,
        ),
        grain=_require_type(
            _require_key(raw, "grain", context, InvalidBackgroundFamilyError),
            str, f"{context}.grain", InvalidBackgroundFamilyError,
        ),
        round_one_role=_require_type(
            _require_key(raw, "round_one_role", context, InvalidBackgroundFamilyError),
            str, f"{context}.round_one_role", InvalidBackgroundFamilyError,
        ),
        procedural_v1=procedural_v1,
    )


def _parse_background_family(
    parsed: Any, schema_hash: str, source_context: str
) -> BackgroundFamily:
    _require_type(parsed, dict, source_context, InvalidBackgroundFamilyError)

    unknown = set(parsed.keys()) - _ALLOWED_FAMILY_KEYS
    if unknown:
        raise InvalidBackgroundFamilyError(
            f"{source_context}: unknown top-level key(s) "
            f"{sorted(unknown)}; allowed = {sorted(_ALLOWED_FAMILY_KEYS)}"
        )

    schema_id = _require_type(
        _require_key(parsed, "schema_id", source_context, InvalidBackgroundFamilyError),
        str, f"{source_context}.schema_id", InvalidBackgroundFamilyError,
    )
    schema_version = _require_type(
        _require_key(parsed, "schema_version", source_context, InvalidBackgroundFamilyError),
        int, f"{source_context}.schema_version", InvalidBackgroundFamilyError,
    )

    bg_raw = _require_key(
        parsed, "backgrounds", source_context, InvalidBackgroundFamilyError
    )
    _require_type(bg_raw, list, f"{source_context}.backgrounds", InvalidBackgroundFamilyError)
    backgrounds = tuple(
        _parse_background(b, f"{source_context}.backgrounds[{i}]")
        for i, b in enumerate(bg_raw)
    )

    # background_id uniqueness — a duplicate silently shadows the
    # first entry once we build a dict below; catch it here loudly.
    seen: set[str] = set()
    for b in backgrounds:
        if b.background_id in seen:
            raise InvalidBackgroundFamilyError(
                f"{source_context}: duplicate background_id "
                f"{b.background_id!r}"
            )
        seen.add(b.background_id)

    tec_map_raw = _require_key(
        parsed,
        "tonal_environment_class_default_background",
        source_context,
        InvalidBackgroundFamilyError,
    )
    _require_type(
        tec_map_raw,
        dict,
        f"{source_context}.tonal_environment_class_default_background",
        InvalidBackgroundFamilyError,
    )
    tec_map: dict[str, str] = {}
    for key, value in tec_map_raw.items():
        _require_type(
            key, str,
            f"{source_context}.tonal_environment_class_default_background key",
            InvalidBackgroundFamilyError,
        )
        _require_type(
            value, str,
            f"{source_context}.tonal_environment_class_default_background[{key}]",
            InvalidBackgroundFamilyError,
        )
        if value not in seen:
            raise InvalidBackgroundFamilyError(
                f"{source_context}: tonal_environment_class_default_background"
                f"[{key!r}] points at unknown background_id {value!r}"
            )
        tec_map[key] = value

    default_id = _require_type(
        _require_key(
            parsed,
            "default_background_for_unspecified_profile",
            source_context,
            InvalidBackgroundFamilyError,
        ),
        str,
        f"{source_context}.default_background_for_unspecified_profile",
        InvalidBackgroundFamilyError,
    )
    if default_id not in seen:
        raise InvalidBackgroundFamilyError(
            f"{source_context}: default_background_for_unspecified_profile "
            f"points at unknown background_id {default_id!r}"
        )

    return BackgroundFamily(
        schema_id=schema_id,
        schema_version=schema_version,
        backgrounds=backgrounds,
        tonal_environment_class_default_background=MappingProxyType(tec_map),
        default_background_for_unspecified_profile=default_id,
        schema_hash=schema_hash,
    )


# ---- Public loaders ---------------------------------------------


def load_surface_profile(
    profile_id: str,
    *,
    schemas_root: Path | None = None,
) -> SurfaceProfile:
    """Load a ratified surface profile by identifier.

    ``schemas_root`` overrides the default directory
    (``default_surface_profiles_dir()``). Tests use it to point at
    fixture directories.
    """
    if not profile_id or not isinstance(profile_id, str):
        raise UnknownSurfaceProfileError(
            f"profile_id must be a non-empty string; got {profile_id!r}"
        )

    root = schemas_root if schemas_root is not None else default_surface_profiles_dir()
    path = root / f"{profile_id}.yaml"
    if not path.is_file():
        raise UnknownSurfaceProfileError(
            f"no surface profile YAML at {path}"
        )
    raw_bytes = path.read_bytes()
    schema_hash = stable_yaml_hash(raw_bytes)
    parsed = yaml.safe_load(raw_bytes)
    profile = _parse_surface_profile(parsed, schema_hash, source_context=str(path))
    if profile.profile_id != profile_id:
        raise InvalidSurfaceProfileError(
            f"{path}: file profile_id {profile.profile_id!r} does not "
            f"match requested {profile_id!r}"
        )
    return profile


def load_background_family(
    *,
    path: Path | None = None,
) -> BackgroundFamily:
    """Load the ratified controlled background family.

    ``path`` overrides the default location
    (``default_backgrounds_path()``).
    """
    yaml_path = path if path is not None else default_backgrounds_path()
    if not yaml_path.is_file():
        raise InvalidBackgroundFamilyError(
            f"no background family YAML at {yaml_path}"
        )
    raw_bytes = yaml_path.read_bytes()
    schema_hash = stable_yaml_hash(raw_bytes)
    parsed = yaml.safe_load(raw_bytes)
    return _parse_background_family(
        parsed, schema_hash, source_context=str(yaml_path),
    )


def get_background(family: BackgroundFamily, background_id: str) -> Background:
    """Look up a background by identifier. Raises
    ``UnknownBackgroundIdError`` if the id is not in the family —
    background provenance stays honest on every manifest.
    """
    for bg in family.backgrounds:
        if bg.background_id == background_id:
            return bg
    raise UnknownBackgroundIdError(
        f"background_id {background_id!r} is not in the loaded family; "
        f"known = {[b.background_id for b in family.backgrounds]}"
    )


def resolve_background_for_profile(
    family: BackgroundFamily,
    profile: SurfaceProfile,
) -> Background:
    """Select the default background for a profile using the
    family's tonal_environment_class mapping.

    If the profile declares a ``tonal_environment_class`` that
    isn't in the family's map, raise — silent fallback would hide
    a schema-drift bug. If the profile doesn't declare a class at
    all, use the family's declared unspecified-profile default.
    """
    tec = profile.tonal_environment_class
    if tec is None:
        return get_background(
            family, family.default_background_for_unspecified_profile
        )
    if tec not in family.tonal_environment_class_default_background:
        raise UnknownBackgroundIdError(
            f"surface profile {profile.profile_id!r} declares "
            f"tonal_environment_class={tec!r} but the loaded background "
            f"family has no default for that class; known classes = "
            f"{sorted(family.tonal_environment_class_default_background)}"
        )
    return get_background(
        family,
        family.tonal_environment_class_default_background[tec],
    )
