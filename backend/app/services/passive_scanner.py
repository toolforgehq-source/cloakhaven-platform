"""
Passive Scanning Pipeline

The core of "score anyone without their input." This is the equivalent
of a credit bureau — it pulls data from multiple sources using just a
name and optional identifiers, then computes a score.

Flow:
1. Identity resolution (PeopleDataLabs) — discover social handles
2. Web presence scan (SerpAPI) — expanded queries including news, images
3. Twitter mention search — what people say ABOUT the person
4. YouTube search by name — channel discovery
5. Public records (CourtListener, SEC, USPTO, Semantic Scholar)
6. Name disambiguation — LLM verifies each finding is about the right person
7. Cross-platform corroboration — findings from multiple sources boost confidence
8. Score calculation — compute score with enhanced accuracy formula

No user account required. Results stored on PublicProfile.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.public_profile import PublicProfile
from app.services.content_classifier import classify_content_llm
from app.services.name_disambiguator import disambiguate_result, _is_common_name
from app.services.public_data_sources import search_all_public_records, PublicRecord

logger = logging.getLogger(__name__)


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class PassiveFinding:
    """A finding discovered through passive scanning (no user account needed)."""
    source: str
    source_type: str  # "public"
    category: str
    severity: str
    title: str
    description: str
    evidence_snippet: Optional[str] = None
    evidence_url: Optional[str] = None
    original_date: Optional[str] = None
    engagement_count: int = 0
    base_score_impact: float = 0.0
    confidence: float = 0.5
    disambiguation_verified: bool = False
    corroboration_count: int = 1  # how many sources found this


@dataclass
class PassiveScanResult:
    """Result of a full passive scan."""
    profile_id: uuid.UUID
    name: str
    findings: list[PassiveFinding] = field(default_factory=list)
    sources_scanned: list[str] = field(default_factory=list)
    identity_confidence: float = 0.0
    enrichment_data: Optional[dict] = None
    overall_score: int = 850
    social_media_score: int = 850
    web_presence_score: int = 850
    posting_behavior_score: int = 850
    accuracy_pct: float = 0.0
    scan_duration_seconds: float = 0.0


# ============================================================
# SERPAPI EXPANDED QUERIES
# ============================================================

SERPAPI_BASE = "https://serpapi.com/search.json"


async def _serpapi_search(query: str, engine: str = "google", num: int = 10) -> list[dict]:
    """Execute a SerpAPI search with the given engine."""
    if not settings.SERPAPI_API_KEY:
        return []
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "api_key": settings.SERPAPI_API_KEY,
                "engine": engine,
                "q": query,
            }
            if engine == "google":
                params["num"] = min(num, 10)
            elif engine == "google_news":
                params["num"] = min(num, 10)

            response = await client.get(SERPAPI_BASE, params=params)

        if response.status_code != 200:
            logger.warning("SerpAPI %s error for '%s': %d", engine, query[:50], response.status_code)
            return []

        data = response.json()

        if engine == "google_news":
            return [
                {
                    "link": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", "") or item.get("date", ""),
                    "source_name": item.get("source", {}).get("name", "") if isinstance(item.get("source"), dict) else "",
                }
                for item in data.get("news_results", [])
            ]
        elif engine == "google":
            return [
                {
                    "link": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                }
                for item in data.get("organic_results", [])
            ]
        return []
    except Exception as e:
        logger.warning("SerpAPI search failed for '%s': %s", query[:50], e)
        return []


async def _expanded_web_search(name: str, context: dict) -> list[dict]:
    """
    Run the expanded set of SerpAPI queries for comprehensive coverage.
    Returns deduplicated results from all queries.
    """
    company = context.get("company", "")
    location = context.get("location", "")

    # Build targeted queries
    queries_google = [
        # Core identity
        f'"{name}"',
        # Platform-specific
        f'"{name}" site:instagram.com',
        f'"{name}" site:facebook.com',
        f'"{name}" site:linkedin.com',
        f'"{name}" site:tiktok.com',
        f'"{name}" site:reddit.com',
        f'"{name}" site:twitter.com OR site:x.com',
        # Professional
        f'"{name}" site:glassdoor.com',
        f'"{name}" site:medium.com OR site:substack.com',
        f'"{name}" site:github.com',
        # Legal / court records
        f'"{name}" arrested OR charged OR convicted OR indictment OR lawsuit',
        f'"{name}" site:courtlistener.com OR site:unicourt.com OR site:pacermonitor.com',
        # Professional achievements
        f'"{name}" award OR recognition OR keynote OR speaker OR published',
        # News coverage
        f'"{name}" news OR interview OR featured OR announced',
    ]

    # Add company-qualified search if available (helps disambiguation)
    if company:
        queries_google.append(f'"{name}" "{company}"')

    # Add location-qualified search
    if location:
        queries_google.append(f'"{name}" "{location}"')

    # Run Google News as separate engine for better news coverage
    news_queries = [
        f'"{name}"',
    ]
    if company:
        news_queries.append(f'"{name}" {company}')

    # Execute all queries concurrently (batched to respect rate limits)
    all_results: list[dict] = []
    seen_urls: set[str] = set()
    sem = asyncio.Semaphore(5)  # Max 5 concurrent SerpAPI calls

    async def _run_google(query: str) -> list[dict]:
        async with sem:
            return await _serpapi_search(query, engine="google", num=10)

    async def _run_news(query: str) -> list[dict]:
        async with sem:
            results = await _serpapi_search(query, engine="google_news", num=10)
            for r in results:
                r["_is_news"] = True
            return results

    tasks = [_run_google(q) for q in queries_google] + [_run_news(q) for q in news_queries]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for batch in batch_results:
        if isinstance(batch, Exception):
            logger.warning("SerpAPI batch error: %s", batch)
            continue
        for r in batch:
            url = r.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)

    return all_results


# ============================================================
# TWITTER MENTION SEARCH
# ============================================================

async def _search_twitter_mentions(name: str) -> list[dict]:
    """Search Twitter for tweets mentioning the person (not their own tweets)."""
    if not settings.TWITTER_BEARER_TOKEN:
        return []

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
                params={
                    "query": f'"{name}" -is:retweet',
                    "max_results": 50,
                    "tweet.fields": "id,text,created_at,public_metrics,author_id",
                },
            )

        if response.status_code == 403:
            logger.info("Twitter search API not available on current plan")
            return []
        if response.status_code != 200:
            logger.warning("Twitter mention search error: %d", response.status_code)
            return []

        data = response.json()
        tweets = data.get("data", [])
        return [
            {
                "text": t.get("text", ""),
                "url": f"https://twitter.com/i/status/{t.get('id', '')}",
                "engagement": sum(t.get("public_metrics", {}).values()) if t.get("public_metrics") else 0,
                "created_at": t.get("created_at", ""),
            }
            for t in tweets
        ]
    except Exception as e:
        logger.warning("Twitter mention search failed: %s", e)
        return []


# ============================================================
# YOUTUBE NAME SEARCH
# ============================================================

async def _search_youtube_by_name(name: str) -> list[dict]:
    """Search YouTube for channels and videos matching the person's name."""
    if not settings.YOUTUBE_API_KEY:
        return []

    import httpx
    results = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for videos mentioning the person
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": settings.YOUTUBE_API_KEY,
                    "q": f'"{name}"',
                    "type": "video",
                    "part": "snippet",
                    "maxResults": 10,
                    "order": "relevance",
                },
            )

        if response.status_code != 200:
            return results

        data = response.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            results.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "url": f"https://youtube.com/watch?v={video_id}" if video_id else "",
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
            })
    except Exception as e:
        logger.warning("YouTube name search failed: %s", e)

    return results


