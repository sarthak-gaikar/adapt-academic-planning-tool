"""
ADAPT — Vector Retrieval Engine

Performs cosine similarity search with metadata pre-filtering.
Uses Python-based similarity computation (SQLite compatible).

Supports three retrieval scopes:
  SYSTEM  — Institutional knowledge (PO-PI guidelines, sample papers, etc.)
  SUBJECT — Faculty-uploaded subject material (syllabus, notes, etc.)
  REQUEST — Temporary generation-scoped context (optional uploads)
"""

import json
import math
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.models.vector_chunk import VectorChunk

logger = get_logger("rag.retriever")


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors in pure Python."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class RetrievedChunk:
    """Represents a retrieved chunk with similarity score and metadata."""

    def __init__(
        self,
        chunk_id: UUID,
        content: str,
        score: float,
        unit_number: Optional[int] = None,
        topic: Optional[str] = None,
        document_type: str = "SYLLABUS",
        source: Optional[str] = None,
        source_scope: Optional[str] = "SUBJECT",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.score = score
        self.unit_number = unit_number
        self.topic = topic
        self.document_type = document_type
        self.source = source
        self.source_scope = source_scope or "SUBJECT"
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": str(self.chunk_id),
            "content": self.content,
            "score": round(self.score, 4),
            "unit_number": self.unit_number,
            "topic": self.topic,
            "document_type": self.document_type,
            "source": self.source,
            "source_scope": self.source_scope,
            "metadata": self.metadata,
        }


