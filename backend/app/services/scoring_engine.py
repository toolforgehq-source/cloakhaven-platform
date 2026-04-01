"""
Cloak Haven Scoring Engine

The core brain of the entire product. Platform-agnostic — it receives
normalized findings and produces scores. It doesn't care where the data
came from.

Score range: 0-1000
Base score: 750 (everyone starts "good", like a 750 FICO)

Components:
  - Social Media History: 40% weight
  - Web Presence: 35% weight
  - Posting Behavior: 25% weight

Each finding has:
  - A base score impact (from category weights)
  - Three modifiers: recency, virality, pattern
  - Juvenile content exclusion
  - Dispute resolution exclusion
"""

import math
import uuid
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.score import Score, ScoreHistory
from app.models.social_account import SocialAccount
from app.models.user import User


# ============================================================
# CATEGORY WEIGHTS — Base score impact per finding category
# ============================================================

CATEGORY_WEIGHTS: dict[str, float] = {
    # Critical severity — genuinely harmful behavior
    "hate_speech": -150.0,
    "threats": -140.0,
    "illegal_activity": -130.0,
    "court_records": -80.0,  # Reduced from -120 but still significant
    "explicit_content": -110.0,
    # High severity
    "discriminatory": -80.0,
    "harassment": -75.0,
    "substance_abuse": -60.0,
    "political_extremism": -50.0,
    "negative_press": 0.0,  # Informational only — opinions/controversy don't affect score
    # Medium severity
    "profanity": -30.0,
    "unprofessional": -25.0,
    "negative_reviews": -35.0,
    "controversial_opinions": 0.0,  # Informational only — opinions don't affect score
    "misinformation": -25.0,
    # Positive — meaningful but capped by diminishing returns in passive scanner
    "professional_achievement": 25.0,
    "community_involvement": 18.0,
    "positive_press": 30.0,
    "constructive_content": 15.0,
    "verified_credentials": 20.0,
    # Neutral — not scored
    "neutral": 0.0,
}

SEVERITY_MAP: dict[str, str] = {
    "hate_speech": "critical",
    "threats": "critical",
    "illegal_activity": "critical",
    "court_records": "critical",
    "explicit_content": "critical",
    "discriminatory": "high",
    "harassment": "high",
    "substance_abuse": "high",
    "political_extremism": "high",
    "negative_press": "neutral",  # Tracked but doesn't penalize — opinions aren't misconduct
    "profanity": "medium",
    "unprofessional": "medium",
    "negative_reviews": "medium",
    "controversial_opinions": "medium",
    "misinformation": "medium",
    "professional_achievement": "positive",
    "community_involvement": "positive",
    "positive_press": "positive",
    "constructive_content": "positive",
    "verified_credentials": "positive",
    "neutral": "neutral",
}

# Sources that count toward social media component
SOCIAL_SOURCES = {"twitter", "instagram", "tiktok", "facebook", "linkedin", "upload", "reddit"}
# Sources that count toward web presence component
WEB_SOURCES = {"google", "youtube"}
# Sources that count toward posting behavior (future: posts made through Cloak Haven)
BEHAVIOR_SOURCES = {"cloakhaven_post"}

# Component weights
SOCIAL_WEIGHT = 0.40
WEB_WEIGHT = 0.35
BEHAVIOR_WEIGHT = 0.25

# Base score — everyone starts here
BASE_SCORE = 850


# ============================================================
# MODIFIERS
# ============================================================

def recency_modifier(finding_date: Optional[datetime]) -> float:
    """
    Smooth exponential temporal decay for finding impact.

    Uses an exponential decay function instead of step buckets so that
    a 31-day-old finding isn't suddenly worth half as much as a 30-day-old one.

    Formula: impact = max_mult * e^(-lambda * days) clamped to [floor, max_mult]
      - max_mult = 2.0 (very recent content has 2x impact)
      - half_life = 180 days (impact halves every 6 months)
      - floor = 0.2 (very old content still has 20% impact)
    """
    if finding_date is None:
        return 1.0

    now = datetime.utcnow()
    days_ago = max((now - finding_date).days, 0)

    max_mult = 2.0
    half_life = 180.0  # days
    floor = 0.2
    decay_lambda = math.log(2) / half_life

    modifier = max_mult * math.exp(-decay_lambda * days_ago)
    return max(modifier, floor)


def virality_modifier(engagement_count: int) -> float:
    """
    Content with more engagement has higher impact.
    Range: 1.0x to 3.0x
    """
    if engagement_count <= 10:
        return 1.0
    elif engagement_count <= 100:
        return 1.2
    elif engagement_count <= 1000:
        return 1.5
    elif engagement_count <= 10000:
        return 2.0
    elif engagement_count <= 100000:
        return 2.5
    else:
        return 3.0


