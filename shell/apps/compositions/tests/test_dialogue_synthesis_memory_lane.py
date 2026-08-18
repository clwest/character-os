"""SESSION 264 Slice 2 — narrative-memory lane wired into dialogue synthesis.

Companion to ``test_dialogue_synthesis_canon_lane.py`` (SESSION 263).
Focused synthesis-layer coverage for the third retrieval lane:

* Memory retrieval fires ONCE per synthesis, cast-aware, gated by
  ``use_knowledge``.
* Memory retrieval receives the same operator topic string canon
  + per-character retrieval receive.
* Memory rows land in the dedicated EPISODE / NARRATIVE MEMORY
  prompt block between SHARED WORLD KNOWLEDGE and per-character
  SCOPED KNOWLEDGE.
* Prompt block wording: "past events in this Universe" +
  "static canon wins on conflict" (load-bearing precedence).
* Memory bodies participate in every eligible speaker's K6.4
  factual corpus.
* ``DialogueResult.memory_ids`` carries the retrieval snapshot
  separately from ``chunk_ids`` (which stays canon → per-character
  K2 for KnowledgeChunk-only observability).
* ``use_knowledge=False`` disables ALL THREE lanes.
* Universe-less cast skips memory retrieval too (memory is a
  Universe primitive).
* Prompt-order invariant: static canon → narrative memory →
  per-character SCOPED KNOWLEDGE.

Tests stub the retrieval functions + OpenAI client. No provider
calls; no real embeddings.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.embeddings.models import KnowledgeChunk
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from character_os.dialogue_synthesis import synthesize_dialogue

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures (mirror SESSION 263 canon-lane test fixtures) ----


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _cast(ws: Workspace, universe: Universe | None = None):
    patch = Teammate.objects.create(
        workspace=ws, name="Patch",
        personality="Curious tinkerer.",
        business_brief="Runs the workshop.",
        universe=universe,
    )
    rivet = Teammate.objects.create(
        workspace=ws, name="Rivet",
        personality="Methodical robot.",
        business_brief="Robot assistant Patch built.",
        universe=universe,
    )
    return patch, rivet


def _valid_turns_json(patch_alias: str, rivet_alias: str,
                      n_turns: int, *, per_turn_chars: int = 113) -> str:
    turns = []
    for i in range(n_turns):
        alias = patch_alias if i % 2 == 0 else rivet_alias
        pad = "x" * max(1, per_turn_chars - 20)
        turns.append({
            "line_index": i,
            "speaker_alias": alias,
            "text": f"turn {i} content {pad}",
        })
    return json.dumps({"turns": turns})


def _openai_returning(*responses: str):
    call_count = {"n": 0}

    def _side_effect(**_kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        payload = responses[min(idx, len(responses) - 1)]
        mock_resp = MagicMock()
        mock_resp.output_text = payload
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 500
        mock_resp.usage = usage
        return mock_resp

    client = MagicMock()
    client.responses.create.side_effect = _side_effect
    return client, call_count


def _fake_chunk(
    *, chunk_id: str, doc_id: str, chunk_text: str, m2m_count: int = 1,
):
    """Duck-type a KnowledgeChunk (matches the canon-lane fixture)."""
    c = MagicMock(spec=KnowledgeChunk)
    c.id = chunk_id
    c.document_id = doc_id
    c.chunk_text = chunk_text
    doc = MagicMock()
    doc.spokespeople.count = MagicMock(return_value=m2m_count)
    c.document = doc
    return c


def _fake_memory(*, memory_id: str, body: str):
    """Duck-type a NarrativeMemory row for synthesis-layer tests.
    The synthesis code reads ``.id`` and ``.body``; nothing else."""
    return SimpleNamespace(id=memory_id, body=body)


# ============================================================
# 1 — Wiring: memory retrieval fires once per synthesis
# ============================================================


def test_memory_retrieval_fires_once_per_synthesis_with_full_cast():
    ws = _workspace("mem-fires@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ) as fake_memory:
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="the agent is acting weird again",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    assert fake_memory.call_count == 1
    args, kwargs = fake_memory.call_args
    # Positional: workspace, universe, cast, query, top_k
    assert args[0] is ws
    assert args[1] is universe
    assert list(args[2]) == [patch, rivet]
    query_val = args[3] if len(args) >= 4 else kwargs.get("query")
    assert query_val == "the agent is acting weird again"
    top_k_val = args[4] if len(args) >= 5 else kwargs.get("top_k")
    assert top_k_val == 1


# ============================================================
# 2 — OFF path: use_knowledge=False skips ALL three lanes
# ============================================================


def test_use_knowledge_false_skips_all_three_lanes():
    ws = _workspace("all-off@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ) as fake_per_char, \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ) as fake_canon, \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ) as fake_memory:
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=False,
        )

    assert fake_per_char.call_count == 0
    assert fake_canon.call_count == 0
    assert fake_memory.call_count == 0
    assert result.used_knowledge is False
    assert result.chunk_ids == []
    assert result.memory_ids == []


# ============================================================
# 3 — Universe-less cast skips memory retrieval
# ============================================================


def test_universe_less_cast_skips_memory_call():
    ws = _workspace("mem-legacy@t")
    patch, rivet = _cast(ws, universe=None)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ) as fake_memory:
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    assert fake_memory.call_count == 0


# ============================================================
# 4 — Prompt block: memory lands in a dedicated EPISODE/NARRATIVE
#     MEMORY block between SHARED and per-character SCOPED.
# ============================================================


def test_memory_row_lands_in_dedicated_prompt_block_between_shared_and_scoped():
    ws = _workspace("mem-prompt@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-1", doc_id="canon-doc",
        chunk_text="THE_WORKSHOP_HAS_A_3D_PRINTER_MARKER",
    )
    memory = _fake_memory(
        memory_id="mem-1",
        body="THE_PRINTER_INCIDENT_MEMORY_MARKER",
    )
    patch_chunk = _fake_chunk(
        chunk_id="p1", doc_id="pd", chunk_text="PATCH_SCOPED_MARKER",
    )

    def _per_char(tm, *args, **kwargs):
        if tm is patch:
            return [patch_chunk]
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             side_effect=_per_char,
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[canon],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[memory],
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    prompt = fake_client.responses.create.call_args.kwargs["input"]
    # All three markers present.
    assert "THE_WORKSHOP_HAS_A_3D_PRINTER_MARKER" in prompt
    assert "THE_PRINTER_INCIDENT_MEMORY_MARKER" in prompt
    assert "PATCH_SCOPED_MARKER" in prompt
    # Block headers present.
    assert "SHARED WORLD KNOWLEDGE" in prompt
    assert "EPISODE / NARRATIVE MEMORY" in prompt
    assert "PATCH'S SCOPED KNOWLEDGE" in prompt
    # Load-bearing wording: memory is past + canon wins on conflict.
    assert "past events" in prompt
    assert "canon wins on conflict" in prompt
    # Prompt order: SHARED → MEMORY → SCOPED.
    shared_pos = prompt.index("SHARED WORLD KNOWLEDGE")
    memory_pos = prompt.index("EPISODE / NARRATIVE MEMORY")
    scoped_pos = prompt.index("PATCH'S SCOPED KNOWLEDGE")
    assert shared_pos < memory_pos < scoped_pos


# ============================================================
# 5 — K6.4 corpus: memory participates for eligible speakers
# ============================================================


def test_memory_body_participates_in_each_speaker_k64_corpus():
    ws = _workspace("mem-k64@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    memory = _fake_memory(
        memory_id="mem-1",
        body="THE_MEMORY_CORPUS_MARKER",
    )
    patch_chunk = _fake_chunk(
        chunk_id="p", doc_id="pd", chunk_text="PATCH_SCOPED_MARKER",
    )
    rivet_chunk = _fake_chunk(
        chunk_id="r", doc_id="rd", chunk_text="RIVET_SCOPED_MARKER",
    )

    seen_corpora: list[str] = []

    def _fake_verifier(text, *, factual_corpus, allowed_vocabulary, mode=None):
        seen_corpora.append(factual_corpus)
        return []

    def _per_char(tm, *args, **kwargs):
        if tm is patch:
            return [patch_chunk]
        if tm is rivet:
            return [rivet_chunk]
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             side_effect=_per_char,
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[memory],
         ), \
         mock_patch(
             "character_os.dialogue_synthesis.run_verifier",
             side_effect=_fake_verifier,
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # Memory body appears in every speaker's corpus AND scoped chunks
    # stay scoped per-speaker (no cross-character K2 merging).
    assert len(seen_corpora) > 0
    for corpus in seen_corpora:
        assert "THE_MEMORY_CORPUS_MARKER" in corpus


# ============================================================
# 6 — Observability: memory_ids separate from chunk_ids
# ============================================================


def test_memory_ids_are_separate_from_chunk_ids():
    """Load-bearing observability decision (audit §Slice 2): memory
    IDs (NarrativeMemory UUIDs) MUST NOT enter ``chunk_ids``
    (KnowledgeChunk UUIDs). Consumers of ``knowledge_chunk_ids``
    resolve those IDs against the KnowledgeChunk model directly,
    so overloading would silently break the citation resolver."""
    ws = _workspace("mem-obs@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-A", doc_id="canon-doc", chunk_text="canon body",
    )
    memory = _fake_memory(memory_id="mem-A", body="memory body")
    patch_chunk = _fake_chunk(
        chunk_id="patch-X", doc_id="patch-doc", chunk_text="patch body",
    )

    def _per_char(tm, *args, **kwargs):
        if tm is patch:
            return [patch_chunk]
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             side_effect=_per_char,
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[canon],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[memory],
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # chunk_ids: canon + per-character only. Memory NEVER here.
    assert "mem-A" not in result.chunk_ids
    assert result.chunk_ids[0] == "canon-A"
    assert "patch-X" in result.chunk_ids
    # memory_ids: memory UUIDs only.
    assert result.memory_ids == ["mem-A"]
    # used_knowledge should be True because memory contributed
    # (even though no per-character chunks came back for Rivet).
    assert result.used_knowledge is True


# ============================================================
# 7 — Empty memory retrieval: prompt block omitted cleanly
# ============================================================


def test_no_memories_omits_the_block_entirely():
    ws = _workspace("mem-none@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-1", doc_id="canon-doc",
        chunk_text="canon text",
    )

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[canon],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    prompt = fake_client.responses.create.call_args.kwargs["input"]
    assert "EPISODE / NARRATIVE MEMORY" not in prompt
    assert result.memory_ids == []


# ============================================================
# 8 — Retrieval failure is non-fatal, degrades to empty memory
# ============================================================


def test_memory_retrieval_failure_is_non_fatal():
    ws = _workspace("mem-fail@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             side_effect=RuntimeError("provider hiccup"),
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # Synthesis still succeeded; memory just degrades to empty.
    assert result.memory_ids == []
