"""SESSION 271 Slice 7 / E-KNOWLEDGE-1 — Patch communication-policy
experiment plumbing.

Pins the smallest transient env-gated mechanism that injects a
character-invariant communication-policy rule into §5 HARD
CONSTRAINTS on every Patch solo_scene render, so we can measure
whether an always-present invariant materially changes first-pass
audience-vocabulary reliability (Slice 6 §91 mechanically confirmed
the rule is currently retrieval-omitted for the tested substrate).

Contract this suite protects (10 invariants — see SESSION 271 §99
+ the E-KNOWLEDGE-1 authorisation brief):

1.  Experiment OFF (env unset / whitespace-only) → canonical
    behaviour byte-behavior-equivalent to pre-Slice-7 shape.
2.  Experiment ON + Patch solo_scene → rule appears verbatim in
    §5 HARD CONSTRAINTS.
3.  Rule reaches BOTH first pass AND corrective pass byte-identically
    (via the closure in synthesize_with_duration_gate — same
    discipline as audience_hint).
4.  Rule does NOT alter Factual Basis (§1) — contained to §5.
5.  Rule does NOT get persisted as NarrativeMemory (no memory writes).
6.  Rule does NOT apply to Rivet (spokesperson-identity gate; case-
    insensitive name check).
7.  Rule does NOT apply to dialogue_scene (dialogue_synthesis is
    untouched; the plumbing lives in avatar_speech / duration_contract /
    script_synthesis only).
8.  No schema / UI changes (this suite is behavioural + regression
    only; contract version stays at 5).
9.  No extra retries (retry policy stays bounded to 2 attempts).
10. Env flag default OFF (unset in fresh worker envs).

Also pinned:
- Rule text is compact + policy-only. Does NOT name specific
  vocabulary (`API`, `state`, `language model`, `database`) per
  operator brief — we test whether the model itself infers
  accessible translations.
- Communication-policy plumbing is orthogonal to Q-270-15c
  revision plumbing; both env vars can be independently set /
  unset without cross-contamination.
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os import dialogue_synthesis
from character_os.duration_contract import (
    _CORRECTIVE_REVISION_ENV,
    synthesize_with_duration_gate,
)
from character_os.script_synthesis import (
    ScriptResult,
    _assemble_task_message,
    build_render_brief,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION
from apps.compositions.primitives.avatar_speech import (
    _PATCH_COMMUNICATION_POLICY_ENV,
    _PATCH_COMMUNICATION_POLICY_TEXT,
    _patch_communication_policy_experiment_active,
    _resolve_patch_communication_policy,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


_EXPECTED_RULE = (
    "Patch uses technical terminology when it actually helps and "
    "translates it into ordinary language when it does not. Match "
    "technical depth and vocabulary to the listener's likely "
    "background knowledge without changing Patch's intelligence, "
    "factual grounding, personality, humor, or confidence."
)


# ---- fixtures -----------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(ws: Workspace, *, name: str) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief="b",
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


# ---- 1. env / resolver primitives ---------------------------------


def test_env_var_name_stable():
    """Pin the env-var identifier so drift is loud + dogfood
    instructions do not silently break."""
    assert _PATCH_COMMUNICATION_POLICY_ENV == (
        "CHARACTER_OS_PATCH_COMMUNICATION_POLICY_EXPERIMENT"
    )


def test_rule_text_matches_authorisation_brief():
    """Rule wording is FROZEN per operator brief. Any drift
    breaks the causal-attribution guarantee."""
    assert _PATCH_COMMUNICATION_POLICY_TEXT == _EXPECTED_RULE


def test_experiment_inactive_by_default(monkeypatch):
    """Default local shell must NOT activate the experiment."""
    monkeypatch.delenv(_PATCH_COMMUNICATION_POLICY_ENV, raising=False)
    assert _patch_communication_policy_experiment_active() is False


def test_experiment_whitespace_only_env_treated_as_inactive(monkeypatch):
    """Same discipline as SESSION 270 audience_hint resolver +
    SESSION 271 Q-270-15c revision resolver — whitespace-only
    counts as inactive so operators can toggle off with
    ``export CHARACTER_OS_PATCH_COMMUNICATION_POLICY_EXPERIMENT=``."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "   ")
    assert _patch_communication_policy_experiment_active() is False


