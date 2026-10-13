"""
ADAPT — Course Outcomes API

POST /api/subjects/{id}/course-outcomes/generate — Generate COs via LLM + RAG
GET  /api/subjects/{id}/course-outcomes          — List subject COs
PUT  /api/course-outcomes/{co_id}               — Edit individual CO
POST /api/course-outcomes/{co_id}/approve       — Approve individual CO
POST /api/subjects/{id}/course-outcomes/approve-all — Approve all draft COs
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.co_generator import COGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.course_outcome import CourseOutcome
from app.models.subject import Subject
from app.models.user import User
from app.schemas.course_outcome import (
    COGenerationRequest,
    CourseOutcomeResponse,
    CourseOutcomeUpdate,
)

router = APIRouter(tags=["Course Outcomes"])


async def _run_bg_co_generation(task_info, subject_id: UUID, user_id: UUID, req: COGenerationRequest):
    async with async_session_factory() as session:
        generator = COGenerator(session)
        cos = await generator.generate_cos(subject_id, user_id, req)
        return {"cos_generated": len(cos)}


@router.post("/api/subjects/{subject_id}/course-outcomes/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_course_outcomes(
    subject_id: UUID,
    req: COGenerationRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of Course Outcomes."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate COs for subject {subject_id}",
        _run_bg_co_generation,
        subject_id,
        current_user.id,
        req or COGenerationRequest(),
    )
    return {"task_id": task_id, "message": "Course Outcomes generation started in background."}


@router.get("/api/subjects/{subject_id}/course-outcomes", response_model=List[CourseOutcomeResponse])
async def list_course_outcomes(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active Course Outcomes for a subject."""
    res = await db.execute(
        select(CourseOutcome)
        .where(
            CourseOutcome.subject_id == subject_id,
            CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
        )
        .order_by(CourseOutcome.co_code)
    )
    cos = res.scalars().all()
    return [CourseOutcomeResponse.model_validate(co) for co in cos]


@router.put("/api/course-outcomes/{co_id}", response_model=CourseOutcomeResponse)
async def update_course_outcome(
    co_id: UUID,
    data: CourseOutcomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits a Course Outcome statement, Bloom level, or supporting units."""
    res = await db.execute(select(CourseOutcome).where(CourseOutcome.id == co_id))
    co = res.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Course Outcome not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(co, field, val)

    await db.commit()
    await db.refresh(co)
    return CourseOutcomeResponse.model_validate(co)


@router.post("/api/course-outcomes/{co_id}/approve", response_model=CourseOutcomeResponse)
async def approve_course_outcome(
    co_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve a specific Course Outcome."""
    res = await db.execute(select(CourseOutcome).where(CourseOutcome.id == co_id))
    co = res.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Course Outcome not found")

    co.status = "APPROVED"
    co.approved_by = current_user.id
    co.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(co)
    return CourseOutcomeResponse.model_validate(co)


@router.post("/api/subjects/{subject_id}/course-outcomes/approve-all", response_model=List[CourseOutcomeResponse])
async def approve_all_course_outcomes(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve all active Course Outcomes for a subject."""
    res = await db.execute(
        select(CourseOutcome).where(
            CourseOutcome.subject_id == subject_id,
            CourseOutcome.status == "DRAFT",
        )
    )
    cos = res.scalars().all()
    now = datetime.now(timezone.utc)
    for co in cos:
        co.status = "APPROVED"
        co.approved_by = current_user.id
        co.approved_at = now

    await db.commit()
    return await list_course_outcomes(subject_id, db, current_user)

@router.delete('/api/course-outcomes/{co_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_outcome(
    co_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(CourseOutcome).where(CourseOutcome.id == co_id))
    co = res.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail='Course Outcome not found')
    await db.delete(co)
    await db.commit()
    return None


@router.delete('/api/subjects/{subject_id}/course-outcomes', status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_course_outcomes(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(CourseOutcome).where(CourseOutcome.subject_id == subject_id))
    cos = res.scalars().all()
    for co in cos:
        await db.delete(co)
    await db.commit()
    return None
