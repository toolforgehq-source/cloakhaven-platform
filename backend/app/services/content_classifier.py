"""
Content Classifier Service

Classifies content (tweets, posts, web results) into finding categories
with severity levels. Uses rule-based classification with optional
LLM enhancement when API keys are available.
"""

import re
from typing import Optional
from datetime import datetime

from app.services.scoring_engine import CATEGORY_WEIGHTS, SEVERITY_MAP


# Keyword patterns for rule-based classification
KEYWORD_PATTERNS: dict[str, list[str]] = {
    "hate_speech": [
        r"\b(racial\s+slur|n[-_]word|hate\s+group|white\s+supremac|nazi)\b",
    ],
    "threats": [
        r"\b(kill\s+you|death\s+threat|bomb\s+threat|shoot\s+up|murder)\b",
    ],
    "illegal_activity": [
        r"\b(drug\s+deal|selling\s+drugs|stolen\s+goods|money\s+launder|fraud\s+scheme)\b",
    ],
    "explicit_content": [
        r"\b(nude|nsfw|explicit\s+content|pornograph|sex\s+tape)\b",
    ],
    "harassment": [
        r"\b(stalking|doxxing|cyberbully|harass(ing|ment)|intimidat)\b",
    ],
    "discriminatory": [
        r"\b(sexist|racist|homophob|transphob|bigot|discriminat)\b",
    ],
    "substance_abuse": [
        r"\b(getting\s+wasted|drunk\s+driving|blacked\s+out|drug\s+use|cocaine|heroin)\b",
    ],
    "political_extremism": [
        r"\b(extremist|radical|insurrection|overthrow|terrorist)\b",
    ],
    "profanity": [
        r"\b(f[-_*]ck|sh[-_*]t|a[-_*]s|damn|hell|b[-_*]tch)\b",
    ],
    "unprofessional": [
        r"\b(party\s+hard|skip\s+work|hate\s+my\s+job|boss\s+sucks|coworker\s+is\s+an)\b",
    ],
    "misinformation": [
        r"\b(conspiracy|flat\s+earth|anti[-_]vax|fake\s+news|hoax|plandemic)\b",
    ],
    "professional_achievement": [
        r"\b(promoted|award|published|patent|certified|graduated|dean.s\s+list|honor)\b",
    ],
    "community_involvement": [
        r"\b(volunteer|charity|donated|fundrais|community\s+service|mentor)\b",
    ],
    "positive_press": [
        r"\b(featured\s+in|interview|keynote|recognized|humanitarian)\b",
    ],
    "constructive_content": [
        r"\b(tutorial|how[-_]to|teaching|open[-_]source|contribut)\b",
    ],
}


class ClassificationResult:
    """Result of classifying a piece of content."""

    def __init__(
        self,
        category: str,
        severity: str,
        confidence: float,
        title: str,
        description: str,
        base_score_impact: float,
    ):
        self.category = category
        self.severity = severity
        self.confidence = confidence
        self.title = title
        self.description = description
        self.base_score_impact = base_score_impact


def classify_content(
    text: str,
    source: str,
    url: Optional[str] = None,
    engagement_count: int = 0,
) -> ClassificationResult:
    """
    Classify a piece of content into a finding category.

    Uses rule-based keyword matching. In production, this would be
    enhanced with LLM-based classification for better accuracy.
    """
    text_lower = text.lower()

    best_match: Optional[str] = None
    best_confidence = 0.0

    for category, patterns in KEYWORD_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # More matches = higher confidence
                confidence = min(len(matches) * 0.3 + 0.5, 1.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = category

    if best_match is None:
        best_match = "neutral"
        best_confidence = 0.5

    severity = SEVERITY_MAP.get(best_match, "neutral")
    base_impact = CATEGORY_WEIGHTS.get(best_match, 0.0)

    # Generate title
    snippet = text[:80] + "..." if len(text) > 80 else text
    title = f"{severity.title()} content detected from {source}"

    return ClassificationResult(
        category=best_match,
        severity=severity,
        confidence=best_confidence,
        title=title,
        description=f"Content classified as '{best_match}' with {best_confidence:.0%} confidence. Snippet: \"{snippet}\"",
        base_score_impact=base_impact,
    )


def classify_web_result(
    title: str,
    snippet: str,
    url: str,
) -> ClassificationResult:
    """Classify a Google search result."""
    combined_text = f"{title} {snippet}"
    return classify_content(combined_text, source="google", url=url)


def classify_tweet(
    text: str,
    retweet_count: int = 0,
    like_count: int = 0,
    reply_count: int = 0,
) -> ClassificationResult:
    """Classify a tweet/post from X/Twitter."""
    total_engagement = retweet_count + like_count + reply_count
    return classify_content(text, source="twitter", engagement_count=total_engagement)


def classify_uploaded_content(
    text: str,
    platform: str,
    engagement_count: int = 0,
) -> ClassificationResult:
    """Classify content from an uploaded data archive."""
    return classify_content(text, source=platform, engagement_count=engagement_count)