def test_experiment_active_when_env_set(monkeypatch):
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    assert _patch_communication_policy_experiment_active() is True


# ---- 2. resolver gate discipline ----------------------------------


def _fake_teammate(name: str):
    return type("FakeSp", (), {"name": name})()


def test_resolver_returns_none_when_env_unset(monkeypatch):
    monkeypatch.delenv(_PATCH_COMMUNICATION_POLICY_ENV, raising=False)
    got = _resolve_patch_communication_policy(
        _fake_teammate("Patch"), is_episode_talking_head=True,
    )
    assert got is None


def test_resolver_returns_none_when_not_solo_scene(monkeypatch):
    """Standalone talking_head + long_form_ad + dialogue_scene
    all resolve to is_episode_talking_head==False in the caller
    (avatar_speech.py:602-605)."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    got = _resolve_patch_communication_policy(
        _fake_teammate("Patch"), is_episode_talking_head=False,
    )
    assert got is None


def test_resolver_returns_none_for_rivet_even_when_env_set(monkeypatch):
    """Spokesperson-identity gate. Rivet must never receive the
    Patch-scoped policy regardless of env / lane."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    got = _resolve_patch_communication_policy(
        _fake_teammate("Rivet"), is_episode_talking_head=True,
    )
    assert got is None


def test_resolver_returns_none_for_arbitrary_other_character(monkeypatch):
    """Belt-and-braces: any spokesperson name other than Patch
    (case-insensitive) MUST fail the gate."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    for name in ("Penny", "Terra", "Rigby", "PatchPending", "Not-Patch"):
        got = _resolve_patch_communication_policy(
            _fake_teammate(name), is_episode_talking_head=True,
        )
        assert got is None, f"Expected None for {name!r}, got {got!r}"


def test_resolver_returns_rule_when_all_gates_hold(monkeypatch):
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    got = _resolve_patch_communication_policy(
        _fake_teammate("Patch"), is_episode_talking_head=True,
    )
    assert got == _EXPECTED_RULE


def test_resolver_is_case_insensitive_on_patch_name(monkeypatch):
    """Name check should tolerate case drift."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    for name in ("Patch", "patch", "PATCH", " Patch "):
        got = _resolve_patch_communication_policy(
            _fake_teammate(name), is_episode_talking_head=True,
        )
        assert got == _EXPECTED_RULE, f"Expected rule for {name!r}, got {got!r}"


# ---- 3. _assemble_task_message plumbing ---------------------------


def test_assemble_task_message_no_communication_policy_block_by_default():
    """Absent / None / whitespace policy → no COMMUNICATION POLICY
    block appears in assembled §5."""
    for policy in (None, "", "   "):
        prompt = _assemble_task_message(
            operator_prompt="Topic",
            communication_policy_hint=policy,
        )
        assert "COMMUNICATION POLICY" not in prompt


def test_assemble_task_message_policy_emits_labelled_block():
    """Non-empty policy → labelled block inside §5 HARD CONSTRAINTS,
    rule text embedded verbatim, framed as always-present character
    invariant."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        communication_policy_hint=_EXPECTED_RULE,
    )
    assert "SECTION 5 — TASK" in prompt
    assert "COMMUNICATION POLICY" in prompt
    assert _EXPECTED_RULE in prompt
    assert "character invariant" in prompt
    assert "HARD CONSTRAINTS" in prompt


def test_assemble_task_message_policy_positioned_after_audience_directive():
    """COMMUNICATION POLICY sits AFTER AUDIENCE DIRECTIVE — trailing
    hard-constraint slot for recency (policy is the LAST invariant
    the model reads before writing)."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        audience_hint="AUDIENCE: nontechnical adults",
        communication_policy_hint=_EXPECTED_RULE,
    )
    a = prompt.index("AUDIENCE DIRECTIVE")
    c = prompt.index("COMMUNICATION POLICY")
    assert c > a, "COMMUNICATION POLICY must sit AFTER AUDIENCE DIRECTIVE"


def test_assemble_task_message_policy_coexists_with_every_hard_constraint():
    """Policy must not corrupt opener / previous_draft / corrective_hint /
    audience_hint blocks."""
    prompt = _assemble_task_message(
        operator_prompt="Topic",
        opener="Here is the opener.",
        previous_draft="prior text",
        corrective_hint="Extend the draft.",
        audience_hint="AUDIENCE: general adults",
        communication_policy_hint=_EXPECTED_RULE,
    )
    for marker in (
        "PINNED OPENER",
        "PREVIOUS DRAFT TO REVISE",
        "CORRECTIVE HINT",
        "AUDIENCE DIRECTIVE",
        "COMMUNICATION POLICY",
    ):
        assert marker in prompt, f"missing {marker!r}"


