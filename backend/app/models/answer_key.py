"""
ADAPT — AnswerKey Model
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_paper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_papers.id"), nullable=True, index=True
    )
    assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=True, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    answers: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # [{question_id, model_answer, key_points, steps, marking_scheme}]
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    exam_paper = relationship("ExamPaper", back_populates="answer_key")
    assignment = relationship("Assignment", back_populates="answer_key")
    generation_run = relationship("GenerationRun", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AnswerKey exam={self.exam_paper_id} assignment={self.assignment_id}>"
