"""SESSION 270 — audience-aware character performance research plumbing.

Pins the smallest transient slice: optional ``audience_hint`` kwarg
threaded from ``avatar_speech`` step params through
``synthesize_with_duration_gate`` / ``build_render_brief`` into the
§5 Task HARD CONSTRAINTS block of the K6 system+user prompt, for
the ``solo_scene`` lane ONLY.

Contract this suite protects:

1. ``audience_hint=None`` (or omitted, whitespace-only, absent from
   every resolver source) → prompt is byte-stable versus the
   pre-SESSION-270 shape. No AUDIENCE DIRECTIVE marker; §5 Hard
   Constraints block only emitted when opener/corrective_hint were
   present.
2. Non-empty ``audience_hint`` → reaches §5 Task HARD CONSTRAINTS
   as an AUDIENCE DIRECTIVE block, and inherits the existing
   precedence contract (Character Voice + Writing Contract can be
   overridden; Factual Basis + Brand Voice prohibitions can NOT).
3. The audience directive text does NOT leak into §1 Factual Basis,
   §2 Character Voice, §3 Brand Voice, or the narrative-memory
   sub-block.
4. ``WRITING_CONTRACT_VERSION`` is unchanged — this slice deliberately
   avoids a v6 bump so audience-conditional writing contracts stay
   an open architectural question, not a shipped commitment.
5. The primitive-layer resolver honours precedence
   step.params > settings > env, and treats whitespace-only strings
   as absent (returns ``None`` so callers pass ``None`` to synthesis
   and the prompt stays byte-stable).
6. ``dialogue_synthesis`` remains untouched — dialogue_scene audience
   plumbing is deliberately out of scope for this slice.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os import dialogue_synthesis
from character_os.script_synthesis import (
    _assemble_task_message,
    build_render_brief,
)
from character_os.duration_contract import synthesize_with_duration_gate
from character_os.writing_contract import WRITING_CONTRACT_VERSION
from apps.compositions.primitives.avatar_speech import (
    _SOLO_AUDIENCE_HINT_ENV,
    _SOLO_AUDIENCE_HINT_SETTING,
    _resolve_solo_audience_hint,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# The exact experimental directive from the SESSION 270 authorisation
# brief. Test text pins this so drift is loud.
_EXPERIMENT_HINT = (
    "AUDIENCE: children around 8-10 years old. Adapt register, "
    "vocabulary accessibility, explanation style, analogy choice, "
    "and assumed background knowledge for this audience. Preserve "
    "character identity, intelligence, personality, humor, factual "
    "grounding, Universe canon, NarrativeMemory semantics, and "
    "Episode intent. Communicate WITH the audience, do not talk "
    "DOWN to them."
)


# ---- 1. audience_hint absent → byte-stable prompt ----------------


def test_assemble_task_message_absent_hint_is_byte_stable_baseline():
    """Pre-SESSION-270 shape: TOPIC + closing 'Write the spokesperson…'
    line, with NO Hard Constraints block when no opener /
    corrective_hint / audience_hint is supplied."""
    prompt = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
    )
    assert "SECTION 5 — TASK" in prompt
    assert "TOPIC:" in prompt
    assert "HARD CONSTRAINTS" not in prompt
    assert "AUDIENCE DIRECTIVE" not in prompt


def test_assemble_task_message_explicit_none_matches_omission():
    """``audience_hint=None`` must be indistinguishable from omitting
    the kwarg entirely — the two calls MUST produce identical bytes."""
    without = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
    )
    with_none = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
        audience_hint=None,
    )
    assert without == with_none


def test_assemble_task_message_whitespace_only_hint_ignored():
    """Whitespace-only string must be treated as absent — the LLM
    should not see an empty AUDIENCE DIRECTIVE marker."""
    baseline = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
    )
    for hint in ("", "   ", "\n\t  \n"):
        prompt = _assemble_task_message(
            operator_prompt="Patch does research on AI Agents",
            audience_hint=hint,
        )
        assert prompt == baseline, f"whitespace hint {hint!r} altered prompt"


# ---- 2. Non-empty hint reaches §5 Hard Constraints ---------------


def test_assemble_task_message_hint_emitted_under_hard_constraints():
    prompt = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
        audience_hint=_EXPERIMENT_HINT,
    )
    # Section header appears.
    assert "HARD CONSTRAINTS" in prompt
    # Named block header for the audience directive.
    assert "AUDIENCE DIRECTIVE" in prompt
    # The verbatim hint text is present.
    assert _EXPERIMENT_HINT in prompt
    # Ordering: HARD CONSTRAINTS block sits AFTER the TOPIC block.
    assert prompt.index("TOPIC:") < prompt.index("HARD CONSTRAINTS")
    # AUDIENCE DIRECTIVE is INSIDE the Hard Constraints block.
    assert prompt.index("HARD CONSTRAINTS") < prompt.index("AUDIENCE DIRECTIVE")


def test_assemble_task_message_hint_inherits_hard_constraint_precedence():
    """The HARD CONSTRAINTS framing text is the load-bearing precedence
    contract — it explicitly authorises overriding Character Voice +
    Writing Contract preferences but NOT Factual Basis or Brand Voice
    prohibitions. The audience directive lives inside that framing,
    so it inherits the same contract by construction."""
    prompt = _assemble_task_message(
        operator_prompt="Patch does research on AI Agents",
        audience_hint=_EXPERIMENT_HINT,
    )
    hard_block_start = prompt.index("HARD CONSTRAINTS")
    hard_block_frame = prompt[hard_block_start:hard_block_start + 400]
    assert "override Character Voice" in hard_block_frame
    assert "Writing Contract preferences" in hard_block_frame
    # ``do NOT override Factual Basis or Brand Voice prohibitions``
    # is the load-bearing precedence clause the audience directive
    # inherits by living inside this block.
    assert "do NOT override Factual Basis" in hard_block_frame
    assert "Brand Voice prohibitions" in hard_block_frame


def test_assemble_task_message_hint_coexists_with_opener_and_corrective():
    """All three per-render Hard Constraints must be able to coexist
    without corrupting each other."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        opener="Here is the opener.",
        corrective_hint="Trim the tail.",
        audience_hint=_EXPERIMENT_HINT,
    )
    assert "PINNED OPENER" in prompt
    assert "CORRECTIVE HINT" in prompt
    assert "AUDIENCE DIRECTIVE" in prompt
    assert "Here is the opener." in prompt
    assert "Trim the tail." in prompt
    assert _EXPERIMENT_HINT in prompt


