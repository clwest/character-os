"""B3.1 — template_renderer helper tests.

Two function surfaces — parse_placeholders + render_template —
plus the TemplateError shape callers rely on (kind="syntax" vs
kind="missing").

Tests are pure Python, no Django ORM, no fixtures. Run via
``pytest character_os/test_template_renderer.py`` from inside
``shell/``.
"""
from __future__ import annotations

import pytest

from character_os.template_renderer import (
    TemplateError,
    parse_placeholders,
    render_template,
)


# ---- parse_placeholders -----------------------------------------


def test_parse_happy_path_named_placeholders() -> None:
    assert parse_placeholders(
        "Hi {first_name}, saw {company} just hit {milestone}!"
    ) == ["first_name", "company", "milestone"]


def test_parse_dedupes_repeated_placeholders() -> None:
    """A placeholder appearing multiple times shows up once."""
    assert parse_placeholders(
        "Hi {first_name}, {first_name} again, signed: {first_name}"
    ) == ["first_name"]


def test_parse_preserves_first_appearance_order() -> None:
    assert parse_placeholders(
        "{c} then {a} then {b} then {a} again"
    ) == ["c", "a", "b"]


def test_parse_no_placeholders_returns_empty() -> None:
    assert parse_placeholders("just literal text, no braces") == []


def test_parse_doubled_braces_are_literal_escapes() -> None:
    """{{literal}} should NOT count as a placeholder (Q-c-7)."""
    assert parse_placeholders(
        "Hi {{literal}}, {name}, {{more literal}}"
    ) == ["name"]


def test_parse_rejects_positional_placeholder_numeric() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Hi {0}, your code is {1}")
    assert exc.value.kind == "syntax"
    assert "positional" in str(exc.value).lower()


def test_parse_rejects_positional_placeholder_bare() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Hi {}, welcome")
    assert exc.value.kind == "syntax"


def test_parse_rejects_attribute_access() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Hi {user.name}")
    assert exc.value.kind == "syntax"
    assert "attribute" in str(exc.value).lower()


def test_parse_rejects_index_access() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Hi {users[0]}")
    assert exc.value.kind == "syntax"


def test_parse_rejects_format_spec() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Number: {amount:>10}")
    assert exc.value.kind == "syntax"
    assert "format" in str(exc.value).lower()


def test_parse_rejects_conversion() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Repr: {x!r}")
    assert exc.value.kind == "syntax"


def test_parse_rejects_unclosed_brace() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders("Hi {name")
    assert exc.value.kind == "syntax"


def test_parse_rejects_non_string_input() -> None:
    with pytest.raises(TemplateError) as exc:
        parse_placeholders(None)  # type: ignore[arg-type]
    assert exc.value.kind == "syntax"


def test_parse_handles_empty_template() -> None:
    assert parse_placeholders("") == []


# ---- render_template --------------------------------------------


def test_render_happy_path() -> None:
    assert render_template(
        "Hi {first_name}, saw {company} just hit {milestone}!",
        {"first_name": "Bob", "company": "Acme", "milestone": "Series B"},
    ) == "Hi Bob, saw Acme just hit Series B!"


def test_render_substitutes_repeated_placeholder() -> None:
    assert render_template(
        "{name}, {name}, {name}",
        {"name": "Alice"},
    ) == "Alice, Alice, Alice"


def test_render_with_extras_in_vars_is_lenient() -> None:
    """Rule 1: CSV header is a SUPERSET of placeholders. Extra
    keys in the variables dict are silently ignored by the
    renderer (they represent CSV columns not referenced in the
    template — fine)."""
    assert render_template(
        "Hi {first_name}",
        {"first_name": "Bob", "company": "Acme", "email": "b@a.co"},
    ) == "Hi Bob"


def test_render_missing_key_raises_typed_error() -> None:
    with pytest.raises(TemplateError) as exc:
        render_template(
            "Hi {first_name}, saw {company}",
            {"first_name": "Bob"},  # missing "company"
        )
    assert exc.value.kind == "missing"
    assert "company" in str(exc.value)


def test_render_doubled_braces_produce_literal() -> None:
    """Q-c-7: {{literal}} renders as {literal}, NOT as a
    placeholder lookup."""
    assert render_template(
        "Save {{50%}} on {product}",
        {"product": "widgets"},
    ) == "Save {50%} on widgets"


def test_render_no_placeholders_returns_template_unchanged() -> None:
    assert render_template(
        "Static script with no variables.",
        {"unused": "x"},
    ) == "Static script with no variables."


def test_render_coerces_non_string_values_via_str() -> None:
    """format_map calls str() on values implicitly — fine for
    CSV (everything is a string anyway) but worth pinning."""
    assert render_template(
        "Count: {n}",
        {"n": 42},
    ) == "Count: 42"


def test_render_empty_string_variable_substitutes_empty() -> None:
    """An operator-paste empty cell becomes "" — the renderer
    substitutes it without complaint; the recipient row's
    rendered_script just has a gap."""
    assert render_template(
        "Hi {first_name}, welcome",
        {"first_name": ""},
    ) == "Hi , welcome"


def test_render_non_string_template_raises() -> None:
    with pytest.raises(TemplateError) as exc:
        render_template(None, {})  # type: ignore[arg-type]
    assert exc.value.kind == "syntax"


def test_template_error_carries_kind_attribute() -> None:
    """Callers branch on err.kind to decide between
    'reject the campaign at create' (syntax) vs 'flip this
    recipient to FAILED' (missing)."""
    err_syntax = TemplateError("bad", kind="syntax")
    err_missing = TemplateError("bad", kind="missing")
    assert err_syntax.kind == "syntax"
    assert err_missing.kind == "missing"
