"""Dispute endpoints."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.finding import Finding
from app.models.dispute import Dispute
from app.schemas.dispute import (
    CreateDisputeRequest,
    ResolveDisputeRequest,
    DisputeResponse,
    DisputeListResponse,
)
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["disputes"])


@router.post("/findings/{finding_id}/dispute", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def create_dispute(
    finding_id: uuid.UUID,
    request: CreateDisputeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify finding belongs to user
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.user_id == current_user.id,
        )
    )
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    if finding.is_disputed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This finding already has an active dispute",
        )

    # Create dispute
    dispute = Dispute(
        user_id=current_user.id,
        finding_id=finding_id,
        reason=request.reason,
        supporting_evidence=request.supporting_evidence,
        status="pending",
    )
    db.add(dispute)

    # Mark finding as disputed
    finding.is_disputed = True
    finding.dispute_status = "pending"
    finding.dispute_reason = request.reason

    await db.commit()
    await db.refresh(dispute)

    return DisputeResponse.model_validate(dispute)


@router.get("/disputes", response_model=DisputeListResponse)
async def list_disputes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dispute).where(Dispute.user_id == current_user.id).order_by(Dispute.submitted_at.desc())
    )
    disputes = result.scalars().all()

    return DisputeListResponse(
        disputes=[DisputeResponse.model_validate(d) for d in disputes],
        total=len(disputes),
    )


@router.get("/disputes/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(
    dispute_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.user_id == current_user.id,
        )
    )
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )

    return DisputeResponse.model_validate(dispute)


@router.put("/disputes/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    request: ResolveDisputeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a dispute (admin action)."""
    result = await db.execute(
        select(Dispute).where(Dispute.id == dispute_id)
    )
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )

    if dispute.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute has already been resolved",
        )

    dispute.status = request.resolution
    dispute.reviewer_notes = request.reviewer_notes
    dispute.resolved_at = datetime.utcnow()

    finding_result = await db.execute(
        select(Finding).where(Finding.id == dispute.finding_id)
    )
    finding = finding_result.scalar_one_or_none()
    if finding:
        finding.dispute_status = request.resolution
        if request.resolution == "overturned":
            finding.final_score_impact = 0.0

    await db.commit()
    await db.refresh(dispute)

    return DisputeResponse.model_validate(dispute)
