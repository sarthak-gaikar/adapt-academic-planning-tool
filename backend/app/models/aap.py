"""
ADAPT — AAPPlan Model

Academic Activity Plan with configurable template and validation.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AAPPlan(Base):
    __tablename__ = "aap_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("generation_runs.id"), nullable=True
    )
    template_config: Mapped[dict] = mapped_column(
        JSON, nullable=True, default=dict
    )  # Column definitions, format settings
    plan_data: Mapped[dict] = mapped_column(
        JSON, nullable=True
    )  # Actual week-by-week plan rows
    total_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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
    subject = relationship("Subject", back_populates="aap_plans")
    generation_run = relationship("GenerationRun", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AAPPlan v{self.version} weeks={self.total_weeks}>"
