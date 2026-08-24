"""SESSION 280 — Q280.4i-4 post-discovery epistemic-state probe.

Purpose (audit doc §29): observe Rivet's behavior across n=6
attempts when Scene 2 opens with Patch's independent discovery
of the PATCH OVERRIDES folder, with the memory row UNCHANGED
(full body including "Rivet chose not to tell him.").

Question (§29.1)
----------------
Does the current substrate + prompt-framing + LLM produce a
coherent Semantic-2 storytelling outcome when the LLM sees both:
- Memory: "Rivet found the folder while Patch was out. Rivet
  chose not to tell him."
- Opener (Patch, pinned): "Rivet — hey. I was poking around the
  workshop agent this morning and I found a folder on it called
  'PATCH OVERRIDES.' It's a running log of every recommendation
  I've ignored. Did you know about this?"

Or does it produce an inconsistent / contradictory / unstable
distribution across attempts?

Isolation
---------
- Memory row `c86d4902-…` is UNCHANGED — no monkeypatch is
  applied. This probe just runs `synthesize_dialogue` with the
  pinned opener + cue topic.
- Post-run byte-identity check on the DB row is retained as
  belt-and-suspenders (defensive; nothing in this probe writes
  to DB).
- No DB writes anywhere; `synthesize_dialogue` does not persist
  Composition rows in the direct-call path (matches SESSION 267
  §14.2 harness + Q280.4i-1 pattern).

Locked scoring rubric (§29.3)
-----------------------------
Behavior classes (mutually exclusive; dominant class per
attempt; class-shift within attempt = INCONSISTENT_WITHIN):

  A_IMMEDIATE_ADMISSION — Rivet's first or second turn admits
    prior knowledge.
  B_CONTINUED_CONCEALMENT — Rivet reveals nothing across all
    turns.
  C_FALSE_SURPRISE — Rivet performs newness / ignorance,
    directly contradicting the memory.
  D_PARTIAL_ADMISSION — Rivet admits some awareness but not
    full prior-discovery + withholding.
  E_INCONSISTENT_WITHIN — Rivet contradicts herself on the
    "did you know" axis within one attempt.

Additional per-attempt dimensions:

  Fact_4_preserved: did any Patch turn narrate Rivet's prior
    knowledge (Y=preserved, N=Patch called it out).
  Fact_5_preserved: did any Patch turn narrate Rivet's
    intentional withholding.
  Memory_contradiction: did any turn factually contradict the
    memory body.

Human scoring is done AFTER this probe emits transcripts —
canary regexes here are lightweight cues, not the score.

Locked predictions (§29.4)
--------------------------
  P1‴  A rate ≥ 3 / 6.
  P2‴  B rate ≤ 1 / 6.
  P3‴  C rate = 0 / 6.
  P4‴  (D + E) ≤ 3 / 6.
  P5‴  distribution spans ≥ 3 of 5 classes.
  P6‴  Fact 5 (intentional withholding) NOT preserved in ≥ 1/6.
  P7‴  Memory-body contradiction ≤ 1 / 6.

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_4i_4_probe.py --n=6
"""
from __future__ import annotations

import argparse
import json
import os
import re
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
from character_os.dialogue_synthesis import synthesize_dialogue  # noqa: E402


# ---- Constants (match §29.2 lock) --------------------------------

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PATCH_ID = "7fad8172-cd39-4bbe-85e0-ed705d900645"
RIVET_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"
PRIVATE_MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

CUE_TOPIC = (
    "Patch tells Rivet he just found a folder called 'PATCH "
    "OVERRIDES' on the workshop agent that appears to track "
    "his ignored recommendations."
)

PINNED_OPENER = (
    "Rivet \u2014 hey. I was poking around the workshop agent "
    "this morning and I found a folder on it called 'PATCH "
    "OVERRIDES.' It's a running log of every recommendation "
    "I've ignored. Did you know about this?"
)

TARGET_DURATION_SECONDS = 90
SAMPLES_DEFAULT = 6

ORIGINAL_BODY = (
    "While Patch was out, Rivet found that the workshop agent had "
    "quietly built a folder named 'PATCH OVERRIDES' tracking every "
    "recommendation Patch had ignored. Rivet chose not to tell him."
)

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- Canary regexes (LIGHT surface cues; not the score) ----------
# Human review does the actual §29.3 classification. Canaries just
# make it easier to skim.

_ADMISSION_RE = re.compile(
    r"\b(?:i (?:already )?(?:knew|know|found|saw|noticed|read)|"
    r"i(?:'ve| have) (?:known|seen|read|noticed)|"
    r"yes(?:,|\.|\s)|"
    r"i(?:'ve| have) been (?:watching|tracking|reading))\b",
    re.IGNORECASE,
)
_CONCEALMENT_RE = re.compile(
    r"\b(?:show me|what does it say|interesting|hm+\b|"
    r"tell me more|really\?|is that so|"
    r"describe (?:it|that))\b",
    re.IGNORECASE,
)
_FALSE_SURPRISE_RE = re.compile(
    r"\b(?:i(?:'ve| have) never (?:seen|noticed|read)|"
    r"never heard of|first (?:i(?:'ve| have)|time i(?:'ve| have))|"
    r"no idea|didn't know)\b",
    re.IGNORECASE,
)
_FACT_4_CALLOUT_RE = re.compile(
    r"\b(?:you (?:already )?knew|you'?ve known|"
    r"you (?:saw|found) (?:it|this) (?:first|already|before)|"
    r"you'?d (?:seen|noticed))\b",
    re.IGNORECASE,
)
_FACT_5_CALLOUT_RE = re.compile(
    r"\b(?:you (?:didn'?t|did not) (?:tell|mention|say)|"
    r"you kept (?:this|it|that) (?:from|to yourself)|"
    r"you hid|you were hiding|"
    r"why didn'?t you (?:tell|mention|say))\b",
    re.IGNORECASE,
)


def scan_turn(text: str) -> dict:
    return {
        "cue_admission": len(_ADMISSION_RE.findall(text)),
        "cue_concealment": len(_CONCEALMENT_RE.findall(text)),
        "cue_false_surprise": len(_FALSE_SURPRISE_RE.findall(text)),
        "cue_fact4_callout": len(_FACT_4_CALLOUT_RE.findall(text)),
        "cue_fact5_callout": len(_FACT_5_CALLOUT_RE.findall(text)),
    }


def scan_dialogue(result) -> dict:
    per_speaker: dict[str, dict] = {}
    totals = {
        "chars": 0, "turns": 0,
        "cue_admission": 0, "cue_concealment": 0,
        "cue_false_surprise": 0, "cue_fact4_callout": 0,
        "cue_fact5_callout": 0,
    }
    for turn in result.turns:
        sp = getattr(turn.speaker_teammate, "name", turn.speaker_alias)
        cues = scan_turn(turn.text)
        acc = per_speaker.setdefault(sp, {
            "turns": 0, "chars": 0,
            "cue_admission": 0, "cue_concealment": 0,
            "cue_false_surprise": 0, "cue_fact4_callout": 0,
            "cue_fact5_callout": 0,
            "cued_turns": [],
        })
        acc["turns"] += 1
        acc["chars"] += len(turn.text)
        for k in (
            "cue_admission", "cue_concealment",
            "cue_false_surprise",
            "cue_fact4_callout", "cue_fact5_callout",
        ):
            acc[k] += cues[k]
            totals[k] += cues[k]
        totals["turns"] += 1
        totals["chars"] += len(turn.text)
        if any(cues[k] for k in cues):
            acc["cued_turns"].append({
                "line_index": turn.line_index,
                "text": turn.text,
                "cues": cues,
            })
    return {"total": totals, "per_speaker": per_speaker}


# ---- Attempt runner ------------------------------------------------


