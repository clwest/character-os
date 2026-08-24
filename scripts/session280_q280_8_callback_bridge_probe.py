"""SESSION 280 Q280.8/A⁹ — Candidate-#3 callback bridge probe.

Three-phase experiment testing whether promoting the model-
authored Q280.9 Candidate #3 ("Tyson joked that the mascot
might be left inside doing community outreach after
closing.") materially influences future Fox & Flour
"Where could this story go next?" suggestions.

Design + rubric + predictions locked at audit doc §77 in
commit f5e6d5e (before this script runs). Approved
Option A¹¹.

Phases
------
1. CONTROL (n=3): refresh suggestions with F&F memory pool
   unchanged (1 memory: Q280.7 cooperation rule).
2. PROMOTE: create Candidate #3 as a NarrativeMemory row via
   the real operator-facing service.
3. TREATMENT (n=3): refresh suggestions with pool = 2
   memories.

Substrate isolation
-------------------
- Suggestion code, prompts, retrieval, verifier, K2,
  characters, existing memories: **untouched**.
- Only substrate mutation: one new NarrativeMemory row via
  the real operator-facing service (reversible via SPA).
- Cache bypassed on every refresh.

Persistence
-----------
- ``docs/design/session280_experiment_data/q280_8_control_evidence.json``
- ``docs/design/session280_experiment_data/q280_8_treatment_evidence.json``

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_8_callback_bridge_probe.py
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

# Candidate #3 verbatim from Q280.9 (evidence:
# session280_experiment_data/q280_9_curator_evidence.json).
CANDIDATE_3_BODY = (
    "Tyson joked that the mascot might be left inside doing "
    "community outreach after closing."
)

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- Helpers -----------------------------------------------------


def _refresh_batch(uni: Universe, phase: str, n: int) -> dict:
    """Fire n cache-bypass suggestion generations and persist
    each raw result."""
    snap = _snapshot(uni)
    task_msg = _build_task_message(snap, n=3)
    refreshes: list[dict] = []
    for i in range(1, n + 1):
        sys.stdout.write(f"  [{phase} refresh {i}/{n}] generating... ")
        sys.stdout.flush()
        payload = suggest_next_episodes(uni, n=3, use_cache=False)
        n_sugg = len(payload.get("suggestions", []))
        sys.stdout.write(
            f"suggestions={n_sugg} tokens_in={payload.get('tokens_input', 0)} "
            f"tokens_out={payload.get('tokens_output', 0)}\n"
        )
        refreshes.append({
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
        "refreshes": refreshes,
    }


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY missing — run set -a; source .env; set +a"
        )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    uni = Universe.objects.get(pk=FOX_AND_FLOUR_ID)
    episode = Episode.objects.get(pk=EPISODE_11_ID)
    composition = Composition.objects.get(pk=COMPOSITION_772E_ID)
    ruby = Teammate.objects.get(universe=uni, name="Ruby")
    tyson = Teammate.objects.get(universe=uni, name="Tyson")
    operator = User.objects.get(email=OPERATOR_EMAIL)

    # Pre-run guardrails (construct validity).
    assert composition.episode_id == episode.id, "comp/episode mismatch"
    assert episode.universe_id == uni.id, "episode/universe mismatch"

    pre_memory_count = NarrativeMemory.objects.filter(
        universe=uni, status="remembered", archived_at__isnull=True,
    ).count()
    print(f"Pre-run F&F REMEMBERED memory count: {pre_memory_count}")
    if pre_memory_count != 1:
        raise RuntimeError(
            f"expected 1 memory pre-run (Q280.7 mutual-departure "
            f"row), got {pre_memory_count}. Aborting."
        )

    cache.clear()
    started_utc = datetime.now(timezone.utc).isoformat()

    # ---- Phase 1 — CONTROL --------------------------------------
    print()
    print("=== Q280.8 Phase 1 — CONTROL (1 memory in pool) ===")
    control = _refresh_batch(uni, phase="CONTROL", n=N_REFRESHES)

    ctrl_path = AUDIT_DIR / "q280_8_control_evidence.json"
    ctrl_path.write_text(json.dumps({
        "started_utc": started_utc,
        "candidate_body": CANDIDATE_3_BODY,
        "universe_id": FOX_AND_FLOUR_ID,
        "episode_id": EPISODE_11_ID,
        "composition_id": COMPOSITION_772E_ID,
        "pre_promotion_memory_count": pre_memory_count,
        "phase": control,
    }, indent=2))
    print(f"Wrote {ctrl_path}")

    # ---- Phase 2 — PROMOTE Candidate #3 -------------------------
    print()
    print("=== Q280.8 Phase 2 — PROMOTE Candidate #3 ===")
    promoted = promote_from_composition(
        composition=composition,
        episode=episode,
        memory_items=[{
            "kind": "dialogue_callback",
            "body": CANDIDATE_3_BODY,
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
    print(f"  kind: {memory.kind}")
    print(f"  embedding present: {memory.embedding_vector is not None}")
    print(
        "  witnesses: "
        f"{[t.name for t in memory.witnessed_by.all()]}"
    )
    print(f"  source_composition_id: {memory.source_composition_id}")
    print(f"  episode_id: {memory.episode_id}")
    print(f"  universe_id: {memory.universe_id}")
    print(f"  body byte-equivalent: {memory.body == CANDIDATE_3_BODY}")

    post_memory_count = NarrativeMemory.objects.filter(
        universe=uni, status="remembered", archived_at__isnull=True,
    ).count()
    print(f"Post-promotion F&F REMEMBERED memory count: {post_memory_count}")
    if post_memory_count != 2:
        raise RuntimeError(
            f"expected 2 memories post-promotion, got {post_memory_count}"
        )

    cache.clear()

    # ---- Phase 3 — TREATMENT ------------------------------------
    print()
    print("=== Q280.8 Phase 3 — TREATMENT (2 memories in pool) ===")
    treatment = _refresh_batch(uni, phase="TREATMENT", n=N_REFRESHES)

    finished_utc = datetime.now(timezone.utc).isoformat()

    tx_path = AUDIT_DIR / "q280_8_treatment_evidence.json"
    tx_path.write_text(json.dumps({
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "candidate_body": CANDIDATE_3_BODY,
        "universe_id": FOX_AND_FLOUR_ID,
        "episode_id": EPISODE_11_ID,
        "composition_id": COMPOSITION_772E_ID,
        "promoted_memory": {
            "id": str(memory.id),
            "kind": memory.kind,
            "weight": memory.weight,
            "witnesses": [t.name for t in memory.witnessed_by.all()],
            "body": memory.body,
            "status": memory.status,
            "embedding_present": memory.embedding_vector is not None,
            "source_composition_id": str(memory.source_composition_id),
            "episode_id": str(memory.episode_id),
            "universe_id": str(memory.universe_id),
        },
        "pre_promotion_memory_count": pre_memory_count,
        "post_promotion_memory_count": post_memory_count,
        "phase": treatment,
    }, indent=2))
    print(f"Wrote {tx_path}")

    print()
    print("=== Q280.8 SUMMARY (counts only; scoring by human) ===")
    for label, block in [("CONTROL", control), ("TREATMENT", treatment)]:
        total = sum(len(r["suggestions"]) for r in block["refreshes"])
        print(f"  {label}: {total} suggestions across n={block['n']} refreshes")
        for r in block["refreshes"]:
            for j, s in enumerate(r["suggestions"], 1):
                print(f"    [{r['refresh_idx']}.{j}] {s['text']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
