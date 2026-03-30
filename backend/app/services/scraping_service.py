"""
Public Profile Scraping Service

Headless browser-based scraping for public social media profiles.
Uses Selenium with ChromeDriver in headless mode to extract publicly
available information from social media platforms.

This is the backbone of the "score anyone" feature — it allows
Cloak Haven to build a digital reputation profile for any person
using only their name and/or usernames, without requiring API access.
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.public_profile import PublicProfile
from app.services.content_classifier import classify_content

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPost:
    """A single scraped post from a public profile."""
    text: str
    platform: str
    url: str = ""
    engagement_count: int = 0
    posted_at: Optional[datetime] = None


@dataclass
class ScrapedProfile:
    """Aggregated data from scraping a person's public profiles."""
    name: str
    username: str = ""
    bio: str = ""
    platforms_found: list[str] = field(default_factory=list)
    posts: list[ScrapedPost] = field(default_factory=list)
    follower_count: int = 0
    profile_urls: dict[str, str] = field(default_factory=dict)


class ScrapingServiceError(Exception):
    pass


def _try_import_selenium():
    """Try to import selenium; return None if not available."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return webdriver, Options, Service, By, WebDriverWait, EC
    except ImportError:
        return None


def _create_headless_driver():
    """Create a headless Chrome WebDriver instance."""
    imports = _try_import_selenium()
    if imports is None:
        raise ScrapingServiceError(
            "Selenium is not installed. Install with: pip install selenium"
        )

    webdriver, Options, Service, By, WebDriverWait, EC = imports

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(15)
        return driver, By, WebDriverWait, EC
    except Exception as e:
        raise ScrapingServiceError(f"Failed to create Chrome driver: {e}")


async def scrape_twitter_public(username: str) -> list[ScrapedPost]:
    """
    Scrape publicly visible tweets from a Twitter/X profile.
    Falls back gracefully if the profile is private or not found.
    """
    posts: list[ScrapedPost] = []

    try:
        driver, By, WebDriverWait, EC = _create_headless_driver()
    except ScrapingServiceError:
        logger.warning("Selenium not available, skipping Twitter scrape")
        return posts

    try:
        url = f"https://x.com/{username}"
        driver.get(url)

        # Wait for tweets to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetText']"))
            )
        except Exception:
            logger.info(f"No tweets found for @{username} (may be private or not exist)")
            return posts

        # Extract tweet texts
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweetText']")

        for elem in tweet_elements[:50]:  # Limit to 50 most recent
            try:
                text = elem.text.strip()
                if text:
                    posts.append(ScrapedPost(
                        text=text,
                        platform="twitter",
                        url=url,
                        engagement_count=0,  # Hard to extract reliably from DOM
                    ))
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"Error scraping Twitter for @{username}: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return posts


async def scrape_public_profiles(
    name: str,
    username: Optional[str] = None,
) -> ScrapedProfile:
    """
    Scrape publicly available information about a person.
    Tries multiple platforms and aggregates results.
    """
    profile = ScrapedProfile(name=name, username=username or "")

    # Try Twitter if username provided
    if username:
        try:
            twitter_posts = await scrape_twitter_public(username)
            if twitter_posts:
                profile.posts.extend(twitter_posts)
                profile.platforms_found.append("twitter")
                profile.profile_urls["twitter"] = f"https://x.com/{username}"
        except Exception as e:
            logger.warning(f"Twitter scrape failed for {username}: {e}")

    return profile


async def scan_and_create_findings(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    username: Optional[str] = None,
) -> list[Finding]:
    """
    Full scraping pipeline:
    1. Scrape public profiles
    2. Classify each post
    3. Create findings in the database
    """
    scraped = await scrape_public_profiles(name, username)
    findings: list[Finding] = []

    for post in scraped.posts:
        classification = classify_content(
            text=post.text,
            source=post.platform,
            url=post.url,
            engagement_count=post.engagement_count,
        )

        # Skip neutral content
        if classification.category == "neutral":
            continue

        finding = Finding(
            user_id=user_id,
            source=post.platform,
            source_type="public_scrape",
            category=classification.category,
            severity=classification.severity,
            title=classification.title,
            description=classification.description,
            evidence_snippet=post.text[:500] if post.text else None,
            evidence_url=post.url,
            original_date=post.posted_at,
            platform_engagement_count=post.engagement_count,
            base_score_impact=classification.base_score_impact,
            final_score_impact=classification.base_score_impact,
        )
        db.add(finding)
        findings.append(finding)

    if findings:
        await db.flush()

    return findings


async def create_or_update_public_profile(
    db: AsyncSession,
    name: str,
    username: Optional[str] = None,
    matched_user_id: Optional[uuid.UUID] = None,
) -> PublicProfile:
    """
    Create or update a public profile entry for a person.
    This is used by the employer search and public scoring features.
    """
    from sqlalchemy import select, or_

    # Check if profile already exists
    conditions = [PublicProfile.lookup_name.ilike(f"%{name}%")]
    if username:
        conditions.append(PublicProfile.lookup_username.ilike(f"%{username}%"))

    result = await db.execute(
        select(PublicProfile).where(or_(*conditions))
    )
    profile = result.scalars().first()

    now = datetime.utcnow()

    if profile:
        profile.last_scanned_at = now
        if matched_user_id:
            profile.matched_user_id = matched_user_id
    else:
        profile = PublicProfile(
            lookup_name=name,
            lookup_username=username,
            is_claimed=matched_user_id is not None,
            matched_user_id=matched_user_id,
            last_scanned_at=now,
        )
        db.add(profile)

    await db.flush()
    return profile
