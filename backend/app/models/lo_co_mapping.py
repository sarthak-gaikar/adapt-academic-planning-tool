"""
ADAPT — LO-CO Mapping Model

Maps Learning Outcomes to Course Outcomes with structured relational data.
Each LO can map to one or more COs with mapping strength and faculty approval.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LOCOMapping(Base):
    __tablename__ = "lo_co_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_outcomes.id"), nullable=False, index=True
    )
    co_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_outcomes.id"), nullable=False, index=True
    )
    mapping_strength: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 0=None, 1=Low, 2=Medium, 3=High
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | APPROVED
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
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
    learning_outcome = relationship("LearningOutcome", back_populates="co_mappings")
    course_outcome = relationship("CourseOutcome", back_populates="lo_mappings", lazy="selectin")

    def __repr__(self) -> str:
        return f"<LOCOMapping LO={self.lo_id} → CO={self.co_id}: {self.mapping_strength}>"
