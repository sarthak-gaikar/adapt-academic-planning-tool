"""
ADAPT — CO-PO Mapping Model

Maps Course Outcomes to Program Outcomes with suggested + approved levels.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class COPOMapping(Base):
    __tablename__ = "co_po_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    co_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_outcomes.id"), nullable=False
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_outcomes.id"), nullable=False
    )
    suggested_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0-3
    approved_level: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 0-3, set by faculty
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    subject = relationship("Subject", back_populates="co_po_mappings")
    course_outcome = relationship("CourseOutcome", back_populates="co_po_mappings")
    program_outcome = relationship("ProgramOutcome", lazy="selectin")

    def __repr__(self) -> str:
        return f"<COPOMapping CO={self.co_id} → PO={self.po_id}: {self.suggested_level}>"
