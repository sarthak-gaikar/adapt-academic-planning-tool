"""
ADAPT — Examination Papers API

POST /api/subjects/{id}/mse/generate — Generate Mid-Semester Exam
POST /api/subjects/{id}/ese/generate — Generate End-Semester Exam
GET  /api/subjects/{id}/exams        — List exam papers
GET  /api/exams/{eid}                — Get exam paper with questions
POST /api/exams/{eid}/validate       — Re-run deterministic validation
POST /api/exams/{eid}/approve        — Officially approve exam paper
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ese_generator import ESEGenerator
from app.ai.mse_generator import MSEGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.exam import ExamBlueprint, ExamPaper, ExamQuestion
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.schemas.exam import (
    ExamGenerateRequest,
    ExamPaperResponse,
    ExamQuestionItem,
)
from app.schemas.question import QuestionResponse
from app.validators.blueprint_validator import MasterBlueprintValidator

router = APIRouter(tags=["Examinations"])


async def _run_bg_mse_gen(task_info, subject_id: UUID, blueprint_id: UUID, user_id: UUID, title: str, instructions: str):
    async with async_session_factory() as session:
        gen = MSEGenerator(session)
        paper = await gen.generate_mse(subject_id, blueprint_id, user_id, title, instructions)
        return {"paper_id": str(paper.id), "title": paper.title}


async def _run_bg_ese_gen(task_info, subject_id: UUID, blueprint_id: UUID, user_id: UUID, title: str, instructions: str):
    async with async_session_factory() as session:
        gen = ESEGenerator(session)
        paper = await gen.generate_ese(subject_id, blueprint_id, user_id, title, instructions)
        return {"paper_id": str(paper.id), "title": paper.title}


@router.post("/api/subjects/{subject_id}/mse/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_mse_endpoint(
    subject_id: UUID,
    req: ExamGenerateRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of MSE paper from blueprint."""
    req = req or ExamGenerateRequest()
    bp_id = req.blueprint_id

    if not bp_id:
        # Find default MSE blueprint
        res = await db.execute(
            select(ExamBlueprint).where(
                ExamBlueprint.subject_id == subject_id,
                ExamBlueprint.exam_type == "MSE",
            ).order_by(ExamBlueprint.created_at.desc()).limit(1)
        )
        bp = res.scalar_one_or_none()
        if not bp:
            # Create default on the fly
            bp = ExamBlueprint(
                subject_id=subject_id,
                created_by=current_user.id,
                exam_type="MSE",
                total_marks=30,
                units_covered=[1, 2, 3],
                difficulty_distribution={"EASY": 30, "MEDIUM": 50, "HARD": 20},
                bloom_distribution={"Remember": 10, "Understand": 30, "Apply": 40, "Analyze": 20},
                status="APPROVED",
            )
            db.add(bp)
            await db.commit()
            await db.refresh(bp)
        bp_id = bp.id

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate MSE Paper for {subject_id}",
        _run_bg_mse_gen,
        subject_id,
        bp_id,
        current_user.id,
        req.custom_title,
        req.custom_instructions,
    )
    return {"task_id": task_id, "message": "MSE paper generation started in background."}


