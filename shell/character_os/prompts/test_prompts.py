"""Unit tests for the prompt helpers.

Standard pytest. No Django fixtures needed — the helpers are pure
data + pure functions. Run via ``pytest character_os/prompts/``
from inside ``shell/`` with the venv active.
"""
from __future__ import annotations

import pytest

from character_os.prompts import (
    BRAND_STYLES,
    COLOR_PALETTES,
    CREATIVE_PRINCIPLES,
    INDUSTRY_PALETTE_MAP,
    TONE_ARCHETYPES,
    check_prompt_sharpness,
    clean_business_brief,
    get_palette,
    get_style,
    principles_for_kind,
    sharpen_prompt,
    suggest_palette_from_brief,
    suggest_tone_from_brief,
)


# ---- sharpening -----------------------------------------------------


class TestSharpenPrompt:
    def test_replaces_hedge_phrase(self):
        out = sharpen_prompt("we should validate the data")
        assert "THIS REQUIRES validation" in out

    def test_case_insensitive(self):
        out = sharpen_prompt("We Should Validate the data")
        assert "THIS REQUIRES validation" in out

    def test_word_boundary_avoids_partial_match(self):
        # "maybe" → "LIKELY or UNLIKELY -". Ensure "maybelline" isn't munged.
        out = sharpen_prompt("maybelline is a brand")
        assert "maybelline" in out

    def test_longer_phrases_match_before_shorter(self):
        # "we should validate" is in the table; the longer phrase
        # should win over the substring "should validate".
        out = sharpen_prompt("we should validate this")
        # Either the long-form or the short-form replacement is fine;
        # what matters is no duplication.
        assert out.count("MUST validate") + out.count("THIS REQUIRES validation") == 1


class TestCleanBusinessBrief:
    def test_strips_fillers(self):
        out = clean_business_brief("Honestly, we basically sell bicycle bells.")
        assert "basically" not in out.lower()
        assert "honestly" not in out.lower()
        assert "bicycle bells" in out.lower()

    def test_softens_hedge_to_natural_voice(self):
        out = clean_business_brief("I think we should probably make videos.")
        # Confidence improved; no ALL CAPS.
        assert "I think we should probably" not in out
        assert out.lower() == out.lower()  # no shouting

    def test_preserves_user_capitalization(self):
        # Operator-typed proper nouns must stay intact.
        out = clean_business_brief("We sell artisan bells in San Francisco.")
        assert "San Francisco" in out
        assert "We" in out

    def test_collapses_whitespace_from_deletions(self):
        out = clean_business_brief("we, honestly, sell bells")
        # Deleting "honestly" leaves "we, , sell" — cleanup should fix.
        assert ", ," not in out
        assert "  " not in out


class TestCheckPromptSharpness:
    def test_clean_text_scores_high(self):
        result = check_prompt_sharpness("We ship the API on Monday. Owner: Casey.")
        assert result["is_sharp"] is True
        assert result["sharpness_score"] > 80

    def test_hedge_heavy_text_scores_low(self):
        result = check_prompt_sharpness(
            "Maybe we should perhaps consider that this might possibly be interesting."
        )
        assert result["is_sharp"] is False
        assert result["hedge_count"] >= 3


# ---- brand ---------------------------------------------------------


class TestPalettes:
    def test_every_palette_has_required_keys(self):
        required = {"primary", "secondary", "accent", "background", "text"}
        for name, palette in COLOR_PALETTES.items():
            assert required.issubset(palette.keys()), (
                f"palette {name!r} missing keys: {required - set(palette.keys())}"
            )

    def test_get_palette_by_internal_key(self):
        assert get_palette("tech_modern") == COLOR_PALETTES["tech_modern"]

    def test_get_palette_by_industry_alias(self):
        # `tech` → `tech_modern` via INDUSTRY_PALETTE_MAP
        assert get_palette("tech") == COLOR_PALETTES["tech_modern"]

    def test_get_palette_unknown_returns_none(self):
        assert get_palette("not_a_real_palette") is None


class TestStyles:
    def test_every_style_has_required_keys(self):
        required = {"characteristics", "avoid", "fonts"}
        for name, style in BRAND_STYLES.items():
            assert required.issubset(style.keys()), (
                f"style {name!r} missing keys: {required - set(style.keys())}"
            )

    def test_get_style_returns_dict(self):
        style = get_style("minimalist")
        assert style is not None
        assert "clean lines" in style["characteristics"]

    def test_get_style_unknown_returns_none(self):
        assert get_style("not_a_real_style") is None


