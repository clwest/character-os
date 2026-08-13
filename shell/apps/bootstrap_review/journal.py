"""Append-only reviewer decision journal — §19 Step 9.b.2 (SESSION 249).

Load-bearing disciplines (§14.2 append-only + SESSION 249 Deliverable E):

* One JSONL file per POST at
  ``fixtures/<fixture_id>/bootstrap/review/<decision_id>.jsonl``.
* Files are **written once and never mutated**. Amendment lands as a
  new file whose decision record carries ``supersedes_decision_id``.
* Canonical JSON serialization (sorted keys, tight separators) so
  bytes are deterministic across writers.
* Atomic creation via temp-file + ``os.replace``.
* Idempotency by ``decision_id``: same UUID + identical canonical
  payload returns the stored decision; different payload raises
  :class:`DecisionIdConflict`.
* Currency is DERIVED, not stored — every read reconstructs the
  terminal decision per slot by walking the ``supersedes_decision_id``
  chain across the fixture's directory.

Reviewer identity per L2 + Q8: authenticated User FK + email captured
at write time. No group / role / "Chris" concept.

This module does not create any Django rows and does not touch the
canonical substrate. That's 9.b.3 territory (Q7, Q22, Finding 3).
"""
from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal

from .evidence import (
    AUTHORIZED_FIXTURE_IDS,
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    FROZEN_EVIDENCE_ROOT,
)

REVIEW_SCHEMA_VERSION = 1
REVIEW_SCHEMA_ID = "bootstrap-review-decision.v1"

Disposition = Literal["selected", "no_candidate_approved"]
AUTHORIZED_DISPOSITIONS: frozenset[str] = frozenset(
    {"selected", "no_candidate_approved"}
)


# ---------------------------------------------------------------------
# Exceptions — stable domain vocabulary
# ---------------------------------------------------------------------


class JournalError(Exception):
    code: str = "journal_error"


class DecisionIdConflict(JournalError):
    """Raised when a decision_id file exists but its bytes differ
    from the proposed payload. Idempotent retry with the SAME payload
    is not a conflict — it returns the stored record.
    """

    code = "decision_id_conflict"


class MalformedJournalRecord(JournalError):
    """Raised when a journal file on disk cannot be parsed or is
    missing required fields. Loud failure — never silently skip
    corrupt evidence.
    """

    code = "malformed_journal_record"


# ---------------------------------------------------------------------
# Decision record — the single row appended per POST
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionRecord:
    """Immutable representation of one reviewer decision."""

    decision_id: str
    review_run_id: str
    bootstrap_run_id: str
    fixture_id: str
    reference_kind: str
    reference_purpose: str
    disposition: Disposition
    frozen_candidate_id: str | None
    supersedes_decision_id: str | None
    amendment_reason: str | None
    reviewer_user_id: int
    reviewer_email_at_write_time: str
    decided_at_utc: str
    review_schema_version: int = REVIEW_SCHEMA_VERSION


# ---------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------


def review_dir_for_fixture(fixture_id: str) -> Path:
    """Return the append-only journal directory for a fixture. Does
    NOT create the directory — creation happens at first write.
    """
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        raise JournalError(f"fixture_id={fixture_id!r} not authorized")
    return FROZEN_EVIDENCE_ROOT / fixture_id / "bootstrap" / "review"


def decision_file_path(fixture_id: str, decision_id: str) -> Path:
    _validate_decision_id_shape(decision_id)
    return review_dir_for_fixture(fixture_id) / f"{decision_id}.jsonl"


def _validate_decision_id_shape(decision_id: str) -> None:
    """Reject decision_ids that could enable path traversal.

    UUIDs are ``[0-9a-f-]`` — reject anything else.
    """
    if not decision_id:
        raise JournalError("decision_id may not be empty")
    if any(c not in "0123456789abcdef-" for c in decision_id):
        raise JournalError(
            f"decision_id={decision_id!r} must be a lowercase hex UUID"
        )
    if "/" in decision_id or "\\" in decision_id or ".." in decision_id:
        raise JournalError(f"decision_id={decision_id!r} contains illegal characters")


# ---------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------


