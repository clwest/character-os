"""SESSION 267 §13 — Promote the locked private-observation memory
via the sanctioned NarrativeMemory promotion service.

Uses apps.memory.views.promote_from_composition — the SAME function
CompositionViewSet.promote_narrative_memory calls when the SPA UI's
"Remember this" form submits. No shortcut / direct-M2M-write path.

Locked wording (Chris, SESSION 267 approval message):
  "While Patch was out, Rivet found that the workshop agent had
   quietly built a folder named 'PATCH OVERRIDES' tracking every
   recommendation Patch had ignored. Rivet chose not to tell him."

Locked witnessed_by = [Rivet] only. Kind + weight left at model
defaults (event / peripheral) — matches every prior Patch' Workshop
memory including cd73d52f. UI does not expose kind; we mirror UI
behavior.

Idempotency guard: refuses to run if a NarrativeMemory already
exists tied to source_composition b0b0e932-...
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth import get_user_model

from apps.compositions.models import Composition
from apps.memory.models import NarrativeMemory
from apps.memory.views import promote_from_composition


COMP_ID = "b0b0e932-4e54-4b1b-b393-3c441aae93b7"
RIVET_TEAMMATE_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"
PROMOTED_BY_USER_ID = 883        # chris@donkeybetz.com — matches every
                                  # prior Patch' Workshop promotion.

LOCKED_BODY = (
    "While Patch was out, Rivet found that the workshop agent had "
    "quietly built a folder named 'PATCH OVERRIDES' tracking every "
    "recommendation Patch had ignored. Rivet chose not to tell him."
)


def _die(msg: str) -> None:
    raise SystemExit(f"PROMOTION HALTED: {msg}")


User = get_user_model()

comp = (
    Composition.objects
    .select_related("workspace", "episode", "episode__universe")
    .get(pk=COMP_ID)
)

if comp.episode_id is None:
    _die(f"Composition {COMP_ID} has no attached episode.")

# Idempotency guard.
existing = list(NarrativeMemory.objects.filter(source_composition=comp))
if existing:
    _die(
        f"Composition {COMP_ID} already has {len(existing)} "
        f"NarrativeMemory promotion(s): {[str(m.id) for m in existing]}. "
        f"Refusing to duplicate."
    )

# Sanity guards on the episode.
cast_ids = list(comp.episode.cast.values_list("id", flat=True))
cast_names = list(comp.episode.cast.values_list("name", flat=True))
if len(cast_ids) != 1:
    _die(f"Episode cast size = {len(cast_ids)} (expected 1); refusing.")
if str(cast_ids[0]) != RIVET_TEAMMATE_ID:
    _die(
        f"Episode cast contains {cast_ids[0]}, not Rivet "
        f"({RIVET_TEAMMATE_ID}). Refusing."
    )

promoted_by = User.objects.get(pk=PROMOTED_BY_USER_ID)

print(f"Composition: {comp.id}")
print(f"Episode:     {comp.episode.id} — {comp.episode.title!r}")
print(f"Episode cast: {cast_names}")
print(f"Promoter:    {promoted_by.email} (id={promoted_by.id})")
print(f"Body length: {len(LOCKED_BODY)} chars")
print(f"witnessed_by: [Rivet ({RIVET_TEAMMATE_ID})]")
print("Invoking promote_from_composition …")

created = promote_from_composition(
    composition=comp,
    episode=comp.episode,
    memory_items=[{
        "body": LOCKED_BODY,
        # kind + weight — service function trusts serializer
        # defaults to supply these. NarrativeMemoryPromoteItemSerializer
        # defaults to EVENT / PERIPHERAL (the SPA promote UI does not
        # expose either field), so we supply them explicitly here to
        # exactly mirror what the sanctioned SPA path would produce.
        "kind": "event",
        "weight": "peripheral",
        # UUID objects match the type the SPA serializer produces
        # (serializers.UUIDField in NarrativeMemoryPromoteItemSerializer).
        # Passing strings here fails the set-membership check in the
        # service against episode.cast.values_list("id", flat=True)
        # which returns UUID instances.
        "witnessed_by": [uuid.UUID(RIVET_TEAMMATE_ID)],
    }],
    promoted_by=promoted_by,
)

assert len(created) == 1, f"Expected 1 memory, got {len(created)}"
mem = created[0]

# Re-fetch to see everything after the inline embed pass.
mem.refresh_from_db()

# Verification snapshot.
witnesses = [
    {"id": str(w.id), "name": w.name} for w in mem.witnessed_by.all()
]
payload = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "locked_body_verbatim": LOCKED_BODY,
    "body_matches_locked": mem.body == LOCKED_BODY,
    "id": str(mem.id),
    "body": mem.body,
    "kind": mem.kind,
    "weight": mem.weight,
    "status": mem.status,
    "archived_at": (
        mem.archived_at.isoformat() if mem.archived_at else None
    ),
    "workspace_id": str(mem.workspace_id),
    "universe_id": str(mem.universe_id),
    "source_episode_id": str(mem.episode_id) if mem.episode_id else None,
    "source_episode_title": (
        mem.episode.title if mem.episode_id else None
    ),
    "source_composition_id": (
        str(mem.source_composition_id) if mem.source_composition_id else None
    ),
    "witnessed_by": witnesses,
    "witness_count": len(witnesses),
    "whole_cast_convention": len(witnesses) == 0,
    "embedding_model": mem.embedding_model,
    "embedding_dimension": mem.embedding_dimension,
    "embedding_cost_micros": mem.embedding_cost_micros,
    "embedded_at": (
        mem.embedded_at.isoformat() if mem.embedded_at else None
    ),
    "has_embedding_vector": mem.embedding_vector is not None,
    "promoted_by_id": mem.promoted_by_id,
    "promoted_by_email": (
        mem.promoted_by.email if mem.promoted_by_id else None
    ),
    "supersedes_id": (
        str(mem.supersedes_id) if mem.supersedes_id else None
    ),
    "created_at": mem.created_at.isoformat(),
    "updated_at": mem.updated_at.isoformat(),
}

out = Path(
    "../docs/design/session_267_experiment_data/04_promotion_verification.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2))

print()
print(f"=== NarrativeMemory {mem.id} ===")
print(f"  body verbatim match:  {payload['body_matches_locked']}")
print(f"  status:               {mem.status}")
print(f"  archived_at:          {mem.archived_at}")
print(f"  witnessed_by:         {witnesses}")
print(f"  witness_count:        {len(witnesses)}  "
      f"(whole_cast_convention={payload['whole_cast_convention']})")
print(f"  kind / weight:        {mem.kind} / {mem.weight}")
print(f"  embedding_model:      {mem.embedding_model}")
print(f"  embedding_dimension:  {mem.embedding_dimension}")
print(f"  has_embedding_vector: {payload['has_embedding_vector']}")
print(f"  embedded_at:          {mem.embedded_at}")
print(f"  embedding_cost_micros:{mem.embedding_cost_micros}")
print(f"  promoted_by:          {payload['promoted_by_email']} "
      f"(id={mem.promoted_by_id})")
print(f"  source_composition:   {mem.source_composition_id}")
print(f"  source_episode:       {mem.episode_id} — "
      f"{payload['source_episode_title']!r}")
print(f"  universe:             {mem.universe_id}")
print(f"\nWrote {out}")
