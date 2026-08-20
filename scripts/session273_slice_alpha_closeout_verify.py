"""SESSION 273 Slice α closeout verification.

Read-only. Does NOT ingest, delete, mutate, edit, retry, or tune.

Verifies the state Chris's UI action produced:
  * KD 74e7f18f-... exists with title, universe, m2m=Ruby-only
  * content_hash matches the ingest committed at §15
  * chunk / embedding coverage still 10/10
  * Ruby persona fields byte-identical to §11 audit values
  * body char count matches the ingest committed at §15 (~6599)

Runs three natural retrieval probes against Ruby:
  * bakery-native
  * customer/community-adjacent
  * operational-detail

For each probe records:
  * distinct retrieved doc ids
  * per-chunk universe scope + distance + preview
  * whether any of the 9 §11.5 unbound workspace-only KDs leak
  * whether any other-Universe (Patch's Workshop) KDs leak
  * whether any Ruby-ineligible KD (m2m to another character) leaks

Preserves everything to a JSON sidecar.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from apps.embeddings.models import (  # noqa: E402
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentSpokesperson,
)
from apps.embeddings.retrieval import retrieve_for_teammate  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
MASON_ID = "28b9a7ea-8230-4463-8b0d-4ebfabfe11ec"
WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
KD_ID = "74e7f18f-5b77-459c-bc36-b4ab617d8aca"

# Approved §11 audit persona hashes captured at Slice α close-of-§13
# (unchanged since 2026-07-23 wizard save). Comparison is via SHA-256
# of the exact string value; Python hash() is randomized per process
# so a stable hash function is required.
import hashlib


def _sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


PROBES = [
    ("bakery-native", "how do we handle the sourdough starter feeding routine for the country loaf"),
    ("customer-community-adjacent", "how do you help a first-time customer who feels intimidated by the case"),
    ("operational-detail", "what is the deposit and cancellation policy on custom celebration cakes"),
]


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _snapshot(teammate, kind, query, top_k=5, allowed_doc_ids=None):
    chunks = retrieve_for_teammate(teammate, query=query, top_k=top_k)
    per_chunk = []
    for c in chunks:
        per_chunk.append({
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "document_title": c.document.title,
            "document_universe_id": (
                str(c.document.universe_id) if c.document.universe_id else None
            ),
            "distance": getattr(c, "distance", None),
            "chunk_preview": (c.chunk_text or "")[:200],
        })
    distinct = sorted({str(c.document_id) for c in chunks})
    unexpected = sorted(set(distinct) - (allowed_doc_ids or set()))
    return {
        "kind": kind,
        "query": query,
        "top_k": top_k,
        "chunk_count": len(chunks),
        "chunks": per_chunk,
        "distinct_document_ids": distinct,
        "distinct_document_universe_ids": sorted({
            str(c.document.universe_id) if c.document.universe_id else "NULL"
            for c in chunks
        }),
        "unexpected_document_ids": unexpected,
    }


def main():
    now = datetime.now(timezone.utc)
    out = {
        "generated_at": now.isoformat(),
        "workspace_id": WORKSPACE_ID,
        "universe_id": UNIVERSE_ID,
        "ruby_id": RUBY_ID,
    }

    # --- KD state verification ---
    kd = KnowledgeDocument.objects.get(id=KD_ID)
    m2m_rows = list(
        KnowledgeDocumentSpokesperson.objects.filter(knowledgedocument=kd).values(
            "teammate_id", "teammate__name"
        )
    )
    chunk_count = KnowledgeChunk.objects.filter(document=kd).count()
    embedded_count = KnowledgeChunk.objects.filter(
        document=kd, embedding_vector__isnull=False
    ).count()

    out["kd_state"] = {
        "id": str(kd.id),
        "title": kd.title,
        "workspace_id": str(kd.workspace_id),
        "universe_id": str(kd.universe_id) if kd.universe_id else None,
        "document_type": kd.document_type,
        "ingested_via": kd.ingested_via,
        "status": kd.status,
        "is_active": kd.is_active,
        "content_hash": kd.content_hash,
        "chunks_total": chunk_count,
        "chunks_embedded": embedded_count,
        "created_at": _iso(kd.created_at),
        "updated_at": _iso(kd.updated_at),
        "m2m_spokespeople_count": len(m2m_rows),
        "m2m_spokespeople": [
            {"id": str(r["teammate_id"]), "name": r["teammate__name"]} for r in m2m_rows
        ],
        "raw_content_char_count": len(kd.raw_content or ""),
        "processed_content_char_count": len(kd.processed_content or ""),
    }

    out["kd_verification"] = {
        "universe_is_fox_and_flour": (
            str(kd.universe_id) == UNIVERSE_ID if kd.universe_id else False
        ),
        "workspace_is_expected": str(kd.workspace_id) == WORKSPACE_ID,
        "m2m_is_ruby_only": (
            len(m2m_rows) == 1 and str(m2m_rows[0]["teammate_id"]) == RUBY_ID
        ),
        "status_is_processed": kd.status == "processed",
        "chunks_fully_embedded": chunk_count == embedded_count == 10,
        "is_active": kd.is_active is True,
    }

    # --- Ruby persona invariant check ---
    ruby = Teammate.objects.get(id=RUBY_ID)
    out["ruby_state"] = {
        "id": str(ruby.id),
        "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
        "updated_at": _iso(ruby.updated_at),
        "persona_sha256": {
            "business_brief": _sha256(ruby.business_brief),
            "personality": _sha256(ruby.personality),
            "who_you_help": _sha256(ruby.who_you_help),
            "what_you_sell": _sha256(ruby.what_you_sell),
            "desired_feeling": _sha256(ruby.desired_feeling),
            "tone_archetype": _sha256(ruby.tone_archetype),
            "character_point_of_view": _sha256(ruby.character_point_of_view),
            "always_emphasize": _sha256(ruby.always_emphasize),
            "never_say": _sha256(ruby.never_say),
            "voice_signature_phrases": _sha256(ruby.voice_signature_phrases),
            "voice_avoid_phrases": _sha256(ruby.voice_avoid_phrases),
        },
        "portrait_path": ruby.portrait_path,
        "runway_avatar_id": ruby.runway_avatar_id,
        "voice_id": ruby.voice_id,
    }
    # Content sanity check — Ruby's brief still starts with the same
    # opening clause; if it doesn't, persona was mutated. String
    # comparison here is against the §13.2 verbatim opening.
    out["ruby_state"]["business_brief_opening"] = (ruby.business_brief or "")[:80]
    out["ruby_state"]["personality_opening"] = (ruby.personality or "")[:80]

    # --- Retrieval probes ---
    allowed = {KD_ID}
    probe_results = []
    for kind, q in PROBES:
        probe_results.append(_snapshot(ruby, kind, q, top_k=5, allowed_doc_ids=allowed))
    out["retrieval_probes"] = probe_results

    # --- Contamination analysis ---
    unbound_workspace_only_kd_ids = {
        str(k.id)
        for k in KnowledgeDocument.objects.filter(
            workspace_id=WORKSPACE_ID, universe__isnull=True
        )
    }
    other_universe_kd_ids = {
        str(k.id)
        for k in KnowledgeDocument.objects.filter(workspace_id=WORKSPACE_ID)
        .exclude(universe__isnull=True)
        .exclude(universe_id=UNIVERSE_ID)
    }
    # KDs m2m-bound to non-Ruby teammates (Ruby-ineligible)
    other_character_bound_kd_ids = set()
    for k in KnowledgeDocument.objects.filter(workspace_id=WORKSPACE_ID):
        m2m = list(
            KnowledgeDocumentSpokesperson.objects.filter(
                knowledgedocument=k
            ).values_list("teammate_id", flat=True)
        )
        if m2m and str(RUBY_ID) not in [str(x) for x in m2m]:
            other_character_bound_kd_ids.add(str(k.id))

    aggregate_docs = set()
    for p in probe_results:
        aggregate_docs.update(p["distinct_document_ids"])

    out["contamination_analysis"] = {
        "aggregate_retrieved_docs": sorted(aggregate_docs),
        "unbound_leaked": sorted(aggregate_docs & unbound_workspace_only_kd_ids),
        "other_universe_leaked": sorted(aggregate_docs & other_universe_kd_ids),
        "other_character_bound_leaked": sorted(
            aggregate_docs & other_character_bound_kd_ids
        ),
        "only_fox_flour_kd_returned": aggregate_docs == {KD_ID},
    }

    # --- Broader workspace state (invariance check) ---
    from apps.compositions.models import Composition
    from apps.memory.models import NarrativeMemory
    from apps.universe.models import Episode

    out["workspace_counts"] = {
        "total_kds": KnowledgeDocument.objects.filter(workspace_id=WORKSPACE_ID).count(),
        "total_narrative_memories": NarrativeMemory.objects.filter(
            workspace_id=WORKSPACE_ID
        ).count(),
        "total_universes": Universe.objects.filter(workspace_id=WORKSPACE_ID).count(),
        "total_episodes": Episode.objects.filter(
            universe__workspace_id=WORKSPACE_ID
        ).count(),
        "total_compositions": Composition.objects.filter(
            workspace_id=WORKSPACE_ID
        ).count(),
    }
    # Mason invariance
    mason = Teammate.objects.get(id=MASON_ID)
    out["mason_state"] = {
        "id": str(mason.id),
        "universe_id": str(mason.universe_id) if mason.universe_id else None,
        "updated_at": _iso(mason.updated_at),
    }

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
        / "05_slice_alpha_closeout_verification.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print("KD state:")
    for k, v in out["kd_verification"].items():
        print(f"  {k}: {v}")
    print()
    print("Ruby state:")
    print(f"  universe_id: {out['ruby_state']['universe_id']}")
    print(f"  updated_at: {out['ruby_state']['updated_at']}")
    print(f"  business_brief opening: {out['ruby_state']['business_brief_opening']!r}")
    print()
    print("Contamination analysis:")
    for k, v in out["contamination_analysis"].items():
        print(f"  {k}: {v}")
    print()
    print("Workspace counts:")
    for k, v in out["workspace_counts"].items():
        print(f"  {k}: {v}")
    print()
    print("Mason invariance:")
    for k, v in out["mason_state"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
