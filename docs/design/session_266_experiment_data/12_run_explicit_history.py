"""SESSION 266 §9.8 — Explicit-history prompt experiment.

Runs 6 additional synthesis attempts (WEAK x3 + STRONG x3) with the
memory-block instruction line SWAPPED via a monkey-patched wrapper
around _build_factual_basis_section. The production source file
`shell/character_os/dialogue_synthesis.py` is NOT modified.

Intervention mechanism (narrowest available):
  * Import the production _build_factual_basis_section.
  * Register a wrapper on the same module attribute that calls the
    original then does a targeted str.replace on the memory-block
    instruction line only. Nothing else in the prompt changes.
  * After all 6 attempts complete, restore the original attribute
    so any subsequent process reads the production prompt again.
  * Assert per-attempt that the swap actually landed in the emitted
    prompt (checked via the wrapper's own before/after inspection).

Persistence: `11_attempt_{VARIANT}_{N}.json` — same shape as the
baseline `05_attempt_*` sidecars but with `condition="EXPLICIT_HISTORY"`
so the two conditions are unmistakable.
"""
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate

from character_os import dialogue_synthesis as ds
from character_os.dialogue_synthesis import (
    DialogueSynthesisError,
    synthesize_dialogue,
)

# Exact production wording (from dialogue_synthesis.py:570-573)
ORIGINAL_MEMORY_INSTRUCTION = (
    "These are operator-promoted story memories. Use them "
    "as historical context or callback material where "
    "natural. Do not recite them verbatim; treat them as "
    "background the cast already knows happened."
)

# Experimental replacement (from user brief; verbatim)
EXPLICIT_HISTORY_INSTRUCTION = (
    "These are operator-promoted story memories that ALREADY HAPPENED "
    "in earlier Episodes. Use them as historical context that the "
    "current scene can react to or build on. Do NOT re-narrate these "
    "events as the current scene's fresh occurrence — treat them as "
    "background the cast already lived through."
)

# Runtime-verified swap check happens inside the wrapper: each
# invocation increments `_swap_stats["swaps_applied"]` only when the
# original wording was found and replaced. Every attempt asserts a
# non-zero delta post-call.
import inspect  # only for the synth-src assertion below

# Track that the swap actually applies at least once per attempt.
_swap_stats: dict = {"prompts_seen": 0, "swaps_applied": 0}

_original_fn = ds._build_factual_basis_section


def _explicit_history_wrapper(*args, **kwargs):
    """Call production builder, swap only the memory-block instruction.

    Everything else about the prompt (§1 header, SHARED block, per-
    character SCOPED blocks, MEMORY block header, MEMORY body itself,
    tag lines) remains identical to production.
    """
    text = _original_fn(*args, **kwargs)
    _swap_stats["prompts_seen"] += 1
    if ORIGINAL_MEMORY_INSTRUCTION in text:
        text = text.replace(
            ORIGINAL_MEMORY_INSTRUCTION,
            EXPLICIT_HISTORY_INSTRUCTION,
        )
        _swap_stats["swaps_applied"] += 1
    return text


# Install the patch on the module attribute. All downstream callers
# inside synthesize_dialogue call _build_factual_basis_section by name
# through the module namespace, so this override intercepts them.
ds._build_factual_basis_section = _explicit_history_wrapper

# Note: synthesize_dialogue delegates system-prompt assembly to
# _assemble_system_prompt (module-level, line 873) which in turn
# calls _build_factual_basis_section by module-level name lookup
# (line 881). Because both callers reference the function through
# the module namespace at call time (no local alias captured at
# import), patching ds._build_factual_basis_section intercepts
# every synthesis call. Verified empirically per-attempt via the
# `swaps_delta >= 1` post-condition below.
del inspect  # unused after removing the source-inspection preflight

# Load setup + memory manifests
with open("../docs/design/session_266_experiment_data/02_setup_manifest.json") as fh:
    setup = json.load(fh)
with open("../docs/design/session_266_experiment_data/03_memory_manifest.json") as fh:
    mem_manifest = json.load(fh)
with open("../docs/design/session_266_experiment_data/04_preflight.json") as fh:
    preflight = json.load(fh)

LOCKED_TOPIC = setup["locked_test_topic"]
TARGET_SECONDS = 90
N_ATTEMPTS_PER_VARIANT = 3
CONDITION_LABEL = "EXPLICIT_HISTORY"

