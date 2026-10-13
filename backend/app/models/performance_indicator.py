"""
ADAPT — PerformanceIndicator Model

Performance Indicators belong to Program Outcomes (POs).
Each PO has one or more PIs. LOs are mapped to PIs to derive LO→PI→PO traceability.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PerformanceIndicator(Base):
    __tablename__ = "performance_indicators"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("program_outcomes.id"), nullable=False, index=True
    )
    pi_code: Mapped[str] = mapped_column(
        String(15), unique=True, nullable=False
    )  # PI1.1, PI1.2, PI2.1, ...
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    program_outcome = relationship("ProgramOutcome", back_populates="performance_indicators", lazy="selectin")
    lo_mappings = relationship(
        "LOPIMapping", back_populates="performance_indicator", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PerformanceIndicator {self.pi_code}>"
