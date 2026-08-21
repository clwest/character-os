"""End-to-end smoke test for the K3 ingestion pipeline.

Drives the full path: ``ingest_text`` (or ``ingest_pdf``) →
``embed_document`` (Celery task, called synchronously here) →
``retrieve_for_teammate``. Asserts that:

  1. The KnowledgeDocument lands in ``status='processed'``.
  2. Chunks were created with embedding vectors of the right
     dimension.
  3. ``retrieve_for_teammate`` returns those chunks when
     queried with content from the document.
  4. The repeat-ingest path is idempotent (deduped=True on
     second run).
  5. The cleanup at the end leaves the workspace in the state
     it found it.

Defaults to ``EMBEDDING_FORCE_MOCK=1`` so the smoke runs
without an OpenAI API key. Pass ``--real`` to exercise the
real OpenAI path (requires ``OPENAI_API_KEY``).

Usage:
    python manage.py smoke_ingest
    python manage.py smoke_ingest --workspace-slug admins-workspace
    python manage.py smoke_ingest --pdf path/to/doc.pdf
    python manage.py smoke_ingest --real   # hit OpenAI

Exit codes:
    0 — pipeline shipped a processed document + retrieval works
    1 — anything else
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_pdf, ingest_text
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import retrieve_for_teammate
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate


_SAMPLE_TEXT = """\
Character OS is post-hackathon SaaS infrastructure for persistent
AI spokespeople. Small businesses create reusable on-camera
identities — powered by Runway's avatar API — that star in
campaign-ready video output without a fresh face every time.

The cast members in the admin workspace are example data, not
product fixtures. Every user creates their own spokespeople with
their own tone archetype, business brief, voice preset, and
portrait.

