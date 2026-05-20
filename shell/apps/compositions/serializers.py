"""DRF serializers for V15 recipe + composition REST surface.

SESSION 144 / V15.0. Three shapes:

* ``RecipeSerializer`` — read-only metadata for the gallery.
  Sourced from ``apps.compositions.recipes.RECIPES``.
* ``CompositionStepSerializer`` / ``AssetSerializer`` — nested
  read shapes for composition detail responses.
* ``CompositionSerializer`` — read shape for list + detail;
  the create endpoint takes a separate body (kind + workspace
  + params) handled directly in the view.

The create flow is intentionally NOT a ``ModelSerializer.save``
because the composition is built by a starter callable, not a
direct model create. The serializer here is read-shape only.
"""
from __future__ import annotations

from rest_framework import serializers

from .assets import compute_storage_health
from .models import Asset, Composition, CompositionStep
from .recipes import list_recipes


class RecipeSerializer(serializers.Serializer):
    """Read-only metadata for one recipe.

    Output mirrors ``Recipe.to_json()``; the serializer exists
    so the viewset can use the standard DRF response shape.
    """

    kind = serializers.CharField()
    display_name = serializers.CharField()
    family = serializers.CharField()
    description = serializers.CharField()
    fields = serializers.ListField(child=serializers.DictField())

    @classmethod
    def all(cls) -> list[dict]:
        return [r.to_json() for r in list_recipes()]


class AssetSerializer(serializers.ModelSerializer):
    """Compact asset shape for composition responses."""

    class Meta:
        model = Asset
        fields = (
            "id",
            "asset_type",
            "file_path",
            "duration_ms",
            "width",
            "height",
            "mime_type",
            "size_bytes",
            "cost_micros",
            "created_at",
        )
        read_only_fields = fields


class ImageAssetSerializer(serializers.ModelSerializer):
    """W11.6.2 — read shape for the ``/api/images/`` surface.

    Surfaces the image-specific fields added in W11.6.1
    (purpose / model / style_preset / prompt / negative_prompt /
    aspect_ratio / spokesperson) alongside the shared Asset
    fields. Excludes ``inline_content`` (always empty for images)
    and ``source_spec`` (composition-runtime provenance, not
    relevant to the operator-facing image library).
    """

    workspace = serializers.PrimaryKeyRelatedField(read_only=True)
    spokesperson = serializers.PrimaryKeyRelatedField(read_only=True)
    composition = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Asset
        fields = (
            "id",
            "workspace",
            "asset_type",
            "file_path",
            "mime_type",
            "width",
            "height",
            "size_bytes",
            "cost_micros",
            "composition",
            # W11.6.1 image-specific fields
            "purpose",
            "model",
            "style_preset",
            "prompt",
            # W11.6.4 — original operator subject (pre-composition)
            # for the Regenerate CTA.
            "subject",
            # W11.6.5.1 — operator-facing label surfaced in
            # pickers and library grid.
            "title",
            "negative_prompt",
            "aspect_ratio",
            "spokesperson",
            "created_at",
        )
        read_only_fields = fields


class CompositionListSerializer(serializers.ModelSerializer):
    """Light row shape for ``GET /api/compositions/``.

    Mirrors ``OverviewComposition`` in ``apps/workspace/serializers.py``
    so the SPA can reuse the same row component for the Videos library
    and the dashboard activity feed. Skips the heavy ``steps`` /
    ``produced_assets`` / ``knowledge_docs_used`` payload — the
    detail endpoint serves those.
    """

    spokesperson_id = serializers.UUIDField(
        source="spokesperson.id", read_only=True,
    )
    spokesperson_name = serializers.CharField(
        source="spokesperson.name", read_only=True,
    )
    final_asset_id = serializers.SerializerMethodField()

    class Meta:
        model = Composition
        fields = (
            "id",
            "name",
            "template_kind",
            "status",
            "mock_mode",
            "cost_actual_micros",
            "verification_status",
            "spokesperson_id",
            "spokesperson_name",
            "final_asset_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_final_asset_id(self, obj) -> str | None:
        return str(obj.final_asset_id) if obj.final_asset_id else None


class CompositionStepSerializer(serializers.ModelSerializer):
    """One step in a composition's plan."""

    output_asset = AssetSerializer(read_only=True)

    class Meta:
        model = CompositionStep
        fields = (
            "id",
            "position",
            "primitive",
            "status",
            "inputs",
            "params",
            "cost_estimate_micros",
            "cost_actual_micros",
            "error_message",
            "output_asset",
        )
        read_only_fields = fields


class CompositionSerializer(serializers.ModelSerializer):
    """Composition read shape with nested steps + final asset."""

    steps = CompositionStepSerializer(many=True, read_only=True)
    final_asset = AssetSerializer(read_only=True)
    knowledge_docs_used = serializers.SerializerMethodField()
    # A8 (SESSION 192) — every Asset emitted by this composition's
    # steps. Light shape; the SPA links each entry to the A6
    # detail view (`/workspace/assets/<id>`). Closes the
    # Asset Library v1 cross-link between the Composition surface
    # and the Asset surface (F-arc-style lineage).
    produced_assets = serializers.SerializerMethodField()

    class Meta:
        model = Composition
        fields = (
            "id",
            "workspace",
            "spokesperson",
            "name",
            "template_kind",
            "status",
            "mock_mode",
            "cost_estimate_micros",
            "cost_actual_micros",
            "knowledge_chunk_ids",
            "knowledge_docs_used",
            "error_message",
            "created_at",
            "updated_at",
            "steps",
            "final_asset",
            "produced_assets",
            # K6.4 v1.1 — verifier surface for the SPA
            "verification_warnings",
            "rejected_synthesis",
            # K6.4 v1.2 — verification_status badge
            "verification_status",
            # K6.6 — synthesized brief on successful renders
            "synthesized_brief",
        )
        read_only_fields = fields

    def get_produced_assets(self, obj) -> list[dict]:
        """A8 — light list of every Asset emitted by this
        composition's pipeline. Includes the final_asset; the
        SPA panel labels which one is final. Ordered by
        Asset.created_at (oldest first) so step-by-step pipeline
        outputs read top-to-bottom on the page."""
        assets = list(
            obj.produced_assets.all().order_by("created_at")
        )
        final_asset_id = (
            str(obj.final_asset.id) if obj.final_asset_id else None
        )
        return [
            {
                "id": str(a.id),
                "asset_type": a.asset_type,
                "role": a.role,
                "title": a.title,
                "file_path": a.file_path,
                "storage_health": compute_storage_health(a),
                "is_final": str(a.id) == final_asset_id,
            }
            for a in assets
        ]

    def get_knowledge_docs_used(self, obj):
        """F6 (workspace fabric) — resolve the K6-populated
        knowledge_chunk_ids JSON list into a doc-level
        summary [{id, title, chunk_count}]. Empty list when
        the composition didn't use knowledge. Resolution
        goes through the sanctioned retrieval module so K0
        contract rule 2 stays intact."""
        chunk_ids = obj.knowledge_chunk_ids or []
        if not chunk_ids:
            return []
        # Lazy import to avoid pulling the embeddings app at
        # module-load time (V1's signal also lazy-imports).
        from apps.embeddings.retrieval import resolve_chunk_ids_to_docs

        return resolve_chunk_ids_to_docs(
            [str(cid) for cid in chunk_ids],
            workspace=obj.workspace,
        )
