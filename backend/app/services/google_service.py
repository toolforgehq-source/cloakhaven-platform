"""
Google Custom Search Integration Service

Scans the web for a person's digital footprint using Google Custom Search API.
Processes results through the content classifier to create findings.
"""

import uuid
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.finding import Finding
from app.services.content_classifier import classify_web_result
from app.services.scoring_engine import CATEGORY_WEIGHTS


GOOGLE_SEARCH_BASE = "https://www.googleapis.com/customsearch/v1"


class GoogleServiceError(Exception):
    pass


async def search_web(query: str, num_results: int = 10) -> list[dict]:
    """Execute a Google Custom Search query."""
    if not settings.GOOGLE_API_KEY or not settings.GOOGLE_SEARCH_ENGINE_ID:
        raise GoogleServiceError("Google Custom Search API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_SEARCH_BASE,
            params={
                "key": settings.GOOGLE_API_KEY,
                "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
                "q": query,
                "num": min(num_results, 10),
            },
        )

    if response.status_code == 403:
        raise GoogleServiceError("Google API quota exceeded or invalid credentials")
    if response.status_code != 200:
        raise GoogleServiceError(f"Google API error: {response.status_code}")

    data = response.json()
    return data.get("items", [])


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
        except GoogleServiceError:
            # If API fails, skip this query but continue with others
            continue

        for item in results:
            url = item.get("link", "")

            # Skip duplicate URLs
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Classify the search result
            classification = classify_web_result(
                title=title,
                snippet=snippet,
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
                original_date=None,  # Google results don't always have dates
                platform_engagement_count=0,
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings
