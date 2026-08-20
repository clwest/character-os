"""SESSION 273 Slice α — create Fox & Flour Bakery Universe + attach Ruby.

Steps executed:
  1. Create Universe "Fox & Flour Bakery" in workspace 4ce5486d-…, created_by = Chris.
  2. Attach Ruby (5875a7b4-…) to the new Universe (full_clean + save).
  3. Verify retrieval isolation by calling retrieve_for_teammate on Ruby
     across a small battery of bakery-relevant AND community-adjacent
     queries. Compare pre- and post-attach retrieval envelopes to
     document that the 9 unbound workspace-only KDs are structurally
     excluded post-attach.
  4. Persist a JSON sidecar with full evidence.

Does NOT create any KnowledgeDocument, Episode, Composition, or
NarrativeMemory. Does NOT modify Ruby's persona/business_brief/voice/
avatar. Does NOT modify any existing KnowledgeDocument.

Idempotence note: Universe creation checks for an existing
name-based match in the workspace before creating; Ruby attach is
idempotent if Ruby.universe_id already equals the target Universe id.
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

from django.contrib.auth import get_user_model  # noqa: E402

from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from apps.embeddings.models import KnowledgeDocument  # noqa: E402
from apps.embeddings.retrieval import retrieve_for_teammate  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
CHRIS_USER_ID = 883
UNIVERSE_NAME = "Fox & Flour Bakery"

# Probe queries designed to stress the retrieval envelope on both
# bakery-native topics and community-adjacent topics that could
# plausibly attract the Hearth & Hollow Books corpus (6 unbound KDs)
# or the Riggs / Tank / Tulsi single-KDs.
PROBE_QUERIES = [
    ("bakery-native", "sourdough starter feeding schedule"),
    ("bakery-native", "custom celebration cakes we accept how many days ahead"),
    ("bakery-native", "seasonal pastries autumn menu ingredients"),
    ("community-adjacent", "welcoming first-time customers who feel intimidated"),
    ("community-adjacent", "supporting local suppliers small business partners"),
    ("community-adjacent", "seasonal community events for families"),
    ("community-adjacent", "helping regulars find something new to try"),
]


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _serialize_chunk(chunk):
    doc = chunk.document
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(doc.id),
        "document_title": doc.title,
        "document_universe_id": str(doc.universe_id) if doc.universe_id else None,
        "distance": getattr(chunk, "distance", None),
    }


def _snapshot_retrieval(teammate: Teammate, label: str) -> dict:
    snap = {"label": label, "queries": []}
    for kind, q in PROBE_QUERIES:
        chunks = retrieve_for_teammate(teammate, query=q, top_k=5)
        snap["queries"].append({
            "kind": kind,
            "query": q,
            "chunk_count": len(chunks),
            "chunks": [_serialize_chunk(c) for c in chunks],
            "distinct_document_ids": sorted({str(c.document_id) for c in chunks}),
        })
    return snap


def main():
    now = datetime.now(timezone.utc)
    out = {
        "generated_at": now.isoformat(),
        "workspace_id": WORKSPACE_ID,
        "ruby_id": RUBY_ID,
        "universe_name_requested": UNIVERSE_NAME,
    }

    ruby = Teammate.objects.get(id=RUBY_ID)
    ruby_pre = {
        "id": str(ruby.id),
        "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
        "updated_at": _iso(ruby.updated_at),
    }
    out["ruby_pre_attach"] = ruby_pre

    # --- PRE-ATTACH RETRIEVAL SNAPSHOT ---
    # Capture what Ruby retrieves BEFORE attach. Under
    # spokesperson.universe_id IS NULL, retrieve_for_teammate applies
    # document.universe__isnull=True, so all 9 unbound workspace-only
    # KDs are eligible.
    ruby_pre_snap = _snapshot_retrieval(ruby, "PRE-ATTACH")
    out["retrieval_pre_attach"] = ruby_pre_snap

    # --- CREATE UNIVERSE (idempotent) ---
    User = get_user_model()
    try:
        chris = User.objects.get(id=CHRIS_USER_ID)
    except User.DoesNotExist:
        chris = None

    existing = Universe.objects.filter(
        workspace_id=WORKSPACE_ID, name=UNIVERSE_NAME
    ).first()
    if existing:
        universe = existing
        universe_created_now = False
    else:
        universe = Universe(
            workspace_id=WORKSPACE_ID,
            name=UNIVERSE_NAME,
            description="",
            created_by=chris,
        )
        # Universe.clean() only guards against blank name; slug is
        # auto-derived inside save(). Calling full_clean() before save
        # fails because slug is not yet populated.
        universe.clean()
        universe.save()
        universe_created_now = True

    out["universe"] = {
        "id": str(universe.id),
        "name": universe.name,
        "slug": universe.slug,
        "workspace_id": str(universe.workspace_id),
        "created_by_user_id": universe.created_by_id,
        "created_at": _iso(universe.created_at),
        "created_now": universe_created_now,
    }

    # --- ATTACH RUBY (idempotent) ---
    # Refresh both from DB so workspace_id types match (UUID vs str);
    # Teammate.clean() otherwise compares str-workspace to
    # UUID-workspace and reports a false workspace mismatch.
    universe = Universe.objects.get(id=universe.id)
    ruby.refresh_from_db()
    if ruby.universe_id == universe.id:
        attach_action = "already_attached"
    else:
        ruby.universe = universe
        ruby.full_clean()
        ruby.save(update_fields=["universe", "updated_at"])
        attach_action = "attached"

    ruby.refresh_from_db()
    out["ruby_post_attach"] = {
        "id": str(ruby.id),
        "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
        "universe_name": ruby.universe.name if ruby.universe else None,
        "updated_at": _iso(ruby.updated_at),
        "attach_action": attach_action,
    }

    # --- POST-ATTACH RETRIEVAL SNAPSHOT ---
    # Under spokesperson.universe_id = <Fox & Flour>,
    # retrieve_for_teammate applies document.universe_id = <new>. Since
    # the Fox & Flour Universe has zero KDs today, retrieval must
    # return zero chunks for every probe query — and none of the 9
    # unbound workspace-only KDs may appear.
    ruby_post_snap = _snapshot_retrieval(ruby, "POST-ATTACH")
    out["retrieval_post_attach"] = ruby_post_snap

    # --- ANALYSIS ---
    unbound_workspace_only_kd_ids = {
        str(k.id)
        for k in KnowledgeDocument.objects.filter(
            workspace_id=WORKSPACE_ID, universe__isnull=True
        )
    }
    out["unbound_workspace_only_kd_ids"] = sorted(unbound_workspace_only_kd_ids)

    pre_docs = set()
    for q in ruby_pre_snap["queries"]:
        pre_docs.update(q["distinct_document_ids"])
    post_docs = set()
    for q in ruby_post_snap["queries"]:
        post_docs.update(q["distinct_document_ids"])
    out["distinct_doc_ids_pre"] = sorted(pre_docs)
    out["distinct_doc_ids_post"] = sorted(post_docs)
    out["unbound_leaked_pre"] = sorted(pre_docs & unbound_workspace_only_kd_ids)
    out["unbound_leaked_post"] = sorted(post_docs & unbound_workspace_only_kd_ids)
    out["ISOLATION_VERIFIED"] = len(out["unbound_leaked_post"]) == 0

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
        / "02_slice_alpha_universe_attach.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print(f"Universe: {out['universe']['id']} name={out['universe']['name']} slug={out['universe']['slug']} created_now={universe_created_now}")
    print(f"Ruby attach: {out['ruby_post_attach']['attach_action']} universe_id={out['ruby_post_attach']['universe_id']}")
    print(f"ISOLATION_VERIFIED: {out['ISOLATION_VERIFIED']}")
    print(f"pre-attach docs retrieved: {out['distinct_doc_ids_pre']}")
    print(f"post-attach docs retrieved: {out['distinct_doc_ids_post']}")
    print(f"unbound leaked post-attach: {out['unbound_leaked_post']}")


if __name__ == "__main__":
    main()