# ============================================================
# SCORING ENGINE FOR PASSIVE SCANS
# ============================================================

BASE_SCORE = 850

# Import scoring constants
from app.services.scoring_engine import (
    CATEGORY_WEIGHTS,
    SEVERITY_MAP,
    SOCIAL_SOURCES,
    WEB_SOURCES,
    SOCIAL_WEIGHT,
    WEB_WEIGHT,
    BEHAVIOR_WEIGHT,
    recency_modifier,
    virality_modifier,
    clamp,
    get_score_color,
    get_score_label,
)


def _calculate_passive_score(findings: list[PassiveFinding]) -> dict:
    """
    Calculate score from passive findings.
    Returns dict with overall_score, component scores, and breakdown.
    """
    social_impact = 0.0
    web_impact = 0.0
    behavior_impact = 0.0

    for finding in findings:
        if finding.category == "neutral":
            continue

        base_impact = finding.base_score_impact

        # Apply corroboration multiplier: findings confirmed by multiple sources
        # are more reliable → stronger impact
        corroboration_mult = 1.0
        if finding.corroboration_count >= 3:
            corroboration_mult = 1.5
        elif finding.corroboration_count >= 2:
            corroboration_mult = 1.25

        # Apply disambiguation confidence: lower confidence → lower impact
        confidence_mult = finding.confidence if finding.disambiguation_verified else 0.7

        final_impact = base_impact * corroboration_mult * confidence_mult

        # Apply virality modifier
        v_mod = virality_modifier(finding.engagement_count)
        final_impact *= v_mod

        # Route to component
        if finding.source in SOCIAL_SOURCES:
            social_impact += final_impact
        elif finding.source in WEB_SOURCES:
            web_impact += final_impact
        else:
            web_impact += final_impact  # Default web for passive scans

    social_score = int(clamp(BASE_SCORE + social_impact, 0, 1000))
    web_score = int(clamp(BASE_SCORE + web_impact, 0, 1000))
    behavior_score = int(clamp(BASE_SCORE + behavior_impact, 0, 1000))

    overall = (
        social_score * SOCIAL_WEIGHT
        + web_score * WEB_WEIGHT
        + behavior_score * BEHAVIOR_WEIGHT
    )
    overall_score = int(clamp(overall, 0, 1000))

    return {
        "overall_score": overall_score,
        "social_media_score": social_score,
        "web_presence_score": web_score,
        "posting_behavior_score": behavior_score,
    }


