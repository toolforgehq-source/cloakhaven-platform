"""
Reddit Integration Service

Connects to the Reddit API to fetch user profiles and posts/comments,
then processes them through the content classifier to create findings.

Reddit API docs: https://www.reddit.com/dev/api/
Auth: OAuth2 client credentials flow using client_id and client_secret.
"""

import uuid
import logging
from datetime import datetime
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.finding import Finding
from app.services.content_classifier import classify_content

logger = logging.getLogger(__name__)

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"


class RedditServiceError(Exception):
    pass


async def _get_reddit_token() -> str:
    """Get an OAuth2 access token from Reddit."""
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        raise RedditServiceError("Reddit API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            REDDIT_AUTH_URL,
            auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": settings.REDDIT_USER_AGENT},
        )

    if response.status_code != 200:
        raise RedditServiceError(f"Reddit auth failed: {response.status_code}")

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise RedditServiceError("No access token in Reddit response")
    return token


async def get_reddit_user(username: str) -> dict:
    """Fetch a Reddit user's profile data."""
    token = await _get_reddit_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REDDIT_API_BASE}/user/{username}/about",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.REDDIT_USER_AGENT,
            },
        )

    if response.status_code == 404:
        raise RedditServiceError(f"Reddit user u/{username} not found")
    if response.status_code != 200:
        raise RedditServiceError(f"Reddit API error: {response.status_code}")

    data = response.json()
    return data.get("data", {})


async def get_user_posts(
    username: str,
    limit: int = 100,
    sort: str = "new",
) -> list[dict]:
    """Fetch a Reddit user's recent posts (submissions)."""
    token = await _get_reddit_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REDDIT_API_BASE}/user/{username}/submitted",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.REDDIT_USER_AGENT,
            },
            params={"limit": min(limit, 100), "sort": sort},
        )

    if response.status_code != 200:
        raise RedditServiceError(f"Reddit API error: {response.status_code}")

    data = response.json()
    children = data.get("data", {}).get("children", [])
    return [child.get("data", {}) for child in children]


async def get_user_comments(
    username: str,
    limit: int = 100,
    sort: str = "new",
) -> list[dict]:
    """Fetch a Reddit user's recent comments."""
    token = await _get_reddit_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REDDIT_API_BASE}/user/{username}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.REDDIT_USER_AGENT,
            },
            params={"limit": min(limit, 100), "sort": sort},
        )

    if response.status_code != 200:
        raise RedditServiceError(f"Reddit API error: {response.status_code}")

    data = response.json()
    children = data.get("data", {}).get("children", [])
    return [child.get("data", {}) for child in children]


async def scan_reddit_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    reddit_username: str,
) -> list[Finding]:
    """
    Full scan of a Reddit account:
    1. Fetch user profile
    2. Fetch recent posts and comments
    3. Classify each piece of content
    4. Create findings
    """
    findings: list[Finding] = []

    # Fetch posts
    try:
        posts = await get_user_posts(reddit_username)
    except RedditServiceError as e:
        logger.warning(f"Failed to fetch Reddit posts for u/{reddit_username}: {e}")
        posts = []

    for post in posts:
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        text = f"{title} {selftext}".strip()
        if not text:
            continue

        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        total_engagement = score + num_comments

        # Parse created_utc
        original_date = None
        created_utc = post.get("created_utc")
        if created_utc:
            try:
                original_date = datetime.utcfromtimestamp(created_utc)
            except (ValueError, OSError):
                pass

        subreddit = post.get("subreddit", "")
        permalink = post.get("permalink", "")
        url = f"https://reddit.com{permalink}" if permalink else ""

        classification = classify_content(
            text=text,
            source="reddit",
            url=url,
            engagement_count=total_engagement,
        )

        if classification.category == "neutral":
            continue

        finding = Finding(
            user_id=user_id,
            source="reddit",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"Reddit post in r/{subreddit}: {classification.title}",
            description=classification.description,
            evidence_snippet=text[:500],
            evidence_url=url,
            original_date=original_date,
            platform_engagement_count=total_engagement,
            base_score_impact=classification.base_score_impact,
            final_score_impact=classification.base_score_impact,
        )
        db.add(finding)
        findings.append(finding)

    # Fetch comments
    try:
        comments = await get_user_comments(reddit_username)
    except RedditServiceError as e:
        logger.warning(f"Failed to fetch Reddit comments for u/{reddit_username}: {e}")
        comments = []

    for comment in comments:
        text = comment.get("body", "").strip()
        if not text:
            continue

        score = comment.get("score", 0)
        total_engagement = max(score, 0)

        original_date = None
        created_utc = comment.get("created_utc")
        if created_utc:
            try:
                original_date = datetime.utcfromtimestamp(created_utc)
            except (ValueError, OSError):
                pass

        subreddit = comment.get("subreddit", "")
        permalink = comment.get("permalink", "")
        url = f"https://reddit.com{permalink}" if permalink else ""

        classification = classify_content(
            text=text,
            source="reddit",
            url=url,
            engagement_count=total_engagement,
        )

        if classification.category == "neutral":
            continue

        finding = Finding(
            user_id=user_id,
            source="reddit",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"Reddit comment in r/{subreddit}: {classification.title}",
            description=classification.description,
            evidence_snippet=text[:500],
            evidence_url=url,
            original_date=original_date,
            platform_engagement_count=total_engagement,
            base_score_impact=classification.base_score_impact,
            final_score_impact=classification.base_score_impact,
        )
        db.add(finding)
        findings.append(finding)

    if findings:
        await db.flush()

    logger.info(
        f"Reddit scan for u/{reddit_username}: {len(posts)} posts, "
        f"{len(comments)} comments → {len(findings)} findings"
    )
    return findings
