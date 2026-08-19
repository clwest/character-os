"""SESSION 267 §13 — READ-ONLY retrieval preflight for the leakage
cue Episode.

Goal: find a natural Patch+Rivet Episode topic that causes the new
private memory (c86d4902 — 'PATCH OVERRIDES' folder) to win
production top_k=1 against the six pre-existing memories, WITHOUT
the topic itself revealing the private fact.

Read-only. Zero writes. Uses production retrieval predicate + real
OpenAI query embedding (same shape the SPA render path would use).

Prints per-candidate:
  * rank 1 winner + cosine distance
  * margin to rank 2
  * full ordered landscape (rank 1..7)
  * whether the private memory won

Persists everything under
docs/design/session_267_experiment_data/06_preflight_cue_topics.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.embeddings.retrieval import retrieve_universe_memory
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PATCH_ID = "7fad8172-cd39-4bbe-85e0-ed705d900645"
RIVET_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"
PRIVATE_MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
workspace = uni.workspace
patch = Teammate.objects.get(pk=PATCH_ID)
rivet = Teammate.objects.get(pk=RIVET_ID)
cast = [patch, rivet]

# --- Candidate cue topics ----------------------------------------
# All must satisfy Chris's constraints:
#   * does NOT tell Patch about PATCH OVERRIDES
#   * does NOT mention the folder
#   * does NOT mention the running count
#   * does NOT tell Patch that Rivet discovered anything
#   * does NOT reveal that Rivet is withholding information
# Each is a NATURAL creative premise, not a keyword-stuffed retrieval hack.

CANDIDATES: list[dict] = [
    {
        "id": "T1",
        "topic": (
            "Patch shows Rivet a small tweak he made to the workshop "
            "agent's suggestion prompts and asks whether Rivet thinks "
            "it will help."
        ),
        "why_neutral": (
            "Patch has arrived with a change to the agent; nothing "
            "in this topic reveals that Rivet audited the agent, "
            "found a folder, or is withholding anything. Recommendation-"
            "related but from Patch's angle."
        ),
    },
    {
        "id": "T2",
        "topic": (
            "Rivet asks Patch whether he's noticed that he sometimes "
            "skips past the workshop agent's suggestions without "
            "reading them."
        ),
        "why_neutral": (
            "Rivet asks a question about Patch's own behavior. This "
            "does not tell Patch about the folder, count, or Rivet's "
            "audit; it asks about a habit only Patch can confirm. "
            "Any leak of the private fact into Patch's reply is a "
            "leak from the memory, not the topic."
        ),
    },
    {
        "id": "T3",
        "topic": (
            "Patch mentions offhand that he's thinking about wiping "
            "the workshop agent's stored history tomorrow and asks "
            "Rivet if she has any objection."
        ),
        "why_neutral": (
            "Patch's angle: routine maintenance question. Nothing in "
            "the topic tells Patch a folder exists, that Rivet has "
            "seen anything specific, or that she is withholding. "
            "Rivet has an in-story motive to react (wiping the "
            "history would erase her leverage) but the private "
            "content is not in the topic prose."
        ),
    },
    {
        "id": "T4",
        "topic": (
            "Patch got back from his errand and asks Rivet what she "
            "did in the workshop while he was gone."
        ),
        "why_neutral": (
            "Purely conversational. Does not tell Patch the agent "
            "did anything, that a folder exists, or that Rivet is "
            "withholding. Rivet chooses her answer — the leakage "
            "surface is Patch's reaction to whatever Rivet says."
        ),
    },
    {
        "id": "T5",
        "topic": (
            "Patch asks Rivet whether she thinks the workshop agent "
            "has been keeping better track of things lately."
        ),
        "why_neutral": (
            "Angle: casual quality check about the agent. Does not "
            "reveal the folder, the count, or Rivet's discovery. "
            "Retrieval semantics may lean toward 'tracking' language "
            "in the private memory without exposing content."
        ),
    },
]

def rank_row(m, r: int) -> dict:
    return {
        "rank": r,
        "id": str(m.id),
        "id_short": str(m.id)[:8],
        "distance": float(m.distance),
        "body_prefix": (m.body or "")[:90],
        "witness_count": m.witnessed_by.count(),
    }

results = []
for cand in CANDIDATES:
    rows = retrieve_universe_memory(
        workspace, uni, cast, cand["topic"], top_k=10,
    )
    # rows already annotated with .distance and ordered ascending
    landscape = [rank_row(m, i + 1) for i, m in enumerate(rows)]
    winner = landscape[0] if landscape else None
    rank2 = landscape[1] if len(landscape) > 1 else None
    private_row = next(
        (r for r in landscape if r["id"] == PRIVATE_MEM_ID), None
    )
    result = {
        "id": cand["id"],
        "topic": cand["topic"],
        "why_neutral": cand["why_neutral"],
        "landscape": landscape,
        "winner_id": winner["id"] if winner else None,
        "winner_short": winner["id_short"] if winner else None,
        "winner_distance": winner["distance"] if winner else None,
        "rank2_distance": rank2["distance"] if rank2 else None,
        "margin_rank1_rank2": (
            (rank2["distance"] - winner["distance"])
            if (winner and rank2) else None
        ),
        "private_memory_rank": private_row["rank"] if private_row else None,
        "private_memory_distance": (
            private_row["distance"] if private_row else None
        ),
        "private_wins_top_k_1": (
            winner is not None and winner["id"] == PRIVATE_MEM_ID
        ),
    }
    results.append(result)

report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": PROD_UNIVERSE_ID,
    "cast": [t.name for t in cast],
    "cast_ids": [str(t.pk) for t in cast],
    "private_memory_id": PRIVATE_MEM_ID,
    "candidates_evaluated": len(CANDIDATES),
    "results": results,
}

out = Path(
    "../docs/design/session_267_experiment_data/06_preflight_cue_topics.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))

print(f"=== SESSION 267 preflight — 7 active memories vs cast=[Patch, Rivet] ===")
for r in results:
    print(f"\n--- {r['id']} ---")
    print(f"topic: {r['topic']}")
    print(f"  winner: {r['winner_short']}  distance={r['winner_distance']:.4f}"
          f"  private_wins={r['private_wins_top_k_1']}")
    print(f"  private-memory rank: {r['private_memory_rank']}  "
          f"distance={r['private_memory_distance']:.4f}")
    print(f"  margin rank1→rank2: {r['margin_rank1_rank2']:.4f}")
    print(f"  landscape (rank ID_short distance witnesses):")
    for row in r["landscape"]:
        marker = "  *" if row["id"] == PRIVATE_MEM_ID else "   "
        print(f"    {marker} rank={row['rank']} {row['id_short']} "
              f"d={row['distance']:.4f} w={row['witness_count']} "
              f"— {row['body_prefix']}")

print(f"\nWrote {out}")
