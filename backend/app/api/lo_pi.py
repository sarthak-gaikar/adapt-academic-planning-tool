"""
ADAPT — LO-PI Mapping API

POST /api/subjects/{id}/lo-pi-mappings/generate — AI-suggest LO-PI mappings
GET  /api/subjects/{id}/lo-pi-mappings          — Get LO-PI matrix
PUT  /api/lo-pi-mappings/{id}                   — Faculty edit mapping
POST /api/lo-pi-mappings/{id}/approve           — Approve mapping
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.lo_pi_mapper import LOPIMapper
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.learning_outcome import LearningOutcome
from app.models.lo_pi_mapping import LOPIMapping
from app.models.performance_indicator import PerformanceIndicator
from app.models.program_outcome import ProgramOutcome
from app.models.subject import Subject
from app.models.user import User
from app.schemas.lo_pi import (
    LOPIMappingItemResponse,
    LOPIMatrixResponse,
    LOPIMappingUpdate,
)

router = APIRouter(tags=["LO-PI Mapping"])


async def _run_bg_lo_pi_mapping(task_info, subject_id: UUID, user_id: UUID):
    async with async_session_factory() as session:
        mapper = LOPIMapper(session)
        mappings = await mapper.generate_mappings(subject_id, user_id)
        return {"mappings_generated": len(mappings)}


@router.post("/api/subjects/{subject_id}/lo-pi-mappings/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_lo_pi_mappings(
    subject_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI-generated LO-PI mapping suggestions."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate LO-PI mappings for subject {subject_id}",
        _run_bg_lo_pi_mapping,
        subject_id,
        current_user.id,
    )
    return {"task_id": task_id, "message": "LO-PI mapping generation started."}


@router.get("/api/subjects/{subject_id}/lo-pi-mappings", response_model=LOPIMatrixResponse)
async def get_lo_pi_matrix(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full LO-PI mapping matrix for a subject."""
    # Get LOs
    lo_res = await db.execute(
        select(LearningOutcome)
        .where(LearningOutcome.subject_id == subject_id, LearningOutcome.status.in_(["DRAFT", "APPROVED"]))
        .order_by(LearningOutcome.lo_code)
    )
    los = lo_res.scalars().all()
    lo_codes = [lo.lo_code for lo in los]
    lo_id_to_code = {lo.id: lo.lo_code for lo in los}

    # Get all PIs and POs
    pi_res = await db.execute(
        select(PerformanceIndicator).where(PerformanceIndicator.is_active == True).order_by(PerformanceIndicator.pi_code)
    )
    pis = pi_res.scalars().all()
    pi_codes = [pi.pi_code for pi in pis]
    pi_id_to_code = {pi.id: pi.pi_code for pi in pis}

    po_res = await db.execute(
        select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
    )
    pos = po_res.scalars().all()
    po_codes = [po.po_code for po in pos]
    po_id_to_code = {po.id: po.po_code for po in pos}

    # Get mappings
    lo_ids = [lo.id for lo in los]
    mappings = []
    if lo_ids:
        m_res = await db.execute(
            select(LOPIMapping).where(LOPIMapping.lo_id.in_(lo_ids))
        )
        mappings = m_res.scalars().all()

    # Build matrix
    matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for lo_code in lo_codes:
        matrix[lo_code] = {}

    for m in mappings:
        lo_code = lo_id_to_code.get(m.lo_id)
        pi_code = pi_id_to_code.get(m.pi_id)
        po_code = po_id_to_code.get(m.po_id)
        if lo_code and pi_code:
            matrix[lo_code][pi_code] = {
                "id": str(m.id),
                "level": m.mapping_level,
                "po_code": po_code or "",
                "rationale": m.rationale,
                "status": m.status,
            }

    return LOPIMatrixResponse(
        subject_id=subject_id,
        lo_list=lo_codes,
        pi_list=pi_codes,
        po_list=po_codes,
        matrix=matrix,
    )


@router.put("/api/lo-pi-mappings/{mapping_id}", response_model=LOPIMappingItemResponse)
async def update_lo_pi_mapping(
    mapping_id: UUID,
    data: LOPIMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits an LO-PI mapping level or rationale."""
    res = await db.execute(select(LOPIMapping).where(LOPIMapping.id == mapping_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="LO-PI mapping not found")

    m.mapping_level = data.mapping_level
    if data.rationale is not None:
        m.rationale = data.rationale
    await db.commit()
    await db.refresh(m)

    lo_code = m.learning_outcome.lo_code if m.learning_outcome else ""
    pi_code = m.performance_indicator.pi_code if m.performance_indicator else ""
    po_code = m.program_outcome.po_code if m.program_outcome else ""

    return LOPIMappingItemResponse(
        id=m.id, lo_id=m.lo_id, pi_id=m.pi_id, po_id=m.po_id,
        lo_code=lo_code, pi_code=pi_code, po_code=po_code,
        mapping_level=m.mapping_level, rationale=m.rationale, status=m.status,
    )


@router.post("/api/lo-pi-mappings/{mapping_id}/approve", response_model=LOPIMappingItemResponse)
async def approve_lo_pi_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve an LO-PI mapping."""
    res = await db.execute(select(LOPIMapping).where(LOPIMapping.id == mapping_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="LO-PI mapping not found")

    m.status = "APPROVED"
    m.approved_by = current_user.id
    await db.commit()
    await db.refresh(m)

    lo_code = m.learning_outcome.lo_code if m.learning_outcome else ""
    pi_code = m.performance_indicator.pi_code if m.performance_indicator else ""
    po_code = m.program_outcome.po_code if m.program_outcome else ""

    return LOPIMappingItemResponse(
        id=m.id, lo_id=m.lo_id, pi_id=m.pi_id, po_id=m.po_id,
        lo_code=lo_code, pi_code=pi_code, po_code=po_code,
        mapping_level=m.mapping_level, rationale=m.rationale, status=m.status,
    )