def confidence_modifier(confidence: float) -> float:
    """
    Findings classified with higher confidence should have greater score impact.

    Low-confidence classifications (e.g. ambiguous content) are downweighted
    so they don't unfairly penalize or reward the subject.

    Range: 0.3x to 1.2x
      - confidence >= 0.9 → 1.2x (high-confidence finding gets full+ weight)
      - confidence ~0.5 → 0.6x (coin-flip classification heavily discounted)
      - confidence < 0.3 → 0.3x (near-random classification, minimal impact)
    """
    if confidence <= 0:
        return 0.3
    # Linear interpolation from (0.3, 0.3) to (1.0, 1.2)
    return max(0.3, min(1.2, 0.3 + (confidence - 0.3) * (1.2 - 0.3) / (1.0 - 0.3)))


def pattern_modifier(category: str, all_findings: list[Finding]) -> float:
    """
    Multiple findings in the same category indicate a pattern, not isolated incident.
    Range: 1.0x to 2.0x
    """
    same_category_count = sum(
        1 for f in all_findings
        if f.category == category
        and not f.is_juvenile_content
        and not (f.is_disputed and f.dispute_status == "overturned")
    )

    if same_category_count <= 1:
        return 1.0
    elif same_category_count <= 3:
        return 1.3
    elif same_category_count <= 5:
        return 1.6
    else:
        return 2.0


# ============================================================
# JUVENILE CONTENT POLICY
# ============================================================

def is_juvenile_content(finding_date: Optional[datetime], user_dob: Optional[date]) -> bool:
    """Content posted before age 18 is excluded from scoring."""
    if user_dob is None or finding_date is None:
        return False
    age_at_post = (finding_date.date() - user_dob).days / 365.25
    return age_at_post < 18


# ============================================================
# INDUSTRY / PROFESSION CONTEXT MODIFIER
# ============================================================

# Some findings are expected in certain professions and should be
# weighted differently. A lawyer appearing in court records is normal;
# a doctor publishing in academic journals is expected.
INDUSTRY_CONTEXT_OVERRIDES: dict[str, dict[str, float]] = {
    "legal": {
        "court_records": 0.3,       # Lawyers appear in court records routinely
        "negative_press": 0.5,      # High-profile cases attract press
    },
    "medical": {
        "professional_achievement": 1.3,  # Publications/research are core output
        "verified_credentials": 1.5,     # Board certs matter more
    },
    "politics": {
        "controversial_opinions": 0.0,   # Politicians express opinions publicly
        "negative_press": 0.3,           # Press coverage is constant
        "political_extremism": 0.6,      # Stronger opinions are more expected
    },
    "finance": {
        "sec_edgar": 0.5,                # SEC filings are routine for finance professionals
        "court_records": 0.7,            # Regulatory proceedings are more common
    },
    "entertainment": {
        "explicit_content": 0.5,         # Entertainment industry norms differ
        "profanity": 0.3,               # Language norms are looser
        "negative_press": 0.3,          # Tabloid coverage is constant
    },
    "technology": {
        "constructive_content": 1.3,     # Open-source contributions valued
        "professional_achievement": 1.2, # Patents, publications matter
    },
}


def industry_context_modifier(
    category: str,
    industry: Optional[str] = None,
) -> float:
    """
    Adjust finding impact based on the subject's profession/industry.

    Returns a multiplier (default 1.0). Industries where a finding category
    is routine get a reduced multiplier; industries where a category is
    especially meaningful get an increased multiplier.
    """
    if not industry:
        return 1.0
    industry_lower = industry.lower()
    # Match industry to closest known context
    for key, overrides in INDUSTRY_CONTEXT_OVERRIDES.items():
        if key in industry_lower:
            return overrides.get(category, 1.0)
    return 1.0


# ============================================================
# SCORE ACCURACY CALCULATION
# ============================================================

ACCURACY_WEIGHTS: dict[str, float] = {
    "twitter": 12.0,
    "instagram": 12.0,
    "tiktok": 8.0,
    "facebook": 8.0,
    "linkedin": 8.0,
    "reddit": 8.0,
    "youtube": 7.0,
    "google": 20.0,
    "enrichment": 7.0,
    "self_verified": 10.0,
}


async def calculate_accuracy(db: AsyncSession, user_id: uuid.UUID) -> float:
    """
    Score accuracy reflects how complete the data picture is.
    100% = all platforms connected + Google scanned + verified
    """
    result = await db.execute(
        select(SocialAccount.platform).where(SocialAccount.user_id == user_id)
    )
    connected_platforms = {row[0] for row in result.all()}

    accuracy = 0.0
    for platform, weight in ACCURACY_WEIGHTS.items():
        if platform == "self_verified":
            # Check if user has completed a full self-audit
            user = await db.get(User, user_id)
            if user and user.is_profile_claimed:
                accuracy += weight
        elif platform == "google":
            # Check if Google scan has been done (findings with source='google' exist)
            google_result = await db.execute(
                select(func.count()).where(
                    Finding.user_id == user_id,
                    Finding.source == "google"
                )
            )
            if google_result.scalar() > 0:
                accuracy += weight
        elif platform in connected_platforms:
            accuracy += weight

    return min(accuracy, 100.0)


