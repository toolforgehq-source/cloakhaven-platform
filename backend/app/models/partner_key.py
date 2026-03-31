"""Partner API key model for B2B score access."""

import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PartnerApiKey(Base):
    __tablename__ = "partner_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
        default=lambda: f"ch_live_{secrets.token_urlsafe(32)}"
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=100)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
