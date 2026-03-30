import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmployerSearch(Base):
    __tablename__ = "employer_searches"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    employer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    searched_name: Mapped[str] = mapped_column(String(255), nullable=False)
    searched_username: Mapped[str | None] = mapped_column(String(255))
    result_profile_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