# ============================================================
# CORE SCORE CALCULATION
# ============================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


async def calculate_score(db: AsyncSession, user_id: uuid.UUID) -> Score:
    """
    The main scoring function. Calculates the complete Cloak Haven score
    for a user based on all their findings.

    Returns a Score object ready to be persisted.
    """
    # Get user for DOB (juvenile content policy)
    user = await db.get(User, user_id)
    _user_dob = user.date_of_birth if user else None  # reserved for juvenile exclusion

    # Get all findings for this user
    result = await db.execute(
        select(Finding).where(Finding.user_id == user_id)
    )
    findings = list(result.scalars().all())

    # Accumulate impacts by component
    social_impact = 0.0
    web_impact = 0.0
    behavior_impact = 0.0

    # Category breakdown for the score_breakdown JSON
    category_counts: dict[str, dict] = {}

    for finding in findings:
        # Skip juvenile content
        if finding.is_juvenile_content:
            continue

        # Skip overturned disputes
        if finding.is_disputed and finding.dispute_status == "overturned":
            continue

        # Calculate modified impact with all modifiers
        base_impact = finding.base_score_impact
        r_mod = recency_modifier(finding.original_date)
        v_mod = virality_modifier(finding.platform_engagement_count)
        p_mod = pattern_modifier(finding.category, findings)
        c_mod = confidence_modifier(getattr(finding, 'confidence', 0.8))

        # Industry context: look up user's industry from their profile
        i_mod = industry_context_modifier(
            finding.category,
            industry=getattr(user, 'industry', None) if user else None,
        )

        final_impact = base_impact * r_mod * v_mod * p_mod * c_mod * i_mod

        # Update the finding's final_score_impact
        finding.final_score_impact = final_impact

        # Route to correct component
        if finding.source in SOCIAL_SOURCES:
            social_impact += final_impact
        elif finding.source in WEB_SOURCES:
            web_impact += final_impact
        elif finding.source in BEHAVIOR_SOURCES:
            behavior_impact += final_impact
        else:
            # Default to social
            social_impact += final_impact

        # Track category breakdown
        cat = finding.category
        if cat not in category_counts:
            category_counts[cat] = {
                "count": 0,
                "total_impact": 0.0,
                "severity": finding.severity,
            }
        category_counts[cat]["count"] += 1
        category_counts[cat]["total_impact"] += final_impact

    # Calculate component scores (each 0-1000)
    social_score = int(clamp(BASE_SCORE + social_impact, 0, 1000))
    web_score = int(clamp(BASE_SCORE + web_impact, 0, 1000))
    behavior_score = int(clamp(BASE_SCORE + behavior_impact, 0, 1000))

    # Weighted overall score
    overall = (
        social_score * SOCIAL_WEIGHT
        + web_score * WEB_WEIGHT
        + behavior_score * BEHAVIOR_WEIGHT
    )
    overall_score = int(clamp(overall, 0, 1000))

    # Calculate accuracy
    accuracy = await calculate_accuracy(db, user_id)

    # Check if verified
    is_verified = accuracy >= 90.0  # Near-complete data picture

    # Build score breakdown
    score_breakdown = {
        "components": {
            "social_media": {
                "score": social_score,
                "weight": SOCIAL_WEIGHT,
                "impact": social_impact,
            },
            "web_presence": {
                "score": web_score,
                "weight": WEB_WEIGHT,
                "impact": web_impact,
            },
            "posting_behavior": {
                "score": behavior_score,
                "weight": BEHAVIOR_WEIGHT,
                "impact": behavior_impact,
            },
        },
        "categories": {
            cat: {
                "count": data["count"],
                "total_impact": round(data["total_impact"], 2),
                "severity": data["severity"],
            }
            for cat, data in category_counts.items()
        },
        "modifiers_applied": True,
        "juvenile_exclusions": sum(1 for f in findings if f.is_juvenile_content),
        "disputed_exclusions": sum(
            1 for f in findings
            if f.is_disputed and f.dispute_status == "overturned"
        ),
    }

    # Check if score already exists for this user
    existing_score = await db.execute(
        select(Score).where(Score.user_id == user_id)
    )
    score_record = existing_score.scalar_one_or_none()

    now = datetime.utcnow()

    if score_record:
        # Update existing score
        score_record.overall_score = overall_score
        score_record.social_media_score = social_score
        score_record.web_presence_score = web_score
        score_record.posting_behavior_score = behavior_score
        score_record.score_accuracy_pct = accuracy
        score_record.is_verified = is_verified
        score_record.score_breakdown = score_breakdown
        score_record.calculated_at = now
        if is_verified and not score_record.verification_date:
            score_record.verification_date = now
    else:
        # Create new score
        score_record = Score(
            user_id=user_id,
            overall_score=overall_score,
            social_media_score=social_score,
            web_presence_score=web_score,
            posting_behavior_score=behavior_score,
            score_accuracy_pct=accuracy,
            is_verified=is_verified,
            verification_date=now if is_verified else None,
            score_breakdown=score_breakdown,
            calculated_at=now,
        )
        db.add(score_record)

    # Record score history
    history_entry = ScoreHistory(
        user_id=user_id,
        overall_score=overall_score,
        social_media_score=social_score,
        web_presence_score=web_score,
        posting_behavior_score=behavior_score,
        recorded_at=now,
    )
    db.add(history_entry)

    await db.flush()
    return score_record


