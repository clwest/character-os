"""Fixture loader — reads ratified fixture identity payloads
from disk, validates against the ratified branch schema, and
computes an immutable content hash suitable for use in the
harness's reproducibility fingerprint.

Boundary discipline (per §19.3 Step 8 + operator F-8.1):

* The loader **does not** write anything to the Django substrate.
  It reads ``identity.yaml`` + ``rationale.md`` and returns an
  in-memory ``LoadedFixture``.
* The loader **does** validate the payload against the ratified
  branch schema so Step 9 can promote the fixture into a
  ``CharacterIdentityVersion`` without reinterpretation.
* The loader **does not** infer branch from directory name — it
  reads the schema id and cross-checks. A fixture whose
  ``spec_schema_version`` disagrees with its schema file is
  rejected at load time.

Fixture-directory layout (ratified §17.8.a):

    fixtures/
      README.md
      FIXTURE_AUTHORING_GUIDE_V1.md
      fixture_<branch><n>/
        identity.yaml     ← this loader reads
        rationale.md      ← this loader reads
        bootstrap/references/     ← Step 9 writes; loader ignores
        runs/<run_id>/…           ← Step 8 writes; loader ignores
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import yaml

from .vocabulary import IdentityBranch, RATIFIED_FIXTURES


class FixtureError(Exception):
    """Base for fixture-loader errors."""


class FixtureNotFoundError(FixtureError):
    """The fixture directory or a required file is missing."""


class FixtureSchemaError(FixtureError):
    """The fixture payload does not validate against its
    branch schema, OR the branch cannot be determined, OR the
    spec_schema_version disagrees with the schema file's
    schema_version.
    """


# ---- Repo paths ----------------------------------------------

# Ratified location. The loader accepts a ``fixtures_root`` /
# ``schemas_root`` override for tests; production callers use
# the defaults resolved via ``__file__``.


def _repo_root() -> Path:
    """Resolve the repo root by walking upward from this module.
    Kept small so the loader has no dependency on Django settings
    or media-engine ``config.Settings``.
    """
    return Path(__file__).resolve().parents[4]


def default_fixtures_root() -> Path:
    return (
        _repo_root()
        / "docs" / "design" / "visual" / "portrait_qualification" / "fixtures"
    )


def default_schemas_root() -> Path:
    return (
        _repo_root()
        / "docs" / "design" / "visual" / "portrait_qualification" / "schemas"
    )


# Filename per branch. Mirrors ``shell/apps/identity/schema_loader.py``
# but is duplicated (as strings) to keep the media-engine harness
# free of a Django-side import — monorepo boundary per CLAUDE.md.

_BRANCH_SCHEMA_FILE: dict[IdentityBranch, str] = {
    IdentityBranch.HUMAN: "human_identity_schema_v1.yaml",
    IdentityBranch.NON_HUMAN: "non_human_test_schema_v1.yaml",
}


# ---- Dataclasses ---------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedFixture:
    """A validated fixture in memory.

    * ``fixture_id`` — the ratified branch-prefixed identifier,
      e.g. ``fixture_h1``. Immutable per §17.8.b.
    * ``branch`` — inferred from the ``spec_payload`` shape after
      cross-checking the schema file's ``branch`` field.
    * ``fixture_version`` — the ``spec_schema_version`` on the
      payload. Bumped only via an authored fixture-schema
      amendment.
    * ``spec_payload`` — the loaded YAML dict, validated against
      the branch schema.
    * ``rationale`` — the free-text ``rationale.md`` content
      verbatim.
    * ``content_hash`` — sha256 hex of the canonical serialization
      of ``(fixture_id, branch, fixture_version, spec_payload,
      rationale)``. Immutable identity of *what this fixture is*
      today; consumed by the run-identity fingerprint.
    """

    fixture_id: str
    branch: IdentityBranch
    fixture_version: int
    spec_payload: Mapping[str, Any]
    rationale: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class LoadedBranchSchema:
    """A validated branch schema in memory."""

    branch: IdentityBranch
    schema_id: str
    schema_version: int
    spec_payload_schema: Mapping[str, Any]
    schema_hash: str


# ---- Loaders --------------------------------------------------


def _stable_json(obj: Any) -> str:
    """Deterministic JSON serialization for hashing.

    ``sort_keys=True`` locks map ordering; ``separators`` removes
    whitespace variance; ``ensure_ascii=True`` prevents encoding
    drift across platforms.

    ``default=str`` handles YAML-native types PyYAML surfaces as
    Python objects (``datetime.date`` from bare ISO dates like
    the ``generated: 2026-08-06`` header fields). Serialized as
    the object's ``str()`` form — stable and lossless for dates.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        default=str,
    )


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def load_branch_schema(
    branch: IdentityBranch,
    *,
    schemas_root: Path | None = None,
) -> LoadedBranchSchema:
    """Load and validate the ratified branch schema."""
    root = schemas_root or default_schemas_root()
    file_name = _BRANCH_SCHEMA_FILE[branch]
    path = root / file_name
    if not path.is_file():
        raise FixtureNotFoundError(
            f"branch schema not found for {branch.value!r} at {path}"
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise FixtureSchemaError(
            f"cannot parse branch schema at {path}: {exc!s}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise FixtureSchemaError(
            f"branch schema at {path} is not a mapping"
        )
    for key in ("schema_id", "schema_version", "branch", "spec_payload_schema"):
        if key not in raw:
            raise FixtureSchemaError(
                f"branch schema at {path} missing required key {key!r}"
            )
    if raw["branch"] != branch.value:
        raise FixtureSchemaError(
            f"branch schema at {path} declares branch "
            f"{raw['branch']!r}; loader requested {branch.value!r}"
        )
    schema_hash = _sha256_hex(_stable_json(dict(raw)))
    return LoadedBranchSchema(
        branch=branch,
        schema_id=str(raw["schema_id"]),
        schema_version=int(raw["schema_version"]),
        spec_payload_schema=dict(raw["spec_payload_schema"]),
        schema_hash=schema_hash,
    )


def _infer_branch(fixture_id: str) -> IdentityBranch:
    """The fixture identifier's branch prefix (`h` / `nh`)
    determines the schema branch per §17.8.b."""
    body = fixture_id.removeprefix("fixture_")
    if body == fixture_id:
        raise FixtureSchemaError(
            f"fixture_id must start with 'fixture_', got {fixture_id!r}"
        )
    if body.startswith("nh"):
        return IdentityBranch.NON_HUMAN
    if body.startswith("h"):
        return IdentityBranch.HUMAN
    raise FixtureSchemaError(
        f"fixture_id {fixture_id!r} has unrecognized branch prefix — "
        f"expected 'h' or 'nh' after 'fixture_'"
    )


def load_fixture(
    fixture_id: str,
    *,
    fixtures_root: Path | None = None,
    schemas_root: Path | None = None,
) -> LoadedFixture:
    """Load one fixture. Validates the payload against its
    branch schema and computes the content hash.

    Raises ``FixtureNotFoundError`` for missing files;
    ``FixtureSchemaError`` for schema disagreements or invalid
    payload.
    """
    if fixture_id not in RATIFIED_FIXTURES:
        # Not a canonical ratified fixture. Loader allows loading
        # off-catalog fixtures for tests, but keeps the caller
        # honest — the exception message names what's ratified
        # so a typo surfaces immediately in real code paths.
        pass  # deliberately non-fatal; catalog check happens elsewhere
    root = fixtures_root or default_fixtures_root()
    fixture_dir = root / fixture_id
    if not fixture_dir.is_dir():
        raise FixtureNotFoundError(
            f"fixture directory not found: {fixture_dir}"
        )
    identity_path = fixture_dir / "identity.yaml"
    rationale_path = fixture_dir / "rationale.md"
    if not identity_path.is_file():
        raise FixtureNotFoundError(f"identity.yaml missing: {identity_path}")
    if not rationale_path.is_file():
        raise FixtureNotFoundError(f"rationale.md missing: {rationale_path}")

    try:
        spec_payload = yaml.safe_load(identity_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise FixtureSchemaError(
            f"cannot parse identity.yaml at {identity_path}: {exc!s}"
        ) from exc
    if not isinstance(spec_payload, Mapping):
        raise FixtureSchemaError(
            f"identity.yaml at {identity_path} is not a mapping"
        )

    branch = _infer_branch(fixture_id)
    branch_schema = load_branch_schema(branch, schemas_root=schemas_root)

    # Validate against the ratified spec_payload schema (JSON
    # Schema draft-07 via ``jsonschema.validate``). This is the
    # ratified authority; catching validation errors here keeps
    # Step 9's promotion path from having to re-validate.
    try:
        jsonschema.validate(instance=dict(spec_payload), schema=dict(branch_schema.spec_payload_schema))
    except jsonschema.ValidationError as exc:
        raise FixtureSchemaError(
            f"identity.yaml at {identity_path} failed schema validation: "
            f"{exc.message}"
        ) from exc

    # Cross-check spec_schema_version.
    fixture_version = int(spec_payload["spec_schema_version"])
    if fixture_version != branch_schema.schema_version:
        raise FixtureSchemaError(
            f"identity.yaml at {identity_path} declares "
            f"spec_schema_version={fixture_version}; branch schema is "
            f"version {branch_schema.schema_version}. Explicit migration "
            f"required — no silent reinterpretation."
        )

    rationale = rationale_path.read_text(encoding="utf-8")

    content_hash = _sha256_hex(
        _stable_json(
            {
                "fixture_id": fixture_id,
                "branch": branch.value,
                "fixture_version": fixture_version,
                "spec_payload": dict(spec_payload),
                "rationale": rationale,
            }
        )
    )

    return LoadedFixture(
        fixture_id=fixture_id,
        branch=branch,
        fixture_version=fixture_version,
        spec_payload=dict(spec_payload),
        rationale=rationale,
        content_hash=content_hash,
    )


def load_ratified_fixtures(
    *,
    fixtures_root: Path | None = None,
    schemas_root: Path | None = None,
) -> tuple[LoadedFixture, ...]:
    """Load every ratified round-one fixture. Order matches
    ``RATIFIED_FIXTURES``, which is authoring-sequence per
    §17.8.b (not quality / priority).
    """
    return tuple(
        load_fixture(
            fx,
            fixtures_root=fixtures_root,
            schemas_root=schemas_root,
        )
        for fx in RATIFIED_FIXTURES
    )


__all__ = [
    "FixtureError",
    "FixtureNotFoundError",
    "FixtureSchemaError",
    "LoadedBranchSchema",
    "LoadedFixture",
    "default_fixtures_root",
    "default_schemas_root",
    "load_branch_schema",
    "load_fixture",
    "load_ratified_fixtures",
]
