"""
Data Archive Processor Service

Handles uploaded data archives from social media platforms:
- Instagram: JSON export
- TikTok: JSON export
- Facebook: HTML/JSON export
- LinkedIn: CSV/JSON export

Processes content through the classifier and creates findings.
Zero data retention — raw files are deleted after processing.
"""

import json
import os
import uuid
import zipfile
import tempfile
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.services.content_classifier import classify_uploaded_content


class ArchiveProcessorError(Exception):
    pass


async def process_archive(
    db: AsyncSession,
    user_id: uuid.UUID,
    file_path: str,
    platform: str,
) -> list[Finding]:
    """
    Process a data archive file and create findings.
    Dispatches to platform-specific processors.
    """
    processors = {
        "instagram": _process_instagram,
        "tiktok": _process_tiktok,
        "facebook": _process_facebook,
        "linkedin": _process_linkedin,
    }

    processor = processors.get(platform)
    if not processor:
        raise ArchiveProcessorError(f"Unsupported platform: {platform}")

    # Extract if zip
    extracted_dir = None
    working_path = file_path

    if file_path.endswith(".zip"):
        extracted_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(extracted_dir)
            working_path = extracted_dir
        except zipfile.BadZipFile:
            raise ArchiveProcessorError("Invalid zip file")

    try:
        findings = await processor(db, user_id, working_path)
    finally:
        # Zero data retention: clean up all extracted files
        if extracted_dir and os.path.exists(extracted_dir):
            import shutil
            shutil.rmtree(extracted_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)

    return findings


