"""SESSION 266 — Clean up any partial EXP266 rows from failed setup runs.

Deletes only:
  * NarrativeMemory rows scoped to EXP266 Universes
  * Composition rows in EXP266 Workspaces
  * Episodes scoped to EXP266 Universes
  * KnowledgeChunk / KnowledgeDocument scoped to EXP266 Universes
  * Teammate scoped to EXP266 Universes
  * Universe rows named 'EXP266-*'
  * Workspace rows named 'EXP266*'

Ordered so RESTRICT constraints don't block. Verifies production
Patch' Workshop untouched at end.
"""
from apps.accounts.models import Workspace
from apps.universe.models import Universe, Episode
from apps.spokespeople.models import Teammate
from apps.embeddings.models import KnowledgeDocument, KnowledgeChunk
from apps.compositions.models import Composition
from apps.memory.models import NarrativeMemory

# 1. Find EXP266 workspaces + universes
exp_ws = list(Workspace.objects.filter(name__startswith="EXP266"))
exp_uni = list(Universe.objects.filter(name__startswith="EXP266-"))
print(f"Found {len(exp_ws)} EXP266 workspaces, {len(exp_uni)} EXP266 universes")
for ws in exp_ws:
    print(f"  Workspace: {ws.name} ({ws.id})")
for uni in exp_uni:
    print(f"  Universe: {uni.name} ({uni.id}) workspace={uni.workspace_id}")

# 2. Delete NarrativeMemory in EXP266 Universes
mem_deleted = NarrativeMemory.objects.filter(universe__in=exp_uni).delete()
print(f"NarrativeMemories deleted: {mem_deleted}")

# 3. Delete Compositions in EXP266 Workspaces (this includes source compositions
#    that hold RESTRICT FKs to Episodes)
comp_deleted = Composition.objects.filter(workspace__in=exp_ws).delete()
print(f"Compositions deleted: {comp_deleted}")

# 4. Delete Episodes
ep_deleted = Episode.objects.filter(universe__in=exp_uni).delete()
print(f"Episodes deleted: {ep_deleted}")

# 5. Delete KnowledgeChunk + KnowledgeDocument in EXP266 Universes
chunk_deleted = KnowledgeChunk.objects.filter(
    document__universe__in=exp_uni
).delete()
print(f"KnowledgeChunks deleted: {chunk_deleted}")
doc_deleted = KnowledgeDocument.objects.filter(universe__in=exp_uni).delete()
print(f"KnowledgeDocuments deleted: {doc_deleted}")

# 6. Delete Teammates
tm_deleted = Teammate.objects.filter(universe__in=exp_uni).delete()
print(f"Teammates deleted: {tm_deleted}")

# 7. Delete Universes
uni_deleted = Universe.objects.filter(name__startswith="EXP266-").delete()
print(f"Universes deleted: {uni_deleted}")

# 8. Delete experimental Workspaces (cascades take care of remaining membership rows)
ws_deleted = Workspace.objects.filter(name__startswith="EXP266").delete()
print(f"Workspaces deleted: {ws_deleted}")

# 9. Verify production untouched
prod_uni = Universe.objects.get(pk="56d16b63-652e-4f54-bc7e-39114bbfc4c5")
print(f"\nProduction Patch' Workshop: name={prod_uni.name} "
      f"updated_at={prod_uni.updated_at.isoformat()}")
print(f"Production teammate count: "
      f"{Teammate.objects.filter(universe=prod_uni).count()}")
print(f"Production doc count: "
      f"{KnowledgeDocument.objects.filter(universe=prod_uni).count()}")
print(f"Production chunk count: "
      f"{KnowledgeChunk.objects.filter(document__universe=prod_uni).count()}")
print(f"Production memory count: "
      f"{NarrativeMemory.objects.filter(universe=prod_uni).count()}")
