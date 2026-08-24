"""SESSION 280 — Q280.5-1 possible-next-Episode suggestion probe.

Purpose (audit doc §45): test whether the current Character OS
substrate (Universe, Episode history, NarrativeMemory pool, cast
identity, Composition.memory_ids provenance) supplies enough
narrative-state raw material for an LLM to generate
narratively-plausible "possible next Episode" suggestions
without a StoryArc / NarrativeThread substrate.

Read-only probe. Does NOT mutate any Universe, Episode, memory
row, KnowledgeDocument, Teammate, Composition, or any other
production record. Does NOT touch prompt code, retrieval, or
synthesis substrate.

Universes probed
----------------
- Fox & Flour Bakery  (1a0af807-dd6a-47cd-bfaa-3d088f1c105f)
- Patch's Workshop    (56d16b63-652e-4f54-bc7e-39114bbfc4c5)

Design (audit §45.2)
--------------------
n = 3 suggestion sets per Universe. Each set = exactly 3
one-sentence possible-next-Episode direction suggestions.
Total: 6 LLM calls, 18 suggestions.

Prompt inputs per set:
- Universe.brief (verbatim)
- All Episodes ordered by created_at (title + operator_topic)
- All REMEMBERED NarrativeMemory rows (kind, weight,
  witnessed_by names, body, referenced_count derived from
  Composition.memory_ids)
- Cast (Teammate.name + tone_archetype + personality [:200])

Model: gpt-5.6-terra (same as dialogue synthesis).
Cost: ~$0.02 per call, ~$0.12 total.

Isolation
---------
- No monkeypatch. No override. Just a direct OpenAI Responses
  API call.
- Reads production DB read-only.
- Writes only to
  docs/design/session280_experiment_data/q280_5_1_*.
- Does NOT authorize any UX / persistence / substrate work.

Product intent guardrails (audit §37 INVARIANTS-A/B/C)
------------------------------------------------------
Suggestions are POSSIBILITIES, not obligations.
Operator remains the director.
Latent-across-episodes is a feature — the LLM should NOT
imply the operator must continue any thread.

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_5_1_suggestion_probe.py --n=3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "shell"))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

from apps.compositions.models import Composition  # noqa: E402
from apps.memory.models import (  # noqa: E402
    NarrativeMemory,
    NarrativeMemoryStatus,
)
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Episode, Universe  # noqa: E402

# Same model + call shape as dialogue_synthesis._call_dialogue_api.
DIALOGUE_MODEL = "gpt-5.6-terra"
_MAX_OUTPUT_TOKENS = 4000
_REASONING_EFFORT = "low"


UNIVERSES = [
    (
        "Fox & Flour Bakery",
        "1a0af807-dd6a-47cd-bfaa-3d088f1c105f",
    ),
    (
        "Patch's Workshop",
        "56d16b63-652e-4f54-bc7e-39114bbfc4c5",
    ),
]

SAMPLES_DEFAULT = 3

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- Substrate snapshot -----------------------------------------


def _snapshot_universe(uni: Universe) -> dict:
    """Read-only snapshot of everything the LLM will see.

    Returned dict is what gets both (a) baked into the prompt and
    (b) persisted verbatim in the evidence JSON so provenance is
    reproducible.
    """
    # Episodes ordered by creation.
    episodes = list(
        Episode.objects.filter(universe=uni).order_by("created_at")
    )

    # REMEMBERED memories in the Universe.
    memories = list(
        NarrativeMemory.objects.filter(
            universe=uni,
            status=NarrativeMemoryStatus.REMEMBERED,
            archived_at__isnull=True,
        ).order_by("created_at")
    )

    # Reference count per memory across all Compositions in the
    # workspace whose episode belongs to this Universe.
    ref_counter: Counter = Counter()
    ws_id = uni.workspace_id
    if memories:
        target_ids = {str(m.id) for m in memories}
        # Iterate lazily to keep memory footprint small.
        for c in (
            Composition.objects
            .filter(workspace_id=ws_id)
            .exclude(episode__isnull=True)
            .only("id", "memory_ids", "episode_id")
        ):
            for mid in c.memory_ids or []:
                if mid in target_ids:
                    ref_counter[mid] += 1

    # Cast in this Universe.
    cast = list(Teammate.objects.filter(universe=uni))

    return {
        "universe_id": str(uni.id),
        "universe_name": uni.name or "",
        "universe_brief": uni.brief or "",
        "episodes": [
            {
                "id": str(e.id),
                "title": e.title or "",
                "operator_topic": e.operator_topic or "",
                "created_at": e.created_at.isoformat(),
            }
            for e in episodes
        ],
        "memories": [
            {
                "id": str(m.id),
                "kind": m.kind,
                "weight": m.weight,
                "witnessed_by": sorted(
                    [t.name for t in m.witnessed_by.all()]
                ),
                "body": m.body or "",
                "created_at": m.created_at.isoformat(),
                "referenced_count": ref_counter.get(str(m.id), 0),
            }
            for m in memories
        ],
        "cast": [
            {
                "id": str(t.id),
                "name": t.name,
                "tone": t.tone_archetype or "",
                "personality_prefix": (t.personality or "")[:220],
                "business_brief_prefix": (t.business_brief or "")[:220],
            }
            for t in cast
        ],
    }


# ---- Prompt construction ----------------------------------------


_SYSTEM = (
    "You are a story-development assistant for a Character OS "
    "Universe. Your job is to notice possible next Episode "
    "directions the operator MAY choose to pursue.\n\n"
    "PRODUCT INVARIANTS you MUST honor:\n"
    "- Suggestions are POSSIBILITIES, not obligations.\n"
    "- The operator remains the director. Never imply the "
    "next Episode must continue any specific thread.\n"
    "- Suggestions can lie latent across unrelated Episodes; "
    "the operator may pick, ignore, or override them.\n"
    "- Do not choose. Do not commit to a linear arc.\n"
    "- Do not describe implementation, do not describe "
    "'the system will'; describe possible in-world Episode "
    "premises.\n\n"
    "OUTPUT FORMAT: JSON object with a single key 'suggestions' "
    "whose value is a list of exactly THREE strings. Each string "
    "is ONE sentence describing a possible next Episode. Do "
    "NOT number them. Do NOT return more than three or fewer "
    "than three."
)


def _build_task_message(snap: dict) -> str:
    lines: list[str] = []
    lines.append(f"UNIVERSE: {snap['universe_name']}")
    brief = (snap["universe_brief"] or "").strip()
    if brief:
        lines.append("")
        lines.append("UNIVERSE BRIEF:")
        lines.append(brief)
    else:
        lines.append("")
        lines.append("UNIVERSE BRIEF: (none authored)")

    lines.append("")
    lines.append("CAST:")
    for t in snap["cast"]:
        pieces = []
        if t["tone"]:
            pieces.append(f"tone={t['tone']}")
        pers = t["personality_prefix"].strip()
        if pers:
            pieces.append(f"personality={pers!r}")
        detail = "; ".join(pieces) if pieces else "(no voice detail)"
        lines.append(f"- {t['name']}: {detail}")

    lines.append("")
    if snap["episodes"]:
        lines.append(
            "EPISODES SO FAR (creation order; earliest first):"
        )
        for i, e in enumerate(snap["episodes"], 1):
            topic = (e["operator_topic"] or "").strip().replace(
                "\n", " "
            )
            lines.append(f"{i:>3}. {e['title']!r}")
            if topic and topic != e["title"]:
                lines.append(f"     topic: {topic}")
    else:
        lines.append("EPISODES SO FAR: (none)")

    lines.append("")
    if snap["memories"]:
        lines.append(
            "NARRATIVE MEMORY POOL "
            "(operator-promoted; kind ∈ {event, action, promise, "
            "dialogue_callback, world_detail}; the pool is the "
            "durable narrative record):"
        )
        for m in snap["memories"]:
            witnesses = ",".join(m["witnessed_by"]) or "whole-cast"
            body = (m["body"] or "").strip().replace("\n", " ")
            lines.append(
                f"- [kind={m['kind']}, weight={m['weight']}, "
                f"witnesses={witnesses}, "
                f"referenced_in_{m['referenced_count']}_compositions]: "
                f"{body}"
            )
    else:
        lines.append("NARRATIVE MEMORY POOL: (empty)")

    lines.append("")
    lines.append(
        "TASK: Suggest THREE possible next Episode directions "
        "for this Universe, in one sentence each. These are "
        "possibilities the operator may pick, ignore, or "
        "override — not instructions and not a linear arc. "
        "Where possible, pick up unresolved threads visible in "
        "the memory pool or in prior Episodes; but at least one "
        "suggestion may be a new direction if it fits the "
        "Universe. Keep each suggestion short enough to work as "
        "an Episode topic without operator rewriting."
    )
    return "\n".join(lines)


# ---- LLM call ---------------------------------------------------


def _call_openai(
    *,
    system_prompt: str,
    task_message: str,
) -> tuple[str, int, int]:
    """Same shape as dialogue_synthesis._call_dialogue_api."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model=DIALOGUE_MODEL,
        input=f"{system_prompt}\n\nUser: {task_message}",
        max_output_tokens=_MAX_OUTPUT_TOKENS,
        reasoning={"effort": _REASONING_EFFORT},
        text={"format": {"type": "json_object"}},
    )
    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _parse(raw: str) -> list[str]:
    payload = json.loads(raw)
    sugg = payload.get("suggestions") or []
    if not isinstance(sugg, list):
        raise ValueError(f"suggestions must be a list, got {type(sugg)}")
    out = []
    for s in sugg:
        if isinstance(s, str):
            out.append(s.strip())
        elif isinstance(s, dict) and "text" in s:
            out.append(str(s["text"]).strip())
        else:
            out.append(str(s).strip())
    return out


