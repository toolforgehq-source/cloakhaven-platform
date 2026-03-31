"""Public profile and search endpoints."""

import asyncio
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_db, async_session_factory
from app.models.user import User
from app.models.score import Score
from app.models.finding import Finding
from app.models.social_account import SocialAccount
from app.models.public_profile import PublicProfile
from app.schemas.public import (
    PublicProfileResponse,
    PublicSearchResponse,
    ClaimProfileRequest,
    ScoreCardResponse,
)
from app.schemas.auth import MessageResponse
from app.middleware.auth import get_current_user
from app.services.scoring_engine import get_score_color, get_score_label
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public", tags=["public"])


async def _background_passive_scan(name: str) -> None:
    """Run a passive scan in the background with its own DB session."""
    try:
        from app.services.passive_scanner import run_passive_scan
        async with async_session_factory() as db:
            await run_passive_scan(db=db, name=name)
            await db.commit()
        logger.info("Background passive scan completed for '%s'", name)
    except Exception as e:
        logger.warning("Background passive scan failed for '%s': %s", name, e)


@router.get("/search", response_model=PublicSearchResponse)
async def search_public_profiles(
    q: str = Query(min_length=2, max_length=255),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Search for a person's public score. Available to anyone.

    If a cached profile exists, returns it instantly.
    If no cached profile is found and query looks like a name, triggers a
    background passive scan and returns an empty result with scan_pending=true.
    The caller should poll GET /api/v1/scan/lookup/{name} to check when the scan completes.
    """
    result = await db.execute(
        select(PublicProfile).where(
            or_(
                PublicProfile.lookup_name.ilike(f"%{q}%"),
                PublicProfile.lookup_username.ilike(f"%{q}%"),
            )
        ).limit(20)
    )
    profiles = result.scalars().all()

    scan_pending = False

    # If no profiles found and query looks like a name, trigger BACKGROUND scan
    # (non-blocking — returns immediately instead of waiting 60s)
    if not profiles and len(q.strip()) >= 3 and " " in q.strip():
        scan_pending = True
        background_tasks.add_task(_background_passive_scan, q.strip())

    return PublicSearchResponse(
        results=[
            PublicProfileResponse(
                id=p.id,
                lookup_name=p.lookup_name,
                lookup_username=p.lookup_username,
                public_score=p.public_score,
                score_accuracy_pct=p.score_accuracy_pct,
                is_claimed=p.is_claimed,
                score_color=get_score_color(p.public_score) if p.public_score else None,
                score_label=get_score_label(p.public_score) if p.public_score else None,
                last_scanned_at=p.last_scanned_at,
                public_findings_summary=p.public_findings_summary,
            )
            for p in profiles
        ],
        total=len(profiles),
        scan_pending=scan_pending,
    )


@router.get("/profile/{username}", response_model=PublicProfileResponse)
async def get_public_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a public profile by username."""
    result = await db.execute(
        select(PublicProfile).where(PublicProfile.lookup_username == username)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return PublicProfileResponse(
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
    )


@router.post("/claim", response_model=MessageResponse)
async def claim_profile(
    request: ClaimProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim a public profile as your own."""
    result = await db.execute(
        select(PublicProfile).where(PublicProfile.id == request.profile_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    if profile.is_claimed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already claimed",
        )

    profile.is_claimed = True
    profile.matched_user_id = current_user.id
    current_user.is_profile_claimed = True

    await db.commit()

    return MessageResponse(message="Profile claimed successfully")


@router.get("/scorecard/{user_id}", response_model=ScoreCardResponse)
async def get_scorecard(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a shareable scorecard for a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.profile_visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user's profile is private",
        )

    result = await db.execute(
        select(Score).where(Score.user_id == user_id)
    )
    score = result.scalar_one_or_none()

    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score available",
        )

    # Get findings for category breakdown
    findings_result = await db.execute(
        select(Finding).where(Finding.user_id == user_id)
    )
    findings = findings_result.scalars().all()
    category_breakdown: dict[str, int] = {}
    for f in findings:
        category_breakdown[f.category] = category_breakdown.get(f.category, 0) + 1

    # Get connected platforms
    accounts_result = await db.execute(
        select(SocialAccount.platform).where(SocialAccount.user_id == user_id).distinct()
    )
    platforms = [row[0] for row in accounts_result.all()]

    return ScoreCardResponse(
        user_id=user_id,
        display_name=user.display_name or user.full_name or "Anonymous",
        overall_score=score.overall_score,
        social_media_score=score.social_media_score,
        web_presence_score=score.web_presence_score,
        posting_behavior_score=score.posting_behavior_score,
        score_accuracy_pct=score.score_accuracy_pct,
        is_verified=score.is_verified,
        score_color=get_score_color(score.overall_score),
        score_label=get_score_label(score.overall_score),
        calculated_at=score.calculated_at,
        share_url=f"{settings.FRONTEND_URL}/scorecard/{user_id}",
        platforms_analyzed=platforms,
        total_findings=len(findings),
        category_breakdown=category_breakdown,
    )
