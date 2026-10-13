"""
ADAPT — Examination Papers API

POST /api/subjects/{id}/papers/generate  — Unified Generate Paper (MSE or ESE)
POST /api/subjects/{id}/mse/generate     — Generate Mid-Semester Exam (legacy)
POST /api/subjects/{id}/ese/generate     — Generate End-Semester Exam (legacy)
GET  /api/subjects/{id}/exams            — List exam papers
GET  /api/exams/{eid}                    — Get exam paper with questions
POST /api/exams/{eid}/validate           — Re-run deterministic validation
POST /api/exams/{eid}/approve            — Officially approve exam paper
POST /api/subjects/{id}/papers/preview   — Preview blueprint validation
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ese_generator import ESEGenerator
from app.ai.mse_generator import MSEGenerator
from app.ai.exam_generator import UnifiedExamGenerator
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
    UnifiedPaperGenerateRequest,
)
from app.schemas.question import QuestionResponse
from app.validators.blueprint_validator import MasterBlueprintValidator

router = APIRouter(tags=["Examinations"])


async def _run_bg_unified_gen(
    task_info, subject_id, user_id, exam_type, unit_ids,
    total_marks, question_counts, additional_file_paths, title, instructions,
):
    async with async_session_factory() as session:
        gen = UnifiedExamGenerator(session)
        paper = await gen.generate_paper(
            subject_id=subject_id,
            user_id=user_id,
            exam_type=exam_type,
            unit_ids=unit_ids,
            total_marks=total_marks,
            question_counts=question_counts,
            additional_file_paths=additional_file_paths or [],
            custom_title=title,
            custom_instructions=instructions,
        )
        return {"paper_id": str(paper.id), "title": paper.title, "exam_type": exam_type}


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


# ---- Unified Generate Paper ----

@router.post("/api/subjects/{subject_id}/papers/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_paper_unified(
    subject_id: UUID,
    req: UnifiedPaperGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified paper generation endpoint for both MSE and ESE.
    
    Pre-validates blueprint arithmetic BEFORE dispatching to background generation.
    Returns 422 with clear error if marks don't add up.
    """
    # Validate paper type
    if req.paper_type not in ("MSE", "ESE"):
        raise HTTPException(status_code=422, detail="paper_type must be 'MSE' or 'ESE'")

    # Validate subject exists
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    # Pre-validate marks arithmetic (BLOCK if mismatch)
    question_counts_int = req.question_counts_int
    is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
        total_marks=req.total_marks,
        question_counts=question_counts_int,
    )

    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "BLUEPRINT_MISMATCH",
                "message": msg,
                "requested_total": req.total_marks,
                "calculated_total": calc_total,
                "question_counts": req.question_counts,
            },
        )

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate {req.paper_type} Paper ({req.total_marks}m) for {subject_id}",
        _run_bg_unified_gen,
        subject_id,
        current_user.id,
        req.paper_type,
        req.unit_ids,
        req.total_marks,
        question_counts_int,
        req.additional_file_paths,
        req.custom_title,
        req.custom_instructions,
    )
    return {
        "task_id": task_id,
        "message": f"{req.paper_type} paper generation started.",
        "blueprint_validation": msg,
        "calculated_marks": calc_total,
        "total_questions": req.total_questions,
    }


@router.post("/api/subjects/{subject_id}/papers/preview", response_model=dict)
async def preview_paper_blueprint(
    subject_id: UUID,
    req: UnifiedPaperGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Preview blueprint validation without generating. Shows calculated marks and validity."""
    question_counts_int = req.question_counts_int
    is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
        total_marks=req.total_marks,
        question_counts=question_counts_int,
    )
    breakdown = [
        {"marks": int(k), "count": v, "subtotal": int(k) * v}
        for k, v in req.question_counts.items()
    ]
    return {
        "is_valid": is_valid,
        "message": msg,
        "requested_total": req.total_marks,
        "calculated_total": calc_total,
        "total_questions": req.total_questions,
        "breakdown": breakdown,
        "paper_type": req.paper_type,
        "units": req.unit_ids,
    }


# ---- Legacy MSE/ESE endpoints (backward compatible) ----

@router.post("/api/subjects/{subject_id}/mse/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_mse_endpoint(
    subject_id: UUID,
    req: ExamGenerateRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of MSE paper from blueprint. (Legacy — use /papers/generate)"""
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
