"""Atomic evidence-writer coverage.

Confirms:
* Append-only invariant — refusing to overwrite an existing run_id.
* Atomic write — no half-written files on failure.
* SHA-256 hashing matches over-the-wire bytes.
* Canonical JSON is deterministic across repeat serializations.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.benchmark_harness import (
    ArtifactConflictError,
    EvidenceWriter,
    RunIdConflictError,
    canonical_json_bytes,
    sha256_hex,
)


def test_writer_refuses_when_run_id_top_level_already_exists(tmp_path: Path) -> None:
    """A prior run left evidence at fixtures/_runs/<run_id>/;
    constructing an EvidenceWriter for the same run_id raises."""
    (tmp_path / "_runs" / "bootstrap_x").mkdir(parents=True)
    with pytest.raises(RunIdConflictError, match="already has evidence"):
        EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_x")


def test_writer_accepts_fresh_run_id(tmp_path: Path) -> None:
    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    assert writer.run_id == "bootstrap_a"
    assert writer.fixtures_root == tmp_path


def test_write_binary_atomic_and_hashes(tmp_path: Path) -> None:
    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    payload = b"\x00\x01\x02hello"
    target = tmp_path / "sub" / "artifact.bin"
    art = writer.write_binary(target, payload)
    assert target.exists()
    assert target.read_bytes() == payload
    assert art.sha256_hex == sha256_hex(payload)
    assert art.byte_count == len(payload)
    assert art.absolute_path == target
    assert art.relative_from_fixtures_root == "sub/artifact.bin"


def test_write_binary_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"prior")
    with pytest.raises(ArtifactConflictError, match="refusing to overwrite"):
        writer.write_binary(target, b"new")


def test_write_binary_no_partial_file_on_failure(tmp_path: Path, monkeypatch) -> None:
    """Simulate a write failure and confirm no partial file lands
    at the final path."""
    import os

    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    target = tmp_path / "artifact.bin"

    # Force os.replace to raise, simulating a filesystem failure
    # AFTER the temp file was written.
    orig_replace = os.replace

    def fail_replace(*a, **kw):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated rename failure"):
        writer.write_binary(target, b"payload")
    # No file at the final path.
    assert not target.exists()
    # No leftover *.tmp.* files in the parent.
    assert list(target.parent.glob("*.tmp.*")) == []

    monkeypatch.setattr(os, "replace", orig_replace)


def test_write_json_produces_canonical_bytes(tmp_path: Path) -> None:
    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    payload = {"b": 2, "a": [3, 1, 2]}
    art = writer.write_json(tmp_path / "sub" / "record.json", payload)
    on_disk = (tmp_path / "sub" / "record.json").read_bytes()
    # Sorted keys, compact separators, trailing newline.
    assert on_disk == b'{"a":[3,1,2],"b":2}\n'
    assert art.sha256_hex == sha256_hex(on_disk)


def test_canonical_json_stable_across_repeat_calls() -> None:
    a = canonical_json_bytes({"a": 1, "b": [2, 3]})
    b = canonical_json_bytes({"b": [2, 3], "a": 1})
    assert a == b


def test_canonical_json_serializes_yaml_native_types_via_str() -> None:
    """PyYAML surfaces bare ISO dates as ``datetime.date``. The
    canonical serializer's ``default=str`` fallback must handle
    them so a payload containing a date field is still
    serializable."""
    from datetime import date

    payload = {"generated_on": date(2026, 8, 8)}
    b = canonical_json_bytes(payload)
    assert b == b'{"generated_on":"2026-08-08"}\n'


def test_create_empty_marker_writes_zero_bytes(tmp_path: Path) -> None:
    writer = EvidenceWriter(fixtures_root=tmp_path, run_id="bootstrap_a")
    marker = tmp_path / "obs" / ".step8_empty_observations"
    art = writer.create_empty_marker(marker)
    assert marker.exists()
    assert marker.stat().st_size == 0
    assert art.byte_count == 0
    assert art.sha256_hex == sha256_hex(b"")
