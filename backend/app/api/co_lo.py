"""
ADAPT — CO-LO Mapping API

POST /api/subjects/{id}/co-lo-mappings/generate — AI-suggest CO-LO mappings
GET  /api/subjects/{id}/co-lo-mappings          — Get CO-LO matrix
PUT  /api/co-lo-mappings/{id}                   — Faculty edit mapping
POST /api/co-lo-mappings/{id}/approve           — Approve mapping
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.co_lo_mapper import COLOMapper
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.course_outcome import CourseOutcome
from app.models.learning_outcome import LearningOutcome
from app.models.lo_co_mapping import LOCOMapping
from app.models.subject import Subject
from app.models.user import User
from app.schemas.co_lo import (
    COLOMappingItemResponse,
    COLOMatrixResponse,
    COLOMappingUpdate,
)

router = APIRouter(tags=["CO-LO Mapping"])


async def _run_bg_co_lo_mapping(task_info, subject_id: UUID, user_id: UUID):
    async with async_session_factory() as session:
        mapper = COLOMapper(session)
        mappings = await mapper.generate_mappings(subject_id, user_id)
        return {"mappings_generated": len(mappings)}


@router.post("/api/subjects/{subject_id}/co-lo-mappings/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_co_lo_mappings(
    subject_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI-generated CO-LO mapping suggestions."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate CO-LO mappings for subject {subject_id}",
        _run_bg_co_lo_mapping,
        subject_id,
        current_user.id,
    )
    return {"task_id": task_id, "message": "CO-LO mapping generation started."}


@router.get("/api/subjects/{subject_id}/co-lo-mappings", response_model=COLOMatrixResponse)
async def get_co_lo_matrix(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full CO-LO mapping matrix for a subject."""
    # Get COs
    co_res = await db.execute(
        select(CourseOutcome)
        .where(CourseOutcome.subject_id == subject_id, CourseOutcome.status.in_(["DRAFT", "APPROVED"]))
        .order_by(CourseOutcome.co_code)
    )
    cos = co_res.scalars().all()
    co_codes = [co.co_code for co in cos]

    # Get LOs
    lo_res = await db.execute(
        select(LearningOutcome)
        .where(LearningOutcome.subject_id == subject_id, LearningOutcome.status.in_(["DRAFT", "APPROVED"]))
        .order_by(LearningOutcome.lo_code)
    )
    los = lo_res.scalars().all()
    lo_codes = [lo.lo_code for lo in los]

    # Get mappings
    lo_ids = [lo.id for lo in los]
    mappings = []
    if lo_ids:
        m_res = await db.execute(
            select(LOCOMapping).where(LOCOMapping.lo_id.in_(lo_ids))
        )
        mappings = m_res.scalars().all()

    # Build lookup
    lo_id_to_code = {lo.id: lo.lo_code for lo in los}
    co_id_to_code = {co.id: co.co_code for co in cos}

    # Build matrix: {lo_code: {co_code: {strength, rationale, id, status}}}
    matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for lo_code in lo_codes:
        matrix[lo_code] = {}

    for m in mappings:
        lo_code = lo_id_to_code.get(m.lo_id)
        co_code = co_id_to_code.get(m.co_id)
        if lo_code and co_code:
            matrix[lo_code][co_code] = {
                "id": str(m.id),
                "strength": m.mapping_strength,
                "rationale": m.rationale,
                "status": m.status,
            }

    return COLOMatrixResponse(
        subject_id=subject_id,
        lo_list=lo_codes,
        co_list=co_codes,
        matrix=matrix,
    )


@router.put("/api/co-lo-mappings/{mapping_id}", response_model=COLOMappingItemResponse)
async def update_co_lo_mapping(
    mapping_id: UUID,
    data: COLOMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits a CO-LO mapping strength or rationale."""
    res = await db.execute(select(LOCOMapping).where(LOCOMapping.id == mapping_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="CO-LO mapping not found")

    m.mapping_strength = data.mapping_strength
    if data.rationale is not None:
        m.rationale = data.rationale
    await db.commit()
    await db.refresh(m)

    lo_code = m.learning_outcome.lo_code if m.learning_outcome else ""
    co_code = m.course_outcome.co_code if m.course_outcome else ""

    return COLOMappingItemResponse(
        id=m.id, lo_id=m.lo_id, co_id=m.co_id,
        lo_code=lo_code, co_code=co_code,
        mapping_strength=m.mapping_strength,
        rationale=m.rationale, status=m.status,
    )


@router.post("/api/co-lo-mappings/{mapping_id}/approve", response_model=COLOMappingItemResponse)
async def approve_co_lo_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a CO-LO mapping."""
    res = await db.execute(select(LOCOMapping).where(LOCOMapping.id == mapping_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="CO-LO mapping not found")

    m.status = "APPROVED"
    m.approved_by = current_user.id
    await db.commit()
    await db.refresh(m)

    lo_code = m.learning_outcome.lo_code if m.learning_outcome else ""
    co_code = m.course_outcome.co_code if m.course_outcome else ""

    return COLOMappingItemResponse(
        id=m.id, lo_id=m.lo_id, co_id=m.co_id,
        lo_code=lo_code, co_code=co_code,
        mapping_strength=m.mapping_strength,
        rationale=m.rationale, status=m.status,
    )
