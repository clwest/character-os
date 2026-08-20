"""SESSION 273 Slice α — ingest the approved Fox & Flour KnowledgeDocument.

Runs the same production ingestion path the SPA `/api/knowledge/`
serializer uses: `ingestion.ingest_text` + `embed_document.delay`.

Then polls for embedding completion and executes a single natural
bakery-native retrieval probe on Ruby.

Preserves all raw evidence to a JSON sidecar. Does NOT create an
Episode, Composition, NarrativeMemory, or PublishBundle. Does NOT
modify Ruby's persona / voice / avatar / brand.

Content note: The proposed KD file
`docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md`
has a leading `> **Status:** PROPOSED — NOT INGESTED. Awaiting Chris
approval before upload …` blockquote that is REVIEW-ARTIFACT
metadata, not KD content. Ingesting it verbatim would insert the
literal string "NOT INGESTED. Awaiting Chris approval before upload"
into the Fox & Flour knowledge corpus — obvious nonsense that
contradicts the ingestion itself. This script therefore:
  * uses the top-level `# Fox & Flour Bakery — Working Knowledge`
    line as the KD `title`,
  * discards the `> Status: …` review blockquote,
  * discards the immediately-following horizontal rule `---`,
  * ingests everything from `## Breads & sourdough` through end.

This mirrors what an operator would do in the SPA (paste body into
text-content, enter title separately). Every KD sentence Chris
authored is preserved verbatim.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from apps.accounts.models import Workspace  # noqa: E402
from apps.embeddings import ingestion  # noqa: E402
from apps.embeddings.models import (  # noqa: E402
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
    KnowledgeChunk,
)
from apps.embeddings.retrieval import retrieve_for_teammate  # noqa: E402
from apps.embeddings.tasks import embed_document  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
CHRIS_USER_ID = 883

KD_SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "session_273_experiment_data"
    / "03_slice_alpha_proposed_knowledge_document.md"
)

# Single bakery-native probe query — plausibly asked by a real operator
# preparing an Episode about Fox & Flour's celebration-cake booking
# rules. Grounded in the KD's §"Celebration cakes" section.
PROBE_QUERY = "how far in advance do we need to book a custom celebration cake"


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _split_kd(raw: str) -> tuple[str, str, str]:
    """Return (title, body_to_ingest, stripped_review_blockquote).

    The proposed file begins:
      # Fox & Flour Bakery — Working Knowledge

      > **Status:** PROPOSED — NOT INGESTED. Awaiting Chris approval
      > before upload through `/workspace/knowledge` in the Fox &
      > Flour Bakery Universe (`1a0af807-...`).
      >
      > Authored per SESSION 273 §11.10: ...

      ---

      ## Breads & sourdough
      ...
    """
    lines = raw.splitlines()

    # Locate title line (leading '# ')
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            body_start = i + 1
            break

    # Skip blank lines, review blockquote, blank lines, horizontal rule
    review_lines: list[str] = []
    j = body_start
    # blank lines
    while j < len(lines) and not lines[j].strip():
        j += 1
    # blockquote block (contiguous '>' lines)
    while j < len(lines) and lines[j].lstrip().startswith(">"):
        review_lines.append(lines[j])
        j += 1
    # blank lines
    while j < len(lines) and not lines[j].strip():
        j += 1
    # optional horizontal rule
    if j < len(lines) and re.fullmatch(r"-{3,}", lines[j].strip()):
        j += 1
    # blank lines
    while j < len(lines) and not lines[j].strip():
        j += 1

    body = "\n".join(lines[j:]).rstrip() + "\n"
    review = "\n".join(review_lines)
    return title, body, review


def _snapshot_retrieval(teammate: Teammate, query: str, top_k: int = 5) -> dict:
    chunks = retrieve_for_teammate(teammate, query=query, top_k=top_k)
    return {
        "query": query,
        "top_k": top_k,
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
                "document_title": c.document.title,
                "document_universe_id": (
                    str(c.document.universe_id) if c.document.universe_id else None
                ),
                "distance": getattr(c, "distance", None),
                "chunk_preview": (c.chunk_text or "")[:220],
            }
            for c in chunks
        ],
        "distinct_document_ids": sorted({str(c.document_id) for c in chunks}),
        "distinct_document_universe_ids": sorted({
            str(c.document.universe_id) if c.document.universe_id else "NULL"
            for c in chunks
        }),
    }


def main():
    now = datetime.now(timezone.utc)
    out = {
        "generated_at": now.isoformat(),
        "workspace_id": WORKSPACE_ID,
        "universe_id": UNIVERSE_ID,
        "ruby_id": RUBY_ID,
        "kd_source_path": str(KD_SOURCE_PATH),
    }

    raw = KD_SOURCE_PATH.read_text()
    title, body, review = _split_kd(raw)

    out["kd_split"] = {
        "title": title,
        "review_blockquote_stripped": review,
        "body_char_count": len(body),
        "body_first_120_chars": body[:120],
        "body_last_120_chars": body[-120:],
    }

    workspace = Workspace.objects.get(id=WORKSPACE_ID)
    universe = Universe.objects.get(id=UNIVERSE_ID)
    ruby = Teammate.objects.get(id=RUBY_ID)

    User = get_user_model()
    try:
        chris = User.objects.get(id=CHRIS_USER_ID)
    except User.DoesNotExist:
        chris = None

    # --- Ingest via production text path (SPA `text_content` branch) ---
    # doc_type = MARKDOWN because body starts with '## Breads & sourdough'.
    doc_type = (
        DocumentType.MARKDOWN
        if (body.startswith("#") or "\n## " in body)
        else DocumentType.TEXT
    )
    result = ingestion.ingest_text(
        workspace=workspace,
        title=title,
        content=body,
        document_type=doc_type,
        ingested_via=IngestedVia.PASTE,
        created_by=chris,
        spokespeople=None,  # empty M2M = broadcast; Universe scope handles isolation
        universe=universe,
    )

    kd = result.document
    out["kd_created"] = {
        "id": str(kd.id),
        "title": kd.title,
        "document_type": kd.document_type,
        "ingested_via": kd.ingested_via,
        "workspace_id": str(kd.workspace_id),
        "universe_id": str(kd.universe_id) if kd.universe_id else None,
        "status_immediate": kd.status,
        "deduped": bool(result.deduped),
        "content_hash": kd.content_hash,
        "created_at": _iso(kd.created_at),
        "is_active": kd.is_active,
        "chunks_immediate": KnowledgeChunk.objects.filter(document=kd).count(),
    }

    # --- Dispatch embedding task (same as serializer does) ---
    if not result.deduped:
        embed_document.delay(str(kd.pk))

    # --- Poll for embedding completion ---
    poll_start = time.time()
    poll_deadline_s = 180  # 3 minutes; real ingest for 7k-char doc is seconds
    poll_history = []
    final_status = kd.status
    final_chunks = 0
    while time.time() - poll_start < poll_deadline_s:
        kd.refresh_from_db()
        chunk_count = KnowledgeChunk.objects.filter(document=kd).count()
        embedded_count = KnowledgeChunk.objects.filter(
            document=kd, embedding_vector__isnull=False
        ).count()
        poll_history.append({
            "elapsed_s": round(time.time() - poll_start, 2),
            "status": kd.status,
            "chunks_total": chunk_count,
            "chunks_embedded": embedded_count,
        })
        final_status = kd.status
        final_chunks = chunk_count
        if kd.status in {"processed", "failed"} and chunk_count > 0 and embedded_count == chunk_count:
            break
        if kd.status == "failed":
            break
        time.sleep(2)

    out["kd_polling"] = {
        "final_status": final_status,
        "final_chunks_total": final_chunks,
        "final_chunks_embedded": KnowledgeChunk.objects.filter(
            document=kd, embedding_vector__isnull=False
        ).count(),
        "elapsed_s_to_final": poll_history[-1]["elapsed_s"] if poll_history else 0,
        "history": poll_history,
    }

    # --- Retrieval probe on Ruby ---
    ruby.refresh_from_db()
    out["ruby_state"] = {
        "id": str(ruby.id),
        "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
        "updated_at": _iso(ruby.updated_at),
    }
    snap = _snapshot_retrieval(ruby, PROBE_QUERY, top_k=5)
    out["retrieval_probe"] = snap

    # --- Contamination check ---
    unbound_workspace_only_kd_ids = {
        str(k.id)
        for k in KnowledgeDocument.objects.filter(
            workspace_id=WORKSPACE_ID, universe__isnull=True
        )
    }
    # Other-universe KDs = workspace KDs scoped to any Universe that
    # is NOT the new Fox & Flour Universe (i.e. Patch's Workshop).
    other_universe_kd_ids = {
        str(k.id)
        for k in KnowledgeDocument.objects.filter(workspace_id=WORKSPACE_ID)
        .exclude(universe__isnull=True)
        .exclude(universe_id=UNIVERSE_ID)
    }
    retrieved_docs = set(snap["distinct_document_ids"])
    retrieved_universes = set(snap["distinct_document_universe_ids"])
    out["contamination_analysis"] = {
        "retrieved_doc_count": len(retrieved_docs),
        "retrieved_universes": sorted(retrieved_universes),
        "expected_universe": UNIVERSE_ID,
        "unbound_workspace_only_leaked": sorted(
            retrieved_docs & unbound_workspace_only_kd_ids
        ),
        "other_universe_leaked": sorted(
            retrieved_docs & other_universe_kd_ids
        ),
        "only_fox_flour_universe": (
            retrieved_universes.issubset({UNIVERSE_ID}) and len(retrieved_universes) > 0
        ),
        "only_new_kd_returned": retrieved_docs == {str(kd.id)},
    }

    # --- Cross-check Ruby wasn't mutated ---
    out["ruby_persona_hashes_after_ingest"] = {
        "business_brief_hash": hash(ruby.business_brief or ""),
        "personality_hash": hash(ruby.personality or ""),
        "who_you_help_hash": hash(ruby.who_you_help or ""),
        "what_you_sell_hash": hash(ruby.what_you_sell or ""),
        "character_pov_hash": hash(ruby.character_point_of_view or ""),
        "voice_signature_hash": hash(ruby.voice_signature_phrases or ""),
        "voice_avoid_hash": hash(ruby.voice_avoid_phrases or ""),
        "always_emphasize_hash": hash(ruby.always_emphasize or ""),
        "never_say_hash": hash(ruby.never_say or ""),
    }

    # Runtime invariants
    out["runtime_invariants"] = {
        "experiment_env_vars_present": {
            k: os.environ.get(k) for k in os.environ if "EXPERIMENT" in k.upper()
        },
        "mock_env_vars_present": {
            k: os.environ.get(k) for k in os.environ if "_MOCK" in k.upper()
        },
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "design"
        / "session_273_experiment_data"
        / "04_slice_alpha_kd_ingest_and_retrieval.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print(f"KD id: {kd.id} title={kd.title!r} universe={kd.universe_id}")
    print(f"final status: {final_status} chunks={final_chunks} embedded={out['kd_polling']['final_chunks_embedded']}")
    print(f"probe: {PROBE_QUERY!r}")
    print(f"retrieved docs: {snap['distinct_document_ids']}")
    print(f"retrieved universes: {snap['distinct_document_universe_ids']}")
    print(f"only_fox_flour: {out['contamination_analysis']['only_fox_flour_universe']}  only_new_kd: {out['contamination_analysis']['only_new_kd_returned']}")
    print(f"unbound_leaked: {out['contamination_analysis']['unbound_workspace_only_leaked']}")
    print(f"other_universe_leaked: {out['contamination_analysis']['other_universe_leaked']}")


if __name__ == "__main__":
    main()
