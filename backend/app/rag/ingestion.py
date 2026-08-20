"""
ADAPT — Document Ingestion & RAG Indexing Pipeline

End-to-end ingestion:
1. Parse PDF / DOCX
2. Save raw text & metadata
3. Chunk into semantic sections
4. Generate embeddings via Provider
5. Store chunks in pgvector (VectorChunk)
6. Trigger LLM Structured Syllabus Extraction
7. Populate Syllabus, SyllabusUnit, Topic tables
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider, get_embedding_provider
from app.ai.prompts.syllabus_analysis import (
    SYLLABUS_ANALYSIS_SYSTEM_PROMPT,
    SYLLABUS_ANALYSIS_USER_PROMPT,
)
from app.core.exceptions import FileParsingError, LLMError
from app.core.logging import get_logger
from app.models.document import Document
from app.models.generation_run import GenerationRun
from app.models.subject import Subject
from app.models.syllabus import Syllabus, SyllabusUnit, Topic
from app.models.vector_chunk import VectorChunk
from app.rag.chunker import SyllabusChunker
from app.rag.document_parsers.docx_parser import DOCXParser
from app.rag.document_parsers.pdf_parser import PDFParser
from app.schemas.syllabus import StructuredSyllabusExtraction

logger = get_logger("rag.ingestion")


class IngestionPipeline:
    """Orchestrates parsing, chunking, embedding, and syllabus structuration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_provider = get_llm_provider()
        self.embedding_provider = get_embedding_provider()
        self.chunker = SyllabusChunker()

    async def ingest_document(
        self,
        document_id: UUID,
        task_info: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs the entire ingestion and indexing pipeline for an uploaded document."""
        # 1. Fetch Document record
        res = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = res.scalar_one_or_none()
        if not doc:
            raise FileParsingError(f"Document {document_id} not found")

        doc.processing_status = "PROCESSING"
        await self.db.flush()

        try:
            if task_info:
                task_info.progress = 10.0
                task_info.message = "Parsing document content..."

            # 2. Extract Text
            file_path = doc.file_path
            ext = Path(file_path).suffix.lower()

            if ext == ".pdf":
                parse_result = PDFParser.parse(file_path)
            elif ext in (".docx", ".doc"):
                parse_result = DOCXParser.parse(file_path)
            else:
                raise FileParsingError(f"Unsupported document format: {ext}")

            extracted_text = parse_result["full_text"]
            doc.extracted_text = extracted_text
            doc.metadata_ = {
                **(doc.metadata_ or {}),
                "page_count": parse_result.get("page_count", 1),
                "title": parse_result.get("title", doc.filename),
            }
            await self.db.flush()

            if not extracted_text.strip():
                raise FileParsingError("Document is empty or contains non-extractable text.")

            if task_info:
                task_info.progress = 30.0
                task_info.message = "Chunking and extracting metadata..."

            # 3. Chunk Document
            default_meta = {
                "document_id": str(doc.id),
                "subject_id": str(doc.subject_id),
                "document_type": doc.document_type,
                "source": doc.filename,
            }
            chunks = self.chunker.chunk_document(extracted_text, default_metadata=default_meta)
            total_chunks = len(chunks)

            if task_info:
                task_info.progress = 50.0
                task_info.message = f"Generating embeddings for {total_chunks} chunks..."

            # 4. Generate Embeddings in batch
            chunk_texts = [c.content for c in chunks]
            embeddings = await self.embedding_provider.embed_batch(chunk_texts)

            # 5. Clear any existing chunks for this document and save new ones
            await self.db.execute(delete(VectorChunk).where(VectorChunk.document_id == doc.id))

            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                v_chunk = VectorChunk(
                    document_id=doc.id,
                    subject_id=doc.subject_id,
                    document_type=doc.document_type,
                    unit_number=chunk.unit_number,
                    topic=chunk.topic,
                    content=chunk.content,
                    metadata_=chunk.metadata,
                    source=doc.filename,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                )
                v_chunk.embedding = emb
                self.db.add(v_chunk)

            await self.db.flush()

            # 6. If this is a SYLLABUS document, extract structured syllabus via LLM
            structured_data = None
            if doc.document_type == "SYLLABUS":
                if task_info:
                    task_info.progress = 75.0
                    task_info.message = "Extracting structured course units and topics with LLM..."

                user_prompt = SYLLABUS_ANALYSIS_USER_PROMPT.format(
                    document_text=extracted_text[:25000] # Fit in context window
                )

                structured_data = await self.llm_provider.generate_structured(
                    prompt=user_prompt,
                    schema=StructuredSyllabusExtraction,
                    system_prompt=SYLLABUS_ANALYSIS_SYSTEM_PROMPT,
                )

                # Persist Syllabus and Units
                await self._persist_structured_syllabus(doc, structured_data)

            doc.processing_status = "COMPLETED"
            await self.db.commit()

            if task_info:
                task_info.progress = 100.0
                task_info.message = "Ingestion completed successfully."

            return {
                "document_id": str(doc.id),
                "chunks_created": total_chunks,
                "structured_syllabus_extracted": structured_data is not None,
                "status": "COMPLETED",
            }

        except Exception as e:
            doc.processing_status = "FAILED"
            await self.db.commit()
            logger.error(f"Ingestion failed for doc {document_id}: {e}")
            raise

    async def _persist_structured_syllabus(
        self,
        doc: Document,
        data: StructuredSyllabusExtraction,
    ):
        """Creates or updates the Syllabus record and populates Unit and Topic tables."""
        # Check existing syllabus version count for subject
        existing = await self.db.execute(
            select(Syllabus).where(Syllabus.subject_id == doc.subject_id).order_by(Syllabus.version.desc())
        )
        latest = existing.scalars().first()
        version = (latest.version + 1) if latest else 1

        syllabus = Syllabus(
            subject_id=doc.subject_id,
            document_id=doc.id,
            version=version,
            structured_data=data.model_dump(),
            status="DRAFT",
        )
        self.db.add(syllabus)
        await self.db.flush()
        await self.db.refresh(syllabus)

        # Update Subject name/code/hours if not set
        subj_res = await self.db.execute(select(Subject).where(Subject.id == doc.subject_id))
        subject = subj_res.scalar_one_or_none()
        if subject:
            if data.credits and not subject.credits:
                subject.credits = data.credits
            if data.teaching_hours and not subject.teaching_hours:
                subject.teaching_hours = data.teaching_hours
            if data.prerequisites:
                subject.prerequisites = data.prerequisites
            if data.course_objectives:
                subject.course_objectives = data.course_objectives

        # Populate Units & Topics
        for u in data.units:
            unit_obj = SyllabusUnit(
                syllabus_id=syllabus.id,
                unit_number=u.unit_number,
                title=u.title,
                hours=u.hours,
            )
            self.db.add(unit_obj)
            await self.db.flush()
            await self.db.refresh(unit_obj)

            for idx, t in enumerate(u.topics):
                topic_obj = Topic(
                    unit_id=unit_obj.id,
                    name=t.name,
                    sequence_order=idx + 1,
                    subtopics=t.subtopics,
                )
                self.db.add(topic_obj)

        await self.db.flush()
