"""DRF viewset for KnowledgeDocument.

SESSION 138. CRUD on workspace-scoped knowledge.

* GET    /api/knowledge/                   list (workspace=<uuid> filter; SESSION 138 / K4)
* POST   /api/knowledge/                   create (paste OR PDF; K4)
* GET    /api/knowledge/<id>/              detail (K4)
* PATCH  /api/knowledge/<id>/              update title + spokespeople (K4)
* DELETE /api/knowledge/<id>/              soft delete (is_active=False; K4)
* POST   /api/knowledge/<id>/attach/       {spokesperson_id: ...} (K5)
* POST   /api/knowledge/<id>/detach/       {spokesperson_id: ...} (K5)

The list view defaults to the requesting user's accessible
workspaces; a ``?workspace=<uuid>`` filter narrows to one.
``?spokesperson=<uuid>`` filters to docs visible to that
spokesperson (empty M2M OR M2M includes them) — same
visibility filter ``retrieve_for_teammate`` uses, so the
SPA's spokesperson Knowledge tab shows exactly what render-
time RAG would draw from.

Workspace scoping is enforced by ``IsWorkspaceMember`` +
queryset filter — the K2 retrieval-surface privacy contract
is unaffected because the chunk table is only queried through
``apps.embeddings.retrieval``.
"""
from __future__ import annotations

import logging

from django.db.models import Q
from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.spokespeople.models import Teammate
from character_os.permissions import IsWorkspaceMember

from .models import AudienceScope, DeactivationReason, KnowledgeDocument
from .serializers import (
    KnowledgeDocumentDetailSerializer,
    KnowledgeDocumentSerializer,
)

