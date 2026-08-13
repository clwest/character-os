"""Atomic evidence writer + SHA-256 hashing.

Load-bearing invariants (operator disciplines #4, #5, #6):

* **Append-only.** If the run's top-level or per-cell target already
  exists, refuse. No ``--force`` overwrite mode. A retry produces a
  new ``run_id`` with the same ``run_fingerprint`` per 8.a discipline.
* **Atomic writes.** Every file lands via temp-in-same-directory +
  ``os.replace`` (POSIX atomic rename on the same filesystem). A
  crash mid-write cannot leave a partially-written file at the
  final path.
* **Hash on write.** Every binary evidence artifact (raw + normalized
  bytes) records a SHA-256 hex digest alongside its path so Step 9
  can prove file identity.
* **JSON is canonical.** Structured records use the deterministic
  serialization discipline established by 8.a's ``_stable_json``
  (sorted keys, compact separators, ASCII, ``default=str`` for
  YAML-native dates).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EvidenceWriteError(Exception):
    """Base for evidence-writer errors."""


class RunIdConflictError(EvidenceWriteError):
    """The requested run_id already has evidence on disk. Refused
    per operator discipline #4 (append-only, no --force)."""


class ArtifactConflictError(EvidenceWriteError):
    """An artifact file at the target path already exists. Only
    raised inside a run whose top-level was cleared to write —
    guards against a runner-loop double-emission bug."""


# ---- Hashing ---------------------------------------------------


def sha256_hex(data: bytes) -> str:
    """SHA-256 hex digest. Matches the repo standard used by
    fixture content_hash + background family schema hash."""
    return hashlib.sha256(data).hexdigest()


# ---- Canonical JSON serialization ------------------------------


def canonical_json_bytes(payload: Any) -> bytes:
    """Return ``payload`` serialized deterministically as UTF-8
    bytes. Mirrors the ``_stable_json`` discipline in 8.a's
    fixture_loader / run_identity modules so evidence produced
    here is byte-identical across two runs with identical
    payloads."""
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    # Trailing newline so the file ends cleanly; canonical bytes
    # unchanged regardless of the OS.
    return (text + "\n").encode("utf-8")


# ---- Atomic filesystem writes ---------------------------------


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically.

    Sequence: create parent, write to a temp file in the SAME
    directory (so ``os.replace`` is guaranteed atomic — same
    filesystem), fsync the temp fd, ``os.replace`` to the final
    name.

    If the temp write or replace fails, no half-written file
    appears at ``path`` — the temp file gets cleaned up
    explicitly.
    """
    if path.exists():
        raise ArtifactConflictError(
            f"refusing to overwrite existing evidence artifact at {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".tmp.",
        dir=path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(tmp_fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # fsync is not universally supported (e.g. some
                # tmpfs mounts on CI). The atomic rename below
                # still guards against half-written files at the
                # final path.
                pass
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file if we failed before rename.
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


# ---- Public writer API ----------------------------------------


@dataclass(frozen=True, slots=True)
class WrittenArtifact:
    """Return shape for a single successful atomic write."""

    absolute_path: Path
    relative_from_fixtures_root: str
    sha256_hex: str
    byte_count: int


class EvidenceWriter:
    """Append-only, atomic filesystem writer for one benchmark run.

    Instantiate once per run. Guards the run_id append-only
    invariant at construction time — if the target top-level
    directory already exists, construction raises. Subsequent
    per-artifact writes are atomic and self-hashing.
    """

    def __init__(self, fixtures_root: Path, run_id: str) -> None:
        self._fixtures_root = fixtures_root
        self._run_id = run_id
        # Top-level cross-fixture directory — the append-only guard
        # anchor. If it exists, an earlier run wrote here; refuse.
        top_level = fixtures_root / "_runs" / run_id
        if top_level.exists():
            raise RunIdConflictError(
                f"run_id {run_id!r} already has evidence at {top_level} — "
                f"a retry must mint a fresh run_id with the same "
                f"run_fingerprint (per SESSION 247 operator discipline #4)"
            )

    @property
    def fixtures_root(self) -> Path:
        return self._fixtures_root

    @property
    def run_id(self) -> str:
        return self._run_id

    def write_binary(self, path: Path, data: bytes) -> WrittenArtifact:
        """Atomic-write a binary artifact + compute SHA-256."""
        _write_bytes_atomic(path, data)
        return WrittenArtifact(
            absolute_path=path,
            relative_from_fixtures_root=path.relative_to(
                self._fixtures_root
            ).as_posix(),
            sha256_hex=sha256_hex(data),
            byte_count=len(data),
        )

    def write_json(self, path: Path, payload: Any) -> WrittenArtifact:
        """Atomic-write a JSON evidence record (deterministic
        canonical serialization). Hash is over the canonical bytes
        so a re-read + re-serialize could reproduce it."""
        data = canonical_json_bytes(payload)
        _write_bytes_atomic(path, data)
        return WrittenArtifact(
            absolute_path=path,
            relative_from_fixtures_root=path.relative_to(
                self._fixtures_root
            ).as_posix(),
            sha256_hex=sha256_hex(data),
            byte_count=len(data),
        )

    def create_empty_marker(self, path: Path) -> WrittenArtifact:
        """Create a zero-byte marker file at ``path``. Used for
        the observations bucket's ``.step8_empty_observations``
        file so a future consumer can prove the bucket was
        created intentionally.

        Idempotent: repeat calls on an existing marker are no-ops
        that still return a WrittenArtifact. This is the one
        exception to the writer's append-only discipline —
        observations markers are per-``<direction>/<provider>``
        directory-flag files, not per-cell artifacts. Two cells
        that share the same provider subtree share the marker.
        """
        if path.exists() and path.is_file() and path.stat().st_size == 0:
            return WrittenArtifact(
                absolute_path=path,
                relative_from_fixtures_root=path.relative_to(
                    self._fixtures_root
                ).as_posix(),
                sha256_hex=sha256_hex(b""),
                byte_count=0,
            )
        return self.write_binary(path, b"")


__all__ = [
    "ArtifactConflictError",
    "EvidenceWriteError",
    "EvidenceWriter",
    "RunIdConflictError",
    "WrittenArtifact",
    "canonical_json_bytes",
    "sha256_hex",
]