@router.post("/api/subjects/{subject_id}/ese/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_ese_endpoint(
    subject_id: UUID,
    req: ExamGenerateRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of ESE paper from blueprint."""
    req = req or ExamGenerateRequest()
    bp_id = req.blueprint_id

    if not bp_id:
        res = await db.execute(
            select(ExamBlueprint).where(
                ExamBlueprint.subject_id == subject_id,
                ExamBlueprint.exam_type == "ESE",
            ).order_by(ExamBlueprint.created_at.desc()).limit(1)
        )
        bp = res.scalar_one_or_none()
        if not bp:
            bp = ExamBlueprint(
                subject_id=subject_id,
                created_by=current_user.id,
                exam_type="ESE",
                total_marks=50,
                units_covered=[1, 2, 3, 4, 5],
                difficulty_distribution={"EASY": 20, "MEDIUM": 60, "HARD": 20},
                bloom_distribution={"Remember": 10, "Understand": 25, "Apply": 35, "Analyze": 20, "Evaluate": 10},
                has_internal_choice=True,
                status="APPROVED",
            )
            db.add(bp)
            await db.commit()
            await db.refresh(bp)
        bp_id = bp.id

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate ESE Paper for {subject_id}",
        _run_bg_ese_gen,
        subject_id,
        bp_id,
        current_user.id,
        req.custom_title,
        req.custom_instructions,
    )
    return {"task_id": task_id, "message": "ESE paper generation started in background."}


@router.get("/api/subjects/{subject_id}/exams", response_model=List[ExamPaperResponse])
async def list_exams(
    subject_id: UUID,
    exam_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List examination papers for a subject."""
    filters = [ExamPaper.subject_id == subject_id, ExamPaper.status != "ARCHIVED"]
    if exam_type:
        filters.append(ExamPaper.exam_type == exam_type)

    res = await db.execute(select(ExamPaper).where(*filters).order_by(ExamPaper.created_at.desc()))
    papers = res.scalars().all()
    out = []
    for p in papers:
        resp = await _build_exam_response(p, db)
        out.append(resp)
    return out


@router.get("/api/exams/{exam_id}", response_model=ExamPaperResponse)
async def get_exam_paper(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get complete exam paper with questions, sections, choices, and validation."""
    res = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    paper = res.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    return await _build_exam_response(paper, db)


@router.post("/api/exams/{exam_id}/validate", response_model=dict)
async def validate_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-runs deterministic validation on an exam paper."""
    res = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    paper = res.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")

    bp_res = await db.execute(select(ExamBlueprint).where(ExamBlueprint.id == paper.blueprint_id))
    bp = bp_res.scalar_one_or_none()

    eq_res = await db.execute(
        select(ExamQuestion, Question)
        .join(Question, ExamQuestion.question_id == Question.id)
        .where(ExamQuestion.exam_paper_id == exam_id)
    )
    rows = eq_res.all()

    q_dicts = []
    for eq, q in rows:
        q_dicts.append({
            "question_text": q.question_text,
            "marks": eq.marks,
            "bloom_level": q.bloom_level,
            "unit_number": q.unit_number,
            "co_code": q.co_code,
            "is_compulsory": eq.is_compulsory,
        })

    val_report = MasterBlueprintValidator.validate_exam_paper(
        questions=q_dicts,
        total_marks=paper.total_marks,
        units_covered=bp.units_covered if bp else [1, 2, 3],
        target_bloom=bp.bloom_distribution if bp else None,
    )
    paper.validation_report = val_report
    await db.commit()
    return val_report


@router.post("/api/exams/{exam_id}/approve", response_model=ExamPaperResponse)
async def approve_exam_paper(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve an examination paper."""
    res = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    paper = res.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")

    paper.status = "APPROVED"
    paper.approved_by = current_user.id
    paper.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return await _build_exam_response(paper, db)


# ---- Helper ----

async def _build_exam_response(paper: ExamPaper, db: AsyncSession) -> ExamPaperResponse:
    eq_res = await db.execute(
        select(ExamQuestion, Question)
        .join(Question, ExamQuestion.question_id == Question.id)
        .where(ExamQuestion.exam_paper_id == paper.id)
        .order_by(ExamQuestion.sequence_order)
    )
    rows = eq_res.all()
    q_items = []
    for eq, q in rows:
        q_items.append(
            ExamQuestionItem(
                id=eq.id,
                section=eq.section,
                sequence_order=eq.sequence_order,
                marks=eq.marks,
                is_compulsory=eq.is_compulsory,
                choice_group=eq.choice_group,
                question=QuestionResponse.model_validate(q),
            )
        )

    resp = ExamPaperResponse.model_validate(paper)
    resp.questions = q_items
    return resp
