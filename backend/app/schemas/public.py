"""Public profile and search schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class PublicSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=255)


class PublicProfileResponse(BaseModel):
    id: uuid.UUID
    lookup_name: str
    lookup_username: Optional[str]
    public_score: Optional[int]
    score_accuracy_pct: Optional[float]
    is_claimed: bool
    score_color: Optional[str]
    score_label: Optional[str]
    last_scanned_at: Optional[datetime]
    public_findings_summary: Optional[dict]

    model_config = {"from_attributes": True}


class PublicSearchResponse(BaseModel):
    results: list[PublicProfileResponse]
    total: int
    scan_pending: bool = False  # True when a background scan was triggered for a new name


class ClaimProfileRequest(BaseModel):
    profile_id: uuid.UUID


class ScoreCardResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    overall_score: int
    social_media_score: int
    web_presence_score: int
    posting_behavior_score: int
    score_accuracy_pct: float
    is_verified: bool
    score_color: str
    score_label: str
    calculated_at: datetime
    share_url: str
    platforms_analyzed: list[str] = []
    total_findings: int = 0
    category_breakdown: dict = {}


class EmployerSearchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    username: Optional[str] = None


class EmployerReportResponse(BaseModel):
    profile: PublicProfileResponse
    findings_summary: dict
    risk_level: str
    recommendation: str
    searched_at: datetime
    fcra_disclaimer: Optional[str] = None


class EmployerSearchHistoryItem(BaseModel):
    id: uuid.UUID
    searched_name: str
    searched_username: Optional[str]
    searched_at: datetime

    model_config = {"from_attributes": True}


class EmployerSearchHistoryResponse(BaseModel):
    searches: list[EmployerSearchHistoryItem]
    total: int
