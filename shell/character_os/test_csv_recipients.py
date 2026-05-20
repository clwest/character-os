"""B3.3 — CSV parser helper tests.

Two function surfaces — ``parse_csv`` + ``derive_label``.
Pure Python, no Django ORM.

Edge cases covered:
* Happy path (3 rows, 3 valid).
* Header missing a required column → top-level rejection.
* Header has extras → kept in variables dict.
* Row with empty required value → rejected.
* Whitespace-only rows → silently skipped.
* Header-only paste → no rows, no error (Q-c-8).
* Empty input → header_error.
* BOM at start → stripped.
* Quoted fields with embedded commas → parsed correctly.
* Short / long rows (column count mismatch) → padded /
  truncated to header length.
"""
from __future__ import annotations

from character_os.csv_recipients import (
    RejectedRow,
    derive_label,
    parse_csv,
)


# ---- parse_csv: happy path --------------------------------------


def test_parse_happy_path_three_rows() -> None:
    csv_text = (
        "first_name,company,milestone\n"
        "Bob,Acme,Series B\n"
        "Carol,Initech,IPO\n"
        "Dave,Globex,Pivot\n"
    )
    result = parse_csv(csv_text, ["first_name", "company", "milestone"])

    assert result.header_error is None
    assert result.header == ["first_name", "company", "milestone"]
    assert len(result.valid_rows) == 3
    assert result.valid_rows[0] == {
        "first_name": "Bob", "company": "Acme", "milestone": "Series B",
    }
    assert result.rejected_rows == []


def test_parse_strips_per_cell_whitespace() -> None:
    """Excel paste sometimes carries leading/trailing spaces
    around values. Strip them at parse time."""
    csv_text = (
        "first_name,company\n"
        "  Bob  ,  Acme Co  \n"
    )
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.valid_rows[0]["first_name"] == "Bob"
    assert result.valid_rows[0]["company"] == "Acme Co"


def test_parse_strips_header_whitespace() -> None:
    csv_text = (
        "first_name , company\n"
        "Bob,Acme\n"
    )
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.header == ["first_name", "company"]
    assert result.valid_rows[0]["first_name"] == "Bob"


# ---- header validation ------------------------------------------


def test_parse_header_missing_required_column_rejects_all() -> None:
    csv_text = (
        "first_name,company\n"
        "Bob,Acme\n"
    )
    result = parse_csv(
        csv_text, ["first_name", "company", "milestone"],
    )
    assert result.header_error is not None
    assert "milestone" in result.header_error
    assert result.valid_rows == []
    assert result.rejected_rows == []


def test_parse_header_extra_columns_kept_in_variables() -> None:
    """Rule 1: header is a SUPERSET; extras are workspace
    metadata, not errors."""
    csv_text = (
        "first_name,company,internal_note,salesforce_id\n"
        "Bob,Acme,'cold lead',00Q5e\n"
    )
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.header_error is None
    row = result.valid_rows[0]
    assert row["first_name"] == "Bob"
    assert row["company"] == "Acme"
    assert "internal_note" in row
    assert "salesforce_id" in row


def test_parse_empty_csv_returns_header_error() -> None:
    result = parse_csv("", ["first_name"])
    assert result.header_error is not None
    assert "empty" in result.header_error.lower()


def test_parse_whitespace_only_csv_returns_header_error() -> None:
    result = parse_csv("   \n  \n", ["first_name"])
    assert result.header_error is not None


def test_parse_header_only_csv_returns_no_rows_no_error() -> None:
    """Q-c-8: header-only paste is a valid parse with empty
    body. Campaign stays in DRAFT; the launch endpoint
    rejects empty-recipient campaigns separately."""
    csv_text = "first_name,company\n"
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.header_error is None
    assert result.valid_rows == []
    assert result.rejected_rows == []


def test_parse_blank_header_returns_header_error() -> None:
    csv_text = ",,\nfoo,bar,baz\n"
    result = parse_csv(csv_text, ["first_name"])
    assert result.header_error is not None


# ---- per-row validation -----------------------------------------


