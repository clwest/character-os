"""§19 Step 9.b.2 append-only journal tests (SESSION 249).

Load-bearing invariants proved here:

* One JSONL file per POST, filename ``<decision_id>.jsonl``.
* Byte-stable canonical serialization (two writers, same payload,
  same bytes on disk).
* Atomic creation — writes via temp + rename; a partial write can
  never leave a half-file at the target path.
* Idempotent replay — same ``decision_id`` + same canonical payload
  returns ``(record, created=False)`` and does NOT rewrite the file.
* ``DecisionIdConflict`` — same ``decision_id`` + different payload
  refuses loudly.
* Currency derivation — terminal decision per slot walks the
  ``supersedes_decision_id`` chain across every file.
* Malformed files raise loudly (never silently skipped).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from apps.bootstrap_review.journal import (
    REVIEW_SCHEMA_VERSION,
    DecisionIdConflict,
    DecisionRecord,
    JournalError,
    MalformedJournalRecord,
    _canonical_json,
    _validate_decision_id_shape,
    append_decision,
    current_decision_per_slot,
    decision_file_path,
    decision_history_for_slot,
    derive_fixture_progress,
    iter_all_decisions,
    review_dir_for_fixture,
)

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"


# ---------------------------------------------------------------------
# Fixture — clean journal directory before + after each test
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_review_directories():
    """Every test starts with fresh empty journal dirs. Cleans up at
    the end so subsequent tests + the pytest runtime see no residue
    (per operator's zero-file guarantee on frozen tree).
    """
    dirs = [
        review_dir_for_fixture(f)
        for f in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    ]
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    yield
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _record(
    *,
    decision_id: str | None = None,
    review_run_id: str | None = None,
    fixture_id: str = "fixture_h1",
    reference_kind: str = "portrait_reference",
    reference_purpose: str = "front",
    disposition: str = "no_candidate_approved",
    frozen_candidate_id: str | None = None,
    supersedes_decision_id: str | None = None,
    amendment_reason: str | None = None,
    reviewer_user_id: int = 42,
    reviewer_email: str = "chris@example.test",
    decided_at_utc: str = "2026-08-08T10:00:00.000000+00:00",
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id or str(uuid.uuid4()),
        review_run_id=review_run_id or str(uuid.uuid4()),
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id=fixture_id,
        reference_kind=reference_kind,
        reference_purpose=reference_purpose,
        disposition=disposition,  # type: ignore[arg-type]
        frozen_candidate_id=frozen_candidate_id,
        supersedes_decision_id=supersedes_decision_id,
        amendment_reason=amendment_reason,
        reviewer_user_id=reviewer_user_id,
        reviewer_email_at_write_time=reviewer_email,
        decided_at_utc=decided_at_utc,
    )


# ---------------------------------------------------------------------
# Shape / vocabulary refusals
# ---------------------------------------------------------------------


def test_decision_id_shape_refuses_traversal():
    for bad in ("", "../etc", "abc/def", "abc\\def", "..", "AB123", "a b"):
        with pytest.raises(JournalError):
            _validate_decision_id_shape(bad)


def test_decision_id_shape_accepts_uuid():
    _validate_decision_id_shape(str(uuid.uuid4()))


def test_unknown_fixture_refused():
    with pytest.raises(JournalError):
        review_dir_for_fixture("fixture_nh1")


# ---------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------


def test_canonical_json_is_byte_stable():
    payload = {"z": 1, "a": [2, 1], "m": "hello"}
    a = _canonical_json(payload)
    b = _canonical_json({"m": "hello", "a": [2, 1], "z": 1})  # keys shuffled
    assert a == b
    # Compact: no spaces around separators.
    assert b" " not in a


# ---------------------------------------------------------------------
# Atomic append + idempotency + conflict
# ---------------------------------------------------------------------


def test_first_append_creates_file_and_records_created_true():
    record = _record()
    result, created = append_decision(record)
    assert created is True
    assert result is record
    path = decision_file_path(record.fixture_id, record.decision_id)
    assert path.is_file()
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    header = json.loads(lines[0])
    decision = json.loads(lines[1])
    assert header["record_type"] == "review_run_header"
    assert header["review_run_id"] == record.review_run_id
    assert decision["record_type"] == "decision"
    assert decision["decision_id"] == record.decision_id
    assert decision["review_schema_version"] == REVIEW_SCHEMA_VERSION


def test_idempotent_replay_same_uuid_same_payload_returns_false():
    record = _record()
    append_decision(record)
    _, created = append_decision(record)
    assert created is False


def test_same_uuid_different_payload_raises_conflict():
    record = _record(decision_id="00000000-0000-4000-8000-000000000001")
    append_decision(record)
    other = _record(
        decision_id="00000000-0000-4000-8000-000000000001",
        reviewer_email="different@example.test",
    )
    with pytest.raises(DecisionIdConflict):
        append_decision(other)


def test_no_partial_file_on_failure(monkeypatch):
    """If os.link (the atomic-create rename) fails, no partial file
    remains at the target path.
    """
    record = _record()
    review_dir = review_dir_for_fixture(record.fixture_id)
    review_dir.mkdir(parents=True, exist_ok=True)
    # Simulate atomic-create failure by making os.link raise a
    # non-FileExistsError. Confirms the tmp file is cleaned up + no
    # target file exists.
    import apps.bootstrap_review.journal as journal_module

    def boom(src, dst):
        raise OSError("simulated write failure")

    monkeypatch.setattr(journal_module.os, "link", boom)
    with pytest.raises(OSError):
        append_decision(record)
    target = decision_file_path(record.fixture_id, record.decision_id)
    assert not target.exists()
    # No leftover *.tmp files.
    leftovers = [p for p in review_dir.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


# ---------------------------------------------------------------------
# Currency derivation
# ---------------------------------------------------------------------


def test_current_decision_derives_first_write():
    r = _record()
    append_decision(r)
    current = current_decision_per_slot(r.fixture_id)
    assert current == {
        (r.reference_kind, r.reference_purpose): pytest.approx_dict_equal
        if False
        else current[(r.reference_kind, r.reference_purpose)]
    }
    assert current[(r.reference_kind, r.reference_purpose)]["decision_id"] == r.decision_id


def test_amendment_chain_derives_terminal_decision():
    r1 = _record(
        decision_id="11111111-1111-4111-8111-111111111111",
        decided_at_utc="2026-08-08T10:00:00.000000+00:00",
    )
    r2 = _record(
        decision_id="22222222-2222-4222-8222-222222222222",
        supersedes_decision_id=r1.decision_id,
        amendment_reason="second thought",
        decided_at_utc="2026-08-08T11:00:00.000000+00:00",
    )
    r3 = _record(
        decision_id="33333333-3333-4333-8333-333333333333",
        supersedes_decision_id=r2.decision_id,
        amendment_reason="third",
        decided_at_utc="2026-08-08T12:00:00.000000+00:00",
    )
    append_decision(r1)
    append_decision(r2)
    append_decision(r3)
    current = current_decision_per_slot(r1.fixture_id)
    assert current[(r1.reference_kind, r1.reference_purpose)]["decision_id"] == r3.decision_id


def test_prior_files_are_never_mutated_by_amendment():
    r1 = _record(decision_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    append_decision(r1)
    r1_path = decision_file_path(r1.fixture_id, r1.decision_id)
    original_bytes = r1_path.read_bytes()

    r2 = _record(
        decision_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        supersedes_decision_id=r1.decision_id,
        amendment_reason="changed",
        decided_at_utc="2026-08-08T13:00:00.000000+00:00",
    )
    append_decision(r2)
    assert r1_path.read_bytes() == original_bytes


def test_history_for_slot_returns_all_decisions_in_order():
    r1 = _record(
        decision_id="c1111111-1111-4111-8111-111111111111",
        decided_at_utc="2026-08-08T10:00:00.000000+00:00",
    )
    r2 = _record(
        decision_id="c2222222-2222-4222-8222-222222222222",
        supersedes_decision_id=r1.decision_id,
        amendment_reason="revise",
        decided_at_utc="2026-08-08T11:00:00.000000+00:00",
    )
    append_decision(r1)
    append_decision(r2)
    history = decision_history_for_slot(
        r1.fixture_id, r1.reference_kind, r1.reference_purpose
    )
    assert [d["decision_id"] for d in history] == [r1.decision_id, r2.decision_id]


def test_malformed_journal_file_raises_loudly():
    d = review_dir_for_fixture("fixture_h1")
    d.mkdir(parents=True, exist_ok=True)
    (d / "corrupt.jsonl").write_text("this is not json\n")
    with pytest.raises(MalformedJournalRecord):
        list(iter_all_decisions("fixture_h1"))


# ---------------------------------------------------------------------
# FixtureProgress — Finding 4 dual signal
# ---------------------------------------------------------------------


def test_progress_zero_of_seven_when_no_decisions():
    progress = derive_fixture_progress(
        "fixture_h1",
        required_for_identity=["portrait_reference/front", "portrait_reference/neutral_rest"],
    )
    assert progress.purposes_dispositioned == 0
    assert progress.purposes_total == 7
    assert progress.review_complete is False
    assert progress.approval_floor_satisfied is False


def test_progress_review_complete_but_floor_unsatisfied():
    # 7 dispositioned but front + neutral_rest are no_candidate_approved.
    for i, purpose in enumerate(
        [
            "front",
            "slight_left",
            "slight_right",
            "neutral_rest",
            "listening",
            "consideration",
            "gentle_positive",
        ]
    ):
        append_decision(
            _record(
                decision_id=f"c{i:07d}-0000-4000-8000-000000000000",
                reference_purpose=purpose,
                disposition="no_candidate_approved",
                decided_at_utc=f"2026-08-08T10:0{i}:00.000000+00:00",
            )
        )
    progress = derive_fixture_progress(
        "fixture_h1",
        required_for_identity=["portrait_reference/front", "portrait_reference/neutral_rest"],
    )
    assert progress.review_complete is True
    assert progress.approval_floor_satisfied is False
    assert progress.approval_floor_satisfied_pairs == ()


def test_progress_floor_satisfied_but_review_incomplete():
    # Only front + neutral_rest dispositioned (selected); 5 optional
    # untouched.
    fcid = f"{FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact"
    append_decision(
        _record(
            decision_id="d0000001-0000-4000-8000-000000000000",
            reference_purpose="front",
            disposition="selected",
            frozen_candidate_id=fcid,
            decided_at_utc="2026-08-08T10:00:00.000000+00:00",
        )
    )
    fcid_nr = f"{FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__neutral_rest__compact"
    append_decision(
        _record(
            decision_id="d0000002-0000-4000-8000-000000000000",
            reference_purpose="neutral_rest",
            disposition="selected",
            frozen_candidate_id=fcid_nr,
            decided_at_utc="2026-08-08T10:01:00.000000+00:00",
        )
    )
    progress = derive_fixture_progress(
        "fixture_h1",
        required_for_identity=["portrait_reference/front", "portrait_reference/neutral_rest"],
    )
    assert progress.review_complete is False
    assert progress.purposes_dispositioned == 2
    assert progress.approval_floor_satisfied is True
    assert set(progress.approval_floor_satisfied_pairs) == {
        "portrait_reference/front",
        "portrait_reference/neutral_rest",
    }


def test_progress_both_signals_true():
    fcid_front = f"{FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact"
    fcid_nr = f"{FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__neutral_rest__compact"
    for i, (purpose, disposition, fcid) in enumerate(
        [
            ("front", "selected", fcid_front),
            ("neutral_rest", "selected", fcid_nr),
            ("slight_left", "no_candidate_approved", None),
            ("slight_right", "no_candidate_approved", None),
            ("listening", "no_candidate_approved", None),
            ("consideration", "no_candidate_approved", None),
            ("gentle_positive", "no_candidate_approved", None),
        ]
    ):
        append_decision(
            _record(
                decision_id=f"e{i:07d}-0000-4000-8000-000000000000",
                reference_purpose=purpose,
                disposition=disposition,
                frozen_candidate_id=fcid,
                decided_at_utc=f"2026-08-08T10:0{i}:00.000000+00:00",
            )
        )
    progress = derive_fixture_progress(
        "fixture_h1",
        required_for_identity=["portrait_reference/front", "portrait_reference/neutral_rest"],
    )
    assert progress.review_complete is True
    assert progress.approval_floor_satisfied is True
