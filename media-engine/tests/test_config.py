"""SESSION 138 — Settings.runway_mock behavior tests.

Covers the three states of the runway_mock property:
- No key, no force → mock (default development state)
- Real key, no force → real mode (production / cast-seeding state)
- Real key, force=True → mock (the e2e-suite escape hatch this slice ships)

The force-mock override exists so the e2e suite can run reliably against
a populated real-mode .env without the `mv .env .env.real` workaround
documented in 00-START-NEXT-SESSION.md.
"""
from __future__ import annotations

from app.config import Settings


def test_runway_mock_true_when_no_key() -> None:
    settings = Settings(runway_api_key="")
    assert settings.runway_mock is True


def test_runway_mock_false_when_key_present() -> None:
    settings = Settings(runway_api_key="sk-fake-real-key")
    assert settings.runway_mock is False


def test_runway_force_mock_overrides_present_key() -> None:
    settings = Settings(runway_api_key="sk-fake-real-key", runway_force_mock=True)
    assert settings.runway_mock is True


def test_runway_force_mock_default_is_false() -> None:
    settings = Settings(runway_api_key="sk-fake-real-key")
    assert settings.runway_force_mock is False
    assert settings.runway_mock is False
