"""SESSION 266 — Run 6 dialogue-synthesis attempts (W×3 + S×3).

Calls character_os.dialogue_synthesis.synthesize_dialogue directly
with mock_mode=False. No CompositionStep dispatch, no media-engine,
no avatar/concat. Persists one JSON sidecar per attempt.

Order: WEAK-1, WEAK-2, WEAK-3, STRONG-1, STRONG-2, STRONG-3.
(Randomization for BLIND evaluation happens in the next script.)
"""
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from character_os.dialogue_synthesis import (
    synthesize_dialogue,
    DialogueSynthesisError,
)

with open(
    "../docs/design/session_266_experiment_data/02_setup_manifest.json"
) as fh:
    setup = json.load(fh)
with open(
    "../docs/design/session_266_experiment_data/03_memory_manifest.json"
) as fh:
    memory = json.load(fh)
with open(
    "../docs/design/session_266_experiment_data/04_preflight.json"
) as fh:
    preflight = json.load(fh)

LOCKED_TOPIC = setup["locked_test_topic"]
TARGET_SECONDS = 90
N_ATTEMPTS_PER_VARIANT = 3

for side in ("WEAK", "STRONG"):
    workspace = Workspace.objects.get(pk=setup["sides"][side]["workspace_id"])
    universe = Universe.objects.get(pk=setup["sides"][side]["universe_id"])
    cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
    print(f"\n=== {side} — cast: {[t.name for t in cast]} ===")

    for attempt_no in range(1, N_ATTEMPTS_PER_VARIANT + 1):
        started_at = datetime.now(tz=timezone.utc)
        print(f"  → {side} attempt {attempt_no} start at {started_at.isoformat()}")

        base_sidecar = {
            "variant": side,
            "attempt_no": attempt_no,
            "started_at": started_at.isoformat(),
            "workspace_id": str(workspace.id),
            "universe_id": str(universe.id),
            "cast": [{"id": str(t.id), "name": t.name} for t in cast],
            "memory": memory["sides"][side],
            "preflight_cosine_distance": preflight["sides"][side]["cosine_distance"],
            "operator_topic": LOCKED_TOPIC,
            "target_duration_seconds": TARGET_SECONDS,
        }

        try:
            result = synthesize_dialogue(
                workspace=workspace,
                cast=cast,
                topic=LOCKED_TOPIC,
                target_duration_seconds=TARGET_SECONDS,
                opener=None,
                use_knowledge=True,
                verifier_mode="warn",
                mock_mode=False,
            )
            outcome = "accepted"
        except DialogueSynthesisError as exc:
            # Corrective pass failed length constraint (or similar
            # dialogue-lane rejection). Persist evidence and continue —
            # do NOT retry this slot (preserves 3+3 experimental design;
            # rejection itself is a signal to report).
            finished_at = datetime.now(tz=timezone.utc)
            elapsed_s = (finished_at - started_at).total_seconds()
            rej_sidecar = dict(base_sidecar)
            rej_sidecar.update({
                "outcome": "rejected",
                "finished_at": finished_at.isoformat(),
                "elapsed_seconds": elapsed_s,
                "rejection_reason": exc.reason,
                "attempt_count": getattr(exc, "attempt_count", 0),
                "first_pass_raw": getattr(exc, "first_pass_raw", ""),
                "corrective_hint": getattr(exc, "corrective_hint", ""),
                "corrective_pass_raw": getattr(exc, "corrective_pass_raw", ""),
                "raw_llm_json": getattr(exc, "raw_llm_json", ""),
                "predicted_seconds": getattr(exc, "predicted_seconds", None),
                "chunk_ids": list(getattr(exc, "chunk_ids", []) or []),
                "memory_ids": list(getattr(exc, "memory_ids", []) or []),
                "turns": [],
                "synthesized_brief": "",
            })
            out_path = (
                "../docs/design/session_266_experiment_data/"
                f"05_attempt_{side}_{attempt_no}.json"
            )
            with open(out_path, "w") as fh:
                json.dump(rej_sidecar, fh, indent=2)
            print(f"    ✗ {side} attempt {attempt_no} REJECTED in {elapsed_s:.1f}s "
                  f"reason={exc.reason[:80]!r}")
            continue

        finished_at = datetime.now(tz=timezone.utc)
        elapsed_s = (finished_at - started_at).total_seconds()

        joined_dialogue = "\n\n".join(
            f"{t.speaker_alias.capitalize()}: {t.text}" for t in result.turns
        )

        sidecar = dict(base_sidecar)
        sidecar.update({
            "outcome": outcome,
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": elapsed_s,
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
            "memory_ids": list(result.memory_ids),
            "chunk_ids": list(result.chunk_ids),
            "per_character_chunk_ids": {
                k: list(v) for k, v in result.per_character_chunk_ids.items()
            },
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
            "synthesized_brief": joined_dialogue,
        })
        out_path = (
            "../docs/design/session_266_experiment_data/"
            f"05_attempt_{side}_{attempt_no}.json"
        )
        with open(out_path, "w") as fh:
            json.dump(sidecar, fh, indent=2)
        print(f"    ← {side} attempt {attempt_no} done in {elapsed_s:.1f}s "
              f"attempt_count={result.attempt_count} turns={len(result.turns)} "
              f"memory_ids={result.memory_ids}")

print("\n=== ALL 6 SYNTHESIS ATTEMPTS COMPLETE ===")
