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

LLM_SYSTEM_PROMPT = """You are a content classifier for CloakHaven, the global standard for digital reputation scoring.
You classify content that appears in search results, social media posts, and public records ABOUT a specific person.

Classify into exactly ONE category:

CRITICAL NEGATIVE (major score reduction):
- hate_speech: Person directly using racial slurs, supporting hate groups, white supremacy advocacy
- threats: Person making death threats, bomb threats, explicit calls for violence
- illegal_activity: Person involved in drug dealing, fraud, money laundering, theft
- court_records: Arrest records, criminal charges, lawsuits filed against the person
- explicit_content: Person sharing nudity, pornography, NSFW material

HIGH NEGATIVE:
- discriminatory: Person making sexist, racist, homophobic, transphobic, or bigoted statements
- harassment: Person stalking, doxxing, cyberbullying others
- substance_abuse: Person glorifying drug use, posting about drunk driving, substance problems
- political_extremism: Person supporting actual extremist groups, insurrection, terrorism. NOT just having strong political opinions.
- negative_press: Negative news coverage about the person (scandals, firings, controversies)

MEDIUM NEGATIVE:
- profanity: Excessive swearing in a professional context
- unprofessional: Complaining about work, badmouthing employers, inappropriate workplace behavior
- misinformation: Person spreading proven conspiracy theories, anti-vax content, demonstrably false claims

POSITIVE (raises score):
- professional_achievement: Awards, promotions, publications, patents, certifications, graduations
- community_involvement: Volunteering, charity work, donations, mentoring
- positive_press: Positive media coverage, keynote speeches, interviews, recognition, company profiles
- constructive_content: Tutorials, open source contributions, educational content, thought leadership

NEUTRAL (no impact):
- neutral: Normal content, factual information, general discussion, opinions within normal bounds

CRITICAL CLASSIFICATION RULES:
1. CONTEXT IS EVERYTHING. "I'm going to kill this presentation" = neutral. An AI safety discussion = neutral. A tech company profile page = positive_press.
2. NEWS REPORTING about events is neutral UNLESS the person is the subject of negative coverage.
3. Discussions about AI, technology, future risks, space exploration = neutral or constructive_content. These are NOT political_extremism.
4. Company/founder profile pages (Forbes, Wikipedia, Tesla, etc.) = positive_press.
5. Having controversial or strong opinions is NOT political_extremism. Reserve that ONLY for actual extremist group support.
6. A Wikipedia page about a public figure = positive_press (it means they're notable).
7. If the content is ambiguous or you're unsure, classify as neutral. False positives are worse than false negatives.
8. Social media profiles and bios are usually neutral unless they contain explicit problematic content.
9. Court records, arrest reports, legal filings = court_records (even if the person was found innocent, the record exists).
10. Satirical or humorous content should be classified based on clear intent, not surface keywords.

Confidence guidelines:
- 0.9-1.0: Very clear, unambiguous classification
- 0.7-0.8: Confident but some nuance
- 0.5-0.6: Uncertain, could go either way (consider classifying as neutral instead)
- Below 0.5: You should classify as neutral

Severity scoring (nuanced — not just category-based):
- For negative categories, provide a severity_score from 1-10:
  - 10: Extremely severe (e.g., convicted of violent crime, confirmed hate group leader)
  - 7-9: Very concerning (e.g., DUI arrest, sexual harassment allegation with evidence)
  - 4-6: Moderately concerning (e.g., public argument, controversial opinion, old misdemeanor)
  - 1-3: Mildly concerning (e.g., excessive profanity, unprofessional photo)
- For positive categories, severity_score represents strength:
  - 10: Major achievement (Nobel prize, Fortune 500 CEO, major humanitarian award)
  - 7-9: Significant (published author, keynote speaker, patent holder)
  - 4-6: Moderate (promoted, graduated, volunteered)
  - 1-3: Minor (tutorial post, small donation, participated in event)

Respond with ONLY a JSON object (no markdown, no code fences):
{"category": "...", "confidence": 0.0-1.0, "severity_score": 1-10, "reasoning": "brief explanation"}
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

        # Apply nuanced severity scaling
        severity_score = int(result.get("severity_score", 5))
        severity_score = max(1, min(10, severity_score))
        severity_mult = severity_score / 5.0  # 1=0.2x, 5=1.0x, 10=2.0x
        adjusted_impact = base_impact * severity_mult

        return ClassificationResult(
            category=category,
            severity=severity,
            confidence=confidence,
            title=f"{severity.title()} content detected from {source}",
            description=f"AI classified as '{category}' ({confidence:.0%} confidence, severity {severity_score}/10). Snippet: \"{snippet}\"",
            base_score_impact=adjusted_impact,
        )
    except Exception as e:
        logger.warning(f"OpenAI classification failed: {e}")
        return None


# Model preference order for interactive classification (user-facing, few items)
_ANTHROPIC_MODELS = [
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

# Fast model for bulk classification (passive scans with 50-100+ items)
_ANTHROPIC_BULK_MODEL = "claude-haiku-4-5"


async def _classify_with_anthropic(text: str, source: str) -> Optional[ClassificationResult]:
    """Classify content using Anthropic's Claude API. Tries Sonnet first, falls back to Haiku."""
    for model in _ANTHROPIC_MODELS:
        result = await _try_anthropic_model(text, source, model)
        if result is not None:
            return result
    return None


