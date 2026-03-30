"""
YouTube Data API Integration Service

Connects to the YouTube Data API v3 to fetch channel info, videos,
and comments, then processes them through the content classifier
to create findings.

YouTube API docs: https://developers.google.com/youtube/v3
"""

import uuid
import logging
from datetime import datetime
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.finding import Finding
from app.services.content_classifier import classify_content, classify_content_llm

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeServiceError(Exception):
    pass


async def search_channels(query: str, max_results: int = 5) -> list[dict]:
    """Search for YouTube channels matching a query (name or handle)."""
    if not settings.YOUTUBE_API_KEY:
        raise YouTubeServiceError("YouTube API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{YOUTUBE_API_BASE}/search",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "q": query,
                "type": "channel",
                "part": "snippet",
                "maxResults": min(max_results, 50),
            },
        )

    if response.status_code == 403:
        raise YouTubeServiceError("YouTube API quota exceeded or invalid key")
    if response.status_code != 200:
        raise YouTubeServiceError(f"YouTube API error: {response.status_code}")

    data = response.json()
    return data.get("items", [])


async def get_channel_details(channel_id: str) -> dict:
    """Get detailed info about a YouTube channel."""
    if not settings.YOUTUBE_API_KEY:
        raise YouTubeServiceError("YouTube API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "id": channel_id,
                "part": "snippet,statistics,contentDetails",
            },
        )

    if response.status_code != 200:
        raise YouTubeServiceError(f"YouTube API error: {response.status_code}")

    data = response.json()
    items = data.get("items", [])
    if not items:
        raise YouTubeServiceError(f"YouTube channel {channel_id} not found")
    return items[0]


async def get_channel_videos(
    channel_id: str,
    max_results: int = 50,
) -> list[dict]:
    """Fetch recent videos from a YouTube channel."""
    if not settings.YOUTUBE_API_KEY:
        raise YouTubeServiceError("YouTube API not configured")

    # First get the uploads playlist ID
    channel = await get_channel_details(channel_id)
    uploads_id = (
        channel.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )
    if not uploads_id:
        return []

    # Fetch videos from the uploads playlist
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{YOUTUBE_API_BASE}/playlistItems",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "playlistId": uploads_id,
                "part": "snippet",
                "maxResults": min(max_results, 50),
            },
        )

    if response.status_code != 200:
        raise YouTubeServiceError(f"YouTube API error: {response.status_code}")

    data = response.json()
    items = data.get("items", [])

    # Get video statistics for engagement counts
    video_ids = [
        item.get("snippet", {}).get("resourceId", {}).get("videoId")
        for item in items
        if item.get("snippet", {}).get("resourceId", {}).get("videoId")
    ]

    stats_map: dict[str, dict] = {}
    if video_ids:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "key": settings.YOUTUBE_API_KEY,
                    "id": ",".join(video_ids[:50]),
                    "part": "statistics",
                },
            )
        if response.status_code == 200:
            stats_data = response.json()
            for vid in stats_data.get("items", []):
                stats_map[vid["id"]] = vid.get("statistics", {})

    # Merge stats into items
    for item in items:
        video_id = item.get("snippet", {}).get("resourceId", {}).get("videoId", "")
        item["_stats"] = stats_map.get(video_id, {})

    return items


async def get_video_comments(
    video_id: str,
    max_results: int = 100,
) -> list[dict]:
    """Fetch top-level comments on a YouTube video."""
    if not settings.YOUTUBE_API_KEY:
        raise YouTubeServiceError("YouTube API not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{YOUTUBE_API_BASE}/commentThreads",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "videoId": video_id,
                "part": "snippet",
                "maxResults": min(max_results, 100),
                "order": "relevance",
            },
        )

    if response.status_code == 403:
        # Comments may be disabled
        return []
    if response.status_code != 200:
        raise YouTubeServiceError(f"YouTube API error: {response.status_code}")

    data = response.json()
    return data.get("items", [])


async def scan_youtube_channel(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel_query: str,
) -> list[Finding]:
    """
    Full scan of a YouTube channel:
    1. Search for the channel by name/handle
    2. Fetch recent videos
    3. Classify video titles and descriptions
    4. Optionally sample comments on recent videos
    5. Create findings
    """
    findings: list[Finding] = []

    # Find channel
    try:
        channels = await search_channels(channel_query, max_results=1)
    except YouTubeServiceError as e:
        logger.warning(f"YouTube channel search failed for '{channel_query}': {e}")
        return findings

    if not channels:
        logger.info(f"No YouTube channel found for '{channel_query}'")
        return findings

    channel_id = channels[0].get("snippet", {}).get("channelId") or channels[0].get("id", {}).get("channelId", "")
    if not channel_id:
        return findings

    channel_title = channels[0].get("snippet", {}).get("title", channel_query)

    # Fetch videos
    try:
        videos = await get_channel_videos(channel_id, max_results=50)
    except YouTubeServiceError as e:
        logger.warning(f"YouTube video fetch failed for channel {channel_id}: {e}")
        return findings

    for video in videos:
        snippet = video.get("snippet", {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        text = f"{title}. {description}".strip()
        if not text or text == ".":
            continue

        video_id = snippet.get("resourceId", {}).get("videoId", "")
        url = f"https://youtube.com/watch?v={video_id}" if video_id else ""

        # Parse publish date
        original_date = None
        published_at = snippet.get("publishedAt")
        if published_at:
            try:
                original_date = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Engagement from statistics
        stats = video.get("_stats", {})
        like_count = int(stats.get("likeCount", 0))
        comment_count = int(stats.get("commentCount", 0))
        total_engagement = like_count + comment_count

        classification = await classify_content_llm(
            text=text,
            source="youtube",
            url=url,
            engagement_count=total_engagement,
        )

        if classification.category == "neutral":
            continue

        finding = Finding(
            user_id=user_id,
            source="youtube",
            source_type="public",
            category=classification.category,
            severity=classification.severity,
            title=f"YouTube video: {title[:200]}",
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
        f"YouTube scan for '{channel_query}' (channel: {channel_title}): "
        f"{len(videos)} videos → {len(findings)} findings"
    )
    return findings
