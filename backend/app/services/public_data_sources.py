"""
Public Data Sources — Free APIs

Pulls data from free public record databases to enrich scoring:
- CourtListener (federal court records)
- SEC EDGAR (corporate filings)
- USPTO (patents)
- Semantic Scholar (academic publications)
- OpenCorporates (business registrations)

Each source is independent — if one fails, the others continue.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PublicRecord:
    """A record found from a public data source."""
    source: str  # courtlistener, sec_edgar, uspto, semantic_scholar, opencorporates
    record_type: str  # court_case, corporate_filing, patent, publication, business
    title: str
    description: str
    url: str
    date: Optional[str] = None
    relevance_score: float = 0.5


# ============================================================
# COURTLISTENER — Federal Court Records (free)
# https://www.courtlistener.com/api/rest/v3/
# ============================================================

async def search_court_records(name: str, max_results: int = 10) -> list[PublicRecord]:
    """Search CourtListener for federal court cases involving a person."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://www.courtlistener.com/api/rest/v4/search/",
                params={
                    "q": f'"{name}"',
                    "type": "o",  # opinions
                    "order_by": "score desc",
                    "page_size": min(max_results, 20),
                },
                headers={"User-Agent": "CloakHaven/1.0 (digital reputation scoring)"},
            )

        if response.status_code != 200:
            logger.warning("CourtListener API error: %d", response.status_code)
            return records

        data = response.json()
        seen_case_names: set[str] = set()  # Deduplicate by case name
        for result in data.get("results", []):
            case_name = result.get("caseName", "") or result.get("case_name", "")
            court = result.get("court", "")
            date_filed = result.get("dateFiled", "") or result.get("date_filed", "")
            absolute_url = result.get("absolute_url", "")
            snippet = result.get("snippet", "") or ""

            if not case_name:
                continue

            # Deduplicate: skip if we've already seen this case name
            case_key = case_name.strip().lower()
            if case_key in seen_case_names:
                continue
            seen_case_names.add(case_key)

            url = f"https://www.courtlistener.com{absolute_url}" if absolute_url else ""

            records.append(PublicRecord(
                source="courtlistener",
                record_type="court_case",
                title=f"Court case: {case_name[:200]}",
                description=f"Court: {court}. {snippet[:300]}",
                url=url,
                date=date_filed,
            ))

    except Exception as e:
        logger.warning("CourtListener search failed for '%s': %s", name, e)

    return records


# ============================================================
# SEC EDGAR — Corporate Filings (free)
# https://efts.sec.gov/LATEST/search-index?q=
# ============================================================

async def search_sec_filings(name: str, max_results: int = 10) -> list[PublicRecord]:
    """Search SEC EDGAR for corporate filings mentioning a person."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{name}"',
                    "dateRange": "custom",
                    "startdt": "2000-01-01",
                    "enddt": "2026-12-31",
                    "forms": "10-K,10-Q,8-K,DEF 14A,S-1",
                },
                headers={
                    "User-Agent": "CloakHaven hello@cloakhaven.com",
                    "Accept": "application/json",
                },
            )

        if response.status_code != 200:
            # Try the full-text search endpoint as fallback
            response = await _sec_fulltext_search(name)
            if response is None:
                return records

        data = response.json()
        hits = data.get("hits", {}).get("hits", [])

        for hit in hits[:max_results]:
            source = hit.get("_source", {})
            filing_type = source.get("file_type", "") or source.get("form_type", "")
            entity = source.get("entity_name", "") or source.get("display_names", [""])[0] if source.get("display_names") else ""
            filed_at = source.get("file_date", "") or source.get("period_of_report", "")
            file_num = source.get("file_num", "")

            title = f"SEC filing ({filing_type}): {entity}" if entity else f"SEC {filing_type} filing"

            records.append(PublicRecord(
                source="sec_edgar",
                record_type="corporate_filing",
                title=title[:300],
                description=f"Filing type: {filing_type}. Entity: {entity}. File #: {file_num}",
                url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={name}&type=&dateb=&owner=include&count=10",
                date=filed_at,
            ))

    except Exception as e:
        logger.warning("SEC EDGAR search failed for '%s': %s", name, e)

    return records


async def _sec_fulltext_search(name: str) -> Optional[httpx.Response]:
    """Fallback SEC full-text search."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={"q": f'"{name}"', "forms": "10-K,8-K,DEF 14A"},
                headers={
                    "User-Agent": "CloakHaven hello@cloakhaven.com",
                    "Accept": "application/json",
                },
            )
        if response.status_code == 200:
            return response
    except Exception:
        pass
    return None