async def _process_instagram(
    db: AsyncSession,
    user_id: uuid.UUID,
    path: str,
) -> list[Finding]:
    """Process Instagram data export."""
    findings: list[Finding] = []

    # Instagram exports have various JSON files
    # Look for posts, comments, messages, etc.
    json_files = _find_json_files(path)

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Process posts
        posts = _extract_instagram_posts(data)
        for post in posts:
            text = post.get("text", "")
            if not text or len(text.strip()) < 5:
                continue

            classification = classify_uploaded_content(
                text=text,
                platform="instagram",
                engagement_count=post.get("likes", 0),
            )

            if classification.category == "neutral":
                continue

            timestamp = post.get("timestamp")
            original_date = None
            if timestamp:
                try:
                    original_date = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError):
                    pass

            finding = Finding(
                user_id=user_id,
                source="instagram",
                source_type="private_upload",
                category=classification.category,
                severity=classification.severity,
                title=classification.title,
                description=classification.description,
                evidence_snippet=text[:500],
                original_date=original_date,
                platform_engagement_count=post.get("likes", 0),
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings


async def _process_tiktok(
    db: AsyncSession,
    user_id: uuid.UUID,
    path: str,
) -> list[Finding]:
    """Process TikTok data export."""
    findings: list[Finding] = []
    json_files = _find_json_files(path)

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # TikTok exports have video descriptions, comments, etc.
        items = _extract_tiktok_content(data)
        for item in items:
            text = item.get("text", "")
            if not text or len(text.strip()) < 5:
                continue

            classification = classify_uploaded_content(
                text=text,
                platform="tiktok",
                engagement_count=item.get("likes", 0),
            )

            if classification.category == "neutral":
                continue

            finding = Finding(
                user_id=user_id,
                source="tiktok",
                source_type="private_upload",
                category=classification.category,
                severity=classification.severity,
                title=classification.title,
                description=classification.description,
                evidence_snippet=text[:500],
                original_date=item.get("date"),
                platform_engagement_count=item.get("likes", 0),
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings


async def _process_facebook(
    db: AsyncSession,
    user_id: uuid.UUID,
    path: str,
) -> list[Finding]:
    """Process Facebook data export."""
    findings: list[Finding] = []
    json_files = _find_json_files(path)

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        items = _extract_facebook_content(data)
        for item in items:
            text = item.get("text", "")
            if not text or len(text.strip()) < 5:
                continue

            classification = classify_uploaded_content(
                text=text,
                platform="facebook",
                engagement_count=item.get("reactions", 0),
            )

            if classification.category == "neutral":
                continue

            finding = Finding(
                user_id=user_id,
                source="facebook",
                source_type="private_upload",
                category=classification.category,
                severity=classification.severity,
                title=classification.title,
                description=classification.description,
                evidence_snippet=text[:500],
                original_date=item.get("date"),
                platform_engagement_count=item.get("reactions", 0),
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings


async def _process_linkedin(
    db: AsyncSession,
    user_id: uuid.UUID,
    path: str,
) -> list[Finding]:
    """Process LinkedIn data export."""
    findings: list[Finding] = []
    json_files = _find_json_files(path)

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        items = _extract_linkedin_content(data)
        for item in items:
            text = item.get("text", "")
            if not text or len(text.strip()) < 5:
                continue

            classification = classify_uploaded_content(
                text=text,
                platform="linkedin",
                engagement_count=item.get("likes", 0),
            )

            if classification.category == "neutral":
                continue

            finding = Finding(
                user_id=user_id,
                source="linkedin",
                source_type="private_upload",
                category=classification.category,
                severity=classification.severity,
                title=classification.title,
                description=classification.description,
                evidence_snippet=text[:500],
                original_date=item.get("date"),
                platform_engagement_count=item.get("likes", 0),
                base_score_impact=classification.base_score_impact,
                final_score_impact=classification.base_score_impact,
            )
            db.add(finding)
            findings.append(finding)

    await db.flush()
    return findings


# ============================================================
# Helpers for extracting content from platform-specific formats
# ============================================================

def _find_json_files(path: str) -> list[str]:
    """Recursively find all JSON files in a directory or return the file itself."""
    if os.path.isfile(path) and path.endswith(".json"):
        return [path]
    if not os.path.isdir(path):
        return []

    json_files = []
    for root, _dirs, files in os.walk(path):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))
    return json_files


def _extract_instagram_posts(data: dict | list) -> list[dict]:
    """Extract post texts from Instagram export JSON."""
    posts = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Instagram media JSON format
                text = item.get("title", "") or ""
                if not text and "node" in item:
                    text = item["node"].get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
                if text:
                    posts.append({
                        "text": text,
                        "timestamp": item.get("creation_timestamp") or item.get("taken_at_timestamp"),
                        "likes": item.get("likes", 0),
                    })
    elif isinstance(data, dict):
        # Check common Instagram export keys
        for key in ["media", "posts", "comments", "stories"]:
            if key in data:
                sub = data[key]
                if isinstance(sub, list):
                    posts.extend(_extract_instagram_posts(sub))

    return posts


def _extract_tiktok_content(data: dict | list) -> list[dict]:
    """Extract content from TikTok export JSON."""
    items = []

    if isinstance(data, dict):
        # TikTok export format
        for key in ["Video", "Comment", "Activity"]:
            section = data.get(key, {})
            if isinstance(section, dict):
                for sub_key, sub_val in section.items():
                    if isinstance(sub_val, list):
                        for entry in sub_val:
                            if isinstance(entry, dict):
                                text = entry.get("Desc", "") or entry.get("Comment", "") or entry.get("text", "")
                                if text:
                                    items.append({
                                        "text": text,
                                        "likes": entry.get("Likes", 0),
                                        "date": None,
                                    })

    return items


def _extract_facebook_content(data: dict | list) -> list[dict]:
    """Extract content from Facebook export JSON."""
    items = []

    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                # Facebook post format
                post_data = entry.get("data", [])
                if isinstance(post_data, list):
                    for pd in post_data:
                        if isinstance(pd, dict) and "post" in pd:
                            items.append({
                                "text": pd["post"],
                                "reactions": 0,
                                "date": None,
                            })
                # Direct text
                text = entry.get("post", "") or entry.get("comment", "") or entry.get("text", "")
                if text:
                    items.append({"text": text, "reactions": 0, "date": None})

    elif isinstance(data, dict):
        for key in ["posts", "comments", "reactions", "status_updates"]:
            if key in data and isinstance(data[key], list):
                items.extend(_extract_facebook_content(data[key]))

    return items


def _extract_linkedin_content(data: dict | list) -> list[dict]:
    """Extract content from LinkedIn export JSON."""
    items = []

    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                text = entry.get("text", "") or entry.get("commentary", "") or entry.get("message", "")
                if text:
                    items.append({"text": text, "likes": 0, "date": None})

    elif isinstance(data, dict):
        for key in ["shares", "posts", "comments", "messages"]:
            if key in data and isinstance(data[key], list):
                items.extend(_extract_linkedin_content(data[key]))

    return items
