"""Social accounts and data upload endpoints."""

import uuid
import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.social_account import SocialAccount
from app.schemas.auth import MessageResponse
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


class SocialAccountResponse:
    pass


from pydantic import BaseModel
from typing import Optional


class AccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: Optional[str]
    connection_type: str
    last_scan_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountsListResponse(BaseModel):
    accounts: list[AccountResponse]


@router.get("", response_model=AccountsListResponse)
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id)
    )
    accounts = result.scalars().all()

    return AccountsListResponse(
        accounts=[AccountResponse.model_validate(a) for a in accounts]
    )


@router.post("/connect/twitter", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_twitter(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect X/Twitter account. In production, this uses OAuth 2.0 flow."""
    # Check if already connected
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
            SocialAccount.platform == "twitter",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Twitter account already connected",
        )

    # Create placeholder connection (OAuth flow would happen in frontend)
    account = SocialAccount(
        user_id=current_user.id,
        platform="twitter",
        connection_type="api",
        platform_username="pending_oauth",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    return AccountResponse.model_validate(account)


@router.post("/upload", response_model=MessageResponse)
async def upload_data_archive(
    platform: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a data archive from a social media platform."""
    valid_platforms = {"instagram", "tiktok", "facebook", "linkedin"}
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )

    # Validate file type
    if not file.filename or not (
        file.filename.endswith(".zip")
        or file.filename.endswith(".json")
        or file.filename.endswith(".html")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be .zip, .json, or .html format",
        )

    # Save to temp directory for processing
    os.makedirs(settings.TEMP_UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(
        settings.TEMP_UPLOAD_DIR,
        f"{current_user.id}_{platform}_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    )

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Create or update social account record
        result = await db.execute(
            select(SocialAccount).where(
                SocialAccount.user_id == current_user.id,
                SocialAccount.platform == platform,
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            account = SocialAccount(
                user_id=current_user.id,
                platform=platform,
                connection_type="upload",
                last_scan_at=datetime.utcnow(),
            )
            db.add(account)
        else:
            account.last_scan_at = datetime.utcnow()

        await db.commit()

        # TODO: Process the archive in background
        # For now, the archive_processor service would handle this
        # and create findings from the extracted data

    finally:
        # Zero data retention: delete the uploaded file after processing
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return MessageResponse(
        message=f"{platform.title()} data archive uploaded and processing. "
                f"Your score will be updated once processing is complete."
    )


@router.delete("/{account_id}", response_model=MessageResponse)
async def disconnect_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    await db.delete(account)
    await db.commit()

    return MessageResponse(message=f"{account.platform.title()} account disconnected")
