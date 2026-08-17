"""
ADAPT — CO-PO Mapping API

POST /api/subjects/{id}/co-po/generate — Generate suggested correlation matrix
GET  /api/subjects/{id}/co-po          — Get full CO x PO matrix with justifications
PUT  /api/co-po/{mapping_id}           — Override individual cell value (0-3)
POST /api/subjects/{id}/co-po/approve  — Officially approve the matrix
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.co_po_mapper import COPOMapper
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.co_po_mapping import COPOMapping
from app.models.course_outcome import CourseOutcome
from app.models.program_outcome import ProgramOutcome
from app.models.subject import Subject
from app.models.user import User
from app.schemas.co_po import (
    COPOMappingItemResponse,
    COPOMappingUpdate,
    COPOMatrixResponse,
)

router = APIRouter(tags=["CO-PO Mapping"])


async def _run_bg_co_po_generation(task_info, subject_id: UUID, user_id: UUID):
    async with async_session_factory() as session:
        mapper = COPOMapper(session)
        mappings = await mapper.generate_mappings(subject_id, user_id)
        return {"cells_generated": len(mappings)}


@router.post("/api/subjects/{subject_id}/co-po/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_co_po_mapping(
    subject_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of NBA CO-PO mapping matrix."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate CO-PO Mapping for {subject_id}",
        _run_bg_co_po_generation,
        subject_id,
        current_user.id,
    )
    return {"task_id": task_id, "message": "CO-PO mapping generation started in background."}


@router.get("/api/subjects/{subject_id}/co-po", response_model=COPOMatrixResponse)
async def get_co_po_matrix(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch complete 2D matrix of CO x PO with suggested & approved values."""
    # Fetch all mappings
    res = await db.execute(
        select(COPOMapping, CourseOutcome.co_code, ProgramOutcome.po_code)
        .join(CourseOutcome, COPOMapping.co_id == CourseOutcome.id)
        .join(ProgramOutcome, COPOMapping.po_id == ProgramOutcome.id)
        .where(COPOMapping.subject_id == subject_id)
        .order_by(CourseOutcome.co_code, ProgramOutcome.po_code)
    )
    rows = res.all()

    co_set = set()
    po_set = set()
    matrix_dict = {}

    for mapping_obj, co_code, po_code in rows:
        co_set.add(co_code)
        po_set.add(po_code)

        if co_code not in matrix_dict:
            matrix_dict[co_code] = {}

        matrix_dict[co_code][po_code] = {
            "id": str(mapping_obj.id),
            "suggested": mapping_obj.suggested_level,
            "approved": mapping_obj.approved_level if mapping_obj.approved_level is not None else mapping_obj.suggested_level,
            "rationale": mapping_obj.rationale,
            "status": mapping_obj.status,
        }

    return COPOMatrixResponse(
        subject_id=subject_id,
        co_list=sorted(list(co_set)),
        po_list=sorted(list(po_set)),
        matrix=matrix_dict,
    )


@router.put("/api/co-po/{mapping_id}", response_model=COPOMappingItemResponse)
async def update_mapping_cell(
    mapping_id: UUID,
    data: COPOMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits a specific CO-PO cell level (0, 1, 2, 3) or rationale."""
    res = await db.execute(select(COPOMapping).where(COPOMapping.id == mapping_id))
    mapping = res.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping cell not found")

    mapping.approved_level = data.approved_level
    if data.rationale:
        mapping.rationale = data.rationale
    mapping.status = "DRAFT"

    await db.commit()
    await db.refresh(mapping)

    # Fetch CO code and PO code
    co_res = await db.execute(select(CourseOutcome.co_code).where(CourseOutcome.id == mapping.co_id))
    po_res = await db.execute(select(ProgramOutcome.po_code).where(ProgramOutcome.id == mapping.po_id))

    return COPOMappingItemResponse(
        id=mapping.id,
        subject_id=mapping.subject_id,
        co_id=mapping.co_id,
        po_id=mapping.po_id,
        co_code=co_res.scalar_one() or "",
        po_code=po_res.scalar_one() or "",
        suggested_level=mapping.suggested_level,
        approved_level=mapping.approved_level,
        rationale=mapping.rationale,
        status=mapping.status,
        version=mapping.version,
    )


@router.post("/api/subjects/{subject_id}/co-po/approve", response_model=dict)
async def approve_all_mappings(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty officially approves the entire CO-PO matrix."""
    res = await db.execute(select(COPOMapping).where(COPOMapping.subject_id == subject_id))
    mappings = res.scalars().all()
    now = datetime.now(timezone.utc)
    for m in mappings:
        m.status = "APPROVED"
        m.approved_by = current_user.id
        if m.approved_level is None:
            m.approved_level = m.suggested_level

    await db.commit()
    return {"message": "CO-PO mapping approved successfully."}
