"""Evidence-tree paths — ratified §17.8.a layout + 8.b additions.

Ratified directory layout (§17.8.a Amendment 1):

    fixtures/
      <fixture_id>/
        identity.yaml
        rationale.md
        bootstrap/references/           ← Step 9 populates; Step 8 never touches
        runs/
          <benchmark_run_id>/
            <direction>/
              <provider>/
                raw/
                normalized/
                manifests/
                observations/
                scores/                 ← Step 9 territory; Step 8 never creates

8.b additions (minimal, documented, non-reversing):

    fixtures/
      _runs/<run_id>/run_summary.json  ← NEW top-level bucket for the cross-
                                          fixture run summary. Underscore-
                                          prefixed so it sorts separately from
                                          real fixture directories. Contains
                                          one JSON per benchmark run.
      <fixture_id>/runs/<run_id>/<direction>/<provider>/
        candidates/<cell_id>.json      ← NEW per-cell bucket alongside the
                                          five ratified buckets. Holds one
                                          canonical evidence-record locator
                                          per cell. Preserves the ratified
                                          per-artifact-type bucketing (raw/,
                                          normalized/, manifests/,
                                          observations/, scores/) intact.

Cell filename encoding (8.b convention):

    <cell_id> = "<fixture_id>__<reference_kind>__<reference_purpose>__<surface_profile>"

    Double-underscore delimiter chosen so it does not collide with the single
    underscores present in ratified identifiers (fixture_h1, portrait_reference,
    slight_left, team_card, etc.). Fixture is included in the filename as
    self-identifying redundancy — the file's path already carries the
    fixture id (it's the topmost directory), but including it in the name
    makes an extracted / copied file self-identifying.

Extensions:

    * .png for image artifacts (raw + normalized)
    * .json for structured evidence (candidate, manifest, run_summary)

Not created by Step 8:

    * ``bootstrap/references/`` — Step 9 populates after human selection.
    * ``scores/`` — Step 9 populates after human scoring.
    * ``observations/`` — created as empty directory (marker file inside)
      so a future consumer can distinguish "no observations at Step 8"
      from "no observations bucket ever existed."
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .matrix import CellKey


# The one added top-level bucket (justified above). Underscore-prefixed so
# it sorts before ratified fixture_ directories in most POSIX listings.
_TOP_LEVEL_RUNS_DIR: str = "_runs"

# The one added per-cell bucket (justified above). Sibling to the ratified
# raw/normalized/manifests/observations/scores buckets.
_CANDIDATES_BUCKET: str = "candidates"

# Ratified buckets. Kept as a tuple so a test can iterate them without
# risking a mutable-default mistake.
RATIFIED_ARTIFACT_BUCKETS: tuple[str, ...] = (
    "raw",
    "normalized",
    "manifests",
    "observations",
    "scores",  # Step 9 territory; enumerated but never created here
)

_CELL_ID_DELIMITER: str = "__"


def cell_id_for(cell: CellKey) -> str:
    """Return the filename-safe cell identifier for the four
    filename-encoded axes (fixture, kind, purpose, profile).

    Direction + provider are directory components in the ratified
    layout and are deliberately NOT included in the filename to
    avoid redundancy.
    """
    return _CELL_ID_DELIMITER.join(
        [
            cell.fixture_id,
            cell.reference_kind,
            cell.reference_purpose,
            cell.surface_profile,
        ]
    )


@dataclass(frozen=True, slots=True)
class EvidenceLayout:
    """Concrete paths for one benchmark run + one cell inside it.

    All paths are absolute. Constructing an ``EvidenceLayout`` never
    creates directories; the caller (evidence_writer) creates them
    atomically at write time.
    """

    fixtures_root: Path
    run_id: str

    # ---- Top-level (cross-fixture) paths ------------------

    @property
    def top_level_run_root(self) -> Path:
        """Directory that holds the cross-fixture ``run_summary.json``."""
        return self.fixtures_root / _TOP_LEVEL_RUNS_DIR / self.run_id

    @property
    def run_summary_path(self) -> Path:
        return self.top_level_run_root / "run_summary.json"

    # ---- Per-cell paths -----------------------------------

    def cell_provider_root(self, cell: CellKey) -> Path:
        """Directory that holds the ratified per-artifact buckets +
        the added ``candidates/`` bucket for one ``(direction,
        provider)`` combination."""
        return (
            self.fixtures_root
            / cell.fixture_id
            / "runs"
            / self.run_id
            / cell.direction
            / cell.provider
        )

    def bucket_dir(self, cell: CellKey, bucket: str) -> Path:
        if bucket not in RATIFIED_ARTIFACT_BUCKETS and bucket != _CANDIDATES_BUCKET:
            raise ValueError(
                f"unknown evidence bucket {bucket!r}. Ratified: "
                f"{RATIFIED_ARTIFACT_BUCKETS}; 8.b addition: "
                f"{_CANDIDATES_BUCKET!r}"
            )
        return self.cell_provider_root(cell) / bucket

    def raw_artifact_path(self, cell: CellKey) -> Path:
        return self.bucket_dir(cell, "raw") / f"{cell_id_for(cell)}.png"

    def normalized_artifact_path(self, cell: CellKey) -> Path:
        return self.bucket_dir(cell, "normalized") / f"{cell_id_for(cell)}.png"

    def normalization_manifest_path(self, cell: CellKey) -> Path:
        return self.bucket_dir(cell, "manifests") / f"{cell_id_for(cell)}.json"

    def candidate_json_path(self, cell: CellKey) -> Path:
        return self.bucket_dir(cell, _CANDIDATES_BUCKET) / f"{cell_id_for(cell)}.json"

    def observations_marker_path(self, cell: CellKey) -> Path:
        """Empty-observations marker file. Existence proves the
        observations bucket was created intentionally by Step 8 and
        left empty of records — as opposed to the bucket never
        existing at all."""
        return self.bucket_dir(cell, "observations") / ".step8_empty_observations"

    def relative_from_fixtures_root(self, path: Path) -> str:
        """Return ``path`` as a slash-separated relative string from
        ``fixtures_root``. Used to store portable references on the
        candidate record so a moved fixture tree still resolves."""
        return path.relative_to(self.fixtures_root).as_posix()


def is_ratified_artifact_bucket(bucket: str) -> bool:
    """True for the ratified §17.8.a artifact buckets. False for
    the 8.b-added ``candidates`` bucket and for anything else."""
    return bucket in RATIFIED_ARTIFACT_BUCKETS


__all__ = [
    "EvidenceLayout",
    "RATIFIED_ARTIFACT_BUCKETS",
    "cell_id_for",
    "is_ratified_artifact_bucket",
]
