"""SESSION 272 Slice B — programmatic setup for the RIVET DEBUGGING paired-paraphrase A/B.

Creates two disposable workspaces (WS_CTL + WS_EXP), each with:
  * one cloned Rivet Teammate (byte-identical persona fields)
  * one Universe
  * one KnowledgeDocument (CTL: canonical DEBUGGING paragraph; EXP: canonical + Option D paraphrase)

Embeds both documents synchronously so the experiment can render immediately.

Idempotent: if the disposable slugs already exist, deletes and re-creates.

Usage:
  python scripts/session272_slice_b_setup.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# Add shell/ to sys.path so this script can be launched from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "shell"))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

from apps.accounts.models import Workspace  # noqa: E402
from apps.embeddings.ingestion import ingest_text  # noqa: E402
from apps.embeddings.models import (  # noqa: E402
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
)
from apps.embeddings.tasks import embed_document  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402

CANONICAL_RIVET_TEAMMATE_ID = "5dd05e3c-e1e8-46bf-8cbf-f7d119ef9e70"
CANONICAL_WORKSPACE_OWNER_ID = 883  # chris@donkeybetz.com

# Content — Slice B's sole differing variable.
CANONICAL_DEBUGGING_PARAGRAPH = (
    "DEBUGGING When something breaks, Rivet prefers reducing the problem "
    "before trying to fix it. Changing one meaningful variable and testing "
    "again is more informative than changing ten things at once. Useful "
    "debugging questions include what changed, what was expected, what "
    "actually happened, whether the behavior can be reproduced, where the "
    "behavior first becomes incorrect, what evidence exists, what "
    "assumption might be wrong, and what smallest test would separate two "
    "possible explanations. Evidence beats guessing."
)

OPTION_D_PAIRED_PARAPHRASE = (
    "In plain terms: ask what changed since it worked, what should have "
    "happened, what actually did, whether you can reproduce it, where the "
    "trouble starts, what evidence you have, what assumption might be "
    "wrong, and what small test would settle it."
)

CTL_SLUG = "session272-rivet-debug-ctl"
EXP_SLUG = "session272-rivet-debug-exp"

CTL_DOC_TITLE = "RIVET-DEBUG (CTL) — SESSION 272 experimental substrate"
EXP_DOC_TITLE = "RIVET-DEBUG (EXP) — SESSION 272 experimental substrate"


def _teardown_if_exists() -> None:
    """Delete disposable workspaces if they already exist (idempotency)."""
    for slug in (CTL_SLUG, EXP_SLUG):
        try:
            ws = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            continue
        # Chained deletes: KnowledgeChunk CASCADE from KnowledgeDocument;
        # KnowledgeDocument CASCADE from workspace; Universe/Teammate/etc CASCADE.
        print(f"  ↺ existing disposable ws found: {ws.id} ({slug}) — deleting")
        ws.delete()


def _clone_rivet_persona(new_workspace: Workspace, new_universe: Universe) -> Teammate:
    """Clone the canonical Rivet Teammate's persona fields into new_workspace.

    Uses field-by-field copy rather than pk=None assignment to control every
    field explicitly. Names the teammate 'Rivet' so the render sees the same
    character identity string as canonical production.
    """
    canonical = Teammate.objects.get(id=CANONICAL_RIVET_TEAMMATE_ID)
    persona_fields = {
        "name": "Rivet",
        "business_brief": canonical.business_brief,
        "personality": canonical.personality,
        "visual_subject": canonical.visual_subject,
        "visual_template": canonical.visual_template,
        "tone_archetype": canonical.tone_archetype,
        "status": canonical.status,
        # runway_avatar_id preserved so any downstream avatar lookup remains
        # coherent; the experiment does not fire Runway but keeping the field
        # symmetric with canonical is safer than nulling it.
        "runway_avatar_id": canonical.runway_avatar_id,
        "runway_avatar_status": canonical.runway_avatar_status,
        "portrait_path": canonical.portrait_path,
        "voice_id": canonical.voice_id,
        "who_you_help": canonical.who_you_help,
        "what_you_sell": canonical.what_you_sell,
        "always_emphasize": canonical.always_emphasize,
        "never_say": canonical.never_say,
        "desired_feeling": canonical.desired_feeling,
        "character_point_of_view": canonical.character_point_of_view,
        "voice_energy": canonical.voice_energy,
        "voice_humor": canonical.voice_humor,
        "voice_directness": canonical.voice_directness,
        "voice_signature_phrases": canonical.voice_signature_phrases,
        "voice_avoid_phrases": canonical.voice_avoid_phrases,
    }
    tm = Teammate.objects.create(
        workspace=new_workspace,
        universe=new_universe,
        **persona_fields,
    )
    return tm


def _create_disposable(slug: str, name_suffix: str, doc_content: str, doc_title: str) -> dict:
    """Create workspace + universe + teammate + doc + embeddings for one condition."""
    owner = get_user_model().objects.get(pk=CANONICAL_WORKSPACE_OWNER_ID)
    with transaction.atomic():
        ws = Workspace.objects.create(
            name=f"SESSION 272 Slice B — {name_suffix}",
            slug=slug,
            owner=owner,
        )
        universe = Universe.objects.create(
            workspace=ws,
            name=f"SESSION 272 Slice B — {name_suffix}",
            slug=slug,
            description=(
                "Disposable universe for SESSION 272 Slice B RIVET DEBUGGING "
                "paired-paraphrase A/B experiment. Delete on completion."
            ),
            created_by=owner,
        )
        rivet = _clone_rivet_persona(ws, universe)
    # Ingest text via the canonical ingestion path (so chunking uses the real
    # pipeline). No spokespeople M2M attach — broadcast (M2M-null) so the
    # cloned Rivet Teammate sees it via the broadcast branch of retrieval.
    result = ingest_text(
        workspace=ws,
        title=doc_title,
        content=doc_content,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        created_by=owner,
        universe=universe,
    )
    doc = result.document
    # Synchronously embed so the render can retrieve immediately.
    embed_document(str(doc.pk))
    doc.refresh_from_db()
    chunks = list(KnowledgeChunk.objects.filter(document=doc).order_by("chunk_index"))
    return {
        "workspace_id": str(ws.id),
        "workspace_slug": ws.slug,
        "universe_id": str(universe.id),
        "rivet_teammate_id": str(rivet.id),
        "doc_id": str(doc.id),
        "doc_title": doc.title,
        "doc_content_sha256": hashlib.sha256(doc_content.encode()).hexdigest(),
        "doc_content_length": len(doc_content),
        "doc_status": doc.status,
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "length": len(c.chunk_text or ""),
                "sha256_16": hashlib.sha256((c.chunk_text or "").encode()).hexdigest()[:16],
                "text": c.chunk_text,
            }
            for c in chunks
        ],
    }


def main() -> int:
    print("SESSION 272 Slice B — creating disposable substrates")
    print("=" * 72)
    _teardown_if_exists()
    ctl = _create_disposable(
        slug=CTL_SLUG,
        name_suffix="CTL",
        doc_content=CANONICAL_DEBUGGING_PARAGRAPH,
        doc_title=CTL_DOC_TITLE,
    )
    exp_content = CANONICAL_DEBUGGING_PARAGRAPH + "\n\n" + OPTION_D_PAIRED_PARAPHRASE
    exp = _create_disposable(
        slug=EXP_SLUG,
        name_suffix="EXP",
        doc_content=exp_content,
        doc_title=EXP_DOC_TITLE,
    )
    manifest = {
        "canonical_debugging_paragraph_sha256": hashlib.sha256(
            CANONICAL_DEBUGGING_PARAGRAPH.encode()
        ).hexdigest(),
        "option_d_paired_paraphrase_sha256": hashlib.sha256(
            OPTION_D_PAIRED_PARAPHRASE.encode()
        ).hexdigest(),
        "canonical_debugging_paragraph_length": len(CANONICAL_DEBUGGING_PARAGRAPH),
        "option_d_paired_paraphrase_length": len(OPTION_D_PAIRED_PARAPHRASE),
        "CTL": ctl,
        "EXP": exp,
    }
    print()
    print(json.dumps(manifest, indent=2))
    manifest_path = "docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json"
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nManifest written to {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
