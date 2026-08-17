"""
ADAPT — Vector Retrieval Engine

Performs pgvector cosine similarity search with metadata pre-filtering.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.ai.factory import get_embedding_provider
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.models.vector_chunk import VectorChunk

logger = get_logger("rag.retriever")


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
    """Retrieves relevant chunks from pgvector using query embeddings and metadata filters."""

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
        Embeds query, runs pgvector cosine similarity search, and filters results.
        """
        try:
            query_vector = await self.embedding_provider.embed_text(query)

            # Build query with metadata filters
            filters = [VectorChunk.subject_id == subject_id]
            if unit_number is not None:
                filters.append(VectorChunk.unit_number == unit_number)
            if document_type is not None:
                filters.append(VectorChunk.document_type == document_type)

            # pgvector cosine distance: VectorChunk.embedding.cosine_distance(query_vector)
            # cosine similarity = 1 - cosine distance
            cosine_dist = VectorChunk.embedding.cosine_distance(query_vector)
            stmt = (
                select(VectorChunk, cosine_dist.label("distance"))
                .where(and_(*filters))
                .order_by(cosine_dist)
                .limit(top_k)
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            retrieved: List[RetrievedChunk] = []
            for chunk_obj, dist in rows:
                similarity = 1.0 - (dist if dist is not None else 1.0)
                if similarity >= min_score:
                    retrieved.append(
                        RetrievedChunk(
                            chunk_id=chunk_obj.id,
                            content=chunk_obj.content,
                            score=similarity,
                            unit_number=chunk_obj.unit_number,
                            topic=chunk_obj.topic,
                            document_type=chunk_obj.document_type,
                            source=chunk_obj.source,
                            metadata=chunk_obj.metadata,
                        )
                    )

            logger.info(f"Retrieved {len(retrieved)} chunks for subject {subject_id} with query '{query[:50]}'")
            return retrieved

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve context: {str(e)}")
