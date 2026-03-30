"""Score and audit endpoints."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.score import Score, ScoreHistory
from app.models.social_account import SocialAccount
from app.schemas.score import (
    ScoreResponse,
    ScoreHistoryItem,
    ScoreHistoryResponse,
    AuditStartResponse,
    AuditStatusResponse,
)
from app.middleware.auth import get_current_user
from app.services.scoring_engine import (
    calculate_score,
    get_score_color,
    get_score_label,
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["score"])


@router.get("/score", response_model=ScoreResponse)
async def get_my_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Score).where(Score.user_id == current_user.id)
    )
    score = result.scalar_one_or_none()

    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score calculated yet. Start an audit to get your score.",
        )

    return ScoreResponse(
        overall_score=score.overall_score,
        social_media_score=score.social_media_score,
        web_presence_score=score.web_presence_score,
        posting_behavior_score=score.posting_behavior_score,
        score_accuracy_pct=score.score_accuracy_pct,
        is_verified=score.is_verified,
        verification_date=score.verification_date,
        score_breakdown=score.score_breakdown,
        calculated_at=score.calculated_at,
        score_color=get_score_color(score.overall_score),
        score_label=get_score_label(score.overall_score),
    )


@router.get("/score/history", response_model=ScoreHistoryResponse)
async def get_score_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.user_id == current_user.id)
        .order_by(desc(ScoreHistory.recorded_at))
        .limit(100)
    )
    history = result.scalars().all()

    return ScoreHistoryResponse(
        history=[
            ScoreHistoryItem(
                overall_score=h.overall_score,
                social_media_score=h.social_media_score,
                web_presence_score=h.web_presence_score,
                posting_behavior_score=h.posting_behavior_score,
                recorded_at=h.recorded_at,
            )
            for h in history
        ]
    )


@router.post("/audit/start", response_model=AuditStartResponse)
async def start_audit(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a comprehensive audit of the user's online presence."""
    audit_id = str(uuid.uuid4())

    # Scan connected Twitter accounts if API key is available
    if settings.TWITTER_BEARER_TOKEN:
        try:
            from app.services.twitter_service import scan_twitter_account
            # Find connected Twitter accounts
            result = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.user_id == current_user.id,
                    SocialAccount.platform == "twitter",
                )
            )
            twitter_account = result.scalar_one_or_none()
            if twitter_account and twitter_account.platform_username:
                await scan_twitter_account(
                    db, current_user.id, twitter_account.platform_username
                )
                logger.info(f"Twitter scan complete for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Twitter scan failed for user {current_user.id}: {e}")

    # Scan web presence via Google if API key is available
    if settings.GOOGLE_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID:
        try:
            from app.services.google_service import scan_web_presence
            # Get connected usernames for search queries
            acct_result = await db.execute(
                select(SocialAccount.platform_username).where(
                    SocialAccount.user_id == current_user.id,
                    SocialAccount.platform_username.isnot(None),
                )
            )
            usernames = [row[0] for row in acct_result.all() if row[0]]
            name = current_user.full_name or current_user.display_name or ""
            if name:
                await scan_web_presence(db, current_user.id, name, usernames or None)
                logger.info(f"Google web scan complete for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Google scan failed for user {current_user.id}: {e}")

    # Calculate score from all findings (existing + newly scanned)
    score = await calculate_score(db, current_user.id)
    await db.commit()

    return AuditStartResponse(
        message="Audit complete. Your score has been calculated.",
        audit_id=audit_id,
        status="complete",
    )


@router.get("/audit/status", response_model=AuditStatusResponse)
async def get_audit_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status of the current audit."""
    # Check if score exists
    result = await db.execute(
        select(Score).where(Score.user_id == current_user.id)
    )
    score = result.scalar_one_or_none()

    if score:
        from sqlalchemy import func
        from app.models.finding import Finding
        count_result = await db.execute(
            select(func.count()).where(Finding.user_id == current_user.id)
        )
        findings_count = count_result.scalar()

        return AuditStatusResponse(
            status="complete",
            progress_pct=100.0,
            platforms_scanned=["twitter", "google"],
            findings_count=findings_count,
            message="Audit complete. Your score is ready.",
        )

    return AuditStatusResponse(
        status="pending",
        progress_pct=0.0,
        platforms_scanned=[],
        findings_count=0,
        message="No audit in progress. Start one to get your score.",
    )
