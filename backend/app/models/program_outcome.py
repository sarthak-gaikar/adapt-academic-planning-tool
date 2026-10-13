"""
ADAPT — ProgramOutcome Model

Institution-wide Program Outcomes (POs) — typically 12 as per NBA/AICTE.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProgramOutcome(Base):
    __tablename__ = "program_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    po_code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False
    )  # PO1, PO2, ..., PSO1, PSO2
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # PO | PSO
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    performance_indicators = relationship(
        "PerformanceIndicator", back_populates="program_outcome", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ProgramOutcome {self.po_code}>"
