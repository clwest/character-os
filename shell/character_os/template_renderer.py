"""Template substitution for personalized video scripts.

C-arc slice B3.1 (SESSION 203). Given a script template like
``"Hi {first_name}, saw {company} just hit {milestone}"`` and a
variables dict like ``{"first_name": "Bob", "company": "Acme",
"milestone": "Series B"}``, returns the rendered script.

Two public functions:

* ``parse_placeholders(template)`` — extracts ``{placeholder}``
  names in template order, deduplicated. Used at
  campaign-create time to populate
  ``PersonalizedCampaign.placeholders`` (the CSV header
  contract per rule 1).
* ``render_template(template, variables)`` — substitutes
  variables into the template. Strict on missing keys (raises
  ``TemplateError``); lenient on extra keys (silently ignored
  per rule 1's "header MUST be a strict superset" clause —
  extras don't break anything).

Contract rules in play (``PERSONALIZED_VIDEO_V1.md``):

* Rule 1 — header is the variable contract. ``parse_placeholders``
  returns the set the CSV header must cover.
* Rule 7 — ``{{escape}}`` produces a literal ``{escape}``;
  matches Python's ``str.format()`` convention (Q-c-7).
* Implicit: positional placeholders (``{0}``, ``{}``) are
  rejected at parse time — there's no CSV column name to map
  them to, so they break the contract structurally.
"""
from __future__ import annotations

import string
from typing import Any


class TemplateError(Exception):
    """Raised for any template-parsing or rendering failure.

    Two flavors via ``kind``:

    * ``kind="syntax"`` — malformed template (unclosed brace,
      positional placeholder, format spec we don't support).
      Caller should reject the campaign at create time.
    * ``kind="missing"`` — render-time: a recipient row's
      variables dict lacks a required key. Caller flips that
      recipient row to FAILED with this exception's message
      as ``error_message``.
    """

    def __init__(self, message: str, *, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


# Pythons string.Formatter().parse yields tuples of
# (literal_text, field_name, format_spec, conversion). For our
# bare-name contract we want:
#   - literal_text only -> the closing piece after the last
#     placeholder; harmless.
#   - field_name is the placeholder name. Empty string ("")
#     means positional ({0} or {}) -> reject.
#   - format_spec / conversion non-empty -> reject (no
#     "{x:>10}" or "{x!r}" v1).
_FORMATTER = string.Formatter()


def parse_placeholders(template: str) -> list[str]:
    """Return the deduplicated list of placeholder names in
    ``template``, in the order they first appear.

    ``{{literal}}`` is treated as an escape — produces a literal
    ``{literal}`` at render time and does NOT count as a
    placeholder.

    Raises ``TemplateError(kind="syntax")`` on:

    * Unclosed brace (``"Hi {name"``)
    * Positional placeholder (``"Hi {0}"`` or ``"Hi {}"``)
    * Attribute / index access on a placeholder
      (``"{x.attr}"`` or ``"{x[0]}"``) — we want bare names so
      the CSV header is a clean 1:1 mapping.
    * Format spec or conversion (``"{x:>10}"`` or ``"{x!r}"``) —
      operator can't choose width / formatting in v1; the
      substituted value IS the value.
    """
    if not isinstance(template, str):
        raise TemplateError(
            f"template must be str, got {type(template).__name__}",
            kind="syntax",
        )
    try:
        parts = list(_FORMATTER.parse(template))
    except ValueError as exc:
        # Unclosed brace / mismatched braces.
        raise TemplateError(
            f"template syntax error: {exc}",
            kind="syntax",
        ) from None

    seen: set[str] = set()
    ordered: list[str] = []
    for _literal, field_name, format_spec, conversion in parts:
        if field_name is None:
            # Pure literal segment — no placeholder.
            continue
        if field_name == "" or field_name.isdigit():
            raise TemplateError(
                "positional placeholders (`{0}` or `{}`) are not "
                "supported; use named placeholders so the CSV "
                "header can map to them",
                kind="syntax",
            )
        if "." in field_name or "[" in field_name:
            raise TemplateError(
                f"attribute / index access in placeholder is not "
                f"supported (got {field_name!r}); use a bare name",
                kind="syntax",
            )
        if format_spec or conversion:
            raise TemplateError(
                f"format specs / conversions are not supported "
                f"(got {field_name!r} with spec={format_spec!r} "
                f"conversion={conversion!r}); use a bare "
                f"{{{field_name}}}",
                kind="syntax",
            )
        name = field_name.strip()
        if not name:
            raise TemplateError(
                "placeholder name cannot be empty / whitespace",
                kind="syntax",
            )
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    return ordered


class _StrictDict(dict):
    """``format_map`` lookup helper. Raises ``KeyError(name)``
    when the template references a name we don't have so the
    caller can surface a clean message."""

    def __missing__(self, key):  # noqa: D401 — Python protocol
        raise KeyError(key)


def render_template(
    template: str, variables: dict[str, Any],
) -> str:
    """Substitute ``{placeholders}`` in ``template`` with values
    from ``variables``.

    Values are str-coerced via ``format_map``'s default behavior
    (``str(value)``). Operators paste CSV — every variable is a
    string at the persistence layer — so coercion is a no-op in
    practice. Extra keys in ``variables`` (not referenced by the
    template) are silently ignored: the CSV header is the
    superset of the placeholder set per rule 1; columns the
    template doesn't reference are workspace-metadata, not
    errors.

    Raises:
        ``TemplateError(kind="syntax")``: malformed template.
            Caller rejects the campaign at create time. (This
            path is normally unreachable if
            ``parse_placeholders`` ran first, but we don't
            assume the caller did.)
        ``TemplateError(kind="missing")``: a referenced
            placeholder isn't in ``variables``. Caller flips
            the recipient row to FAILED with this message.
    """
    if not isinstance(template, str):
        raise TemplateError(
            f"template must be str, got {type(template).__name__}",
            kind="syntax",
        )
    try:
        return template.format_map(_StrictDict(variables))
    except KeyError as exc:
        name = exc.args[0] if exc.args else "<unknown>"
        raise TemplateError(
            f"template references {{{name}}} but no such "
            f"variable was provided",
            kind="missing",
        ) from None
    except (IndexError, ValueError) as exc:
        raise TemplateError(
            f"template syntax error: {exc}",
            kind="syntax",
        ) from None
