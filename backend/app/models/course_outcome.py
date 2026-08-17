"""
ADAPT — CourseOutcome Model
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CourseOutcome(Base):
    __tablename__ = "course_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    co_code: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # CO1, CO2, ...
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    bloom_level: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # Remember | Understand | Apply | Analyze | Evaluate | Create
    bloom_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bloom_model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supporting_units: Mapped[dict] = mapped_column(JSON, nullable=True, default=list)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED | ARCHIVED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    subject = relationship("Subject", back_populates="course_outcomes")
    generation_run = relationship("GenerationRun", lazy="selectin")
    co_po_mappings = relationship(
        "COPOMapping", back_populates="course_outcome", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CourseOutcome {self.co_code}: {self.bloom_level}>"
