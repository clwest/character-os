"""SESSION 281 Slice 281.1 — real-provider verification (ONE controlled call).

Fires ONE real OpenAI Responses-API call against composition
`772e9012-4d26-4f93-a50c-158b4e8a42f1` (Fox & Flour Bakery,
Episode `eb47350e`) via the newly-landed
``apps.memory.services.suggest_memories_from_composition``.

Purpose (per SESSION 281 slice authorization):
    Prove that moving the Q280.9 probe behavior into production
    preserved real provider compatibility, prompt construction,
    response parsing, candidate contract, and rough cost
    characteristics.

Does NOT:
    * promote any returned candidate
    * mutate any NarrativeMemory row
    * retry / refresh the provider more than once (unless the call
      fails for an implementation reason — in which case the
      failure is logged and the script exits non-zero for triage)

Records evidence to:
    docs/design/session281_experiment_data/slice_281_1_real_provider_evidence.json

Usage:
    set -a; source .env; set +a
    python scripts/session281_slice_281_1_real_provider_verify.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "shell"))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

from apps.compositions.models import Composition  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.memory.services import (  # noqa: E402
    SuggestMemoriesUpstreamError,
    suggest_memories_from_composition,
)

FOX_AND_FLOUR_COMPOSITION = "772e9012-4d26-4f93-a50c-158b4e8a42f1"

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session281_experiment_data"


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    comp = Composition.objects.get(pk=FOX_AND_FLOUR_COMPOSITION)
    print(
        f"Composition {str(comp.id)[:8]} status={comp.status} "
        f"brief_chars={len(comp.synthesized_brief or '')} "
        f"episode={str(comp.episode_id)[:8] if comp.episode_id else None}"
    )

    memory_count_before = NarrativeMemory.objects.count()
    print(f"NarrativeMemory rows before call: {memory_count_before}")

    started_utc = datetime.now(timezone.utc).isoformat()
    print("=== Firing ONE real OpenAI call via curator service ===")
    t0 = time.time()
    try:
        payload = suggest_memories_from_composition(
            comp, n=3, use_cache=False,
        )
    except SuggestMemoriesUpstreamError as exc:
        elapsed = time.time() - t0
        print(f"UPSTREAM ERROR after {elapsed:.2f}s: {exc}")
        finished_utc = datetime.now(timezone.utc).isoformat()
        evidence = {
            "started_utc": started_utc,
            "finished_utc": finished_utc,
            "composition_id": FOX_AND_FLOUR_COMPOSITION,
            "result": "upstream_error",
            "error": str(exc),
            "elapsed_seconds": round(elapsed, 3),
        }
        (AUDIT_DIR / "slice_281_1_real_provider_evidence.json").write_text(
            json.dumps(evidence, indent=2)
        )
        return 1
    elapsed = time.time() - t0
    finished_utc = datetime.now(timezone.utc).isoformat()

    memory_count_after = NarrativeMemory.objects.count()
    write_delta = memory_count_after - memory_count_before

    print(
        f"elapsed={elapsed:.2f}s "
        f"model={payload['model']} "
        f"tokens_input={payload.get('tokens_input', '?')} "
        f"tokens_output={payload.get('tokens_output', '?')} "
        f"candidates={len(payload['candidates'])} "
        f"cache_hit={payload['cache']['hit']}"
    )
    print(f"NarrativeMemory rows after call: {memory_count_after}")
    print(f"Write delta (must be 0 per invariant): {write_delta}")

    if write_delta != 0:
        print("!! INVARIANT VIOLATION: curator wrote to NarrativeMemory !!")
        return 2

    print()
    print("=== CANDIDATES (verbatim; scoring by human) ===")
    for i, c in enumerate(payload["candidates"], 1):
        witnesses = c.get("witnesses", [])
        witnesses_repr = witnesses if witnesses else ["everyone (whole-cast)"]
        print(f"[{i}] kind={c.get('kind')} witnesses={witnesses_repr}")
        print(f"    body: {c.get('body')}")
        note = c.get("narrative_gravity_note", "")
        if note:
            print(f"    why:  {note}")
        print()

    evidence = {
        "slice": "281.1",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "composition_id": FOX_AND_FLOUR_COMPOSITION,
        "result": "ok",
        "elapsed_seconds": round(elapsed, 3),
        "model": payload["model"],
        "cache": payload["cache"],
        "substrate_summary": payload["substrate_summary"],
        "tokens_input": payload.get("tokens_input"),
        "tokens_output": payload.get("tokens_output"),
        "candidates_verbatim": payload["candidates"],
        "narrative_memory_write_delta": write_delta,
        "memory_count_before": memory_count_before,
        "memory_count_after": memory_count_after,
    }
    out_path = AUDIT_DIR / "slice_281_1_real_provider_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
