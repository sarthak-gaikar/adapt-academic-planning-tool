"""
ADAPT — Vector Retrieval Engine

Performs cosine similarity search with metadata pre-filtering.
Uses Python-based similarity computation (SQLite compatible).
"""

import json
import math
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, and_
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
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.score = score
        self.unit_number = unit_number
        self.topic = topic
        self.document_type = document_type
        self.source = source
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
                        metadata=chunk_obj.metadata_ if hasattr(chunk_obj, 'metadata_') else {},
                    )
                )

            logger.info(f"Retrieved {len(retrieved)} chunks for subject {subject_id} with query '{query[:50]}'")
            return retrieved

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve context: {str(e)}")