# ---- 4. signature plumbing ----------------------------------------


def test_build_render_brief_signature_has_kwarg():
    """Keyword-only, default None."""
    sig = inspect.signature(build_render_brief)
    assert "communication_policy_hint" in sig.parameters
    p = sig.parameters["communication_policy_hint"]
    assert p.default is None
    assert p.kind is inspect.Parameter.KEYWORD_ONLY


def test_synthesize_with_duration_gate_signature_has_kwarg():
    """Keyword-only, default None. Public function accepts it so
    the avatar_speech primitive can pass through the resolver's
    output — mirrors the audience_hint contract."""
    sig = inspect.signature(synthesize_with_duration_gate)
    assert "communication_policy_hint" in sig.parameters
    p = sig.parameters["communication_policy_hint"]
    assert p.default is None
    assert p.kind is inspect.Parameter.KEYWORD_ONLY


# ---- 5. duration-gate closure — byte-identical on both passes ----


def test_duration_gate_forwards_policy_to_both_passes(monkeypatch):
    """Contract test: when the caller passes communication_policy_hint,
    BOTH first-pass and corrective-pass build_render_brief calls
    receive the identical string. Same closure discipline as
    audience_hint (SESSION 270 §60)."""
    ws = _workspace("policy-both-passes@t")
    tm = _teammate(ws, name="Patch")
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
            tm, "topic",
            target_duration_seconds=90,
            communication_policy_hint=_EXPECTED_RULE,
        )
    assert result.brief == accepted
    assert fake_brb.call_count == 2

    first_policy = fake_brb.call_args_list[0].kwargs.get("communication_policy_hint")
    second_policy = fake_brb.call_args_list[1].kwargs.get("communication_policy_hint")
    assert first_policy == _EXPECTED_RULE, (
        "First-pass build_render_brief must carry the policy"
    )
    assert second_policy == _EXPECTED_RULE, (
        "Corrective build_render_brief must carry the policy"
    )
    assert first_policy == second_policy, (
        "Policy must be byte-identical between passes"
    )


def test_duration_gate_forwards_none_when_caller_omits(monkeypatch):
    """Byte-stability check: when caller omits the kwarg, both
    passes receive None (canonical prompt shape unchanged)."""
    ws = _workspace("policy-none-both@t")
    tm = _teammate(ws, name="Patch")
    short = "x" * 400
    accepted = "x" * 1350

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short),
            _fake_script_result(accepted),
        ],
    ) as fake_brb:
        synthesize_with_duration_gate(tm, "topic", target_duration_seconds=90)
    assert fake_brb.call_count == 2
    for i, call in enumerate(fake_brb.call_args_list):
        assert call.kwargs.get("communication_policy_hint") is None, (
            f"Call {i} unexpectedly received a communication_policy_hint"
        )


# ---- 6. Retry-count invariant preserved ---------------------------


def test_policy_active_does_not_introduce_extra_retries(monkeypatch):
    """Attempt count must stay bounded to 2 even when the policy
    is present on both passes."""
    ws = _workspace("policy-bounded@t")
    tm = _teammate(ws, name="Patch")
    short_1 = "x" * 400
    short_2 = "x" * 500  # still too short — retry fails acceptance

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
                tm, "topic",
                target_duration_seconds=90,
                communication_policy_hint=_EXPECTED_RULE,
            )
    assert fake_brb.call_count == 2


# ---- 7. Containment — policy stays in §5 --------------------------


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
    return Teammate.objects.create(
        workspace=ws, name="Patch", business_brief="Runs a small maker workshop.",
        personality="Curious impulsive builder. Warm dry wit.",
        character_point_of_view="Notices weird bugs first.",
        who_you_help="Fellow tinkerers.", what_you_sell="Custom small hardware.",
        always_emphasize="Show your work.", never_say="perfect the first try",
        desired_feeling="curious", voice_energy="medium",
        voice_humor="dry", voice_directness="direct",
    )