# ---- 3. Hint MUST NOT leak into non-Hard-Constraint sections -----


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate_patch_like(ws: Workspace) -> Teammate:
    """A stand-in Teammate. This test is prompt-shape only — the
    fields exercise every prompt section that could theoretically
    absorb an audience directive by accident."""
    return Teammate.objects.create(
        workspace=ws,
        name="Patch",
        business_brief="Runs a small maker workshop.",
        personality="Curious impulsive builder. Warm dry wit.",
        character_point_of_view="Notices weird bugs first.",
        who_you_help="Fellow tinkerers.",
        what_you_sell="Custom small hardware.",
        always_emphasize="Show your work.",
        never_say="perfect the first try",
        desired_feeling="curious",
        voice_energy="medium",
        voice_humor="dry",
        voice_directness="direct",
    )


class _FakeChunk:
    def __init__(self, text: str, doc_id: str = "doc-1"):
        self.chunk_text = text
        self.document_id = doc_id
        self.id = "chunk-1"


class _FakeMemory:
    def __init__(self, body: str, mid: str):
        self.body = body
        self.id = mid


def test_build_render_brief_hint_does_not_leak_via_synthesis_path(monkeypatch):
    """End-to-end via ``build_render_brief`` with the OpenAI call
    stubbed: capture the assembled prompt and assert the audience
    directive only appears inside §5 HARD CONSTRAINTS — never in §1
    Factual Basis, §2 Character Voice, §3 Brand Voice, or the
    NarrativeMemory block."""
    ws = _workspace("s270-noleak@t")
    tm = _teammate_patch_like(ws)

    captured_input: dict[str, str] = {}

    def _fake_retrieve(spokesperson, *, query, top_k):
        return [_FakeChunk("Retrieved workshop-agent chunk.")]

    class _FakeUsage:
        input_tokens = 10
        output_tokens = 20

    class _FakeResponse:
        output_text = "synthesised script body"
        usage = _FakeUsage()

    class _FakeClient:
        class responses:
            @staticmethod
            def create(**kwargs):
                captured_input["input"] = kwargs["input"]
                return _FakeResponse()

    def _fake_openai(api_key):
        return _FakeClient()

    memory_row = _FakeMemory("Patch remembers a prior workshop moment.", "mem-1")

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(
        "character_os.script_synthesis.retrieve_for_teammate",
        _fake_retrieve,
    )
    monkeypatch.setattr(
        "openai.OpenAI",
        _fake_openai,
    )

    build_render_brief(
        tm,
        "Patch does research on AI Agents",
        target_shape="solo_scene",
        memory_rows=[memory_row],
        audience_hint=_EXPERIMENT_HINT,
    )

    assembled = captured_input["input"]

    # Section anchors present.
    assert "SECTION 1 — FACTUAL BASIS" in assembled
    assert "SECTION 2 — CHARACTER VOICE" in assembled
    assert "SECTION 3 — BRAND VOICE" in assembled
    assert "SECTION 5 — TASK" in assembled
    assert "AUDIENCE DIRECTIVE" in assembled
    assert _EXPERIMENT_HINT in assembled

    # The directive text and the AUDIENCE DIRECTIVE marker sit
    # AFTER the §5 header and before any post-§5 content — i.e.
    # inside the Hard-Constraints region of §5.
    section5_start = assembled.index("SECTION 5 — TASK")
    directive_pos = assembled.index("AUDIENCE DIRECTIVE")
    assert directive_pos > section5_start

    # The directive text itself does not appear before §5.
    assert assembled.index(_EXPERIMENT_HINT) > section5_start

    # Non-§5 sections must not contain the audience-hint fingerprint
    # substrings. Slice everything BEFORE §5 and search there.
    pre_section5 = assembled[:section5_start]
    assert "AUDIENCE DIRECTIVE" not in pre_section5
    assert "children around 8-10" not in pre_section5
    assert "Communicate WITH the audience" not in pre_section5
    # Sanity: memory block sits pre-§5 (inside §1 Factual Basis).
    assert "EPISODE / NARRATIVE MEMORY" in pre_section5
    assert "Patch remembers a prior workshop moment." in pre_section5


