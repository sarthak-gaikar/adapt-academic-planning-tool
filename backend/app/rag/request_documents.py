"""
ADAPT — Request-Scoped Document Manager

Handles temporary file uploads for a single generation request.
Files are parsed, chunked, embedded, and stored with source_scope='REQUEST'
tied to a specific generation_run_id.

These chunks are NOT part of the permanent knowledge base and are isolated
from other generation runs.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.core.logging import get_logger
from app.models.vector_chunk import VectorChunk
from app.rag.chunker import SyllabusChunker
from app.rag.document_parsers.pdf_parser import PDFParser
from app.rag.document_parsers.docx_parser import DOCXParser

logger = get_logger("rag.request_documents")


class RequestDocumentManager:
    """Manages temporary, request-scoped document ingestion for generation runs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_provider = get_embedding_provider()
        self.chunker = SyllabusChunker()

    async def ingest_request_files(
        self,
        file_paths: List[str],
        generation_run_id: str,
        subject_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Parse, chunk, and embed uploaded files with REQUEST scope.
        
        These chunks are tagged with the generation_run_id and source_scope='REQUEST'
        so they are only retrievable within the context of this specific generation.
        """
        total_chunks = 0
        results = []

        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if not file_path.exists():
                logger.warning(f"Request file not found: {file_path}")
                results.append({"file": file_path.name, "status": "not_found"})
                continue

            try:
                # Parse document
                ext = file_path.suffix.lower()
                if ext == ".pdf":
                    parse_result = PDFParser.parse(str(file_path))
                elif ext in (".docx", ".doc"):
                    parse_result = DOCXParser.parse(str(file_path))
                else:
                    logger.warning(f"Unsupported format for request file: {ext}")
                    results.append({"file": file_path.name, "status": "unsupported_format"})
                    continue

                extracted_text = parse_result.get("full_text", "")
                if not extracted_text.strip():
                    results.append({"file": file_path.name, "status": "empty"})
                    continue

                # Chunk
                default_meta = {
                    "source_scope": "REQUEST",
                    "generation_run_id": generation_run_id,
                    "source": file_path.name,
                    "document_type": "REQUEST_REFERENCE",
                }
                chunks = self.chunker.chunk_document(
                    extracted_text, default_metadata=default_meta
                )

                # Embed
                chunk_texts = [c.content for c in chunks]
                embeddings = await self.embedding_provider.embed_batch(chunk_texts)

                # Store
                for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    v_chunk = VectorChunk(
                        document_id=None,
                        subject_id=subject_id,
                        document_type="REQUEST_REFERENCE",
                        source_scope="REQUEST",
                        generation_run_id=generation_run_id,
                        unit_number=chunk.unit_number,
                        topic=chunk.topic,
                        content=chunk.content,
                        metadata_={
                            **(chunk.metadata or {}),
                            "source_scope": "REQUEST",
                            "generation_run_id": generation_run_id,
                        },
                        source=file_path.name,
                        chunk_index=idx,
                        total_chunks=len(chunks),
                    )
                    v_chunk.embedding = emb
                    self.db.add(v_chunk)

                total_chunks += len(chunks)
                results.append({
                    "file": file_path.name,
                    "status": "ingested",
                    "chunks": len(chunks),
                })
                logger.info(
                    f"Request-scoped ingestion: {file_path.name} → "
                    f"{len(chunks)} chunks (run: {generation_run_id[:8]}...)"
                )

            except Exception as e:
                logger.error(f"Failed to ingest request file {file_path.name}: {e}")
                results.append({"file": file_path.name, "status": "failed", "error": str(e)})

        await self.db.flush()
        return {
            "generation_run_id": generation_run_id,
            "total_chunks": total_chunks,
            "files": results,
        }

    async def cleanup_request_chunks(self, generation_run_id: str) -> int:
        """
        Delete all REQUEST-scoped chunks for a specific generation run.
        Call this after generation is complete if cleanup is desired.
        Returns the number of chunks deleted.
        """
        result = await self.db.execute(
            delete(VectorChunk).where(
                VectorChunk.source_scope == "REQUEST",
                VectorChunk.generation_run_id == generation_run_id,
            )
        )
        count = result.rowcount
        await self.db.flush()
        logger.info(f"Cleaned up {count} REQUEST chunks for run {generation_run_id[:8]}...")
        return count
