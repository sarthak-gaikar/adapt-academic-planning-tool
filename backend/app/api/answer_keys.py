"""
ADAPT — Answer Keys API

POST /api/exams/{eid}/answer-key/generate — Generate model answers & rubrics
GET  /api/exams/{eid}/answer-key          — Get active answer key
POST /api/exams/{eid}/answer-key/approve  — Approve answer key
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.answer_key_generator import AnswerKeyGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.answer_key import AnswerKey
from app.models.exam import ExamPaper
from app.models.user import User
from app.schemas.answer_key import AnswerKeyResponse

router = APIRouter(tags=["Answer Keys"])


async def _run_bg_ak_gen(task_info, exam_id: UUID, user_id: UUID):
    async with async_session_factory() as session:
        generator = AnswerKeyGenerator(session)
        ak = await generator.generate_exam_answer_key(exam_id, user_id)
        return {"answer_key_id": str(ak.id)}


@router.post("/api/exams/{exam_id}/answer-key/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_answer_key_endpoint(
    exam_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of Answer Key & Marking Scheme."""
    res = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam paper not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate Answer Key for Exam {exam_id}",
        _run_bg_ak_gen,
        exam_id,
        current_user.id,
    )
    return {"task_id": task_id, "message": "Answer Key generation started in background."}


@router.get("/api/exams/{exam_id}/answer-key", response_model=AnswerKeyResponse)
async def get_exam_answer_key(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get official answer key for an exam paper."""
    res = await db.execute(select(AnswerKey).where(AnswerKey.exam_paper_id == exam_id))
    ak = res.scalar_one_or_none()
    if not ak:
        raise HTTPException(status_code=404, detail="No answer key found. Please generate one first.")
    return AnswerKeyResponse.model_validate(ak)


@router.post("/api/exams/{exam_id}/answer-key/approve", response_model=AnswerKeyResponse)
async def approve_answer_key(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve an answer key."""
    res = await db.execute(select(AnswerKey).where(AnswerKey.exam_paper_id == exam_id))
    ak = res.scalar_one_or_none()
    if not ak:
        raise HTTPException(status_code=404, detail="Answer key not found")

    ak.status = "APPROVED"
    ak.approved_by = current_user.id
    await db.commit()
    await db.refresh(ak)
    return AnswerKeyResponse.model_validate(ak)