# ---- 4. Writing contract version unchanged -----------------------


def test_writing_contract_version_unchanged_by_this_slice():
    """SESSION 270 slice must NOT bump the writing contract version.
    Audience-conditional writing contracts remain an open
    architectural question, deliberately unshipped."""
    assert WRITING_CONTRACT_VERSION == 5


# ---- 5. Primitive-layer resolver precedence ----------------------


def _fake_step(params: dict | None):
    step = MagicMock()
    step.params = params or {}
    return step


def test_resolve_audience_hint_returns_none_when_all_sources_absent(
    monkeypatch,
):
    monkeypatch.delenv(_SOLO_AUDIENCE_HINT_ENV, raising=False)
    with override_settings():
        # Ensure the setting attribute is absent for the duration of
        # the check — override_settings with no kwargs leaves any
        # previously set attribute in place, so delattr explicitly.
        from django.conf import settings as _s
        if hasattr(_s, _SOLO_AUDIENCE_HINT_SETTING):
            delattr(_s, _SOLO_AUDIENCE_HINT_SETTING)
        assert _resolve_solo_audience_hint(_fake_step(None)) is None


def test_resolve_audience_hint_treats_whitespace_as_absent(monkeypatch):
    monkeypatch.setenv(_SOLO_AUDIENCE_HINT_ENV, "   \n\t  ")
    with override_settings(**{_SOLO_AUDIENCE_HINT_SETTING: "   "}):
        assert (
            _resolve_solo_audience_hint(_fake_step({"audience_hint": "  "}))
            is None
        )


def test_resolve_audience_hint_step_params_beat_settings_and_env(
    monkeypatch,
):
    monkeypatch.setenv(_SOLO_AUDIENCE_HINT_ENV, "env-hint")
    with override_settings(**{_SOLO_AUDIENCE_HINT_SETTING: "settings-hint"}):
        got = _resolve_solo_audience_hint(
            _fake_step({"audience_hint": "params-hint"})
        )
        assert got == "params-hint"


def test_resolve_audience_hint_settings_beat_env(monkeypatch):
    monkeypatch.setenv(_SOLO_AUDIENCE_HINT_ENV, "env-hint")
    with override_settings(**{_SOLO_AUDIENCE_HINT_SETTING: "settings-hint"}):
        got = _resolve_solo_audience_hint(_fake_step(None))
        assert got == "settings-hint"


def test_resolve_audience_hint_env_used_when_only_source(monkeypatch):
    monkeypatch.setenv(_SOLO_AUDIENCE_HINT_ENV, "env-hint-content")
    got = _resolve_solo_audience_hint(_fake_step(None))
    assert got == "env-hint-content"


# ---- 6. dialogue_synthesis remains untouched ---------------------


def test_dialogue_synthesis_has_no_audience_hint_kwarg():
    """Solo-only scope. Any drift into dialogue_synthesis should
    happen through a deliberate SESSION 270+ slice, not by accident."""
    sig = inspect.signature(dialogue_synthesis.synthesize_dialogue)
    assert "audience_hint" not in sig.parameters
    src = inspect.getsource(dialogue_synthesis)
    assert "audience_hint" not in src
    assert "AUDIENCE DIRECTIVE" not in src


def test_dialogue_task_section_does_not_emit_audience_directive():
    """Belt-and-braces — even if a future slice adds audience_hint
    to dialogue_synthesis, the current implementation must produce
    no AUDIENCE DIRECTIVE marker."""
    text = dialogue_synthesis._build_task_section(
        topic="Any topic",
        target_duration_seconds=90,
        alias_to_teammate={},
        opener=None,
        corrective_hint=None,
    )
    assert "AUDIENCE DIRECTIVE" not in text


# ---- 7. Public API surface --------------------------------------


def test_build_render_brief_signature_has_audience_hint_kwarg():
    sig = inspect.signature(build_render_brief)
    assert "audience_hint" in sig.parameters
    param = sig.parameters["audience_hint"]
    assert param.default is None
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


def test_synthesize_with_duration_gate_signature_has_audience_hint_kwarg():
    sig = inspect.signature(synthesize_with_duration_gate)
    assert "audience_hint" in sig.parameters
    param = sig.parameters["audience_hint"]
    assert param.default is None
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