async def _try_anthropic_model(text: str, source: str, model: str) -> Optional[ClassificationResult]:
    """Try classification with a specific Anthropic model."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 200,
                    "system": LLM_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": f"Platform: {source}\nContent: {text[:2000]}"},
                    ],
                },
            )

        if response.status_code == 404:
            # Model not available on this API key — try next model
            logger.info(f"Anthropic model {model} not available, trying fallback")
            return None
        if response.status_code != 200:
            logger.warning(f"Anthropic API error ({model}): {response.status_code}")
            return None

        data = response.json()
        content = data["content"][0]["text"].strip()

        # Handle potential markdown code fences in response
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        result = json.loads(content)
        category = result.get("category", "neutral")
        confidence = float(result.get("confidence", 0.5))

        if category not in CATEGORY_WEIGHTS:
            category = "neutral"

        # Low confidence — default to neutral to avoid false positives
        if confidence < 0.5:
            category = "neutral"

        severity = SEVERITY_MAP.get(category, "neutral")
        base_impact = CATEGORY_WEIGHTS.get(category, 0.0)
        snippet = text[:80] + "..." if len(text) > 80 else text

        # Apply nuanced severity scaling (guard against None values)
        raw_severity = result.get("severity_score")
        severity_score = int(raw_severity) if raw_severity is not None else 5
        severity_score = max(1, min(10, severity_score))
        severity_mult = severity_score / 5.0  # 1=0.2x, 5=1.0x, 10=2.0x
        adjusted_impact = base_impact * severity_mult

        return ClassificationResult(
            category=category,
            severity=severity,
            confidence=confidence,
            title=f"{severity.title()} content detected from {source}",
            description=f"AI classified as '{category}' ({confidence:.0%} confidence, severity {severity_score}/10). Snippet: \"{snippet}\"",
            base_score_impact=adjusted_impact,
        )
    except json.JSONDecodeError:
        logger.warning(f"Anthropic returned non-JSON response ({model})")
        return None
    except Exception as e:
        logger.warning(f"Anthropic classification failed ({model}): {e}")
        return None


async def classify_content_llm(
    text: str,
    source: str,
    url: Optional[str] = None,
    engagement_count: int = 0,
    bulk: bool = False,
) -> ClassificationResult:
    """
    Classify content using LLM if available, falling back to rules.
    This is the async version that should be used when an LLM key is configured.

    Args:
        bulk: If True, use the faster/cheaper Haiku model for bulk classification
              (passive scans with many items). Default False uses Sonnet for accuracy.
    """
    # Try LLM classification first
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        if bulk:
            # Use Haiku directly for bulk classification (10x faster, avoids rate limits)
            result = await _try_anthropic_model(text, source, _ANTHROPIC_BULK_MODEL)
        else:
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


# ============================================================
# IMAGE / VIDEO CONTENT ANALYSIS
# ============================================================

IMAGE_ANALYSIS_PROMPT = """You are analyzing an image found in search results or social media for CloakHaven digital reputation scoring.

Describe what you see in the image and classify it using the same categories as text content:
- Is there anything problematic (hate symbols, explicit content, illegal activity, substance abuse)?
- Is there anything positive (professional events, awards, community service)?
- Is it neutral (normal photo, selfie, landscape, food)?

Respond with ONLY a JSON object:
{"category": "...", "confidence": 0.0-1.0, "severity_score": 1-10, "description": "brief description of what's in the image"}
"""


async def classify_image_content(
    image_url: str,
    source: str = "image",
    context: str = "",
) -> Optional[ClassificationResult]:
    """
    Classify an image using OpenAI's vision API (GPT-4o supports image input).

    Falls back to None if no vision-capable API key is available,
    letting the caller decide how to handle unclassified images.
    """
    if not settings.OPENAI_API_KEY:
        return None

    try:
        messages = [
            {"role": "system", "content": IMAGE_ANALYSIS_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Source: {source}. Context: {context[:500]}"},
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
                ],
            },
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
            )

        if response.status_code != 200:
            logger.warning("OpenAI Vision API error: %d", response.status_code)
            return None

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON response
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        result = json.loads(content)
        category = result.get("category", "neutral")
        confidence = float(result.get("confidence", 0.5))
        description = result.get("description", "Image content")

        if category not in CATEGORY_WEIGHTS:
            category = "neutral"

        if confidence < 0.5:
            category = "neutral"

        severity = SEVERITY_MAP.get(category, "neutral")
        base_impact = CATEGORY_WEIGHTS.get(category, 0.0)

        severity_score = int(result.get("severity_score", 5))
        severity_score = max(1, min(10, severity_score))
        severity_mult = severity_score / 5.0
        adjusted_impact = base_impact * severity_mult

        return ClassificationResult(
            category=category,
            severity=severity,
            confidence=confidence,
            title=f"Image content from {source}",
            description=f"Image analysis: {description[:300]}. Category: '{category}' ({confidence:.0%} confidence).",
            base_score_impact=adjusted_impact,
        )

    except json.JSONDecodeError:
        logger.warning("OpenAI Vision returned non-JSON response")
        return None
    except Exception as e:
        logger.warning("Image classification failed: %s", e)
        return None
