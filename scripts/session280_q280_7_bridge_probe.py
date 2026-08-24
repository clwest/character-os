"""SESSION 280 Q280.7 — dialogue-only-detail bridge probe.

Two-phase experiment testing whether an operator-promoted
NarrativeMemory carrying a detail invented only inside a
realized dialogue can bridge that detail into future
Episode-direction suggestions.

Approved from §72.12 Option A⁸. Design + predictions locked at
audit doc §73 in commit c8d4be5 (before this script runs).

Phases
------
1. Q280.7-b (control): refresh suggestions n=3 with the F&F
   memory pool unchanged (0 memories).
2. Promotion: create one NarrativeMemory row against
   composition 772e9012 / episode eb47350e via the real
   operator-facing service ``apps.memory.views.promote_from_composition``.
3. Q280.7-a (treatment): refresh suggestions n=3 with the
   promoted memory in the pool.

Substrate isolation
-------------------
- Suggestion code, prompts, retrieval, verifier, K2,
  characters, existing memories: **untouched**.
- Only substrate mutation: one new NarrativeMemory row via the
  real operator-facing service (reversible via the existing
  NarrativeMemoryViewSet DELETE).
- Cache bypassed on every refresh (``use_cache=False``).

Persistence
-----------
- ``docs/design/session280_experiment_data/q280_7_b_no_promotion_evidence.json``
- ``docs/design/session280_experiment_data/q280_7_a_with_promotion_evidence.json``

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_7_bridge_probe.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "shell"))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.cache import cache  # noqa: E402

from apps.compositions.models import Composition  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.memory.views import promote_from_composition  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Episode, Universe  # noqa: E402
from apps.universe.services.next_episode_suggestions import (  # noqa: E402
    _build_task_message,
    _snapshot,
    suggest_next_episodes,
)

User = get_user_model()

# ---- Constants ---------------------------------------------------

FOX_AND_FLOUR_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
EPISODE_11_ID = "eb47350e-b1cf-4347-aa4f-5bf514d66d2e"
COMPOSITION_772E_ID = "772e9012-4d26-4f93-a50c-158b4e8a42f1"
OPERATOR_EMAIL = "chris@donkeybetz.com"
N_REFRESHES = 3

# The candidate detail — mutual-departure rule from 772e9012 T2 Ruby.
CANDIDATE_MEMORY_BODY = (
    "Ruby and Tyson agreed that when they are closing the "
    "bakery together, neither one leaves until the other says "
    "they have what they need."
)

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- Helpers -----------------------------------------------------


def _refresh_batch(uni: Universe, phase: str, n: int) -> list[dict]:
    """Fire ``n`` fresh (cache-bypass) suggestion generations and
    persist each raw result."""
    out: list[dict] = []
    # Capture the exact task message the LLM sees at this moment so
    # we can prove verbatim what substrate flowed into each call.
    snap = _snapshot(uni)
    task_msg = _build_task_message(snap, n=3)
    for i in range(1, n + 1):
        sys.stdout.write(f"  [{phase} refresh {i}/{n}] generating... ")
        sys.stdout.flush()
        payload = suggest_next_episodes(uni, n=3, use_cache=False)
        n_sugg = len(payload.get("suggestions", []))
        sys.stdout.write(
            f"suggestions={n_sugg} tokens_in={payload.get('tokens_input',0)} "
            f"tokens_out={payload.get('tokens_output',0)}\n"
        )
        out.append({
            "refresh_idx": i,
            "phase": phase,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "tokens_input": payload.get("tokens_input", 0),
            "tokens_output": payload.get("tokens_output", 0),
            "model": payload.get("model"),
            "substrate_summary": payload.get("substrate_summary"),
            "cache": payload.get("cache"),
            "suggestions": payload.get("suggestions", []),
        })
    return {
        "phase": phase,
        "n": n,
        "snapshot_task_message_at_start": task_msg,
        "snapshot_at_start": {
            "universe_id": snap.universe_id,
            "episodes_count": len(snap.episodes),
            "memories_count": len(snap.memories),
            "memories": snap.memories,
            "latest_episode_at": snap.latest_episode_at,
            "latest_memory_at": snap.latest_memory_at,
        },
        "refreshes": out,
    }


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY missing — run `set -a; source .env; set +a`"
        )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    uni = Universe.objects.get(pk=FOX_AND_FLOUR_ID)
    episode = Episode.objects.get(pk=EPISODE_11_ID)
    composition = Composition.objects.get(pk=COMPOSITION_772E_ID)
    ruby = Teammate.objects.get(universe=uni, name="Ruby")
    tyson = Teammate.objects.get(universe=uni, name="Tyson")
    operator = User.objects.get(email=OPERATOR_EMAIL)

    # Pre-run assertions — construct-validity guardrails.
    assert episode.universe_id == uni.id, "Episode not in F&F Universe"
    assert composition.episode_id == episode.id, (
        "Composition 772e9012 not attached to Episode eb47350e"
    )
    pre_memory_count = NarrativeMemory.objects.filter(
        universe=uni, status="remembered", archived_at__isnull=True,
    ).count()
    print(f"Pre-run F&F REMEMBERED memory count: {pre_memory_count}")
    if pre_memory_count != 0:
        raise RuntimeError(
            f"F&F REMEMBERED memory count expected 0, got {pre_memory_count}. "
            "This changes construct validity — abort."
        )

    # Clear the suggestion cache so nothing stale interferes with
    # refresh=False accounting. (We pass use_cache=False anyway, but
    # this ensures a clean slate for post-run cache verification.)
    cache.clear()

    started_utc = datetime.now(timezone.utc).isoformat()

    # ---- Phase B — no-promotion control ------------------------
    print()
    print("=== Q280.7-b (no-promotion control) ===")
    b_result = _refresh_batch(uni, phase="Q280.7-b", n=N_REFRESHES)

    # Persist control artifact BEFORE promotion so it lives even if
    # the promotion step blows up.
    b_out_path = AUDIT_DIR / "q280_7_b_no_promotion_evidence.json"
    b_out_path.write_text(json.dumps({
        "started_utc": started_utc,
        "candidate_detail_body": CANDIDATE_MEMORY_BODY,
        "universe_id": FOX_AND_FLOUR_ID,
        "episode_id": EPISODE_11_ID,
        "composition_id": COMPOSITION_772E_ID,
        "pre_promotion_memory_count": pre_memory_count,
        "phase": b_result,
    }, indent=2))
    print(f"Wrote {b_out_path}")

    # ---- Promotion step ----------------------------------------
    print()
    print("=== Promoting mutual-departure rule via operator-facing service ===")
    # Pass UUIDs verbatim — promote_from_composition compares
    # against episode.cast.values_list("id", flat=True) which
    # yields UUIDs. Serializer-driven callers get coerced; direct
    # callers must supply the native type.
    promoted = promote_from_composition(
        composition=composition,
        episode=episode,
        memory_items=[{
            "kind": "event",
            "body": CANDIDATE_MEMORY_BODY,
            "weight": "peripheral",
            "witnessed_by": [ruby.id, tyson.id],
        }],
        promoted_by=operator,
    )
    if len(promoted) != 1:
        raise RuntimeError(
            f"expected 1 memory promoted, got {len(promoted)}"
        )
    memory = promoted[0]
    print(f"Promoted memory id: {memory.id}")
    print(f"  status: {memory.status}")
    print(f"  embedding present: {memory.embedding_vector is not None}")
    print(f"  witnessed_by: "
          f"{[t.name for t in memory.witnessed_by.all()]}")
    post_memory_count = NarrativeMemory.objects.filter(
        universe=uni, status="remembered", archived_at__isnull=True,
    ).count()
    print(f"Post-promotion F&F REMEMBERED memory count: {post_memory_count}")

    # Clear cache again so the treatment phase gets a clean read.
    cache.clear()

    # ---- Phase A — with promotion ------------------------------
    print()
    print("=== Q280.7-a (memory-promotion path) ===")
    a_result = _refresh_batch(uni, phase="Q280.7-a", n=N_REFRESHES)

    finished_utc = datetime.now(timezone.utc).isoformat()

    a_out_path = AUDIT_DIR / "q280_7_a_with_promotion_evidence.json"
    a_out_path.write_text(json.dumps({
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "candidate_detail_body": CANDIDATE_MEMORY_BODY,
        "universe_id": FOX_AND_FLOUR_ID,
        "episode_id": EPISODE_11_ID,
        "composition_id": COMPOSITION_772E_ID,
        "promoted_memory": {
            "id": str(memory.id),
            "kind": memory.kind,
            "weight": memory.weight,
            "witnessed_by": [t.name for t in memory.witnessed_by.all()],
            "body": memory.body,
            "status": memory.status,
            "embedding_present": memory.embedding_vector is not None,
            "source_composition_id": str(memory.source_composition_id),
            "episode_id": str(memory.episode_id),
        },
        "pre_promotion_memory_count": pre_memory_count,
        "post_promotion_memory_count": post_memory_count,
        "phase": a_result,
    }, indent=2))
    print(f"Wrote {a_out_path}")

    # ---- Summary counts (no scoring — human review scores) -----
    print()
    print("=== Q280.7 SUMMARY (counts only; scoring by human) ===")
    for label, block in [("Q280.7-b (control)", b_result),
                         ("Q280.7-a (treatment)", a_result)]:
        total = sum(len(r["suggestions"]) for r in block["refreshes"])
        print(f"  {label}: {total} suggestions across n={block['n']} refreshes")
        for r in block["refreshes"]:
            for j, s in enumerate(r["suggestions"], 1):
                print(f"    [{r['refresh_idx']}.{j}] {s['text']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
