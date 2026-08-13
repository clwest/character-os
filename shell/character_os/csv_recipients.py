"""CSV → recipient rows parser for the B-3 personalized arc.

C-arc slice B3.3 (SESSION 203). Operator pastes a CSV body
into the SPA campaign-create form. This module parses it,
validates the header against the campaign's placeholders
(rule 1 — header is a strict superset), and returns the
valid rows + per-row rejections in a shape the REST surface
can persist.

Two public functions:

* ``parse_csv(csv_text, expected_placeholders)`` — returns
  a ``ParseResult`` with the header, valid rows, rejected
  rows, and an optional header-level error.
* ``derive_label(variables, position)`` — Q-c-5: first_name
  → email → "recipient #N". Used at PersonalizedRecipient
  create time so the SPA grid renders a friendly label.

Contract rules in play (``PERSONALIZED_VIDEO_V1.md``):

* Rule 1 — CSV header MUST be a superset of the campaign's
  placeholders. If a placeholder isn't in the header, ALL
  rows are rejected via a top-level ``header_error`` — no
  point attempting per-row validation.
* Rule 8 — per-row failures don't block; rejected rows go
  into ``rejected_rows`` with a row number + reason; valid
  rows go into ``valid_rows``.
* Q-c-3 — Python ``csv`` module with the standard ``excel``
  dialect. TSV / pipe / custom dialects are v2.
* Q-c-8 — header-only CSV (no body rows) is a valid parse
  with empty ``valid_rows``. The launch endpoint rejects
  empty-recipient campaigns separately.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class RejectedRow:
    """One row that didn't make it.

    ``row_number`` is 1-indexed within the BODY (header is
    row 0; first data row is row 1). Matches the operator's
    Excel mental model so the SPA can show "row 4 is
    missing first_name."
    """

    row_number: int
    error: str
    raw: dict[str, str]


@dataclass
class ParseResult:
    """Outcome of ``parse_csv``.

    Three states callers handle:

    * ``header_error`` set + empty rows — top-level rejection
      (no expected_placeholders satisfied). Campaign-create
      endpoint returns 400 with this message.
    * No header_error, ``valid_rows`` populated, optional
      ``rejected_rows`` — happy path. Persist valid rows;
      surface rejected rows in the SPA preview.
    * No header_error, empty rows (header-only paste) — also
      valid per Q-c-8. Campaign stays in DRAFT; launch
      endpoint returns 400 separately.
    """

    header: list[str] = field(default_factory=list)
    valid_rows: list[dict[str, str]] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)
    header_error: str | None = None


def parse_csv(
    csv_text: str,
    expected_placeholders: Iterable[str],
) -> ParseResult:
    """Parse ``csv_text`` into recipient rows.

    Args:
        csv_text: Raw CSV string (operator's paste). UTF-8;
            BOM stripped if present.
        expected_placeholders: The campaign's placeholders
            (from ``parse_placeholders(template)``). The CSV
            header MUST be a superset.

    Returns:
        ``ParseResult`` as documented above. Never raises;
        all failure modes surface via the result.
    """
    expected = list(expected_placeholders)

    # Strip UTF-8 BOM if present (Excel paste sometimes
    # leaves one). io.StringIO's csv reader doesn't strip
    # it on its own.
    text = (csv_text or "").lstrip("\ufeff")

    if not text.strip():
        return ParseResult(
            header_error="CSV body is empty",
        )

    reader = csv.reader(io.StringIO(text), dialect="excel")
    rows_iter = iter(reader)

    try:
        raw_header = next(rows_iter)
    except StopIteration:
        return ParseResult(
            header_error="CSV body is empty",
        )

    header = [col.strip() for col in raw_header]
    if not any(header):
        return ParseResult(
            header_error="CSV header is blank",
        )

    # Rule 1 — header must be a strict superset of
    # expected placeholders. Reject the whole paste on
    # any miss so the operator sees the contract violation
    # once, not per-row.
    missing = [p for p in expected if p not in header]
    if missing:
        return ParseResult(
            header=header,
            header_error=(
                f"CSV header is missing required column(s): "
                f"{', '.join(missing)}. Header has: "
                f"{', '.join(header) or '(none)'}."
            ),
        )

    valid_rows: list[dict[str, str]] = []
    rejected_rows: list[RejectedRow] = []

    body_row_index = 0  # 1-indexed for the operator
    for raw_row in rows_iter:
        body_row_index += 1

        # Whitespace-only or all-empty rows are silently
        # skipped — Excel paste commonly carries trailing
        # blanks the operator didn't intend to include.
        if not raw_row or all(not (cell or "").strip() for cell in raw_row):
            continue

        # Pad short rows + truncate long rows to the
        # header's column count so dict construction works.
        cells = list(raw_row[: len(header)])
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))

        variables = {
            header[i]: (cells[i] or "").strip()
            for i in range(len(header))
            if header[i]  # skip blank header columns
        }

        # Per-row validation: every expected placeholder
        # must have a non-empty value.
        missing_vals = [
            p for p in expected if not variables.get(p, "")
        ]
        if missing_vals:
            rejected_rows.append(RejectedRow(
                row_number=body_row_index,
                error=(
                    f"missing value(s) for required column(s): "
                    f"{', '.join(missing_vals)}"
                ),
                raw=variables,
            ))
            continue

        valid_rows.append(variables)

    return ParseResult(
        header=header,
        valid_rows=valid_rows,
        rejected_rows=rejected_rows,
    )


def derive_label(
    variables: dict[str, str], position: int,
) -> str:
    """Q-c-5 — operator-friendly per-recipient label for the
    SPA grid.

    Priority: ``first_name`` → ``email`` → ``recipient #N``
    (1-indexed). Falls through to the numeric label only
    when neither field is present in ``variables`` (or both
    are empty).

    Position is 1-indexed to match the operator's Excel
    mental model and the ``RejectedRow.row_number`` shape.
    """
    first_name = (variables.get("first_name") or "").strip()
    if first_name:
        return first_name

    email = (variables.get("email") or "").strip()
    if email:
        return email

    return f"recipient #{position}"
