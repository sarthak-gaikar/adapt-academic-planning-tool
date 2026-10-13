"""
ADAPT — SystemDocument Model

Tracks institutional/system-level knowledge base documents that have been
ingested into the RAG vector store. Used for idempotent re-ingestion:
content hashes are compared to skip unchanged files on restart.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemDocument(Base):
    __tablename__ = "system_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, unique=True
    )  # Relative path within knowledge_base
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # PO_PI_GUIDELINE | AAP_FORMAT | MSE_SAMPLE | ESE_SAMPLE
    source_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SYSTEM"
    )  # Always SYSTEM for institutional docs
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hex digest
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING | PROCESSING | COMPLETED | FAILED
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SystemDocument {self.document_type}: {self.filename}>"
