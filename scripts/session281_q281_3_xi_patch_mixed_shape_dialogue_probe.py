"""SESSION 281 Q281.3-ξ — Patch's Workshop mixed-shape dialogue probe.

Fires ONE real `dialogue_scene` synthesis against Patch's Workshop
with a Q281.3-ζ mixed-shape (D+C, off-stage subject + explicit
complication) topic verbatim. Tests whether rich continuity
substrate protects an off-stage-initiator topic from procedural
collapse.

Topic (verbatim from Q281.3-ζ sample 2.3):
    "The unexplained box begins making a sound at regular
    intervals, forcing Patch to admit only part of what he
    remembers about building it."

Comparative endpoints (already in audit doc):
    * Q281.3-α CONTROL — Fox & Flour customer-cake topic → procedural
    * Q281.3-α TREATMENT — Fox & Flour on-stage-verb topic → event

Isolation guarantees:
    * Zero production code changes.
    * Zero DB mutations — synthesize_dialogue is called directly
      (no Episode created, no Composition persisted, no memory
      promoted).
    * Uses SHIPPED synthesize_dialogue verbatim so knowledge
      retrieval, memory retrieval (top_k=1), synthesis prompt,
      corrective pass, and verifier all fire identically to
      production.
    * ONE run only. No regeneration to chase a preferred answer.

Budget (per §P2 dialogue_scene rule): ~$0.10-$0.15 for one arm.
Patch's Workshop's richer substrate may push token count higher
than Fox & Flour's ~$0.13 per-arm actual.

Evidence artifact:
    docs/design/session281_experiment_data/q281_3_xi_patch_mixed_shape_dialogue_evidence.json

Usage:
    set -a; source .env; set +a
    python scripts/session281_q281_3_xi_patch_mixed_shape_dialogue_probe.py
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
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from character_os.dialogue_synthesis import (  # noqa: E402
    DialogueResult,
    synthesize_dialogue,
)

PATCH_WORKSHOP_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
TOPIC = (
    "The unexplained box begins making a sound at regular "
    "intervals, forcing Patch to admit only part of what he "
    "remembers about building it."
)
TARGET_DURATION_SECONDS = 90

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session281_experiment_data"


def _result_to_dict(result: DialogueResult, elapsed: float) -> dict:
    turns = [
        {
            "line_index": t.line_index,
            "speaker_alias": t.speaker_alias,
            "speaker_name": getattr(t.speaker_teammate, "name", ""),
            "text": t.text,
            "verification_status": t.verification_status,
            "verification_warnings_count": len(t.verification_warnings),
        }
        for t in result.turns
    ]
    return {
        "elapsed_seconds": round(elapsed, 3),
        "model": result.model,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "target_duration_seconds": result.target_duration_seconds,
        "predicted_seconds": round(result.predicted_seconds, 2),
        "total_chars": result.total_chars,
        "attempt_count": result.attempt_count,
        "used_knowledge": result.used_knowledge,
        "overall_verification_status": result.overall_verification_status,
        "chunk_ids": list(result.chunk_ids),
        "memory_ids": list(result.memory_ids),
        "aliases": dict(result.aliases),
        "first_pass_raw": result.first_pass_raw,
        "corrective_hint": result.corrective_hint,
        "corrective_pass_raw": result.corrective_pass_raw,
        "turns": turns,
    }


def _dump_dialogue(result: DialogueResult) -> None:
    print(f"\n=== FINAL DIALOGUE ({len(result.turns)} turns, "
          f"~{result.predicted_seconds:.0f}s, {result.total_chars} chars, "
          f"attempt={result.attempt_count}) ===")
    for t in result.turns:
        name = getattr(t.speaker_teammate, "name", t.speaker_alias)
        print(f"  [{t.line_index:>2}] {name}: {t.text}")


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    universe = Universe.objects.get(pk=PATCH_WORKSHOP_ID)
    workspace = universe.workspace
    # Order cast Patch first (spokesperson-primary) then Rivet, matching
    # the alias-map convention used across Patch's Workshop production
    # compositions. Query-time order alphabetized so we sort explicitly.
    cast_by_name = {
        t.name: t
        for t in Teammate.objects.filter(universe=universe)
    }
    cast = [cast_by_name["Patch"], cast_by_name["Rivet"]]
    print(f"Universe: {universe.name}")
    print(f"Workspace: {workspace.id}")
    print(f"Cast (ordered): {[t.name for t in cast]}")

    mem_count_before = NarrativeMemory.objects.count()
    print(f"NarrativeMemory rows before probe: {mem_count_before}")
    print(f"\nTopic: {TOPIC!r}")

    started_utc = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    result = synthesize_dialogue(
        workspace=workspace,
        cast=cast,
        topic=TOPIC,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        opener=None,
        use_knowledge=True,
        verifier_mode="warn",
        mock_mode=False,
    )
    elapsed = time.time() - t0
    finished_utc = datetime.now(timezone.utc).isoformat()

    mem_count_after = NarrativeMemory.objects.count()
    write_delta = mem_count_after - mem_count_before

    print(f"\n=== SYNTHESIS COMPLETE ===")
    print(f"elapsed={elapsed:.2f}s "
          f"tokens_in={result.tokens_input} tokens_out={result.tokens_output} "
          f"attempts={result.attempt_count} "
          f"predicted={result.predicted_seconds:.1f}s "
          f"chars={result.total_chars} "
          f"verification={result.overall_verification_status}")
    print(f"chunk_ids: {result.chunk_ids}")
    print(f"memory_ids: {result.memory_ids}")

    _dump_dialogue(result)

    print(f"\n=== Post-probe invariants ===")
    print(f"NarrativeMemory count delta (must be 0): {write_delta}")
    assert write_delta == 0, "probe wrote NarrativeMemory rows — abort"

    # Resolve retrieved memory bodies + chunks so audit can quote them.
    memory_details = []
    for mid in result.memory_ids:
        m = NarrativeMemory.objects.filter(pk=mid).first()
        if m is None:
            memory_details.append({"id": mid, "resolved": False})
            continue
        witnesses = sorted(t.name for t in m.witnessed_by.all())
        memory_details.append({
            "id": str(m.id), "resolved": True, "kind": m.kind,
            "status": m.status, "witnesses": witnesses,
            "body": m.body,
        })

    evidence = {
        "probe": "Q281.3-ξ",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "universe_id": PATCH_WORKSHOP_ID,
        "universe_name": universe.name,
        "workspace_id": str(workspace.id),
        "cast": [{"id": str(t.id), "name": t.name} for t in cast],
        "topic": TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "result": _result_to_dict(result, elapsed),
        "resolved_memories": memory_details,
        "invariants": {
            "narrative_memory_write_delta": write_delta,
            "cost_estimate_dollars_at_0_013_per_1k": round(
                (result.tokens_input + result.tokens_output) / 1000.0 * 0.013,
                4,
            ),
        },
    }
    out_path = AUDIT_DIR / "q281_3_xi_patch_mixed_shape_dialogue_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2))
    print(f"\nWrote {out_path}")
    print(f"Estimated spend: ~${evidence['invariants']['cost_estimate_dollars_at_0_013_per_1k']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
