"""
ADAPT — Document Upload & Management API

POST /api/subjects/{id}/documents — Upload syllabus or reference file
GET  /api/subjects/{id}/documents — List subject documents
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.document import Document
from app.models.subject import Subject
from app.models.user import User
from app.rag.ingestion import IngestionPipeline
from app.schemas.document import DocumentResponse, DocumentUploadResponse

router = APIRouter(prefix="/api/subjects", tags=["Documents"])
settings = get_settings()


async def _run_background_ingestion(task_info, document_id: UUID):
    """Background runner for document ingestion."""
    async with async_session_factory() as session:
        pipeline = IngestionPipeline(session)
        return await pipeline.ingest_document(document_id, task_info=task_info)


@router.post("/{subject_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    subject_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form("SYLLABUS"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF or DOCX syllabus / academic document."""
    # Verify subject
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = res.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if current_user.role != "ADMIN" and subject.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate file extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .docx",
        )

    # Save file to disk
    subject_dir = Path(settings.upload_dir) / str(subject_id)
    subject_dir.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{uuid.uuid4()}_{filename}"
    file_path = str(subject_dir / saved_filename)

    file_size = 0
    async with aiofiles.open(file_path, "wb") as out_file:
        while content := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(content)
            if file_size > settings.max_upload_size_bytes:
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"File exceeds maximum allowed size ({settings.max_upload_size_mb}MB)",
                )
            await out_file.write(content)

    # Create Document record
    doc = Document(
        subject_id=subject_id,
        uploaded_by=current_user.id,
        filename=filename,
        file_path=file_path,
        file_type=ext.replace(".", "").upper(),
        document_type=document_type.upper(),
        file_size=file_size,
        processing_status="PENDING",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Launch background ingestion
    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Ingest & Index {filename} ({document_type})",
        _run_background_ingestion,
        doc.id,
    )

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(doc),
        task_id=task_id,
        message="Document uploaded. Processing and syllabus extraction started in background.",
    )


@router.get("/{subject_id}/documents", response_model=List[DocumentResponse])
async def list_subject_documents(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents uploaded for a subject."""
    res = await db.execute(
        select(Document)
        .where(Document.subject_id == subject_id)
        .order_by(Document.created_at.desc())
    )
    docs = res.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]
