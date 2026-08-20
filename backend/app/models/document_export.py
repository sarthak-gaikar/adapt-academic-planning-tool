"""
ADAPT — DocumentExport Model

Tracks exported DOCX/PDF files.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentExport(Base):
    __tablename__ = "document_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )  # FK to exam, assignment, aap, etc.
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # EXAM | ASSIGNMENT | AAP | ANSWER_KEY | CO_REPORT
    format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # DOCX | PDF
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    template_config: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DocumentExport {self.source_type} ({self.format})>"