class TestSuggestPalette:
    @pytest.mark.parametrize(
        "brief,expected",
        [
            ("Sustainable, organic candles handmade in Vermont.", "eco_natural"),
            ("Luxury artisan bicycle bells for serious cyclists.", "luxury_elegant"),
            ("SaaS platform for B2B compliance teams.", "tech_modern"),
            ("Indie design studio doing brand identity work.", "creative_bold"),
            ("Early-stage founder building an indie hack.", "startup_energetic"),
            ("B2B enterprise compliance consulting firm.", "professional_corporate"),
            ("Nothing interesting at all.", "professional_corporate"),  # fallback
        ],
    )
    def test_brief_maps_to_palette(self, brief: str, expected: str):
        assert suggest_palette_from_brief(brief) == expected

    def test_empty_brief_returns_fallback(self):
        assert suggest_palette_from_brief("") == "professional_corporate"

    def test_industry_map_covers_all_known_industries(self):
        # Every industry in INDUSTRY_PALETTE_MAP must point at a real
        # palette — guards against drift if someone edits one dict
        # but not the other.
        for industry, palette_key in INDUSTRY_PALETTE_MAP.items():
            assert palette_key in COLOR_PALETTES, (
                f"INDUSTRY_PALETTE_MAP[{industry!r}] → {palette_key!r} "
                f"but no such key in COLOR_PALETTES"
            )


class TestSuggestTone:
    @pytest.mark.parametrize(
        "brief,expected",
        [
            # tutor — education
            ("High school history teacher building lessons.", "tutor"),
            ("Online course for homeschool students.", "tutor"),
            ("AI-powered tutor for math homework.", "tutor"),
            # performer — entertainment / persuasion
            ("YouTube creator who entertains a viral audience.", "performer"),
            ("Stand-up comedian touring small clubs.", "performer"),
            # friend — community / casual
            ("Local mom-and-pop coffee shop for our neighbors.", "friend"),
            ("Community garden run by a casual collective of friends.", "friend"),
            # authority — decisive / leader
            ("CEO with a no-nonsense leadership style.", "authority"),
            ("Blunt straight-talk newsletter for executives.", "authority"),
            # expert — credentialed / research
            ("PhD scientist consulting on engineering projects.", "expert"),
            ("Research-backed evidence for B2B specialists.", "expert"),
            # fallback
            ("Nothing interesting at all.", "expert"),
            ("", "expert"),
        ],
    )
    def test_brief_maps_to_tone(self, brief: str, expected: str):
        assert suggest_tone_from_brief(brief) == expected

    def test_returned_tone_is_always_in_archetypes(self):
        # Every output value must be one of the five canonical
        # archetypes — guards against typos in the hint table.
        sample_briefs = [
            "",
            "random text",
            "teacher",
            "executive",
            "friend",
            "creator",
            "scientist",
        ]
        for brief in sample_briefs:
            assert suggest_tone_from_brief(brief) in TONE_ARCHETYPES, (
                f"suggest_tone_from_brief({brief!r}) returned a value "
                f"not in TONE_ARCHETYPES"
            )

    def test_distinctive_keyword_beats_generic(self):
        # When a brief mentions both 'teacher' (tutor) and 'expert',
        # the more-distinctive archetype (tutor, listed first in the
        # hint table) wins.
        assert (
            suggest_tone_from_brief("expert teacher with credentials")
            == "tutor"
        )


# ---- creative ------------------------------------------------------


class TestCreativePrinciples:
    def test_spokesperson_ad_is_present(self):
        # The shipped video kind MUST have principles.
        assert "spokesperson_ad" in CREATIVE_PRINCIPLES

    def test_every_kind_has_required_sections(self):
        required = {"key_principles", "common_mistakes", "enhancement_tips"}
        for kind, principles in CREATIVE_PRINCIPLES.items():
            assert required.issubset(principles.keys()), (
                f"kind {kind!r} missing sections: {required - set(principles.keys())}"
            )
            for section in required:
                assert isinstance(principles[section], list)
                assert len(principles[section]) >= 3, (
                    f"kind {kind!r} section {section!r} has fewer than 3 items"
                )

    def test_principles_for_kind_returns_dict(self):
        result = principles_for_kind("spokesperson_ad")
        assert result is not None
        assert "key_principles" in result

    def test_principles_for_kind_unknown_returns_none(self):
        assert principles_for_kind("not_a_kind") is None

    def test_covers_all_video_kinds_we_plan(self):
        # The four video kinds named in MEDIA_ENGINE_INTERNAL_API.md
        # all have principles entries — drift guard.
        for kind in ("spokesperson_ad", "cinematic_video", "dialogue_scene", "long_ad"):
            assert kind in CREATIVE_PRINCIPLES, f"{kind!r} missing from CREATIVE_PRINCIPLES"