class VectorRetriever:
    """Retrieves relevant chunks using query embeddings and metadata filters."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_provider = get_embedding_provider()

    async def retrieve(
        self,
        query: str,
        subject_id: UUID,
        top_k: int = 5,
        unit_number: Optional[int] = None,
        document_type: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Embeds query, fetches candidate chunks from DB, and ranks by cosine similarity.
        """
        try:
            query_vector = await self.embedding_provider.embed_text(query)

            # Build query with metadata filters
            filters = [VectorChunk.subject_id == subject_id]
            if unit_number is not None:
                filters.append(VectorChunk.unit_number == unit_number)
            if document_type is not None:
                filters.append(VectorChunk.document_type == document_type)

            # Fetch all candidate chunks that have embeddings
            stmt = (
                select(VectorChunk)
                .where(and_(*filters))
                .where(VectorChunk.embedding_json.isnot(None))
            )

            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

            # Compute cosine similarity in Python and rank
            scored: List[tuple] = []
            for chunk in chunks:
                chunk_embedding = chunk.embedding
                if chunk_embedding:
                    similarity = _cosine_similarity(query_vector, chunk_embedding)
                    if similarity >= min_score:
                        scored.append((chunk, similarity))

            # Sort by similarity descending, take top_k
            scored.sort(key=lambda x: x[1], reverse=True)
            scored = scored[:top_k]

            retrieved: List[RetrievedChunk] = []
            for chunk_obj, similarity in scored:
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk_obj.id,
                        content=chunk_obj.content,
                        score=similarity,
                        unit_number=chunk_obj.unit_number,
                        topic=chunk_obj.topic,
                        document_type=chunk_obj.document_type,
                        source=chunk_obj.source,
                        source_scope=chunk_obj.source_scope,
                        metadata=chunk_obj.metadata_ if hasattr(chunk_obj, 'metadata_') else {},
                    )
                )

            logger.info(f"Retrieved {len(retrieved)} chunks for subject {subject_id} with query '{query[:50]}'")
            return retrieved

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve context: {str(e)}")

    async def retrieve_system(
        self,
        query: str,
        document_types: List[str],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Retrieve from SYSTEM-scoped chunks only (institutional knowledge).
        No subject_id filtering — these are institution-wide.
        """
        try:
            query_vector = await self.embedding_provider.embed_text(query)

            filters = [
                VectorChunk.source_scope == "SYSTEM",
                VectorChunk.document_type.in_(document_types),
                VectorChunk.embedding_json.isnot(None),
            ]

            stmt = select(VectorChunk).where(and_(*filters))
            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

            scored: List[tuple] = []
            for chunk in chunks:
                chunk_embedding = chunk.embedding
                if chunk_embedding:
                    similarity = _cosine_similarity(query_vector, chunk_embedding)
                    if similarity >= min_score:
                        scored.append((chunk, similarity))

            scored.sort(key=lambda x: x[1], reverse=True)
            scored = scored[:top_k]

            retrieved = []
            for chunk_obj, similarity in scored:
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk_obj.id,
                        content=chunk_obj.content,
                        score=similarity,
                        unit_number=chunk_obj.unit_number,
                        topic=chunk_obj.topic,
                        document_type=chunk_obj.document_type,
                        source=chunk_obj.source,
                        source_scope="SYSTEM",
                        metadata=chunk_obj.metadata_ if hasattr(chunk_obj, 'metadata_') else {},
                    )
                )

            logger.info(f"Retrieved {len(retrieved)} SYSTEM chunks ({document_types})")
            return retrieved

        except Exception as e:
            logger.error(f"System retrieval error: {e}")
            return []  # Graceful fallback — system context is supplementary

    async def retrieve_request_scoped(
        self,
        query: str,
        generation_run_id: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Retrieve from REQUEST-scoped chunks tied to a specific generation run.
        """
        try:
            query_vector = await self.embedding_provider.embed_text(query)

            filters = [
                VectorChunk.source_scope == "REQUEST",
                VectorChunk.generation_run_id == generation_run_id,
                VectorChunk.embedding_json.isnot(None),
            ]

            stmt = select(VectorChunk).where(and_(*filters))
            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

            scored = []
            for chunk in chunks:
                chunk_embedding = chunk.embedding
                if chunk_embedding:
                    similarity = _cosine_similarity(query_vector, chunk_embedding)
                    if similarity >= min_score:
                        scored.append((chunk, similarity))

            scored.sort(key=lambda x: x[1], reverse=True)
            scored = scored[:top_k]

            return [
                RetrievedChunk(
                    chunk_id=c.id, content=c.content, score=s,
                    unit_number=c.unit_number, topic=c.topic,
                    document_type=c.document_type, source=c.source,
                    source_scope="REQUEST",
                    metadata=c.metadata_ if hasattr(c, 'metadata_') else {},
                )
                for c, s in scored
            ]
        except Exception as e:
            logger.error(f"Request-scoped retrieval error: {e}")
            return []

    async def retrieve_with_hierarchy(
        self,
        query: str,
        subject_id: UUID,
        operation: str,
        system_doc_types: Optional[List[str]] = None,
        unit_numbers: Optional[List[int]] = None,
        generation_run_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[RetrievedChunk]:
        """
        Layered retrieval with priority ordering:
        1. Institutional/system documents (highest authority)
        2. Subject syllabus + approved material
        3. Request-scoped optional files (if generation_run_id provided)

        Results are merged and re-ranked by score, with system chunks
        receiving a small authority boost.
        """
        all_chunks: List[RetrievedChunk] = []

        # Layer 1: System/institutional documents
        if system_doc_types:
            sys_chunks = await self.retrieve_system(
                query=query,
                document_types=system_doc_types,
                top_k=max(3, top_k // 3),
            )
            # Apply authority boost for institutional docs
            for c in sys_chunks:
                c.score = min(1.0, c.score + 0.05)
            all_chunks.extend(sys_chunks)

        # Layer 2: Subject-specific documents
        subject_types = self._get_subject_doc_types(operation)
        per_unit_k = max(2, top_k // max(1, len(unit_numbers or [1])))
        if unit_numbers:
            for unit_num in unit_numbers:
                for doc_type in subject_types:
                    chunks = await self.retrieve(
                        query=query,
                        subject_id=subject_id,
                        top_k=per_unit_k,
                        unit_number=unit_num,
                        document_type=doc_type,
                    )
                    all_chunks.extend(chunks)
        else:
            for doc_type in subject_types:
                chunks = await self.retrieve(
                    query=query,
                    subject_id=subject_id,
                    top_k=max(2, top_k // len(subject_types)) if subject_types else top_k,
                    document_type=doc_type,
                )
                all_chunks.extend(chunks)

        # Layer 3: Request-scoped optional files
        if generation_run_id:
            req_chunks = await self.retrieve_request_scoped(
                query=query,
                generation_run_id=generation_run_id,
                top_k=max(2, top_k // 4),
            )
            all_chunks.extend(req_chunks)

        # De-duplicate by chunk_id and re-rank
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)

        unique_chunks.sort(key=lambda c: c.score, reverse=True)
        return unique_chunks[:top_k]

    @staticmethod
    def _get_subject_doc_types(operation: str) -> List[str]:
        """Get subject-level document types relevant to an operation."""
        type_map = {
            "CO_GENERATION": ["SYLLABUS", "TEXTBOOK", "REFERENCE"],
            "LO_GENERATION": ["SYLLABUS", "TEXTBOOK"],
            "LO_PI_MAPPING": ["SYLLABUS"],
            "QUESTION_GENERATION": ["QUESTION_BANK", "TEXTBOOK", "SYLLABUS"],
            "MSE_GENERATION": ["QUESTION_BANK", "SYLLABUS", "PREV_PAPER"],
            "ESE_GENERATION": ["QUESTION_BANK", "SYLLABUS", "PREV_PAPER"],
            "AAP_GENERATION": ["SYLLABUS"],
            "ASSIGNMENT_GENERATION": ["TEXTBOOK", "QUESTION_BANK", "SYLLABUS"],
        }
        return type_map.get(operation, ["SYLLABUS"])

    async def retrieve_multi_type(
        self,
        query: str,
        subject_id: UUID,
        document_types: List[str],
        top_k: int = 5,
        unit_number: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[RetrievedChunk]:
        """Retrieve from multiple document types, merging results by score."""
        all_chunks: List[RetrievedChunk] = []
        per_type_k = max(2, top_k // len(document_types)) if document_types else top_k
        for doc_type in document_types:
            chunks = await self.retrieve(
                query=query,
                subject_id=subject_id,
                top_k=per_type_k,
                unit_number=unit_number,
                document_type=doc_type,
                min_score=min_score,
            )
            all_chunks.extend(chunks)
        # Re-sort merged results and take top_k
        all_chunks.sort(key=lambda c: c.score, reverse=True)
        return all_chunks[:top_k]

    # Operation-specific query templates
    _OPERATION_QUERIES = {
        "CO_GENERATION": "Course objectives outcomes competencies {subject}",
        "LO_GENERATION": "Learning outcomes unit topics Bloom taxonomy {subject}",
        "QUESTION_GENERATION": "Exam questions problem-solving {subject} {unit}",
        "MSE_GENERATION": "Mid-semester exam assessment syllabus {subject}",
        "ESE_GENERATION": "End-semester exam comprehensive assessment {subject}",
        "AAP_GENERATION": "Academic activity plan teaching schedule {subject}",
        "ASSIGNMENT_GENERATION": "Assignment practice problems exercises {subject}",
        "LO_PI_MAPPING": "Performance indicators program outcomes mapping {subject}",
    }

    # System document types per operation
    _OPERATION_SYSTEM_DOCS = {
        "MSE_GENERATION": ["MSE_SAMPLE"],
        "ESE_GENERATION": ["ESE_SAMPLE"],
        "AAP_GENERATION": ["AAP_FORMAT"],
        "LO_PI_MAPPING": ["PO_PI_GUIDELINE"],
        "CO_GENERATION": [],
        "LO_GENERATION": [],
        "QUESTION_GENERATION": [],
        "ASSIGNMENT_GENERATION": [],
    }

    async def retrieve_for_operation(
        self,
        operation: str,
        subject_id: UUID,
        subject_name: str = "",
        unit_number: Optional[int] = None,
        unit_numbers: Optional[List[int]] = None,
        generation_run_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        """Operation-aware retrieval with system + subject + request layers."""
        query_template = self._OPERATION_QUERIES.get(operation, "academic content {subject}")
        query = query_template.format(
            subject=subject_name,
            unit=f"Unit {unit_number}" if unit_number else "",
        )

        system_doc_types = self._OPERATION_SYSTEM_DOCS.get(operation, [])
        effective_units = unit_numbers or ([unit_number] if unit_number else None)

        return await self.retrieve_with_hierarchy(
            query=query,
            subject_id=subject_id,
            operation=operation,
            system_doc_types=system_doc_types if system_doc_types else None,
            unit_numbers=effective_units,
            generation_run_id=generation_run_id,
            top_k=top_k,
        )


