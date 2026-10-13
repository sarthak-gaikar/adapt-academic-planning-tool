"""
ADAPT — LearningOutcome Model

Unit-level Learning Outcomes with Bloom ordering, CO and PI mapping support.
Each LO belongs to a SyllabusUnit and is ordered by increasing Bloom complexity within that unit.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("syllabus_units.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    lo_code: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # LO1.1, LO1.2, LO2.1, ...
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    bloom_level: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # Remember | Understand | Apply | Analyze | Evaluate | Create
    bloom_order: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # 1-6 deterministic Bloom hierarchy position
    bloom_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    subject = relationship("Subject", back_populates="learning_outcomes")
    unit = relationship("SyllabusUnit", back_populates="learning_outcomes", lazy="selectin")
    generation_run = relationship("GenerationRun", lazy="selectin")
    co_mappings = relationship(
        "LOCOMapping", back_populates="learning_outcome", lazy="selectin"
    )
    pi_mappings = relationship(
        "LOPIMapping", back_populates="learning_outcome", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<LearningOutcome {self.lo_code}: {self.bloom_level}>"
