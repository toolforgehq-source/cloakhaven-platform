"""
Passive Scan Endpoints

Score anyone by name/email without requiring them to sign up.
This is the "credit bureau" functionality — employers, partners,
and the public search all trigger passive scans.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.public_profile import PublicProfile
from app.services.passive_scanner import run_passive_scan
from app.services.scoring_engine import get_score_color, get_score_label
from app.config import settings
from app.middleware.rate_limit import scan_limiter, check_rate_limit, check_daily_scan_cap, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


def _check_scan_rate_limit(request: Request, name: str | None = None) -> None:
    """Check scan-specific rate limits (persistent, hourly + daily cap)."""
    client_ip = get_client_ip(request)
    check_rate_limit(client_ip, scan_limiter, "Scan rate limit exceeded. Please wait before scanning again.")
    if name:
        check_daily_scan_cap(client_ip, name)


# ── Request/Response Schemas ──

class PassiveScanRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255, description="Full name of the person to scan")
    email: Optional[str] = Field(None, max_length=255, description="Email address (improves accuracy)")
    company: Optional[str] = Field(None, max_length=255, description="Current company (helps disambiguation)")
    location: Optional[str] = Field(None, max_length=255, description="City/state/country (helps disambiguation)")
    linkedin_url: Optional[str] = Field(None, max_length=500, description="LinkedIn profile URL")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title (helps disambiguation)")


class PassiveScanFinding(BaseModel):
    source: str
    category: str
    severity: str
    title: str
    description: str
    evidence_url: Optional[str] = None
    confidence: float
    corroboration_count: int = 1
    base_score_impact: float


class PassiveScanResponse(BaseModel):
    profile_id: uuid.UUID
    name: str
    overall_score: int
    social_media_score: int
    web_presence_score: int
    posting_behavior_score: int
    accuracy_pct: float
    identity_confidence: float
    score_color: str
    score_label: str
    sources_scanned: list[str]
    total_findings: int
    findings: list[PassiveScanFinding]
    enrichment_data: Optional[dict] = None
    scan_duration_seconds: float
    scanned_at: datetime


class QuickLookupResponse(BaseModel):
    """Lightweight response for quick lookups (returns cached score if available)."""
    profile_id: uuid.UUID
    name: str
    overall_score: Optional[int]
    accuracy_pct: Optional[float]
    score_color: Optional[str]
    score_label: Optional[str]
    is_cached: bool
    last_scanned_at: Optional[datetime]
    needs_fresh_scan: bool


# ── Endpoints ──

@router.post("/passive", response_model=PassiveScanResponse)
async def passive_scan(
    request: Request,
    body: PassiveScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Score anyone by name without requiring their signup.

    This is the core "credit bureau" functionality. It:
    1. Resolves identity via PeopleDataLabs (discovers social handles)
    2. Searches 15+ data sources (SerpAPI, Twitter mentions, YouTube, court records, etc.)
    3. Disambiguates results with LLM (ensures findings are about the right person)
    4. Cross-references findings for corroboration
    5. Computes and stores the score

    Returns cached results if scanned within the last 24 hours.
    Provide more identifiers (email, company, location) for higher accuracy.
    """
    _check_scan_rate_limit(request, name=body.name)

    # Check for recent cached result (within 24 hours)
    force_rescan = request.query_params.get("force", "").lower() == "true"
    if not force_rescan:
        cached = await db.execute(
            select(PublicProfile).where(PublicProfile.lookup_name == body.name)
        )
        cached_profile = cached.scalar_one_or_none()
        if cached_profile and cached_profile.last_scanned_at:
            hours_since = (datetime.utcnow() - cached_profile.last_scanned_at).total_seconds() / 3600
            if hours_since < 24 and cached_profile.public_score is not None:
                # Return cached result
                findings_data = cached_profile.public_findings_summary or {}
                findings_list = findings_data.get("findings", [])
                return PassiveScanResponse(
                    profile_id=cached_profile.id,
                    name=cached_profile.lookup_name,
                    overall_score=cached_profile.public_score,
                    social_media_score=cached_profile.social_media_score or 850,
                    web_presence_score=cached_profile.web_presence_score or 0,
                    posting_behavior_score=cached_profile.posting_behavior_score or 850,
                    accuracy_pct=cached_profile.score_accuracy_pct or 0.0,
                    identity_confidence=cached_profile.identity_confidence or 0.3,
                    score_color=get_score_color(cached_profile.public_score),
                    score_label=get_score_label(cached_profile.public_score),
                    sources_scanned=findings_data.get("sources_scanned", []),
                    total_findings=findings_data.get("total_findings", 0),
                    findings=[
                        PassiveScanFinding(
                            source=f.get("source", ""),
                            category=f.get("category", "neutral"),
                            severity=f.get("severity", "neutral"),
                            title=f.get("title", ""),
                            description=f.get("description", "")[:300],
                            evidence_url=f.get("evidence_url"),
                            confidence=f.get("confidence", 0.5),
                            corroboration_count=f.get("corroboration_count", 1),
                            base_score_impact=f.get("base_score_impact", 0.0),
                        )
                        for f in findings_list[:50]
                    ],
                    enrichment_data=findings_data.get("enrichment_data"),
                    scan_duration_seconds=cached_profile.scan_duration_seconds or 0.0,
                    scanned_at=cached_profile.last_scanned_at,
                )

    result = await run_passive_scan(
        db=db,
        name=body.name,
        email=body.email,
        company=body.company,
        location=body.location,
        linkedin_url=body.linkedin_url,
        job_title=body.job_title,
    )
    await db.commit()

    return PassiveScanResponse(
        profile_id=result.profile_id,
        name=result.name,
        overall_score=result.overall_score,
        social_media_score=result.social_media_score,
        web_presence_score=result.web_presence_score,
        posting_behavior_score=result.posting_behavior_score,
        accuracy_pct=result.accuracy_pct,
        identity_confidence=result.identity_confidence,
        score_color=get_score_color(result.overall_score),
        score_label=get_score_label(result.overall_score),
        sources_scanned=result.sources_scanned,
        total_findings=len(result.findings),
        findings=[
            PassiveScanFinding(
                source=f.source,
                category=f.category,
                severity=f.severity,
                title=f.title,
                description=f.description[:300],
                evidence_url=f.evidence_url,
                confidence=round(f.confidence, 2),
                corroboration_count=f.corroboration_count,
                base_score_impact=f.base_score_impact,
            )
            for f in result.findings[:50]  # Cap response at 50 findings
        ],
        enrichment_data=result.enrichment_data,
        scan_duration_seconds=result.scan_duration_seconds,
        scanned_at=datetime.utcnow(),
    )


