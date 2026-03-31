"""Admin panel endpoints — user management, dispute review, system health."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, desc
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.finding import Finding
from app.models.dispute import Dispute
from app.models.score import Score
from app.models.audit_log import AuditLog
from app.models.partner_key import PartnerApiKey
from app.middleware.auth import get_admin_user


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    total_users: int
    verified_users: int
    paying_users: int
    total_findings: int
    total_disputes: int
    pending_disputes: int
    avg_score: float
    users_today: int


class AdminUserItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    display_name: Optional[str]
    email_verified: bool
    subscription_tier: str
    subscription_status: str
    is_admin: bool
    is_profile_claimed: bool
    profile_visibility: str
    created_at: datetime
    overall_score: Optional[int] = None
    findings_count: int = 0
    disputes_count: int = 0

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class AdminDisputeItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: Optional[str]
    finding_id: uuid.UUID
    finding_title: str
    finding_severity: str
    reason: str
    supporting_evidence: Optional[str]
    status: str
    reviewer_notes: Optional[str]
    submitted_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AdminDisputeListResponse(BaseModel):
    disputes: list[AdminDisputeItem]
    total: int
    page: int
    page_size: int


class ResolveDisputeBody(BaseModel):
    resolution: str  # "overturned" or "upheld"
    reviewer_notes: Optional[str] = None


class SetAdminBody(BaseModel):
    is_admin: bool


class SetTierBody(BaseModel):
    tier: str  # "free", "audit", "subscriber", "employer"


class CreatePartnerKeyBody(BaseModel):
    partner_name: str
    contact_email: str
    rate_limit_per_minute: int = 100


class PartnerKeyResponse(BaseModel):
    id: str
    partner_name: str
    api_key: str
    contact_email: str
    is_active: bool
    rate_limit_per_minute: int
    total_requests: int
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Dashboard Stats ──────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics for the admin dashboard."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    verified_users = (await db.execute(
        select(func.count(User.id)).where(User.email_verified.is_(True))
    )).scalar() or 0
    paying_users = (await db.execute(
        select(func.count(User.id)).where(User.subscription_tier != "free")
    )).scalar() or 0
    total_findings = (await db.execute(select(func.count(Finding.id)))).scalar() or 0
    total_disputes = (await db.execute(select(func.count(Dispute.id)))).scalar() or 0
    pending_disputes = (await db.execute(
        select(func.count(Dispute.id)).where(Dispute.status == "pending")
    )).scalar() or 0
    avg_score_result = (await db.execute(select(func.avg(Score.overall_score)))).scalar()
    avg_score = round(avg_score_result, 1) if avg_score_result else 0.0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    users_today = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )).scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        verified_users=verified_users,
        paying_users=paying_users,
        total_findings=total_findings,
        total_disputes=total_disputes,
        pending_disputes=pending_disputes,
        avg_score=avg_score,
        users_today=users_today,
    )


# ── User Management ─────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional filtering."""
    query = select(User)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if tier:
        query = query.where(User.subscription_tier == tier)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Enrich with score/findings/disputes counts
    items = []
    for u in users:
        score_result = await db.execute(
            select(Score.overall_score).where(Score.user_id == u.id)
        )
        overall_score = score_result.scalar_one_or_none()

        findings_count = (await db.execute(
            select(func.count(Finding.id)).where(Finding.user_id == u.id)
        )).scalar() or 0

        disputes_count = (await db.execute(
            select(func.count(Dispute.id)).where(Dispute.user_id == u.id)
        )).scalar() or 0

        items.append(AdminUserItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            display_name=u.display_name,
            email_verified=u.email_verified,
            subscription_tier=u.subscription_tier,
            subscription_status=u.subscription_status,
            is_admin=u.is_admin,
            is_profile_claimed=u.is_profile_claimed,
            profile_visibility=u.profile_visibility,
            created_at=u.created_at,
            overall_score=overall_score,
            findings_count=findings_count,
            disputes_count=disputes_count,
        ))

    return AdminUserListResponse(users=items, total=total, page=page, page_size=page_size)