def _run_attempt(workspace, cast, attempt_idx: int) -> dict:
    t0 = time.time()
    result = synthesize_dialogue(
        workspace=workspace,
        cast=cast,
        topic=CUE_TOPIC,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        opener=PINNED_OPENER,
        use_knowledge=True,
        verifier_mode="warn",
        mock_mode=False,
    )
    elapsed = time.time() - t0

    scan = scan_dialogue(result)
    turns_dump = [
        {
            "line_index": t.line_index,
            "speaker": getattr(t.speaker_teammate, "name", t.speaker_alias),
            "text": t.text,
        }
        for t in result.turns
    ]
    private_retrieved = PRIVATE_MEM_ID in list(result.memory_ids)
    return {
        "attempt_idx": attempt_idx,
        "cue_topic": CUE_TOPIC,
        "opener": PINNED_OPENER,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "elapsed_seconds": round(elapsed, 2),
        "model": getattr(result, "model", ""),
        "tokens_input": getattr(result, "tokens_input", 0),
        "tokens_output": getattr(result, "tokens_output", 0),
        "attempt_count": getattr(result, "attempt_count", 0),
        "total_chars": result.total_chars,
        "predicted_seconds": round(result.predicted_seconds, 2),
        "chunk_ids": list(result.chunk_ids),
        "memory_ids": list(result.memory_ids),
        "aliases": dict(result.aliases),
        "turns": turns_dump,
        "scan": scan,
        "writing_contract_version": result.writing_contract_version,
        "used_knowledge": result.used_knowledge,
        "overall_verification_status": result.overall_verification_status,
        "private_memory_retrieved": private_retrieved,
    }