@router.get("/lookup/{name}", response_model=QuickLookupResponse)
async def quick_lookup(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Quick lookup — returns cached score if available, otherwise indicates
    a fresh scan is needed. Use this for instant results in search UIs.
    """
    _check_scan_rate_limit(request)

    result = await db.execute(
        select(PublicProfile).where(PublicProfile.lookup_name == name)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # No cached data — return empty result indicating fresh scan needed
        # (lookup is read-only, no daily cap hit since no scan is triggered)
        return QuickLookupResponse(
            profile_id=uuid.uuid4(),  # Placeholder
            name=name,
            overall_score=None,
            accuracy_pct=None,
            score_color=None,
            score_label=None,
            is_cached=False,
            last_scanned_at=None,
            needs_fresh_scan=True,
        )

    # Check freshness (>30 days = stale)
    is_stale = False
    if profile.last_scanned_at:
        days_since = (datetime.utcnow() - profile.last_scanned_at).days
        is_stale = days_since > settings.PUBLIC_SCORE_REFRESH_DAYS

    return QuickLookupResponse(
        profile_id=profile.id,
        name=profile.lookup_name,
        overall_score=profile.public_score,
        accuracy_pct=profile.score_accuracy_pct,
        score_color=get_score_color(profile.public_score) if profile.public_score else None,
        score_label=get_score_label(profile.public_score) if profile.public_score else None,
        is_cached=True,
        last_scanned_at=profile.last_scanned_at,
        needs_fresh_scan=is_stale,
    )


@router.post("/batch", response_model=list[QuickLookupResponse])
async def batch_lookup(
    request: Request,
    names: list[str],
    db: AsyncSession = Depends(get_db),
):
    """
    Batch lookup — check multiple names at once. Returns cached scores
    where available. Useful for employer bulk screening.
    Max 25 names per request.
    """
    _check_scan_rate_limit(request)

    if len(names) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 names per batch request for unauthenticated users",
        )
    if len(names) > 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 25 names per batch request",
        )

    results = []
    for name in names:
        name = name.strip()
        if len(name) < 2:
            continue

        profile_result = await db.execute(
            select(PublicProfile).where(PublicProfile.lookup_name == name)
        )
        profile = profile_result.scalar_one_or_none()

        if profile:
            is_stale = False
            if profile.last_scanned_at:
                days_since = (datetime.utcnow() - profile.last_scanned_at).days
                is_stale = days_since > settings.PUBLIC_SCORE_REFRESH_DAYS

            results.append(QuickLookupResponse(
                profile_id=profile.id,
                name=profile.lookup_name,
                overall_score=profile.public_score,
                accuracy_pct=profile.score_accuracy_pct,
                score_color=get_score_color(profile.public_score) if profile.public_score else None,
                score_label=get_score_label(profile.public_score) if profile.public_score else None,
                is_cached=True,
                last_scanned_at=profile.last_scanned_at,
                needs_fresh_scan=is_stale,
            ))
        else:
            results.append(QuickLookupResponse(
                profile_id=uuid.uuid4(),
                name=name,
                overall_score=None,
                accuracy_pct=None,
                score_color=None,
                score_label=None,
                is_cached=False,
                last_scanned_at=None,
                needs_fresh_scan=True,
            ))

    return results