def _calculate_passive_accuracy(
    sources_scanned: list[str],
    identity_confidence: float,
    findings_count: int,
) -> float:
    """
    Enhanced accuracy formula for passive scans.

    accuracy = (
        data_sources_scanned / total_possible × 60%
        + identity_confidence × 25%
        + findings_depth × 15%
    )
    """
    # Breadth: how many source types did we scan?
    possible_sources = {
        "serpapi_web", "serpapi_news", "twitter_mentions",
        "youtube_search", "enrichment", "courtlistener",
        "sec_edgar", "uspto", "semantic_scholar", "opencorporates",
    }
    scanned_set = set(sources_scanned)
    breadth_score = len(scanned_set & possible_sources) / len(possible_sources) * 100

    # Findings depth: more findings = more statistically meaningful
    if findings_count == 0:
        depth_score = 0.0
    elif findings_count <= 5:
        depth_score = 30.0
    elif findings_count <= 20:
        depth_score = 60.0
    elif findings_count <= 50:
        depth_score = 80.0
    else:
        depth_score = 100.0

    accuracy = (
        breadth_score * 0.60
        + (identity_confidence * 100) * 0.25
        + depth_score * 0.15
    )
    return min(accuracy, 100.0)


# ============================================================
# CROSS-PLATFORM CORROBORATION
# ============================================================

def _apply_corroboration(findings: list[PassiveFinding]) -> list[PassiveFinding]:
    """
    Check if the same finding (similar URL or similar content) appears
    from multiple sources. If so, increase the corroboration count.
    """
    # Group by evidence URL (exact match)
    url_groups: dict[str, list[int]] = {}
    for i, f in enumerate(findings):
        if f.evidence_url:
            normalized = f.evidence_url.rstrip("/").lower()
            if normalized not in url_groups:
                url_groups[normalized] = []
            url_groups[normalized].append(i)

    # Mark corroborated findings
    for indices in url_groups.values():
        if len(indices) > 1:
            for idx in indices:
                findings[idx].corroboration_count = len(indices)

    # Also check for category corroboration (same category from different sources)
    category_sources: dict[str, set[str]] = {}
    for f in findings:
        if f.category != "neutral":
            if f.category not in category_sources:
                category_sources[f.category] = set()
            category_sources[f.category].add(f.source)

    # If a negative category appears from 3+ different sources, boost all findings in that category
    for f in findings:
        if f.category in category_sources:
            source_count = len(category_sources[f.category])
            if source_count >= 3:
                f.corroboration_count = max(f.corroboration_count, source_count)

    return findings


# ============================================================
# MAIN PASSIVE SCAN PIPELINE
# ============================================================