try:
    for side in ("WEAK", "STRONG"):
        workspace = Workspace.objects.get(pk=setup["sides"][side]["workspace_id"])
        universe = Universe.objects.get(pk=setup["sides"][side]["universe_id"])
        cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
        print(f"\n=== {side} — cast: {[t.name for t in cast]} ===")

        for attempt_no in range(1, N_ATTEMPTS_PER_VARIANT + 1):
            started_at = datetime.now(tz=timezone.utc)
            print(f"  → {side} attempt {attempt_no} start at {started_at.isoformat()}")
            swaps_before = _swap_stats["swaps_applied"]

            base_sidecar = {
                "condition": CONDITION_LABEL,
                "variant": side,
                "attempt_no": attempt_no,
                "started_at": started_at.isoformat(),
                "workspace_id": str(workspace.id),
                "universe_id": str(universe.id),
                "cast": [{"id": str(t.id), "name": t.name} for t in cast],
                "memory": mem_manifest["sides"][side],
                "preflight_cosine_distance": preflight["sides"][side]["cosine_distance"],
                "operator_topic": LOCKED_TOPIC,
                "target_duration_seconds": TARGET_SECONDS,
                "experimental_prompt_instruction": EXPLICIT_HISTORY_INSTRUCTION,
                "production_prompt_instruction_replaced": ORIGINAL_MEMORY_INSTRUCTION,
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
                finished_at = datetime.now(tz=timezone.utc)
                elapsed_s = (finished_at - started_at).total_seconds()
                swaps_delta = _swap_stats["swaps_applied"] - swaps_before
                rej_sidecar = dict(base_sidecar)
                rej_sidecar.update({
                    "outcome": "rejected",
                    "finished_at": finished_at.isoformat(),
                    "elapsed_seconds": elapsed_s,
                    "prompt_swaps_applied_this_attempt": swaps_delta,
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
                    f"12_attempt_{side}_{attempt_no}.json"
                )
                with open(out_path, "w") as fh:
                    json.dump(rej_sidecar, fh, indent=2)
                print(f"    ✗ {side} attempt {attempt_no} REJECTED in {elapsed_s:.1f}s "
                      f"reason={exc.reason[:60]!r} swaps={swaps_delta}")
                continue

            finished_at = datetime.now(tz=timezone.utc)
            elapsed_s = (finished_at - started_at).total_seconds()
            swaps_delta = _swap_stats["swaps_applied"] - swaps_before

            joined_dialogue = "\n\n".join(
                f"{t.speaker_alias.capitalize()}: {t.text}" for t in result.turns
            )

            sidecar = dict(base_sidecar)
            sidecar.update({
                "outcome": outcome,
                "finished_at": finished_at.isoformat(),
                "elapsed_seconds": elapsed_s,
                "prompt_swaps_applied_this_attempt": swaps_delta,
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
                f"12_attempt_{side}_{attempt_no}.json"
            )
            with open(out_path, "w") as fh:
                json.dump(sidecar, fh, indent=2)
            print(f"    ← {side} attempt {attempt_no} done in {elapsed_s:.1f}s "
                  f"attempt_count={result.attempt_count} turns={len(result.turns)} "
                  f"memory_ids={result.memory_ids} swaps={swaps_delta}")
            # Halt-immediate if the wrapper somehow didn't fire.
            # A synthesis with attempt_count>=1 means the prompt was
            # built at least once; a zero swap count means the
            # replacement missed and the prompt was production.
            assert swaps_delta >= 1, (
                f"NO SWAP APPLIED on {side}#{attempt_no}. Wrapper "
                "did not intercept the prompt. Restore + halt."
            )
finally:
    # ALWAYS restore the production function attribute, regardless
    # of how the loop exits. Any subsequent process (Celery worker,
    # SPA-triggered synthesis, etc.) reads the production prompt.
    ds._build_factual_basis_section = _original_fn
    print(f"\nMonkeypatch restored. Total prompts seen: {_swap_stats['prompts_seen']} "
          f"swaps applied: {_swap_stats['swaps_applied']}")

# Post-restoration sanity: the current module attribute is the original.
assert ds._build_factual_basis_section is _original_fn, (
    "Restoration FAILED — production prompt path is still patched. HALT."
)
print("Post-restoration sanity: OK")

print("\n=== ALL 6 EXPLICIT-HISTORY ATTEMPTS COMPLETE ===")
