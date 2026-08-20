"""SESSION 271 Q-270-15c — corrective-revision experiment plumbing.

Pins the smallest transient slice: optional ``previous_draft`` kwarg
threaded through ``build_render_brief`` / ``_call_responses_api`` /
``_assemble_task_message``, plus an env-gated branch inside
``synthesize_with_duration_gate`` that swaps the canonical
:func:`_expansion_hint` for :func:`_experimental_expansion_revision_hint`
AND passes Draft A back to the LLM on the expansion retry.

Contract this suite protects (10 invariants — see SESSION 271 §32.3
+ the SESSION 271 Q-270-15c authorisation brief):

1. Experiment OFF (env var unset / whitespace-only) → canonical
   behaviour is byte-behavior-equivalent to pre-SESSION-271 shape.
2. Experiment OFF → corrective retry does NOT receive Draft A;
   ``previous_draft`` kwarg to build_render_brief is either absent
   or explicitly ``None``.
3. Experiment ON → first pass remains unchanged (no previous_draft,
   canonical corrective_hint absent).
4. Experiment ON → expansion corrective pass DOES receive Draft A
   as ``previous_draft`` and uses the experimental revision hint.
5. Experiment ON → Draft A appears ONLY in the corrective prompt,
   never in the first-pass prompt.
6. Experiment ON → audience_hint still reaches BOTH passes
   byte-identically (Q-270-15c does not weaken SESSION 270 invariants).
7. Experiment ON → the revision instruction ("REVISE THE PREVIOUS
   DRAFT" + PREVIOUS DRAFT TO REVISE label) is present only on
   the corrective call.
8. Experiment ON → previous_draft text is emitted only inside §5
   Task HARD CONSTRAINTS; never leaks into §1 Factual Basis,
   §2 Character Voice, §3 Brand Voice, or the NarrativeMemory block.
9. Experiment ON → compression path stays canonical (expansion-only
   scope); no previous_draft on the compression retry.
10. Experiment ON → still exactly one bounded corrective retry
    (attempt_count capped at 2; no extra LLM calls).

Also pinned:

- ``WRITING_CONTRACT_VERSION`` unchanged by this slice.
- Dialogue synthesis untouched (Q-270-15c scopes to duration_contract
  / solo + long-form only).
"""
from __future__ import annotations

import inspect

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os import dialogue_synthesis
from character_os.duration_contract import (
    _CORRECTIVE_REVISION_ENV,
    _corrective_revision_experiment_active,
    synthesize_with_duration_gate,
)
from character_os.script_synthesis import (
    ScriptResult,
    _assemble_task_message,
    build_render_brief,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION
from unittest.mock import patch

User = get_user_model()

pytestmark = pytest.mark.django_db


# Exact SESSION 270 §13.24 nontechnical-adult directive — the specimen
# Q-270-15c is designed to test against.
_Q270_15c_AUDIENCE_HINT = (
    "AUDIENCE: general adults with no technical background who are "
    "new to AI agents."
)

# A representative first-pass excerpt drawn from the SESSION 270
# frozen `c3ff972d` sidecar. Verbatim so the test surface pins the
# exact substring the experiment would carry back to the LLM.
_DRAFT_A_SPECIMEN = (
    "An AI agent is not just a chatbot with a little hat on.\n\n"
    "I'm digging into what actually makes one an agent, and the "
    "useful answer seems to be: it can do more than give you one "
    "response.\n\n"
    "It might choose tools, search for information, read documents, "
    "write things down, make decisions, keep track of what happened, "
    "and handle a task across multiple steps."
)


# ---- fixtures -----------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(ws: Workspace, *, name: str = "Patch") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief="Runs a small maker workshop.",
        runway_avatar_id="fake-avatar",
    )


def _fake_script_result(text: str) -> ScriptResult:
    return ScriptResult(
        brief=text,
        chunk_ids=["c1"],
        used_knowledge=True,
        verification_status="verified",
        writing_contract_version=WRITING_CONTRACT_VERSION,
    )


