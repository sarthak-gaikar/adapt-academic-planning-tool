"""
ADAPT — Learning Outcomes API

POST /api/subjects/{id}/learning-outcomes/generate — Generate LOs via LLM + RAG
GET  /api/subjects/{id}/learning-outcomes          — List all LOs (filterable by unit)
GET  /api/subjects/{id}/learning-outcomes/by-unit   — LOs grouped by unit
PUT  /api/learning-outcomes/{lo_id}                — Edit individual LO
POST /api/learning-outcomes/{lo_id}/approve        — Approve individual LO
POST /api/subjects/{id}/learning-outcomes/approve-all — Approve all draft LOs
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.lo_generator import LOGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.learning_outcome import LearningOutcome
from app.models.lo_co_mapping import LOCOMapping
from app.models.subject import Subject
from app.models.syllabus import Syllabus, SyllabusUnit
from app.models.user import User
from app.schemas.learning_outcome import (
    LOGenerationRequest,
    LearningOutcomeResponse,
    LearningOutcomeUpdate,
    LOsByUnitResponse,
)

router = APIRouter(tags=["Learning Outcomes"])


def _lo_to_response(lo: LearningOutcome) -> LearningOutcomeResponse:
    """Convert LO ORM object to response schema with unit info and CO mappings."""
    unit_number = lo.unit.unit_number if lo.unit else None
    unit_title = lo.unit.title if lo.unit else None
    mapped_cos = [m.course_outcome.co_code for m in (lo.co_mappings or []) if m.course_outcome]
    return LearningOutcomeResponse(
        id=lo.id,
        subject_id=lo.subject_id,
        unit_id=lo.unit_id,
        generation_run_id=lo.generation_run_id,
        lo_code=lo.lo_code,
        statement=lo.statement,
        bloom_level=lo.bloom_level,
        bloom_order=lo.bloom_order,
        bloom_confidence=lo.bloom_confidence,
        rationale=lo.rationale,
        status=lo.status,
        version=lo.version,
        approved_by=lo.approved_by,
        approved_at=lo.approved_at,
        created_at=lo.created_at,
        updated_at=lo.updated_at,
        unit_number=unit_number,
        unit_title=unit_title,
        mapped_cos=mapped_cos,
    )


async def _run_bg_lo_generation(task_info, subject_id: UUID, user_id: UUID, req: LOGenerationRequest):
    async with async_session_factory() as session:
        generator = LOGenerator(session)
        los = await generator.generate_los(subject_id, user_id, req)
        return {"los_generated": len(los)}


@router.post("/api/subjects/{subject_id}/learning-outcomes/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_learning_outcomes(
    subject_id: UUID,
    req: LOGenerationRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of Learning Outcomes for all or selected units."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate LOs for subject {subject_id}",
        _run_bg_lo_generation,
        subject_id,
        current_user.id,
        req or LOGenerationRequest(),
    )
    return {"task_id": task_id, "message": "Learning Outcomes generation started in background."}


@router.get("/api/subjects/{subject_id}/learning-outcomes", response_model=List[LearningOutcomeResponse])
async def list_learning_outcomes(
    subject_id: UUID,
    unit_number: Optional[int] = Query(None, description="Filter by unit number"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active Learning Outcomes for a subject, optionally filtered by unit."""
    query = (
        select(LearningOutcome)
        .where(
            LearningOutcome.subject_id == subject_id,
            LearningOutcome.status.in_(["DRAFT", "APPROVED"]),
        )
    )
    if unit_number is not None:
        # Need to join to SyllabusUnit to filter by unit_number
        query = query.join(SyllabusUnit, LearningOutcome.unit_id == SyllabusUnit.id).where(
            SyllabusUnit.unit_number == unit_number
        )
    query = query.order_by(LearningOutcome.lo_code)

    res = await db.execute(query)
    los = res.scalars().all()
    return [_lo_to_response(lo) for lo in los]


@router.get("/api/subjects/{subject_id}/learning-outcomes/by-unit", response_model=List[LOsByUnitResponse])
async def list_learning_outcomes_by_unit(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Learning Outcomes grouped by unit for the subject."""
    # Fetch syllabus units
    syl_res = await db.execute(
        select(Syllabus)
        .where(Syllabus.subject_id == subject_id)
        .order_by(Syllabus.version.desc())
        .limit(1)
    )
    syllabus = syl_res.scalar_one_or_none()
    if not syllabus:
        return []

    units_res = await db.execute(
        select(SyllabusUnit)
        .where(SyllabusUnit.syllabus_id == syllabus.id)
        .order_by(SyllabusUnit.unit_number)
    )
    units = units_res.scalars().all()

    result = []
    for unit in units:
        lo_res = await db.execute(
            select(LearningOutcome)
            .where(
                LearningOutcome.unit_id == unit.id,
                LearningOutcome.status.in_(["DRAFT", "APPROVED"]),
            )
            .order_by(LearningOutcome.lo_code)
        )
        unit_los = lo_res.scalars().all()
        result.append(LOsByUnitResponse(
            unit_number=unit.unit_number,
            unit_title=unit.title,
            unit_id=unit.id,
            learning_outcomes=[_lo_to_response(lo) for lo in unit_los],
        ))
    return result


@router.put("/api/learning-outcomes/{lo_id}", response_model=LearningOutcomeResponse)
async def update_learning_outcome(
    lo_id: UUID,
    data: LearningOutcomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits a Learning Outcome statement, Bloom level, or rationale."""
    res = await db.execute(select(LearningOutcome).where(LearningOutcome.id == lo_id))
    lo = res.scalar_one_or_none()
    if not lo:
        raise HTTPException(status_code=404, detail="Learning Outcome not found")

    update_dict = data.model_dump(exclude_unset=True)
    if "bloom_level" in update_dict:
        from app.validators.bloom_order_validator import bloom_to_order
        lo.bloom_order = bloom_to_order(update_dict["bloom_level"])
    for field, val in update_dict.items():
        setattr(lo, field, val)

    await db.commit()
    await db.refresh(lo)
    return _lo_to_response(lo)


@router.post("/api/learning-outcomes/{lo_id}/approve", response_model=LearningOutcomeResponse)
async def approve_learning_outcome(
    lo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve a specific Learning Outcome."""
    res = await db.execute(select(LearningOutcome).where(LearningOutcome.id == lo_id))
    lo = res.scalar_one_or_none()
    if not lo:
        raise HTTPException(status_code=404, detail="Learning Outcome not found")

    lo.status = "APPROVED"
    lo.approved_by = current_user.id
    lo.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(lo)
    return _lo_to_response(lo)


@router.post("/api/subjects/{subject_id}/learning-outcomes/approve-all", response_model=List[LearningOutcomeResponse])
async def approve_all_learning_outcomes(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve all active Learning Outcomes for a subject."""
    res = await db.execute(
        select(LearningOutcome).where(
            LearningOutcome.subject_id == subject_id,
            LearningOutcome.status == "DRAFT",
        )
    )
    los = res.scalars().all()
    now = datetime.now(timezone.utc)
    for lo in los:
        lo.status = "APPROVED"
        lo.approved_by = current_user.id
        lo.approved_at = now

    await db.commit()
    return await list_learning_outcomes(subject_id, None, db, current_user)
