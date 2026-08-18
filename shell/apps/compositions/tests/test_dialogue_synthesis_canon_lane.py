"""SESSION 263 Slice B + C.1 — canon lane wired into dialogue synthesis.

Focused synthesis-layer coverage:

* Canon retrieval fires ONCE per synthesis, cast-aware.
* Canon retrieval receives the same topic string as per-character
  retrieval — the operator's topic is preserved verbatim.
* Canon chunks land in the SHARED prompt block deterministically
  (independent of the pre-SESSION-263 post-hoc detector).
* Each speaking character's K6.4 factual corpus contains the
  canon chunk text (so canon-cited facts pass verification for
  either speaker).
* ``Composition.knowledge_chunk_ids`` (via
  ``DialogueResult.chunk_ids``) contains the canon chunk IDs
  alongside per-character IDs, canon-first for provenance.
* ``use_knowledge=False`` disables BOTH character retrieval AND
  the canon lane.
* C.1 scope-aware SHARED promotion — a per-character retrieval
  that happens to surface a scope-shared doc (M2M-null or
  M2M-many) does not mislabel that chunk under a character
  SCOPED block. The chunk gets promoted to the SHARED block.

Tests use ``mock_patch`` to stub both retrieval calls and the
OpenAI client — no provider calls, no real embeddings.
"""
from __future__ import annotations

import json
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


# ---- fixtures ----------------------------------------------------


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
    """Duck-type a KnowledgeChunk without touching the DB. The
    dialogue synthesis path reads ``.id``, ``.document_id``,
    ``.chunk_text``, and ``.document`` — the latter only via
    ``_is_scope_shared_document`` which touches
    ``.spokespeople.count()``. Default ``m2m_count=1`` matches
    the character-scoped case; tests exercising C.1 promotion
    override to 0 (M2M-null) or ``>1`` (M2M-many)."""
    c = MagicMock(spec=KnowledgeChunk)
    c.id = chunk_id
    c.document_id = doc_id
    c.chunk_text = chunk_text
    doc = MagicMock()
    doc.spokespeople.count = MagicMock(return_value=m2m_count)
    c.document = doc
    return c


# ---- canon-lane wiring ------------------------------------------


def test_canon_retrieval_fires_once_per_synthesis_with_full_cast():
    ws = _workspace("canon-fires@t")
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
         ) as fake_canon:
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic worth talking about",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # ONE canon call total (not per-character).
    assert fake_canon.call_count == 1
    call = fake_canon.call_args
    # Positional: workspace, universe, cast, query, top_k
    args = call.args
    kwargs = call.kwargs
    # workspace + universe + cast may be passed positionally.
    assert args[0] is ws
    assert args[1] is universe
    assert list(args[2]) == [patch, rivet]
    # Query is the operator topic, verbatim.
    query_val = args[3] if len(args) >= 4 else kwargs.get("query")
    assert query_val == "a topic worth talking about"
    # top_k defaults to 2 per audit — passed either positionally or as kwarg.
    top_k_val = args[4] if len(args) >= 5 else kwargs.get("top_k")
    assert top_k_val == 2


def test_use_knowledge_false_skips_canon_and_per_character():
    ws = _workspace("canon-off@t")
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
         ) as fake_canon:
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=False,
        )

    assert fake_per_char.call_count == 0
    assert fake_canon.call_count == 0
    assert result.used_knowledge is False
    assert result.chunk_ids == []


def test_universe_less_cast_skips_canon_call():
    """A cast whose members have no Universe (legacy) does not
    fire the canon lane — canon is a Universe primitive."""
    ws = _workspace("canon-legacy-cast@t")
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
         ) as fake_canon:
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    assert fake_canon.call_count == 0


# ---- canon → prompt SHARED block --------------------------------