# ---- 1. Env-gate helper --------------------------------------------


def test_env_var_name_stable():
    """Pin the env-var identifier so drift is loud and dogfood
    instructions do not silently break."""
    assert _CORRECTIVE_REVISION_ENV == (
        "CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT"
    )


def test_experiment_inactive_by_default(monkeypatch):
    """Default local shell must NOT have the experiment active."""
    monkeypatch.delenv(_CORRECTIVE_REVISION_ENV, raising=False)
    assert _corrective_revision_experiment_active() is False


def test_experiment_whitespace_only_env_treated_as_inactive(monkeypatch):
    """Same discipline as SESSION 270 audience-hint resolver —
    whitespace-only values are unset, so operators can toggle off
    with ``export CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=``."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "   ")
    assert _corrective_revision_experiment_active() is False


def test_experiment_active_when_env_set(monkeypatch):
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    assert _corrective_revision_experiment_active() is True


# ---- 2. _assemble_task_message plumbing ----------------------------


def test_assemble_task_message_no_previous_draft_block_by_default():
    """Absent / None / whitespace-only previous_draft → no
    PREVIOUS DRAFT TO REVISE block appears in the assembled §5."""
    prompt = _assemble_task_message(operator_prompt="Topic")
    assert "PREVIOUS DRAFT TO REVISE" not in prompt

    prompt2 = _assemble_task_message(
        operator_prompt="Topic",
        previous_draft=None,
    )
    assert "PREVIOUS DRAFT TO REVISE" not in prompt2

    prompt3 = _assemble_task_message(
        operator_prompt="Topic",
        previous_draft="   ",
    )
    assert "PREVIOUS DRAFT TO REVISE" not in prompt3


def test_assemble_task_message_previous_draft_emits_labelled_block():
    """Non-empty previous_draft → labelled block inside §5 Hard
    Constraints, verbatim draft text embedded, framed as a source
    draft NOT a truth authority."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        previous_draft=_DRAFT_A_SPECIMEN,
    )
    assert "SECTION 5 — TASK" in prompt
    assert "PREVIOUS DRAFT TO REVISE" in prompt
    assert _DRAFT_A_SPECIMEN in prompt
    # Framing text present — Draft A is NOT a factual authority.
    assert "Factual Basis still governs truth" in prompt
    # Sits inside the HARD CONSTRAINTS block preface.
    assert "HARD CONSTRAINTS" in prompt


