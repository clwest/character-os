"""B2.3 — DRF serializers for the B-2 / E-arc scripts REST surface.

Four serializers:

* ``ScriptListSerializer`` — lite shape for the list view.
* ``ScriptDetailSerializer`` — full row + resolved citations
  via ``apps.embeddings.retrieval.resolve_chunk_ids_to_docs``
  (so the SPA shows "drew from doc A / doc B").
* ``CreateScriptSerializer`` — write shape for
  ``POST /api/scripts/``.
* ``RegenerateScriptSerializer`` — write shape for
  ``POST /api/scripts/<id>/regenerate/`` (all fields optional;
  the regenerate endpoint inherits prompt / opener / verifier_mode
  from the existing row when omitted).
"""
from __future__ import annotations

from rest_framework import serializers

from .models import Script


_VALID_VERIFIER_MODES = {"strict", "warn", "off"}


class _BaseScriptSerializer(serializers.ModelSerializer):
    """Shared bits between list + detail serializers."""

    workspace_id = serializers.UUIDField(source="workspace.id", read_only=True)
    spokesperson_id = serializers.UUIDField(
        source="spokesperson.id", read_only=True,
    )
    spokesperson_name = serializers.CharField(
        source="spokesperson.name", read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    verification_status_label = serializers.CharField(
        source="get_verification_status_display",
        read_only=True,
        default="",
    )
    revision_count = serializers.SerializerMethodField()
    knowledge_chunk_count = serializers.SerializerMethodField()

    def get_revision_count(self, obj: Script) -> int:
        return len(obj.revision_history or [])

    def get_knowledge_chunk_count(self, obj: Script) -> int:
        return len(obj.knowledge_chunk_ids or [])


class ScriptListSerializer(_BaseScriptSerializer):
    """Lite shape for ``GET /api/scripts/``. Excludes the
    chunky JSON fields (revision_history, verification_warnings,
    knowledge_chunk_ids) that the detail view surfaces."""

    class Meta:
        model = Script
        fields = [
            "id",
            "workspace_id",
            "spokesperson_id",
            "spokesperson_name",
            "name",
            "prompt",
            "opener",
            "draft_text",
            "model",
            "status",
            "status_label",
            "verification_status",
            "verification_status_label",
            "verifier_mode",
            "tokens_input",
            "tokens_output",
            "revision_count",
            "knowledge_chunk_count",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ScriptDetailSerializer(_BaseScriptSerializer):
    """Full row + resolved citations (rule 3 + Q-e-10).

    ``cited_documents`` resolves ``knowledge_chunk_ids`` into
    "this draft drew from doc A (3 chunks), doc B (1 chunk)"
    via F6's existing ``resolve_chunk_ids_to_docs``. The SPA
    renders this inline with the draft for the brief-mode
    panel.
    """

    cited_documents = serializers.SerializerMethodField()

    class Meta:
        model = Script
        fields = [
            "id",
            "workspace_id",
            "spokesperson_id",
            "spokesperson_name",
            "name",
            "prompt",
            "opener",
            "draft_text",
            "knowledge_chunk_ids",
            "cited_documents",
            "model",
            "tokens_input",
            "tokens_output",
            "verification_status",
            "verification_status_label",
            "verification_warnings",
            "verifier_mode",
            "revision_history",
            "revision_count",
            "knowledge_chunk_count",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_cited_documents(self, obj: Script) -> list[dict]:
        """Resolve chunk_ids → docs via F6's existing helper.
        Workspace-filtered so a leak in revision_history can't
        surface foreign-workspace doc titles.

        Defense-in-depth: filter for UUID-shaped strings before
        the resolver call. Non-UUID entries in the JSON field
        (legacy seed data, mock fixtures, future schema drift)
        return [] for that entry rather than 500-ing the detail
        endpoint.
        """
        import uuid as _uuid

        from apps.embeddings.retrieval import resolve_chunk_ids_to_docs

        valid_ids: list[str] = []
        for cid in (obj.knowledge_chunk_ids or []):
            try:
                _uuid.UUID(str(cid))
            except (ValueError, TypeError):
                continue
            valid_ids.append(str(cid))
        if not valid_ids:
            return []
        return resolve_chunk_ids_to_docs(
            valid_ids, workspace=obj.workspace,
        )


class CreateScriptSerializer(serializers.Serializer):
    """Body shape for ``POST /api/scripts/``.

    The viewset resolves the spokesperson + workspace from the
    requesting user's memberships; this serializer validates
    the operator-supplied fields.
    """

    spokesperson_id = serializers.UUIDField(required=True)
    name = serializers.CharField(
        max_length=120, allow_blank=True, default="",
    )
    prompt = serializers.CharField(min_length=1, max_length=4000)
    opener = serializers.CharField(
        max_length=280, required=False, allow_blank=True, default="",
    )
    verifier_mode = serializers.CharField(
        max_length=10, required=False, allow_blank=True, default="",
    )

    def validate_verifier_mode(self, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in _VALID_VERIFIER_MODES:
            raise serializers.ValidationError(
                f"verifier_mode must be one of {sorted(_VALID_VERIFIER_MODES)} "
                f"or blank to inherit the default."
            )
        return value


class RegenerateScriptSerializer(serializers.Serializer):
    """Body shape for ``POST /api/scripts/<id>/regenerate/``.

    All fields optional. Omitted fields inherit from the
    existing Script row before re-firing ``draft_script``.
    """

    prompt = serializers.CharField(
        min_length=1, max_length=4000, required=False, allow_blank=False,
    )
    opener = serializers.CharField(
        max_length=280, required=False, allow_blank=True,
    )
    verifier_mode = serializers.CharField(
        max_length=10, required=False, allow_blank=True,
    )

    def validate_verifier_mode(self, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in _VALID_VERIFIER_MODES:
            raise serializers.ValidationError(
                f"verifier_mode must be one of {sorted(_VALID_VERIFIER_MODES)} "
                f"or blank to inherit the default."
            )
        return value