def test_canon_chunk_lands_in_shared_prompt_block():
    ws = _workspace("canon-prompt@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-1",
        doc_id="canon-doc",
        chunk_text="THE_WORKSHOP_HAS_A_3D_PRINTER_MARKER",
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
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic under test",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # The system prompt is the first positional arg on
    # ``client.responses.create``. Inspect it.
    call_kwargs = fake_client.responses.create.call_args.kwargs
    prompt = call_kwargs["input"]
    assert "SHARED WORLD KNOWLEDGE" in prompt
    assert "THE_WORKSHOP_HAS_A_3D_PRINTER_MARKER" in prompt


def test_canon_chunk_ids_prefixed_in_observability_aggregate():
    """Canon IDs land first in ``chunk_ids`` for provenance."""
    ws = _workspace("canon-ids@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-A", doc_id="canon-doc", chunk_text="canon body",
    )
    patch_chunk = _fake_chunk(
        chunk_id="patch-X", doc_id="patch-doc", chunk_text="patch body",
    )
    rivet_chunk = _fake_chunk(
        chunk_id="rivet-Y", doc_id="rivet-doc", chunk_text="rivet body",
    )
    # per-character retrieval returns different chunks per teammate;
    # the mock has no idea which caller it is, so return a callable
    # side_effect that keys on the first positional arg.
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
             return_value=[canon],
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic under test",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # Canon-first ordering + per-character IDs present + deduped.
    assert result.chunk_ids[0] == "canon-A"
    assert set(result.chunk_ids) == {"canon-A", "patch-X", "rivet-Y"}
    # Per-character IDs unchanged.
    assert result.per_character_chunk_ids["patch"] == ["patch-X"]
    assert result.per_character_chunk_ids["rivet"] == ["rivet-Y"]


# ---- K6.4 corpus participation ----------------------------------


def test_canon_chunk_participates_in_each_speaker_k64_corpus():
    """Each speaker's factual corpus contains the canon chunk text
    (SESSION 263 requirement: canon-cited facts pass K6.4 for
    either speaker without cross-character K2 merging)."""
    ws = _workspace("canon-k64@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    canon = _fake_chunk(
        chunk_id="canon-1", doc_id="canon-doc",
        chunk_text="THE_CANON_SENTENCE_MARKER",
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
             return_value=[canon],
         ), \
         mock_patch(
             "character_os.dialogue_synthesis.run_verifier",
             side_effect=_fake_verifier,
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic under test",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # 8 turns → 8 verifier calls → 8 captured corpora.
    assert len(seen_corpora) == 8
    # Every speaker's corpus contains the canon marker (each
    # speaker can cite canon).
    for corpus in seen_corpora:
        assert "THE_CANON_SENTENCE_MARKER" in corpus

    # Character isolation is preserved: Patch's corpus (even turns)
    # never contains Rivet's marker, and vice versa.
    for i, corpus in enumerate(seen_corpora):
        if i % 2 == 0:  # Patch speaks even turns
            assert "PATCH_SCOPED_MARKER" in corpus
            assert "RIVET_SCOPED_MARKER" not in corpus
        else:  # Rivet speaks odd turns
            assert "RIVET_SCOPED_MARKER" in corpus
            assert "PATCH_SCOPED_MARKER" not in corpus


# ---- C.1 scope-aware SHARED promotion ---------------------------


def test_per_character_retrieval_of_scope_shared_chunk_promoted_to_shared():
    """C.1 fix — a chunk that appears in a character's per-
    character retrieval but whose document is scope-shared
    (M2M-null or M2M count > 1) is promoted to the SHARED block,
    NOT mislabelled under that character's SCOPED block."""
    ws = _workspace("canon-c1@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    # Doc appears in Patch's per-character retrieval (via cosine
    # ranking) but its document is M2M-null → scope-shared. The
    # C.1 detector treats ``m2m_count == 0`` as broadcast canon.
    shared_leak = _fake_chunk(
        chunk_id="leak", doc_id="shared-doc",
        chunk_text="THE_LEAKED_SCOPE_SHARED_MARKER",
        m2m_count=0,
    )

    def _per_char(tm, *args, **kwargs):
        if tm is patch:
            return [shared_leak]
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
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic under test",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    prompt = fake_client.responses.create.call_args.kwargs["input"]

    # The chunk text must appear under SHARED, not under PATCH SCOPED.
    assert "SHARED WORLD KNOWLEDGE" in prompt
    assert "THE_LEAKED_SCOPE_SHARED_MARKER" in prompt
    # PATCH's SCOPED block still exists (identity fields) but does
    # not contain the scope-shared chunk text.
    # Split the prompt on the two section headers and check.
    shared_start = prompt.index("SHARED WORLD KNOWLEDGE")
    patch_start = prompt.index("PATCH'S SCOPED KNOWLEDGE")
    if shared_start < patch_start:
        shared_block = prompt[shared_start:patch_start]
    else:
        # SHARED after PATCH — split differently.
        rivet_start = prompt.index("RIVET'S SCOPED KNOWLEDGE") \
            if "RIVET'S SCOPED KNOWLEDGE" in prompt else len(prompt)
        shared_block = prompt[shared_start:rivet_start]
    assert "THE_LEAKED_SCOPE_SHARED_MARKER" in shared_block


def test_per_character_scope_single_stays_in_character_block():
    """Contrast to the above — a chunk from a doc scoped to
    exactly one teammate (M2M count == 1) stays in that
    character's SCOPED block. The C.1 detector does not
    incorrectly promote per-character docs."""
    ws = _workspace("canon-nopromote@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    patch_only = _fake_chunk(
        chunk_id="p1", doc_id="pd",
        chunk_text="THE_PATCH_ONLY_MARKER",
        m2m_count=1,
    )

    def _per_char(tm, *args, **kwargs):
        if tm is patch:
            return [patch_only]
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
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="topic under test",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    prompt = fake_client.responses.create.call_args.kwargs["input"]
    # The chunk should appear under PATCH'S SCOPED KNOWLEDGE, not SHARED.
    assert "THE_PATCH_ONLY_MARKER" in prompt
    # No SHARED WORLD KNOWLEDGE block because no scope-shared or canon chunks.
    assert "SHARED WORLD KNOWLEDGE" not in prompt
