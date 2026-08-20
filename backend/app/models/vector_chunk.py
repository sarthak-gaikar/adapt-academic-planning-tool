"""
ADAPT — VectorChunk Model

Stores document chunks with embeddings for RAG retrieval.
Embeddings are stored as JSON-serialized float lists for SQLite compatibility.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VectorChunk(Base):
    __tablename__ = "vector_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    syllabus_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SYLLABUS | NOTES | PREV_PAPER | REFERENCE | GUIDELINES
    unit_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding stored as JSON text (list of floats) for SQLite compatibility
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # UNIVERSITY | FACULTY | REFERENCE
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document = relationship("Document", back_populates="vector_chunks")

    @property
    def embedding(self) -> Optional[List[float]]:
        """Deserialize embedding from JSON text."""
        if self.embedding_json:
            return json.loads(self.embedding_json)
        return None

    @embedding.setter
    def embedding(self, value: Optional[List[float]]):
        """Serialize embedding to JSON text."""
        if value is not None:
            self.embedding_json = json.dumps(value)
        else:
            self.embedding_json = None

    def __repr__(self) -> str:
        return f"<VectorChunk {self.document_type} U{self.unit_number} #{self.chunk_index}>"
