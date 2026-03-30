"""Findings endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.user import User
from app.models.finding import Finding
from app.schemas.finding import FindingResponse, FindingsListResponse
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


@router.get("", response_model=FindingsListResponse)
async def list_findings(
    source: str | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Finding).where(Finding.user_id == current_user.id)

    if source:
        query = query.where(Finding.source == source)
    if category:
        query = query.where(Finding.category == category)
    if severity:
        query = query.where(Finding.severity == severity)

    # Count total
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(desc(Finding.final_score_impact)).offset(
        (page - 1) * page_size
    ).limit(page_size)

    result = await db.execute(query)
    findings = result.scalars().all()

    return FindingsListResponse(
        findings=[FindingResponse.model_validate(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

    return FindingResponse.model_validate(finding)
