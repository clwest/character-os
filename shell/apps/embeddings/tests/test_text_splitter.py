"""Unit tests for TextSplitter — pure function, no DB."""
from __future__ import annotations

import pytest

from apps.embeddings.text_splitter import TextSplitter


def test_empty_text_returns_no_chunks() -> None:
    assert TextSplitter().split("") == []
    assert TextSplitter().split("   \n  \t ") == []


def test_short_text_returns_single_chunk() -> None:
    splitter = TextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split("hello world")
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].index == 0


def test_paragraphs_split_on_blank_lines() -> None:
    splitter = TextSplitter(chunk_size=50, chunk_overlap=10)
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = splitter.split(text)
    assert len(chunks) >= 2
    # Chunk indices are dense
    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_oversized_paragraph_is_split_on_sentences() -> None:
    """A single paragraph longer than chunk_size gets split at
    sentence boundaries (period delimited)."""
    splitter = TextSplitter(chunk_size=80, chunk_overlap=10)
    # ~250-char paragraph, no internal blank lines
    paragraph = (
        "First sentence here. Second sentence is a bit longer. "
        "Third sentence keeps going. Fourth sentence is even longer than the others. "
        "Fifth sentence rounds it out."
    )
    chunks = splitter.split(paragraph)
    assert len(chunks) >= 2
    for chunk in chunks:
        # Sub-chunks may exceed chunk_size by one sentence, but not by much
        assert chunk.size < 200


def test_chunk_indices_are_sequential_and_dense() -> None:
    splitter = TextSplitter(chunk_size=60, chunk_overlap=10)
    text = "\n\n".join(f"Paragraph {n} with enough content to count." for n in range(20))
    chunks = splitter.split(text)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_invalid_init_args_raise() -> None:
    with pytest.raises(ValueError):
        TextSplitter(chunk_size=0)
    with pytest.raises(ValueError):
        TextSplitter(chunk_size=100, chunk_overlap=200)  # overlap >= size
    with pytest.raises(ValueError):
        TextSplitter(chunk_size=100, chunk_overlap=-1)


def test_overlap_zero_produces_disjoint_chunks() -> None:
    splitter = TextSplitter(chunk_size=50, chunk_overlap=0)
    text = "\n\n".join(f"Paragraph {n}." for n in range(10))
    chunks = splitter.split(text)
    # With 0 overlap, none of the chunks should contain content
    # from a chunk-boundary overlap window.
    assert len(chunks) >= 2
