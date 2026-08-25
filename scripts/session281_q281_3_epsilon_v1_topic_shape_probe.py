"""SESSION 281 Q281.3-ε — v1 story-direction topic-shape probe.

Falsifiable question:
    Does the live v1 "Where could this story go next?" generator
    predominantly emit CONTROL-shape (off-stage-actor + no
    complication) Episode topics, or was Chris's celebration-cake
    selection unusual?

Method:
    Fire `suggest_next_episodes(fox_and_flour, use_cache=False)`
    3× to obtain 3 distinct fresh candidate sets (server-side
    cache bypassed on each call). Preserve every returned
    suggestion verbatim in a JSON evidence artifact for durable
    audit. Classification is done manually by Claude below and
    appended to the SESSION 281 audit doc.

Isolation guarantees:
    * Read-only over existing substrate; no Episode / Composition /
      NarrativeMemory rows created, edited, archived, or superseded.
    * Uses the SHIPPED v1 service verbatim. No prompt lever swapped,
      no top_k / cache / model change.
    * Do NOT synthesize dialogue. Do NOT promote memories.

Expected cost (using SESSION 280 §11.3's calibrated v1 range of
$0.005-$0.02 per call): ~$0.015-$0.06 total for 3 calls.

Usage:
    set -a; source .env; set +a
    python scripts/session281_q281_3_epsilon_v1_topic_shape_probe.py
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

from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from apps.universe.services import suggest_next_episodes  # noqa: E402

FOX_AND_FLOUR_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
N_PER_CALL = 5   # request the max (service clamps to [1, 5])
N_CALLS = 3

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session281_experiment_data"


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    universe = Universe.objects.get(pk=FOX_AND_FLOUR_ID)
    print(f"Universe: {universe.name}")

    mem_count_before = NarrativeMemory.objects.count()
    print(f"NarrativeMemory rows before probe: {mem_count_before}")

    started_utc = datetime.now(timezone.utc).isoformat()
    calls: list[dict] = []
    all_suggestions: list[str] = []

    for i in range(1, N_CALLS + 1):
        print(f"\n=== Call {i}/{N_CALLS} — use_cache=False ===")
        t0 = time.time()
        payload = suggest_next_episodes(
            universe, n=N_PER_CALL, use_cache=False,
        )
        elapsed = time.time() - t0
        suggestions = [s["text"] for s in payload.get("suggestions", [])]
        tokens_in = payload.get("tokens_input", 0)
        tokens_out = payload.get("tokens_output", 0)
        print(f"  elapsed={elapsed:.2f}s tokens_in={tokens_in} "
              f"tokens_out={tokens_out} candidates={len(suggestions)} "
              f"cache_hit={payload.get('cache', {}).get('hit')}")
        for j, text in enumerate(suggestions, 1):
            print(f"  [{i}.{j}] {text}")
            all_suggestions.append(text)
        calls.append({
            "call_index": i,
            "elapsed_seconds": round(elapsed, 3),
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cache_hit": payload.get("cache", {}).get("hit"),
            "generated_at": payload.get("generated_at"),
            "model": payload.get("model"),
            "substrate_summary": payload.get("substrate_summary", {}),
            "suggestions_verbatim": suggestions,
        })

    finished_utc = datetime.now(timezone.utc).isoformat()

    mem_count_after = NarrativeMemory.objects.count()
    write_delta = mem_count_after - mem_count_before
    print()
    print("=== Post-probe invariants ===")
    print(f"NarrativeMemory count delta (must be 0): {write_delta}")
    assert write_delta == 0, "probe wrote NarrativeMemory rows — abort"

    total_tokens_in = sum(c["tokens_input"] for c in calls)
    total_tokens_out = sum(c["tokens_output"] for c in calls)
    total_calls_cost_estimate = round(
        (total_tokens_in + total_tokens_out) / 1000.0 * 0.013, 4
    )

    evidence = {
        "probe": "Q281.3-ε",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "universe_id": FOX_AND_FLOUR_ID,
        "universe_name": universe.name,
        "n_calls": N_CALLS,
        "n_per_call": N_PER_CALL,
        "calls": calls,
        "all_suggestions_verbatim": all_suggestions,
        "summary": {
            "total_suggestions": len(all_suggestions),
            "total_tokens_input": total_tokens_in,
            "total_tokens_output": total_tokens_out,
            "cost_estimate_dollars_blended_at_0_013_per_1k": total_calls_cost_estimate,
        },
        "invariants": {
            "narrative_memory_write_delta": write_delta,
        },
    }
    out_path = AUDIT_DIR / "q281_3_epsilon_v1_topic_shape_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2))
    print(f"\nWrote {out_path}")
    print(f"Total spend estimate: ~${total_calls_cost_estimate:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
