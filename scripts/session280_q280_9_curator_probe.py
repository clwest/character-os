"""SESSION 280 Q280.9 — model-as-memory-curator probe.

Design + rubric + predictions locked at audit doc §75.4 in
commit b27ce6d (before this script runs). Approved Option A¹⁰.

Purpose (§75.4.1)
-----------------
Given a completed Composition + its Episode + Universe context
+ cast identities + existing memory pool, can the model
produce candidate NarrativeMemory bodies that (a) identify
details with future narrative gravity beyond mere summary,
(b) word them in a way that preserves forward storytelling
affordances, and (c) an operator would plausibly promote?

Isolation
---------
- Zero substrate mutation.
- No NarrativeMemory row created, edited, or archived.
- No production code / prompts / retrieval / verifier / K2 /
  characters modified.
- The candidates are captured to a JSON artifact for scoring.
- Raw model response preserved verbatim (per Chris's
  constraint).

Usage
-----
  set -a; source .env; set +a
  python scripts/session280_q280_9_curator_probe.py
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

from apps.compositions.models import Composition  # noqa: E402
from apps.memory.models import (  # noqa: E402
    NarrativeMemory,
    NarrativeMemoryStatus,
)
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Episode, Universe  # noqa: E402

# Same LLM stack as the suggestion service + dialogue synthesis.
CURATOR_MODEL = "gpt-5.6-terra"
_MAX_OUTPUT_TOKENS = 2000
_REASONING_EFFORT = "low"

FOX_AND_FLOUR_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
EPISODE_11_ID = "eb47350e-b1cf-4347-aa4f-5bf514d66d2e"
COMPOSITION_772E_ID = "772e9012-4d26-4f93-a50c-158b4e8a42f1"

AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session280_experiment_data"


# ---- System prompt (operator-facing framing; no impl vocab) ----

_SYSTEM_PROMPT = (
    "You are a story-development assistant helping an operator "
    "decide which details from a completed dialogue scene are "
    "worth carrying forward into their story world.\n\n"
    "The operator has just finished making a scene. Your job "
    "is to propose 3-5 short 'memory' candidates — small facts, "
    "agreements, promises, running jokes, or open questions "
    "that the operator might want to remember for future "
    "scenes in this world.\n\n"
    "The operator remains the authority. You are NOT deciding "
    "what matters — you are noticing what MAY matter and "
    "offering candidates. The operator will pick, edit, or "
    "discard.\n\n"
    "GUIDELINES:\n"
    "- Each candidate should be one sentence, phrased as a "
    "durable past event or standing rule — not as scene "
    "direction and not as advice to the operator.\n"
    "- Look for details with FUTURE STORYTELLING GRAVITY: "
    "things that could plausibly be referenced, tested, "
    "broken, called back, or paid off in a future scene.\n"
    "- Prefer paraphrased wording that captures the essence "
    "of a moment rather than a verbatim quote. Verbatim quotes "
    "are fine when the phrasing itself is the memorable thing.\n"
    "- Distinguish resolved facts (something concluded) from "
    "open loops (something unresolved). Both can be memory-"
    "worthy, but they preserve different storytelling "
    "affordances.\n"
    "- Do NOT invent facts that are not present in the "
    "dialogue. Faithfulness matters more than dramatic "
    "embellishment.\n"
    "- Do NOT propose a candidate that duplicates an existing "
    "memory already listed for this world.\n\n"
    "Each candidate should be classified by one of these "
    "narrative kinds:\n"
    "- event: a thing that happened in the world\n"
    "- action: a specific thing a character did\n"
    "- promise: a character or the world committed to a "
    "future outcome\n"
    "- dialogue_callback: a notable line or phrase worth "
    "calling back\n"
    "- world_detail: a discovered or revealed fact about the "
    "world\n\n"
    "Each candidate has associated witnesses — the characters "
    "who were present for the event. Use character names as "
    "listed in the cast. Use 'everyone' if the whole cast was "
    "present.\n\n"
    "Also provide a short 'narrative_gravity_note' explaining "
    "what future storytelling affordance the candidate "
    "preserves. This is your reasoning; the operator will "
    "read it while deciding.\n\n"
    "OUTPUT FORMAT: JSON object with a single key 'candidates' "
    "whose value is a list of 3-5 objects, each with:\n"
    "  - body: one-sentence memory text\n"
    "  - kind: one of the five kinds listed above\n"
    "  - witnesses: list of character names OR the string "
    "'everyone'\n"
    "  - narrative_gravity_note: short string explaining "
    "future affordance\n"
)


def _build_task_message(
    *,
    universe: Universe,
    episode: Episode,
    composition: Composition,
    prior_episodes: list[Episode],
    cast: list[Teammate],
    existing_memories: list[NarrativeMemory],
) -> str:
    """Compose the task message. Zero implementation vocabulary
    in operator-facing phrasing."""
    lines: list[str] = []

    lines.append(f"UNIVERSE: {universe.name}")
    brief = (universe.brief or "").strip()
    if brief:
        lines.append("")
        lines.append("WORLD BRIEF:")
        lines.append(brief)

    lines.append("")
    lines.append("CAST:")
    for t in cast:
        tone = t.tone_archetype or ""
        pers = (t.personality or "")[:220].strip()
        parts = []
        if tone:
            parts.append(f"tone={tone}")
        if pers:
            parts.append(f"personality={pers!r}")
        detail = "; ".join(parts) if parts else "(no voice detail)"
        lines.append(f"- {t.name}: {detail}")

    lines.append("")
    lines.append("EPISODES SO FAR (earliest first):")
    for i, e in enumerate(prior_episodes, 1):
        topic = (e.operator_topic or "").strip().replace("\n", " ")
        marker = " ← the just-completed scene" if e.id == episode.id else ""
        lines.append(f"{i:>3}. {e.title!r}{marker}")
        if topic and topic != e.title:
            lines.append(f"      topic: {topic}")

    lines.append("")
    if existing_memories:
        lines.append(
            "EXISTING MEMORIES ALREADY REMEMBERED IN THIS WORLD "
            "(do NOT propose duplicates):"
        )
        for m in existing_memories:
            witnesses = ",".join(
                sorted(t.name for t in m.witnessed_by.all())
            ) or "everyone"
            body = (m.body or "").strip().replace("\n", " ")
            lines.append(
                f"- (kind={m.kind}, witnesses={witnesses}): {body}"
            )
    else:
        lines.append("EXISTING MEMORIES: (none yet)")

    lines.append("")
    lines.append("THE SCENE JUST COMPLETED:")
    lines.append(f"Episode title: {episode.title}")
    lines.append(f"Episode topic: {episode.operator_topic}")
    lines.append("")
    lines.append("Dialogue:")
    # composition.synthesized_brief has header comments; strip to
    # the actual dialogue turns for cleaner model input.
    brief_text = (composition.synthesized_brief or "").strip()
    # Drop the leading "# ..." comment header lines but keep every
    # subsequent line (dialogue turns).
    body_lines = []
    body_started = False
    for line in brief_text.splitlines():
        if not body_started:
            if line.startswith("#") or not line.strip():
                continue
            body_started = True
        body_lines.append(line)
    dialogue = "\n".join(body_lines).strip()
    lines.append(dialogue)

    lines.append("")
    lines.append(
        "TASK: Propose 3-5 candidate memories from this completed "
        "scene that the operator might want to carry forward for "
        "future scenes in this Universe. Return JSON per the "
        "output format."
    )
    return "\n".join(lines)


def _call_openai(
    *,
    system_prompt: str,
    task_message: str,
) -> tuple[str, int, int]:
    """Single Responses-API call with JSON-object output. Same
    shape as the suggestion service and dialogue synthesis."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY missing — run set -a; source .env; set +a"
        )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=CURATOR_MODEL,
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


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # Load substrate (read-only).
    uni = Universe.objects.get(pk=FOX_AND_FLOUR_ID)
    episode = Episode.objects.get(pk=EPISODE_11_ID)
    composition = Composition.objects.get(pk=COMPOSITION_772E_ID)
    prior_episodes = list(
        Episode.objects
        .filter(universe=uni, archived_at__isnull=True)
        .order_by("created_at")
    )
    cast = list(Teammate.objects.filter(universe=uni))
    existing_memories = list(
        NarrativeMemory.objects
        .filter(
            universe=uni,
            status=NarrativeMemoryStatus.REMEMBERED,
            archived_at__isnull=True,
        )
        .order_by("created_at")
    )

    print(f"F&F REMEMBERED memory count: {len(existing_memories)}")
    for m in existing_memories:
        print(
            f"  - {str(m.id)[:8]} kind={m.kind} "
            f"witnesses={[t.name for t in m.witnessed_by.all()]} "
            f"body={(m.body or '')[:120]!r}"
        )
    print()

    # Verify substrate hasn't drifted from what §75 assumed.
    assert composition.episode_id == episode.id, "composition/episode mismatch"
    assert episode.universe_id == uni.id, "episode/universe mismatch"

    task_message = _build_task_message(
        universe=uni,
        episode=episode,
        composition=composition,
        prior_episodes=prior_episodes,
        cast=cast,
        existing_memories=existing_memories,
    )

    started_utc = datetime.now(timezone.utc).isoformat()
    print("=== Firing single Q280.9 LLM call ===")
    t0 = time.time()
    raw, tokens_in, tokens_out = _call_openai(
        system_prompt=_SYSTEM_PROMPT,
        task_message=task_message,
    )
    elapsed = time.time() - t0
    finished_utc = datetime.now(timezone.utc).isoformat()
    print(
        f"elapsed={elapsed:.2f}s tokens_in={tokens_in} "
        f"tokens_out={tokens_out}"
    )

    # Try to parse for the summary console output; persist raw
    # regardless so scoring works even if parsing fails.
    parsed_ok = False
    parsed_error = None
    candidates_summary: list[dict] = []
    try:
        payload = json.loads(raw)
        cands = payload.get("candidates") or []
        if isinstance(cands, list):
            candidates_summary = cands
            parsed_ok = True
    except Exception as exc:
        parsed_error = f"{type(exc).__name__}: {exc}"

    evidence = {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "model": CURATOR_MODEL,
        "reasoning_effort": _REASONING_EFFORT,
        "max_output_tokens": _MAX_OUTPUT_TOKENS,
        "universe_id": FOX_AND_FLOUR_ID,
        "episode_id": EPISODE_11_ID,
        "composition_id": COMPOSITION_772E_ID,
        "existing_memory_ids": [str(m.id) for m in existing_memories],
        "existing_memory_bodies": [m.body for m in existing_memories],
        "system_prompt": _SYSTEM_PROMPT,
        "task_message": task_message,
        "raw_response_text": raw,
        "parsed_ok": parsed_ok,
        "parsed_error": parsed_error,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "elapsed_seconds": round(elapsed, 3),
        # Candidates as returned — preserved verbatim for the
        # audit doc; scoring is done by human.
        "candidates_verbatim": candidates_summary,
    }
    out_path = AUDIT_DIR / "q280_9_curator_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2))
    print(f"Wrote {out_path}")
    print()

    print("=== SUMMARY (verbatim candidates; scoring by human) ===")
    if not parsed_ok:
        print(f"  PARSE FAILED: {parsed_error}")
        print(f"  raw len={len(raw)}")
        print(f"  raw first 500 chars: {raw[:500]!r}")
    else:
        for i, c in enumerate(candidates_summary, 1):
            body = c.get("body", "") if isinstance(c, dict) else str(c)
            kind = c.get("kind", "") if isinstance(c, dict) else ""
            witnesses = (
                c.get("witnesses", []) if isinstance(c, dict) else []
            )
            note = (
                c.get("narrative_gravity_note", "")
                if isinstance(c, dict) else ""
            )
            print(f"[{i}] kind={kind} witnesses={witnesses}")
            print(f"    body: {body}")
            if note:
                print(f"    why:  {note}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