async def run_passive_scan(
    db: AsyncSession,
    name: str,
    email: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    job_title: Optional[str] = None,
) -> PassiveScanResult:
    """
    Run a full passive scan on a person. No user account needed.

    This is the credit-bureau equivalent: given a name and optional identifiers,
    discover everything we can about this person from public sources.
    """
    start_time = datetime.utcnow()
    sources_scanned: list[str] = []
    all_findings: list[PassiveFinding] = []
    identity_confidence = 0.3  # Base confidence from name alone
    enrichment_data: Optional[dict] = None

    # Build context dict for disambiguation
    context = {
        "email": email or "",
        "company": company or "",
        "location": location or "",
        "job_title": job_title or "",
        "linkedin_url": linkedin_url or "",
    }

    # ── 1. Identity Resolution via PeopleDataLabs ──
    enriched_handles: dict[str, str] = {}
    if settings.PEOPLEDATALABS_API_KEY:
        try:
            from app.services.enrichment_service import enrich_person
            enriched = await enrich_person(
                name=name, email=email,
                linkedin_url=linkedin_url, company=company,
            )
            if enriched:
                sources_scanned.append("enrichment")
                identity_confidence = 0.7  # PDL match raises confidence

                # Capture discovered handles
                if enriched.twitter_username:
                    enriched_handles["twitter"] = enriched.twitter_username
                if enriched.github_username:
                    enriched_handles["github"] = enriched.github_username
                for platform, url in enriched.social_profiles.items():
                    enriched_handles[platform] = url

                # Store enrichment context for disambiguation
                if enriched.company:
                    context["company"] = enriched.company
                if enriched.location:
                    context["location"] = enriched.location
                if enriched.job_title:
                    context["job_title"] = enriched.job_title
                if enriched.linkedin_url:
                    context["linkedin_url"] = enriched.linkedin_url

                # If email was confirmed via enrichment, highest confidence
                if email and enriched.email:
                    identity_confidence = 0.9

                enrichment_data = {
                    "name": enriched.name,
                    "company": enriched.company,
                    "job_title": enriched.job_title,
                    "location": enriched.location,
                    "handles_discovered": enriched_handles,
                    "source": enriched.source,
                }

                logger.info(
                    "Enrichment for '%s': found %d handles, confidence=%.2f",
                    name, len(enriched_handles), identity_confidence,
                )
        except Exception as e:
            logger.warning("Enrichment failed for '%s': %s", name, e)

    # ── 2-5. Run all data sources CONCURRENTLY for speed ──
    web_task = asyncio.create_task(_expanded_web_search(name, context))
    twitter_task = asyncio.create_task(_search_twitter_mentions(name))
    youtube_task = asyncio.create_task(_search_youtube_by_name(name))
    public_records_task = asyncio.create_task(search_all_public_records(name))

    # Wait for all with a global timeout of 45 seconds
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                web_task, twitter_task, youtube_task, public_records_task,
                return_exceptions=True,
            ),
            timeout=45.0,
        )
        web_results = results[0] if not isinstance(results[0], Exception) else []
        twitter_mentions = results[1] if not isinstance(results[1], Exception) else []
        youtube_results = results[2] if not isinstance(results[2], Exception) else []
        public_records = results[3] if not isinstance(results[3], Exception) else []

        for i, label in enumerate(["web", "twitter", "youtube", "public_records"]):
            if isinstance(results[i], Exception):
                logger.warning("Data source '%s' failed: %s", label, results[i])
    except asyncio.TimeoutError:
        logger.warning("Passive scan data gathering timed out after 45s for '%s'", name)
        web_results = web_task.result() if web_task.done() and not web_task.cancelled() else []
        twitter_mentions = twitter_task.result() if twitter_task.done() and not twitter_task.cancelled() else []
        youtube_results = youtube_task.result() if youtube_task.done() and not youtube_task.cancelled() else []
        public_records = public_records_task.result() if public_records_task.done() and not public_records_task.cancelled() else []
        # Cancel anything still running
        for t in [web_task, twitter_task, youtube_task, public_records_task]:
            if not t.done():
                t.cancel()

    if web_results:
        sources_scanned.append("serpapi_web")
        if any(r.get("_is_news") for r in web_results):
            sources_scanned.append("serpapi_news")
    if twitter_mentions:
        sources_scanned.append("twitter_mentions")
    if youtube_results:
        sources_scanned.append("youtube_search")
    for record in public_records:
        if record.source not in sources_scanned:
            sources_scanned.append(record.source)

    # ── 6. Classify + Disambiguate all results ──
    # Process web results
    need_disambiguation = _is_common_name(name) and identity_confidence < 0.85
    semaphore = asyncio.Semaphore(5)  # Max 5 parallel LLM calls

    async def _process_web_result(item: dict) -> Optional[PassiveFinding]:
        url = item.get("link", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if not title and not snippet:
            return None

        # Disambiguate if needed
        is_verified = False
        confidence = identity_confidence
        if need_disambiguation:
            async with semaphore:
                disambig = await disambiguate_result(
                    target_name=name,
                    target_context=context,
                    result_title=title,
                    result_snippet=snippet,
                    result_url=url,
                )
            if not disambig.is_match or disambig.confidence < 0.5:
                return None
            is_verified = True
            confidence = disambig.confidence
        else:
            is_verified = True  # High identity confidence, no disambiguation needed

        # Classify content
        from app.services.google_service import _detect_source
        source = _detect_source(url)
        combined_text = f"{title} {snippet}"

        async with semaphore:
            classification = await classify_content_llm(
                text=combined_text,
                source=source,
                url=url,
            )

        if classification.category == "neutral" and classification.confidence > 0.7:
            return None

        return PassiveFinding(
            source=source,
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"{title[:200]}",
            description=classification.description,
            evidence_snippet=snippet[:500] if snippet else None,
            evidence_url=url,
            base_score_impact=classification.base_score_impact,
            confidence=confidence,
            disambiguation_verified=is_verified,
        )

    # Process Twitter mentions
    async def _process_tweet(tweet: dict) -> Optional[PassiveFinding]:
        text = tweet.get("text", "")
        if not text:
            return None

        async with semaphore:
            classification = await classify_content_llm(
                text=text,
                source="twitter",
                url=tweet.get("url", ""),
            )

        if classification.category == "neutral":
            return None

        return PassiveFinding(
            source="twitter",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"Twitter mention: {text[:100]}",
            description=classification.description,
            evidence_snippet=text[:500],
            evidence_url=tweet.get("url", ""),
            engagement_count=tweet.get("engagement", 0),
            base_score_impact=classification.base_score_impact,
            confidence=identity_confidence,
            disambiguation_verified=not need_disambiguation,
        )

    # Process YouTube results
    async def _process_youtube(video: dict) -> Optional[PassiveFinding]:
        title = video.get("title", "")
        desc = video.get("description", "")
        combined = f"{title}. {desc}".strip()
        if not combined or combined == ".":
            return None

        # Disambiguate YouTube results
        if need_disambiguation:
            async with semaphore:
                disambig = await disambiguate_result(
                    target_name=name,
                    target_context=context,
                    result_title=title,
                    result_snippet=desc[:200],
                    result_url=video.get("url", ""),
                )
            if not disambig.is_match or disambig.confidence < 0.5:
                return None

        async with semaphore:
            classification = await classify_content_llm(
                text=combined,
                source="youtube",
                url=video.get("url", ""),
            )

        if classification.category == "neutral":
            return None

        return PassiveFinding(
            source="youtube",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"YouTube: {title[:200]}",
            description=classification.description,
            evidence_snippet=combined[:500],
            evidence_url=video.get("url", ""),
            base_score_impact=classification.base_score_impact,
            confidence=identity_confidence,
            disambiguation_verified=True,
        )

    # Process public records
    def _process_public_record(record: PublicRecord) -> PassiveFinding:
        # Map record types to finding categories
        category_map = {
            "court_case": "court_records",
            "corporate_filing": "positive_press",
            "patent": "professional_achievement",
            "publication": "constructive_content",
            "business": "professional_achievement",
        }
        category = category_map.get(record.record_type, "neutral")
        severity = SEVERITY_MAP.get(category, "neutral")
        base_impact = CATEGORY_WEIGHTS.get(category, 0.0)

        return PassiveFinding(
            source=record.source,
            source_type="public",
            category=category,
            severity=severity,
            title=record.title[:300],
            description=record.description[:500],
            evidence_snippet=record.description[:500],
            evidence_url=record.url,
            original_date=record.date,
            base_score_impact=base_impact,
            confidence=record.relevance_score,
            disambiguation_verified=False,  # Public records need name match verification
        )

    # Run all classification tasks concurrently
    tasks = []
    tasks.extend([_process_web_result(r) for r in web_results])
    tasks.extend([_process_tweet(t) for t in twitter_mentions])
    tasks.extend([_process_youtube(v) for v in youtube_results])

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Classification task error: %s", result)
                continue
            if result is not None:
                all_findings.append(result)

    # Add public records (no async classification needed)
    for record in public_records:
        finding = _process_public_record(record)
        if finding.category != "neutral":
            all_findings.append(finding)

    # ── 7. Cross-platform corroboration ──
    all_findings = _apply_corroboration(all_findings)

    # ── 8. Calculate score ──
    scores = _calculate_passive_score(all_findings)
    accuracy = _calculate_passive_accuracy(
        sources_scanned=sources_scanned,
        identity_confidence=identity_confidence,
        findings_count=len(all_findings),
    )

    # Build findings summary for storage
    category_summary: dict[str, int] = {}
    for f in all_findings:
        if f.category != "neutral":
            category_summary[f.category] = category_summary.get(f.category, 0) + 1

    # ── 9. Persist to PublicProfile ──
    # Check if profile already exists
    existing = await db.execute(
        select(PublicProfile).where(PublicProfile.lookup_name == name)
    )
    profile = existing.scalar_one_or_none()

    scan_duration = (datetime.utcnow() - start_time).total_seconds()

    if profile:
        profile.public_score = scores["overall_score"]
        profile.score_accuracy_pct = round(accuracy, 1)
        profile.last_scanned_at = datetime.utcnow()
        profile.identity_confidence = round(identity_confidence, 3)
        profile.match_context = context
        profile.sources_scanned = {"sources": sources_scanned}
        profile.social_media_score = scores["social_media_score"]
        profile.web_presence_score = scores["web_presence_score"]
        profile.posting_behavior_score = scores["posting_behavior_score"]
        profile.total_findings_count = len(all_findings)
        profile.scan_duration_seconds = round(scan_duration, 1)
        profile.public_findings_summary = {
            "categories": category_summary,
            "total_findings": len(all_findings),
            "sources_scanned": sources_scanned,
            "identity_confidence": round(identity_confidence, 2),
            "enrichment_data": enrichment_data,
            "findings": [
                {
                    "source": f.source,
                    "category": f.category,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description[:200],
                    "evidence_url": f.evidence_url,
                    "confidence": round(f.confidence, 2),
                    "corroboration_count": f.corroboration_count,
                    "base_score_impact": f.base_score_impact,
                }
                for f in all_findings[:100]  # Cap at 100 findings for storage
            ],
        }
    else:
        profile = PublicProfile(
            lookup_name=name,
            lookup_username=name.lower().replace(" ", "_"),
            public_score=scores["overall_score"],
            score_accuracy_pct=round(accuracy, 1),
            last_scanned_at=datetime.utcnow(),
            identity_confidence=round(identity_confidence, 3),
            match_context=context,
            sources_scanned={"sources": sources_scanned},
            social_media_score=scores["social_media_score"],
            web_presence_score=scores["web_presence_score"],
            posting_behavior_score=scores["posting_behavior_score"],
            total_findings_count=len(all_findings),
            scan_duration_seconds=round(scan_duration, 1),
            public_findings_summary={
                "categories": category_summary,
                "total_findings": len(all_findings),
                "sources_scanned": sources_scanned,
                "identity_confidence": round(identity_confidence, 2),
                "enrichment_data": enrichment_data,
                "findings": [
                    {
                        "source": f.source,
                        "category": f.category,
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description[:200],
                        "evidence_url": f.evidence_url,
                        "confidence": round(f.confidence, 2),
                        "corroboration_count": f.corroboration_count,
                        "base_score_impact": f.base_score_impact,
                    }
                    for f in all_findings[:100]
                ],
            },
        )
        db.add(profile)

    await db.flush()

    logger.info(
        "Passive scan for '%s': %d findings from %d sources, score=%d, accuracy=%.1f%%, took %.1fs",
        name, len(all_findings), len(sources_scanned),
        scores["overall_score"], accuracy, scan_duration,
    )

    return PassiveScanResult(
        profile_id=profile.id,
        name=name,
        findings=all_findings,
        sources_scanned=sources_scanned,
        identity_confidence=identity_confidence,
        enrichment_data=enrichment_data,
        overall_score=scores["overall_score"],
        social_media_score=scores["social_media_score"],
        web_presence_score=scores["web_presence_score"],
        posting_behavior_score=scores["posting_behavior_score"],
        accuracy_pct=round(accuracy, 1),
        scan_duration_seconds=round(scan_duration, 1),
    )
