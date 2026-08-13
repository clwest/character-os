"""Bridge-tool description contract.

Engine-bridge tools (``consult_engine``, ``query_spider_data``,
``agent_consult``) cannot rely on the avatar narrating their
results: Runway's SDK is one-way (avatar → SPA), so the LLM
never sees the tool result event. The descriptions therefore
hand the answer off to the SPA ("renders on screen for the
operator") and explicitly tell the avatar not to recite.

An earlier iteration also embedded a pre-narration cue ("Before
invoking, voice ..."). Real-mode dogfood showed Runway's LLM
ignored it — same class of bias documented at
``feedback_runway_avatar_greeting_bias``. The cue was dropped;
v2 narration will pipe the answer through VO-arc TTS so a
real voice plays through the SPA's audio channel.

These tests freeze the post-cleanup contract so a future
refactor can't accidentally re-add an instruction Runway won't
honour, or remove the screen-handoff that frees the avatar
from trying to recite.
"""
from __future__ import annotations

import pytest

from apps.realtime.tools import get_tool


# 500-char ceiling matches the media-engine Pydantic schema
# (InternalRealtimeToolDef.description max_length=500).
MAX_DESCRIPTION_CHARS = 500

BRIDGE_TOOLS = ("consult_engine", "query_spider_data", "agent_consult")


@pytest.mark.parametrize("tool_name", BRIDGE_TOOLS)
def test_bridge_tool_description_under_runway_cap(tool_name):
    spec = get_tool(tool_name)
    assert len(spec.description) <= MAX_DESCRIPTION_CHARS, (
        f"{tool_name} description is {len(spec.description)} chars "
        f"(cap {MAX_DESCRIPTION_CHARS})"
    )


@pytest.mark.parametrize("tool_name", BRIDGE_TOOLS)
def test_bridge_tool_description_has_no_pre_narration_cue(tool_name):
    """The avatar IGNORES "Before invoking, voice X" instructions
    in real mode (same bias as ``feedback_runway_avatar_greeting_
    bias``). The cue was dropped to keep descriptions honest;
    re-adding it would mislead future readers about what the
    description can control."""
    spec = get_tool(tool_name)
    text = spec.description.lower()
    assert "before invoking" not in text, (
        f"{tool_name} description re-added a pre-narration cue that "
        f"Runway's LLM ignores in real mode"
    )


@pytest.mark.parametrize("tool_name", BRIDGE_TOOLS)
def test_bridge_tool_description_hands_off_to_screen(tool_name):
    """The avatar can't see the tool result — the description
    must point it at the SPA panel so it doesn't try to recite
    what it can't see."""
    spec = get_tool(tool_name)
    text = spec.description.lower()
    assert "on screen" in text, (
        f"{tool_name} description lost the screen-hand-off cue"
    )


@pytest.mark.parametrize("tool_name", BRIDGE_TOOLS)
def test_bridge_tool_description_no_summarise_instruction(tool_name):
    """Older descriptions told the avatar to "summarise briefly" —
    impossible when the avatar never receives the answer. The
    pre-narration + screen-hand-off pair replaces that
    instruction."""
    spec = get_tool(tool_name)
    text = spec.description.lower()
    assert "summarise" not in text, (
        f"{tool_name} still tells the avatar to summarise — it "
        f"can't, because Runway's SDK is one-way"
    )
    assert "summarize" not in text, (
        f"{tool_name} still tells the avatar to summarize — it "
        f"can't, because Runway's SDK is one-way"
    )
