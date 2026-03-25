"""Score and audit endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.score import Score, ScoreHistory
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
    # For now, calculate score from existing findings
    # In production, this triggers background scanning of connected accounts + Google
    audit_id = str(uuid.uuid4())

    # Calculate score from existing findings
    score = await calculate_score(db, current_user.id)
    await db.commit()

    return AuditStartResponse(
        message="Audit started. Your score is being calculated.",
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
