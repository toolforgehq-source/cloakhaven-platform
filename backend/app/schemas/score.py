"""Score request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScoreResponse(BaseModel):
    overall_score: int
    social_media_score: int
    web_presence_score: int
    posting_behavior_score: int
    score_accuracy_pct: float
    is_verified: bool
    verification_date: Optional[datetime]
    score_breakdown: dict
    calculated_at: datetime
    score_color: str
    score_label: str

    model_config = {"from_attributes": True}


class ScoreHistoryItem(BaseModel):
    overall_score: int
    social_media_score: int
    web_presence_score: int
    posting_behavior_score: int
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ScoreHistoryResponse(BaseModel):
    history: list[ScoreHistoryItem]


class AuditStartResponse(BaseModel):
    message: str
    audit_id: str
    status: str


class AuditStatusResponse(BaseModel):
    status: str  # pending, scanning, processing, complete, failed
    progress_pct: float
    platforms_scanned: list[str]
    findings_count: int
    message: str
