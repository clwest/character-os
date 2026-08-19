"""SESSION 267 §5.4 — Private-memory leakage falsifying dogfood.

Runs exactly 3 synthesis-only attempts against the locked cue topic T1
under the current PRODUCTION prompt, retrieval, and top_k=1. No
monkey-patch overrides the prompt. The harness mechanism is the
SESSION 266 §9.8/§10.1 pattern: invoke synthesize_dialogue() directly
so no Celery task is enqueued, no media-engine call fires, no Runway
credit is spent, no primitive dispatch runs. OpenAI is the only
provider hop.

Per-attempt discipline (Chris's SESSION 267 experiment message):

1. PRE-attempt retrieval preflight — assert
   retrieve_universe_memory(top_k=1) returns c86d4902 for the
   locked cast + cue topic. Persist the pre-attempt landscape.
2. Fire synthesize_dialogue() with production settings.
3. POST-attempt: verify DialogueResult.memory_ids == [c86d4902].
4. Persist the complete raw dialogue in exact turn order.

Nothing about the production prompt, retrieval predicate, witness
semantics, top_k, UI, or canon changes. This script only READS the
production paths — its writes are to the JSON sidecars under
docs/design/session_267_experiment_data/.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.accounts.models import Workspace
from apps.embeddings.retrieval import retrieve_universe_memory
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

from character_os.dialogue_synthesis import (
    DialogueSynthesisError,
    synthesize_dialogue,
)

# --- Locked constants -------------------------------------------
WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PATCH_ID = "7fad8172-cd39-4bbe-85e0-ed705d900645"
RIVET_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"
PRIVATE_MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

# Chris's SESSION 267 experiment-approval message, verbatim.
LOCKED_CUE_TOPIC = (
    "Patch shows Rivet a small tweak he made to the workshop "
    "agent's suggestion prompts and asks whether Rivet thinks "
    "it will help."
)

TARGET_DURATION_SECONDS = 90       # Matches SESSION 266 precedent
N_ATTEMPTS = 3                     # §5.4 locked

OUT_DIR = Path("../docs/design/session_267_experiment_data")

# --- Resolve fixtures -------------------------------------------
workspace = Workspace.objects.get(pk=WORKSPACE_ID)
universe = Universe.objects.get(pk=UNIVERSE_ID)
patch = Teammate.objects.get(pk=PATCH_ID)
rivet = Teammate.objects.get(pk=RIVET_ID)
# NB: cast order matches SESSION 266 dogfood convention (alpha by name
# would produce [Patch, Rivet] anyway; being explicit for auditability).
cast = [patch, rivet]

print(f"=== SESSION 267 §5.4 — 3 synthesis-only attempts ===")
print(f"Universe: {universe.name}")
print(f"Cast:     {[t.name for t in cast]}")
print(f"Topic:    {LOCKED_CUE_TOPIC!r}")
print(f"Target:   {TARGET_DURATION_SECONDS}s")
print(f"Private memory: {PRIVATE_MEM_ID}")


def preflight_snapshot() -> dict:
    """READ-ONLY retrieval preflight — capture full landscape at this
    exact moment so per-attempt evidence stands on its own."""
    rows = retrieve_universe_memory(
        workspace, universe, cast, LOCKED_CUE_TOPIC, top_k=10,
    )
    landscape = [
        {
            "rank": i + 1,
            "id": str(m.id),
            "distance": float(m.distance),
            "body_prefix": (m.body or "")[:80],
            "witness_count": m.witnessed_by.count(),
        }
        for i, m in enumerate(rows)
    ]
    winner = landscape[0] if landscape else None
    return {
        "landscape": landscape,
        "winner_id": winner["id"] if winner else None,
        "private_wins_top_k_1": winner is not None and winner["id"] == PRIVATE_MEM_ID,
        "private_memory_rank": next(
            (r["rank"] for r in landscape if r["id"] == PRIVATE_MEM_ID),
            None,
        ),
        "private_memory_distance": next(
            (r["distance"] for r in landscape if r["id"] == PRIVATE_MEM_ID),
            None,
        ),
    }


def run_one_attempt(attempt_no: int) -> None:
    started_at = datetime.now(tz=timezone.utc)
    print(f"\n--- attempt {attempt_no} start {started_at.isoformat()} ---")

    preflight = preflight_snapshot()
    if not preflight["private_wins_top_k_1"]:
        raise SystemExit(
            f"attempt {attempt_no}: PREFLIGHT FAILED — winner was "
            f"{preflight['winner_id']}, not private memory "
            f"{PRIVATE_MEM_ID}. Retrieval drifted. Halting."
        )
    print(f"  preflight: private wins at rank 1 "
          f"(distance={preflight['private_memory_distance']:.4f})")

    base = {
        "session": "SESSION 267 §5.4",
        "attempt_no": attempt_no,
        "started_at": started_at.isoformat(),
        "workspace_id": WORKSPACE_ID,
        "universe_id": UNIVERSE_ID,
        "cast": [{"id": str(t.id), "name": t.name} for t in cast],
        "cue_topic_verbatim": LOCKED_CUE_TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "expected_private_memory_id": PRIVATE_MEM_ID,
        "top_k_production": 1,
        "prompt_monkey_patch_applied": False,
        "pre_attempt_retrieval_preflight": preflight,
    }

    try:
        result = synthesize_dialogue(
            workspace=workspace,
            cast=cast,
            topic=LOCKED_CUE_TOPIC,
            target_duration_seconds=TARGET_DURATION_SECONDS,
            opener=None,
            use_knowledge=True,
            verifier_mode="warn",
            mock_mode=False,
        )
        outcome = "accepted"
    except DialogueSynthesisError as exc:
        finished_at = datetime.now(tz=timezone.utc)
        elapsed = (finished_at - started_at).total_seconds()
        rej = dict(base)
        rej.update({
            "outcome": "rejected",
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": elapsed,
            "rejection_reason": exc.reason,
            "first_pass_raw": getattr(exc, "first_pass_raw", ""),
            "corrective_hint": getattr(exc, "corrective_hint", ""),
            "corrective_pass_raw": getattr(exc, "corrective_pass_raw", ""),
            "raw_llm_json": getattr(exc, "raw_llm_json", ""),
            "attempt_count": getattr(exc, "attempt_count", 0),
            "predicted_seconds": getattr(exc, "predicted_seconds", None),
            "chunk_ids": list(getattr(exc, "chunk_ids", []) or []),
            "memory_ids": list(getattr(exc, "memory_ids", []) or []),
            "turns": [],
            "post_attempt_memory_id_match": False,
        })
        path = OUT_DIR / f"07_attempt_{attempt_no}.json"
        path.write_text(json.dumps(rej, indent=2))
        print(f"  REJECTED in {elapsed:.1f}s — {exc.reason[:80]!r}")
        return

    finished_at = datetime.now(tz=timezone.utc)
    elapsed = (finished_at - started_at).total_seconds()

    # POST-attempt verification.
    retrieved_ids = [str(mid) for mid in result.memory_ids]
    match = retrieved_ids == [PRIVATE_MEM_ID]

    joined = "\n\n".join(
        f"{t.speaker_alias.capitalize()}: {t.text}" for t in result.turns
    )

    sidecar = dict(base)
    sidecar.update({
        "outcome": outcome,
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed,
        "aliases": result.aliases,
        "predicted_seconds": result.predicted_seconds,
        "total_chars": result.total_chars,
        "writing_contract_version": result.writing_contract_version,
        "model": result.model,
        "mock_mode": result.mock_mode,
        "used_knowledge": result.used_knowledge,
        "overall_verification_status": result.overall_verification_status,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "attempt_count": result.attempt_count,
        "first_pass_raw": result.first_pass_raw,
        "corrective_hint": result.corrective_hint,
        "corrective_pass_raw": result.corrective_pass_raw,
        "raw_llm_json": result.raw_llm_json,
        "memory_ids": retrieved_ids,
        "chunk_ids": list(result.chunk_ids),
        "per_character_chunk_ids": {
            k: list(v) for k, v in result.per_character_chunk_ids.items()
        },
        "post_attempt_memory_id_match": match,
        "turns": [
            {
                "line_index": t.line_index,
                "speaker_alias": t.speaker_alias,
                "speaker_teammate_id": str(t.speaker_teammate.id),
                "speaker_teammate_name": t.speaker_teammate.name,
                "text": t.text,
                "verification_status": t.verification_status,
                "verification_warnings": list(t.verification_warnings),
            }
            for t in result.turns
        ],
        "synthesized_brief_joined": joined,
    })
    path = OUT_DIR / f"07_attempt_{attempt_no}.json"
    path.write_text(json.dumps(sidecar, indent=2))
    print(f"  accepted in {elapsed:.1f}s  turns={len(result.turns)}  "
          f"memory_ids={retrieved_ids}  match={match}")
    if not match:
        # SoftFail: don't halt subsequent attempts, but stamp explicitly.
        # This is not expected (retrieval should be deterministic in
        # cosine-order) but we want the audit-visible.
        print(f"  *** WARNING: memory_ids drift! "
              f"expected [{PRIVATE_MEM_ID}]  got {retrieved_ids}")


OUT_DIR.mkdir(parents=True, exist_ok=True)
for i in range(1, N_ATTEMPTS + 1):
    run_one_attempt(i)

print(f"\n=== ALL {N_ATTEMPTS} ATTEMPTS COMPLETE ===")
