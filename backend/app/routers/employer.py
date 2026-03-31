"""Employer tier endpoints."""

from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.database import get_db
from app.models.user import User
from app.models.finding import Finding
from app.models.public_profile import PublicProfile
from app.models.audit_log import EmployerSearch
from app.schemas.public import (
    EmployerSearchRequest,
    EmployerReportResponse,
    EmployerSearchHistoryItem,
    EmployerSearchHistoryResponse,
    PublicProfileResponse,
)
from app.middleware.auth import get_employer_user
from app.services.scoring_engine import get_score_color, get_score_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/employer", tags=["employer"])


@router.post("/search", response_model=EmployerReportResponse)
async def employer_search(
    request: EmployerSearchRequest,
    current_user: User = Depends(get_employer_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for a candidate's reputation report. Employer tier only."""
    # Find matching public profile
    query = select(PublicProfile).where(
        or_(
            PublicProfile.lookup_name.ilike(f"%{request.name}%"),
            PublicProfile.lookup_username.ilike(f"%{request.username}%") if request.username else False,
        )
    )
    result = await db.execute(query)
    profile = result.scalars().first()

    if not profile:
        # No cached profile — trigger a passive scan to create one
        try:
            from app.services.passive_scanner import run_passive_scan
            scan_result = await run_passive_scan(
                db=db,
                name=request.name,
            )
            await db.commit()

            # Re-query the now-created profile
            result = await db.execute(query)
            profile = result.scalars().first()
        except Exception as e:
            logger.warning("Passive scan failed during employer search: %s", e)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching profile found",
        )

    # Log the search
    search_log = EmployerSearch(
        employer_user_id=current_user.id,
        searched_name=request.name,
        searched_username=request.username,
        result_profile_id=profile.id,
    )
    db.add(search_log)
    await db.commit()

    # Get findings summary if profile is claimed and has a linked user
    findings_summary: dict = {}
    risk_level = "unknown"
    recommendation = "Insufficient data to make a recommendation. The candidate has not yet claimed their Cloak Haven profile."

    if profile.matched_user_id:
        # Get category breakdown
        cat_result = await db.execute(
            select(Finding.category, func.count(Finding.id)).where(
                Finding.user_id == profile.matched_user_id,
                Finding.is_juvenile_content.is_(False),
            ).group_by(Finding.category)
        )
        findings_summary = {row[0]: row[1] for row in cat_result.all()}

        if profile.public_score is not None:
            if profile.public_score >= 800:
                risk_level = "low"
                recommendation = "Low risk candidate. Strong online reputation with minimal concerning findings."
            elif profile.public_score >= 600:
                risk_level = "medium"
                recommendation = "Moderate risk. Some findings warrant review but overall acceptable online presence."
            elif profile.public_score >= 400:
                risk_level = "high"
                recommendation = "High risk. Multiple concerning findings detected. Manual review recommended."
            else:
                risk_level = "critical"
                recommendation = "Critical risk. Significant concerning content found across multiple platforms."

    from app.routers.compliance import FCRA_DISCLAIMER

    return EmployerReportResponse(
        profile=PublicProfileResponse(
            id=profile.id,
            lookup_name=profile.lookup_name,
            lookup_username=profile.lookup_username,
            public_score=profile.public_score,
            score_accuracy_pct=profile.score_accuracy_pct,
            is_claimed=profile.is_claimed,
            score_color=get_score_color(profile.public_score) if profile.public_score else None,
            score_label=get_score_label(profile.public_score) if profile.public_score else None,
            last_scanned_at=profile.last_scanned_at,
            public_findings_summary=profile.public_findings_summary,
        ),
        findings_summary=findings_summary,
        risk_level=risk_level,
        recommendation=recommendation,
        searched_at=datetime.utcnow(),
        fcra_disclaimer=FCRA_DISCLAIMER,
    )


@router.get("/search/history", response_model=EmployerSearchHistoryResponse)
async def get_search_history(
    current_user: User = Depends(get_employer_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the employer's search history."""
    result = await db.execute(
        select(EmployerSearch)
        .where(EmployerSearch.employer_user_id == current_user.id)
        .order_by(EmployerSearch.searched_at.desc())
        .limit(100)
    )
    searches = result.scalars().all()

    return EmployerSearchHistoryResponse(
        searches=[
            EmployerSearchHistoryItem(
                id=s.id,
                searched_name=s.searched_name,
                searched_username=s.searched_username,
                searched_at=s.searched_at,
            )
            for s in searches
        ],
        total=len(searches),
    )
