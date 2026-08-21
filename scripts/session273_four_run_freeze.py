"""SESSION 273 §25 — freeze all 4 Ruby failed 90s Compositions.

Read-only. Dumps full observability + statistical cluster analysis
+ per-run corrective hint sha256 (same hint text should mean same
sha256; a divergence would itself be a finding).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from apps.compositions.models import Composition, CompositionStep  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
EPISODE_ID = "77b04b6b-110d-408d-82a3-a04e5ca66417"

# Chris-supplied ordering (create_at ascending)
COMP_IDS = [
    "35eace56-4611-4a0d-abdd-be5d764bb4b8",
    "21e25a2b-47ed-4abc-bcd8-9077fd42d217",
    "f99fe915-dcfb-4832-9f7f-d4e1e5c54a09",
    "fcc52ef6-8c3c-4614-81f9-9251960b0543",
]

# Hard render-side constants for target=90s (from source-of-truth
# _AVATAR_SPEECH_CHARS_PER_SECOND=15 and _DURATION_TOLERANCE=0.20)
HARD_MIN_SECS = 72
HARD_MAX_SECS = 108
HARD_MIN_CHARS = 1080  # 90 * 15 * 0.8
HARD_IDEAL_CHARS = 1350  # 90 * 15
HARD_MAX_CHARS = 1620  # 90 * 15 * 1.2

# K6 corrective-hint math for target=90s under 0.90 multiplier
SYNTH_TARGET_SECS = 81  # round(90 * 0.90)
HINT_MIN_CHARS = 972  # 81 * 15 * 0.8
HINT_IDEAL_CHARS = 1215  # 81 * 15
HINT_MAX_CHARS = 1458  # 81 * 15 * 1.2


def cc(s):
    return len(s or "")


def wc(s):
    return len(re.findall(r"\S+", s or ""))


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def main():
    ruby = Teammate.objects.get(id=RUBY_ID)

    per_run = []
    for i, cid in enumerate(COMP_IDS, start=1):
        c = Composition.objects.get(id=cid)
        first_pass_chars = cc(c.first_pass_synthesis)
        corr_chars = cc(c.corrective_pass_synthesis)
        first_pass_words = wc(c.first_pass_synthesis)
        corr_words = wc(c.corrective_pass_synthesis)
        first_pass_secs = round(first_pass_chars / 15.0, 1) if first_pass_chars else 0
        corr_secs = round(corr_chars / 15.0, 1) if corr_chars else 0
        hint_sha = hashlib.sha256((c.corrective_hint or "").encode()).hexdigest()[:12]

        per_run.append({
            "run": i,
            "composition_id": str(c.id),
            "created_at": _iso(c.created_at),
            "target_duration_seconds": c.target_duration_seconds,
            "operator_topic": c.operator_topic,
            "audience_hint": c.audience_hint,
            "writing_contract_version": c.writing_contract_version,
            "synthesis_attempt_count": c.synthesis_attempt_count,
            "synthesis_predicted_seconds": c.synthesis_predicted_seconds,
            "validation_failure_reason": c.validation_failure_reason,
            "verification_status": c.verification_status,
            "render_dispatched_at": _iso(c.render_dispatched_at),
            "cost_actual_micros": c.cost_actual_micros,
            "final_asset_id": str(c.final_asset_id) if c.final_asset_id else None,
            "knowledge_chunk_ids_len": len(c.knowledge_chunk_ids or []),
            "memory_ids_len": len(c.memory_ids or []),
            "first_pass": {
                "chars": first_pass_chars,
                "words": first_pass_words,
                "predicted_seconds": first_pass_secs,
                "distance_from_hint_min": first_pass_chars - HINT_MIN_CHARS,
                "distance_from_render_min": first_pass_chars - HARD_MIN_CHARS,
                "head_180": (c.first_pass_synthesis or "")[:180],
            },
            "corrective": {
                "chars": corr_chars,
                "words": corr_words,
                "predicted_seconds": corr_secs,
                "distance_from_hint_min": corr_chars - HINT_MIN_CHARS,
                "distance_from_render_min": corr_chars - HARD_MIN_CHARS,
                "cleared_hint_min": corr_chars >= HINT_MIN_CHARS,
                "cleared_render_min": corr_chars >= HARD_MIN_CHARS,
                "head_180": (c.corrective_pass_synthesis or "")[:180],
                "tail_180": (c.corrective_pass_synthesis or "")[-180:],
            },
            "corrective_hint_sha256_12": hint_sha,
            "corrective_hint_bytes": len(c.corrective_hint or ""),
            "error_message": c.error_message,
        })

    # Cluster statistics on corrective outputs
    corr_chars_list = [r["corrective"]["chars"] for r in per_run]
    fp_chars_list = [r["first_pass"]["chars"] for r in per_run]
    cluster = {
        "corrective_chars": corr_chars_list,
        "corrective_chars_min": min(corr_chars_list),
        "corrective_chars_max": max(corr_chars_list),
        "corrective_chars_mean": round(mean(corr_chars_list), 1),
        "corrective_chars_median": round(median(corr_chars_list), 1),
        "corrective_chars_stdev": round(stdev(corr_chars_list), 1) if len(corr_chars_list) > 1 else 0,
        "corrective_cleared_hint_min_count": sum(1 for x in corr_chars_list if x >= HINT_MIN_CHARS),
        "corrective_cleared_render_min_count": sum(1 for x in corr_chars_list if x >= HARD_MIN_CHARS),
        "first_pass_chars": fp_chars_list,
        "first_pass_chars_mean": round(mean(fp_chars_list), 1),
    }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spokesperson_id": RUBY_ID,
        "spokesperson_name": ruby.name,
        "episode_id": EPISODE_ID,
        "target_math": {
            "operator_target_seconds": 90,
            "hard_min_secs": HARD_MIN_SECS,
            "hard_max_secs": HARD_MAX_SECS,
            "hard_min_chars": HARD_MIN_CHARS,
            "hard_ideal_chars": HARD_IDEAL_CHARS,
            "hard_max_chars": HARD_MAX_CHARS,
            "k6_calibration_multiplier": 0.90,
            "synth_target_seconds": SYNTH_TARGET_SECS,
            "hint_min_chars": HINT_MIN_CHARS,
            "hint_ideal_chars": HINT_IDEAL_CHARS,
            "hint_max_chars": HINT_MAX_CHARS,
            "instrumentation_gap_chars": HARD_MIN_CHARS - HINT_MIN_CHARS,  # 108
        },
        "runs": per_run,
        "cluster": cluster,
        "persona_snapshot": {
            "business_brief_chars": cc(ruby.business_brief),
            "personality_chars": cc(ruby.personality),
            "character_point_of_view_chars": cc(ruby.character_point_of_view),
            "voice_signature_phrases_chars": cc(ruby.voice_signature_phrases),
            "voice_avoid_phrases_chars": cc(ruby.voice_avoid_phrases),
            "always_emphasize_chars": cc(ruby.always_emphasize),
            "never_say_chars": cc(ruby.never_say),
            "who_you_help_chars": cc(ruby.who_you_help),
            "what_you_sell_chars": cc(ruby.what_you_sell),
            "desired_feeling_chars": cc(ruby.desired_feeling),
        },
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs" / "design" / "session_273_experiment_data"
        / "09_slice_beta_four_run_failure.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print("=== FOUR-RUN CORRECTIVE OUTPUT ===")
    print(f"{'Run':<4}{'CompID':<12}{'FP chars':<10}{'Corr chars':<12}{'Corr secs':<12}{'Δ hint(972)':<14}{'Δ render(1080)':<16}{'attempt#':<9}")
    for r in per_run:
        cid8 = r['composition_id'][:8]
        print(f"{r['run']:<4}{cid8:<12}{r['first_pass']['chars']:<10}{r['corrective']['chars']:<12}{r['corrective']['predicted_seconds']:<12}{r['corrective']['distance_from_hint_min']:<+14}{r['corrective']['distance_from_render_min']:<+16}{r['synthesis_attempt_count']:<9}")
    print()
    print(f"cluster: chars={cluster['corrective_chars']}, mean={cluster['corrective_chars_mean']}, median={cluster['corrective_chars_median']}, stdev={cluster['corrective_chars_stdev']}")
    print(f"cleared 972 hint-min: {cluster['corrective_cleared_hint_min_count']}/4")
    print(f"cleared 1080 render-min: {cluster['corrective_cleared_render_min_count']}/4")
    print()
    print(f"instrumentation gap: {out['target_math']['instrumentation_gap_chars']} chars ({HINT_MIN_CHARS} hint min vs {HARD_MIN_CHARS} render min)")
    print()
    print("=== per-run corrective hint sha256 (12 chars) ===")
    for r in per_run:
        print(f"  run {r['run']}: {r['corrective_hint_sha256_12']}  (bytes={r['corrective_hint_bytes']})")


if __name__ == "__main__":
    main()
