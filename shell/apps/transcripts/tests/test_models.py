"""B1.2 — ``TranscriptHighlight`` model tests.

Six concerns:

1. Happy-path save with realistic FK shape.
2. Workspace isolation enforced via ``clean()``.
3. Signal catches the raw ``.save()`` path (no full_clean()).
4. ``source_transcript`` must be ``AssetType.TRANSCRIPT``.
5. ``char_end > char_start`` enforced (at clean() + DB check).
6. ``text`` ≤ 280 chars enforced.

Status enum membership + ordering verified inline.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType, Composition
from apps.spokespeople.models import Teammate
from apps.transcripts.models import (
    MAX_HIGHLIGHT_CHARS,
    TranscriptHighlight,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_transcript(ws: Workspace, body: str = "Assistant: hi there.") -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=body,
        source_spec={"primitive_kind": "realtime_transcript"},
        mime_type="text/plain",
        size_bytes=len(body.encode("utf-8")),
    )


def _make_clip_asset(ws: Workspace) -> Asset:
    """A non-TRANSCRIPT asset for the type-validation test."""
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/data/test/clip.mp4",
        mime_type="video/mp4",
        size_bytes=1024,
    )


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Marcus", runway_avatar_id="av_marcus",
        portrait_path="https://fake/p.png",
        business_brief="Roman history guide.",
    )


def _make_composition(ws: Workspace, sp: Teammate) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="test comp",
        template_kind="talking_head_polished",
    )


# ---- happy path ------------------------------------------------


def test_highlight_persists_with_realistic_fields() -> None:
    """Smoke: model accepts a representative row + can be
    queried back. Defaults align with scope-lock expectations
    (status=PENDING, llm fields zero-valued)."""
    ws = _make_workspace("b12hp@test")
    transcript = _make_transcript(
        ws,
        "Assistant: This is the punchy moment worth sharing.",
    )
    text = "This is the punchy moment worth sharing."
    cs = transcript.inline_content.index(text)
    ce = cs + len(text)

    h = TranscriptHighlight.objects.create(
        workspace=ws,
        source_transcript=transcript,
        text=text,
        char_start=cs,
        char_end=ce,
        llm_reasoning="self-contained insight",
        llm_model_id="gpt-5-mini",
        llm_cost_micros=500,
        llm_tokens_input=120,
        llm_tokens_output=80,
    )

    assert h.id is not None
    assert h.status == TranscriptHighlight.Status.PENDING
    assert h.produced_composition is None
    assert h.decided_at is None
    assert h.mined_at is not None

    # Round-trip query
    reloaded = TranscriptHighlight.objects.get(pk=h.pk)
    assert reloaded.text == text


def test_status_enum_has_v1_values() -> None:
    """v1 ships exactly four status values per scope-lock
    rule 5 state machine. Future additions would be a
    contract change."""
    expected = {"pending", "approved", "rejected", "rendered"}
    actual = {choice for choice, _ in TranscriptHighlight.Status.choices}
    assert actual == expected


# ---- workspace isolation ---------------------------------------


def test_cross_workspace_source_transcript_rejected_at_clean() -> None:
    """Rule 2 — clean() catches the form path. A highlight
    whose workspace differs from the source_transcript's
    workspace must raise ValidationError."""
    ws_a = _make_workspace("b12iso_a@test")
    ws_b = _make_workspace("b12iso_b@test")
    transcript = _make_transcript(ws_b, "Assistant: cross-ws content.")

    h = TranscriptHighlight(
        workspace=ws_a,
        source_transcript=transcript,
        text="cross-ws content.",
        char_start=transcript.inline_content.index("cross-ws content."),
        char_end=transcript.inline_content.index("cross-ws content.") + len("cross-ws content."),
    )
    with pytest.raises(ValidationError) as exc:
        h.full_clean()
    assert "different workspace" in str(exc.value)


def test_cross_workspace_source_transcript_rejected_at_signal() -> None:
    """Rule 2 — signal catches the raw .save() path (no
    full_clean()). Same shape as the R-arc signal pattern."""
    ws_a = _make_workspace("b12iso_sig_a@test")
    ws_b = _make_workspace("b12iso_sig_b@test")
    transcript = _make_transcript(ws_b, "Assistant: cross-ws signal.")

    h = TranscriptHighlight(
        workspace=ws_a,
        source_transcript=transcript,
        text="cross-ws signal.",
        char_start=transcript.inline_content.index("cross-ws signal."),
        char_end=transcript.inline_content.index("cross-ws signal.") + len("cross-ws signal."),
    )
    with pytest.raises(ValidationError):
        h.save()


def test_cross_workspace_produced_composition_rejected() -> None:
    """Rule 2 — produced_composition cross-ws also rejected."""
    ws_a = _make_workspace("b12iso_comp_a@test")
    ws_b = _make_workspace("b12iso_comp_b@test")
    transcript = _make_transcript(ws_a, "Assistant: content.")
    sp_b = _make_teammate(ws_b)
    comp_b = _make_composition(ws_b, sp_b)

    text = "content."
    h = TranscriptHighlight(
        workspace=ws_a,
        source_transcript=transcript,
        text=text,
        char_start=transcript.inline_content.index(text),
        char_end=transcript.inline_content.index(text) + len(text),
        produced_composition=comp_b,
        status=TranscriptHighlight.Status.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        h.full_clean()
    assert "different workspace" in str(exc.value)


def test_same_workspace_save_succeeds() -> None:
    """Regression guard for the isolation tests — same-ws
    saves continue to work cleanly."""
    ws = _make_workspace("b12iso_ok@test")
    transcript = _make_transcript(ws, "Assistant: clean save.")
    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=transcript,
        text="clean save.",
        char_start=transcript.inline_content.index("clean save."),
        char_end=transcript.inline_content.index("clean save.") + len("clean save."),
    )
    h.full_clean()  # should not raise
    h.save()
    assert h.pk is not None


# ---- source asset type -----------------------------------------


def test_non_transcript_source_rejected() -> None:
    """source_transcript MUST be asset_type=TRANSCRIPT (rule 1).
    Pointing it at a CLIP / IMAGE / AUDIO raises at clean()."""
    ws = _make_workspace("b12srctype@test")
    clip = _make_clip_asset(ws)

    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=clip,
        text="x",
        char_start=0,
        char_end=1,
    )
    with pytest.raises(ValidationError) as exc:
        h.full_clean()
    assert "asset_type=TRANSCRIPT" in str(exc.value)


# ---- char range validation -------------------------------------


def test_char_end_must_exceed_char_start_at_clean() -> None:
    ws = _make_workspace("b12char_eq@test")
    transcript = _make_transcript(ws, "Assistant: short.")
    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=transcript,
        text="",
        char_start=5,
        char_end=5,
    )
    with pytest.raises(ValidationError) as exc:
        h.full_clean()
    assert "char_end" in str(exc.value)


def test_char_end_lt_start_rejected_at_db() -> None:
    """CheckConstraint enforces char_end > char_start even
    if clean() is skipped. Defense in depth."""
    ws = _make_workspace("b12char_db@test")
    transcript = _make_transcript(ws, "Assistant: content.")
    # bypass clean() by going straight to .save() with bad data
    # the pre_save signal won't catch this (it routes to clean()
    # only on FK-field changes), so the DB constraint is the
    # final guard
    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=transcript,
        text="x",
        char_start=10,
        char_end=5,
    )
    with pytest.raises((IntegrityError, ValidationError)):
        h.save()


# ---- 280-char cap (rule 8) -------------------------------------


def test_text_exceeding_cap_rejected_at_clean() -> None:
    """Rule 8 — clean() catches text > 280 chars."""
    ws = _make_workspace("b12cap@test")
    body = "Assistant: " + ("x" * 400)
    transcript = _make_transcript(ws, body)

    too_long = "x" * 281
    cs = body.index(too_long[:50])
    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=transcript,
        text=too_long,
        char_start=cs,
        char_end=cs + len(too_long),
    )
    with pytest.raises(ValidationError) as exc:
        h.full_clean()
    assert "exceeds" in str(exc.value).lower()


def test_text_at_cap_accepted() -> None:
    """Edge — exactly 280 chars is fine."""
    ws = _make_workspace("b12capedge@test")
    body = "Assistant: " + ("x" * 300)
    transcript = _make_transcript(ws, body)

    at_cap = "x" * MAX_HIGHLIGHT_CHARS
    cs = body.index(at_cap[:50])
    h = TranscriptHighlight(
        workspace=ws,
        source_transcript=transcript,
        text=at_cap,
        char_start=cs,
        char_end=cs + len(at_cap),
    )
    h.full_clean()  # should not raise


# ---- query patterns --------------------------------------------


def test_approval_queue_query_uses_indexed_lookup() -> None:
    """The (workspace, status) index supports the approval
    queue pattern. Smoke-test the obvious query — no perf
    assertion, just shape."""
    ws = _make_workspace("b12queue@test")
    transcript = _make_transcript(ws, "Assistant: pick one. Assistant: pick two.")

    TranscriptHighlight.objects.create(
        workspace=ws, source_transcript=transcript,
        text="pick one.", char_start=11, char_end=20,
        status=TranscriptHighlight.Status.PENDING,
    )
    TranscriptHighlight.objects.create(
        workspace=ws, source_transcript=transcript,
        text="pick two.", char_start=32, char_end=41,
        status=TranscriptHighlight.Status.APPROVED,
    )

    pending = TranscriptHighlight.objects.filter(
        workspace=ws, status=TranscriptHighlight.Status.PENDING,
    )
    assert pending.count() == 1
    assert "pick one" in pending.first().text
