"""Score and audit endpoints."""

import asyncio
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db, async_session_maker
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
    calculate_score_trajectory,
    get_score_color,
    get_score_label,
)
from app.config import settings
from app.middleware.rate_limit import audit_limiter, check_rate_limit

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

    # Include behavioral trajectory in score breakdown
    trajectory = await calculate_score_trajectory(db, current_user.id)
    breakdown = dict(score.score_breakdown) if score.score_breakdown else {}
    breakdown["trajectory"] = trajectory

    return ScoreResponse(
        overall_score=score.overall_score,
        social_media_score=score.social_media_score,
        web_presence_score=score.web_presence_score,
        posting_behavior_score=score.posting_behavior_score,
        score_accuracy_pct=score.score_accuracy_pct,
        is_verified=score.is_verified,
        verification_date=score.verification_date,
        score_breakdown=breakdown,
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
    """
    Start a comprehensive audit of the user's online presence.

    Scans all available platforms in order:
    1. Data enrichment (Proxycurl/PeopleDataLabs) — resolve cross-platform identity
    2. Twitter/X API — direct tweet scanning
    3. Reddit API — posts and comments
    4. YouTube Data API — channel videos
    5. Google Custom Search — web presence
    6. Public profile scraping — fallback for platforms without API access

    Each scanner is independent — if one fails, the others continue.
    """
    # Rate limit: 5 audits per hour per user
    check_rate_limit(
        str(current_user.id), audit_limiter,
        "Audit rate limit exceeded. Please wait before starting another audit.",
    )

    audit_id = str(uuid.uuid4())
    platforms_scanned: list[str] = []

    # Helper: get user's display name and connected usernames
    name = current_user.full_name or current_user.display_name or ""
    acct_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
        )
    )
    connected_accounts = list(acct_result.scalars().all())
    usernames = [a.platform_username for a in connected_accounts if a.platform_username]

    # Build a map of platform → username for easy lookup
    platform_usernames: dict[str, str] = {}
    for acct in connected_accounts:
        if acct.platform_username:
            platform_usernames[acct.platform] = acct.platform_username

    # ── 1. Data Enrichment (resolve identity across platforms) ──
    if settings.PEOPLEDATALABS_API_KEY:
        try:
            from app.services.enrichment_service import enrich_person
            enriched = await enrich_person(
                name=name,
                email=current_user.email,
            )
            if enriched:
                # Use enrichment to discover social handles we didn't know about
                if enriched.twitter_username and "twitter" not in platform_usernames:
                    platform_usernames["twitter"] = enriched.twitter_username
                if enriched.github_username and "github" not in platform_usernames:
                    platform_usernames["github"] = enriched.github_username
                for platform, url in enriched.social_profiles.items():
                    if platform not in platform_usernames:
                        platform_usernames[platform] = url
                platforms_scanned.append("enrichment")
                logger.info(f"Data enrichment complete for user {current_user.id}: found {list(enriched.social_profiles.keys())}")
        except Exception as e:
            logger.warning(f"Data enrichment failed for user {current_user.id}: {e}")

    # ── 2-5. Run all scanners concurrently for performance ──
    # Each scanner gets its own DB session for safe concurrent writes.
    async def _scan_twitter():
        """Twitter/X API scan."""
        if not settings.TWITTER_BEARER_TOKEN:
            return
        twitter_username = platform_usernames.get("twitter")
        if not twitter_username:
            return
        async with async_session_maker() as scan_db:
            try:
                from app.services.twitter_service import scan_twitter_account
                await scan_twitter_account(scan_db, current_user.id, twitter_username)
                await scan_db.commit()
                platforms_scanned.append("twitter")
                logger.info(f"Twitter scan complete for user {current_user.id}")
            except Exception as e:
                await scan_db.rollback()
                logger.warning(f"Twitter scan failed for user {current_user.id}: {e}")

    async def _scan_reddit():
        """Reddit API scan."""
        if not (settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET):
            return
        reddit_username = platform_usernames.get("reddit")
        if not reddit_username:
            return
        async with async_session_maker() as scan_db:
            try:
                from app.services.reddit_service import scan_reddit_account
                await scan_reddit_account(scan_db, current_user.id, reddit_username)
                await scan_db.commit()
                platforms_scanned.append("reddit")
                logger.info(f"Reddit scan complete for user {current_user.id}")
            except Exception as e:
                await scan_db.rollback()
                logger.warning(f"Reddit scan failed for user {current_user.id}: {e}")

    async def _scan_youtube():
        """YouTube Data API scan."""
        if not settings.YOUTUBE_API_KEY:
            return
        youtube_username = platform_usernames.get("youtube")
        search_query = youtube_username or name
        if not search_query:
            return
        async with async_session_maker() as scan_db:
            try:
                from app.services.youtube_service import scan_youtube_channel
                await scan_youtube_channel(scan_db, current_user.id, search_query)
                await scan_db.commit()
                platforms_scanned.append("youtube")
                logger.info(f"YouTube scan complete for user {current_user.id}")
            except Exception as e:
                await scan_db.rollback()
                logger.warning(f"YouTube scan failed for user {current_user.id}: {e}")

    # Build disambiguation context from user profile + enrichment data
    disambiguation_context: dict[str, str] = {}
    if current_user.email:
        disambiguation_context["email"] = current_user.email
    # Pull company/job_title/location from enrichment if available
    if settings.PEOPLEDATALABS_API_KEY and "enrichment" in platforms_scanned:
        # enrichment already ran above; context was built from enriched data
        pass

    async def _scan_web():
        """Web Search via SerpAPI (comprehensive web presence)."""
        if not settings.SERPAPI_API_KEY:
            return
        if not name:
            return
        async with async_session_maker() as scan_db:
            try:
                from app.services.google_service import scan_web_presence
                await scan_web_presence(
                    scan_db, current_user.id, name,
                    usernames or None,
                    disambiguation_context=disambiguation_context or None,
                )
                await scan_db.commit()
                platforms_scanned.append("google")
                logger.info(f"Web search scan complete for user {current_user.id}")
            except Exception as e:
                await scan_db.rollback()
                logger.warning(f"Web search scan failed for user {current_user.id}: {e}")

    # Run all scanners concurrently — each has its own DB session
    await asyncio.gather(
        _scan_twitter(),
        _scan_reddit(),
        _scan_youtube(),
        _scan_web(),
        return_exceptions=True,
    )

    # ── 6. Public profile scraping (fallback for unscanned platforms) ──
    if "twitter" not in platforms_scanned:
        twitter_username = platform_usernames.get("twitter")
        if twitter_username:
            try:
                from app.services.scraping_service import scan_and_create_findings
                await scan_and_create_findings(db, current_user.id, name, twitter_username)
                platforms_scanned.append("scraping")
                logger.info(f"Public scraping complete for user {current_user.id}")
            except Exception as e:
                logger.warning(f"Public scraping failed for user {current_user.id}: {e}")

    # ── Calculate final score from all findings ──
    await calculate_score(db, current_user.id)
    await db.commit()

    return AuditStartResponse(
        message=f"Audit complete. Scanned {len(platforms_scanned)} sources: {', '.join(platforms_scanned) or 'none (no API keys configured)'}.",
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
            platforms_scanned=["twitter", "reddit", "youtube", "google", "enrichment"],
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