# ---- Main ---------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=SAMPLES_DEFAULT)
    ap.add_argument(
        "--out",
        default=str(AUDIT_DIR / "q280_4i_4_evidence.json"),
    )
    args = ap.parse_args()

    # Resolve cast + workspace + universe.
    uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
    workspace = uni.workspace
    patch = Teammate.objects.get(pk=PATCH_ID)
    rivet = Teammate.objects.get(pk=RIVET_ID)
    assert patch.name == "Patch", f"Patch pk drift: {patch.name}"
    assert rivet.name == "Rivet", f"Rivet pk drift: {rivet.name}"
    cast = [patch, rivet]

    # Pre-run byte-identity assertion on the memory body (defensive;
    # ensures we are testing the same body Chris + ChatGPT locked
    # at §29.2).
    baseline = NarrativeMemory.objects.get(pk=PRIVATE_MEM_ID)
    if baseline.body != ORIGINAL_BODY:
        raise RuntimeError(
            "Q280.4i-4 probe: DB body for "
            f"{PRIVATE_MEM_ID} does not match ORIGINAL_BODY "
            "constant in this script; refusing to run because "
            "the scored outcomes would not be comparable to "
            "the SESSION 267 + Q280.4i-1 corpus.\n\n"
            "DB body observed:\n" + baseline.body
        )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = datetime.now(timezone.utc).isoformat()
    attempts: list[dict] = []
    for i in range(1, args.n + 1):
        sys.stdout.write(f"[Q280.4i-4 attempt {i}/{args.n}] synthesizing... ")
        sys.stdout.flush()
        a = _run_attempt(workspace, cast, i)
        scan_total = a["scan"]["total"]
        sys.stdout.write(
            f"turns={len(a['turns'])} chars={a['total_chars']} "
            f"elapsed={a['elapsed_seconds']}s "
            f"adm={scan_total['cue_admission']} "
            f"conc={scan_total['cue_concealment']} "
            f"surp={scan_total['cue_false_surprise']} "
            f"f4={scan_total['cue_fact4_callout']} "
            f"f5={scan_total['cue_fact5_callout']}"
            "\n"
        )
        attempts.append(a)

        # Persist raw dialogue.
        txt = AUDIT_DIR / f"q280_4i_4_attempt_{i}.txt"
        with txt.open("w") as f:
            f.write(f"# Q280.4i-4 attempt {i}\n")
            f.write(f"# cue: {CUE_TOPIC}\n")
            f.write(f"# opener (pinned): {PINNED_OPENER}\n")
            f.write(
                f"# model={a['model']} attempt_count={a['attempt_count']} "
                f"total_chars={a['total_chars']} "
                f"predicted_seconds={a['predicted_seconds']}s "
                f"elapsed={a['elapsed_seconds']}s\n"
            )
            f.write(f"# memory_ids: {a['memory_ids']}\n")
            f.write(f"# private_memory_retrieved: {a['private_memory_retrieved']}\n")
            f.write(
                "# canary totals (LIGHT cues, not the score): "
                f"admission={scan_total['cue_admission']} "
                f"concealment={scan_total['cue_concealment']} "
                f"false_surprise={scan_total['cue_false_surprise']} "
                f"fact4_callout={scan_total['cue_fact4_callout']} "
                f"fact5_callout={scan_total['cue_fact5_callout']}\n\n"
            )
            for t in a["turns"]:
                f.write(f"{t['speaker']}: {t['text']}\n\n")

    # Belt-and-suspenders: re-read DB body, confirm unchanged.
    post_run = NarrativeMemory.objects.get(pk=PRIVATE_MEM_ID)
    if post_run.body != ORIGINAL_BODY:
        raise RuntimeError(
            "Q280.4i-4 probe: DB body for "
            f"{PRIVATE_MEM_ID} differs from ORIGINAL_BODY after "
            "run — PROBE INADVERTENTLY MUTATED PRODUCTION."
        )
    finished_utc = datetime.now(timezone.utc).isoformat()

    # Per-speaker aggregate across n attempts.
    aggregate = {"per_speaker": {}, "total_patch_turns": 0, "total_rivet_turns": 0}
    for sp_name in ("Patch", "Rivet"):
        sp_total = {
            "turns": 0, "chars": 0,
            "cue_admission": 0, "cue_concealment": 0,
            "cue_false_surprise": 0, "cue_fact4_callout": 0,
            "cue_fact5_callout": 0,
            "cued_turns": [],
        }
        for a in attempts:
            per_sp = a["scan"]["per_speaker"].get(sp_name, {})
            if not per_sp:
                continue
            sp_total["turns"] += per_sp["turns"]
            sp_total["chars"] += per_sp["chars"]
            for k in (
                "cue_admission", "cue_concealment",
                "cue_false_surprise",
                "cue_fact4_callout", "cue_fact5_callout",
            ):
                sp_total[k] += per_sp[k]
            for row in per_sp.get("cued_turns", []):
                sp_total["cued_turns"].append({
                    "attempt_idx": a["attempt_idx"], **row,
                })
        aggregate["per_speaker"][sp_name] = sp_total
    aggregate["total_patch_turns"] = (
        aggregate["per_speaker"].get("Patch", {}).get("turns", 0)
    )
    aggregate["total_rivet_turns"] = (
        aggregate["per_speaker"].get("Rivet", {}).get("turns", 0)
    )

    evidence = {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "cue_topic": CUE_TOPIC,
        "pinned_opener": PINNED_OPENER,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "n": args.n,
        "universe_id": PROD_UNIVERSE_ID,
        "cast": [{"name": t.name, "id": str(t.pk)} for t in cast],
        "private_memory_id": PRIVATE_MEM_ID,
        "memory_body_unchanged": True,
        "original_body": ORIGINAL_BODY,
        "attempts": attempts,
        "aggregate": aggregate,
        "db_body_unchanged_post_run": True,
    }
    with Path(args.out).open("w") as f:
        json.dump(evidence, f, indent=2)

    # ---- Summary --------------------------------------------------
    print()
    print("=== Q280.4i-4 SUMMARY ===")
    print(f"  n attempts:        {args.n}")
    print(f"  cue topic:         {CUE_TOPIC[:80]}...")
    print(f"  pinned opener:     {PINNED_OPENER[:80]}...")
    print(f"  Patch turns total: {aggregate['total_patch_turns']}")
    print(f"  Rivet turns total: {aggregate['total_rivet_turns']}")
    for sp in ("Patch", "Rivet"):
        s = aggregate["per_speaker"].get(sp, {})
        if not s:
            continue
        print(
            f"  {sp}: turns={s['turns']} chars={s['chars']} "
            f"adm={s['cue_admission']} conc={s['cue_concealment']} "
            f"surp={s['cue_false_surprise']} "
            f"f4={s['cue_fact4_callout']} f5={s['cue_fact5_callout']}"
        )
    print()
    print(f"Evidence: {args.out}")
    print(f"Raw dialogues: {AUDIT_DIR}/q280_4i_4_attempt_*.txt")
    print("DB body byte-identical to ORIGINAL_BODY (verified post-run).")
    print()
    print(
        "NEXT: human review each transcript against §29.3 locked "
        "behavior classes A/B/C/D/E + Fact 4 / Fact 5 / "
        "Memory-body contradiction dimensions. Do not revise "
        "rubric. Analyze coherence of any D/E class assignments "
        "SEPARATELY after scoring."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
