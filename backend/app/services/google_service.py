"""
Web Search Integration Service

Scans the web for a person's digital footprint using SerpAPI (Google search results).
Falls back gracefully if API key is not configured.
Processes results through the content classifier to create findings.
"""

import logging
import uuid
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.finding import Finding
from app.services.content_classifier import classify_content_llm

logger = logging.getLogger("cloakhaven.google")

SERPAPI_BASE = "https://serpapi.com/search.json"


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


async def scan_web_presence(
    db: AsyncSession,
    user_id: uuid.UUID,
    full_name: str,
    usernames: Optional[list[str]] = None,
) -> list[Finding]:
    """
    Scan the web for a person's digital footprint:
    1. Search by full name
    2. Search by known usernames
    3. Classify each result
    4. Create findings
    """
    findings: list[Finding] = []
    seen_urls: set[str] = set()

    # Build search queries
    queries = [f'"{full_name}"']
    if usernames:
        for username in usernames:
            queries.append(f'"{username}"')
            queries.append(f'"{full_name}" {username}')

    for query in queries:
        try:
            results = await search_web(query)
        except GoogleServiceError as e:
            logger.warning("Web search failed for query '%s': %s", query, e)
            continue

        for item in results:
            url = item.get("link", "")

            # Skip duplicate URLs
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Classify the search result using LLM if available
            combined_text = f"{title} {snippet}"
            classification = await classify_content_llm(
                text=combined_text,
                source="google",
                url=url,
            )

            # Skip neutral content
            if classification.category == "neutral":
                continue

            finding = Finding(
                user_id=user_id,
                source="google",
                source_type="public",
                category=classification.category,
                severity=classification.severity,
                title=f"Web result: {title[:200]}",
                description=classification.description,
                evidence_snippet=snippet[:500] if snippet else None,
                evidence_url=url,
                original_date=None,
                platform_engagement_count=0,
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings
