"""
ADAPT — Document Export API

POST /api/export                  — Generate downloadable DOCX/PDF
GET  /api/exports/{id}/download   — Download exported file
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.document_generation.docx_generator import DOCXGenerator
from app.models.aap import AAPPlan
from app.models.answer_key import AnswerKey
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.document_export import DocumentExport
from app.models.exam import ExamPaper, ExamQuestion
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.schemas.export import DocumentExportRequest, DocumentExportResponse

router = APIRouter(prefix="/api", tags=["Document Export"])
EXPORT_DIR = Path("./exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/export", response_model=DocumentExportResponse)
async def export_document(
    req: DocumentExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate official DOCX export for an Exam, Assignment, AAP, or Answer Key."""
    export_id = uuid4()
    filename = f"{req.source_type.lower()}_{export_id}.docx"
    file_path = str(EXPORT_DIR / filename)

    if req.source_type == "EXAM":
        res = await db.execute(select(ExamPaper).where(ExamPaper.id == req.source_id))
        paper = res.scalar_one_or_none()
        if not paper:
            raise HTTPException(status_code=404, detail="Exam paper not found")

        s_res = await db.execute(select(Subject).where(Subject.id == paper.subject_id))
        subject = s_res.scalar_one_or_none()

        eq_res = await db.execute(
            select(ExamQuestion, Question)
            .join(Question, ExamQuestion.question_id == Question.id)
            .where(ExamQuestion.exam_paper_id == paper.id)
            .order_by(ExamQuestion.sequence_order)
        )
        questions_data = []
        for eq, q in eq_res.all():
            questions_data.append({
                "sequence_order": eq.sequence_order,
                "section": eq.section,
                "question_text": q.question_text,
                "marks": eq.marks,
                "co_code": q.co_code,
                "bloom_level": q.bloom_level,
                "choice_group": eq.choice_group,
            })

        DOCXGenerator.generate_exam_paper_docx(
            subject_name=subject.name if subject else "Course",
            course_code=subject.course_code if subject else "ITXXX",
            exam_type=paper.exam_type,
            title=paper.title,
            total_marks=paper.total_marks,
            instructions=paper.instructions or "",
            questions=questions_data,
            output_path=file_path,
            include_tags=req.include_co_bloom_tags,
        )

    elif req.source_type == "AAP":
        res = await db.execute(select(AAPPlan).where(AAPPlan.id == req.source_id))
        plan = res.scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="AAP plan not found")

        s_res = await db.execute(select(Subject).where(Subject.id == plan.subject_id))
        subject = s_res.scalar_one_or_none()

        weeks_data = (plan.plan_data or {}).get("weeks", [])
        DOCXGenerator.generate_aap_docx(
            subject_name=subject.name if subject else "Course",
            course_code=subject.course_code if subject else "ITXXX",
            total_weeks=plan.total_weeks or len(weeks_data),
            total_hours=plan.total_hours or 45,
            weeks_data=weeks_data,
            output_path=file_path,
        )

    elif req.source_type == "ANSWER_KEY":
        res = await db.execute(select(AnswerKey).where(AnswerKey.id == req.source_id))
        ak = res.scalar_one_or_none()
        if not ak:
            raise HTTPException(status_code=404, detail="Answer key not found")

        exam_res = await db.execute(select(ExamPaper).where(ExamPaper.id == ak.exam_paper_id))
        paper = exam_res.scalar_one_or_none()
        s_res = await db.execute(select(Subject).where(Subject.id == paper.subject_id)) if paper else None
        subject = s_res.scalar_one_or_none() if s_res else None

        DOCXGenerator.generate_answer_key_docx(
            subject_name=subject.name if subject else "Course",
            exam_title=paper.title if paper else "Examination",
            answers=ak.answers or [],
            output_path=file_path,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export source_type: {req.source_type}")

    # Track export in DB
    export_record = DocumentExport(
        id=export_id,
        source_id=req.source_id,
        source_type=req.source_type,
        format=req.format,
        file_path=file_path,
        generated_by=current_user.id,
    )
    db.add(export_record)
    await db.commit()

    return DocumentExportResponse(
        export_id=export_id,
        source_id=req.source_id,
        source_type=req.source_type,
        format=req.format,
        filename=filename,
        download_url=f"/api/exports/{export_id}/download",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/exports/{export_id}/download")
async def download_exported_document(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the generated export document."""
    res = await db.execute(select(DocumentExport).where(DocumentExport.id == export_id))
    exp = res.scalar_one_or_none()
    if not exp or not Path(exp.file_path).exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=exp.file_path,
        filename=Path(exp.file_path).name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