def _canonical_json(payload: dict) -> bytes:
    """Byte-stable JSON serialization: sorted keys, no whitespace,
    UTF-8. Two writers producing the same logical payload produce
    byte-identical bytes.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _build_file_bytes(record: DecisionRecord) -> bytes:
    """Compose the 2-line JSONL bytes for a decision file.

    Line 1: review_run_header (Deliverable E schema).
    Line 2: decision record.
    """
    header = {
        "record_type": "review_run_header",
        "review_run_id": record.review_run_id,
        "schema": REVIEW_SCHEMA_ID,
        "opened_at_utc": record.decided_at_utc,
        "opened_by": {
            "user_id": record.reviewer_user_id,
            "email_at_write_time": record.reviewer_email_at_write_time,
        },
        "bootstrap_run_id": record.bootstrap_run_id,
        "fixture_id": record.fixture_id,
    }
    decision_line = {"record_type": "decision", **asdict(record)}
    return (
        _canonical_json(header)
        + b"\n"
        + _canonical_json(decision_line)
        + b"\n"
    )


# ---------------------------------------------------------------------
# Atomic append (one file per POST)
# ---------------------------------------------------------------------


def append_decision(record: DecisionRecord) -> tuple[DecisionRecord, bool]:
    """Write ``record`` to a new JSONL file atomically.

    Returns ``(record, created)`` where ``created=True`` if the file
    was newly written and ``False`` if the file already existed with
    byte-identical content (idempotent replay).

    Raises :class:`DecisionIdConflict` when the file exists but its
    bytes differ (same ``decision_id`` used with a different payload).

    Atomicity: writes to a temp file inside the same directory and
    calls :func:`os.replace` — a single rename is atomic on POSIX
    filesystems. The temp file is unlinked on any exception before
    the rename.
    """
    _validate_decision_id_shape(record.decision_id)
    if record.fixture_id not in AUTHORIZED_FIXTURE_IDS:
        raise JournalError(f"fixture_id={record.fixture_id!r} not authorized")

    payload_bytes = _build_file_bytes(record)
    review_dir = review_dir_for_fixture(record.fixture_id)
    review_dir.mkdir(parents=True, exist_ok=True)
    target = review_dir / f"{record.decision_id}.jsonl"

    if target.exists():
        # Idempotent replay if the bytes match; conflict otherwise.
        existing = target.read_bytes()
        if existing == payload_bytes:
            return record, False
        raise DecisionIdConflict(
            f"decision_id={record.decision_id!r} already exists with "
            "different canonical payload"
        )

    # Write to a temp file in the same directory (same-filesystem
    # requirement for os.replace atomicity), then rename.
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{record.decision_id}.", suffix=".tmp", dir=str(review_dir)
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # O_EXCL-flavored: os.link raises FileExistsError if
            # target appeared between the earlier .exists() check
            # and now. Race-safe idempotency check.
            os.link(str(tmp_path), str(target))
        except FileExistsError:
            # Raced with a concurrent writer. Re-check idempotency
            # against whatever landed first.
            existing = target.read_bytes()
            if existing == payload_bytes:
                return record, False
            raise DecisionIdConflict(
                f"decision_id={record.decision_id!r} landed concurrently "
                "with a different canonical payload"
            ) from None
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return record, True


# ---------------------------------------------------------------------
# Reads — enumerate + derive currency
# ---------------------------------------------------------------------


def _iter_decision_files(fixture_id: str) -> Iterator[Path]:
    review_dir = review_dir_for_fixture(fixture_id)
    if not review_dir.exists():
        return
    yield from sorted(review_dir.glob("*.jsonl"))


def _parse_decision_record(path: Path) -> dict:
    """Parse a journal file and return its decision record dict.

    Raises :class:`MalformedJournalRecord` on any parse failure or
    missing required field. Never silently skips.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    decision_line = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MalformedJournalRecord(
                f"invalid JSON in {path.name}: {exc}"
            ) from exc
        if isinstance(obj, dict) and obj.get("record_type") == "decision":
            decision_line = obj
    if decision_line is None:
        raise MalformedJournalRecord(f"no decision record in {path.name}")
    required = {
        "decision_id",
        "review_run_id",
        "bootstrap_run_id",
        "fixture_id",
        "reference_kind",
        "reference_purpose",
        "disposition",
        "decided_at_utc",
        "reviewer_user_id",
    }
    missing = required - set(decision_line)
    if missing:
        raise MalformedJournalRecord(
            f"decision record in {path.name} missing fields: {missing}"
        )
    return decision_line


