"""B2B Partner API — allows businesses to pull user scores with API key auth."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.score import Score
from app.models.finding import Finding
from app.models.social_account import SocialAccount
from app.models.partner_key import PartnerApiKey
from app.services.scoring_engine import get_score_color, get_score_label
from app.middleware.rate_limit import partner_limiter, check_rate_limit

router = APIRouter(prefix="/api/v1/partner", tags=["partner"])


class PartnerScoreRequest(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None


class PartnerScoreResponse(BaseModel):
    user_id: str
    display_name: str
    overall_score: int
    social_media_score: int
    web_presence_score: int
    posting_behavior_score: int
    score_accuracy_pct: float
    is_verified: bool
    score_color: str
    score_label: str
    platforms_analyzed: list[str]
    total_findings: int
    calculated_at: str
    fcra_disclaimer: str


class PartnerKeyInfo(BaseModel):
    partner_name: str
    rate_limit_per_minute: int
    total_requests: int
    is_active: bool


async def get_partner_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> PartnerApiKey:
    """Validate partner API key from X-API-Key header."""
    result = await db.execute(
        select(PartnerApiKey).where(
            PartnerApiKey.api_key == x_api_key,
            PartnerApiKey.is_active.is_(True),
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    # Update usage stats
    key.total_requests += 1
    key.last_used_at = datetime.utcnow()
    await db.commit()
    return key


@router.post("/score", response_model=PartnerScoreResponse)
async def pull_user_score(
    request: PartnerScoreRequest,
    partner: PartnerApiKey = Depends(get_partner_key),
    db: AsyncSession = Depends(get_db),
):
    """Pull a user's score. Requires valid partner API key.

    Partners must provide either email or user_id to look up the user.
    Only returns scores for users with public visibility.
    """
    # Rate limit per partner API key
    check_rate_limit(
        str(partner.id), partner_limiter,
        "Partner rate limit exceeded. Please try again later.",
    )

    if not request.email and not request.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either email or user_id",
        )

    # Look up user
    if request.user_id:
        try:
            uid = uuid.UUID(request.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        user = await db.get(User, uid)
    else:
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

    # Return same error for not-found and private to prevent user enumeration
    if not user or user.profile_visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No public score found for this identifier",
        )

    # Get score
    result = await db.execute(
        select(Score).where(Score.user_id == user.id)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score available for this user",
        )

    # Get platforms
    accounts_result = await db.execute(
        select(SocialAccount.platform).where(SocialAccount.user_id == user.id).distinct()
    )
    platforms = [row[0] for row in accounts_result.all()]

    # Count findings
    findings_result = await db.execute(
        select(Finding).where(Finding.user_id == user.id)
    )
    findings_count = len(findings_result.scalars().all())

    return PartnerScoreResponse(
        user_id=str(user.id),
        display_name=user.display_name or user.full_name or "Anonymous",
        overall_score=score.overall_score,
        social_media_score=score.social_media_score,
        web_presence_score=score.web_presence_score,
        posting_behavior_score=score.posting_behavior_score,
        score_accuracy_pct=score.score_accuracy_pct,
        is_verified=score.is_verified,
        score_color=get_score_color(score.overall_score),
        score_label=get_score_label(score.overall_score),
        platforms_analyzed=platforms,
        total_findings=findings_count,
        calculated_at=score.calculated_at.isoformat(),
        fcra_disclaimer=(
            "This score is for informational purposes only and is not a consumer report "
            "under the Fair Credit Reporting Act (FCRA). It should not be used as the "
            "sole basis for employment, housing, credit, or insurance decisions."
        ),
    )


@router.get("/info", response_model=PartnerKeyInfo)
async def get_partner_info(
    partner: PartnerApiKey = Depends(get_partner_key),
):
    """Get info about the current partner API key."""
    return PartnerKeyInfo(
        partner_name=partner.partner_name,
        rate_limit_per_minute=partner.rate_limit_per_minute,
        total_requests=partner.total_requests,
        is_active=partner.is_active,
    )
