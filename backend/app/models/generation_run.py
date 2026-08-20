"""
ADAPT — GenerationRun Model

Tracks every AI generation operation for observability and debugging.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    operation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SYLLABUS_ANALYSIS | CO_GENERATION | BLOOM_CLASSIFICATION | ...
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_params: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    retrieved_documents: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=list
    )  # IDs of chunks retrieved
    token_usage_prompt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_usage_completion: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="RUNNING"
    )  # RUNNING | COMPLETED | FAILED
    validation_result: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    subject = relationship("Subject", back_populates="generation_runs")
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<GenerationRun {self.operation} ({self.status})>"
