"""
Content Classifier Service

Classifies content (tweets, posts, web results) into finding categories
with severity levels. Uses rule-based classification as the baseline,
with LLM-powered classification (OpenAI or Anthropic) when API keys
are available for far superior accuracy — understanding context,
sarcasm, sentiment, and nuance that keywords cannot capture.
"""

import json
import re
import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.scoring_engine import CATEGORY_WEIGHTS, SEVERITY_MAP

logger = logging.getLogger(__name__)


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


# ============================================================
# LLM-POWERED CLASSIFICATION
# ============================================================

LLM_SYSTEM_PROMPT = """You are a content classifier for a digital reputation scoring system.
Classify the given content into exactly ONE of these categories:

NEGATIVE (lowers score):
- hate_speech: Racial slurs, hate group support, white supremacy
- threats: Death threats, bomb threats, violence
- illegal_activity: Drug dealing, fraud, money laundering
- explicit_content: Nudity, pornography, NSFW material
- harassment: Stalking, doxxing, cyberbullying
- discriminatory: Sexism, racism, homophobia, bigotry
- substance_abuse: Drug use glorification, drunk driving
- political_extremism: Extremist rhetoric, insurrection support
- profanity: Excessive swearing (mild)
- unprofessional: Complaining about work, unprofessional behavior
- misinformation: Conspiracy theories, anti-vax, fake news

POSITIVE (raises score):
- professional_achievement: Promotions, awards, publications, certifications
- community_involvement: Volunteering, charity, mentoring
- positive_press: Featured in media, keynote speeches, recognition
- constructive_content: Tutorials, open source contributions, teaching

NEUTRAL (no impact):
- neutral: Normal everyday content with no reputation impact

IMPORTANT RULES:
1. Understand CONTEXT and SARCASM. "I'm going to kill this presentation" is neutral/positive, not a threat.
2. Quotations or reporting on events are usually neutral unless the person is endorsing the content.
3. Professional criticism or debate is neutral, not harassment.
4. Humor and jokes should be classified based on their actual content, not surface keywords.
5. Consider the platform context — a tweet saying "this code is trash" is unprofessional but not harassment.

Respond with ONLY a JSON object (no markdown, no explanation):
{"category": "...", "confidence": 0.0-1.0, "reasoning": "brief explanation"}
"""


async def _classify_with_openai(text: str, source: str) -> Optional[ClassificationResult]:
    """Classify content using OpenAI's GPT API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": LLM_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Platform: {source}\nContent: {text[:2000]}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
            )

        if response.status_code != 200:
            logger.warning(f"OpenAI API error: {response.status_code}")
            return None

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON response
        result = json.loads(content)
        category = result.get("category", "neutral")
        confidence = float(result.get("confidence", 0.5))

        if category not in CATEGORY_WEIGHTS:
            category = "neutral"

        severity = SEVERITY_MAP.get(category, "neutral")
        base_impact = CATEGORY_WEIGHTS.get(category, 0.0)
        snippet = text[:80] + "..." if len(text) > 80 else text

        return ClassificationResult(
            category=category,
            severity=severity,
            confidence=confidence,
            title=f"{severity.title()} content detected from {source}",
            description=f"AI classified as '{category}' ({confidence:.0%} confidence). Snippet: \"{snippet}\"",
            base_score_impact=base_impact,
        )
    except Exception as e:
        logger.warning(f"OpenAI classification failed: {e}")
        return None


async def _classify_with_anthropic(text: str, source: str) -> Optional[ClassificationResult]:
    """Classify content using Anthropic's Claude API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 200,
                    "system": LLM_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": f"Platform: {source}\nContent: {text[:2000]}"},
                    ],
                },
            )

        if response.status_code != 200:
            logger.warning(f"Anthropic API error: {response.status_code}")
            return None

        data = response.json()
        content = data["content"][0]["text"].strip()

        result = json.loads(content)
        category = result.get("category", "neutral")
        confidence = float(result.get("confidence", 0.5))

        if category not in CATEGORY_WEIGHTS:
            category = "neutral"

        severity = SEVERITY_MAP.get(category, "neutral")
        base_impact = CATEGORY_WEIGHTS.get(category, 0.0)
        snippet = text[:80] + "..." if len(text) > 80 else text

        return ClassificationResult(
            category=category,
            severity=severity,
            confidence=confidence,
            title=f"{severity.title()} content detected from {source}",
            description=f"AI classified as '{category}' ({confidence:.0%} confidence). Snippet: \"{snippet}\"",
            base_score_impact=base_impact,
        )
    except Exception as e:
        logger.warning(f"Anthropic classification failed: {e}")
        return None


async def classify_content_llm(
    text: str,
    source: str,
    url: Optional[str] = None,
    engagement_count: int = 0,
) -> ClassificationResult:
    """
    Classify content using LLM if available, falling back to rules.
    This is the async version that should be used when an LLM key is configured.
    """
    # Try LLM classification first
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        result = await _classify_with_anthropic(text, source)
        if result:
            return result
    elif settings.OPENAI_API_KEY:
        result = await _classify_with_openai(text, source)
        if result:
            return result

    # Fall back to rule-based
    return classify_content(text, source, url, engagement_count)


# ============================================================
# RULE-BASED CLASSIFICATION (baseline / fallback)
# ============================================================


def classify_content(
    text: str,
    source: str,
    url: Optional[str] = None,
    engagement_count: int = 0,
) -> ClassificationResult:
    """
    Classify a piece of content into a finding category.

    Uses rule-based keyword matching as the baseline. When LLM API keys
    are configured, use classify_content_llm() instead for far better accuracy.
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
