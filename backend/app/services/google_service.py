"""
Web Search Integration Service

Scans the web for a person's digital footprint using SerpAPI (Google search results).
Falls back gracefully if API key is not configured.
Processes results through the content classifier to create findings.
"""

import asyncio
import logging
import uuid
from typing import Optional
from urllib.parse import urlparse
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.finding import Finding
from app.services.content_classifier import classify_content_llm

logger = logging.getLogger("cloakhaven.google")

SERPAPI_BASE = "https://serpapi.com/search.json"

# Map URL domains to platform source names
DOMAIN_TO_SOURCE: dict[str, str] = {
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "facebook.com": "facebook",
    "www.facebook.com": "facebook",
    "m.facebook.com": "facebook",
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
    "reddit.com": "reddit",
    "www.reddit.com": "reddit",
    "old.reddit.com": "reddit",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
}


def _detect_source(url: str) -> str:
    """Detect the platform source from a URL domain."""
    try:
        domain = urlparse(url).netloc.lower()
        return DOMAIN_TO_SOURCE.get(domain, "google")
    except Exception:
        return "google"


class GoogleServiceError(Exception):
    pass


async def search_web(query: str, num_results: int = 10) -> list[dict]:
    """Execute a web search via SerpAPI (returns Google results)."""
    if not settings.SERPAPI_API_KEY:
        raise GoogleServiceError("SerpAPI not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            SERPAPI_BASE,
            params={
                "api_key": settings.SERPAPI_API_KEY,
                "engine": "google",
                "q": query,
                "num": min(num_results, 10),
            },
        )

    if response.status_code == 401:
        raise GoogleServiceError("SerpAPI: invalid API key")
    if response.status_code == 429:
        raise GoogleServiceError("SerpAPI: rate limit exceeded")
    if response.status_code != 200:
        raise GoogleServiceError(f"SerpAPI error: {response.status_code}")

    data = response.json()
    organic = data.get("organic_results", [])

    results = []
    for item in organic:
        results.append({
            "link": item.get("link", ""),
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
        })
    return results


async def _classify_result(
    item: dict,
    semaphore: asyncio.Semaphore,
) -> Optional[dict]:
    """Classify a single search result with rate-limited LLM call."""
    url = item.get("link", "")
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    source = _detect_source(url)

    combined_text = f"{title} {snippet}"
    async with semaphore:
        classification = await classify_content_llm(
            text=combined_text,
            source=source,
            url=url,
        )

    if classification.category == "neutral":
        return None

    # Confidence threshold — skip low-confidence classifications
    if classification.confidence < 0.6:
        return None

    return {
        "source": source,
        "category": classification.category,
        "severity": classification.severity,
        "title": title,
        "description": classification.description,
        "snippet": snippet,
        "url": url,
        "base_score_impact": classification.base_score_impact,
    }


async def scan_web_presence(
    db: AsyncSession,
    user_id: uuid.UUID,
    full_name: str,
    usernames: Optional[list[str]] = None,
) -> list[Finding]:
    """
    Comprehensive web scan for a person's digital footprint.

    Searches across multiple vectors:
    1. General name search
    2. Platform-specific searches (Instagram, Facebook, LinkedIn, TikTok, Reddit)
    3. Court records and legal mentions
    4. News coverage
    5. Username-based searches

    Each result is classified via LLM and tagged with the correct
    platform source based on the URL domain.
    """
    findings: list[Finding] = []
    seen_urls: set[str] = set()

    # Build comprehensive search queries
    queries = [
        # General web presence
        f'"{full_name}"',
        # Platform-specific searches
        f'"{full_name}" site:instagram.com',
        f'"{full_name}" site:facebook.com',
        f'"{full_name}" site:linkedin.com',
        f'"{full_name}" site:tiktok.com',
        f'"{full_name}" site:reddit.com',
        # Legal / court records
        f'"{full_name}" court records OR arrest OR lawsuit OR indictment',
        # News coverage
        f'"{full_name}" news OR interview OR featured OR announced',
    ]

    # Add username-based searches
    if usernames:
        for username in usernames:
            queries.append(f'"{username}"')

    # Run all searches (sequentially to respect SerpAPI rate limits)
    all_results: list[dict] = []
    for query in queries:
        try:
            results = await search_web(query)
            all_results.extend(results)
        except GoogleServiceError as e:
            logger.warning("Web search failed for query '%s': %s", query, e)
            continue

    # Deduplicate by URL
    unique_results: list[dict] = []
    for item in all_results:
        url = item.get("link", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(item)

    # Classify all results concurrently (max 5 parallel LLM calls)
    semaphore = asyncio.Semaphore(5)
    classification_tasks = [
        _classify_result(item, semaphore)
        for item in unique_results
    ]
    classified = await asyncio.gather(*classification_tasks, return_exceptions=True)

    for result in classified:
        if isinstance(result, Exception):
            logger.warning("Classification error: %s", result)
            continue
        if result is None:
            continue

        source = result["source"]
        source_label = source.title() if source != "google" else "Web"

        finding = Finding(
            user_id=user_id,
            source=source,
            source_type="public",
            category=result["category"],
            severity=result["severity"],
            title=f"{source_label} result: {result['title'][:200]}",
            description=result["description"],
            evidence_snippet=result["snippet"][:500] if result["snippet"] else None,
            evidence_url=result["url"],
            original_date=None,
            platform_engagement_count=0,
            base_score_impact=result["base_score_impact"],
            final_score_impact=result["base_score_impact"],
        )
        db.add(finding)
        findings.append(finding)

    if findings:
        await db.flush()

    logger.info(
        "Web scan for '%s': %d queries, %d unique results, %d findings",
        full_name, len(queries), len(unique_results), len(findings),
    )
    return findings