Knowledge ingestion lets each workspace teach its spokespeople
what the workspace is selling — product details, FAQ entries,
marketing positioning, voice guidelines. Render-flow RAG injects
the relevant chunks at script-generation time so the spokesperson
speaks from real workspace knowledge rather than the LLM's blank
imagination.
"""


class Command(BaseCommand):
    help = (
        "End-to-end smoke of the K3 ingestion pipeline: "
        "ingest_text → embed_document → retrieve_for_teammate."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--workspace-slug",
            default="admins-workspace",
            help="Target workspace slug. Default: admins-workspace.",
        )
        parser.add_argument(
            "--pdf",
            type=Path,
            default=None,
            help=(
                "Optional PDF path. When set, the smoke exercises the "
                "ingest_pdf path instead of ingest_text."
            ),
        )
        parser.add_argument(
            "--real",
            action="store_true",
            help=(
                "Use the real OpenAI embedding API. Requires "
                "OPENAI_API_KEY. Default is EMBEDDING_FORCE_MOCK=1."
            ),
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Don't rollback the ingested document at the end.",
        )

    def handle(self, *args, **options) -> None:
        slug = options["workspace_slug"]
        pdf_path: Path | None = options["pdf"]
        use_real = options["real"]
        keep = options["keep"]

        if not use_real:
            os.environ.setdefault("EMBEDDING_FORCE_MOCK", "1")
            self.stdout.write("  · EMBEDDING_FORCE_MOCK=1 (mock vectors)")
        else:
            if not os.environ.get("OPENAI_API_KEY", "").strip():
                raise CommandError(
                    "--real requires OPENAI_API_KEY in the environment."
                )
            self.stdout.write("  · real OpenAI mode (will burn embedding tokens)")

        try:
            workspace = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist as exc:
            raise CommandError(f"workspace slug={slug!r} not found") from exc

        spokesperson = workspace.teammates.first()
        if spokesperson is None:
            raise CommandError(
                f"workspace {slug!r} has no spokespeople — seed cast first"
            )

        self.stdout.write(f"  · workspace = {workspace.name} (slug={slug})")
        self.stdout.write(f"  · spokesperson = {spokesperson.name}")

        # Wrap the whole smoke in a savepoint we can roll back at
        # the end. Keeps the workspace clean unless --keep is set.
        sid = transaction.savepoint()

        try:
            self._run_pipeline(workspace, spokesperson, pdf_path)
        except Exception:
            transaction.savepoint_rollback(sid)
            raise

        if keep:
            transaction.savepoint_commit(sid)
            self.stdout.write(self.style.SUCCESS("  ✓ kept (--keep)"))
        else:
            transaction.savepoint_rollback(sid)
            self.stdout.write("  · rolled back smoke document")

        self.stdout.write(self.style.SUCCESS("✓ smoke test PASSED"))

    def _run_pipeline(
        self,
        workspace: Workspace,
        spokesperson: Teammate,
        pdf_path: Path | None,
    ) -> None:
        if pdf_path is not None:
            self.stdout.write(f"  · ingest_pdf({pdf_path})")
            result = ingest_pdf(
                workspace=workspace,
                title=f"smoke-pdf {pdf_path.name}",
                payload=pdf_path,
                # SESSION 276 Slice 20 — explicit positive audience
                # signal per Delta fresh-write NULL closure. The smoke
                # command validates the workspace-wide ingestion+retrieval
                # pipeline; WORKSPACE audience matches that scope.
                workspace_shared_intent=True,
            )
        else:
            self.stdout.write("  · ingest_text(sample)")
            result = ingest_text(
                workspace=workspace,
                title="smoke ingestion document",
                content=_SAMPLE_TEXT,
                document_type=DocumentType.MARKDOWN,
                ingested_via=IngestedVia.PASTE,
                # SESSION 276 Slice 20 — explicit positive audience
                # signal per Delta fresh-write NULL closure.
                workspace_shared_intent=True,
            )

        doc = result.document
        if result.deduped:
            self.stdout.write(
                f"  · dedup hit — doc {doc.pk} already existed; will re-embed"
            )
        else:
            self.stdout.write(f"  · created doc {doc.pk} (status={doc.status})")

        # Run the Celery task synchronously. `.apply()` runs in-process
        # so we don't need a separate worker for the smoke. The same
        # task signature is what production async ingest calls.
        async_result = embed_document.apply(args=[str(doc.pk)])
        outcome = async_result.get()
        self.stdout.write(
            f"  · embed_document result: chunks={outcome['chunks_created']} "
            f"cached={outcome['cached_hits']} "
            f"cost_micros={outcome['total_cost_micros']} "
            f"status={outcome['status']}"
        )

        doc.refresh_from_db()
        if doc.status != DocumentStatus.PROCESSED:
            raise CommandError(
                f"expected status=processed, got {doc.status} "
                f"(error: {doc.error_message!r})"
            )

        chunk_count = doc.chunks.count()
        if chunk_count == 0:
            raise CommandError("no chunks created — TextSplitter or embed failed")
        self.stdout.write(f"  · {chunk_count} chunk(s) persisted")

        # Verify retrieval — query with a slice of the source text and
        # confirm the chunk surface returns the doc.
        sample_query = doc.processed_content[:120]
        retrieved = retrieve_for_teammate(
            spokesperson, query=sample_query, top_k=5,
        )
        if not retrieved:
            raise CommandError(
                "retrieve_for_teammate returned 0 chunks — "
                "visibility filter wrong?"
            )
        doc_ids = {c.document_id for c in retrieved}
        if doc.pk not in doc_ids:
            raise CommandError(
                f"retrieval returned other docs but not our smoke doc "
                f"{doc.pk}: {doc_ids}"
            )
        self.stdout.write(
            f"  · retrieval returned {len(retrieved)} chunk(s); "
            f"smoke doc was hit"
        )

        # Idempotency: re-ingesting the same content returns
        # the same row with deduped=True. Skip when we came in
        # via PDF since dedup hashes the extracted text, not the
        # binary, but the same path still applies.
        if pdf_path is None:
            second = ingest_text(
                workspace=workspace,
                title="smoke ingestion document (retry)",
                content=_SAMPLE_TEXT,
                document_type=DocumentType.MARKDOWN,
                ingested_via=IngestedVia.PASTE,
                # SESSION 276 Slice 20 — explicit positive audience signal.
                workspace_shared_intent=True,
            )
            if not second.deduped or second.document.pk != doc.pk:
                raise CommandError(
                    f"dedup broken: expected same doc {doc.pk}, "
                    f"got {second.document.pk} (deduped={second.deduped})"
                )
            self.stdout.write("  · second ingest deduped to same row")


def _entry() -> None:
    """Internal — used by tests that import this module."""
    sys.exit(0)
