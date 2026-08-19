"""SESSION 267 §13 — Re-embed the promoted private memory after the
initial inline embed failed for lack of OPENAI_API_KEY in the shell env.

Sanctioned recovery per apps/memory/services.py docstring:
  'Embedding failures do not roll back the promotion. The row lands
   with embedding_vector=NULL; retrieval simply excludes it until a
   re-embed lands. Operator intent (a manual "Remember this" click)
   is authoritative and must not be lost to a provider hiccup.'

READ-then-WRITE: reads the promoted row, calls the sanctioned
apps.memory.services.embed_memory(...) which fires the same code
path a Celery-worker-side embed would use. No promotion path
touched; the row identity is stable.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.memory.models import NarrativeMemory
from apps.memory.services import embed_memory

MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

mem = NarrativeMemory.objects.get(pk=MEM_ID)
print(f"Before: has_vector={mem.embedding_vector is not None} "
      f"embedded_at={mem.embedded_at}")

changed = embed_memory(mem, force=False)
mem.refresh_from_db()

print(f"After : has_vector={mem.embedding_vector is not None} "
      f"embedded_at={mem.embedded_at} model={mem.embedding_model!r} "
      f"dim={mem.embedding_dimension} cost_micros={mem.embedding_cost_micros}")
print(f"changed_flag_from_embed_memory: {changed}")

payload = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "memory_id": str(mem.id),
    "changed": changed,
    "has_embedding_vector": mem.embedding_vector is not None,
    "embedded_at": mem.embedded_at.isoformat() if mem.embedded_at else None,
    "embedding_model": mem.embedding_model,
    "embedding_dimension": mem.embedding_dimension,
    "embedding_cost_micros": mem.embedding_cost_micros,
}
out = Path(
    "../docs/design/session_267_experiment_data/04b_reembed_result.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2))
print(f"Wrote {out}")
