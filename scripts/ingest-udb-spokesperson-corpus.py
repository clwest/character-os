#!/usr/bin/env python3
"""Ingest the unified-donkey-betz spokesperson corpus into a Character OS
workspace and bind each document to a target spokesperson.

The u-d-b repo ships ``docs/spokesperson/`` — a curated markdown corpus
voiced for the public 24/7 Global AI brand (one chunk per section type:
overview, voice, pillars, suite product, lab/engine, channel, story, faq,
facts). This script reads those files, ingests each as a
``KnowledgeDocument`` in the target Character OS workspace via
``apps.embeddings.ingestion.ingest_text``, and adds the target spokesperson
to each doc's ``spokespeople`` M2M so retrieval surfaces them.

Idempotent: content-hash dedup means re-running with unchanged corpus
returns the existing rows (``deduped=True``) and skips re-embedding.

Run from ``shell/`` with the venv active and ``.env`` sourced:

    python ../scripts/ingest-udb-spokesperson-corpus.py \\
        --workspace-id f4f2aa20-e2e2-4ae2-85a0-abacd8bea231 \\
        --spokesperson-id d3d0fb14-193e-4c4c-88d1-acae9af25bb5

Add ``--dry-run`` to list what would be ingested without writing.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


UDB_CORPUS_DIR = Path("/Users/donkeyking/development/unified-donkey-betz/docs/spokesperson")
DEFAULT_WORKSPACE_ID = "f4f2aa20-e2e2-4ae2-85a0-abacd8bea231"
DEFAULT_SPOKESPERSON_ID = "d3d0fb14-193e-4c4c-88d1-acae9af25bb5"


TITLE_PREFIX = "24/7 Global AI — "
TITLE_OVERRIDES = {
    "00_overview.md": "Overview (Suite, Verticals, Lab, Channels taxonomy)",
    "01_voice.md": "Voice (tagline, canonical names, banned vocab)",
    "02_pillars.md": "Pillars (Intelligence, Automation, Innovation, Impact)",
    "10_mentorforge.md": "Suite — MentorForge",
    "30_the_network.md": "Lab — The Network (live intelligence engine)",
    "40_operator_edge.md": "Channel — The Operator Edge (newsletter)",
    "60_origin_pivot.md": "Story — Origin & brand pivot",
    "70_faq.md": "FAQ — public-facing Q&A",
    "90_facts.md": "Facts — every cited number with source",
    "README.md": "Corpus manifest (source-of-truth pointers)",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--spokesperson-id", default=DEFAULT_SPOKESPERSON_ID)
    parser.add_argument("--corpus-dir", default=str(UDB_CORPUS_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--include-readme",
        action="store_true",
        help="Also ingest README.md (manifest). Off by default — it's a pointer "
        "file, not voice content.",
    )
    args = parser.parse_args()

    # Django setup
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shell"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
    import django

    django.setup()

    from apps.accounts.models import Workspace
    from apps.embeddings.ingestion import ingest_text
    from apps.embeddings.models import DocumentType, IngestedVia
    from apps.embeddings.tasks import embed_document
    from apps.spokespeople.models import Spokesperson

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.is_dir():
        print(f"✗ corpus dir not found: {corpus_dir}", file=sys.stderr)
        return 1

    try:
        workspace = Workspace.objects.get(id=args.workspace_id)
    except Workspace.DoesNotExist:
        print(f"✗ workspace {args.workspace_id} not found", file=sys.stderr)
        return 1

    try:
        rigby = Spokesperson.objects.get(id=args.spokesperson_id)
    except Spokesperson.DoesNotExist:
        print(f"✗ spokesperson {args.spokesperson_id} not found", file=sys.stderr)
        return 1

    if rigby.workspace_id != workspace.id:
        print(
            f"✗ spokesperson workspace_id ({rigby.workspace_id}) != "
            f"target workspace ({workspace.id})",
            file=sys.stderr,
        )
        return 1

    print(f"workspace : {workspace.id} | {workspace.name}")
    print(f"spokesperson: {rigby.id} | {rigby.name}")
    print(f"corpus_dir : {corpus_dir}")
    print()

    files = sorted(corpus_dir.glob("*.md"))
    if not args.include_readme:
        files = [f for f in files if f.name != "README.md"]
    if not files:
        print("✗ no markdown files found", file=sys.stderr)
        return 1

    print(f"Found {len(files)} markdown files:")
    for f in files:
        print(f"  - {f.name}")
    print()

    if args.dry_run:
        print("(dry-run — no writes)")
        return 0

    embedded = 0
    deduped = 0
    new_docs = []
    for f in files:
        content = f.read_text()
        suffix = TITLE_OVERRIDES.get(f.name, f.stem)
        title = f"{TITLE_PREFIX}{suffix}"
        result = ingest_text(
            workspace=workspace,
            title=title,
            content=content,
            document_type=DocumentType.MARKDOWN,
            ingested_via=IngestedVia.SEED,
            created_by=workspace.owner,
            spokespeople=[rigby],
            source_metadata={
                "source_path": str(f),
                "source_repo": "unified-donkey-betz",
                "source_corpus": "docs/spokesperson",
                "source_file": f.name,
            },
        )
        if result.deduped:
            print(f"  · {f.name:30s} → deduped  {result.document.id}")
            deduped += 1
        else:
            print(f"  + {f.name:30s} → ingested {result.document.id}")
            new_docs.append(result.document)

    print()
    if new_docs:
        print(f"Embedding {len(new_docs)} new documents (sync, EMBEDDING_FORCE_MOCK active)...")
        for d in new_docs:
            embed_document(d.pk)
            embedded += 1
            print(f"  ✓ embedded {d.title!r}")
    print()
    print(f"summary: {embedded} new, {deduped} deduped, "
          f"{len(files)} total in corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
