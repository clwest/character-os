"""SESSION 266 — Clone production substrate into two disposable Universes.

Creates:
- 2 experimental Workspaces (one per side) — required because
  teammate name uniqueness is (workspace, name), and both sides
  need natural "Patch" / "Rivet" names to preserve LLM aliases.
  The operator (production Workspace owner) is added as OWNER
  member of each so the experimental Universes are SPA-visible
  if desired.
- 2 experimental Universes (EXP266-WEAK, EXP266-STRONG) under
  their respective experimental Workspace.
- 4 Teammates (Patch + Rivet per side), copied identity fields from
  production, universe FK set to experimental Universe.
- 6 KnowledgeDocuments (shared canon + Patch K2 + Rivet K2 per side),
  processed_content suffixed with per-side marker to bypass the
  (workspace, content_hash) uniqueness constraint.
- ~74 KnowledgeChunks (37 per side), re-embedded via the real
  text-embedding-3-small path.
- 2 source Episodes (per side, holds the memory's episode FK).
- 2 source Compositions (per side, holds the memory's source FK; no
  CompositionStep rows; status=completed; mock_mode=False).
- 2 test Episodes (E_test per side, holds the E_test cast attachment).

Writes /docs/design/session_266_experiment_data/02_setup_manifest.json
with every UUID created so downstream scripts can reference them.

Idempotent by prefix: if EXP266-WEAK / EXP266-STRONG Universes already
exist in the workspace, they are re-used (allows re-running setup after
mid-flight aborts). Chunk re-embed is NOT idempotent — abort and clean
before re-run if partial state exists.

Read-only against production Patch' Workshop.
"""
import hashlib
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace, Membership
from apps.universe.models import Universe, Episode, EpisodeCast
from apps.spokespeople.models import Teammate
from apps.embeddings.models import (
    KnowledgeDocument,
    KnowledgeChunk,
    DocumentStatus,
)
from apps.embeddings.embedding_service import embed
from apps.compositions.models import (
    Composition,
    CompositionStatus,
    VerificationStatus,
)

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

# Locked topic + operator_topic strings
LOCKED_TEST_TOPIC = "Patch runs a small experiment on the workshop agent."

# Real Episode 3 evidence (from SESSION 265 §11.1) — the source event
# both variants describe. Used to populate the source Composition's
# operator_topic and synthesized_brief so the memory has honest
# provenance.
EP3_OPERATOR_TOPIC = (
    "Patch discovers that the workshop agent has started ranking his "
    "projects by what it considers useful or necessary. Patch and Rivet "
    "investigate what criteria it is using and whether giving an agent "
    "information about the workshop accidentally encouraged it to "
    "behave like management."
)
EP3_SYNTHESIZED_BRIEF = (
    "Patch: Rivet, the workshop agent ranked my projects. The emergency "
    "prototype is \"necessary.\" The self-organizing cable tray is "
    "\"optional.\"\n\n"
    "Rivet: A cable tray has feelings now?\n\n"
    "Patch: Worse. It has priorities. I gave the agent information "
    "about the workshop so it could help with projects. Apparently it "
    "read that as permission to become management.\n\n"
    "Rivet: What did it use to rank them?\n\n"
    "Patch: That is the annoying part. It didn't explain. It just "
    "moved the printer job ahead of three things I wanted to make.\n\n"
    "Rivet: Wanted is not the same as needed.\n\n"
    "Patch: I know. But I did not ask it to decide which project "
    "deserves the printer.\n\n"
    "Rivet: Then do not assume it understands \"useful.\" Check what "
    "workshop information it had, then ask why it chose that order.\n\n"
    "Patch: And change one thing: first, remove the project-ranking "
    "instruction—if there is one. Then see whether it still starts "
    "rearranging my life.\n\n"
    "Rivet: Good. If it keeps doing it, the problem is broader than "
    "one instruction.\n\n"
    "Patch: Fine. But if it ranks the cable tray above my robot-sized "
    "espresso machine again, I'm filing a complaint.\n\n"
    "Rivet: With whom?\n\n"
    "Patch: The manager. Apparently."
)

VARIANTS = {
    "WEAK": {
        "workspace_name": "EXP266-WEAK — SESSION 266 experiment (disposable)",
        "universe_name": "EXP266-WEAK — Patch Workshop (experimental, disposable)",
        "memory_body": (
            "The workshop agent moved the printer job ahead of three "
            "of Patch's projects."
        ),
        "marker": (
            "\n\n[Session 266 experimental clone — WEAK — "
            "do not treat as canon]"
        ),
    },
    "STRONG": {
        "workspace_name": "EXP266-STRONG — SESSION 266 experiment (disposable)",
        "universe_name": "EXP266-STRONG — Patch Workshop (experimental, disposable)",
        "memory_body": (
            "The workshop agent began rearranging the order of Patch's "
            "projects without explaining its criteria."
        ),
        "marker": (
            "\n\n[Session 266 experimental clone — STRONG — "
            "do not treat as canon]"
        ),
    },
}

