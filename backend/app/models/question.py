"""
ADAPT — Question Model

Individual questions with full academic metadata for the question bank.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DESCRIPTIVE"
    )  # MCQ | SHORT | LONG | NUMERICAL | CODING | DESCRIPTIVE
    marks: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MEDIUM"
    )  # EASY | MEDIUM | HARD
    bloom_level: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # Remember | Understand | Apply | Analyze | Evaluate | Create
    bloom_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    co_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    unit_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reference_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marking_scheme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_context: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )  # RAG context used for generation
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED | ARCHIVED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
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
    subject = relationship("Subject", back_populates="questions")
    generation_run = relationship("GenerationRun", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Question {self.marks}m {self.bloom_level} U{self.unit_number}>"
