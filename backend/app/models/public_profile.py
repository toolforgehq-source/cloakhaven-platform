import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, Boolean, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PublicProfile(Base):
    __tablename__ = "public_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    lookup_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    lookup_username: Mapped[str | None] = mapped_column(String(255), index=True)
    matched_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id")
    )
    public_score: Mapped[int | None] = mapped_column(Integer)
    score_accuracy_pct: Mapped[float | None] = mapped_column(Float)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime)
    public_findings_summary: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # --- Passive scan accuracy fields ---
    identity_confidence: Mapped[float | None] = mapped_column(Float, default=0.0)
    match_context: Mapped[dict | None] = mapped_column(JSON)
    identity_match_reasoning: Mapped[str | None] = mapped_column(String(2000))
    sources_scanned: Mapped[dict | None] = mapped_column(JSON)
    social_media_score: Mapped[int | None] = mapped_column(Integer)
    web_presence_score: Mapped[int | None] = mapped_column(Integer)
    posting_behavior_score: Mapped[int | None] = mapped_column(Integer)
    total_findings_count: Mapped[int | None] = mapped_column(Integer, default=0)
    scan_duration_seconds: Mapped[float | None] = mapped_column(Float)
    sources_scanned_count: Mapped[int | None] = mapped_column(Integer, default=0)