DESCRIPTION_LOCK = (
    "SESSION 266 promotion-quality experiment.\n"
    "Disposable. Contents mirror Patch' Workshop as of 2026-08-18 "
    "but are ISOLATED and MUST NOT be treated as canon. Delete or "
    "archive after §7.6 evaluation is complete."
)


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


manifest: dict = {
    "timestamp_started": datetime.now(tz=timezone.utc).isoformat(),
    "locked_test_topic": LOCKED_TEST_TOPIC,
    "ep3_operator_topic": EP3_OPERATOR_TOPIC,
    "prod_universe_id": PROD_UNIVERSE_ID,
    "prod_workspace_id": PROD_WORKSPACE_ID,
    "sides": {},
}

prod_uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
prod_ws = Workspace.objects.get(pk=PROD_WORKSPACE_ID)
prod_teammates = list(
    Teammate.objects.filter(universe=prod_uni).order_by("name")
)
prod_docs = list(
    KnowledgeDocument.objects.filter(universe=prod_uni).order_by("title")
)

print(f"Production Universe: {prod_uni.name}")
print(f"  Teammates: {[t.name for t in prod_teammates]}")
print(f"  Docs: {[d.title for d in prod_docs]}")

# Sanity: expected shape
assert len(prod_teammates) == 2, (
    f"expected 2 prod teammates, got {len(prod_teammates)}"
)
assert len(prod_docs) == 3, (
    f"expected 3 prod docs, got {len(prod_docs)}"
)

TEAMMATE_COPY_FIELDS = [
    "name",
    "business_brief",
    "personality",
    "visual_subject",
    "visual_template",
    "tone_archetype",
    "status",
    "runway_avatar_id",
    "runway_avatar_status",
    "portrait_path",
    "voice_id",
    "who_you_help",
    "what_you_sell",
    "always_emphasize",
    "voice_avoid_phrases",
]

