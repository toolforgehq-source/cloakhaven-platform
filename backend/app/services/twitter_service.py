"""
X/Twitter Integration Service

Connects to the Twitter API v2 to fetch user profiles and tweets,
then processes them through the content classifier to create findings.
"""

import uuid
from datetime import datetime
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.finding import Finding
from app.models.social_account import SocialAccount
from app.services.content_classifier import classify_content_llm


TWITTER_API_BASE = "https://api.twitter.com/2"


class TwitterServiceError(Exception):
    pass


async def get_twitter_user(username: str) -> dict:
    """Fetch a Twitter user profile by username."""
    if not settings.TWITTER_BEARER_TOKEN:
        raise TwitterServiceError("Twitter API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
            params={
                "user.fields": "id,name,username,description,profile_image_url,public_metrics,created_at,verified"
            },
        )

    if response.status_code == 401:
        raise TwitterServiceError("Invalid Twitter API credentials")
    if response.status_code == 404:
        raise TwitterServiceError(f"Twitter user @{username} not found")
    if response.status_code != 200:
        raise TwitterServiceError(f"Twitter API error: {response.status_code}")

    data = response.json()
    if "data" not in data:
        raise TwitterServiceError(f"Twitter user @{username} not found")

    return data["data"]


async def get_user_tweets(
    twitter_user_id: str,
    max_results: int = 100,
) -> list[dict]:
    """Fetch recent tweets for a Twitter user."""
    if not settings.TWITTER_BEARER_TOKEN:
        raise TwitterServiceError("Twitter API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWITTER_API_BASE}/users/{twitter_user_id}/tweets",
            headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
            params={
                "max_results": min(max_results, 100),
                "tweet.fields": "id,text,created_at,public_metrics,entities",
            },
        )

    if response.status_code != 200:
        raise TwitterServiceError(f"Twitter API error: {response.status_code}")

    data = response.json()
    return data.get("data", [])


async def scan_twitter_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    twitter_username: str,
) -> list[Finding]:
    """
    Full scan of a Twitter account:
    1. Fetch user profile
    2. Fetch recent tweets
    3. Classify each tweet
    4. Create findings
    5. Return all findings created
    """
    # Get Twitter user
    twitter_user = await get_twitter_user(twitter_username)
    twitter_user_id = twitter_user["id"]

    # Update social account with real data
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == "twitter",
        )
    )
    account = result.scalar_one_or_none()
    if account:
        account.platform_user_id = twitter_user_id
        account.platform_username = twitter_username
        account.last_scan_at = datetime.utcnow()

    # Fetch tweets
    tweets = await get_user_tweets(twitter_user_id)

    findings: list[Finding] = []

    for tweet in tweets:
        text = tweet.get("text", "")
        metrics = tweet.get("public_metrics", {})
        created_at_str = tweet.get("created_at")

        retweet_count = metrics.get("retweet_count", 0)
        like_count = metrics.get("like_count", 0)
        reply_count = metrics.get("reply_count", 0)
        total_engagement = retweet_count + like_count + reply_count

        # Parse created_at
        original_date = None
        if created_at_str:
            try:
                original_date = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Classify the tweet using LLM (falls back to rule-based)
        classification = await classify_content_llm(
            text=text,
            source="twitter",
            url=f"https://twitter.com/{twitter_username}/status/{tweet.get('id', '')}",
            engagement_count=total_engagement,
        )

        # Skip neutral content — no finding needed
        if classification.category == "neutral":
            continue

        # Create finding
        finding = Finding(
            user_id=user_id,
            source="twitter",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=classification.title,
            description=classification.description,
            evidence_snippet=text[:500] if text else None,
            evidence_url=f"https://twitter.com/{twitter_username}/status/{tweet.get('id', '')}",
            original_date=original_date,
            platform_engagement_count=total_engagement,
            base_score_impact=classification.base_score_impact,
            final_score_impact=classification.base_score_impact,  # Will be recalculated by scoring engine
        )
        db.add(finding)
        findings.append(finding)

    await db.flush()
    return findings