def test_assemble_task_message_previous_draft_coexists_with_all_hard_constraints():
    """Draft A must not corrupt opener / corrective_hint / audience_hint."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        opener="Here is the opener.",
        corrective_hint="Expand secondary detail.",
        audience_hint=_Q270_15c_AUDIENCE_HINT,
        previous_draft=_DRAFT_A_SPECIMEN,
    )
    assert "PINNED OPENER" in prompt
    assert "PREVIOUS DRAFT TO REVISE" in prompt
    assert "CORRECTIVE HINT" in prompt
    assert "AUDIENCE DIRECTIVE" in prompt
    assert "Here is the opener." in prompt
    assert _DRAFT_A_SPECIMEN in prompt
    assert "Expand secondary detail." in prompt
    assert _Q270_15c_AUDIENCE_HINT in prompt


def test_build_render_brief_signature_has_previous_draft_kwarg():
    """Keyword-only, default None, str | None type — same discipline
    as audience_hint (SESSION 270)."""
    sig = inspect.signature(build_render_brief)
    assert "previous_draft" in sig.parameters
    param = sig.parameters["previous_draft"]
    assert param.default is None
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


def test_synthesize_with_duration_gate_signature_unchanged():
    """Experiment is env-gated inside the function body; the public
    signature deliberately does NOT gain a ``previous_draft`` kwarg
    so no caller can accidentally activate the experiment via
    step.params."""
    sig = inspect.signature(synthesize_with_duration_gate)
    assert "previous_draft" not in sig.parameters


# ---- 3. Experiment OFF → canonical behaviour byte-stable -----------


def test_experiment_off_expansion_retry_omits_previous_draft(monkeypatch):
    """The canonical path — SESSION 270-era invariant. First pass
    too short → expansion retry → build_render_brief called twice,
    NEITHER call carries previous_draft."""
    monkeypatch.delenv(_CORRECTIVE_REVISION_ENV, raising=False)
    ws = _workspace("q270-15c-off-exp@t")
    tm = _teammate(ws)
    short = "x" * 400
    accepted = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short),
            _fake_script_result(accepted),
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == accepted
    assert fake_brb.call_count == 2

    for i, call in enumerate(fake_brb.call_args_list):
        assert call.kwargs.get("previous_draft") is None, (
            f"Call {i} (canonical) received previous_draft; "
            f"experiment env unset — this violates Q-270-15c contract"
        )

    # Canonical expansion hint fingerprint retained on the retry.
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert retry_kwargs.get("corrective_hint")
    assert "REWRITE THE SAME NARRATIVE" in retry_kwargs["corrective_hint"]
    assert "REVISE THE PREVIOUS DRAFT" not in retry_kwargs["corrective_hint"]


def test_experiment_off_first_pass_never_receives_previous_draft(monkeypatch):
    """First pass never carries previous_draft regardless of the
    duration outcome. Canonical path — no retry fires."""
    monkeypatch.delenv(_CORRECTIVE_REVISION_ENV, raising=False)
    ws = _workspace("q270-15c-off-first@t")
    tm = _teammate(ws)
    perfect = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result(perfect),
    ) as fake_brb:
        synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert fake_brb.call_count == 1
    assert fake_brb.call_args_list[0].kwargs.get("previous_draft") is None


# ---- 4. Experiment ON — expansion path invariants ------------------


def test_experiment_on_expansion_retry_receives_previous_draft(monkeypatch):
    """Core invariant. Env ON + expansion retry → the SECOND
    build_render_brief call carries ``previous_draft=<first-pass-text>``
    and the experimental revision hint replaces the canonical
    expansion hint."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    ws = _workspace("q270-15c-on-exp@t")
    tm = _teammate(ws)
    short = "x" * 400
    accepted = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short),
            _fake_script_result(accepted),
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == accepted
    assert fake_brb.call_count == 2

    # First call: canonical shape, no previous_draft.
    assert fake_brb.call_args_list[0].kwargs.get("previous_draft") is None
    assert fake_brb.call_args_list[0].kwargs.get("corrective_hint") is None

    # Corrective call: Draft A byte-identical to first-pass output.
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert retry_kwargs.get("previous_draft") == short, (
        "Corrective retry must carry the exact first-pass brief text "
        "as previous_draft when the Q-270-15c experiment is ON"
    )
    # Experimental hint fingerprint present, canonical fingerprint absent.
    assert retry_kwargs.get("corrective_hint")
    assert "REVISE THE PREVIOUS DRAFT" in retry_kwargs["corrective_hint"]
    assert "REWRITE THE SAME NARRATIVE" not in retry_kwargs["corrective_hint"]