# ============================================================
# USPTO — Patents (free via PatentsView API)
# https://api.patentsview.org/patents/query
# ============================================================

async def search_patents(name: str, max_results: int = 10) -> list[PublicRecord]:
    """Search USPTO PatentsView for patents by an inventor."""
    records: list[PublicRecord] = []
    parts = name.split()
    if len(parts) < 2:
        return records

    first_name = parts[0]
    last_name = parts[-1]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.patentsview.org/patents/query",
                json={
                    "q": {
                        "_and": [
                            {"inventor_first_name": first_name},
                            {"inventor_last_name": last_name},
                        ]
                    },
                    "f": [
                        "patent_number", "patent_title", "patent_date",
                        "inventor_first_name", "inventor_last_name",
                    ],
                    "o": {"per_page": min(max_results, 25)},
                },
                headers={"Content-Type": "application/json"},
            )

        if response.status_code != 200:
            logger.warning("USPTO API error: %d", response.status_code)
            return records

        data = response.json()
        patents = data.get("patents", [])

        for patent in patents or []:
            patent_num = patent.get("patent_number", "")
            title = patent.get("patent_title", "")
            date = patent.get("patent_date", "")

            records.append(PublicRecord(
                source="uspto",
                record_type="patent",
                title=f"Patent: {title[:200]}",
                description=f"US Patent #{patent_num}",
                url=f"https://patents.google.com/patent/US{patent_num}",
                date=date,
                relevance_score=0.8,
            ))

    except Exception as e:
        logger.warning("USPTO search failed for '%s': %s", name, e)

    return records


# ============================================================
# SEMANTIC SCHOLAR — Academic Publications (free)
# https://api.semanticscholar.org/graph/v1/
# ============================================================

async def search_publications(name: str, max_results: int = 10) -> list[PublicRecord]:
    """Search Semantic Scholar for academic papers by an author."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for authors
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/author/search",
                params={"query": name, "limit": 3},
                headers={"User-Agent": "CloakHaven/1.0"},
            )

        if response.status_code != 200:
            return records

        data = response.json()
        authors = data.get("data", [])
        if not authors:
            return records

        # Get papers for the top matching author
        author_id = authors[0].get("authorId")
        if not author_id:
            return records

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers",
                params={
                    "fields": "title,year,citationCount,url,externalIds",
                    "limit": min(max_results, 25),
                },
                headers={"User-Agent": "CloakHaven/1.0"},
            )

        if response.status_code != 200:
            return records

        papers_data = response.json()
        for paper in papers_data.get("data", []):
            title = paper.get("title", "")
            year = paper.get("year", "")
            citations = paper.get("citationCount", 0) or 0
            url = paper.get("url", "")

            records.append(PublicRecord(
                source="semantic_scholar",
                record_type="publication",
                title=f"Publication: {title[:200]}",
                description=f"Year: {year}. Citations: {citations}.",
                url=url or f"https://scholar.google.com/scholar?q={title[:100]}",
                date=str(year) if year else None,
                relevance_score=min(0.5 + (citations / 100), 1.0),
            ))

    except Exception as e:
        logger.warning("Semantic Scholar search failed for '%s': %s", name, e)

    return records


# ============================================================
# OPENCORPORATES — Business Registrations (free tier)
# https://api.opencorporates.com/v0.4/
# ============================================================

async def search_business_registrations(name: str, max_results: int = 5) -> list[PublicRecord]:
    """Search OpenCorporates for businesses associated with a person (as officer)."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.opencorporates.com/v0.4/officers/search",
                params={
                    "q": name,
                    "per_page": min(max_results, 10),
                },
            )

        if response.status_code != 200:
            return records

        data = response.json()
        officers = data.get("results", {}).get("officers", [])

        for item in officers:
            officer = item.get("officer", {})
            officer_name = officer.get("name", "")
            position = officer.get("position", "")
            company_name = officer.get("company", {}).get("name", "") if isinstance(officer.get("company"), dict) else ""
            company_url = officer.get("company", {}).get("opencorporates_url", "") if isinstance(officer.get("company"), dict) else ""

            records.append(PublicRecord(
                source="opencorporates",
                record_type="business",
                title=f"Business officer: {officer_name} at {company_name}"[:300],
                description=f"Position: {position}. Company: {company_name}.",
                url=company_url or "https://opencorporates.com",
                relevance_score=0.7,
            ))

    except Exception as e:
        logger.warning("OpenCorporates search failed for '%s': %s", name, e)

    return records


