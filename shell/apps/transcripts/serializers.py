"""B1.3 — DRF serializers for the transcript miner REST surface.

One serializer for the highlight row. The mine endpoint
accepts a minimal request body (transcript_asset_id +
optional knobs) and returns serialized highlights; the
list / retrieve actions use the same shape.
"""
from __future__ import annotations

from rest_framework import serializers

from .models import TranscriptHighlight


class TranscriptHighlightSerializer(serializers.ModelSerializer):
    """Read-only output shape. Mining + approve/reject paths
    construct rows server-side; SPA receives this shape back.

    The character-offset fields are surfaced so the SPA can
    render the source-transcript view with the highlight
    range highlighted (B1.6 SPA approval UX).
    """

    workspace_id = serializers.UUIDField(source="workspace.id", read_only=True)
    source_transcript_id = serializers.UUIDField(
        source="source_transcript.id", read_only=True,
    )
    produced_composition_id = serializers.UUIDField(
        source="produced_composition.id",
        read_only=True,
        allow_null=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )

    class Meta:
        model = TranscriptHighlight
        fields = [
            "id",
            "workspace_id",
            "source_transcript_id",
            "text",
            "char_start",
            "char_end",
            "llm_reasoning",
            "status",
            "status_label",
            "produced_composition_id",
            "rejection_reason",
            "mined_at",
            "decided_at",
            "llm_model_id",
            "llm_cost_micros",
            "llm_tokens_input",
            "llm_tokens_output",
        ]
        read_only_fields = fields


class MineRequestSerializer(serializers.Serializer):
    """Body shape for ``POST /api/transcript_highlights/mine/``.

    The miner-side knobs are clamped at the helper layer; we
    don't reject out-of-range values here — just surface the
    operator's request and let
    ``select_transcript_highlights`` apply its own
    MIN/MAX_TARGET_COUNT bounds.
    """

    transcript_asset_id = serializers.UUIDField(required=True)
    target_count = serializers.IntegerField(required=False)
    max_chars = serializers.IntegerField(required=False)
