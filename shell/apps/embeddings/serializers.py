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

from .models import AudienceScope, DocumentType, KnowledgeChunk, KnowledgeDocument


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
    # SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) — positive
    # WORKSPACE fresh-create marker. Only ``"workspace"`` is a valid
    # value in this slice; CHARACTER and UNIVERSE audience states
    # continue to derive from their already-proven positive inputs
    # (``spokesperson_ids`` and ``universe`` respectively). This
    # marker exists so the SPA's "None (legacy)" gesture in
    # ``UniverseScopePicker`` (which the operator explicitly picks)
    # carries positive intent through DRF into ``ingest_*``; non-SPA
    # callers that omit the marker continue to produce
    # ``audience_scope=NULL`` — no absence-means-broadcast
    # reinterpretation. Write-only + create-only (PATCH ignores).
    # See docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §186-§204.
    audience_scope = serializers.ChoiceField(
        write_only=True,
        required=False,
        allow_null=True,
        choices=[("workspace", "Workspace-shared")],
    )

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "workspace",
            "workspace_name",
            # SESSION 261 — Universe substrate FK. Optional; NULL
            # means "legacy workspace-wide doc; visible only to
            # legacy universe=NULL teammates via the empty-M2M
            # fallback." Distinguish "absent" (no change on PATCH)
            # from "explicit null" (detach from Universe).
            "universe",
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
            # SESSION 275 — expose the reason a KD's ``is_active``
            # went False (operator delete vs system orphan archive).
            # Read-only; the two mutation paths are the DELETE view
            # and the ``pre_delete`` signal on ``Teammate``.
            "deactivated_reason",
            "chunk_count",
            "created_at",
            "updated_at",
            # write-only
            "text_content",
            "pdf_data_uri",
            "source_url_input",
            "via_serper",
            # SESSION 276 Slice 12 — WORKSPACE fresh-create marker.
            "audience_scope",
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
            # SESSION 275 — set only by DELETE view or the Teammate
            # pre_delete signal; never operator-writable.
            "deactivated_reason",
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

        # SESSION 261 — Universe consistency + M2M consistency
        # checks at the serializer level. Same rationale as the
        # workspace guard: prefer a clean 400 over letting
        # .clean() or the m2m_changed signal raise mid-save. On
        # PATCH, the "universe" key may be absent (no change) or
        # explicit null (detach) — both are handled by attrs.get().
        universe = attrs.get(
            "universe",
            self.instance.universe if self.instance else None,
        )
        if workspace and universe is not None:
            if universe.workspace_id != workspace.pk:
                raise serializers.ValidationError({
                    "universe": (
                        "Universe belongs to a different workspace than "
                        "this document."
                    ),
                })

        if spokespeople and universe is not None:
            bad_universe = [
                sp.name
                for sp in spokespeople
                if sp.universe_id != universe.pk
            ]
            if bad_universe:
                raise serializers.ValidationError({
                    "spokesperson_ids": (
                        f"Spokespeople must belong to this document's "
                        f"Universe. Bad: {bad_universe}"
                    ),
                })
        # SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) — reject
        # contradictory positive-audience payloads at the create
        # boundary rather than silently reinterpreting. Precedence
        # (per §189): spokespeople > universe > workspace marker >
        # NULL. If the caller sends more than one positive-audience
        # signal, that's a bug — surface it as a clean 400.
        #
        # Applied only on CREATE (``self.instance is None``); PATCH
        # ignores the marker entirely so revival / metadata edits
        # can't smuggle audience transitions through this field.
        audience_scope_intent = attrs.get("audience_scope")
        if self.instance is None and audience_scope_intent == "workspace":
            if spokespeople:
                raise serializers.ValidationError({
                    "audience_scope": (
                        "Cannot combine ``audience_scope='workspace'`` with "
                        "explicit spokespeople — the two positive-audience "
                        "signals contradict. Send one or the other."
                    ),
                })
            if universe is not None:
                raise serializers.ValidationError({
                    "audience_scope": (
                        "Cannot combine ``audience_scope='workspace'`` with "
                        "an explicit Universe — the two positive-audience "
                        "signals contradict. Send one or the other."
                    ),
                })

        if spokespeople and universe is None:
            # Doc is legacy; spokespeople must also be legacy.
            bad_legacy = [
                sp.name for sp in spokespeople if sp.universe_id is not None
            ]
            if bad_legacy:
                raise serializers.ValidationError({
                    "spokesperson_ids": (
                        f"Legacy (universe=null) docs cannot include "
                        f"Universe-scoped spokespeople. Bad: {bad_legacy}"
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
        # SESSION 261 — Universe scope from the payload. NULL /
        # absent means "legacy workspace-wide"; a supplied Universe
        # scopes the doc to that world.
        universe = validated_data.get("universe")

        text = (validated_data.get("text_content") or "").strip()
        pdf_uri = (validated_data.get("pdf_data_uri") or "").strip()
        source_url = (validated_data.get("source_url_input") or "").strip()
        via_serper = bool(validated_data.get("via_serper") or False)
        # SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) —
        # positive WORKSPACE fresh-create marker. Only ``"workspace"``
        # is a valid value; contradiction with spokespeople / universe
        # rejected in ``validate()`` above. Forwarded to ``ingest_*``
        # as ``workspace_shared_intent=True`` when present.
        workspace_shared_intent = (
            validated_data.get("audience_scope") == "workspace"
        )

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
                    universe=universe,
                    workspace_shared_intent=workspace_shared_intent,
                )
            except ingestion.pdf.PdfExtractionError as exc:
                raise serializers.ValidationError({
                    "pdf_data_uri": f"PDF extraction failed: {exc}",
                })
            except ingestion.OrphanRevivalRejected as exc:
                raise serializers.ValidationError({
                    "spokesperson_ids": str(exc),
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
                    universe=universe,
                    workspace_shared_intent=workspace_shared_intent,
                )
            except ingestion.url_fetch.UrlFetchError as exc:
                raise serializers.ValidationError({
                    "source_url_input": f"URL fetch failed: {exc}",
                })
            except ingestion.OrphanRevivalRejected as exc:
                raise serializers.ValidationError({
                    "spokesperson_ids": str(exc),
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
            try:
                result = ingestion.ingest_text(
                    workspace=workspace,
                    title=title,
                    content=text,
                    document_type=doc_type,
                    spokespeople=spokespeople,
                    created_by=created_by,
                    universe=universe,
                    workspace_shared_intent=workspace_shared_intent,
                )
            except ingestion.OrphanRevivalRejected as exc:
                raise serializers.ValidationError({
                    "spokesperson_ids": str(exc),
                })

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
        # SESSION 276 Slice 14 / Delta Stage 3C-2 (Q-276-28) —
        # explicit-empty-spokespeople guard for PATCH on active
        # CHARACTER KDs. Symmetric with the Slice 13 ``/detach/``
        # final-detach guard at ``apps/embeddings/views.py``
        # ``_toggle_spokesperson``. The invariant is:
        #
        #     ``audience_scope=CHARACTER`` requires at least one
        #     spokesperson at all times while active.
        #
        # Rule shape: reject any PATCH that explicitly supplies
        # ``spokesperson_ids=[]`` (source-mapped to ``spokespeople``
        # in ``validated_data``) on an active CHARACTER KD, regardless
        # of the current M2M size. This is stricter than "reject only
        # the final detach" — the invariant target is the resulting
        # row shape (CHARACTER + empty M2M is malformed), not the
        # number of members going in.
        #
        # Distinguishing explicit-empty from omission is load-bearing:
        # ``validated_data.get("spokespeople")`` collapses
        # ``None``/``[]``/absent into the same falsy value, so we use
        # ``"spokespeople" in validated_data`` to detect a positive
        # empty-list payload.
        #
        # Guard runs at the TOP of ``update()`` — after
        # ``is_valid()``/``run_validation`` has fully completed but
        # BEFORE any field mutation on ``instance``. This placement is
        # load-bearing for two reasons:
        #
        #   1. Raising here bypasses DRF's serializer-level
        #      ``as_serializer_error()`` normalization (which wraps
        #      dict values in lists for field-error rendering). The
        #      raised ``ValidationError.detail`` is rendered by the
        #      global exception handler as-is — matching the Slice 13
        #      ``/detach/`` guard's response shape exactly. Load-
        #      bearing for the ``test_slice14_error_code_matches_
        #      slice13_detach_guard`` byte-identical-code assertion.
        #
        #   2. All subsequent ``update()`` code (title assign, universe
        #      preflight, text_content re-ingest, ``.save()``,
        #      ``.spokespeople.set()``) runs sequentially AFTER this
        #      check. Raising here guarantees NO partial field
        #      mutation persists alongside a rejected audience payload
        #      (test H). If the guard were in ``validate()``, the same
        #      atomicity would apply — but the list-wrapping breaks
        #      contract symmetry with Slice 13.
        #
        # Only fires on PATCH (``update()`` is only called on PATCH
        # for existing instances). Only fires when
        # ``instance.audience_scope == CHARACTER`` — legacy NULL rows
        # retain existing serializer behavior (Slice 13 carve-out;
        # real DB has ZERO NULL+non-empty-M2M rows).
        #
        # Reuses the Slice 13 ``code`` string byte-identically for
        # SPA + external-client discrimination symmetry across
        # ``/detach/`` and PATCH mutation surfaces. See
        # docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md
        # §230-§252.
        if (
            "spokespeople" in validated_data
            and validated_data["spokespeople"] == []
            and instance.is_active
            and instance.audience_scope == AudienceScope.CHARACTER
        ):
            raise serializers.ValidationError({
                "code": "final_character_detach_requires_audience_decision",
                "detail": (
                    "This knowledge needs at least one character unless "
                    "you choose a different audience or archive it."
                ),
            })

        # SESSION 276 Slice 15 / Delta Stage 3C-3 (Q-276-29) — narrow
        # shape-preservation guards for Universe PATCH on active shared-
        # canon rows. Two Delta-invariant violations are reachable
        # today via ``PATCH {"universe": ...}`` on non-CHARACTER rows
        # (existing M2M-orphan preflight at ``:567-579`` only covers
        # cross-Universe consistency for M2M-carrying rows, not
        # audience-shape preservation for shared canon):
        #
        #   Guard #1 — ``audience_scope=UNIVERSE`` + ``universe=None``
        #     Violates Slice 4 §52 invariant #2 (UNIVERSE requires
        #     universe non-NULL). Would leave the row in the Slice 4
        #     §51 row-#5 malformed shape.
        #
        #   Guard #2 — ``audience_scope=WORKSPACE`` + ``universe non-NULL``
        #     Violates Slice 4 §52 invariant #3 (WORKSPACE requires
        #     universe NULL). Would leave the row in the §51 row-#7
        #     malformed shape.
        #
        # Slice 15 caller inventory (audit doc §257): ZERO SPA
        # callers, ZERO backend callers, ZERO scripts PATCH
        # ``universe`` on an existing KD today. These guards are
        # therefore purely defensive against future / external
        # callers; they cannot break any current operator gesture.
        #
        # Guards are shape-preservation, NOT audience-transition. They
        # do NOT auto-transition ``audience_scope`` (that would be
        # exactly the "absence-means-audience-change" anti-pattern
        # Delta was introduced to eliminate). To move a UNIVERSE row
        # to WORKSPACE or vice versa, a future slice must design an
        # explicit audience-transition contract with positive operator
        # intent — see §274 for the deferred question.
        #
        # Placed at top of ``update()`` (post-``is_valid()``) so DRF's
        # global exception handler renders ``.detail`` as-is, matching
        # the Slice 13/14 error-shape contract byte-identically. The
        # ``code`` strings are new (not the CHARACTER-specific Slice
        # 13/14 code) — they describe distinct invariants and clients
        # should discriminate them separately.
        #
        # Both guards run BEFORE the M2M-orphan preflight below, so a
        # payload that combines a shape-violating Universe change
        # with a spokespeople change rejects on the shape-invariant
        # first (unrelated fields do not partially persist).
        if (
            "universe" in validated_data
            and instance.is_active
        ):
            new_universe_val = validated_data["universe"]
            if (
                instance.audience_scope == AudienceScope.UNIVERSE
                and new_universe_val is None
            ):
                raise serializers.ValidationError({
                    "code": "universe_audience_row_requires_universe",
                    "detail": (
                        "This knowledge is shared with everyone in a "
                        "specific World. Removing the World would leave "
                        "it without a defined audience. Choose a "
                        "different World, or delete this knowledge "
                        "instead."
                    ),
                })
            if (
                instance.audience_scope == AudienceScope.WORKSPACE
                and new_universe_val is not None
            ):
                raise serializers.ValidationError({
                    "code": "workspace_audience_row_forbids_universe",
                    "detail": (
                        "This knowledge is shared workspace-wide. "
                        "Assigning it to a specific World would change "
                        "who can see it. That kind of audience change "
                        "requires a dedicated audience action, not a "
                        "scope edit."
                    ),
                })

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
        # SESSION 276 Slice 12 — ``audience_scope`` write-only marker
        # is create-only; PATCH must ignore it silently. Audience-
        # transition PATCH semantics are deferred to a future slice
        # with its own falsifiable question.
        validated_data.pop("audience_scope", None)

        text_content = validated_data.pop("text_content", None)
        content_changed = False
        changed_fields: list[str] = []

        if "title" in validated_data:
            instance.title = validated_data["title"]
            changed_fields.append("title")

        # SESSION 261 — Universe reassignment on PATCH. The
        # serializer's validate() already ran the Universe-workspace
        # + Universe-M2M guards; this just persists the FK change.
        # Explicit ``None`` in the payload detaches from the
        # Universe (returns to legacy). Absent key = no change.
        if "universe" in validated_data:
            new_universe = validated_data["universe"]
            # Additional M2M orphan preflight for the reassignment
            # path: if any existing attach row would become cross-
            # Universe, reject with a 400 pointing at the offending
            # rows. Mirrors the SPA universe-move-preview contract.
            if instance.pk:
                bad = instance.spokespeople.exclude(
                    universe_id=(new_universe.pk if new_universe else None),
                )
                if bad.exists():
                    names = [sp.name for sp in bad[:5]]
                    raise serializers.ValidationError({
                        "universe": (
                            f"Reassigning would orphan existing spokesperson "
                            f"attach rows: {names}. Reassign or detach them "
                            f"first."
                        ),
                    })
            instance.universe = new_universe
            changed_fields.append("universe")

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
