import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # public, private_upload
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    evidence_snippet: Mapped[str | None] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    original_date: Mapped[datetime | None] = mapped_column(DateTime)
    platform_engagement_count: Mapped[int] = mapped_column(Integer, default=0)
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False)
    dispute_status: Mapped[str | None] = mapped_column(String(20))
    dispute_reason: Mapped[str | None] = mapped_column(Text)
    is_juvenile_content: Mapped[bool] = mapped_column(Boolean, default=False)
    base_score_impact: Mapped[float] = mapped_column(Float, nullable=False)
    final_score_impact: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user = relationship("User", back_populates="findings")
    disputes = relationship("Dispute", back_populates="finding", cascade="all, delete-orphan")
