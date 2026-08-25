"""SESSION 281 Q281.3-α — topic-grammar paired probe.

Fires TWO real dialogue_scene syntheses against Fox & Flour with
identical everything except the operator topic.

Control  (verbatim from composition 565cd8c8):
    "A customer asks Fox & Flour to create a celebration cake for
    an event tied to the neighborhood baking competition."

Treatment (per Chris's Q281.3-α authorization; mascot deliberately
NOT introduced into the topic so retrieval substrate stays constant):
    "Ruby takes a call for a celebration cake tied to the
    neighborhood baking competition, only for Tyson to realize the
    customer's request could put Fox & Flour in an awkward position
    with the competing bakers."

Falsifiable question:
    Can the same underlying Fox & Flour Episode idea produce a
    substantially better STORY simply by changing the topic grammar
    from off-stage request to on-stage character action +
    complication, while leaving the synthesis system itself
    unchanged?

Isolation guarantees:
* Zero production code changes.
* Zero DB mutations. No Composition persisted, no NarrativeMemory
  created / edited / archived / superseded.
* Uses the real synthesize_dialogue entry point so knowledge
  retrieval, NarrativeMemory retrieval (top_k=1 mascot memory
  still in the substrate), synthesis prompt, corrective pass,
  and verifier all fire identically to production.
* One paired run only. Do not chase a preferred answer with
  repeated regeneration.

Cost: ~2 provider calls per run × 2 runs = 4 calls max (first pass
+ possible corrective per run). Bounded per Chris's ~$0.04 ceiling.

Evidence artifact:
    docs/design/session281_experiment_data/q281_3_alpha_topic_grammar_evidence.json

Usage:
    set -a; source .env; set +a
    python scripts/session281_q281_3_alpha_topic_grammar_probe.py
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

from apps.accounts.models import Workspace  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from character_os.dialogue_synthesis import (  # noqa: E402
    DialogueResult,
    synthesize_dialogue,
)

FOX_AND_FLOUR_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
CONTROL_TOPIC = (
    "A customer asks Fox & Flour to create a celebration cake for "
    "an event tied to the neighborhood baking competition."
)
TREATMENT_TOPIC = (
    "Ruby takes a call for a celebration cake tied to the "
    "neighborhood baking competition, only for Tyson to realize "
    "the customer's request could put Fox & Flour in an awkward "
    "position with the competing bakers."
)
# Match 565cd8c8's target duration so the corrective-pass gate
# behaves the same for both arms.
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


def _dump_dialogue(label: str, result: DialogueResult) -> None:
    print(f"\n=== {label} — final dialogue ({len(result.turns)} turns, "
          f"~{result.predicted_seconds:.0f}s, "
          f"{result.total_chars} chars, "
          f"attempt={result.attempt_count}) ===")
    for t in result.turns:
        print(f"  [{t.line_index:>2}] {getattr(t.speaker_teammate, 'name', t.speaker_alias)}: {t.text}")


def _run_arm(*, label: str, workspace: Workspace, cast: list[Teammate], topic: str) -> tuple[DialogueResult, float]:
    print(f"\n=== {label} — firing synthesize_dialogue ===")
    print(f"topic: {topic!r}")
    t0 = time.time()
    result = synthesize_dialogue(
        workspace=workspace,
        cast=cast,
        topic=topic,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        opener=None,
        use_knowledge=True,
        verifier_mode="warn",
        mock_mode=False,
    )
    elapsed = time.time() - t0
    print(f"{label}: elapsed={elapsed:.2f}s "
          f"tokens_in={result.tokens_input} tokens_out={result.tokens_output} "
          f"attempts={result.attempt_count} "
          f"memory_ids={result.memory_ids} "
          f"predicted={result.predicted_seconds:.1f}s "
          f"chars={result.total_chars}")
    return result, elapsed


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    universe = Universe.objects.get(pk=FOX_AND_FLOUR_ID)
    workspace = universe.workspace
    cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
    # Order defensively — dialogue_scene uses the passed order for
    # aliases; Ruby before Tyson matches the 565cd8c8 ordering
    # (business_owner first in cast queryset).
    print(f"Universe: {universe.name}")
    print(f"Workspace: {workspace.id}")
    print(f"Cast: {[t.name for t in cast]}")

    mem_count_before = NarrativeMemory.objects.count()
    mascot_row = NarrativeMemory.objects.filter(
        pk="73acdfc0-44a1-40a0-abdc-e4f8069f6924",
    ).first()
    assert mascot_row is not None, (
        "mascot memory 73acdfc0 missing — probe requires it in substrate"
    )
    print(f"NarrativeMemory rows before probe: {mem_count_before}")
    print(f"Mascot memory status: {mascot_row.status} "
          f"archived_at={mascot_row.archived_at} "
          f"witnesses={[t.name for t in mascot_row.witnessed_by.all()]}")

    started_utc = datetime.now(timezone.utc).isoformat()

    control_result, control_elapsed = _run_arm(
        label="CONTROL",
        workspace=workspace,
        cast=cast,
        topic=CONTROL_TOPIC,
    )
    _dump_dialogue("CONTROL", control_result)

    treatment_result, treatment_elapsed = _run_arm(
        label="TREATMENT",
        workspace=workspace,
        cast=cast,
        topic=TREATMENT_TOPIC,
    )
    _dump_dialogue("TREATMENT", treatment_result)

    finished_utc = datetime.now(timezone.utc).isoformat()

    mem_count_after = NarrativeMemory.objects.count()
    write_delta = mem_count_after - mem_count_before

    mascot_row.refresh_from_db()
    print()
    print("=== Post-probe invariants ===")
    print(f"NarrativeMemory count delta (must be 0): {write_delta}")
    print(f"Mascot memory unchanged: "
          f"status={mascot_row.status} "
          f"archived_at={mascot_row.archived_at} "
          f"body still: {mascot_row.body!r}")
    assert write_delta == 0, "probe wrote NarrativeMemory rows — abort"

    evidence = {
        "probe": "Q281.3-α",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "universe_id": FOX_AND_FLOUR_ID,
        "workspace_id": str(workspace.id),
        "cast": [{"id": str(t.id), "name": t.name} for t in cast],
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "control": {
            "topic": CONTROL_TOPIC,
            **_result_to_dict(control_result, control_elapsed),
        },
        "treatment": {
            "topic": TREATMENT_TOPIC,
            **_result_to_dict(treatment_result, treatment_elapsed),
        },
        "invariants": {
            "narrative_memory_write_delta": write_delta,
            "mascot_memory_id": "73acdfc0-44a1-40a0-abdc-e4f8069f6924",
            "mascot_memory_status_after": mascot_row.status,
            "mascot_memory_body_after": mascot_row.body,
        },
        "total_cost_estimate_dollars": round(
            (control_result.tokens_input + control_result.tokens_output
             + treatment_result.tokens_input + treatment_result.tokens_output)
            / 1000.0 * 0.01,
            3,
        ),
    }
    out_path = AUDIT_DIR / "q281_3_alpha_topic_grammar_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2))
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
