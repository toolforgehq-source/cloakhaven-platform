"""Finding request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class FindingResponse(BaseModel):
    id: uuid.UUID
    source: str
    source_type: str
    category: str
    severity: str
    title: str
    description: Optional[str]
    evidence_snippet: Optional[str]
    evidence_url: Optional[str]
    original_date: Optional[datetime]
    platform_engagement_count: int
    is_disputed: bool
    dispute_status: Optional[str]
    is_juvenile_content: bool
    base_score_impact: float
    final_score_impact: float
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingsListResponse(BaseModel):
    findings: list[FindingResponse]
    total: int
    page: int
    page_size: int


class FindingFilterParams(BaseModel):
    source: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    page: int = 1
    page_size: int = 20