logger = logging.getLogger(__name__)


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """Workspace-scoped CRUD on KnowledgeDocument."""

    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsWorkspaceMember]

    def get_serializer_class(self):
        """SESSION 140 / K4.1 — detail responses include chunks
        so the operator can verify what got captured. List
        responses keep the lighter serializer."""
        if self.action == "retrieve":
            return KnowledgeDocumentDetailSerializer
        return KnowledgeDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return KnowledgeDocument.objects.none()

        qs = (
            KnowledgeDocument.objects.filter(
                workspace__memberships__user=user,
                is_active=True,
            )
            .select_related("workspace")
            .prefetch_related("spokespeople")
            .distinct()
        )

        # Optional workspace narrowing.
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)

        # SESSION 138 / K5 — optional spokesperson visibility filter.
        # SESSION 276 / Slice 17 / Delta Stage 5B (Q-276-31) —
        # Cut over to the positive ``audience_scope``-keyed predicate,
        # mirroring the Slice 16 retrieval cutover at
        # ``retrieval.py:194-224``. Semantics per Delta scope:
        #
        # * CHARACTER — visible if the requesting spokesperson is in
        #   the doc's M2M.
        # * UNIVERSE — visible (Universe-scoped docs are broadcast to
        #   teammates in that Universe; the ``?universe=`` filter below
        #   provides operator-explicit narrowing on top of this).
        # * WORKSPACE — visible (workspace-shared canon).
        # * NULL fallback — preserves legacy shape-derived semantics
        #   byte-identically for the 10 unresolved historical rows the
        #   Stage-2 migration intentionally left as ``audience_scope=NULL``.
        # * NONE + any future unknown ``audience_scope`` value — fail
        #   closed (no matching branch). NONE is defense in depth on top
        #   of the ``is_active=True`` filter above; unknown values must
        #   NOT silently receive legacy broadcast (load-bearing NULL
        #   contract; see retrieval.py:216-269 for the sibling constraint).
        #
        # Universe scoping is intentionally NOT auto-derived from the
        # requesting spokesperson (that is retrieval.py's contract).
        # The SPA list surface uses an explicit ``?universe=`` query
        # param, applied below, so operators can narrow independently.
        #
        # Real-DB equivalence: SESSION 276 Slice 17 §… — 16/16 real
        # teammates return byte-identical doc-ID sets under the legacy
        # and Delta predicates. Zero divergences on any scope class.
        spokesperson_id = self.request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(
                (
                    Q(audience_scope__isnull=True)
                    & (
                        Q(spokespeople__isnull=True)
                        | Q(spokespeople=spokesperson_id)
                    )
                )
                | Q(
                    audience_scope=AudienceScope.CHARACTER,
                    spokespeople=spokesperson_id,
                )
                | Q(audience_scope=AudienceScope.UNIVERSE)
                | Q(audience_scope=AudienceScope.WORKSPACE)
            ).distinct()

        # Optional doc-type filter (useful for the SPA's tab UI).
        doc_type = self.request.query_params.get("document_type")
        if doc_type:
            qs = qs.filter(document_type=doc_type)

        # SESSION 261 — optional Universe filter. ``?universe=<uuid>``
        # narrows to that Universe's docs; ``?universe=none`` narrows
        # to legacy (universe=NULL) docs. No silent auto-scoping —
        # the SPA passes the value the operator picked.
        universe_param = self.request.query_params.get("universe")
        if universe_param:
            if universe_param.strip().lower() == "none":
                qs = qs.filter(universe__isnull=True)
            else:
                qs = qs.filter(universe_id=universe_param)

        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete — flip ``is_active=False`` instead of
        dropping the row. The chunk rows stay so the retrieval
        path's ``is_active=True`` filter is the gatekeeper.
        Hard-delete is an admin-only operation.

        SESSION 275 — also stamps ``deactivated_reason=OPERATOR_DELETE``
        so the safe-revival gate in ``ingestion._persist`` and any
        future audit UI can distinguish operator-initiated soft-deletes
        from system-initiated orphan-archives set by the ``pre_delete``
        signal on ``Teammate``. See
        ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``.
        """
        instance = self.get_object()
        instance.is_active = False
        instance.deactivated_reason = DeactivationReason.OPERATOR_DELETE
        instance.save(
            update_fields=["is_active", "deactivated_reason", "updated_at"],
        )
        return Response(status=drf_status.HTTP_204_NO_CONTENT)

    # ---- M2M toggle actions (K5) -----------------------

    @action(detail=True, methods=["post"])
    def attach(self, request, *args, **kwargs):
        """Attach a single spokesperson to this doc's visibility
        M2M. Body: ``{"spokesperson_id": "<uuid>"}``. Idempotent —
        attaching an already-attached spokesperson is a no-op
        that returns the updated doc.

        Cross-workspace attaches are rejected by the
        m2m_changed signal in ``apps.embeddings.signals``;
        we surface that as a 400 instead of a 500.
        """
        return self._toggle_spokesperson(request, attach=True)

    @action(detail=True, methods=["post"])
    def detach(self, request, *args, **kwargs):
        """Detach a single spokesperson from this doc's M2M.
        Body: ``{"spokesperson_id": "<uuid>"}``. Idempotent —
        detaching an unattached spokesperson is a no-op.

        SESSION 276 Slice 13 / Delta Stage 3C-1 (refined Q-276-27):
        an attempt to detach the LAST remaining spokesperson from an
        active ``audience_scope=CHARACTER`` KD is rejected with a
        structured 4xx BEFORE any M2M mutation. Under legacy
        retrieval such a transition silently broadened the KD to a
        workspace-wide broadcast (Slice 3 §37.J); under Delta the
        row would also be malformed (Slice 4 §51 row #3 — CHARACTER
        + empty M2M). The operator must instead choose a different
        audience or archive/delete the document — those alternative
        transitions belong to later slices and are NOT wired here.
        Multi-character detach (count>1) is unchanged: narrowing
        {A,B} → {B} remains a legitimate CHARACTER-scoped audience
        change.
        """
        return self._toggle_spokesperson(request, attach=False)

    def _toggle_spokesperson(self, request, *, attach: bool):
        from django.core.exceptions import ValidationError as DjangoValidationError

        doc = self.get_object()
        sp_id = request.data.get("spokesperson_id")
        if not sp_id:
            raise ValidationError({"spokesperson_id": "Required."})

        try:
            sp = Teammate.objects.get(pk=sp_id)
        except Teammate.DoesNotExist as exc:
            raise NotFound(f"Teammate {sp_id} not found.") from exc

        if sp.workspace_id != doc.workspace_id:
            raise ValidationError({
                "spokesperson_id": (
                    f"Teammate {sp.name!r} is in another workspace."
                ),
            })

        # SESSION 276 Slice 13 / Delta Stage 3C-1 (refined Q-276-27) —
        # final-character detach guard. Reject BEFORE any M2M mutation
        # when the request would leave an active CHARACTER KD with an
        # empty spokespeople set. Scope: ``audience_scope=CHARACTER``
        # only (positive evidence that this KD is character-scoped).
        # Legacy transitional NULL-audience rows are NOT guarded here
        # because inferring intent from absence is exactly what Delta
        # was introduced to eliminate; the real DB currently contains
        # ZERO NULL+non-empty-M2M rows (Slice 7 backfill classified
        # every M2M-carrying row as CHARACTER), so this guard covers
        # 100% of production character-scoped KDs. Test fixtures that
        # create KDs directly via ``KnowledgeDocument.objects.create``
        # without going through Slice 10's CREATE stamp path may land
        # at NULL+M2M — those retain existing legacy detach behavior
        # deliberately.
        if (
            not attach
            and doc.audience_scope == AudienceScope.CHARACTER
            and doc.spokespeople.filter(pk=sp.pk).exists()
            and doc.spokespeople.count() == 1
        ):
            raise ValidationError({
                "code": "final_character_detach_requires_audience_decision",
                "detail": (
                    f"{sp.name!r} is the last character using this "
                    f"knowledge. Removing them would leave the knowledge "
                    f"without an audience. Choose a new audience or "
                    f"archive/delete the knowledge instead."
                ),
            })

        try:
            if attach:
                doc.spokespeople.add(sp)
            else:
                doc.spokespeople.remove(sp)
        except DjangoValidationError as exc:
            # The m2m_changed signal raised — translate to DRF.
            raise ValidationError({"spokesperson_id": list(exc.messages)}) from exc

        serializer = self.get_serializer(doc)
        return Response(serializer.data)

    # ---- search discovery (K7) -------------------------

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        """Serper-backed search. Body: ``{"q": "<query>", "top_k": N}``.

        Returns ``{"results": [{title, url, snippet, position}, ...]}``.
        Not workspace-scoped — search results aren't documents
        yet. Operator picks one → SPA POSTs to ``/api/knowledge/``
        with the URL.

        Authenticated-only. Cached for 1 hour by sha256(query).
        ``SERPER_FORCE_MOCK=1`` returns deterministic stubs
        without hitting the API.
        """
        from . import serper

        query = (request.data.get("q") or "").strip()
        if not query:
            raise ValidationError({"q": "Required."})
        top_k = request.data.get("top_k") or serper.DEFAULT_TOP_K

        try:
            results = serper.search(query, top_k=top_k)
        except ValueError as exc:
            raise ValidationError({"q": str(exc)}) from exc
        except serper.SerperError as exc:
            # 502 — upstream failure. Operator should retry or
            # paste a URL directly.
            return Response(
                {"detail": str(exc)},
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        from dataclasses import asdict as _asdict
        return Response({
            "query": query,
            "results": [_asdict(r) for r in results],
        })

    # ---- compositions reverse (F7, workspace fabric arc) -

    @action(detail=True, methods=["get"], url_path="compositions")
    def compositions(self, request, *args, **kwargs):
        """Compositions that drew on chunks from this doc.

        Inverse of F6's citations panel — the doc-detail page
        ``/workspace/knowledge/<id>`` consumes this to render
        "Used in N compositions." Workspace-scoped via the
        ViewSet's existing queryset filter.

        Implementation: pulls the doc's chunk ids via the
        sanctioned retrieval helper, then walks workspace
        compositions whose ``knowledge_chunk_ids`` JSON list
        intersects. Per-row chunk count surfaces how heavily
        a composition leaned on this doc.

        Returns ``{"compositions": [...]}`` ordered newest
        first; cap at 100 for v1.
        """
        from apps.compositions.models import Composition
        from apps.embeddings.retrieval import list_chunk_ids_for_document

        doc = self.get_object()  # honors IsWorkspaceMember
        doc_chunk_ids = set(list_chunk_ids_for_document(doc))
        if not doc_chunk_ids:
            return Response({"compositions": []})

        # v1 — Python-side filter. For workspace sizes this is
        # cheap (the workspace's composition count is small).
        # When this gets slow, a Postgres-native
        # ``knowledge_chunk_ids @> jsonb`` lookup is the upgrade.
        candidates = (
            Composition.objects.filter(workspace=doc.workspace)
            .select_related("spokesperson")
            .order_by("-created_at")
            .only(
                "id", "name", "template_kind", "status",
                "created_at", "knowledge_chunk_ids",
                "spokesperson",
            )
        )
        matches: list[dict] = []
        for comp in candidates:
            used_ids = doc_chunk_ids.intersection(
                {str(c) for c in (comp.knowledge_chunk_ids or [])}
            )
            if not used_ids:
                continue
            matches.append({
                "composition_id": str(comp.id),
                "composition_name": comp.name,
                "template_kind": comp.template_kind,
                "status": comp.status,
                "created_at": comp.created_at.isoformat(),
                "spokesperson_name": (
                    comp.spokesperson.name if comp.spokesperson_id else None
                ),
                "chunk_count": len(used_ids),
            })
            if len(matches) >= 100:
                break

        return Response({"compositions": matches})

    # ---- knowledge preview (F4, workspace fabric arc) ---

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request, *args, **kwargs):
        """Return doc-level summary of what `retrieve_for_teammate`
        would surface for a given query — powers the F4 preview
        panel on recipe forms.

        Body: ``{"spokesperson": <uuid>, "query": "<text>", "top_k": N?}``

        Response: ``{
            "docs_used": [{"id", "title", "chunk_count"}, ...],
            "total_chunks": int,
            "query_used": str,
        }``

        Workspace scoping derives from the spokesperson — the
        caller must be a workspace member. Best-effort per F0
        contract rule 6: any retrieval failure returns an empty
        result instead of a 500 so the SPA's preview panel
        never blocks the recipe form's submit.
        """
        from collections import Counter

        from apps.accounts.models import Membership
        from apps.embeddings.retrieval import retrieve_for_teammate
        from apps.spokespeople.models import Teammate

        sp_id = (request.data.get("spokesperson") or "").strip()
        query = (request.data.get("query") or "").strip()
        if not sp_id:
            raise ValidationError({"spokesperson": "Required."})
        if not query:
            raise ValidationError({"query": "Required."})

        top_k = request.data.get("top_k")
        try:
            top_k_int = int(top_k) if top_k is not None else 5
        except (TypeError, ValueError):
            top_k_int = 5
        top_k_int = max(1, min(top_k_int, 20))

        try:
            spokesperson = Teammate.objects.get(pk=sp_id)
        except Teammate.DoesNotExist:
            raise ValidationError({"spokesperson": "Not found."})
        if not Membership.objects.filter(
            user=request.user, workspace=spokesperson.workspace,
        ).exists():
            raise PermissionDenied("Not a member of this spokesperson's workspace.")

        # Best-effort retrieval. Any failure becomes an empty
        # result so the SPA panel can show "no preview available"
        # without surfacing an HTTP error to the operator.
        try:
            chunks = retrieve_for_teammate(
                spokesperson, query, top_k=top_k_int,
            )
        except Exception as exc:
            logger.warning(
                "knowledge preview failed for spokesperson=%s: %s",
                spokesperson.id, exc,
            )
            return Response({
                "docs_used": [],
                "total_chunks": 0,
                "query_used": query,
                "preview_failed": True,
            })

        # Group chunks by document, preserving the highest-match
        # ordering (the first time we see a doc id is its first
        # chunk's position in the result list).
        doc_order: list[str] = []
        doc_titles: dict[str, str] = {}
        counts: Counter[str] = Counter()
        for chunk in chunks:
            doc_id = str(chunk.document_id)
            if doc_id not in doc_titles:
                doc_titles[doc_id] = chunk.document.title
                doc_order.append(doc_id)
            counts[doc_id] += 1

        docs_used = [
            {
                "id": doc_id,
                "title": doc_titles[doc_id],
                "chunk_count": counts[doc_id],
            }
            for doc_id in doc_order
        ]

        return Response({
            "docs_used": docs_used,
            "total_chunks": len(chunks),
            "query_used": query,
        })
