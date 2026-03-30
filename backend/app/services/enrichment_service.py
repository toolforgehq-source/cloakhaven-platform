"""
Data Enrichment Service

Integrates with Proxycurl and PeopleDataLabs to look up a person
across all social platforms using just a name, email, or LinkedIn URL.

This is the backbone of "score anyone" — it resolves a person's identity
across platforms without needing direct API access to each one.

Proxycurl docs: https://nubela.co/proxycurl/docs
PeopleDataLabs docs: https://docs.peopledatalabs.com/
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PROXYCURL_BASE = "https://nubela.co/proxycurl/api"
PDL_BASE = "https://api.peopledatalabs.com/v5"


class EnrichmentError(Exception):
    pass


@dataclass
class EnrichedProfile:
    """Cross-platform profile data resolved from enrichment APIs."""
    name: str
    email: str = ""
    linkedin_url: str = ""
    twitter_username: str = ""
    facebook_url: str = ""
    github_username: str = ""
    personal_website: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    industry: str = ""
    company: str = ""
    job_title: str = ""
    education: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    social_profiles: dict[str, str] = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)
    source: str = ""  # "proxycurl" or "peopledatalabs"


# ============================================================
# PROXYCURL
# ============================================================


async def proxycurl_lookup_by_linkedin(linkedin_url: str) -> EnrichedProfile:
    """
    Look up a person's full profile using their LinkedIn URL via Proxycurl.
    This returns detailed work history, education, and social links.
    """
    if not settings.PROXYCURL_API_KEY:
        raise EnrichmentError("Proxycurl API not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PROXYCURL_BASE}/v2/linkedin",
            headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
            params={"linkedin_profile_url": linkedin_url, "use_cache": "if-recent"},
        )

    if response.status_code == 404:
        raise EnrichmentError("LinkedIn profile not found via Proxycurl")
    if response.status_code == 403:
        raise EnrichmentError("Proxycurl API credits exhausted or invalid key")
    if response.status_code != 200:
        raise EnrichmentError(f"Proxycurl API error: {response.status_code}")

    data = response.json()
    return _parse_proxycurl_profile(data)


async def proxycurl_search_person(
    name: str,
    email: Optional[str] = None,
    company: Optional[str] = None,
) -> Optional[EnrichedProfile]:
    """
    Search for a person by name (and optionally email/company) using
    Proxycurl's Person Search API. Returns the best match.
    """
    if not settings.PROXYCURL_API_KEY:
        raise EnrichmentError("Proxycurl API not configured")

    params: dict[str, str] = {}

    # Use the person lookup endpoint if email is provided
    if email:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PROXYCURL_BASE}/linkedin/profile/resolve/email",
                headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
                params={"work_email": email},
            )

        if response.status_code == 200:
            data = response.json()
            linkedin_url = data.get("url")
            if linkedin_url:
                return await proxycurl_lookup_by_linkedin(linkedin_url)

    # Fall back to person search by name
    params["first_name"] = name.split()[0] if " " in name else name
    if " " in name:
        params["last_name"] = " ".join(name.split()[1:])
    if company:
        params["current_company_name"] = company

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PROXYCURL_BASE}/search/person/",
            headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
            params=params,
        )

    if response.status_code != 200:
        logger.warning(f"Proxycurl person search failed: {response.status_code}")
        return None

    data = response.json()
    results = data.get("results", [])
    if not results:
        return None

    # Take the top result and look up full profile
    top_result = results[0]
    linkedin_url = top_result.get("linkedin_profile_url")
    if linkedin_url:
        try:
            return await proxycurl_lookup_by_linkedin(linkedin_url)
        except EnrichmentError:
            pass

    return None


def _parse_proxycurl_profile(data: dict) -> EnrichedProfile:
    """Parse Proxycurl API response into an EnrichedProfile."""
    social_profiles: dict[str, str] = {}

    # Extract social profiles from the data
    github = data.get("github_profile_id")
    twitter_handle = data.get("twitter_profile_id")
    facebook_id = data.get("facebook_profile_id")

    if twitter_handle:
        social_profiles["twitter"] = f"https://twitter.com/{twitter_handle}"
    if github:
        social_profiles["github"] = f"https://github.com/{github}"
    if facebook_id:
        social_profiles["facebook"] = f"https://facebook.com/{facebook_id}"

    # Parse education
    education = []
    for edu in data.get("education", []) or []:
        education.append({
            "school": edu.get("school", ""),
            "degree": edu.get("degree_name", ""),
            "field": edu.get("field_of_study", ""),
            "start_year": edu.get("starts_at", {}).get("year") if edu.get("starts_at") else None,
            "end_year": edu.get("ends_at", {}).get("year") if edu.get("ends_at") else None,
        })

    # Parse work experience
    experience = []
    for exp in data.get("experiences", []) or []:
        experience.append({
            "company": exp.get("company", ""),
            "title": exp.get("title", ""),
            "start_year": exp.get("starts_at", {}).get("year") if exp.get("starts_at") else None,
            "end_year": exp.get("ends_at", {}).get("year") if exp.get("ends_at") else None,
            "description": exp.get("description", ""),
        })

    full_name = data.get("full_name", "")

    return EnrichedProfile(
        name=full_name,
        linkedin_url=data.get("public_identifier", ""),
        twitter_username=twitter_handle or "",
        facebook_url=f"https://facebook.com/{facebook_id}" if facebook_id else "",
        github_username=github or "",
        personal_website=data.get("personal_website") or "",
        headline=data.get("headline", ""),
        summary=data.get("summary", ""),
        location=f"{data.get('city', '')} {data.get('state', '')} {data.get('country_full_name', '')}".strip(),
        industry=data.get("industry", ""),
        company=experience[0]["company"] if experience else "",
        job_title=experience[0]["title"] if experience else "",
        education=education,
        experience=experience,
        social_profiles=social_profiles,
        raw_data=data,
        source="proxycurl",
    )


# ============================================================
# PEOPLEDATALABS
# ============================================================


async def pdl_enrich_person(
    name: Optional[str] = None,
    email: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[EnrichedProfile]:
    """
    Enrich a person's profile using PeopleDataLabs.
    Accepts name, email, LinkedIn URL, or phone — any combination.
    """
    if not settings.PEOPLEDATALABS_API_KEY:
        raise EnrichmentError("PeopleDataLabs API not configured")

    params: dict[str, str] = {}
    if name:
        params["name"] = name
    if email:
        params["email"] = email
    if linkedin_url:
        params["profile"] = linkedin_url
    if phone:
        params["phone"] = phone

    if not params:
        raise EnrichmentError("At least one identifier required for PDL lookup")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PDL_BASE}/person/enrich",
            headers={"X-Api-Key": settings.PEOPLEDATALABS_API_KEY},
            params=params,
        )

    if response.status_code == 404:
        return None
    if response.status_code == 402:
        raise EnrichmentError("PeopleDataLabs API credits exhausted")
    if response.status_code != 200:
        raise EnrichmentError(f"PeopleDataLabs API error: {response.status_code}")

    data = response.json()
    return _parse_pdl_profile(data)


async def pdl_search_person(
    name: str,
    location: Optional[str] = None,
    company: Optional[str] = None,
) -> Optional[EnrichedProfile]:
    """
    Search for a person by name using PeopleDataLabs search API.
    """
    if not settings.PEOPLEDATALABS_API_KEY:
        raise EnrichmentError("PeopleDataLabs API not configured")

    # Build Elasticsearch-style query
    must_clauses = [{"match": {"full_name": name}}]
    if location:
        must_clauses.append({"match": {"location_name": location}})
    if company:
        must_clauses.append({"match": {"job_company_name": company}})

    payload = {
        "query": {"bool": {"must": must_clauses}},
        "size": 1,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PDL_BASE}/person/search",
            headers={
                "X-Api-Key": settings.PEOPLEDATALABS_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        logger.warning(f"PDL person search failed: {response.status_code}")
        return None

    data = response.json()
    results = data.get("data", [])
    if not results:
        return None

    return _parse_pdl_profile(results[0])


def _parse_pdl_profile(data: dict) -> EnrichedProfile:
    """Parse PeopleDataLabs API response into an EnrichedProfile."""
    social_profiles: dict[str, str] = {}

    # Extract social profiles
    for profile in data.get("profiles", []) or []:
        network = profile.get("network", "").lower()
        url = profile.get("url", "")
        username = profile.get("username", "")
        if network and (url or username):
            social_profiles[network] = url or username

    # Extract LinkedIn from dedicated field
    linkedin_url = data.get("linkedin_url", "")
    if linkedin_url:
        social_profiles["linkedin"] = linkedin_url

    twitter_username = ""
    for profile in data.get("profiles", []) or []:
        if profile.get("network", "").lower() == "twitter":
            twitter_username = profile.get("username", "")
            break

    github_username = ""
    for profile in data.get("profiles", []) or []:
        if profile.get("network", "").lower() == "github":
            github_username = profile.get("username", "")
            break

    # Parse education
    education = []
    for edu in data.get("education", []) or []:
        education.append({
            "school": edu.get("school", {}).get("name", "") if isinstance(edu.get("school"), dict) else str(edu.get("school", "")),
            "degree": edu.get("degrees", [""])[0] if edu.get("degrees") else "",
            "field": edu.get("majors", [""])[0] if edu.get("majors") else "",
            "start_year": edu.get("start_date"),
            "end_year": edu.get("end_date"),
        })

    # Parse experience
    experience = []
    for exp in data.get("experience", []) or []:
        experience.append({
            "company": exp.get("company", {}).get("name", "") if isinstance(exp.get("company"), dict) else str(exp.get("company", "")),
            "title": exp.get("title", {}).get("name", "") if isinstance(exp.get("title"), dict) else str(exp.get("title", "")),
            "start_year": exp.get("start_date"),
            "end_year": exp.get("end_date"),
            "description": "",
        })

    full_name = data.get("full_name", "")
    job_title = data.get("job_title", "")
    job_company = data.get("job_company_name", "")

    return EnrichedProfile(
        name=full_name,
        email=data.get("work_email", "") or data.get("personal_emails", [""])[0] if data.get("personal_emails") else "",
        linkedin_url=linkedin_url,
        twitter_username=twitter_username,
        github_username=github_username,
        personal_website=data.get("website") or "",
        headline=job_title,
        summary=data.get("summary", "") or "",
        location=data.get("location_name", ""),
        industry=data.get("industry", ""),
        company=job_company,
        job_title=job_title,
        education=education,
        experience=experience,
        social_profiles=social_profiles,
        raw_data=data,
        source="peopledatalabs",
    )


# ============================================================
# UNIFIED ENRICHMENT PIPELINE
# ============================================================


async def enrich_person(
    name: str,
    email: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    company: Optional[str] = None,
) -> Optional[EnrichedProfile]:
    """
    Try to enrich a person's profile using all available services.
    Falls back gracefully: Proxycurl → PeopleDataLabs.
    Returns the best result, or None if no match found.
    """
    # Try Proxycurl first (if configured)
    if settings.PROXYCURL_API_KEY:
        try:
            if linkedin_url:
                result = await proxycurl_lookup_by_linkedin(linkedin_url)
                if result:
                    return result
            result = await proxycurl_search_person(name, email=email, company=company)
            if result:
                return result
        except EnrichmentError as e:
            logger.warning(f"Proxycurl enrichment failed: {e}")

    # Fall back to PeopleDataLabs (if configured)
    if settings.PEOPLEDATALABS_API_KEY:
        try:
            result = await pdl_enrich_person(
                name=name, email=email, linkedin_url=linkedin_url
            )
            if result:
                return result
            result = await pdl_search_person(name, company=company)
            if result:
                return result
        except EnrichmentError as e:
            logger.warning(f"PeopleDataLabs enrichment failed: {e}")

    return None
