"""
ADAPT — Question Bank API

POST   /api/subjects/{id}/questions/generate — Generate questions via LLM
GET    /api/subjects/{id}/questions          — Search/filter question bank
GET    /api/questions/{qid}                  — Get question details
PUT    /api/questions/{qid}                  — Edit question
POST   /api/questions/{qid}/approve          — Approve question
DELETE /api/questions/{qid}                  — Archive question
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.question_generator import QuestionGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.schemas.question import (
    QuestionGenerateRequest,
    QuestionResponse,
    QuestionUpdate,
)
from app.schemas.question_bank_blueprint import (
    QuestionBankBlueprintRequest,
    BlueprintPreviewResponse,
)

router = APIRouter(tags=["Question Bank"])


async def _run_bg_question_gen(task_info, subject_id: UUID, user_id: UUID, req: QuestionGenerateRequest):
    async with async_session_factory() as session:
        generator = QuestionGenerator(session)
        questions = await generator.generate_questions(subject_id, user_id, req)
        return {"questions_generated": len(questions)}


@router.post("/api/subjects/{subject_id}/questions/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_questions_endpoint(
    subject_id: UUID,
    req: QuestionGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of questions for the question bank."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate {req.count} questions for subject {subject_id}",
        _run_bg_question_gen,
        subject_id,
        current_user.id,
        req,
    )
    return {"task_id": task_id, "message": "Question generation started in background."}


@router.get("/api/subjects/{subject_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    subject_id: UUID,
    unit_number: Optional[int] = Query(None),
    topic: Optional[str] = Query(None),
    co_code: Optional[str] = Query(None),
    bloom_level: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("ALL"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Filter and browse questions in the subject Question Bank."""
    filters = [Question.subject_id == subject_id]

    if status_filter != "ALL":
        filters.append(Question.status == status_filter)
    else:
        filters.append(Question.status != "ARCHIVED")

    if unit_number is not None:
        filters.append(Question.unit_number == unit_number)
    if topic:
        filters.append(Question.topic.ilike(f"%{topic}%"))
    if co_code:
        filters.append(Question.co_code == co_code)
    if bloom_level:
        filters.append(Question.bloom_level == bloom_level)
    if difficulty:
        filters.append(Question.difficulty == difficulty)
    if question_type:
        filters.append(Question.question_type == question_type)
    if search:
        filters.append(Question.question_text.ilike(f"%{search}%"))

    res = await db.execute(
        select(Question)
        .where(*filters)
        .order_by(Question.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    questions = res.scalars().all()
    return [QuestionResponse.model_validate(q) for q in questions]


@router.get("/api/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Question).where(Question.id == question_id))
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse.model_validate(q)


@router.put("/api/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits a question text, marks, answer, or marking scheme."""
    res = await db.execute(select(Question).where(Question.id == question_id))
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(q, field, val)

    await db.commit()
    await db.refresh(q)
    return QuestionResponse.model_validate(q)


@router.post("/api/questions/{question_id}/approve", response_model=QuestionResponse)
async def approve_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a question for inclusion in exams and official question bank."""
    res = await db.execute(select(Question).where(Question.id == question_id))
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    q.status = "APPROVED"
    q.approved_by = current_user.id
    q.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(q)
    return QuestionResponse.model_validate(q)


@router.delete("/api/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a question."""
    res = await db.execute(select(Question).where(Question.id == question_id))
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    q.status = "ARCHIVED"
    await db.commit()


async def _run_bg_blueprint_gen(task_info, subject_id: UUID, user_id: UUID, req: QuestionBankBlueprintRequest):
    async with async_session_factory() as session:
        generator = QuestionGenerator(session)
        questions = await generator.generate_from_blueprint(subject_id, user_id, req)
        return {"questions_generated": len(questions), "total_marks": req.total_marks}


@router.post("/api/subjects/{subject_id}/question-bank/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_question_bank_from_blueprint(
    subject_id: UUID,
    req: QuestionBankBlueprintRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured question bank from a marks × count blueprint.
    
    The system auto-calculates total marks from the mark configs.
    Example: [{marks: 2, count: 10}, {marks: 5, count: 5}] → 45 total marks, 15 questions.
    """
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate question bank ({req.total_questions} Qs, {req.total_marks}m) for subject {subject_id}",
        _run_bg_blueprint_gen,
        subject_id,
        current_user.id,
        req,
    )
    return {
        "task_id": task_id,
        "message": f"Question bank generation started: {req.total_questions} questions, {req.total_marks} total marks.",
        "preview": {
            "total_questions": req.total_questions,
            "total_marks": req.total_marks,
            "mark_breakdown": [{"marks": mc.marks, "count": mc.count, "subtotal": mc.marks * mc.count} for mc in req.mark_configs],
        },
    }


@router.post("/api/subjects/{subject_id}/question-bank/preview", response_model=BlueprintPreviewResponse)
async def preview_question_bank_blueprint(
    subject_id: UUID,
    req: QuestionBankBlueprintRequest,
    current_user: User = Depends(get_current_user),
):
    """Preview calculated marks before generating."""
    return BlueprintPreviewResponse(
        mark_configs=req.mark_configs,
        total_marks=req.total_marks,
        total_questions=req.total_questions,
        units=req.units,
    )
