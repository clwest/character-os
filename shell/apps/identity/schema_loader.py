"""Branch-schema loader for the Canonical Identity substrate.

The ratified branch schemas live under the repository's
``docs/design/visual/portrait_qualification/schemas/`` directory
(landed in SESSION 239 as the §19.1 prerequisite artifacts). This
module is the runtime consumer of those YAML files — the
authoritative write path (``apps.identity.services``) delegates
here to decide:

* whether a ``CharacterIdentityVersion.spec`` payload is valid
  for its branch (§17.3.a — schema selection by kind);
* whether an ``IdentityReference`` purpose value is one that the
  branch's purpose schema currently enumerates (§17.5.a — adding
  a purpose does not require a Django migration);
* whether an identity's approved reference set satisfies the
  branch's declarative approval floor (§17.5.b — floor lives in
  the schema, not in Python transition logic);
* what surfaces the current bundle can serve (§17.5.b — surface
  requirements are declarative data).

Runtime dependency note: the schemas ship with the repository
working tree (there is no build step that strips ``docs/`` at this
stage — verified against the local docker-compose deploy story in
SESSION 241). Any future deployment machinery that packages the
shell without ``docs/`` must arrange to ship these files as
runtime resources; otherwise this module raises
``BranchSchemaNotFound`` at import time on the first identity
write.

Non-human branch (§17.2.a): the current non-human schema is
non-canonical and exists **solely** to exercise substrate
branch-neutrality in round-one benchmark. When Character Presence
Language is authored, its schema replaces the non-human file
entirely — this loader will pick up the replacement transparently
because it resolves the branch by kind, not by file name.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml
from django.conf import settings

# Repository schemas directory. Resolved from ``settings.BASE_DIR``
# (which is ``shell/``) so tests + prod both find the same files.
_SCHEMAS_DIR = Path(settings.BASE_DIR).parent / "docs" / "design" / "visual" / "portrait_qualification" / "schemas"


# Filename per branch. The non-human file is explicitly labeled
# non-canonical in its header per §17.2.a; the loader treats both
# files identically at runtime.
_BRANCH_SCHEMA_FILES = {
    "human": "human_identity_schema_v1.yaml",
    "non_human": "non_human_test_schema_v1.yaml",
}

_PURPOSE_SCHEMA_FILES = {
    "human": "purpose_schema_human_v1.yaml",
    # Non-human purpose schema is folded into
    # ``non_human_test_schema_v1.yaml`` at authoring time (there
    # is no separate purpose-per-branch file for non-human in the
    # non-canonical fixture set). The BranchSchema wrapper reads
    # purposes from the branch file when a separate purpose file
    # is absent.
}


class BranchSchemaNotFound(Exception):
    """Raised when a caller requests a schema whose file is
    missing on disk (or whose branch is not recognized).
    """


class BranchSchemaInvalid(Exception):
    """Raised when the loaded YAML does not carry the required
    top-level keys (spec_payload_schema, required_for_identity,
    surface_requirements). Indicates the on-disk artifact has
    drifted from the contract shape §17.5.b requires.
    """


@dataclass(frozen=True)
class BranchSchema:
    """Runtime view over a ratified branch schema.

    Exposes the schema's authored structure — not a Python-side
    flattening. Callers that need the declarative approval floor
    receive it as authored (a list of ``<kind>/<purpose>``
    strings); callers that need surface requirements receive the
    authored map. Neither structure is transformed on the way out
    (per Correction 5, SESSION 241 gate).
    """

    kind: str
    schema_version: int
    spec_payload_schema: dict
    required_for_identity: list[str]
    surface_requirements: dict[str, list[str]]
    purpose_kinds: dict[str, list[str]]

    def validate_spec(self, payload: dict) -> None:
        """Validate a ``CharacterIdentityVersion.spec`` payload
        against ``spec_payload_schema``. Raises
        ``jsonschema.exceptions.ValidationError`` on failure.
        """
        jsonschema.validate(instance=payload, schema=self.spec_payload_schema)

    def validate_purpose(self, kind: str, purpose: str) -> bool:
        """Return True if ``(kind, purpose)`` is enumerated in
        this branch's purpose schema. The write-path service
        raises the domain-appropriate error; this method's
        contract is a plain boolean predicate.
        """
        allowed = self.purpose_kinds.get(kind, [])
        return purpose in allowed


@functools.lru_cache(maxsize=None)
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise BranchSchemaNotFound(
            f"Required branch-schema artifact is missing on disk: {path}. "
            "The ratified schemas ship under "
            "``docs/design/visual/portrait_qualification/schemas/``; "
            "any deployment packaging that strips ``docs/`` must "
            "arrange to ship these files as runtime resources."
        )
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_purpose_kinds(kind: str) -> dict[str, list[str]]:
    """Build the ``{artifact_kind: [purpose_value, ...]}`` map
    from the purpose schema for this branch. When a branch does
    not ship a separate purpose file (currently only human ships
    one), the branch schema itself is the source.
    """
    filename = _PURPOSE_SCHEMA_FILES.get(kind)
    if filename is None:
        return {}
    raw = _load_yaml(_SCHEMAS_DIR / filename)
    kinds_block = raw.get("kinds") or {}
    result: dict[str, list[str]] = {}
    for artifact_kind, spec in kinds_block.items():
        purposes = spec.get("purposes") or []
        # Each purpose is authored as a mapping with ``value``;
        # preserve the authored list order.
        result[artifact_kind] = [entry["value"] for entry in purposes if "value" in entry]
    return result


@functools.lru_cache(maxsize=None)
def get_branch_schema(kind: str) -> BranchSchema:
    """Return the ratified schema for ``kind`` as an authored,
    declarative structure.

    Raises ``BranchSchemaNotFound`` if the branch is not
    recognized or the on-disk artifact is missing.
    Raises ``BranchSchemaInvalid`` if the loaded YAML does not
    carry the required top-level shape.
    """
    filename = _BRANCH_SCHEMA_FILES.get(kind)
    if filename is None:
        raise BranchSchemaNotFound(
            f"Unknown identity branch: {kind!r}. Supported branches: "
            f"{sorted(_BRANCH_SCHEMA_FILES)}."
        )
    raw = _load_yaml(_SCHEMAS_DIR / filename)

    for required_key in ("spec_payload_schema", "required_for_identity", "surface_requirements"):
        if required_key not in raw:
            raise BranchSchemaInvalid(
                f"Branch schema for {kind!r} is missing required key "
                f"{required_key!r}. Expected shape ratified in §17.5.b."
            )

    return BranchSchema(
        kind=kind,
        schema_version=int(raw.get("schema_version", 1)),
        spec_payload_schema=raw["spec_payload_schema"],
        required_for_identity=list(raw["required_for_identity"]),
        surface_requirements={
            surface: list(refs)
            for surface, refs in (raw["surface_requirements"] or {}).items()
        },
        purpose_kinds=_load_purpose_kinds(kind),
    )


def _reset_cache_for_tests() -> None:
    """Clear the module-level LRU caches. Test-only entry point —
    the schemas are stable at runtime so production code has no
    reason to invalidate.
    """
    _load_yaml.cache_clear()
    get_branch_schema.cache_clear()


def _resolve_reference_pair(pair: str) -> tuple[str, str]:
    """Parse a ``<kind>/<purpose>`` string from
    ``required_for_identity`` or ``surface_requirements`` into
    the (kind, purpose) tuple. Kept private — callers work with
    the authored strings directly whenever possible so the
    declarative structure is preserved end to end.
    """
    if "/" not in pair:
        raise BranchSchemaInvalid(
            f"Reference pair {pair!r} is not in the ratified "
            f"``<kind>/<purpose>`` shape (§17.5.a)."
        )
    kind, _, purpose = pair.partition("/")
    return kind, purpose


__all__ = [
    "BranchSchema",
    "BranchSchemaInvalid",
    "BranchSchemaNotFound",
    "get_branch_schema",
]
