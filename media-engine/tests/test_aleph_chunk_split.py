"""Aleph chunked-path tail-residual merging.

SESSION 181 dogfood of style_remix_pass on a 10.041-second
``generate_visual_clip`` source failed with Aleph rejecting the
third chunk: ``Asset duration must be at least 1 seconds``. The
``ffmpeg segment`` muxer produced 5s + 5s + 0.041s chunks; the
sub-1s tail blew up the whole batch.

These tests cover ``_merge_sub_min_tail_chunk`` — the helper
that merges any sub-min tail chunk back into the penultimate
chunk before Aleph sees it. The unit tests build chunk
fixtures by hand (ffmpeg lavfi) so the test is hermetic and
doesn't depend on the segment muxer's split behaviour, which
varies with input keyframe layout.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.routers.internal import (
    _ALEPH_MIN_CHUNK_SECONDS,
    _aleph_split_into_chunks,
    _merge_sub_min_tail_chunk,
    _probe_duration,
)


def _make_clip(scratch: Path, name: str, duration_s: float) -> Path:
    """Generate a tiny mp4 of the requested duration via lavfi."""
    out = scratch / name
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i",
            f"color=c=blue:s=160x120:r=30:d={duration_s}",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")
    return tmp_path


def test_tail_above_min_is_left_alone(scratch: Path) -> None:
    """Three chunks all comfortably above the Aleph minimum —
    the guard is a no-op."""
    chunks = [
        _make_clip(scratch, "chunk-000.mp4", 5.0),
        _make_clip(scratch, "chunk-001.mp4", 5.0),
        _make_clip(scratch, "chunk-002.mp4", 3.0),
    ]
    result = _merge_sub_min_tail_chunk(chunks, scratch)
    assert len(result) == 3
    assert result == chunks


def test_sub_min_tail_chunk_is_merged_into_penultimate(
    scratch: Path,
) -> None:
    """SESSION 181 trigger: 0.5s tail (below the 1s Aleph
    minimum) gets concat'd into the previous chunk. Returned
    list has one fewer entry; the penultimate file now holds
    the combined content; the tail file is removed."""
    c0 = _make_clip(scratch, "chunk-000.mp4", 5.0)
    c1 = _make_clip(scratch, "chunk-001.mp4", 5.0)
    c2 = _make_clip(scratch, "chunk-002.mp4", 0.5)
    result = _merge_sub_min_tail_chunk([c0, c1, c2], scratch)
    assert len(result) == 2
    # Tail file got cleaned up.
    assert not c2.exists()
    # Penultimate file inherited the merged content.
    merged_dur = _probe_duration(result[1])
    assert merged_dur > 5.0, (
        f"merged chunk should hold the residual (>5s); got {merged_dur:.3f}s"
    )
    # Every surviving chunk is above the Aleph minimum.
    for c in result:
        assert _probe_duration(c) >= _ALEPH_MIN_CHUNK_SECONDS


def test_single_chunk_list_is_returned_unchanged(scratch: Path) -> None:
    """Single-chunk input can't be merged — Aleph would reject a
    sub-min single chunk but that's a caller bug, not something
    this helper recovers from."""
    chunks = [_make_clip(scratch, "chunk-000.mp4", 0.5)]
    result = _merge_sub_min_tail_chunk(chunks, scratch)
    assert result == chunks


def test_two_chunks_with_sub_min_tail_merges_to_one(
    scratch: Path,
) -> None:
    """Edge case: a 2-chunk list with a sub-min tail collapses
    to a single chunk after merge."""
    c0 = _make_clip(scratch, "chunk-000.mp4", 5.0)
    c1 = _make_clip(scratch, "chunk-001.mp4", 0.3)
    result = _merge_sub_min_tail_chunk([c0, c1], scratch)
    assert len(result) == 1
    assert not c1.exists()
    assert _probe_duration(result[0]) >= _ALEPH_MIN_CHUNK_SECONDS


def test_tail_at_exact_minimum_is_left_alone(scratch: Path) -> None:
    """The guard fires only on chunks STRICTLY shorter than the
    minimum. A chunk at the threshold is acceptable to Aleph."""
    c0 = _make_clip(scratch, "chunk-000.mp4", 5.0)
    c1 = _make_clip(
        scratch, "chunk-001.mp4", _ALEPH_MIN_CHUNK_SECONDS,
    )
    result = _merge_sub_min_tail_chunk([c0, c1], scratch)
    assert len(result) == 2
    assert result == [c0, c1]


# ---- SESSION 201 forward-defense — silent-source segmenter -------


def _make_silent_clip(scratch: Path, name: str, duration_s: float) -> Path:
    """Generate a silent mp4 — no audio stream. Mirrors what
    ``concat_clips`` produces when every input came from
    ``generate_visual_clip`` / ``extend_visual_clip`` (Runway
    gen4_turbo / gen4.5 outputs)."""
    out = scratch / name
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i",
            f"color=c=blue:s=160x120:r=30:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def _probe_codecs(path: Path) -> list[str]:
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(path),
        ],
        check=True, capture_output=True, text=True, timeout=10,
    )
    return [
        line.strip() for line in probe.stdout.splitlines() if line.strip()
    ]


def test_split_silent_source_emits_video_only_chunks(scratch: Path) -> None:
    """SESSION 201 forward-defense — when the source has no audio
    stream, the segmenter must drop the ``-c:a aac`` encoder args
    + map only video. Pre-fix, ``-map 0`` + ``-c:a aac`` against
    a silent source either errors or produces empty audio streams
    depending on ffmpeg version. Post-fix, chunks are video-only
    and ready for Aleph's video-to-video endpoint."""
    source = _make_silent_clip(scratch, "silent_source.mp4", 12.0)

    chunks_dir = scratch / "chunks"
    chunks_dir.mkdir()
    chunks = _aleph_split_into_chunks(source, 5, chunks_dir)

    assert len(chunks) >= 2, f"expected ≥2 chunks for 12s source, got {len(chunks)}"
    for chunk in chunks:
        codecs = _probe_codecs(chunk)
        assert "video" in codecs
        assert "audio" not in codecs, (
            f"silent source produced a chunk with audio: {chunk.name} "
            f"({codecs}) — the silent-base branch wasn't applied"
        )


def test_split_audio_source_preserves_audio_in_chunks(scratch: Path) -> None:
    """Regression guard for the existing happy path. Audio sources
    (talking_head_polished, the canonical Aleph caller) continue
    to emit chunks with audio streams. Validates the silent-base
    branch didn't break the audio path."""
    source = _make_clip(scratch, "voiced_source.mp4", 12.0)

    chunks_dir = scratch / "chunks"
    chunks_dir.mkdir()
    chunks = _aleph_split_into_chunks(source, 5, chunks_dir)

    assert len(chunks) >= 2
    for chunk in chunks:
        codecs = _probe_codecs(chunk)
        assert "video" in codecs
        assert "audio" in codecs