def test_experiment_on_first_pass_no_previous_draft(monkeypatch):
    """Env ON but first pass converges within tolerance → still no
    retry, no previous_draft, no experimental hint. Draft A only
    reaches the corrective call."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    ws = _workspace("q270-15c-on-first@t")
    tm = _teammate(ws)
    perfect = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result(perfect),
    ) as fake_brb:
        synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert fake_brb.call_count == 1
    call = fake_brb.call_args_list[0]
    assert call.kwargs.get("previous_draft") is None
    assert call.kwargs.get("corrective_hint") is None


def test_experiment_on_audience_hint_reaches_both_passes(monkeypatch):
    """Q-270-15c must not weaken the SESSION 270 audience-hint
    closure invariant: audience_hint reaches both first-pass and
    corrective-pass byte-identically. The experiment adds
    previous_draft on the retry; it must not drop audience_hint."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    ws = _workspace("q270-15c-audience-parity@t")
    tm = _teammate(ws)
    short = "x" * 400
    accepted = "x" * 1350

    from character_os.duration_contract import synthesize_with_duration_gate as sgate

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short),
            _fake_script_result(accepted),
        ],
    ) as fake_brb:
        sgate(
            tm, "topic",
            target_duration_seconds=90,
            audience_hint=_Q270_15c_AUDIENCE_HINT,
        )
    assert fake_brb.call_count == 2
    first_ah = fake_brb.call_args_list[0].kwargs.get("audience_hint")
    second_ah = fake_brb.call_args_list[1].kwargs.get("audience_hint")
    assert first_ah == _Q270_15c_AUDIENCE_HINT
    assert second_ah == _Q270_15c_AUDIENCE_HINT
    assert first_ah == second_ah


def test_experiment_on_compression_path_stays_canonical(monkeypatch):
    """Q-270-15c scopes to expansion only. When the flag is ON but
    the first pass is TOO LONG (compression path), corrective
    behaviour must remain canonical: canonical compression hint,
    NO previous_draft."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    ws = _workspace("q270-15c-on-compress@t")
    tm = _teammate(ws)
    long_ = "x" * 1800  # over 1620 acceptance max, under 1900 cap
    accepted = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(long_),
            _fake_script_result(accepted),
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == accepted
    assert fake_brb.call_count == 2
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert retry_kwargs.get("previous_draft") is None, (
        "Compression retry must NOT carry previous_draft even when "
        "the experiment flag is ON — expansion-only scope"
    )
    # Canonical compression hint fingerprint present.
    assert "REWRITE THE SAME NARRATIVE" in retry_kwargs["corrective_hint"]
    assert "REVISE THE PREVIOUS DRAFT" not in retry_kwargs["corrective_hint"]


def test_experiment_on_still_bounded_to_one_corrective_retry(monkeypatch):
    """Retry policy remains one bounded pass. Q-270-15c does not
    introduce a third LLM call under any code path."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    ws = _workspace("q270-15c-bounded@t")
    tm = _teammate(ws)
    short_1 = "x" * 400   # too short
    short_2 = "x" * 500   # still too short — retry fails acceptance

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short_1),
            _fake_script_result(short_2),
        ],
    ) as fake_brb:
        from character_os.duration_contract import DurationContractError
        with pytest.raises(DurationContractError):
            synthesize_with_duration_gate(
                tm, "topic", target_duration_seconds=90,
            )
    # Exactly two calls — no third attempt even under the experiment.
    assert fake_brb.call_count == 2


# ---- 5. Prompt containment — Draft A only in §5 --------------------


class _FakeChunk:
    def __init__(self, text: str, doc_id: str = "doc-1"):
        self.chunk_text = text
        self.document_id = doc_id
        self.id = "chunk-1"


class _FakeMemory:
    def __init__(self, body: str, mid: str):
        self.body = body
        self.id = mid


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
            _FakeClient._captured = kwargs["input"]  # type: ignore[attr-defined]
            return _FakeResponse()


def _teammate_full(ws: Workspace) -> Teammate:
    """Populate every field that could theoretically absorb a
    previous_draft leak, matching the SESSION 270 no-leak test."""
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


