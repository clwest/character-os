"""The ``split_script`` step primitive.

SESSION 143 / V5. Splits a long-form script into N
sentence-boundary chunks for downstream avatar-speech rendering.

### How V5 actually uses this

The ``long_form_ad`` starter **calls the underlying
``chunk_script`` helper directly** at composition-create time
to determine how many ``generate_avatar_speech`` steps to lay
down. The runtime sees a deterministic N-step plan (contract
rule 5: linear ordering only). The chunks ride as ``params.script``
on each speech step.

### Why the primitive still exists

V0 lists 16 primitives — ``split_script`` is one of them.
Composition authors who want a single-step "produce chunked
TRANSCRIPT asset" capability (e.g. for V12's ``recut_teaser``
composition that picks one of N chunks) can use this primitive
in its registry-driven form. The output is a TRANSCRIPT Asset
whose ``inline_content`` is a JSON array of chunk strings,
queryable by downstream steps.

The two paths share the same ``chunk_script`` /
``split_script_with_llm`` helpers — no duplication.

### Params

* ``script`` (str, required) — the input long-form script.
* ``max_chars`` (int, optional) — per-chunk char ceiling.
  Defaults to ``DEFAULT_CHUNK_MAX_CHARS`` (280, Runway's
  per-call ceiling minus headroom).
* ``use_llm`` (bool, default False) — call gpt-5-mini for
  semantic splits. Falls back to the naive splitter on any
  failure (graceful degradation per V0 contract rule 6).

### Output

One TRANSCRIPT Asset whose ``inline_content`` is JSON:
``["chunk 1 text", "chunk 2 text", ...]``. Downstream
consumers can parse + iterate. ``source_spec`` records the
chunk count, max_chars setting, and whether the LLM path
was used.
"""
from __future__ import annotations

import json
import logging

from apps.compositions.models import AssetRole, AssetType
from apps.compositions.script_splitter import (
    DEFAULT_CHUNK_MAX_CHARS,
    chunk_script,
    split_script_with_llm,
)

from .mock import PrimitiveError, PrimitiveResult

logger = logging.getLogger(__name__)


# Cost model: gpt-5-mini at ~$0.15/1M input + $0.60/1M output
# tokens. Conservative single-call estimate for the typical
# long-form script (≤4000 input chars ~= 1000 tokens, ≤500
# output tokens). Naive path costs zero.
_SPLIT_SCRIPT_LLM_MICROS = 500   # ~$0.0005 per call
_SPLIT_SCRIPT_NAIVE_MICROS = 0


class SplitScriptPrimitive:
    """``split_script`` step primitive.

    Single-output semantics for V2 runtime compatibility: the
    chunks are returned as a JSON array in the TRANSCRIPT
    asset's ``inline_content``."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        script = str(params.get("script", "")).strip()
        if not script:
            raise PrimitiveError(
                "split_script requires a non-empty script param"
            )

        max_chars = int(params.get("max_chars") or DEFAULT_CHUNK_MAX_CHARS)
        use_llm = bool(params.get("use_llm")) and not mock_mode

        if use_llm:
            chunks = split_script_with_llm(script, max_chars=max_chars)
            split_path = "llm_with_naive_fallback"
        else:
            chunks = chunk_script(script, max_chars=max_chars)
            split_path = "naive"

        if not chunks:
            raise PrimitiveError(
                f"split_script produced zero chunks from a {len(script)}-char input"
            )

        # All chunks must respect the cap — the naive splitter
        # guarantees this; the LLM path's fallback chain enforces
        # it. Defensive check anyway.
        for i, c in enumerate(chunks):
            if len(c) > max_chars:
                raise PrimitiveError(
                    f"split_script chunk {i} exceeds max_chars "
                    f"({len(c)} > {max_chars})"
                )

        inline_payload = json.dumps(chunks, ensure_ascii=False)
        cost = (
            _SPLIT_SCRIPT_LLM_MICROS if use_llm else _SPLIT_SCRIPT_NAIVE_MICROS
        )

        logger.info(
            "split_script step=%s input_chars=%d chunks=%d max_chars=%d path=%s",
            step.id, len(script), len(chunks), max_chars, split_path,
        )
        return PrimitiveResult(
            asset_type=AssetType.TRANSCRIPT,
            inline_content=inline_payload,
            mime_type="application/json",
            size_bytes=len(inline_payload.encode("utf-8")),
            cost_micros=cost,
            extra_source_spec={
                "primitive_kind": "split_script",
                "chunk_count": len(chunks),
                "max_chars": max_chars,
                "split_path": split_path,
                "input_chars": len(script),
            },
            role=AssetRole.TRANSCRIPT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Naive path is free; LLM path is bounded by a single
        gpt-5-mini call."""
        if bool((params or {}).get("use_llm")):
            return _SPLIT_SCRIPT_LLM_MICROS
        return _SPLIT_SCRIPT_NAIVE_MICROS
