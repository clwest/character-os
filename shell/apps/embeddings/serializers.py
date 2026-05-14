"""DRF serializers for the knowledge layer.

SESSION 138 / K4. The ViewSet drives create/list/detail
through this serializer; create dispatches to
``ingestion.ingest_text`` or ``ingestion.ingest_pdf`` based
on which write-only payload field is supplied.

Pure JSON in, pure JSON out (same rule as the wizard +
media-engine contract): PDF uploads arrive as base64 data
URIs, not multipart form data.
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from rest_framework import serializers

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson

from .models import DocumentType, KnowledgeDocument


# Cap the inbound PDF payload at 10 MB. The base64 encoded form
# is ~33% larger than the raw bytes, so a 10 MB base64 string
# is roughly a 7.5 MB PDF. Reasonable v1 ceiling — anything
# larger should be split into multiple docs anyway.
PDF_MAX_BYTES = 10 * 1024 * 1024
PDF_DATA_URI_PREFIX = "data:application/pdf;base64,"


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Read + write surface for KnowledgeDocument.

    Read side: identity + status + ingest provenance + chunk
    count + attached spokespeople. The chunk-level vectors are
    deliberately not exposed (they're huge and only useful to
    the retrieval surface).

    Write side: three write-only fields disambiguate the input
    shape — ``text_content`` for paste, ``pdf_data_uri`` for
    upload, ``spokesperson_ids`` for the M2M. Exactly one of
    ``text_content`` or ``pdf_data_uri`` must be supplied on
    create.
    """

    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    chunk_count = serializers.SerializerMethodField()
    spokesperson_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Spokesperson.objects.all(),
        source="spokespeople",
        required=False,
    )

    # Write-only inputs — disambiguate the ingest path.
    text_content = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        style={"base_template": "textarea.html"},
    )
    pdf_data_uri = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=PDF_MAX_BYTES * 2,  # base64 inflates ~33%; loose cap
        trim_whitespace=False,
    )

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "spokespeople",
            "spokesperson_ids",
            "title",
            "document_type",
            "content_hash",
            "source_url",
            "source_metadata",
            "ingested_via",
            "status",
            "error_message",
            "is_active",
            "chunk_count",
            "created_at",
            "updated_at",
            # write-only
            "text_content",
            "pdf_data_uri",
        ]
        read_only_fields = [
            "id",
            "workspace_name",
            "spokespeople",
            "content_hash",
            "source_url",
            "source_metadata",
            "status",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
            # ingested_via is derived from which payload field is set
            "ingested_via",
            # document_type is derived from the same branching
            "document_type",
        ]

    def get_chunk_count(self, obj: KnowledgeDocument) -> int:
        # Reverse FK count — fine even for unprocessed docs (0).
        return obj.chunks.count()

    # ---- validation -------------------------------------

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Only on create do we require an input payload. Updates
        # don't re-ingest — they edit metadata only (title,
        # spokespeople M2M).
        if self.instance is None:
            text = (attrs.get("text_content") or "").strip()
            pdf = (attrs.get("pdf_data_uri") or "").strip()

            if bool(text) == bool(pdf):
                raise serializers.ValidationError(
                    "Supply exactly one of ``text_content`` or "
                    "``pdf_data_uri`` — not both, not neither."
                )

            if pdf:
                self._validate_pdf_data_uri(pdf)

        # Cross-workspace spokesperson check at the serializer
        # level — surfaces a clean 400 instead of letting the
        # m2m_changed signal raise mid-create.
        workspace: Workspace | None = attrs.get("workspace") or (
            self.instance.workspace if self.instance else None
        )
        spokespeople = attrs.get("spokespeople") or []
        if workspace and spokespeople:
            bad = [sp.name for sp in spokespeople if sp.workspace_id != workspace.pk]
            if bad:
                raise serializers.ValidationError({
                    "spokesperson_ids": (
                        f"Spokespeople must belong to the document's "
                        f"workspace. Bad: {bad}"
                    ),
                })

        return attrs

    def _validate_pdf_data_uri(self, value: str) -> None:
        if not value.startswith(PDF_DATA_URI_PREFIX):
            raise serializers.ValidationError({
                "pdf_data_uri": (
                    f"Expected ``{PDF_DATA_URI_PREFIX}<base64>``. "
                    "Other MIME prefixes are not accepted in v1."
                ),
            })
        try:
            decoded = base64.b64decode(value[len(PDF_DATA_URI_PREFIX) :], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise serializers.ValidationError({
                "pdf_data_uri": f"Invalid base64: {exc}",
            })
        if len(decoded) > PDF_MAX_BYTES:
            raise serializers.ValidationError({
                "pdf_data_uri": (
                    f"PDF exceeds {PDF_MAX_BYTES // (1024*1024)} MB cap "
                    f"(got {len(decoded) // (1024*1024)} MB)."
                ),
            })
        if len(decoded) < 100:
            # PDFs always have a sizable header; <100 bytes is
            # almost certainly truncated or corrupt.
            raise serializers.ValidationError({
                "pdf_data_uri": "PDF payload too small to be valid.",
            })

    # ---- write path -------------------------------------

    def create(self, validated_data: dict[str, Any]) -> KnowledgeDocument:
        """Branches into ``ingest_text`` or ``ingest_pdf`` based
        on which payload was supplied. The actual chunking +
        embedding fires asynchronously via Celery; this returns
        the ``pending`` document immediately."""
        from . import ingestion
        from .tasks import embed_document

        workspace: Workspace = validated_data["workspace"]
        title: str = validated_data["title"]
        spokespeople: list[Spokesperson] = list(validated_data.get("spokespeople") or [])

        text = (validated_data.get("text_content") or "").strip()
        pdf_uri = (validated_data.get("pdf_data_uri") or "").strip()

        request = self.context.get("request")
        created_by = request.user if request and request.user.is_authenticated else None

        if pdf_uri:
            payload = base64.b64decode(pdf_uri[len(PDF_DATA_URI_PREFIX) :])
            try:
                result = ingestion.ingest_pdf(
                    workspace=workspace,
                    title=title,
                    payload=payload,
                    spokespeople=spokespeople,
                    created_by=created_by,
                )
            except ingestion.pdf.PdfExtractionError as exc:
                raise serializers.ValidationError({
                    "pdf_data_uri": f"PDF extraction failed: {exc}",
                })
        else:
            # Heuristic: if the text starts with ``#`` or contains
            # ``\n## `` it's probably markdown; everything else is
            # plain text. Operator can override later via PATCH.
            doc_type = (
                DocumentType.MARKDOWN
                if (text.startswith("#") or "\n## " in text)
                else DocumentType.TEXT
            )
            result = ingestion.ingest_text(
                workspace=workspace,
                title=title,
                content=text,
                document_type=doc_type,
                spokespeople=spokespeople,
                created_by=created_by,
            )

        # Fire the async embedding pass only on fresh ingests —
        # dedup hits already have chunks. Re-fetch afterward so
        # that in eager-Celery mode (tests) the serializer
        # surfaces the post-task state. In production Celery the
        # refresh is a no-op — status stays ``pending`` until
        # the real worker picks the task up.
        if not result.deduped:
            embed_document.delay(str(result.document.pk))
            result.document.refresh_from_db()

        return result.document

    def update(self, instance: KnowledgeDocument, validated_data: dict[str, Any]) -> KnowledgeDocument:
        """Update path is intentionally narrow — title + M2M only.
        Editing content means re-ingesting (delete + create)."""
        if "text_content" in validated_data or "pdf_data_uri" in validated_data:
            raise serializers.ValidationError(
                "Edit content by deleting + re-ingesting. "
                "Updates only touch title + spokespeople."
            )
        if "title" in validated_data:
            instance.title = validated_data["title"]
            instance.save(update_fields=["title", "updated_at"])
        if "spokespeople" in validated_data:
            instance.spokespeople.set(validated_data["spokespeople"])
        return instance
