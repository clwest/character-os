"""SESSION 273 CLOSEOUT — invariant / non-change audit.

Read-only. Verifies every invariant Chris named in §6 of the closeout
brief before doc writing / commit. Prints one line per check; exit
non-zero if any expected invariant fails.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from apps.compositions.models import Composition  # noqa: E402
from apps.embeddings.models import (  # noqa: E402
    KnowledgeDocument,
    KnowledgeDocumentSpokesperson,
)
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Episode, EpisodeCast, Universe  # noqa: E402

from character_os.duration_contract import (  # noqa: E402
    AVATAR_SPEECH_SAFE_MAX_CHARS,
    K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    _compression_hint,
    _expansion_hint,
    calibrated_synthesis_target,
)
from character_os.script_synthesis import char_budget_for_duration  # noqa: E402
from character_os.writing_contract import WRITING_CONTRACT_VERSION  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
MASON_ID = "28b9a7ea-8230-4463-8b0d-4ebfabfe11ec"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
KD_ID = "74e7f18f-5b77-459c-bc36-b4ab617d8aca"
WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

# From §11.2 audit (Ruby wizard-default baseline captured 2026-07-23).
RUBY_BASELINE_BRIEF_OPEN = "Ruby owns Fox & Flour Bakery, a neighborhood artisan bakery known for naturally "
RUBY_BASELINE_PERSONALITY_OPEN = "Warm, cheerful, and genuinely caring. Ruby loves helping people find the perfect "

# From §15 ingest (KD content_hash frozen at ingest, unchanged since).
KD_BASELINE_CONTENT_HASH_PREFIX = "7a0e4bd2551f"

CHECKS = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    CHECKS.append((label, condition, detail))
    marker = "✓" if condition else "✗"
    print(f"  {marker} [{status}] {label}: {detail}")


def sha256_first(s, n=12):
    return hashlib.sha256((s or "").encode()).hexdigest()[:n]


def main():
    print("=== SESSION 273 CLOSEOUT INVARIANTS ===\n")

    # Writing Contract
    print("Writing Contract:")
    check(
        "WCV == 6",
        WRITING_CONTRACT_VERSION == 6,
        f"observed={WRITING_CONTRACT_VERSION}",
    )

    # Duration constants
    print("\nDuration constants:")
    check(
        "K6 multiplier == 0.90 (first-pass calibration unchanged)",
        K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 0.90,
        f"observed={K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER}",
    )
    check(
        "AVATAR_SPEECH_SAFE_MAX_CHARS == 1900",
        AVATAR_SPEECH_SAFE_MAX_CHARS == 1900,
        f"observed={AVATAR_SPEECH_SAFE_MAX_CHARS}",
    )
    check(
        "calibrated_synthesis_target(90) == 81",
        calibrated_synthesis_target(90) == 81,
        f"observed={calibrated_synthesis_target(90)}",
    )

    # Hint wording — mechanical produce and check
    print("\n_expansion_hint / _compression_hint text:")
    exp = _expansion_hint(
        actual_chars=623, actual_words=113, actual_seconds=43,
        target_duration_seconds=90,
        effective_ideal=1350, effective_min=1080, effective_max=1620,
    )
    check(
        "_expansion_hint CORRECT_ANCHOR (EXPAND YOUR SCRIPT)",
        "EXPAND YOUR SCRIPT" in exp,
        "SESSION 272 Slice F",
    )
    check(
        "_expansion_hint absent REWRITE THE SAME NARRATIVE ABOVE",
        "REWRITE THE SAME NARRATIVE ABOVE" not in exp,
        "",
    )
    check(
        "_expansion_hint uses 90s raw target under §25 caller",
        "Target is 90s" in exp,
        "",
    )
    check(
        "_expansion_hint honours §25 hint bounds (1080/1350/1620)",
        "AT LEAST 1080 CHARACTERS" in exp
        and "aim for ~1350" in exp
        and "do not exceed 1620" in exp,
        "raw-target bounds for 90s",
    )
    cmp_ = _compression_hint(
        actual_chars=1800, actual_words=300, actual_seconds=120,
        target_duration_seconds=81,
        effective_ideal=1215, effective_min=972, effective_max=1458,
    )
    check(
        "_compression_hint still opens with REWRITE THE SAME NARRATIVE BELOW (unchanged)",
        "REWRITE THE SAME NARRATIVE BELOW" in cmp_,
        "not scope of §25",
    )

    # char_budget_for_duration under provider cap
    print("\nchar_budget_for_duration(target, cap=1900):")
    for target, expected in [
        (60, (900, 720, 1080)),
        (90, (1350, 1080, 1620)),
        (120, (1800, 1440, 1900)),
    ]:
        got = char_budget_for_duration(target, max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS)
        check(
            f"char_budget({target}, cap) == {expected}",
            got == expected,
            f"observed={got}",
        )

    # Q-270-15c gate off
    print("\nQ-270-15c gate:")
    env = os.environ.get("CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT", "")
    check(
        "Q-270-15c env var empty (dormant)",
        not env.strip(),
        f"observed={env!r}",
    )

    # Ruby persona invariants
    print("\nRuby persona:")
    ruby = Teammate.objects.get(id=RUBY_ID)
    check(
        "Ruby.universe_id == Fox & Flour",
        str(ruby.universe_id) == UNIVERSE_ID,
        f"observed={ruby.universe_id}",
    )
    check(
        "Ruby.updated_at unchanged from §13.2 attach (2026-08-20 22:44:22)",
        str(ruby.updated_at).startswith("2026-08-20 22:44:22"),
        f"observed={ruby.updated_at}",
    )
    check(
        "Ruby.business_brief opens with §11.2 baseline text",
        (ruby.business_brief or "").startswith(RUBY_BASELINE_BRIEF_OPEN),
        "byte-identical to wizard-default",
    )
    check(
        "Ruby.personality opens with §11.2 baseline text",
        (ruby.personality or "").startswith(RUBY_BASELINE_PERSONALITY_OPEN),
        "byte-identical to wizard-default",
    )
    for field in ("character_point_of_view", "voice_signature_phrases",
                  "voice_avoid_phrases", "always_emphasize", "never_say",
                  "who_you_help", "what_you_sell", "desired_feeling"):
        v = getattr(ruby, field, None) or ""
        check(
            f"Ruby.{field} still empty",
            v == "",
            "wizard-default baseline preserved",
        )

    # Mason invariants
    print("\nMason persona:")
    mason = Teammate.objects.get(id=MASON_ID)
    check(
        "Mason.universe_id still None (never attached)",
        mason.universe_id is None,
        f"observed={mason.universe_id}",
    )
    check(
        "Mason.updated_at unchanged from 2026-07-23",
        str(mason.updated_at).startswith("2026-07-23"),
        f"observed={mason.updated_at}",
    )

    # Ruby KD invariants
    print("\nRuby KD (74e7f18f):")
    kd = KnowledgeDocument.objects.get(id=KD_ID)
    check(
        "KD.universe_id == Fox & Flour",
        str(kd.universe_id) == UNIVERSE_ID,
        f"observed={kd.universe_id}",
    )
    check(
        "KD content_hash matches §15 ingest prefix",
        (kd.content_hash or "").startswith(KD_BASELINE_CONTENT_HASH_PREFIX),
        f"observed_prefix={(kd.content_hash or '')[:12]}",
    )
    check(
        "KD.status == processed",
        kd.status == "processed",
        f"observed={kd.status}",
    )
    check(
        "KD.is_active == True",
        kd.is_active is True,
        "",
    )
    m2m = list(KnowledgeDocumentSpokesperson.objects.filter(knowledgedocument=kd).values_list("teammate_id", flat=True))
    check(
        "KD m2m spokespeople == [Ruby] only",
        [str(x) for x in m2m] == [RUBY_ID],
        f"observed={[str(x) for x in m2m]}",
    )

    # Universe invariants
    print("\nFox & Flour Universe:")
    uni = Universe.objects.get(id=UNIVERSE_ID)
    check(
        "Universe archived_at is None",
        uni.archived_at is None,
        "",
    )

    # NarrativeMemory + composition counts
    print("\nWorld state:")
    nm_count = NarrativeMemory.objects.filter(universe_id=UNIVERSE_ID).count()
    check(
        "Fox & Flour NarrativeMemory count == 0",
        nm_count == 0,
        f"observed={nm_count}",
    )
    ep_count = Episode.objects.filter(universe_id=UNIVERSE_ID).count()
    print(f"  · Fox & Flour Episode count: {ep_count} (informational; both Chris-created)")
    comp_success = Composition.objects.filter(
        spokesperson_id=RUBY_ID, status="completed"
    ).count()
    comp_failed = Composition.objects.filter(
        spokesperson_id=RUBY_ID, status="failed"
    ).count()
    check(
        "Ruby successful compositions == 2 (video #1 + video #2)",
        comp_success == 2,
        f"observed={comp_success}",
    )
    check(
        "Ruby failed compositions == 4 (pre-§25 cluster preserved)",
        comp_failed == 4,
        f"observed={comp_failed}",
    )

    # Provider mocks + experiment env
    print("\nRuntime environment:")
    experiment_vars = {k: v for k, v in os.environ.items() if "EXPERIMENT" in k.upper()}
    check(
        "No experiment env vars set",
        len(experiment_vars) == 0,
        f"observed={experiment_vars}",
    )
    mock_vars = {k: v for k, v in os.environ.items() if "_MOCK" in k.upper()}
    check(
        "No _MOCK env vars set",
        len(mock_vars) == 0,
        f"observed={mock_vars}",
    )

    # Summary
    print("\n=== SUMMARY ===")
    pass_count = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    print(f"  {pass_count}/{total} invariants PASS")
    fails = [(label, detail) for label, ok, detail in CHECKS if not ok]
    if fails:
        print("  FAILURES:")
        for label, detail in fails:
            print(f"    ✗ {label}: {detail}")
        sys.exit(1)
    else:
        print("  ALL CLEAR.")


if __name__ == "__main__":
    main()
