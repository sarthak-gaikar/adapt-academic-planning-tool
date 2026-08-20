"""
ADAPT — Assignment & AssignmentQuestion Models
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )  # Generation parameters: units, bloom, difficulty, etc.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED | ARCHIVED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    validation_report: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subject = relationship("Subject", back_populates="assignments")
    generation_run = relationship("GenerationRun", lazy="selectin")
    assignment_questions = relationship(
        "AssignmentQuestion",
        back_populates="assignment",
        lazy="selectin",
        order_by="AssignmentQuestion.sequence_order",
    )
    answer_key = relationship(
        "AnswerKey",
        back_populates="assignment",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Assignment '{self.title}' {self.total_marks}m>"


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assignments.id"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id"), nullable=False
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    assignment = relationship("Assignment", back_populates="assignment_questions")
    question = relationship("Question", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AssignmentQuestion #{self.sequence_order} {self.marks}m>"