def test_policy_contained_to_section_5(monkeypatch):
    """End-to-end through build_render_brief with the OpenAI call
    stubbed. Assert COMMUNICATION POLICY block appears ONLY after
    §5 header — never in §1 Factual Basis / §2 Character Voice /
    §3 Brand Voice / NarrativeMemory block. Belt-and-braces mirroring
    the SESSION 270 audience-hint + SESSION 271 Q-270-15c no-leak
    tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    ws = _workspace("policy-no-leak@t")
    tm = _teammate_full(ws)

    def _fake_retrieve(spokesperson, *, query, top_k):
        return [_FakeChunk("Retrieved workshop-agent chunk.")]

    def _fake_openai(api_key):
        return _FakeClient()

    monkeypatch.setattr(
        "character_os.script_synthesis.retrieve_for_teammate", _fake_retrieve,
    )
    monkeypatch.setattr("openai.OpenAI", _fake_openai)

    memory_row = _FakeMemory(
        "Patch remembers a prior workshop moment.", "mem-1",
    )
    build_render_brief(
        tm, "Patch does research on AI Agents",
        target_shape="solo_scene",
        memory_rows=[memory_row],
        audience_hint="AUDIENCE: general adults",
        communication_policy_hint=_EXPECTED_RULE,
    )
    assembled = _FakeClient._captured  # type: ignore[attr-defined]

    # Section anchors present.
    assert "SECTION 1 — FACTUAL BASIS" in assembled
    assert "SECTION 2 — CHARACTER VOICE" in assembled
    assert "SECTION 3 — BRAND VOICE" in assembled
    assert "SECTION 5 — TASK" in assembled
    assert "COMMUNICATION POLICY" in assembled
    assert _EXPECTED_RULE in assembled

    # Policy + label sit AFTER §5 header.
    section5_start = assembled.index("SECTION 5 — TASK")
    assert assembled.index("COMMUNICATION POLICY") > section5_start
    assert assembled.index(_EXPECTED_RULE) > section5_start

    # Policy MUST NOT leak into pre-§5 regions.
    pre_section5 = assembled[:section5_start]
    assert "COMMUNICATION POLICY" not in pre_section5
    for fragment in (
        "translates it into ordinary language",
        "listener's likely background knowledge",
        "without changing Patch's intelligence",
    ):
        assert fragment not in pre_section5, (
            f"Policy fragment {fragment!r} leaked into pre-§5 region"
        )
    # Sanity: memory block sits pre-§5 (inside §1 Factual Basis).
    assert "EPISODE / NARRATIVE MEMORY" in pre_section5


# ---- 8. Non-interference guards -----------------------------------


def test_writing_contract_version_unchanged_by_this_slice():
    """SESSION 271 Slice 7 must NOT bump the writing contract version.
    Communication-policy plumbing is transient research infrastructure,
    not a shipped commitment."""
    assert WRITING_CONTRACT_VERSION == 5


def test_dialogue_synthesis_has_no_communication_policy_kwarg():
    """Slice 7 scopes to avatar_speech + duration_contract only.
    Dialogue correction (SESSION 263 §6.5 companion question)
    remains untouched."""
    sig = inspect.signature(dialogue_synthesis.synthesize_dialogue)
    assert "communication_policy_hint" not in sig.parameters


def test_dialogue_module_source_does_not_reference_policy():
    """Belt-and-braces regression: dialogue module must not grow a
    policy-injection branch through import contamination."""
    src = inspect.getsource(dialogue_synthesis)
    assert "communication_policy_hint" not in src
    assert "COMMUNICATION POLICY" not in src


def test_q270_15c_revision_env_name_still_stable():
    """Q-270-15c revision-experiment env name must not have changed
    (both env vars are independent surfaces)."""
    assert _CORRECTIVE_REVISION_ENV == (
        "CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT"
    )


def test_policy_and_revision_envs_are_orthogonal(monkeypatch):
    """Cross-experiment isolation: setting policy env does NOT
    activate revision experiment (and vice versa)."""
    monkeypatch.setenv(_PATCH_COMMUNICATION_POLICY_ENV, "1")
    monkeypatch.delenv(_CORRECTIVE_REVISION_ENV, raising=False)
    from character_os.duration_contract import (
        _corrective_revision_experiment_active,
    )
    assert _patch_communication_policy_experiment_active() is True
    assert _corrective_revision_experiment_active() is False
