"""
ADAPT — ExamBlueprint, ExamPaper, ExamQuestion Models
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExamBlueprint(Base):
    __tablename__ = "exam_blueprints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    exam_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # MSE | ESE
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    units_covered: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=list
    )  # [1, 2, 3]
    difficulty_distribution: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )  # {"EASY": 30, "MEDIUM": 50, "HARD": 20}
    bloom_distribution: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )  # {"Remember": 10, "Understand": 30, ...}
    co_distribution: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )
    section_structure: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=list
    )  # [{name, marks, num_questions, question_type, ...}]
    question_type_config: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )
    has_internal_choice: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
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
    subject = relationship("Subject", back_populates="exam_blueprints")
    exam_papers = relationship("ExamPaper", back_populates="blueprint", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ExamBlueprint {self.exam_type} {self.total_marks}m>"


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exam_blueprints.id"), nullable=False
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    exam_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # MSE | ESE
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paper_data: Mapped[dict] = mapped_column(
        JSON, nullable=True
    )  # Full paper structure
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False)
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
    subject = relationship("Subject", back_populates="exam_papers")
    blueprint = relationship("ExamBlueprint", back_populates="exam_papers")
    generation_run = relationship("GenerationRun", lazy="selectin")
    exam_questions = relationship(
        "ExamQuestion",
        back_populates="exam_paper",
        lazy="selectin",
        order_by="ExamQuestion.sequence_order",
    )
    answer_key = relationship(
        "AnswerKey",
        back_populates="exam_paper",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ExamPaper {self.exam_type} '{self.title}'>"


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_paper_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exam_papers.id"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id"), nullable=False
    )
    section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)
    is_compulsory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    choice_group: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # Questions in same group are OR choices

    # Relationships
    exam_paper = relationship("ExamPaper", back_populates="exam_questions")
    question = relationship("Question", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ExamQuestion #{self.sequence_order} {self.marks}m>"