def test_parse_row_missing_required_value_rejected() -> None:
    csv_text = (
        "first_name,company,milestone\n"
        "Bob,Acme,Series B\n"
        ",Initech,IPO\n"  # missing first_name
        "Carol,,Pivot\n"  # missing company
        "Dave,Globex,\n"  # missing milestone
    )
    result = parse_csv(
        csv_text, ["first_name", "company", "milestone"],
    )
    assert result.header_error is None
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0]["first_name"] == "Bob"
    assert len(result.rejected_rows) == 3
    assert all(isinstance(r, RejectedRow) for r in result.rejected_rows)
    # Row numbers are body-1-indexed (header is row 0).
    assert [r.row_number for r in result.rejected_rows] == [2, 3, 4]
    # Errors call out which column.
    assert "first_name" in result.rejected_rows[0].error
    assert "company" in result.rejected_rows[1].error
    assert "milestone" in result.rejected_rows[2].error


def test_parse_whitespace_only_row_silently_skipped() -> None:
    """Trailing-blank-row tolerance — don't reject for what
    the operator clearly didn't intend to send."""
    csv_text = (
        "first_name\n"
        "Bob\n"
        "\n"
        "   \n"
        ",,,\n"
        "Carol\n"
    )
    result = parse_csv(csv_text, ["first_name"])
    assert result.header_error is None
    assert len(result.valid_rows) == 2
    assert result.rejected_rows == []


# ---- BOM + quoting + column-count mismatch ----------------------


def test_parse_strips_utf8_bom() -> None:
    csv_text = "\ufefffirst_name,company\nBob,Acme\n"
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.header_error is None
    assert result.header == ["first_name", "company"]


def test_parse_handles_quoted_field_with_comma() -> None:
    csv_text = (
        'first_name,company\n'
        '"Bob","Acme, Inc."\n'
    )
    result = parse_csv(csv_text, ["first_name", "company"])
    assert result.valid_rows[0]["company"] == "Acme, Inc."


def test_parse_short_row_padded_then_rejected_on_missing_value() -> None:
    """Excel sometimes truncates trailing-empty columns —
    don't crash. Pad with empty strings, then the missing-value
    check catches the violation."""
    csv_text = (
        "first_name,company,milestone\n"
        "Bob,Acme\n"  # only 2 columns vs 3 in header
    )
    result = parse_csv(
        csv_text, ["first_name", "company", "milestone"],
    )
    assert len(result.valid_rows) == 0
    assert len(result.rejected_rows) == 1
    assert "milestone" in result.rejected_rows[0].error


def test_parse_long_row_truncated_to_header_length() -> None:
    """A row with MORE columns than the header — truncate to
    header length silently. (Unlikely but operator-pasted
    data might carry stragglers.)"""
    csv_text = (
        "first_name,company\n"
        "Bob,Acme,EXTRA,ALSO_EXTRA\n"
    )
    result = parse_csv(csv_text, ["first_name", "company"])
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0] == {"first_name": "Bob", "company": "Acme"}


# ---- derive_label ----------------------------------------------


def test_label_prefers_first_name() -> None:
    assert derive_label(
        {"first_name": "Bob", "email": "bob@a.co"}, position=3,
    ) == "Bob"


def test_label_falls_back_to_email() -> None:
    assert derive_label(
        {"email": "carol@i.co", "company": "Initech"}, position=2,
    ) == "carol@i.co"


def test_label_falls_back_to_position_when_neither_present() -> None:
    assert derive_label(
        {"company": "Globex"}, position=7,
    ) == "recipient #7"


def test_label_treats_empty_string_first_name_as_missing() -> None:
    """Empty values are treated as missing for label-derivation
    purposes — the operator pasted an empty cell."""
    assert derive_label(
        {"first_name": "  ", "email": "carol@i.co"}, position=4,
    ) == "carol@i.co"


def test_label_treats_empty_string_email_as_missing() -> None:
    assert derive_label(
        {"first_name": "", "email": ""}, position=5,
    ) == "recipient #5"