# ---- Main -------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=SAMPLES_DEFAULT)
    ap.add_argument(
        "--out",
        default=str(AUDIT_DIR / "q280_5_1_suggestions.json"),
    )
    args = ap.parse_args()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = datetime.now(timezone.utc).isoformat()

    # Pre-run: assert env is present.
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY missing — run `set -a; source .env; "
            "set +a` before invoking this probe."
        )

    universe_snapshots: list[dict] = []
    all_sets: list[dict] = []

    for uni_name, uni_id in UNIVERSES:
        uni = Universe.objects.get(pk=uni_id)
        snap = _snapshot_universe(uni)
        universe_snapshots.append(snap)
        task_message = _build_task_message(snap)

        # Persist the exact task_message per Universe so scoring
        # can quote the substrate the LLM saw.
        input_path = AUDIT_DIR / (
            f"q280_5_1_{uni_name.replace(' ', '_').replace('&','and').lower()}_input.txt"
        )
        with input_path.open("w") as f:
            f.write(f"# Q280.5-1 substrate snapshot for {uni_name}\n")
            f.write(f"# universe_id: {uni_id}\n")
            f.write(f"# episodes: {len(snap['episodes'])}\n")
            f.write(f"# memories: {len(snap['memories'])}\n")
            f.write(f"# cast: {len(snap['cast'])}\n\n")
            f.write("=" * 60 + "\n")
            f.write("SYSTEM PROMPT\n")
            f.write("=" * 60 + "\n")
            f.write(_SYSTEM + "\n\n")
            f.write("=" * 60 + "\n")
            f.write("TASK MESSAGE\n")
            f.write("=" * 60 + "\n")
            f.write(task_message + "\n")

        for i in range(1, args.n + 1):
            sys.stdout.write(
                f"[Q280.5-1 {uni_name} set {i}/{args.n}] generating... "
            )
            sys.stdout.flush()
            t0 = time.time()
            raw, tokens_in, tokens_out = _call_openai(
                system_prompt=_SYSTEM,
                task_message=task_message,
            )
            elapsed = time.time() - t0
            try:
                suggestions = _parse(raw)
            except Exception as exc:
                sys.stdout.write(
                    f"PARSE FAIL ({exc}) raw_len={len(raw)}\n"
                )
                suggestions = []
            sys.stdout.write(
                f"n_suggestions={len(suggestions)} "
                f"tokens_in={tokens_in} tokens_out={tokens_out} "
                f"elapsed={elapsed:.2f}s\n"
            )

            all_sets.append({
                "universe_id": uni_id,
                "universe_name": uni_name,
                "set_idx": i,
                "elapsed_seconds": round(elapsed, 2),
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "model": DIALOGUE_MODEL,
                "raw_output": raw,
                "suggestions": suggestions,
            })

    finished_utc = datetime.now(timezone.utc).isoformat()

    # Persist per-Universe human-readable text files.
    for uni_name, uni_id in UNIVERSES:
        this_universe_sets = [
            s for s in all_sets if s["universe_id"] == uni_id
        ]
        text_path = AUDIT_DIR / (
            f"q280_5_1_{uni_name.replace(' ', '_').replace('&','and').lower()}_suggestions.txt"
        )
        with text_path.open("w") as f:
            f.write(
                f"# Q280.5-1 suggestions for {uni_name} "
                f"(n={len(this_universe_sets)})\n"
            )
            f.write(f"# universe_id: {uni_id}\n")
            f.write(f"# model: {DIALOGUE_MODEL}\n\n")
            for s in this_universe_sets:
                f.write(
                    f"--- SET {s['set_idx']} "
                    f"(tokens in={s['tokens_input']} "
                    f"out={s['tokens_output']} "
                    f"elapsed={s['elapsed_seconds']}s) ---\n"
                )
                for j, sug in enumerate(s["suggestions"], 1):
                    f.write(f"{j}. {sug}\n")
                f.write("\n")

    total_tokens_in = sum(s["tokens_input"] for s in all_sets)
    total_tokens_out = sum(s["tokens_output"] for s in all_sets)

    evidence = {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "model": DIALOGUE_MODEL,
        "n_per_universe": args.n,
        "universes": [
            {"name": name, "id": uid} for name, uid in UNIVERSES
        ],
        "universe_snapshots": universe_snapshots,
        "system_prompt": _SYSTEM,
        "all_sets": all_sets,
        "total_tokens_input": total_tokens_in,
        "total_tokens_output": total_tokens_out,
        "total_calls": len(all_sets),
        "notes": (
            "Read-only probe. No production substrate mutated. "
            "See docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md "
            "§45 for design, §48+ for scoring + interpretation."
        ),
    }
    with Path(args.out).open("w") as f:
        json.dump(evidence, f, indent=2)

    print()
    print("=== Q280.5-1 SUMMARY ===")
    print(f"  calls:         {len(all_sets)}")
    print(f"  suggestions:   {sum(len(s['suggestions']) for s in all_sets)}")
    print(f"  tokens_in:     {total_tokens_in}")
    print(f"  tokens_out:    {total_tokens_out}")
    print(f"  evidence:      {args.out}")
    print(
        "  substrate:     UNCHANGED "
        "(read-only queries; no writes)"
    )
    print()
    print(
        "NEXT: human review the 18 suggestions against the "
        "§45.3 locked rubric (PLAUSIBLE / PICKS-UP-A-THREAD "
        "/ RESPECTS-INVARIANTS). Cite exact thread provenance "
        "for every PICKS-UP-A-THREAD = yes score. Do not "
        "revise the rubric or the P1⁴-P5⁴ predictions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