@router.put("/users/{user_id}/admin", response_model=dict)
async def set_user_admin(
    user_id: uuid.UUID,
    body: SetAdminBody,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke admin privileges."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = body.is_admin
    await db.commit()
    return {"message": f"Admin status set to {body.is_admin}"}


@router.put("/users/{user_id}/tier", response_model=dict)
async def set_user_tier(
    user_id: uuid.UUID,
    body: SetTierBody,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually set a user's subscription tier."""
    valid_tiers = {"free", "audit", "subscriber", "employer"}
    if body.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_tier = body.tier
    user.subscription_status = "active" if body.tier != "free" else "inactive"
    await db.commit()
    return {"message": f"Tier set to {body.tier}"}


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all their data."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


# ── Dispute Management ───────────────────────────────────────────────────

@router.get("/disputes", response_model=AdminDisputeListResponse)
async def list_all_disputes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all disputes platform-wide with optional status filter."""
    query = select(Dispute)
    if status_filter:
        query = query.where(Dispute.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(
        case((Dispute.status == "pending", 0), else_=1),
        desc(Dispute.submitted_at),
    ).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    disputes = result.scalars().all()

    items = []
    for d in disputes:
        # Get user info
        user_result = await db.execute(select(User).where(User.id == d.user_id))
        user = user_result.scalar_one_or_none()
        # Get finding info
        finding_result = await db.execute(select(Finding).where(Finding.id == d.finding_id))
        finding = finding_result.scalar_one_or_none()

        items.append(AdminDisputeItem(
            id=d.id,
            user_id=d.user_id,
            user_email=user.email if user else "unknown",
            user_name=user.full_name if user else None,
            finding_id=d.finding_id,
            finding_title=finding.title if finding else "Unknown finding",
            finding_severity=finding.severity if finding else "unknown",
            reason=d.reason,
            supporting_evidence=d.supporting_evidence,
            status=d.status,
            reviewer_notes=d.reviewer_notes,
            submitted_at=d.submitted_at,
            resolved_at=d.resolved_at,
        ))

    return AdminDisputeListResponse(
        disputes=items, total=total, page=page, page_size=page_size,
    )


@router.put("/disputes/{dispute_id}/resolve", response_model=dict)
async def admin_resolve_dispute(
    dispute_id: uuid.UUID,
    body: ResolveDisputeBody,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a dispute as admin."""
    if body.resolution not in ("overturned", "upheld"):
        raise HTTPException(status_code=400, detail="Resolution must be 'overturned' or 'upheld'")

    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.status != "pending":
        raise HTTPException(status_code=409, detail="Dispute already resolved")

    dispute.status = body.resolution
    dispute.reviewer_notes = body.reviewer_notes
    dispute.resolved_at = datetime.utcnow()

    # Update the finding
    finding_result = await db.execute(select(Finding).where(Finding.id == dispute.finding_id))
    finding = finding_result.scalar_one_or_none()
    if finding:
        finding.dispute_status = body.resolution
        if body.resolution == "overturned":
            finding.final_score_impact = 0.0

    await db.commit()
    return {"message": f"Dispute {body.resolution}"}


# ── Audit Log ────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get system audit log."""
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    result = await db.execute(
        select(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── Partner Key Management ──────────────────────────────────────────────

@router.get("/partner-keys")
async def list_partner_keys(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all partner API keys."""
    result = await db.execute(select(PartnerApiKey).order_by(desc(PartnerApiKey.created_at)))
    keys = result.scalars().all()
    return {
        "keys": [
            {
                "id": str(k.id),
                "partner_name": k.partner_name,
                "api_key": k.api_key[:12] + "..." + k.api_key[-4:],
                "contact_email": k.contact_email,
                "is_active": k.is_active,
                "rate_limit_per_minute": k.rate_limit_per_minute,
                "total_requests": k.total_requests,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ],
        "total": len(keys),
    }


@router.post("/partner-keys", response_model=PartnerKeyResponse, status_code=201)
async def create_partner_key(
    body: CreatePartnerKeyBody,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new partner API key."""
    key = PartnerApiKey(
        partner_name=body.partner_name,
        contact_email=body.contact_email,
        rate_limit_per_minute=body.rate_limit_per_minute,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return PartnerKeyResponse(
        id=str(key.id),
        partner_name=key.partner_name,
        api_key=key.api_key,
        contact_email=key.contact_email,
        is_active=key.is_active,
        rate_limit_per_minute=key.rate_limit_per_minute,
        total_requests=key.total_requests,
        created_at=key.created_at,
        last_used_at=key.last_used_at,
    )


@router.delete("/partner-keys/{key_id}", response_model=dict)
async def revoke_partner_key(
    key_id: uuid.UUID,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) a partner API key."""
    result = await db.execute(select(PartnerApiKey).where(PartnerApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Partner key not found")
    key.is_active = False
    await db.commit()
    return {"message": f"Partner key for '{key.partner_name}' revoked"}
