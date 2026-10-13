"""
ADAPT — OBE Matrix API

GET /api/subjects/{id}/obe-matrix — Full CO→LO→PI→PO traceability matrix
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.database import get_db
from app.models.course_outcome import CourseOutcome
from app.models.learning_outcome import LearningOutcome
from app.models.lo_co_mapping import LOCOMapping
from app.models.lo_pi_mapping import LOPIMapping
from app.models.performance_indicator import PerformanceIndicator
from app.models.program_outcome import ProgramOutcome
from app.models.user import User

router = APIRouter(tags=["OBE Matrix"])


class OBEMatrixLO(BaseModel):
    lo_code: str
    statement: str
    bloom_level: Optional[str] = None
    unit_number: Optional[int] = None
    pis: List[Dict[str, Any]] = []  # [{pi_code, po_code, level, rationale}]


class OBEMatrixCO(BaseModel):
    co_code: str
    statement: str
    bloom_level: Optional[str] = None
    bloom_order: Optional[int] = None
    supporting_units: List[int] = []
    los: List[OBEMatrixLO] = []
    derived_pos: List[Dict[str, Any]] = []  # [{po_code, max_level}]


class OBEMatrixResponse(BaseModel):
    subject_id: UUID
    cos: List[OBEMatrixCO] = []
    po_list: List[str] = []
    summary: Dict[str, Any] = {}  # {total_cos, total_los, total_pis_mapped, total_pos_covered}


@router.get("/api/subjects/{subject_id}/obe-matrix", response_model=OBEMatrixResponse)
async def get_obe_matrix(
    subject_id: UUID,
    co_filter: Optional[str] = Query(None, description="Filter by CO code"),
    unit_filter: Optional[int] = Query(None, description="Filter by unit number"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full CO→LO→PI→PO OBE traceability matrix."""
    # Fetch COs
    co_query = select(CourseOutcome).where(
        CourseOutcome.subject_id == subject_id,
        CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
    )
    if co_filter:
        co_query = co_query.where(CourseOutcome.co_code == co_filter)
    co_query = co_query.order_by(CourseOutcome.co_code)
    co_res = await db.execute(co_query)
    cos = co_res.scalars().all()

    # Fetch LOs
    lo_query = select(LearningOutcome).where(
        LearningOutcome.subject_id == subject_id,
        LearningOutcome.status.in_(["DRAFT", "APPROVED"]),
    )
    lo_query = lo_query.order_by(LearningOutcome.lo_code)
    lo_res = await db.execute(lo_query)
    los = lo_res.scalars().all()

    # Build LO lookup
    lo_dict = {lo.id: lo for lo in los}

    # Fetch CO-LO mappings
    lo_ids = [lo.id for lo in los]
    co_lo_mappings = []
    if lo_ids:
        clm_res = await db.execute(select(LOCOMapping).where(LOCOMapping.lo_id.in_(lo_ids)))
        co_lo_mappings = clm_res.scalars().all()

    # Build CO → LO_ids mapping
    co_to_lo_ids: Dict[UUID, List[UUID]] = {}
    for m in co_lo_mappings:
        co_to_lo_ids.setdefault(m.co_id, []).append(m.lo_id)

    # Fetch LO-PI mappings
    lo_pi_mappings = []
    if lo_ids:
        lpm_res = await db.execute(select(LOPIMapping).where(LOPIMapping.lo_id.in_(lo_ids)))
        lo_pi_mappings = lpm_res.scalars().all()

    # Build LO → PI mappings
    lo_to_pis: Dict[UUID, List[Dict]] = {}
    for m in lo_pi_mappings:
        pi_code = m.performance_indicator.pi_code if m.performance_indicator else ""
        po_code = m.program_outcome.po_code if m.program_outcome else ""
        lo_to_pis.setdefault(m.lo_id, []).append({
            "pi_code": pi_code,
            "po_code": po_code,
            "level": m.mapping_level,
            "rationale": m.rationale,
        })

    # Fetch POs
    po_res = await db.execute(
        select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
    )
    pos = po_res.scalars().all()
    po_list = [po.po_code for po in pos]

    # Build matrix
    all_pos_covered = set()
    total_pis = set()
    cos_result = []
    for co in cos:
        mapped_lo_ids = co_to_lo_ids.get(co.id, [])
        co_los = []
        co_po_levels: Dict[str, int] = {}

        for lo_id in mapped_lo_ids:
            lo = lo_dict.get(lo_id)
            if not lo:
                continue
            # Apply unit filter
            unit_num = lo.unit.unit_number if lo.unit else None
            if unit_filter is not None and unit_num != unit_filter:
                continue

            lo_pis = lo_to_pis.get(lo_id, [])
            for pi_entry in lo_pis:
                total_pis.add(pi_entry["pi_code"])
                po_code = pi_entry["po_code"]
                if po_code:
                    all_pos_covered.add(po_code)
                    current_max = co_po_levels.get(po_code, 0)
                    co_po_levels[po_code] = max(current_max, pi_entry["level"])

            co_los.append(OBEMatrixLO(
                lo_code=lo.lo_code,
                statement=lo.statement,
                bloom_level=lo.bloom_level,
                unit_number=unit_num,
                pis=lo_pis,
            ))

        derived_pos = [{"po_code": k, "max_level": v} for k, v in sorted(co_po_levels.items())]

        cos_result.append(OBEMatrixCO(
            co_code=co.co_code,
            statement=co.statement,
            bloom_level=co.bloom_level,
            bloom_order=co.bloom_order,
            supporting_units=co.supporting_units or [],
            los=co_los,
            derived_pos=derived_pos,
        ))

    return OBEMatrixResponse(
        subject_id=subject_id,
        cos=cos_result,
        po_list=po_list,
        summary={
            "total_cos": len(cos_result),
            "total_los": sum(len(c.los) for c in cos_result),
            "total_pis_mapped": len(total_pis),
            "total_pos_covered": len(all_pos_covered),
        },
    )
