"""Frozen 9.a evidence reader — §19 Step 9.b.1 (SESSION 249).

Read-only access to the immutable bootstrap run frozen in SESSION 248
under ``docs/design/visual/portrait_qualification/fixtures/``. Every
public function in this module reads the tree; no function writes.

Load-bearing disciplines enforced here:

* **Single authorized run.** 9.b.1 exposes only
  ``bootstrap_20260808T044853Z_7eb392992e0f``. Arbitrary run IDs are
  refused with :class:`UnauthorizedRunId` so future runs cannot leak
  through this surface before their own scope-lock.
* **Frozen-tree containment.** Every path is resolved with
  :func:`Path.resolve` and asserted to be an ancestor of the
  frozen-evidence root. Prevents path traversal via ``..`` segments or
  absolute-path injection.
* **Canonical candidate identity.** ``frozen_candidate_id`` per
  SESSION 249 Finding 1 is the four-part
  ``<run_id>/<direction>/<provider>/<cell_id>`` identifier. This
  module is the only place that parses or constructs it.
* **Integrity verification.** :func:`read_artifact_bytes` verifies
  the on-disk SHA-256 against ``candidate.json`` before returning
  bytes. Any mismatch raises :class:`ArtifactIntegrityError` — never
  a silent stream.
* **Absent artifact honesty.** Missing raw / normalized / manifest
  artifacts return a distinct :class:`ArtifactAbsent` sentinel; the
  view layer emits a stable JSON error code rather than fabricating
  data.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from django.conf import settings

# ---------------------------------------------------------------------
# Frozen-tree root + authorized run vocabulary
# ---------------------------------------------------------------------

FROZEN_EVIDENCE_ROOT = (
    Path(settings.BASE_DIR).parent
    / "docs"
    / "design"
    / "visual"
    / "portrait_qualification"
    / "fixtures"
).resolve()

# 9.b.1 exposes exactly this run. Adding future runs requires a new
# scope-lock and an explicit expansion of this frozenset — never a
# pattern-based carve-out.
AUTHORIZED_RUN_IDS: frozenset[str] = frozenset(
    {"bootstrap_20260808T044853Z_7eb392992e0f"}
)

# Ratified round-one fixture set (§17.8.a). 9.b.1 exposes only the
# human branch (fixture_h1..h4). fixture_nh1 remains substrate-
# exercise-only per SESSION 248 §Q24.
AUTHORIZED_FIXTURE_IDS: frozenset[str] = frozenset(
    {"fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"}
)

AUTHORIZED_DIRECTIONS: frozenset[str] = frozenset(
    {"identity_only", "softened_photographic"}
)

AUTHORIZED_PROVIDERS: frozenset[str] = frozenset(
    {"stability_still", "runway_still_portrait"}
)

AUTHORIZED_REFERENCE_KINDS: frozenset[str] = frozenset({"portrait_reference"})

AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES: tuple[str, ...] = (
    "front",
    "slight_left",
    "slight_right",
    "neutral_rest",
    "listening",
    "consideration",
    "gentle_positive",
)

AUTHORIZED_SURFACE_PROFILES: frozenset[str] = frozenset(
    {"compact", "team_card", "presence", "studio", "conversation"}
)

# Cell filename encoding per §F-8.2 (SESSION 247).
_CELL_ID_PATTERN = re.compile(
    r"^(?P<fixture>fixture_[a-z0-9]+)__"
    r"(?P<kind>[a-z_]+)__"
    r"(?P<purpose>[a-z_]+)__"
    r"(?P<profile>[a-z_]+)$"
)


ArtifactKind = Literal["raw", "normalized", "manifest", "candidate"]


# ---------------------------------------------------------------------
# Exceptions — stable domain vocabulary
# ---------------------------------------------------------------------


class EvidenceError(Exception):
    """Base class for evidence-reader failures.

    Every subclass carries a ``.code`` attribute the view layer maps
    to a JSON ``{"code": ...}`` payload so the SPA can render stable
    UX per failure class.
    """

    code: str = "evidence_error"


class UnauthorizedRunId(EvidenceError):
    code = "unauthorized_run_id"


class InvalidFrozenCandidateId(EvidenceError):
    code = "invalid_frozen_candidate_id"


class CandidateJsonMissing(EvidenceError):
    code = "candidate_json_missing"


class ArtifactAbsent(EvidenceError):
    """Raised when a raw / normalized / manifest artifact does not
    exist for a candidate. Honest signal — not an error condition
    for unsupported or normalization-failed candidates.
    """

    code = "artifact_absent"


class ArtifactIntegrityError(EvidenceError):
    """Raised when the on-disk bytes of an artifact do not match the
    SHA-256 recorded in candidate.json. Loud, non-degrading failure.
    """

    code = "artifact_integrity_mismatch"


class PathContainmentViolation(EvidenceError):
    """Raised when a resolved path escapes the frozen-tree root.
    Should be impossible under normal use because every input is
    validated against the authorized-vocabulary frozensets — this is
    defense in depth.
    """

    code = "path_containment_violation"


# ---------------------------------------------------------------------
# frozen_candidate_id — canonical candidate identity
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenCandidateId:
    """Parsed representation of the canonical candidate identity.

    Format: ``<run_id>/<direction>/<provider>/<cell_id>``. Constructed
    only via :meth:`parse` so validation runs on every use.
    """

    run_id: str
    direction: str
    provider: str
    cell_id: str

    @property
    def value(self) -> str:
        return f"{self.run_id}/{self.direction}/{self.provider}/{self.cell_id}"

    @property
    def fixture_id(self) -> str:
        match = _CELL_ID_PATTERN.match(self.cell_id)
        if match is None:
            raise InvalidFrozenCandidateId(
                f"cell_id {self.cell_id!r} does not match ratified encoding"
            )
        return match.group("fixture")

    @property
    def reference_kind(self) -> str:
        match = _CELL_ID_PATTERN.match(self.cell_id)
        if match is None:
            raise InvalidFrozenCandidateId(
                f"cell_id {self.cell_id!r} does not match ratified encoding"
            )
        return match.group("kind")

    @property
    def reference_purpose(self) -> str:
        match = _CELL_ID_PATTERN.match(self.cell_id)
        if match is None:
            raise InvalidFrozenCandidateId(
                f"cell_id {self.cell_id!r} does not match ratified encoding"
            )
        return match.group("purpose")

    @property
    def surface_profile(self) -> str:
        match = _CELL_ID_PATTERN.match(self.cell_id)
        if match is None:
            raise InvalidFrozenCandidateId(
                f"cell_id {self.cell_id!r} does not match ratified encoding"
            )
        return match.group("profile")

    @classmethod
    def parse(cls, raw: str) -> "FrozenCandidateId":
        if not isinstance(raw, str):
            raise InvalidFrozenCandidateId("frozen_candidate_id must be a string")
        parts = raw.split("/")
        if len(parts) != 4:
            raise InvalidFrozenCandidateId(
                f"expected 4 components (run_id/direction/provider/cell_id); "
                f"got {len(parts)}"
            )
        return cls.build(*parts)

    @classmethod
    def build(
        cls,
        run_id: str,
        direction: str,
        provider: str,
        cell_id: str,
    ) -> "FrozenCandidateId":
        _validate_no_path_traversal(run_id, "run_id")
        _validate_no_path_traversal(direction, "direction")
        _validate_no_path_traversal(provider, "provider")
        _validate_no_path_traversal(cell_id, "cell_id")

        if run_id not in AUTHORIZED_RUN_IDS:
            raise UnauthorizedRunId(
                f"run_id={run_id!r} is not authorized for 9.b.1"
            )
        if direction not in AUTHORIZED_DIRECTIONS:
            raise InvalidFrozenCandidateId(
                f"direction={direction!r} is not in the ratified vocabulary"
            )
        if provider not in AUTHORIZED_PROVIDERS:
            raise InvalidFrozenCandidateId(
                f"provider={provider!r} is not in the ratified vocabulary"
            )
        cell_match = _CELL_ID_PATTERN.match(cell_id)
        if cell_match is None:
            raise InvalidFrozenCandidateId(
                f"cell_id={cell_id!r} does not match the ratified encoding"
            )
        if cell_match.group("fixture") not in AUTHORIZED_FIXTURE_IDS:
            raise InvalidFrozenCandidateId(
                f"fixture in cell_id={cell_id!r} is not authorized for 9.b.1"
            )
        if cell_match.group("kind") not in AUTHORIZED_REFERENCE_KINDS:
            raise InvalidFrozenCandidateId(
                f"reference_kind in cell_id={cell_id!r} is not authorized"
            )
        if cell_match.group("purpose") not in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
            raise InvalidFrozenCandidateId(
                f"reference_purpose in cell_id={cell_id!r} is not authorized"
            )
        if cell_match.group("profile") not in AUTHORIZED_SURFACE_PROFILES:
            raise InvalidFrozenCandidateId(
                f"surface_profile in cell_id={cell_id!r} is not authorized"
            )
        return cls(
            run_id=run_id,
            direction=direction,
            provider=provider,
            cell_id=cell_id,
        )


def _validate_no_path_traversal(component: str, name: str) -> None:
    """Reject empty strings, ``..``, path separators, and leading dots.

    The FrozenCandidateId vocabulary uses only ``[a-z0-9_]`` so any
    other character is a red flag.
    """
    if not component:
        raise InvalidFrozenCandidateId(f"{name} may not be empty")
    if component in (".", ".."):
        raise InvalidFrozenCandidateId(
            f"{name}={component!r} is not a valid identifier"
        )
    if "/" in component or "\\" in component:
        raise InvalidFrozenCandidateId(
            f"{name}={component!r} may not contain path separators"
        )
    if component.startswith("."):
        raise InvalidFrozenCandidateId(
            f"{name}={component!r} may not begin with a dot"
        )
    if "\x00" in component:
        raise InvalidFrozenCandidateId(f"{name} contains a null byte")


# ---------------------------------------------------------------------
# Filesystem access — every read routes through here
# ---------------------------------------------------------------------


def _ensure_inside_frozen_root(path: Path) -> Path:
    """Resolve ``path`` and assert containment inside the frozen root."""
    resolved = path.resolve()
    try:
        resolved.relative_to(FROZEN_EVIDENCE_ROOT)
    except ValueError as exc:
        raise PathContainmentViolation(
            f"resolved path {resolved} is outside frozen root "
            f"{FROZEN_EVIDENCE_ROOT}"
        ) from exc
    return resolved


def run_summary_path(run_id: str) -> Path:
    if run_id not in AUTHORIZED_RUN_IDS:
        raise UnauthorizedRunId(
            f"run_id={run_id!r} is not authorized for 9.b.1"
        )
    _validate_no_path_traversal(run_id, "run_id")
    path = FROZEN_EVIDENCE_ROOT / "_runs" / run_id / "run_summary.json"
    return _ensure_inside_frozen_root(path)


def candidate_json_path(fcid: FrozenCandidateId) -> Path:
    """Locate the candidate.json for this identity inside the frozen
    tree. Raises :class:`CandidateJsonMissing` when the file is absent.
    """
    path = (
        FROZEN_EVIDENCE_ROOT
        / fcid.fixture_id
        / "runs"
        / fcid.run_id
        / fcid.direction
        / fcid.provider
        / "candidates"
        / f"{fcid.cell_id}.json"
    )
    resolved = _ensure_inside_frozen_root(path)
    if not resolved.is_file():
        raise CandidateJsonMissing(
            f"candidate.json not found for frozen_candidate_id={fcid.value!r}"
        )
    return resolved


def _artifact_relative_subdir(kind: ArtifactKind) -> str:
    return {
        "raw": "raw",
        "normalized": "normalized",
        "manifest": "manifests",
        "candidate": "candidates",
    }[kind]


def _artifact_extension(kind: ArtifactKind) -> str:
    return {
        "raw": ".png",
        "normalized": ".png",
        "manifest": ".json",
        "candidate": ".json",
    }[kind]


def artifact_path(fcid: FrozenCandidateId, kind: ArtifactKind) -> Path:
    """Return the on-disk path for a specific artifact kind attached
    to ``fcid``. Does NOT check existence — callers use
    :func:`read_artifact_bytes` which handles the absent case.
    """
    path = (
        FROZEN_EVIDENCE_ROOT
        / fcid.fixture_id
        / "runs"
        / fcid.run_id
        / fcid.direction
        / fcid.provider
        / _artifact_relative_subdir(kind)
        / f"{fcid.cell_id}{_artifact_extension(kind)}"
    )
    return _ensure_inside_frozen_root(path)


# ---------------------------------------------------------------------
# Reads — parse candidate.json, verify artifact bytes, iterate slots
# ---------------------------------------------------------------------


def load_run_summary(run_id: str) -> dict:
    path = run_summary_path(run_id)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_candidate_json(fcid: FrozenCandidateId) -> dict:
    with candidate_json_path(fcid).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _recorded_sha256(candidate: dict, kind: ArtifactKind) -> str | None:
    """Extract the recorded SHA-256 for an artifact from candidate.json.

    Returns ``None`` when the artifact is intentionally absent (e.g.
    unsupported cells have no raw_artifact). Raises
    :class:`ArtifactAbsent` when the candidate is a class that CAN
    have this artifact but the candidate.json records it as null.
    """
    if kind == "candidate":
        # The candidate.json itself is the artifact; no recorded sha.
        return None
    if kind == "raw":
        raw = candidate.get("raw_artifact")
        if raw is None:
            raise ArtifactAbsent("candidate has no raw artifact")
        return raw.get("sha256_hex")
    if kind == "normalized":
        norm = candidate.get("normalization_stage", {}).get("normalized_artifact")
        if norm is None:
            raise ArtifactAbsent("candidate has no normalized artifact")
        return norm.get("sha256_hex")
    if kind == "manifest":
        manifest = candidate.get("normalization_stage", {}).get("manifest_artifact")
        if manifest is None:
            raise ArtifactAbsent("candidate has no manifest artifact")
        return manifest.get("sha256_hex")
    raise ValueError(f"unknown artifact kind: {kind}")


def read_artifact_bytes(fcid: FrozenCandidateId, kind: ArtifactKind) -> bytes:
    """Read an artifact's bytes from disk with SHA-256 verification.

    Raises:
      * :class:`ArtifactAbsent` if the candidate is not expected to
        have this artifact (unsupported cell, normalization-failed).
      * :class:`ArtifactIntegrityError` if the on-disk SHA-256 does
        not match the value recorded in candidate.json.
    """
    candidate = load_candidate_json(fcid)
    recorded_sha = _recorded_sha256(candidate, kind)

    path = artifact_path(fcid, kind)
    if not path.is_file():
        raise ArtifactAbsent(f"artifact not on disk: {path.name}")

    payload = path.read_bytes()

    if recorded_sha is not None:
        actual = hashlib.sha256(payload).hexdigest()
        if actual != recorded_sha:
            raise ArtifactIntegrityError(
                f"SHA-256 mismatch for artifact kind={kind} "
                f"frozen_candidate_id={fcid.value!r}: "
                f"expected={recorded_sha} actual={actual}"
            )

    return payload


def iter_slot_candidates(
    run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> Iterable[dict]:
    """Yield every candidate.json under a canonical review slot,
    across both directions and both providers, in a stable order.

    Slot = ``(fixture_id, reference_kind, reference_purpose)``. Under
    the ratified matrix that is 2 directions × 2 providers × 5
    profiles = 20 candidate.json files per slot.
    """
    if run_id not in AUTHORIZED_RUN_IDS:
        raise UnauthorizedRunId(f"run_id={run_id!r} is not authorized")
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        raise InvalidFrozenCandidateId(
            f"fixture_id={fixture_id!r} not authorized for 9.b.1"
        )
    if reference_kind not in AUTHORIZED_REFERENCE_KINDS:
        raise InvalidFrozenCandidateId(
            f"reference_kind={reference_kind!r} not authorized"
        )
    if reference_purpose not in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        raise InvalidFrozenCandidateId(
            f"reference_purpose={reference_purpose!r} not authorized"
        )

    for direction in sorted(AUTHORIZED_DIRECTIONS):
        for provider in sorted(AUTHORIZED_PROVIDERS):
            for profile in sorted(AUTHORIZED_SURFACE_PROFILES):
                cell_id = (
                    f"{fixture_id}__{reference_kind}__"
                    f"{reference_purpose}__{profile}"
                )
                try:
                    fcid = FrozenCandidateId.build(
                        run_id=run_id,
                        direction=direction,
                        provider=provider,
                        cell_id=cell_id,
                    )
                except EvidenceError:
                    # Unauthorized vocab combination — skip. Should
                    # not happen given the guards above, but defense in
                    # depth.
                    continue
                try:
                    yield load_candidate_json(fcid)
                except CandidateJsonMissing:
                    # A frozen run must have candidate.json for every
                    # planned cell. Absent files here signal evidence
                    # tampering; raise loudly rather than filtering.
                    raise


def factual_normalization_notices(candidate: dict) -> list[str]:
    """Extract factual normalization-limitation notices from a
    candidate's manifest_payload, if present.

    Returns an empty list when the candidate has no normalization
    manifest (unsupported cell or normalization-failed). Never
    manufactures notices; only reads what the manifest recorded.
    """
    payload = (
        candidate.get("normalization_stage", {})
        .get("manifest_payload")
        or {}
    )
    if not payload:
        return []

    notices: list[str] = []
    crop = payload.get("crop_metadata") or {}

    for field, label in (
        ("subject_scale_honored", "subject_scale not honored (v1 pipeline limitation)"),
        ("min_edge_padding_honored", "min_edge_padding not honored (v1 pipeline limitation)"),
        ("framing_behavior_honored", "framing_behavior not honored (v1 pipeline limitation)"),
    ):
        honored = crop.get(field)
        if honored is False:
            blocker = crop.get(
                field.replace("_honored", "_honor_blocker")
            )
            if blocker:
                notices.append(f"{label} — blocker: {blocker}")
            else:
                notices.append(label)

    eye_line = payload.get("eye_line_adjustments") or {}
    if eye_line.get("eye_line_clamped") is True:
        vertical = eye_line.get("eye_line_clamped_vertical")
        horizontal = eye_line.get("eye_line_clamped_horizontal")
        parts: list[str] = []
        if vertical:
            parts.append("vertical")
        if horizontal:
            parts.append("horizontal")
        reason = eye_line.get("eye_line_clamp_reason")
        axis = " + ".join(parts) or "unspecified axis"
        if reason:
            notices.append(
                f"eye-line clamped ({axis}) — reason: {reason}"
            )
        else:
            notices.append(f"eye-line clamped ({axis})")

    return notices


def enumerate_planned_slot_grid(
    run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> list[FrozenCandidateId]:
    """Return every ratified ``FrozenCandidateId`` under a slot in
    stable order, whether or not the candidate.json exists on disk.

    Used by tests to enumerate the 20-cell-per-slot planned matrix
    and to prove ``frozen_candidate_id`` uniqueness across the run.
    """
    ids: list[FrozenCandidateId] = []
    for direction in sorted(AUTHORIZED_DIRECTIONS):
        for provider in sorted(AUTHORIZED_PROVIDERS):
            for profile in sorted(AUTHORIZED_SURFACE_PROFILES):
                cell_id = (
                    f"{fixture_id}__{reference_kind}__"
                    f"{reference_purpose}__{profile}"
                )
                ids.append(
                    FrozenCandidateId.build(
                        run_id=run_id,
                        direction=direction,
                        provider=provider,
                        cell_id=cell_id,
                    )
                )
    return ids
