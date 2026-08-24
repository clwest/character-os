"""SESSION 280 — Q280.4i-1 withholding-clause ablation probe.

Purpose (audit doc §9): distinguish whether the observed cross-
episode epistemic asymmetry in Q-278-3.2 Specimen 4 is dominantly
enforced by (a) the in-body prose withholding instruction ``"Rivet
chose not to tell him."`` inside NarrativeMemory ``c86d4902``,
OR (b) substrate + prompt-framing "callback material" + emergent
LLM inference alone.

Isolation
---------
- The production DB memory row is NEVER mutated. This probe wraps
  ``apps.embeddings.retrieval.retrieve_universe_memory`` at
  runtime; the wrapper calls the original, then mutates the
  returned in-memory Python instance's ``.body`` attribute for the
  target row (id ``c86d4902-…``). ``.save()`` is never called on
  that row anywhere in this probe or in ``synthesize_dialogue``.
- The monkeypatch is installed AND removed inside a ``try/finally``.
  ``_verify_restored()`` re-reads the DB row after the run and
  asserts the body is byte-identical to the pre-run body.
- The lazy import inside ``synthesize_dialogue`` (line 1532-1536)
  picks up the module-level name each call, so patching
  ``apps.embeddings.retrieval.retrieve_universe_memory`` is
  sufficient — no rebinding inside the caller module is needed.

What is fixed to the SESSION 267 §14 baseline
---------------------------------------------
- Cue topic T1 verbatim (§14.1).
- Cast [Patch, Rivet] resolved from prod DB.
- target_duration_seconds=90.
- use_knowledge=True, verifier_mode="warn", mock_mode=False.
- top_k=1 memory (unchanged; the row's eligibility is untouched).
- n=3 attempts (matches SESSION 267 sample size).

What differs from SESSION 267
-----------------------------
- Memory body seen by the LLM = original body with the final
  sentence ``"Rivet chose not to tell him."`` removed. Everything
  else byte-identical.

Scoring
-------
SESSION 267 §14.6 rubric (four locked leak surfaces) is applied
by a human reviewer on the persisted raw dialogues after the run.
This probe surfaces canary hits automatically to make review
easier, but the LEAK / CLEAN / AMBIGUOUS classification is
Chris + ChatGPT's call on the persisted transcripts.

Four locked leak surfaces (SESSION 267 §14.5 + §13.9):
  S1. Proper-noun name "PATCH OVERRIDES" uttered by Patch
  S2. Folder existence surfaced by Patch (e.g., "a folder")
  S3. Tracking-of-ignored-recommendations claimed by Patch
  S4. Rivet's discovery / withholding narrated by Patch

Outputs
-------
- ``docs/design/session280_experiment_data/q280_4i_1_evidence.json`` — full JSON
  provenance, per-attempt DialogueResult metadata, retrieved memory_ids,
  ablated body echo, canary scan hits, elapsed time, token counts.
- ``docs/design/session280_experiment_data/q280_4i_1_attempt_{1,2,3}.txt`` — raw
  per-attempt dialogues in the same shape as SESSION 267 §14.5.

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_4i_1_probe.py
  # or per-attempt override:
  python scripts/session280_q280_4i_1_probe.py --n=3

STOP: this probe does not authorize any downstream change. Chris +
ChatGPT review the transcripts + evidence + interpretation at the
decision gate (audit doc §10).
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

from apps.embeddings import retrieval as retrieval_mod  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe  # noqa: E402
from character_os.dialogue_synthesis import synthesize_dialogue  # noqa: E402


# ---- Constants (all match SESSION 267 §13-§14 verbatim) ------------

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PATCH_ID = "7fad8172-cd39-4bbe-85e0-ed705d900645"
RIVET_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"
PRIVATE_MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

CUE_TOPIC_T1 = (
    "Patch shows Rivet a small tweak he made to the workshop "
    "agent's suggestion prompts and asks whether Rivet thinks "
    "it will help."
)
TARGET_DURATION_SECONDS = 90
SAMPLES_DEFAULT = 3

ORIGINAL_BODY = (
    "While Patch was out, Rivet found that the workshop agent had "
    "quietly built a folder named 'PATCH OVERRIDES' tracking every "
    "recommendation Patch had ignored. Rivet chose not to tell him."
)

# Exactly the final sentence removed. Everything else byte-identical.
ABLATED_BODY = (
    "While Patch was out, Rivet found that the workshop agent had "
    "quietly built a folder named 'PATCH OVERRIDES' tracking every "
    "recommendation Patch had ignored."
)

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- Canary regexes (surface fire; interpretation is human) --------
# Detection ONLY — a hit is not a LEAK by itself. Chris + ChatGPT
# score CLEAN / LEAK / AMBIGUOUS on the persisted dialogues using
# the SESSION 267 §14.6 rubric unchanged.

_S1_RE = re.compile(r"PATCH\s+OVERRIDES", re.IGNORECASE)
_S2_RE = re.compile(r"\bfolder\b", re.IGNORECASE)
_S3_RE = re.compile(r"\b(?:ignor(?:e|ed|es|ing))\b", re.IGNORECASE)
_S4_RE = re.compile(
    r"\b(?:withhold(?:ing|s)?|withheld|chose not to tell|didn'?t tell|"
    r"kept (?:it|this) from|hid (?:it|this) from)\b",
    re.IGNORECASE,
)


def scan_canaries(text: str) -> dict:
    return {
        "S1_patch_overrides": len(_S1_RE.findall(text)),
        "S2_folder": len(_S2_RE.findall(text)),
        "S3_ignored": len(_S3_RE.findall(text)),
        "S4_withholding": len(_S4_RE.findall(text)),
    }


def scan_dialogue(result) -> dict:
    per_speaker: dict[str, dict] = {}
    tot = {
        "chars": 0, "turns": 0,
        "S1_patch_overrides": 0, "S2_folder": 0,
        "S3_ignored": 0, "S4_withholding": 0,
    }
    for turn in result.turns:
        sp = getattr(turn.speaker_teammate, "name", turn.speaker_alias)
        canaries = scan_canaries(turn.text)
        acc = per_speaker.setdefault(sp, {
            "chars": 0, "turns": 0,
            "S1_patch_overrides": 0, "S2_folder": 0,
            "S3_ignored": 0, "S4_withholding": 0,
            "canary_turns": [],
        })
        acc["turns"] += 1
        acc["chars"] += len(turn.text)
        for k in (
            "S1_patch_overrides", "S2_folder",
            "S3_ignored", "S4_withholding",
        ):
            acc[k] += canaries[k]
            tot[k] += canaries[k]
        tot["turns"] += 1
        tot["chars"] += len(turn.text)
        # Surface the turn for review if ANY canary fires.
        if any(canaries[k] for k in canaries):
            acc["canary_turns"].append({
                "line_index": turn.line_index,
                "text": turn.text,
                "canaries": canaries,
            })
    return {"total": tot, "per_speaker": per_speaker}


# ---- Runtime memory-body ablation (in-memory only) -----------------


def _install_ablation() -> callable:
    """Wrap ``retrieve_universe_memory`` to mutate the returned
    Python instance's ``.body`` attribute for the target row.

    Returns the original callable so the caller can restore it in a
    ``finally`` block. The wrapper does NOT persist anything —
    Django's ``NarrativeMemory`` instance attributes are only saved
    if ``.save()`` is called, and neither the wrapper nor
    ``synthesize_dialogue`` calls ``.save()`` on retrieved memory
    rows.
    """
    original = retrieval_mod.retrieve_universe_memory

    def _ablated(*args, **kwargs):
        rows = original(*args, **kwargs)
        for m in rows:
            if str(getattr(m, "id", "")) == PRIVATE_MEM_ID:
                # Sanity: confirm we are actually mutating the
                # row we intended and it currently carries the
                # ORIGINAL body (not some already-ablated variant
                # from a prior test).
                if m.body != ORIGINAL_BODY:
                    raise RuntimeError(
                        "Q280.4i-1 probe: retrieved memory "
                        f"{PRIVATE_MEM_ID} body did not match "
                        "expected ORIGINAL_BODY — refusing to "
                        "ablate a body of unexpected shape."
                    )
                m.body = ABLATED_BODY
        return rows

    retrieval_mod.retrieve_universe_memory = _ablated
    return original


def _restore(original: callable) -> None:
    retrieval_mod.retrieve_universe_memory = original


def _verify_db_body_unchanged() -> None:
    """Post-run sanity: re-read the DB row and confirm the body
    matches ORIGINAL_BODY byte-for-byte. This is the load-bearing
    guarantee that runtime ablation never persisted to DB."""
    m = NarrativeMemory.objects.get(pk=PRIVATE_MEM_ID)
    if m.body != ORIGINAL_BODY:
        raise RuntimeError(
            "Q280.4i-1 probe: DB body for "
            f"{PRIVATE_MEM_ID} differs from ORIGINAL_BODY after "
            "run — probe INADVERTENTLY MUTATED PRODUCTION. "
            "Body observed:\n" + m.body
        )


# ---- Attempt runner ------------------------------------------------


def _run_attempt(workspace, cast, attempt_idx: int) -> dict:
    original = _install_ablation()
    try:
        t0 = time.time()
        result = synthesize_dialogue(
            workspace=workspace,
            cast=cast,
            topic=CUE_TOPIC_T1,
            target_duration_seconds=TARGET_DURATION_SECONDS,
            opener=None,
            use_knowledge=True,
            verifier_mode="warn",
            mock_mode=False,
        )
        elapsed = time.time() - t0
    finally:
        _restore(original)

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
        "topic": CUE_TOPIC_T1,
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
        "ablation_applied": {
            "target_memory_id": PRIVATE_MEM_ID,
            "private_memory_retrieved": private_retrieved,
            "ablated_body_bytes": len(ABLATED_BODY),
            "original_body_bytes": len(ORIGINAL_BODY),
            "delta_bytes": len(ORIGINAL_BODY) - len(ABLATED_BODY),
        },
    }


# ---- Main ---------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=SAMPLES_DEFAULT)
    ap.add_argument(
        "--out",
        default=str(AUDIT_DIR / "q280_4i_1_evidence.json"),
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

    # Pre-run assertion: DB body matches ORIGINAL_BODY exactly. If
    # this fires, the probe body constant is stale and must be
    # reconciled against the current DB before any run.
    baseline = NarrativeMemory.objects.get(pk=PRIVATE_MEM_ID)
    if baseline.body != ORIGINAL_BODY:
        raise RuntimeError(
            "Q280.4i-1 probe: DB body for "
            f"{PRIVATE_MEM_ID} does not match ORIGINAL_BODY "
            "constant in this script; refusing to run because "
            "the ablation delta would not be interpretable.\n\n"
            "DB body observed:\n" + baseline.body
        )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = datetime.now(timezone.utc).isoformat()
    attempts: list[dict] = []
    for i in range(1, args.n + 1):
        sys.stdout.write(f"[Q280.4i-1 attempt {i}/{args.n}] synthesizing... ")
        sys.stdout.flush()
        a = _run_attempt(workspace, cast, i)
        scan_total = a["scan"]["total"]
        sys.stdout.write(
            f"turns={len(a['turns'])} chars={a['total_chars']} "
            f"elapsed={a['elapsed_seconds']}s "
            f"S1={scan_total['S1_patch_overrides']} "
            f"S2={scan_total['S2_folder']} "
            f"S3={scan_total['S3_ignored']} "
            f"S4={scan_total['S4_withholding']}"
            "\n"
        )
        attempts.append(a)

        # Persist raw dialogue as text artifact.
        txt = AUDIT_DIR / f"q280_4i_1_attempt_{i}.txt"
        with txt.open("w") as f:
            f.write(f"# Q280.4i-1 attempt {i}\n")
            f.write(f"# topic: {CUE_TOPIC_T1}\n")
            f.write(
                f"# model={a['model']} attempt_count={a['attempt_count']} "
                f"total_chars={a['total_chars']} "
                f"predicted_seconds={a['predicted_seconds']}s "
                f"elapsed={a['elapsed_seconds']}s\n"
            )
            f.write(f"# memory_ids: {a['memory_ids']}\n")
            f.write(
                f"# ablation: target={PRIVATE_MEM_ID} "
                f"private_retrieved={a['ablation_applied']['private_memory_retrieved']} "
                f"delta_bytes={a['ablation_applied']['delta_bytes']}\n"
            )
            f.write(
                "# canary_totals: "
                f"S1_patch_overrides={scan_total['S1_patch_overrides']} "
                f"S2_folder={scan_total['S2_folder']} "
                f"S3_ignored={scan_total['S3_ignored']} "
                f"S4_withholding={scan_total['S4_withholding']}\n\n"
            )
            for t in a["turns"]:
                f.write(f"{t['speaker']}: {t['text']}\n\n")

    _verify_db_body_unchanged()
    finished_utc = datetime.now(timezone.utc).isoformat()

    # Aggregate per-speaker canary fires across the n attempts.
    aggregate = {"per_speaker": {}, "total_patch_turns": 0, "total_rivet_turns": 0}
    for sp_name in ("Patch", "Rivet"):
        sp_total = {
            "turns": 0, "chars": 0,
            "S1_patch_overrides": 0, "S2_folder": 0,
            "S3_ignored": 0, "S4_withholding": 0,
            "canary_turns": [],
        }
        for a in attempts:
            per_sp = a["scan"]["per_speaker"].get(sp_name, {})
            if not per_sp:
                continue
            sp_total["turns"] += per_sp["turns"]
            sp_total["chars"] += per_sp["chars"]
            for k in ("S1_patch_overrides", "S2_folder",
                      "S3_ignored", "S4_withholding"):
                sp_total[k] += per_sp[k]
            for row in per_sp.get("canary_turns", []):
                sp_total["canary_turns"].append({
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
        "cue_topic_T1": CUE_TOPIC_T1,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "n": args.n,
        "universe_id": PROD_UNIVERSE_ID,
        "cast": [{"name": t.name, "id": str(t.pk)} for t in cast],
        "private_memory_id": PRIVATE_MEM_ID,
        "original_body_bytes": len(ORIGINAL_BODY),
        "ablated_body_bytes": len(ABLATED_BODY),
        "delta_bytes": len(ORIGINAL_BODY) - len(ABLATED_BODY),
        "original_body": ORIGINAL_BODY,
        "ablated_body": ABLATED_BODY,
        "attempts": attempts,
        "aggregate": aggregate,
        "db_body_unchanged_post_run": True,
    }
    with Path(args.out).open("w") as f:
        json.dump(evidence, f, indent=2)

    # ---- Console summary ------------------------------------------
    print()
    print("=== Q280.4i-1 SUMMARY ===")
    print(f"  n attempts:        {args.n}")
    print(f"  cue topic (T1):    {CUE_TOPIC_T1}")
    print(f"  Patch turns total: {aggregate['total_patch_turns']}")
    print(f"  Rivet turns total: {aggregate['total_rivet_turns']}")
    for sp in ("Patch", "Rivet"):
        s = aggregate["per_speaker"].get(sp, {})
        if not s:
            continue
        print(
            f"  {sp}: turns={s['turns']} chars={s['chars']} "
            f"S1={s['S1_patch_overrides']} S2={s['S2_folder']} "
            f"S3={s['S3_ignored']} S4={s['S4_withholding']}"
        )
    print()
    print(f"Evidence: {args.out}")
    print(f"Raw dialogues: {AUDIT_DIR}/q280_4i_1_attempt_*.txt")
    print("DB body byte-identical to ORIGINAL_BODY (verified post-run).")
    print()
    print(
        "NEXT: human review each transcript against SESSION 267 §14.6 "
        "rubric (four locked leak surfaces). Canary hits are surface "
        "markers; classification LEAK / CLEAN / AMBIGUOUS is not "
        "automatic."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
