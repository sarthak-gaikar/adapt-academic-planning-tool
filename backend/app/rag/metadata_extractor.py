"""
ADAPT — Metadata Extractor

Enriches document chunks with academic context (Subject, Unit, Topic, Source, Authority).
"""

from typing import Any, Dict, Optional
from uuid import UUID


class MetadataExtractor:
    """Enriches raw chunks with complete institutional metadata for pgvector."""

    @staticmethod
    def build_chunk_metadata(
        document_id: UUID,
        subject_id: UUID,
        document_type: str,
        source_filename: str,
        unit_number: Optional[int] = None,
        topic: Optional[str] = None,
        academic_year: Optional[str] = None,
        authority: str = "UNIVERSITY",
    ) -> Dict[str, Any]:
        return {
            "document_id": str(document_id),
            "subject_id": str(subject_id),
            "document_type": document_type,
            "source_filename": source_filename,
            "unit_number": unit_number,
            "topic": topic,
            "academic_year": academic_year or "2024-25",
            "authority": authority,
        }
