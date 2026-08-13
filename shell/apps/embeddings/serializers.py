"""DRF serializers for the knowledge layer.

SESSION 138 / K4. The ViewSet drives create/list/detail
through this serializer; create dispatches to
``ingestion.ingest_text`` or ``ingestion.ingest_pdf`` based
on which write-only payload field is supplied.

Pure JSON in, pure JSON out (same rule as the wizard +
media-engine contract): PDF uploads arrive as base64 data
URIs, not multipart form data.

SESSION 140 / K4.1: ``KnowledgeDocumentDetailSerializer`` adds
a chunk list to the detail response so operators can verify
what actually got captured. List responses still use the
base serializer (chunks would be a perf cliff at scale).
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from rest_framework import serializers

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate

from .models import DocumentType, KnowledgeChunk, KnowledgeDocument


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
    # Title becomes optional so URL ingests can fall back to the
    # extracted page title; the model still requires non-empty,
    # but ``_persist`` substitutes "Untitled" and ``ingest_url``
    # substitutes the page's <title> tag.
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)
    spokesperson_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Teammate.objects.all(),
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
    # SESSION 140 / K7 — URL ingest path. Writable on create only.
    # Reuses the model's ``source_url`` column for the response.
    source_url_input = serializers.URLField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=2000,
    )
    # SESSION 140 / K7 — flag set by the SPA when the URL came
    # from a serper search result rather than a direct paste.
    # Drives ``ingested_via`` on the created row.
    via_serper = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
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
            "source_url_input",
            "via_serper",
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
            url = (attrs.get("source_url_input") or "").strip()

            # Three-way XOR — exactly one must be present.
            supplied = sum(1 for v in (text, pdf, url) if v)
            if supplied != 1:
                raise serializers.ValidationError(
                    "Supply exactly one of ``text_content``, "
                    "``pdf_data_uri``, or ``source_url_input`` — "
                    "not zero, not more than one."
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
        title: str = validated_data.get("title") or ""
        spokespeople: list[Teammate] = list(validated_data.get("spokespeople") or [])

        text = (validated_data.get("text_content") or "").strip()
        pdf_uri = (validated_data.get("pdf_data_uri") or "").strip()
        source_url = (validated_data.get("source_url_input") or "").strip()
        via_serper = bool(validated_data.get("via_serper") or False)

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
        elif source_url:
            from .models import IngestedVia
            try:
                result = ingestion.ingest_url(
                    workspace=workspace,
                    url=source_url,
                    title=title,
                    spokespeople=spokespeople,
                    created_by=created_by,
                    ingested_via=IngestedVia.SERPER if via_serper else IngestedVia.PASTE,
                )
            except ingestion.url_fetch.UrlFetchError as exc:
                raise serializers.ValidationError({
                    "source_url_input": f"URL fetch failed: {exc}",
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
        """Update path: title, spokespeople M2M, and (SESSION 235,
        Chapter 6 slice-2 Beat 3) text_content.

        A ``text_content`` PATCH re-ingests in place — the same
        row keeps its id, workspace, M2M attachments, and title
        (unless title is also patched), but its
        ``processed_content`` + ``content_hash`` are recomputed
        and its chunks are dropped and re-embedded asynchronously.
        The K4 doctrine that content edits meant delete + re-
        ingest was lifted to honor Chapter 6's Beat 3 ship bar
        ("the fix loop closes on the same page"). Design lock:
        ``docs/design/CUSTOMER_JOURNEY_V1.md`` §"Chapter 6 —
        Ongoing training" §"Beat 3 — Fix the source".

        PDF and URL re-ingest are still create-only — Beat 3
        edits raw text, not source uploads. Callers that need
        to swap the source can delete + re-create.
        """
        # These write-only fields remain create-only. Editing a
        # PDF-provenance doc means editing its extracted text, not
        # re-uploading a new PDF; same for URL. Rejecting keeps
        # provenance (``document_type``, ``ingested_via``,
        # ``source_url``) intact across text edits.
        for forbidden in ("pdf_data_uri", "source_url_input"):
            if forbidden in validated_data:
                raise serializers.ValidationError({
                    forbidden: (
                        "Create-only. To swap a PDF or URL source, "
                        "delete this note and re-ingest."
                    ),
                })
        validated_data.pop("via_serper", None)

        text_content = validated_data.pop("text_content", None)
        content_changed = False
        changed_fields: list[str] = []

        if "title" in validated_data:
            instance.title = validated_data["title"]
            changed_fields.append("title")

        if text_content is not None:
            from . import ingestion
            from .models import DocumentStatus

            normalized = ingestion._normalize(text_content)
            if not normalized:
                raise serializers.ValidationError({
                    "text_content": "Cannot save empty content.",
                })

            new_hash = ingestion._content_hash(normalized)
            if new_hash != instance.content_hash:
                # (workspace, content_hash) is unique. If another
                # active-or-not doc in this workspace already owns
                # this exact content, hand back a clean 400 rather
                # than let the DB raise IntegrityError mid-save.
                clash = (
                    KnowledgeDocument.objects
                    .filter(workspace=instance.workspace, content_hash=new_hash)
                    .exclude(pk=instance.pk)
                    .exists()
                )
                if clash:
                    raise serializers.ValidationError({
                        "text_content": (
                            "Another note in this workspace already has "
                            "this exact content."
                        ),
                    })

                instance.raw_content = text_content
                instance.processed_content = normalized
                instance.content_hash = new_hash
                instance.status = DocumentStatus.PENDING
                instance.error_message = ""
                changed_fields.extend([
                    "raw_content",
                    "processed_content",
                    "content_hash",
                    "status",
                    "error_message",
                ])
                # Drop stale chunks synchronously so the retrieval
                # surface stops matching outdated text the instant
                # the operator saves. embed_document will rebuild.
                instance.chunks.all().delete()
                content_changed = True

        if changed_fields:
            changed_fields.append("updated_at")
            instance.save(update_fields=changed_fields)

        if "spokespeople" in validated_data:
            instance.spokespeople.set(validated_data["spokespeople"])

        if content_changed:
            from .tasks import embed_document
            embed_document.delay(str(instance.pk))

        return instance


# ---- SESSION 140 / K4.1 — detail view chunks ---------------


class KnowledgeChunkSerializer(serializers.ModelSerializer):
    """Per-chunk view for the operator detail page. Drops the
    vector column (huge + not human-meaningful); keeps the
    text + indexing metadata."""

    class Meta:
        model = KnowledgeChunk
        fields = [
            "id",
            "chunk_index",
            "chunk_text",
            "chunk_size",
            "overlap_size",
            "embedding_model",
            "embedding_cost_micros",
            "processing_time_ms",
        ]
        read_only_fields = fields


class KnowledgeDocumentDetailSerializer(KnowledgeDocumentSerializer):
    """Detail-view serializer. Same shape as the base list
    serializer, plus an inline list of chunks so the operator
    can verify what got captured (per K4.1 polish — answering
    "what exactly did I just ingest?").

    SESSION 235 / Chapter 6 slice-2 (Beat 3): also surfaces
    ``processed_content`` so the SPA's inline doc editor can
    prefill its textarea from the detail endpoint. Kept off the
    list serializer — a long list of ingested docs shouldn't
    ship the full body of every row.

    The base serializer stays the list serializer; chunks would
    be a perf cliff if surfaced for every row of a long list.
    """

    chunks = serializers.SerializerMethodField()

    class Meta(KnowledgeDocumentSerializer.Meta):
        fields = KnowledgeDocumentSerializer.Meta.fields + [
            "chunks",
            "processed_content",
        ]
        read_only_fields = KnowledgeDocumentSerializer.Meta.read_only_fields + [
            "chunks",
            "processed_content",
        ]

    def get_chunks(self, obj: KnowledgeDocument) -> list[dict]:
        # Reverse FK access via the parent document — already
        # scoped to this document so we never cross workspaces.
        # The K2 privacy-grep test only flags the chunk model's
        # default-manager entry point, which we deliberately
        # avoid by going through ``obj.chunks`` instead.
        qs = obj.chunks.all().order_by("chunk_index")
        return KnowledgeChunkSerializer(qs, many=True).data