def test_experiment_on_previous_draft_contained_to_section5(monkeypatch):
    """End-to-end through build_render_brief with the OpenAI call
    stubbed. Assert Draft A only appears inside §5 HARD CONSTRAINTS
    — never in §1 Factual Basis, §2 Character Voice, §3 Brand Voice,
    or the NarrativeMemory block. Belt-and-braces mirroring the
    SESSION 270 audience-hint no-leak test."""
    monkeypatch.setenv(_CORRECTIVE_REVISION_ENV, "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    ws = _workspace("q270-15c-no-leak@t")
    tm = _teammate_full(ws)

    def _fake_retrieve(spokesperson, *, query, top_k):
        return [_FakeChunk("Retrieved workshop-agent chunk.")]

    def _fake_openai(api_key):
        return _FakeClient()

    monkeypatch.setattr(
        "character_os.script_synthesis.retrieve_for_teammate",
        _fake_retrieve,
    )
    monkeypatch.setattr("openai.OpenAI", _fake_openai)

    memory_row = _FakeMemory(
        "Patch remembers a prior workshop moment.", "mem-1",
    )

    build_render_brief(
        tm,
        "Patch does research on AI Agents",
        target_shape="solo_scene",
        memory_rows=[memory_row],
        audience_hint=_Q270_15c_AUDIENCE_HINT,
        previous_draft=_DRAFT_A_SPECIMEN,
        corrective_hint="Extend to the length target.",
    )

    assembled = _FakeClient._captured  # type: ignore[attr-defined]

    # Section anchors present.
    assert "SECTION 1 — FACTUAL BASIS" in assembled
    assert "SECTION 2 — CHARACTER VOICE" in assembled
    assert "SECTION 3 — BRAND VOICE" in assembled
    assert "SECTION 5 — TASK" in assembled
    assert "PREVIOUS DRAFT TO REVISE" in assembled
    assert _DRAFT_A_SPECIMEN in assembled

    # Draft A + its label must sit AFTER §5 header.
    section5_start = assembled.index("SECTION 5 — TASK")
    label_pos = assembled.index("PREVIOUS DRAFT TO REVISE")
    assert label_pos > section5_start
    assert assembled.index(_DRAFT_A_SPECIMEN) > section5_start

    # Nothing about Draft A or its label appears before §5.
    pre_section5 = assembled[:section5_start]
    assert "PREVIOUS DRAFT TO REVISE" not in pre_section5
    # Fingerprint substrings from the specimen text.
    assert "chatbot with a little hat" not in pre_section5
    assert "keep track of what happened" not in pre_section5
    assert "handle a task across multiple steps" not in pre_section5
    # Sanity: memory block sits pre-§5 (inside §1 Factual Basis).
    assert "EPISODE / NARRATIVE MEMORY" in pre_section5
    assert "Patch remembers a prior workshop moment." in pre_section5


# ---- 6. Slice non-interference guards ------------------------------


def test_writing_contract_version_unchanged_by_this_slice():
    """SESSION 271 Q-270-15c must NOT bump the writing contract
    version. Corrective-revision semantics remain an open
    architectural question, not a shipped commitment.

    SESSION 271 §187 (later slice in the same session) landed the
    universal AUDIENCE-AWARE COMMUNICATION invariant in
    ``_solo_scene_contract`` — a v5→v6 bump orthogonal to
    corrective-revision. This assertion tracks the post-§187
    canonical version; the Q-270-15c slice itself still touched
    zero contract text."""
    assert WRITING_CONTRACT_VERSION == 6


def test_dialogue_synthesis_has_no_previous_draft_kwarg():
    """Q-270-15c scopes to duration_contract only. Dialogue
    correction (SESSION 263 §6.5 evidence) is a separate open
    question and must not be touched by this slice."""
    sig = inspect.signature(dialogue_synthesis.synthesize_dialogue)
    assert "previous_draft" not in sig.parameters


def test_dialogue_task_message_does_not_emit_previous_draft_block():
    """Dialogue's ``_build_task_section`` must not accidentally
    grow a previous_draft branch through import contamination.
    Belt-and-braces regression guard."""
    src = inspect.getsource(dialogue_synthesis)
    assert "previous_draft" not in src
    assert "PREVIOUS DRAFT TO REVISE" not in src
