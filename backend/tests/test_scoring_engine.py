"""Tests for the scoring engine — modifiers, labels, colors, clamp."""

import math
from datetime import datetime, timedelta
from app.services.scoring_engine import (
    recency_modifier,
    virality_modifier,
    confidence_modifier,
    industry_context_modifier,
    clamp,
    get_score_color,
    get_score_label,
    CATEGORY_WEIGHTS,
    SEVERITY_MAP,
    BASE_SCORE,
)


# ── recency_modifier (exponential decay: half_life=180d, max=2.0, floor=0.2) ─

def test_recency_very_recent():
    """Content from 5 days ago: close to max (2.0) but slightly decayed."""
    recent = datetime.utcnow() - timedelta(days=5)
    result = recency_modifier(recent)
    assert 1.9 < result < 2.0, f"5-day-old finding should be ~1.96, got {result}"


def test_recency_90_days():
    """Content from 60 days ago: decayed but still well above 1.0."""
    recent = datetime.utcnow() - timedelta(days=60)
    result = recency_modifier(recent)
    assert 1.4 < result < 1.7, f"60-day-old finding should be ~1.59, got {result}"


def test_recency_half_life():
    """At exactly 180 days, the modifier should be ~1.0 (half of 2.0)."""
    old = datetime.utcnow() - timedelta(days=180)
    result = recency_modifier(old)
    assert 0.95 < result < 1.05, f"180-day-old finding should be ~1.0, got {result}"


def test_recency_1_year():
    """Content from 365 days ago: decayed past 1.0 but above floor."""
    old = datetime.utcnow() - timedelta(days=365)
    result = recency_modifier(old)
    assert 0.4 < result < 0.6, f"365-day-old finding should be ~0.49, got {result}"


def test_recency_very_old():
    """Content from 3000 days ago: at the floor (0.2)."""
    old = datetime.utcnow() - timedelta(days=3000)
    result = recency_modifier(old)
    assert result == 0.2, f"Very old finding should be at floor 0.2, got {result}"


def test_recency_none():
    """None date should return 1.0 (neutral)."""
    assert recency_modifier(None) == 1.0


def test_recency_monotonically_decreasing():
    """Modifier should decrease as content gets older — no cliff edges."""
    days = [0, 30, 60, 90, 180, 365, 730, 1500, 3000]
    values = [recency_modifier(datetime.utcnow() - timedelta(days=d)) for d in days]
    for i in range(1, len(values)):
        assert values[i] <= values[i - 1], (
            f"Not monotonically decreasing: day {days[i - 1]}={values[i - 1]}, "
            f"day {days[i]}={values[i]}"
        )


# ── confidence_modifier ───────────────────────────────────────────────

def test_confidence_high():
    """High confidence (0.9+) should give ~1.2x weight."""
    result = confidence_modifier(0.95)
    assert 1.1 < result <= 1.2

def test_confidence_medium():
    """Medium confidence (~0.65) should give ~0.75x weight."""
    result = confidence_modifier(0.65)
    assert 0.6 < result < 0.9

def test_confidence_low():
    """Low confidence (0.3) should give floor weight (0.3)."""
    result = confidence_modifier(0.3)
    assert result == 0.3

def test_confidence_zero():
    """Zero confidence should give floor (0.3)."""
    assert confidence_modifier(0.0) == 0.3


# ── industry_context_modifier ─────────────────────────────────────────

def test_industry_legal_court_records():
    """Lawyers in court records should get reduced penalty."""
    assert industry_context_modifier("court_records", "legal") == 0.3

def test_industry_no_industry():
    """No industry = default 1.0."""
    assert industry_context_modifier("court_records", None) == 1.0

def test_industry_unknown_category():
    """Unknown category in a known industry = default 1.0."""
    assert industry_context_modifier("some_random", "legal") == 1.0

def test_industry_unknown_industry():
    """Unknown industry = default 1.0."""
    assert industry_context_modifier("court_records", "plumbing") == 1.0


# ── virality_modifier ───────────────────────────────────────────────────

def test_virality_low():
    assert virality_modifier(5) == 1.0


def test_virality_medium():
    assert virality_modifier(500) == 1.5


def test_virality_high():
    assert virality_modifier(5000) == 2.0


def test_virality_viral():
    assert virality_modifier(50000) == 2.5


def test_virality_mega_viral():
    assert virality_modifier(500000) == 3.0


# ── clamp ───────────────────────────────────────────────────────────────

def test_clamp_within_range():
    assert clamp(500, 0, 1000) == 500


def test_clamp_below_min():
    assert clamp(-50, 0, 1000) == 0


def test_clamp_above_max():
    assert clamp(1500, 0, 1000) == 1000


# ── get_score_color ─────────────────────────────────────────────────────

def test_score_color_excellent():
    assert get_score_color(850) == "#10B981"


def test_score_color_very_good():
    assert get_score_color(770) == "#22C55E"


def test_score_color_good():
    assert get_score_color(720) == "#84CC16"