# ============================================================
# BEHAVIORAL TRAJECTORY TRACKING
# ============================================================

async def calculate_score_trajectory(
    db: AsyncSession,
    user_id: uuid.UUID,
    lookback_days: int = 90,
) -> dict:
    """
    Analyze score history to determine the behavioral trajectory.

    Returns a dict with:
      - trend: "improving" | "stable" | "declining"
      - slope: float (positive = improving, negative = declining)
      - recent_scores: list of recent score snapshots
      - volatility: float (0-1, how much the score fluctuates)

    This gives users and employers a richer picture than a single
    point-in-time score. Someone at 650 but steadily improving is
    very different from someone at 750 but declining.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    result = await db.execute(
        select(ScoreHistory)
        .where(
            ScoreHistory.user_id == user_id,
            ScoreHistory.recorded_at >= cutoff,
        )
        .order_by(ScoreHistory.recorded_at.asc())
    )
    history = list(result.scalars().all())

    if len(history) < 2:
        return {
            "trend": "stable",
            "slope": 0.0,
            "recent_scores": [
                {"score": h.overall_score, "date": h.recorded_at.isoformat()}
                for h in history
            ],
            "volatility": 0.0,
            "data_points": len(history),
        }

    scores = [h.overall_score for h in history]
    dates = [h.recorded_at for h in history]

    # Linear regression (simple least-squares) to find trend slope
    n = len(scores)
    # Convert dates to numeric (days since first data point)
    day_offsets = [(d - dates[0]).total_seconds() / 86400.0 for d in dates]
    x_mean = sum(day_offsets) / n
    y_mean = sum(scores) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(day_offsets, scores))
    denominator = sum((x - x_mean) ** 2 for x in day_offsets)

    slope = numerator / denominator if denominator != 0 else 0.0

    # Classify trend based on slope (points per day)
    if slope > 0.5:
        trend = "improving"
    elif slope < -0.5:
        trend = "declining"
    else:
        trend = "stable"

    # Volatility: standard deviation of score changes between consecutive readings
    changes = [abs(scores[i] - scores[i - 1]) for i in range(1, len(scores))]
    avg_change = sum(changes) / len(changes) if changes else 0.0
    # Normalize to 0-1 range (100-point change = max volatility)
    volatility = min(avg_change / 100.0, 1.0)

    return {
        "trend": trend,
        "slope": round(slope, 3),
        "recent_scores": [
            {"score": h.overall_score, "date": h.recorded_at.isoformat()}
            for h in history[-10:]  # Last 10 data points
        ],
        "volatility": round(volatility, 3),
        "data_points": n,
    }


def get_score_color(score: int) -> str:
    """Return the hex color for a given score value.
    Calibrated like FICO: 850 is near-perfect, 750 is good, 600 is fair."""
    if score >= 800:
        return "#10B981"  # Emerald Green — Excellent (rare, like 800+ FICO)
    elif score >= 750:
        return "#22C55E"  # Green — Very Good
    elif score >= 700:
        return "#84CC16"  # Yellow-Green — Good
    elif score >= 650:
        return "#EAB308"  # Yellow — Fair
    elif score >= 550:
        return "#F97316"  # Orange — Needs Attention
    elif score >= 400:
        return "#EF4444"  # Red-Orange — Poor
    else:
        return "#DC2626"  # Red — Critical


def get_score_label(score: int) -> str:
    """Return the label for a given score value.
    Calibrated like FICO: 800+ is exceptional, 750 is very good."""
    if score >= 800:
        return "Excellent"  # Like 800+ FICO — rare and exceptional
    elif score >= 750:
        return "Very Good"
    elif score >= 700:
        return "Good"
    elif score >= 650:
        return "Fair"
    elif score >= 550:
        return "Needs Attention"
    elif score >= 400:
        return "Poor"
    else:
        return "Critical"
