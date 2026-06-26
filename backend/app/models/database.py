"""SQLAlchemy database models (MySQL-compatible)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    contradictions_count: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[dict] = mapped_column(JSON, default=list)
    contradictions: Mapped[dict] = mapped_column(JSON, default=list)
    trust_report: Mapped[dict] = mapped_column(JSON, default=dict)
    claims: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    verification_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sources_used: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