def test_score_color_fair():
    assert get_score_color(660) == "#EAB308"


def test_score_color_needs_attention():
    assert get_score_color(560) == "#F97316"


def test_score_color_poor():
    assert get_score_color(450) == "#EF4444"


def test_score_color_critical():
    assert get_score_color(300) == "#DC2626"


# ── get_score_label ─────────────────────────────────────────────────────

def test_score_label_excellent():
    assert get_score_label(850) == "Excellent"


def test_score_label_very_good():
    assert get_score_label(770) == "Very Good"


def test_score_label_good():
    assert get_score_label(720) == "Good"


def test_score_label_fair():
    assert get_score_label(660) == "Fair"


def test_score_label_needs_attention():
    assert get_score_label(560) == "Needs Attention"


def test_score_label_poor():
    assert get_score_label(450) == "Poor"


def test_score_label_critical():
    assert get_score_label(300) == "Critical"


# ── Category weights sanity ─────────────────────────────────────────────

def test_category_weights_all_have_severity():
    """Every category in CATEGORY_WEIGHTS must have a severity mapping."""
    for cat in CATEGORY_WEIGHTS:
        assert cat in SEVERITY_MAP, f"Category '{cat}' missing from SEVERITY_MAP"


def test_informational_categories_zero_weight():
    """negative_press and controversial_opinions should have 0 weight."""
    assert CATEGORY_WEIGHTS["negative_press"] == 0.0
    assert CATEGORY_WEIGHTS["controversial_opinions"] == 0.0


def test_positive_categories_have_positive_weight():
    positive_cats = ["professional_achievement", "community_involvement", "positive_press", "constructive_content", "verified_credentials"]
    for cat in positive_cats:
        assert CATEGORY_WEIGHTS[cat] > 0, f"Positive category '{cat}' should have positive weight"


def test_negative_categories_have_negative_weight():
    negative_cats = ["hate_speech", "threats", "illegal_activity", "court_records", "harassment"]
    for cat in negative_cats:
        assert CATEGORY_WEIGHTS[cat] < 0, f"Negative category '{cat}' should have negative weight"


def test_base_score_is_reasonable():
    """Authenticated base score should be within FICO-like range."""
    assert 700 <= BASE_SCORE <= 900


# ── Passive accuracy formula ───────────────────────────────────────────

def test_passive_accuracy_all_scanned():
    """If all 16 sources are scanned, coverage should be 100%."""
    from app.services.passive_scanner import _calculate_passive_accuracy
    all_sources = [
        "serpapi_web", "serpapi_news", "twitter_mentions",
        "youtube_search", "enrichment", "courtlistener",
        "sec_edgar", "semantic_scholar", "github", "wikipedia",
        "stack_exchange", "wayback_machine",
        "linkedin", "facebook", "instagram", "reddit",
    ]
    result = _calculate_passive_accuracy(
        sources_scanned=all_sources,
        identity_confidence=0.9,
        findings_count=20,
        sources_attempted=all_sources,
    )
    assert result >= 90.0, f"All sources scanned should give 90%+, got {result}"


def test_passive_accuracy_partial_credit():
    """Sources attempted but empty should get partial credit (higher than 0)."""
    from app.services.passive_scanner import _calculate_passive_accuracy

    # Only attempted, nothing scanned
    result_attempted = _calculate_passive_accuracy(
        sources_scanned=[],
        identity_confidence=0.5,
        findings_count=0,
        sources_attempted=["serpapi_web", "serpapi_news", "twitter_mentions",
                           "linkedin", "facebook", "instagram", "reddit"],
    )

    # Nothing attempted at all
    result_empty = _calculate_passive_accuracy(
        sources_scanned=[],
        identity_confidence=0.5,
        findings_count=0,
        sources_attempted=[],
    )

    assert result_attempted > result_empty, (
        f"Attempted sources should score higher: {result_attempted} vs {result_empty}"
    )


def test_passive_accuracy_social_platforms_boost():
    """Adding social platform hits should meaningfully raise accuracy."""
    from app.services.passive_scanner import _calculate_passive_accuracy

    base_sources = ["serpapi_web", "courtlistener", "sec_edgar"]
    base_attempted = base_sources + ["serpapi_news", "twitter_mentions",
                                      "youtube_search", "enrichment",
                                      "semantic_scholar", "github", "wikipedia",
                                      "stack_exchange", "wayback_machine",
                                      "linkedin", "facebook", "instagram", "reddit"]

    # Without social platforms
    result_without = _calculate_passive_accuracy(
        sources_scanned=base_sources,
        identity_confidence=0.55,
        findings_count=7,
        sources_attempted=base_attempted,
    )

    # With social platforms scanned
    result_with = _calculate_passive_accuracy(
        sources_scanned=base_sources + ["linkedin", "facebook", "instagram", "reddit"],
        identity_confidence=0.55,
        findings_count=7,
        sources_attempted=base_attempted,
    )

    assert result_with > result_without, (
        f"Social platforms should boost accuracy: {result_with} vs {result_without}"
    )
