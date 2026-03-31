"""Tests for the scoring engine — modifiers, labels, colors, clamp."""

from datetime import datetime, timedelta
from app.services.scoring_engine import (
    recency_modifier,
    virality_modifier,
    clamp,
    get_score_color,
    get_score_label,
    CATEGORY_WEIGHTS,
    SEVERITY_MAP,
    BASE_SCORE,
)


# ── recency_modifier ────────────────────────────────────────────────────

def test_recency_very_recent():
    """Content from the last 30 days should have 2.0x impact."""
    recent = datetime.utcnow() - timedelta(days=5)
    assert recency_modifier(recent) == 2.0


def test_recency_90_days():
    recent = datetime.utcnow() - timedelta(days=60)
    assert recency_modifier(recent) == 1.5


def test_recency_1_year():
    old = datetime.utcnow() - timedelta(days=200)
    assert recency_modifier(old) == 1.0


def test_recency_3_years():
    old = datetime.utcnow() - timedelta(days=800)
    assert recency_modifier(old) == 0.7


def test_recency_5_years():
    old = datetime.utcnow() - timedelta(days=1500)
    assert recency_modifier(old) == 0.5


def test_recency_very_old():
    old = datetime.utcnow() - timedelta(days=3000)
    assert recency_modifier(old) == 0.3


def test_recency_none():
    """None date should return 1.0 (neutral)."""
    assert recency_modifier(None) == 1.0


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
