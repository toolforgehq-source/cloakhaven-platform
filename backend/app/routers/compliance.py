"""GDPR, FCRA, and compliance endpoints."""

import uuid
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.user import User
from app.models.finding import Finding
from app.models.score import Score, ScoreHistory
from app.models.social_account import SocialAccount
from app.models.dispute import Dispute
from app.models.audit_log import AuditLog
from app.schemas.auth import MessageResponse
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["compliance"])

# FCRA disclaimer text — required on all employer-facing reports
FCRA_DISCLAIMER = (
    "IMPORTANT NOTICE: This report is provided for informational purposes only and "
    "is NOT a consumer report as defined by the Fair Credit Reporting Act (FCRA), "
    "15 U.S.C. § 1681 et seq. This report must NOT be used as a factor in determining "
    "a consumer's eligibility for credit, insurance, employment, or any other purpose "
    "covered by the FCRA. The information in this report is based on publicly available "
    "data and automated analysis, and may not be complete or accurate. Any employment "
    "decisions should be based on direct assessment of the candidate through interviews, "
    "reference checks, and other lawful methods. Cloak Haven does not guarantee the "
    "accuracy of this information and is not liable for decisions made based on this data."
)

DISPUTE_SLA_DAYS = 30  # Maximum days to resolve a dispute


@router.get("/compliance/fcra-notice")
async def get_fcra_notice():
    """Return the FCRA compliance disclaimer text."""
    return {
        "disclaimer": FCRA_DISCLAIMER,
        "version": "1.0",
        "effective_date": "2026-01-01",
    }


@router.get("/user/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 20 — Data portability. Export all user data as JSON.

    Returns a complete export of all data Cloak Haven holds about the user,
    including their profile, findings, scores, social accounts, and disputes.
    """
    # Gather all user data
    findings_result = await db.execute(
        select(Finding).where(Finding.user_id == current_user.id)
    )
    findings = findings_result.scalars().all()

    score_result = await db.execute(
        select(Score).where(Score.user_id == current_user.id)
    )
    score = score_result.scalar_one_or_none()

    history_result = await db.execute(
        select(ScoreHistory).where(ScoreHistory.user_id == current_user.id)
    )
    score_history = history_result.scalars().all()

    accounts_result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id)
    )
    social_accounts = accounts_result.scalars().all()

    disputes_result = await db.execute(
        select(Dispute).where(Dispute.user_id == current_user.id)
    )
    disputes = disputes_result.scalars().all()

    # Log the export for compliance audit trail
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="data_export",
        details={"reason": "user_request"},
    )
    db.add(audit_entry)
    await db.commit()

    export_data = {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "user_id": str(current_user.id),
            "format_version": "1.0",
        },
        "profile": {
            "email": current_user.email,
            "full_name": current_user.full_name,
            "display_name": current_user.display_name,
            "date_of_birth": str(current_user.date_of_birth) if current_user.date_of_birth else None,
            "email_verified": current_user.email_verified,
            "subscription_tier": current_user.subscription_tier,
            "profile_visibility": current_user.profile_visibility,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "score": {
            "overall_score": score.overall_score if score else None,
            "social_media_score": score.social_media_score if score else None,
            "web_presence_score": score.web_presence_score if score else None,
            "posting_behavior_score": score.posting_behavior_score if score else None,
            "score_accuracy_pct": score.score_accuracy_pct if score else None,
            "calculated_at": score.calculated_at.isoformat() if score and score.calculated_at else None,
        },
        "score_history": [
            {
                "overall_score": h.overall_score,
                "social_media_score": h.social_media_score,
                "web_presence_score": h.web_presence_score,
                "posting_behavior_score": h.posting_behavior_score,
                "recorded_at": h.recorded_at.isoformat() if h.recorded_at else None,
            }
            for h in score_history
        ],
        "social_accounts": [
            {
                "platform": a.platform,
                "platform_username": a.platform_username,
                "connection_type": a.connection_type,
                "last_scan_at": a.last_scan_at.isoformat() if a.last_scan_at else None,
            }
            for a in social_accounts
        ],
        "findings": [
            {
                "source": f.source,
                "source_type": f.source_type,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "evidence_snippet": f.evidence_snippet,
                "evidence_url": f.evidence_url,
                "original_date": f.original_date.isoformat() if f.original_date else None,
                "is_disputed": f.is_disputed,
                "dispute_status": f.dispute_status,
                "base_score_impact": f.base_score_impact,
                "final_score_impact": f.final_score_impact,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in findings
        ],
        "disputes": [
            {
                "finding_id": str(d.finding_id),
                "reason": d.reason,
                "supporting_evidence": d.supporting_evidence,
                "status": d.status,
                "reviewer_notes": d.reviewer_notes,
                "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
                "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
            }
            for d in disputes
        ],
    }

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=cloakhaven-export-{current_user.id}.json",
        },
    )


@router.delete("/user/data", response_model=MessageResponse)
async def delete_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 17 — Right to erasure (right to be forgotten).

    Permanently deletes all user data including findings, scores,
    social accounts, and disputes. The user account itself is also deleted.
    This action is irreversible.
    """
    user_id = current_user.id

    # Log deletion for compliance audit trail (before deleting)
    audit_entry = AuditLog(
        user_id=user_id,
        action="data_deletion",
        details={"reason": "user_request", "email": current_user.email},
    )
    db.add(audit_entry)

    # Cascade delete handles findings, scores, social accounts, disputes
    # because all FK relationships have ondelete="CASCADE"
    await db.delete(current_user)
    await db.commit()

    logger.info("User %s data deleted (GDPR erasure request)", user_id)

    return MessageResponse(
        message="All your data has been permanently deleted. Your account no longer exists."
    )


@router.post("/auth/resend-verification", response_model=MessageResponse)
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resend email verification link."""
    if current_user.email_verified:
        return MessageResponse(message="Email is already verified")

    from app.utils.security import generate_verification_token
    from app.services.email_service import send_verification_email

    token = generate_verification_token()
    current_user.email_verification_token = token
    await db.commit()

    try:
        send_verification_email(current_user.email, token, current_user.full_name or "")
    except Exception as e:
        logger.warning("Failed to send verification email: %s", e)

    return MessageResponse(message="Verification email sent. Check your inbox.")
