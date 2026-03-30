"""Dispute request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class CreateDisputeRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)
    supporting_evidence: Optional[str] = Field(None, max_length=5000)


class DisputeResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    reason: str
    supporting_evidence: Optional[str]
    status: str
    reviewer_notes: Optional[str]
    submitted_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ResolveDisputeRequest(BaseModel):
    resolution: str = Field(pattern="^(overturned|upheld)$")
    reviewer_notes: Optional[str] = Field(None, max_length=5000)


class DisputeListResponse(BaseModel):
    disputes: list[DisputeResponse]
    total: int
