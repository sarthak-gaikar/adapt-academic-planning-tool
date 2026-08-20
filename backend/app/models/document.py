"""
ADAPT — Document Model

Represents uploaded files (syllabus PDFs, DOCX, notes, previous papers, etc.)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # PDF | DOCX
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SYLLABUS | NOTES | PREV_PAPER | REFERENCE | GUIDELINES
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING | PROCESSING | COMPLETED | FAILED
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subject = relationship("Subject", back_populates="documents")
    uploader = relationship("User", lazy="selectin")
    syllabus = relationship("Syllabus", back_populates="document", uselist=False)
    vector_chunks = relationship(
        "VectorChunk", back_populates="document", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Document {self.filename} ({self.document_type})>"