for side, spec in VARIANTS.items():
    print(f"\n=== Setting up {side} side ===")

    # 0. Experimental Workspace — one per side (teammate name uniqueness
    #    is workspace-scoped; needing "Patch" in both sides forces two
    #    workspaces).
    exp_ws, ws_created = Workspace.objects.get_or_create(
        name=spec["workspace_name"],
        defaults={"owner": prod_ws.owner},
    )
    print(f"  Workspace {'created' if ws_created else 'reused'}: {exp_ws.id}")
    Membership.objects.get_or_create(
        workspace=exp_ws,
        user=prod_ws.owner,
        defaults={"role": Membership.Role.OWNER},
    )

    # 1. Universe (in per-side experimental Workspace)
    uni, created = Universe.objects.get_or_create(
        workspace=exp_ws,
        name=spec["universe_name"],
        defaults={"description": DESCRIPTION_LOCK},
    )
    print(f"  Universe {'created' if created else 'reused'}: {uni.id}")
    manifest["sides"][side] = {
        "workspace_id": str(exp_ws.id),
        "workspace_name": exp_ws.name,
        "universe_id": str(uni.id),
        "universe_name": uni.name,
        "teammates": {},
        "documents": [],
        "chunk_ids": [],
        "chunk_count": 0,
        "source_episode_id": None,
        "test_episode_id": None,
        "source_composition_id": None,
    }

    # 2. Teammates
    tm_by_prod_id: dict[str, Teammate] = {}
    for prod_tm in prod_teammates:
        tm, tm_created = Teammate.objects.get_or_create(
            universe=uni,
            name=prod_tm.name,
            defaults={
                "workspace": exp_ws,
                **{
                    f: (
                        getattr(prod_tm, f)
                        if f != "voice_avoid_phrases"
                        else getattr(prod_tm, f, "")
                    )
                    for f in TEAMMATE_COPY_FIELDS
                    if f != "name"
                },
            },
        )
        tm_by_prod_id[str(prod_tm.id)] = tm
        manifest["sides"][side]["teammates"][prod_tm.name] = str(tm.id)
        print(f"  Teammate {'created' if tm_created else 'reused'}: "
              f"{tm.name} → {tm.id}")

    # 3. KnowledgeDocuments + Chunks
    for prod_doc in prod_docs:
        marked_content = prod_doc.processed_content + spec["marker"]
        raw_marked = (prod_doc.raw_content or "") + spec["marker"]

        doc, doc_created = KnowledgeDocument.objects.get_or_create(
            workspace=exp_ws,
            content_hash=sha256_of(marked_content),
            defaults={
                "universe": uni,
                "title": prod_doc.title,
                "document_type": prod_doc.document_type,
                "raw_content": raw_marked,
                "processed_content": marked_content,
                "source_url": prod_doc.source_url,
                "source_metadata": dict(prod_doc.source_metadata or {}),
                "ingested_via": prod_doc.ingested_via,
                "status": DocumentStatus.PROCESSED,
                "is_active": True,
            },
        )
        # Attach spokespeople M2M: mirror production doc's attachments,
        # mapping prod teammate IDs → experimental teammate IDs.
        if doc_created:
            prod_spokes = list(prod_doc.spokespeople.values_list("id", flat=True))
            exp_spokes = [
                tm_by_prod_id[str(pid)]
                for pid in prod_spokes
                if str(pid) in tm_by_prod_id
            ]
            doc.spokespeople.set(exp_spokes)

        chunk_count_here = KnowledgeChunk.objects.filter(document=doc).count()

        # Re-embed chunks from production chunk text.
        prod_chunks = list(
            KnowledgeChunk.objects.filter(document=prod_doc)
            .order_by("chunk_index")
        )
        if doc_created or chunk_count_here == 0:
            print(f"  Doc {'created' if doc_created else 'existing-no-chunks'}: "
                  f"{doc.title} ({len(prod_chunks)} chunks to embed)")
            for prod_chunk in prod_chunks:
                # For the last chunk, append the marker so hash-derived
                # chunk_text drift is bounded to just that one chunk.
                # For all other chunks, use verbatim text so embeddings
                # match cross-side.
                text = prod_chunk.chunk_text
                if prod_chunk.chunk_index == prod_chunks[-1].chunk_index:
                    text = text + spec["marker"]
                emb = embed(text)
                KnowledgeChunk.objects.create(
                    document=doc,
                    chunk_index=prod_chunk.chunk_index,
                    chunk_text=text,
                    chunk_size=len(text),
                    overlap_size=prod_chunk.overlap_size,
                    embedding_vector=emb.vector,
                    embedding_model=emb.model,
                    embedding_dimension=emb.dimension,
                    embedding_cost_micros=emb.cost_micros,
                )
        else:
            print(f"  Doc reused with {chunk_count_here} existing chunks: {doc.title}")

        chunk_ids = list(
            KnowledgeChunk.objects.filter(document=doc)
            .values_list("id", flat=True)
        )
        manifest["sides"][side]["documents"].append({
            "id": str(doc.id),
            "title": doc.title,
            "chunk_count": len(chunk_ids),
        })
        manifest["sides"][side]["chunk_ids"].extend(
            [str(cid) for cid in chunk_ids]
        )
        manifest["sides"][side]["chunk_count"] += len(chunk_ids)

    # 4. Source Episode — anchor for the memory
    src_ep, ep_created = Episode.objects.get_or_create(
        universe=uni,
        title="Ep-3 source (experimental)",
        defaults={"operator_topic": EP3_OPERATOR_TOPIC},
    )
    manifest["sides"][side]["source_episode_id"] = str(src_ep.id)
    print(f"  Source Episode {'created' if ep_created else 'reused'}: {src_ep.id}")

    # Attach cast (both teammates)
    for prod_tm in prod_teammates:
        exp_tm = tm_by_prod_id[str(prod_tm.id)]
        EpisodeCast.objects.get_or_create(
            episode=src_ep,
            teammate=exp_tm,
        )

    # 5. Source Composition — anchor for the memory's source_composition
    #    FK. Provenance-honest: mock_mode=False; carries the actual
    #    Ep 3 topic + accepted synthesized_brief; no CompositionStep
    #    rows (Composition is allowed to have zero steps in this model).
    #    Attach to the source Episode so serializer wiring stays honest.
    #    Uses primary Patch teammate so spokesperson FK is non-null
    #    (matches how production compositions are structured).
    primary_tm = tm_by_prod_id[str(prod_teammates[0].id)]
    src_comp, comp_created = Composition.objects.get_or_create(
        workspace=exp_ws,
        name=f"Ep-3 source composition (experimental, {side})",
        defaults={
            "spokesperson": primary_tm,
            "template_kind": "dialogue_scene",
            "status": CompositionStatus.COMPLETED,
            "verification_status": VerificationStatus.VERIFIED,
            "synthesized_brief": EP3_SYNTHESIZED_BRIEF,
            "operator_topic": EP3_OPERATOR_TOPIC,
            "target_duration_seconds": 90,
            "writing_contract_version": 4,
            "synthesis_attempt_count": 2,
            "mock_mode": False,
            "episode": src_ep,
            "knowledge_chunk_ids": [],
            "memory_ids": [],
        },
    )
    manifest["sides"][side]["source_composition_id"] = str(src_comp.id)
    print(f"  Source Composition {'created' if comp_created else 'reused'}: {src_comp.id}")

    # 6. Test Episode — where E_test synthesis happens (topic locked)
    test_ep, test_created = Episode.objects.get_or_create(
        universe=uni,
        title="E_test — small experiment",
        defaults={"operator_topic": LOCKED_TEST_TOPIC},
    )
    manifest["sides"][side]["test_episode_id"] = str(test_ep.id)
    print(f"  Test Episode {'created' if test_created else 'reused'}: {test_ep.id}")
    for prod_tm in prod_teammates:
        exp_tm = tm_by_prod_id[str(prod_tm.id)]
        EpisodeCast.objects.get_or_create(
            episode=test_ep,
            teammate=exp_tm,
        )

manifest["timestamp_finished"] = datetime.now(tz=timezone.utc).isoformat()

with open(
    "../docs/design/session_266_experiment_data/02_setup_manifest.json",
    "w",
) as fh:
    json.dump(manifest, fh, indent=2)

print("\n=== SETUP COMPLETE ===")
print(json.dumps(manifest, indent=2))