def iter_all_decisions(fixture_id: str) -> Iterable[dict]:
    """Yield every decision record under a fixture in
    ``decided_at_utc`` order.

    Malformed files raise immediately — currency derivation cannot
    proceed against a corrupt journal.
    """
    records = [_parse_decision_record(p) for p in _iter_decision_files(fixture_id)]
    records.sort(key=lambda r: (r["decided_at_utc"], r["decision_id"]))
    yield from records


def current_decision_per_slot(fixture_id: str) -> dict[tuple[str, str], dict]:
    """Return ``{(reference_kind, reference_purpose): terminal_decision}``.

    Terminal = a decision no later decision supersedes. The append-
    only journal + slot-scoped stale_supersedes_decision guard
    together mean each slot has exactly one terminal decision under
    normal operation. If the invariant is violated (multi-writer
    branching), the newest-by-timestamp wins for read purposes and
    the situation is discoverable via :func:`decision_history_for_slot`.
    """
    decisions = list(iter_all_decisions(fixture_id))
    by_slot: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for d in decisions:
        key = (d["reference_kind"], d["reference_purpose"])
        by_slot[key].append(d)

    result: dict[tuple[str, str], dict] = {}
    for slot, recs in by_slot.items():
        superseded_ids = {
            r["supersedes_decision_id"]
            for r in recs
            if r.get("supersedes_decision_id")
        }
        terminals = [r for r in recs if r["decision_id"] not in superseded_ids]
        if not terminals:
            # Impossible under correct writes (cycle).
            continue
        if len(terminals) > 1:
            terminals.sort(key=lambda r: (r["decided_at_utc"], r["decision_id"]))
        result[slot] = terminals[-1]
    return result


def decision_history_for_slot(
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> list[dict]:
    """Return every decision for one slot in chronological order.

    Used by the SPA's history expander per §Q14. Returns raw record
    dicts so all fields (including reviewer identity + amendment
    reason) are available to the caller.
    """
    return [
        d
        for d in iter_all_decisions(fixture_id)
        if d["reference_kind"] == reference_kind
        and d["reference_purpose"] == reference_purpose
    ]


# ---------------------------------------------------------------------
# Fixture progress — Finding 4 dual-signal derivation
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureProgress:
    """Two distinct signals per Finding 4.

    * ``review_complete`` — all 7 human portrait_reference purposes
      have a terminal decision (``selected`` or ``no_candidate_approved``).
    * ``approval_floor_satisfied`` — every ``<kind>/<purpose>`` pair
      in the branch schema's ``required_for_identity`` list has a
      terminal decision of ``selected``.
    """

    purposes_total: int
    purposes_dispositioned: int
    review_complete: bool
    approval_floor_pairs: tuple[str, ...]
    approval_floor_satisfied_pairs: tuple[str, ...]
    approval_floor_satisfied: bool


def derive_fixture_progress(
    fixture_id: str,
    required_for_identity: list[str],
) -> FixtureProgress:
    """Compute both progress signals for a fixture."""
    current = current_decision_per_slot(fixture_id)

    purposes_total = len(AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES)
    dispositioned = 0
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if ("portrait_reference", purpose) in current:
            dispositioned += 1

    satisfied: list[str] = []
    for pair in required_for_identity:
        if "/" not in pair:
            continue
        kind, purpose = pair.split("/", 1)
        decision = current.get((kind, purpose))
        if decision is not None and decision["disposition"] == "selected":
            satisfied.append(pair)

    return FixtureProgress(
        purposes_total=purposes_total,
        purposes_dispositioned=dispositioned,
        review_complete=(dispositioned == purposes_total),
        approval_floor_pairs=tuple(required_for_identity),
        approval_floor_satisfied_pairs=tuple(satisfied),
        approval_floor_satisfied=(
            len(satisfied) == len(required_for_identity)
            and len(required_for_identity) > 0
        ),
    )
