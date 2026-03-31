"""
LLM-powered Name Disambiguation Service

Before attributing any finding to a person, this service verifies
that the search result is actually about the target individual — not
a different person with the same name.

This is critical for accuracy: "John Smith VP at Acme Corp" should not
get findings attributed from a different John Smith who is a plumber.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DisambiguationResult:
    """Result of verifying whether content is about the target person."""
    is_match: bool
    confidence: float  # 0.0-1.0
    reasoning: str


DISAMBIGUATION_PROMPT = """You are verifying whether a search result is about a specific person.

TARGET PERSON:
{target_description}

SEARCH RESULT:
Title: {title}
Snippet: {snippet}
URL: {url}

Is this search result about the target person described above, or a different person with the same/similar name?

Consider:
1. Does the job title, company, or industry match?
2. Does the location match?
3. Are there any identifying details (education, age, specific projects) that confirm or deny the match?
4. If the search result is generic (e.g., a social media profile with just a name), it could be anyone — mark as uncertain.
5. News articles about a specific person at a specific company are high confidence.
6. Common names (John Smith, Maria Garcia) need MORE corroborating details to confirm.

Respond with ONLY a JSON object (no markdown, no code fences):
{{"is_match": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

Confidence guidelines:
- 0.9-1.0: Multiple identifying details match (name + company + role, or name + specific event)
- 0.7-0.8: Name matches and context is consistent but not confirmed
- 0.5-0.6: Could be this person or someone else — insufficient info
- Below 0.5: Likely a different person
"""


async def disambiguate_result(
    target_name: str,
    target_context: dict,
    result_title: str,
    result_snippet: str,
    result_url: str,
) -> DisambiguationResult:
    """
    Use LLM to verify whether a search result is about the target person.

    target_context can include:
    - email, company, job_title, location, linkedin_url, etc.
    """
    # Build target description from available context
    parts = [f"Name: {target_name}"]
    if target_context.get("email"):
        parts.append(f"Email: {target_context['email']}")
    if target_context.get("company"):
        parts.append(f"Company: {target_context['company']}")
    if target_context.get("job_title"):
        parts.append(f"Job Title: {target_context['job_title']}")
    if target_context.get("location"):
        parts.append(f"Location: {target_context['location']}")
    if target_context.get("linkedin_url"):
        parts.append(f"LinkedIn: {target_context['linkedin_url']}")
    if target_context.get("industry"):
        parts.append(f"Industry: {target_context['industry']}")

    target_description = "\n".join(parts)

    prompt = DISAMBIGUATION_PROMPT.format(
        target_description=target_description,
        title=result_title[:300],
        snippet=result_snippet[:500],
        url=result_url[:200],
    )

    # Try Anthropic first, then OpenAI
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        result = await _disambiguate_anthropic(prompt)
        if result:
            return result
    if settings.OPENAI_API_KEY:
        result = await _disambiguate_openai(prompt)
        if result:
            return result

    # Fallback: assume match with low confidence for non-common names
    is_common = _is_common_name(target_name)
    return DisambiguationResult(
        is_match=not is_common,
        confidence=0.3 if is_common else 0.5,
        reasoning="No LLM available for disambiguation; using heuristic",
    )


async def _disambiguate_anthropic(prompt: str) -> Optional[DisambiguationResult]:
    """Disambiguate using Anthropic Claude."""
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
                    "model": "claude-haiku-4-5",
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

        if response.status_code != 200:
            return None

        data = response.json()
        content = data["content"][0]["text"].strip()
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        result = json.loads(content)
        return DisambiguationResult(
            is_match=bool(result.get("is_match", False)),
            confidence=float(result.get("confidence", 0.5)),
            reasoning=result.get("reasoning", ""),
        )
    except Exception as e:
        logger.warning("Anthropic disambiguation failed: %s", e)
        return None


async def _disambiguate_openai(prompt: str) -> Optional[DisambiguationResult]:
    """Disambiguate using OpenAI."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 150,
                },
            )

        if response.status_code != 200:
            return None

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        result = json.loads(content)
        return DisambiguationResult(
            is_match=bool(result.get("is_match", False)),
            confidence=float(result.get("confidence", 0.5)),
            reasoning=result.get("reasoning", ""),
        )
    except Exception as e:
        logger.warning("OpenAI disambiguation failed: %s", e)
        return None


# Common names that need extra disambiguation
_COMMON_FIRST_NAMES = {
    "james", "john", "robert", "michael", "david", "william", "richard",
    "joseph", "thomas", "charles", "mary", "patricia", "jennifer", "linda",
    "elizabeth", "barbara", "susan", "jessica", "sarah", "karen",
    "maria", "jose", "juan", "carlos", "miguel", "mohammed", "ahmed",
    "wei", "li", "zhang", "wang", "chen",
}

_COMMON_LAST_NAMES = {
    "smith", "johnson", "williams", "brown", "jones", "garcia", "miller",
    "davis", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez",
    "wilson", "anderson", "thomas", "taylor", "moore", "jackson", "martin",
    "lee", "kim", "park", "wang", "li", "zhang", "chen", "kumar", "singh",
    "patel",
}


def _is_common_name(name: str) -> bool:
    """Check if a name is common enough to require extra disambiguation."""
    parts = name.lower().split()
    if len(parts) < 2:
        return True  # Single name is always ambiguous

    first = parts[0]
    last = parts[-1]

    return first in _COMMON_FIRST_NAMES or last in _COMMON_LAST_NAMES