# ============================================================
# GITHUB — Public Profile + Repos (free, no API key needed)
# https://api.github.com/search/users
# ============================================================

async def search_github_profile(name: str, max_results: int = 5) -> list[PublicRecord]:
    """Search GitHub for public profiles and notable repos matching a person's name."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for users matching the name
            response = await client.get(
                "https://api.github.com/search/users",
                params={"q": f"{name} in:fullname", "per_page": 3},
                headers={
                    "User-Agent": "CloakHaven/1.0",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

        if response.status_code != 200:
            logger.warning("GitHub API error: %d", response.status_code)
            return records

        data = response.json()
        users = data.get("items", [])

        for user in users[:max_results]:
            login = user.get("login", "")
            profile_url = user.get("html_url", "")
            avatar = user.get("avatar_url", "")

            # Get user details for more info
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    detail_resp = await client.get(
                        f"https://api.github.com/users/{login}",
                        headers={
                            "User-Agent": "CloakHaven/1.0",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    )
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    full_name = detail.get("name", "") or ""
                    bio = detail.get("bio", "") or ""
                    public_repos = detail.get("public_repos", 0)
                    followers = detail.get("followers", 0)
                    company = detail.get("company", "") or ""

                    # Only include if the GitHub name reasonably matches
                    name_lower = name.lower()
                    full_name_lower = full_name.lower()
                    if name_lower not in full_name_lower and full_name_lower not in name_lower:
                        continue

                    desc = f"GitHub: {full_name}. {bio[:200]}. {public_repos} repos, {followers} followers."
                    if company:
                        desc += f" Company: {company}."

                    # More followers/repos = higher relevance
                    relevance = min(0.5 + (followers / 500) + (public_repos / 200), 1.0)

                    records.append(PublicRecord(
                        source="github",
                        record_type="business",  # Maps to professional_achievement
                        title=f"GitHub profile: {full_name} (@{login})"[:300],
                        description=desc[:500],
                        url=profile_url,
                        relevance_score=relevance,
                    ))
            except Exception:
                continue

    except Exception as e:
        logger.warning("GitHub search failed for '%s': %s", name, e)

    return records


# ============================================================
# WIKIPEDIA — Quick existence check (free, no API key needed)
# https://en.wikipedia.org/api/rest_v1/
# ============================================================

async def search_wikipedia(name: str) -> list[PublicRecord]:
    """Check if a person has a Wikipedia page — strong signal of notability."""
    records: list[PublicRecord] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" + name.replace(" ", "_"),
                headers={"User-Agent": "CloakHaven/1.0"},
            )

        if response.status_code != 200:
            return records

        data = response.json()
        title = data.get("title", "")
        extract = data.get("extract", "")
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        page_type = data.get("type", "")

        # Only include if it's a standard article (not disambiguation, etc.)
        if page_type == "standard" and extract:
            records.append(PublicRecord(
                source="wikipedia",
                record_type="publication",
                title=f"Wikipedia: {title}"[:300],
                description=extract[:500],
                url=page_url or f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
                relevance_score=0.9,  # Wikipedia page = very high relevance
            ))

    except Exception as e:
        logger.warning("Wikipedia search failed for '%s': %s", name, e)

    return records


# ============================================================
# UNIFIED SEARCH — Run all public data sources concurrently
# ============================================================

async def search_all_public_records(name: str) -> list[PublicRecord]:
    """
    Search all free public data sources concurrently.
    Returns combined results from all sources.
    """
    results = await asyncio.gather(
        search_court_records(name),
        search_sec_filings(name),
        search_patents(name),
        search_publications(name),
        search_business_registrations(name),
        search_github_profile(name),
        search_wikipedia(name),
        return_exceptions=True,
    )

    all_records: list[PublicRecord] = []
    source_names = [
        "CourtListener", "SEC EDGAR", "USPTO", "Semantic Scholar",
        "OpenCorporates", "GitHub", "Wikipedia",
    ]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("%s search failed: %s", source_names[i], result)
            continue
        if isinstance(result, list):
            all_records.extend(result)

    logger.info(
        "Public records search for '%s': %d total records from %d sources",
        name, len(all_records), sum(1 for r in results if isinstance(r, list) and r),
    )
    return all_records
