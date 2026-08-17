"""
ADAPT — InstitutionConfig Model

Key-value config store for institution settings, exam rules, AAP templates, etc.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InstitutionConfig(Base):
    __tablename__ = "institution_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # INSTITUTION | EXAM | AAP | TEMPLATE | BLOOM
    description: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<InstitutionConfig {self.key} ({self.category})>"
