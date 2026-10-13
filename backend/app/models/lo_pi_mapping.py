"""
ADAPT — LO-PI Mapping Model

Maps Learning Outcomes to Performance Indicators with PO derivation.
Since each PI belongs to a PO, the system automatically derives LO → PI → PO relationships.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LOPIMapping(Base):
    __tablename__ = "lo_pi_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_outcomes.id"), nullable=False, index=True
    )
    pi_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("performance_indicators.id"), nullable=False, index=True
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("program_outcomes.id"), nullable=False, index=True
    )  # Denormalized: PI's parent PO for efficient queries
    mapping_level: Mapped[int] = mapped_column(
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
    learning_outcome = relationship("LearningOutcome", back_populates="pi_mappings")
    performance_indicator = relationship("PerformanceIndicator", back_populates="lo_mappings", lazy="selectin")
    program_outcome = relationship("ProgramOutcome", lazy="selectin")

    def __repr__(self) -> str:
        return f"<LOPIMapping LO={self.lo_id} → PI={self.pi_id} → PO={self.po_id}: {self.mapping_level}>"
