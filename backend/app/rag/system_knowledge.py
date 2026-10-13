"""
ADAPT — System Knowledge Base Manager

Idempotent ingestion of institutional/system-level documents:
- PO-PI Mapping Guidelines
- AAP Format
- MSE Sample Papers
- ESE Sample Papers

Documents are stored in backend/knowledge_base/institutional/ and indexed
into the vector store on application startup. Content hashes prevent
redundant re-embedding when files haven't changed.
"""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.config import get_settings
from app.core.logging import get_logger
from app.models.system_document import SystemDocument
from app.models.vector_chunk import VectorChunk
from app.rag.chunker import SyllabusChunker
from app.rag.document_parsers.pdf_parser import PDFParser
from app.rag.document_parsers.docx_parser import DOCXParser

logger = get_logger("rag.system_knowledge")
settings = get_settings()

# Document type mapping based on directory/filename patterns
DOCUMENT_TYPE_RULES = {
    "po_pi": "PO_PI_GUIDELINE",
    "aap_format": "AAP_FORMAT",
    "mse_sample": "MSE_SAMPLE",
    "ese_sample": "ESE_SAMPLE",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def _classify_document_type(file_path: Path) -> str:
    """Infer document type from the file path and parent directory name."""
    path_lower = str(file_path).lower()
    if "mse_sample" in path_lower:
        return "MSE_SAMPLE"
    elif "ese_sample" in path_lower:
        return "ESE_SAMPLE"
    elif "po_pi" in path_lower or "pi_mapping" in path_lower:
        return "PO_PI_GUIDELINE"
    elif "aap" in path_lower:
        return "AAP_FORMAT"
    else:
        return "SYSTEM_REFERENCE"


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents for change detection."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def _discover_knowledge_files(base_dir: Path) -> List[Path]:
    """Recursively discover all supported document files in the knowledge base directory."""
    files = []
    if not base_dir.exists():
        logger.warning(f"Knowledge base directory does not exist: {base_dir}")
        return files

    for ext in SUPPORTED_EXTENSIONS:
        files.extend(base_dir.rglob(f"*{ext}"))

    return sorted(files)


class SystemKnowledgeManager:
    """Manages idempotent ingestion of institutional/system-level RAG documents."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_provider = get_embedding_provider()
        self.chunker = SyllabusChunker()

    async def ingest_all_system_documents(self) -> Dict[str, Any]:
        """
        Scan the institutional knowledge base directory and ingest
        new or changed documents. Skip unchanged files.

        Returns a summary dict of actions taken.
        """
        base_dir = Path(settings.knowledge_base_dir).resolve()
        files = _discover_knowledge_files(base_dir)

        summary = {
            "scanned": len(files),
            "ingested": 0,
            "skipped": 0,
            "updated": 0,
            "failed": 0,
            "details": [],
        }

        if not files:
            logger.info(f"No knowledge base documents found in {base_dir}")
            return summary

        logger.info(f"System KB scan: found {len(files)} document(s) in {base_dir}")

        for file_path in files:
            try:
                result = await self._ingest_if_changed(file_path, base_dir)
                summary[result["action"]] += 1
                summary["details"].append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {e}")
                summary["failed"] += 1
                summary["details"].append({
                    "file": file_path.name,
                    "action": "failed",
                    "error": str(e),
                })

        await self.db.commit()
        logger.info(
            f"System KB ingestion complete: "
            f"{summary['ingested']} ingested, {summary['updated']} updated, "
            f"{summary['skipped']} skipped, {summary['failed']} failed"
        )
        return summary

    async def _ingest_if_changed(
        self, file_path: Path, base_dir: Path
    ) -> Dict[str, Any]:
        """
        Check if a file has already been ingested with the same hash.
        If unchanged, skip. If new or changed, (re-)ingest.
        """
        relative_path = str(file_path.relative_to(base_dir.parent))
        current_hash = _compute_file_hash(file_path)
        document_type = _classify_document_type(file_path)

        # Check for existing record by file path
        result = await self.db.execute(
            select(SystemDocument).where(
                SystemDocument.file_path == relative_path
            )
        )
        existing = result.scalar_one_or_none()

        if existing and existing.content_hash == current_hash:
            logger.debug(f"System KB skip (unchanged): {file_path.name}")
            return {
                "file": file_path.name,
                "action": "skipped",
                "document_type": document_type,
            }

        action = "updated" if existing else "ingested"

        # Parse the document
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            parse_result = PDFParser.parse(str(file_path))
        elif ext in (".docx", ".doc"):
            parse_result = DOCXParser.parse(str(file_path))
        else:
            raise ValueError(f"Unsupported format: {ext}")

        extracted_text = parse_result.get("full_text", "")
        if not extracted_text.strip():
            logger.warning(f"System KB: empty text from {file_path.name}")
            return {
                "file": file_path.name,
                "action": "skipped",
                "reason": "empty_text",
            }

        # Chunk the document
        default_meta = {
            "source_scope": "SYSTEM",
            "document_type": document_type,
            "source": file_path.name,
        }
        chunks = self.chunker.chunk_document(
            extracted_text, default_metadata=default_meta
        )
        total_chunks = len(chunks)

        # Generate embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = await self.embedding_provider.embed_batch(chunk_texts)

        # If updating, clear old chunks first
        if existing:
            await self.db.execute(
                delete(VectorChunk).where(
                    VectorChunk.source_scope == "SYSTEM",
                    VectorChunk.source == existing.filename,
                )
            )
            existing.content_hash = current_hash
            existing.processing_status = "PROCESSING"
            existing.file_size = file_path.stat().st_size
            existing.extracted_text = extracted_text[:50000]
        else:
            existing = SystemDocument(
                filename=file_path.name,
                file_path=relative_path,
                document_type=document_type,
                source_scope="SYSTEM",
                content_hash=current_hash,
                file_size=file_path.stat().st_size,
                processing_status="PROCESSING",
                extracted_text=extracted_text[:50000],
            )
            self.db.add(existing)
            await self.db.flush()

        # Store vector chunks
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            v_chunk = VectorChunk(
                document_id=None,  # No user-uploaded Document reference
                subject_id=None,  # System-wide, not subject-specific
                document_type=document_type,
                source_scope="SYSTEM",
                unit_number=chunk.unit_number,
                topic=chunk.topic,
                content=chunk.content,
                metadata_={
                    **(chunk.metadata or {}),
                    "system_document_id": str(existing.id),
                    "source_scope": "SYSTEM",
                    "document_type": document_type,
                },
                source=file_path.name,
                authority="UNIVERSITY",
                chunk_index=idx,
                total_chunks=total_chunks,
            )
            v_chunk.embedding = emb
            self.db.add(v_chunk)

        existing.chunk_count = total_chunks
        existing.processing_status = "COMPLETED"
        existing.error_message = None
        await self.db.flush()

        logger.info(
            f"System KB {action}: {file_path.name} "
            f"({document_type}, {total_chunks} chunks)"
        )
        return {
            "file": file_path.name,
            "action": action,
            "document_type": document_type,
            "chunks": total_chunks,
        }

    async def get_ingestion_status(self) -> List[Dict[str, Any]]:
        """Return current status of all system documents."""
        result = await self.db.execute(
            select(SystemDocument).order_by(SystemDocument.document_type)
        )
        docs = result.scalars().all()
        return [
            {
                "id": str(d.id),
                "filename": d.filename,
                "document_type": d.document_type,
                "status": d.processing_status,
                "chunk_count": d.chunk_count,
                "content_hash": d.content_hash[:12] + "...",
                "ingested_at": str(d.ingested_at),
            }
            for d in docs
        ]
