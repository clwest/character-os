"""SESSION 269 §10 — narrative-memory lane wired into talking_head.

Companion to ``test_dialogue_synthesis_memory_lane.py`` (SESSION 264
Slice 2) and ``test_dialogue_synthesis_canon_lane.py`` (SESSION 263).
Focused coverage for the solo-cast memory retrieval path added by
the pre-Rivet / Rivet-solo product gap identified in SESSION 269
§9:

* solo talking_head with a Universe-scoped spokesperson calls
  ``retrieve_universe_memory`` with ``cast=[spokesperson]`` and
  ``top_k=1``;
* the same retrieval predicate governs eligibility (whole-cast +
  overlap semantics; Rivet-only invisible to Patch-solo and vice
  versa; workspace + universe isolation preserved);
* retrieved memory rows land inside the §1 Factual Basis prompt
  block with the past-events framing the dialogue lane uses;
* ``Composition.memory_ids`` receives the selected UUIDs via the
  same recipe-agnostic JSONField the dialogue path writes to
  (SESSION 264 Slice 2);
* legacy universe-less spokespeople skip retrieval entirely (no
  regression on pre-§10 talking_head shape);
* ``use_knowledge=False`` skips retrieval (K6 short-circuits on
  the trusted-passthrough branch);
* ``build_render_brief`` still calls the LLM when only memory rows
  are present (empty K2 chunks alone must NOT short-circuit past
  the memory block).

Tests are hermetic: the OpenAI client + the retrieval calls that
have their own dedicated suites are patched. The retrieval
PREDICATE itself is exercised through real DB fixtures in
``apps/embeddings/tests/test_retrieval_universe_memory.py`` — see
§Patch-solo + Rivet-solo eligibility below for the two new
solo-cast cases added here.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.compositions.models import Composition, CompositionStep
from apps.compositions.primitives.avatar_speech import (
    _maybe_synthesize_script,
)
from apps.embeddings.models import EMBEDDING_DIMENSION
from apps.embeddings.retrieval import retrieve_universe_memory
from apps.memory.models import NarrativeMemory, NarrativeMemoryStatus
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe
from character_os.script_synthesis import (
    ScriptResult,
    _build_factual_basis_section,
    build_render_brief,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures ------------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _cast(ws: Workspace, universe: Universe | None):
    patch = Teammate.objects.create(
        workspace=ws, universe=universe, name="Patch",
        runway_avatar_id="av-patch",
        portrait_path="https://fake/patch.png",
        business_brief="Workshop inventor.",
    )
    rivet = Teammate.objects.create(
        workspace=ws, universe=universe, name="Rivet",
        runway_avatar_id="av-rivet",
        portrait_path="https://fake/rivet.png",
        business_brief="Counterweight.",
    )
    return patch, rivet


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIMENSION
    v[0] = seed
    return v


def _episode_with_composition(ws, universe, cast, spokesperson=None):
    episode = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic="The printer decided to make Patch royalty.",
    )
    for tm in cast:
        episode.cast.add(tm)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=spokesperson or cast[0],
        name="AI-lab source",
        template_kind="dialogue_scene",
        mock_mode=True,
        operator_topic=episode.operator_topic,
        episode=episode,
    )
    return episode, comp


def _memory(
    ws, universe, episode, comp, body: str,
    *,
    witnessed_by=None,
    vector=None,
    status=NarrativeMemoryStatus.REMEMBERED,
    archived: bool = False,
    embedded: bool = True,
) -> NarrativeMemory:
    m = NarrativeMemory.objects.create(
        episode=episode,
        source_composition=comp,
        workspace=ws,
        universe=universe,
        body=body,
        status=status,
        archived_at=timezone.now() if archived else None,
    )
    if witnessed_by:
        m.witnessed_by.set(witnessed_by)
    if embedded:
        m.embedding_vector = vector if vector is not None else _vec(0.5)
        m.embedding_model = "test-mock"
        m.embedding_dimension = EMBEDDING_DIMENSION
        m.embedded_at = timezone.now()
        m.save(update_fields=[
            "embedding_vector",
            "embedding_model",
            "embedding_dimension",
            "embedded_at",
            "updated_at",
        ])
    return m


def _talking_head_composition(
    ws, spokesperson, *, script: str, use_knowledge: bool = True,
    target_duration_seconds: int | None = None,
) -> tuple[Composition, CompositionStep]:
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=spokesperson,
        name="test-talking-head",
        template_kind="talking_head",
        mock_mode=False,
        operator_topic=script if use_knowledge else "",
        target_duration_seconds=target_duration_seconds,
    )
    step_params: dict = {
        "script": script,
        "use_knowledge": use_knowledge,
    }
    if target_duration_seconds:
        step_params["target_duration_seconds"] = target_duration_seconds
    step = CompositionStep.objects.create(
        composition=comp,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[],
        params=step_params,
    )
    return comp, step


def _script_result_stub(brief: str = "solo brief") -> ScriptResult:
    """A minimal ScriptResult that _maybe_synthesize_script can
    consume without hitting real synthesis."""
    return ScriptResult(
        brief=brief,
        chunk_ids=[],
        used_knowledge=False,
        model="test-mock",
        verification_status="trusted_passthrough",
        verification_warnings=[],
        writing_contract_version=0,
        memory_ids=[],
    )


# ============================================================
# Predicate — Patch solo + Rivet solo + cross-witness exclusion
# ============================================================


def test_patch_solo_whole_cast_memory_eligible():
    """Phase 7 item 1 — whole-cast memory retrieves under a Patch-only
    cast. The witness predicate treats empty ``witnessed_by`` as
    broadcast so the row is visible."""
    ws = _workspace("solo-wc@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    m = _memory(ws, universe, episode, comp, "whole", vector=_vec(1.0))
    got = retrieve_universe_memory(
        ws, universe, [patch], _query_vector=_vec(1.0),
    )
    assert [x.id for x in got] == [m.id]


def test_patch_solo_patch_only_memory_eligible():
    """Phase 7 item 2 — Patch-only witness memory retrieves under a
    Patch-only cast. Witness intersection with {Patch} is non-empty."""
    ws = _workspace("solo-p@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    m = _memory(
        ws, universe, episode, comp, "patch-only",
        witnessed_by=[patch], vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [patch], _query_vector=_vec(1.0),
    )
    assert [x.id for x in got] == [m.id]


def test_patch_solo_rivet_only_memory_excluded():
    """Phase 7 item 3 — Rivet-only witness memory is invisible to a
    Patch-only cast (zero witness overlap)."""
    ws = _workspace("solo-p-exc@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    _memory(
        ws, universe, episode, comp, "rivet-only",
        witnessed_by=[rivet], vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [patch], _query_vector=_vec(1.0),
    )
    assert got == []


def test_rivet_solo_rivet_only_memory_eligible():
    """Phase 7 item 4 — Rivet-only witness memory retrieves under a
    Rivet-only cast (mirror of item 2)."""
    ws = _workspace("solo-r@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    m = _memory(
        ws, universe, episode, comp, "rivet-only",
        witnessed_by=[rivet], vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [rivet], _query_vector=_vec(1.0),
    )
    assert [x.id for x in got] == [m.id]


def test_rivet_solo_patch_only_memory_excluded():
    """Phase 7 item 5 — Patch-only memory invisible to a Rivet-only
    cast (already covered symmetrically in
    ``test_retrieval_universe_memory.test_narrowed_witness_excluded_when_no_overlap``;
    duplicated here so the solo-cast contract is asserted next to
    the wiring)."""
    ws = _workspace("solo-r-exc@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    _memory(
        ws, universe, episode, comp, "patch-only",
        witnessed_by=[patch], vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [rivet], _query_vector=_vec(1.0),
    )
    assert got == []


def test_solo_cast_cross_universe_excluded():
    """Phase 7 item 6 — Universe isolation preserved for solo cast.
    Same guard the dialogue path relies on."""
    ws = _workspace("solo-cu@t")
    u1 = Universe.objects.create(workspace=ws, name="workshop")
    u2 = Universe.objects.create(workspace=ws, name="bakery")
    patch1, _ = _cast(ws, u1)
    baker = Teammate.objects.create(
        workspace=ws, universe=u2, name="Baker",
        runway_avatar_id="av-b", portrait_path="https://b",
        business_brief="bakes",
    )
    yeasty = Teammate.objects.create(
        workspace=ws, universe=u2, name="Yeasty",
        runway_avatar_id="av-y", portrait_path="https://y",
        business_brief="rises",
    )
    ep2, comp2 = _episode_with_composition(ws, u2, [baker, yeasty])
    _memory(ws, u2, ep2, comp2, "u2 mem", vector=_vec(1.0))
    got = retrieve_universe_memory(
        ws, u1, [patch1], _query_vector=_vec(1.0),
    )
    assert got == []


# ============================================================
# Wiring — the talking_head primitive calls retrieve_universe_memory
# with the right args and threads memory_rows into synthesis.
# ============================================================


def test_universe_scoped_talking_head_invokes_memory_retrieval():
    """avatar_speech primitive fires the shared predicate exactly
    once with cast=[spokesperson] and top_k=1 when the spokesperson
    has a Universe."""
    ws = _workspace("wire-fires@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, _rivet = _cast(ws, universe)
    comp, step = _talking_head_composition(
        ws, patch, script="a topic", use_knowledge=True,
    )
    stub_result = _script_result_stub()

    with mock_patch(
        "apps.embeddings.retrieval.retrieve_universe_memory",
        return_value=[],
    ) as fake_mem, mock_patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
        return_value=stub_result,
    ):
        _maybe_synthesize_script(step, comp)

    assert fake_mem.call_count == 1
    args, kwargs = fake_mem.call_args
    assert args[0] is ws
    assert args[1] is universe
    assert list(args[2]) == [patch]
    query_val = args[3] if len(args) >= 4 else kwargs.get("query")
    assert query_val == "a topic"
    top_k_val = args[4] if len(args) >= 5 else kwargs.get("top_k")
    assert top_k_val == 1


def test_universe_less_talking_head_skips_memory_retrieval():
    """Legacy (universe-less) spokespeople do NOT call the retrieval
    predicate. Preserves pre-§10 talking_head shape byte-for-byte."""
    ws = _workspace("wire-legacy@t")
    patch, _rivet = _cast(ws, universe=None)
    comp, step = _talking_head_composition(
        ws, patch, script="a topic", use_knowledge=True,
    )
    stub_result = _script_result_stub()

    with mock_patch(
        "apps.embeddings.retrieval.retrieve_universe_memory",
        return_value=[],
    ) as fake_mem, mock_patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
        return_value=stub_result,
    ):
        _maybe_synthesize_script(step, comp)

    assert fake_mem.call_count == 0


def test_use_knowledge_false_skips_memory_retrieval():
    """When ``use_knowledge=False`` the primitive short-circuits on
    trusted-passthrough BEFORE any retrieval — mirrors dialogue-lane
    ``use_knowledge=False`` behaviour for all three lanes."""
    ws = _workspace("wire-off@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    comp, step = _talking_head_composition(
        ws, patch, script="a topic", use_knowledge=False,
    )

    with mock_patch(
        "apps.embeddings.retrieval.retrieve_universe_memory",
        return_value=[],
    ) as fake_mem:
        brief, chunk_ids, warnings, status, contract_v = (
            _maybe_synthesize_script(step, comp)
        )

    assert fake_mem.call_count == 0
    assert brief == "a topic"
    assert chunk_ids == []
    assert status == "trusted_passthrough"


def test_retrieved_memory_persists_to_composition_memory_ids():
    """Phase 7 item 9 — Composition.memory_ids receives selected
    NarrativeMemory UUIDs via the recipe-agnostic JSONField the
    dialogue path writes to."""
    ws = _workspace("wire-persist@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    comp, step = _talking_head_composition(
        ws, patch, script="a topic", use_knowledge=True,
    )
    fake_memory = SimpleNamespace(id="mem-abc", body="past event")
    stub_result = ScriptResult(
        brief="solo brief",
        chunk_ids=[],
        used_knowledge=True,
        model="test-mock",
        verification_status="verified",
        verification_warnings=[],
        writing_contract_version=1,
        memory_ids=[str(fake_memory.id)],
    )

    with mock_patch(
        "apps.embeddings.retrieval.retrieve_universe_memory",
        return_value=[fake_memory],
    ), mock_patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
        return_value=stub_result,
    ) as fake_build:
        _maybe_synthesize_script(step, comp)

    # build_render_brief received the retrieval output
    _, brief_kwargs = fake_build.call_args
    assert list(brief_kwargs.get("memory_rows") or []) == [fake_memory]

    comp.refresh_from_db()
    assert comp.memory_ids == [str(fake_memory.id)]


def test_composition_memory_ids_untouched_when_pool_empty():
    """Empty retrieval leaves ``Composition.memory_ids`` at default
    ``[]`` — no bogus provenance is written when the pool is empty."""
    ws = _workspace("wire-empty@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    comp, step = _talking_head_composition(
        ws, patch, script="a topic", use_knowledge=True,
    )
    stub_result = _script_result_stub()

    with mock_patch(
        "apps.embeddings.retrieval.retrieve_universe_memory",
        return_value=[],
    ), mock_patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
        return_value=stub_result,
    ):
        _maybe_synthesize_script(step, comp)

    comp.refresh_from_db()
    assert comp.memory_ids == []


# ============================================================
# Prompt block — memory_rows land in §1 Factual Basis
# ============================================================


def test_memory_block_lands_in_factual_basis_with_past_events_framing():
    """The dedicated MEMORY block emits under §1 Factual Basis with
    the same past-events / canon-wins framing the dialogue lane uses,
    so both lanes share one operator mental model."""
    ws = _workspace("prompt-block@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, _rivet = _cast(ws, universe)
    fake_memory = SimpleNamespace(
        id="MEMORY_MARKER_ID",
        body="THE_PRINTER_INCIDENT_MEMORY_MARKER",
    )
    section = _build_factual_basis_section(
        patch, chunks=[], memory_rows=[fake_memory],
    )
    assert "MEMORY_MARKER_ID" in section
    assert "THE_PRINTER_INCIDENT_MEMORY_MARKER" in section
    assert "past events in this Universe" in section
    assert "static canon wins on conflict" in section


def test_empty_memory_rows_emits_no_memory_block():
    """Absence of memory_rows leaves §1 unchanged from the pre-§10
    shape — no dangling MEMORY header, no whitespace regression."""
    ws = _workspace("prompt-empty@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, _rivet = _cast(ws, universe)
    section = _build_factual_basis_section(patch, chunks=[])
    assert "MEMORY" not in section
    assert "past events" not in section


# ============================================================
# build_render_brief — memory-only path still calls LLM
# ============================================================


def test_build_render_brief_calls_llm_when_only_memory_present():
    """K2 chunks may be empty but a non-empty memory_rows must NOT
    short-circuit onto trusted_passthrough — the memory block would
    silently be dropped. Instead the LLM is invoked so the memory
    body actually informs the script."""
    ws = _workspace("brief-mem-only@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    fake_memory = SimpleNamespace(id="m-1", body="memory body")

    fake_openai_resp = MagicMock()
    fake_openai_resp.output_text = "generated brief mentioning memory"
    fake_openai_resp.usage = MagicMock(input_tokens=10, output_tokens=20)
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_openai_resp

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "character_os.script_synthesis.retrieve_for_teammate",
             return_value=[],
         ):
        result = build_render_brief(
            patch, "topic", memory_rows=[fake_memory],
        )

    assert fake_client.responses.create.call_count == 1
    # memory_ids threaded through to the result even on the
    # non-degraded LLM path.
    assert result.memory_ids == ["m-1"]
    # LLM output landed as the brief.
    assert "generated brief" in result.brief


def test_build_render_brief_memory_ids_default_empty_when_no_memory():
    """Backwards-compat: the pre-§10 default (no memory_rows) leaves
    ``ScriptResult.memory_ids`` at its default empty list."""
    ws = _workspace("brief-nomem@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)

    with mock_patch(
        "character_os.script_synthesis.retrieve_for_teammate",
        return_value=[],
    ), mock_patch(
        "character_os.script_synthesis._is_force_mock",
        return_value=True,
    ):
        result = build_render_brief(patch, "topic")

    assert result.memory_ids == []
