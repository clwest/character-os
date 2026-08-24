"""SESSION 279 — Q-279-3 Phase 2 real-model synthesis probe.

Three-condition writer-voice attractor probe. Exercises the real
production ``synthesize_dialogue()`` path with real production
inputs (real Fox & Flour Ruby + Tyson from the real DB, real
Knowledge, real embeddings, real gpt-family LLM). Does NOT create
Composition rows. Does NOT invoke Runway / media-engine. Does NOT
render avatar speech or video. Writes ONLY to a durable audit
artifact directory.

Design: see SESSION_279_CHARACTER_KNOWLEDGE_DEPTH_AUDIT.md §107-§117
(the Phase-2 reconciliation approved by Chris + ChatGPT).

Conditions:

  * P2-A "baseline"          — no monkeypatch. Everything production.
  * P2-B "contract-lite"     — WritingContract.for_shape('dialogue_scene')
                               substituted with §111.3 + §111.4 lite
                               variant (watchability §1 wants-list
                               replaced with permissive stance rule;
                               narrative-shapes menu replaced with
                               "no prescribed skeleton"). All other
                               contract elements unchanged.
  * P2-C "personality-lite"  — Ruby.personality + Tyson.personality
                               substituted in-memory with neutral
                               free-text ("Ruby is friendly and
                               helpful." / "Tyson is friendly and
                               helpful."). All other Teammate fields
                               unchanged. No DB write.

Isolation:

  * Monkeypatches applied via ``try/finally``; the finally block
    restores the original class attribute / instance attribute
    before the probe returns.
  * P2-C substitution mutates in-memory Teammate instances only;
    ``.save()`` is never called on Ruby or Tyson during the probe,
    so the DB row remains untouched.
  * The probe writes to ``docs/design/session279_phase2/*.json`` +
    ``docs/design/session279_phase2/*.txt``. It does NOT write to
    the production Django DB.

Measurement (per §114, locked BEFORE run):

  * COMPOSITE attractor rate per 1000 chars =
    (D1 + D2 + D3 + D4a + D4n) / total_chars * 1000
    D1n is NOT added — it is a subset of D1.
  * Per-family breakdown reported alongside composite.

Usage:
  set -a; source .env; set +a; python scripts/session279_q279_3_phase2_probe.py
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

import character_os.writing_contract as wc_mod  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from character_os.dialogue_synthesis import synthesize_dialogue  # noqa: E402
from character_os.writing_contract import WritingContract  # noqa: E402


TOPIC = (
    "Ruby and Tyson watch the sunrise through the bakery window before opening."
)
TARGET_DURATION_SECONDS = 90
SAMPLES_PER_CONDITION = 3
AUDIT_DIR = _REPO_ROOT / "docs" / "design" / "session279_phase2"

RUBY_ID = "9d69a80c-ff69-4dbc-84eb-f76b02f22add"  # resolved below via name
TYSON_ID = "f4de81f3-ef65-4196-a50e-38cfc6d1854f"


# ---- Contract-lite substitution text (audit §111.3 + §111.4) -----

_LITE_WATCHABILITY_BLOCK = (
    "DIALOGUE WATCHABILITY (behavioral guidance — every scene, "
    "regardless of narrative shape chosen)\n"
    "\n"
    "  1. ENTER WITH AN IN-SCENE STANCE\n"
    "     Each character arrives with a purpose for THIS scene. "
    "Observation, sharing, acknowledgment, curiosity, or "
    "question-asking are all valid stances. This does not mean "
    "every scene requires hostility, argument, or comedy — "
    "collaboration is a valid stance when the topic calls for it. "
    "A character with no in-scene stance should not speak.\n"
    "\n"
    "  2. SOMETHING CHANGES\n"
    "     The scene must not end in the same conversational "
    "state in which it began. Somewhere between opening and "
    "close, at least one meaningful change should occur: new "
    "information, correction, decision, concession, reveal, "
    "escalation, misunderstanding resolved, new question, "
    "changed plan, discovered problem, or earned agreement. If "
    "no character moves, the scene didn't happen.\n"
    "\n"
    "  3. PREFER SPECIFIC ACTION / REACTION OVER PHILOSOPHY\n"
    "     Characters should talk about what is happening, what "
    "just happened, what they want to try, what they noticed, "
    "what broke, what surprised them, or what they want next. "
    "Prefer 'Run it again.' over 'Our methodology emphasizes "
    "repeatability.' Prefer 'What did you change?' over 'We "
    "should separate variables during experimentation.' The "
    "underlying knowledge may drive the line without being "
    "recited.\n"
    "\n"
    "  4. KNOWLEDGE INFLUENCES — IT DOES NOT NEED TO BE QUOTED\n"
    "     Retrieved knowledge is factual grounding and context. "
    "Do NOT feel obligated to reproduce frameworks, headings, "
    "lists, slogans, or methodology language from the retrieved "
    "chunks. Translate knowledge into natural character behavior "
    "whenever possible. A character who knows experimental "
    "methodology can ask 'Did you try it twice?' — they do not "
    "need to say 'Our framework requires repeatable validation.'\n"
    "\n"
    "  5. END ON A MOMENT, NOT A SUMMARY\n"
    "     Prefer endings such as a reaction, decision, reveal, "
    "callback, escalation, challenge, refusal, concession, "
    "naturally-earned punchline, or unresolved hook. Avoid "
    "wrapping the scene with both characters summarizing their "
    "roles, relationship, philosophy, or shared lesson. Let the "
    "scene finish while something is still happening."
)

_LITE_NARRATIVE_SHAPES_BLOCK = (
    "NARRATIVE SHAPE — no prescribed skeleton; write the scene "
    "the topic calls for. Legitimate hybrids are fine. Do not "
    "force conflict, argument, or reveal shape when the topic "
    "does not require it."
)


def _dialogue_scene_contract_lite() -> str:
    """§111.5 substitute: two blocks replaced; all other elements
    unchanged. Assembles the same overall dialogue_scene contract
    as ``wc_mod._dialogue_scene_contract`` with only the two
    identified stakes-elevating pieces neutralized."""
    return "\n\n".join([
        "SHAPE — multi-character dialogue",
        "The scene is a conversation between the characters "
        "introduced in Section 2. Every turn is spoken by one "
        "character. The audience is watching a real exchange, "
        "not a pair of parallel presentations.",
        wc_mod._DIALOGUE_INVARIANTS_BLOCK,
        _LITE_WATCHABILITY_BLOCK,
        wc_mod._DIALOGUE_ANTI_PATTERNS_BLOCK,
        _LITE_NARRATIVE_SHAPES_BLOCK,
        wc_mod._CTA_POLICY_BLOCK,
        wc_mod._ANTI_SELF_DESCRIPTION_BLOCK,
        wc_mod._ANTI_GENERIC_REGISTER_BLOCK,
    ])


# ---- Rubric (locked at §95.1 / §99.1; unchanged) -----------------

D1_RE     = re.compile(r"\b(?:That is|That was|That['\u2019]s)\s+(?:not|a\b|an\b)", re.IGNORECASE)
D1_NEG_RE = re.compile(r"\b(?:That is|That was|That['\u2019]s)\s+not\b", re.IGNORECASE)
D1_AST_RE = re.compile(r"\b(?:That is|That was|That['\u2019]s)\s+(?:a|an)\b", re.IGNORECASE)
_D2_FORMAL = (
    "courtroom|committee|hearing|kingdom|empire|government|ceremony|ritual|"
    "institution|bureaucrat|judgment|dispute|tribunal|parliament|ministry|"
    "department|agency|chamber|jury|coup|revolution|rebellion|throne|army|"
    "insurrection|protocol|procedure|board|panel|cabinet|oath|contract|treaty|"
    "invasion|treason|battle|court|campaign|verdict|dossier|briefing|club|"
    "management|company|business|corporation|police|policy"
)
D2_RE = re.compile(rf"\b(?:tiny|small|little)\s+(?:{_D2_FORMAL})\b", re.IGNORECASE)
_D3_LEX = [
    "court","trial","judge","jury","deposition","evidence","testify","witness",
    "verdict","detective","rehears","inspector","committee","hearing","defend",
    "prosecut",
]
D3_RE = re.compile(r"\b(?:" + "|".join(_D3_LEX) + r")\w*\b", re.IGNORECASE)
D4_ADJ_RE = re.compile(r"\b(?:serious|consequential|important|dramatic)\w*\b", re.IGNORECASE)
D4_NOT_RE = re.compile(r"\bnot (?:casual|small|a\b)", re.IGNORECASE)


def score_text(text: str) -> dict:
    return dict(
        chars=len(text),
        D1=len(D1_RE.findall(text)),
        D1n=len(D1_NEG_RE.findall(text)),
        D1a=len(D1_AST_RE.findall(text)),
        D2=len(D2_RE.findall(text)),
        D3=len(D3_RE.findall(text)),
        D4a=len(D4_ADJ_RE.findall(text)),
        D4n=len(D4_NOT_RE.findall(text)),
    )


def score_dialogue(result) -> dict:
    per_speaker: dict = {}
    tot: dict = dict(chars=0, turns=0, D1=0, D1n=0, D1a=0, D2=0, D3=0, D4a=0, D4n=0)
    for turn in result.turns:
        sc = score_text(turn.text)
        sp = getattr(turn.speaker_teammate, "name", turn.speaker_alias)
        acc = per_speaker.setdefault(
            sp, dict(chars=0, turns=0, D1=0, D1n=0, D1a=0, D2=0, D3=0, D4a=0, D4n=0)
        )
        acc["turns"] += 1
        acc["chars"] += sc["chars"]
        for k in ("D1", "D1n", "D1a", "D2", "D3", "D4a", "D4n"):
            acc[k] += sc[k]
            tot[k] += sc[k]
        tot["turns"] += 1
        tot["chars"] += sc["chars"]
    composite = tot["D1"] + tot["D2"] + tot["D3"] + tot["D4a"] + tot["D4n"]
    out = dict(tot)  # widen to Any for the float field
    out["composite"] = composite
    out["composite_per_1k"] = (
        1000.0 * composite / tot["chars"] if tot["chars"] else 0.0
    )
    return dict(total=out, per_speaker=per_speaker)


# ---- Condition runners ------------------------------------------


def _sample_baseline(workspace, cast, sample_idx: int) -> dict:
    """P2-A. Real production behaviour. No monkeypatch."""
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
    return _package_sample("A", sample_idx, result, elapsed)


def _sample_contract_lite(workspace, cast, sample_idx: int) -> dict:
    """P2-B. Monkeypatch WritingContract.for_shape only."""
    original_for_shape = WritingContract.for_shape

    def _lite(shape: str, **kwargs) -> str:
        if shape == "dialogue_scene":
            return _dialogue_scene_contract_lite()
        return original_for_shape(shape, **kwargs)

    WritingContract.for_shape = staticmethod(_lite)
    try:
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
    finally:
        WritingContract.for_shape = original_for_shape
    return _package_sample("B", sample_idx, result, elapsed)


def _sample_personality_lite(workspace, cast, sample_idx: int) -> dict:
    """P2-C. Mutate cast[i].personality in-memory only."""
    saved = {tm.pk: tm.personality for tm in cast}
    try:
        for tm in cast:
            tm.personality = f"{tm.name} is friendly and helpful."
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
    finally:
        for tm in cast:
            tm.personality = saved[tm.pk]
    return _package_sample("C", sample_idx, result, elapsed)


def _package_sample(config: str, sample_idx: int, result, elapsed: float) -> dict:
    scored = score_dialogue(result)
    turns_dump = [
        dict(
            line_index=t.line_index,
            speaker=getattr(t.speaker_teammate, "name", t.speaker_alias),
            text=t.text,
        )
        for t in result.turns
    ]
    return dict(
        config=config,
        sample_idx=sample_idx,
        topic=TOPIC,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        elapsed_seconds=round(elapsed, 2),
        model=getattr(result, "model", ""),
        tokens_input=getattr(result, "tokens_input", 0),
        tokens_output=getattr(result, "tokens_output", 0),
        attempt_count=getattr(result, "attempt_count", 0),
        total_chars=result.total_chars,
        predicted_seconds=round(result.predicted_seconds, 2),
        chunk_ids=list(result.chunk_ids),
        aliases=dict(result.aliases),
        turns=turns_dump,
        scored=scored,
        writing_contract_version=result.writing_contract_version,
        used_knowledge=result.used_knowledge,
        overall_verification_status=result.overall_verification_status,
    )


# ---- Restoration verification ------------------------------------


def _verify_restored() -> None:
    """Post-run sanity: WritingContract.for_shape must produce the
    real production dialogue_scene contract; personality of Ruby +
    Tyson must be non-neutral."""
    prod_contract = WritingContract.for_shape("dialogue_scene")
    # Contract-lite marker: the neutral shape sentence is only
    # present in the lite variant.
    lite_marker = "no prescribed skeleton"
    if lite_marker in prod_contract:
        raise RuntimeError(
            "WritingContract.for_shape appears to still be monkeypatched "
            "at exit — contract-lite marker present."
        )
    # Personality check via DB fetch (not the mutable in-memory
    # instance we just restored).
    ruby = Teammate.objects.get(pk=RUBY_ID)
    tyson = Teammate.objects.get(pk=TYSON_ID)
    if "friendly and helpful." in (ruby.personality or "") and len(ruby.personality or "") < 50:
        raise RuntimeError("Ruby.personality appears to be the neutral substitute in DB.")
    if "friendly and helpful." in (tyson.personality or "") and len(tyson.personality or "") < 50:
        raise RuntimeError("Tyson.personality appears to be the neutral substitute in DB.")


# ---- Main ---------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=["A", "B", "C", "ALL"], default="ALL")
    ap.add_argument("--n", type=int, default=SAMPLES_PER_CONDITION)
    ap.add_argument("--out", default=str(AUDIT_DIR / "phase2_evidence.json"))
    args = ap.parse_args()

    global RUBY_ID
    # Resolve Ruby by name+universe (guard against hardcoded pk drift).
    ruby = Teammate.objects.get(
        name="Ruby",
        universe__slug="fox-flour-bakery",
    )
    tyson = Teammate.objects.get(
        name="Tyson",
        universe__slug="fox-flour-bakery",
    )
    RUBY_ID = str(ruby.pk)
    assert str(tyson.pk) == TYSON_ID, (
        f"Tyson pk drift: expected {TYSON_ID}, got {tyson.pk}"
    )
    workspace = ruby.workspace
    cast = [ruby, tyson]

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    runners = dict(A=_sample_baseline, B=_sample_contract_lite, C=_sample_personality_lite)
    order = ["A", "B", "C"] if args.config == "ALL" else [args.config]

    all_samples: list[dict] = []
    started = datetime.now(timezone.utc).isoformat()
    for cfg in order:
        for i in range(1, args.n + 1):
            sys.stdout.write(f"[{cfg}#{i}] synthesizing... ")
            sys.stdout.flush()
            sample = runners[cfg](workspace, cast, i)
            comp = sample["scored"]["total"]["composite"]
            per1k = sample["scored"]["total"]["composite_per_1k"]
            chars = sample["scored"]["total"]["chars"]
            sys.stdout.write(
                f"turns={len(sample['turns'])} chars={chars} "
                f"composite={comp} composite/1k={per1k:.3f} "
                f"elapsed={sample['elapsed_seconds']}s\n"
            )
            all_samples.append(sample)
            # Persist raw dialogue as text artifact for durable audit.
            txt_path = AUDIT_DIR / f"p2{cfg.lower()}_sample{i}.txt"
            with txt_path.open("w") as f:
                f.write(f"# Q-279-3 Phase 2  config=P2-{cfg}  sample={i}\n")
                f.write(f"# topic: {TOPIC}\n")
                f.write(
                    f"# model={sample['model']}  attempt_count={sample['attempt_count']}  "
                    f"total_chars={chars}  predicted_seconds={sample['predicted_seconds']}s\n"
                )
                f.write(
                    f"# composite={comp}  composite_per_1k={per1k:.3f}\n\n"
                )
                for t in sample["turns"]:
                    f.write(f"{t['speaker']}: {t['text']}\n\n")

    _verify_restored()

    aggregate: dict = {}
    for cfg in order:
        cfg_samples = [s for s in all_samples if s["config"] == cfg]
        tot_chars = sum(s["scored"]["total"]["chars"] for s in cfg_samples)
        tot_comp = sum(s["scored"]["total"]["composite"] for s in cfg_samples)
        agg = dict(
            n=len(cfg_samples),
            total_chars=tot_chars,
            total_turns=sum(s["scored"]["total"]["turns"] for s in cfg_samples),
            composite_hits=tot_comp,
            composite_per_1k=1000.0 * tot_comp / tot_chars if tot_chars else 0.0,
            D1=sum(s["scored"]["total"]["D1"] for s in cfg_samples),
            D1n=sum(s["scored"]["total"]["D1n"] for s in cfg_samples),
            D1a=sum(s["scored"]["total"]["D1a"] for s in cfg_samples),
            D2=sum(s["scored"]["total"]["D2"] for s in cfg_samples),
            D3=sum(s["scored"]["total"]["D3"] for s in cfg_samples),
            D4a=sum(s["scored"]["total"]["D4a"] for s in cfg_samples),
            D4n=sum(s["scored"]["total"]["D4n"] for s in cfg_samples),
        )
        aggregate[f"P2-{cfg}"] = agg

    finished = datetime.now(timezone.utc).isoformat()
    with Path(args.out).open("w") as f:
        json.dump(dict(
            started_utc=started, finished_utc=finished,
            topic=TOPIC, target_duration_seconds=TARGET_DURATION_SECONDS,
            samples_per_condition=args.n,
            ruby_id=RUBY_ID, tyson_id=TYSON_ID,
            samples=all_samples, aggregate=aggregate,
        ), f, indent=2)

    print()
    print("=== AGGREGATE PER CONDITION ===")
    for cfg, agg in aggregate.items():
        print(
            f"  {cfg}: n={agg['n']}  chars={agg['total_chars']}  "
            f"turns={agg['total_turns']}  composite={agg['composite_hits']}  "
            f"composite/1k={agg['composite_per_1k']:.3f}  "
            f"D1={agg['D1']} D1n={agg['D1n']} D1a={agg['D1a']} D2={agg['D2']} "
            f"D3={agg['D3']} D4a={agg['D4a']} D4n={agg['D4n']}"
        )
    if "P2-A" in aggregate and "P2-B" in aggregate:
        d = aggregate["P2-A"]["composite_per_1k"]
        r = aggregate["P2-B"]["composite_per_1k"]
        pct = 100.0 * (r - d) / d if d else 0.0
        print(f"  H1 (contract): P2-B/P2-A composite/1k = {r:.3f}/{d:.3f} = {pct:+.1f}%")
    if "P2-A" in aggregate and "P2-C" in aggregate:
        d = aggregate["P2-A"]["composite_per_1k"]
        r = aggregate["P2-C"]["composite_per_1k"]
        pct = 100.0 * (r - d) / d if d else 0.0
        print(f"  H3 (persona): P2-C/P2-A composite/1k = {r:.3f}/{d:.3f} = {pct:+.1f}%")
    print()
    print(f"Evidence written to {args.out}")
    print(f"Raw dialogues written to {AUDIT_DIR}/p2*_sample*.txt")
    print("Post-run restoration verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
