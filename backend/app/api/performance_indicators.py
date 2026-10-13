"""
ADAPT — Performance Indicators API

GET  /api/performance-indicators                       — List all PIs grouped by PO
GET  /api/program-outcomes/{po_id}/performance-indicators — PIs for a specific PO
PUT  /api/performance-indicators/{pi_id}               — Edit PI
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.performance_indicator import PerformanceIndicator
from app.models.program_outcome import ProgramOutcome
from app.models.user import User
from app.schemas.performance_indicator import (
    PerformanceIndicatorResponse,
    PerformanceIndicatorUpdate,
    PIsGroupedByPOResponse,
)

router = APIRouter(tags=["Performance Indicators"])


def _pi_to_response(pi: PerformanceIndicator) -> PerformanceIndicatorResponse:
    po_code = pi.program_outcome.po_code if pi.program_outcome else None
    return PerformanceIndicatorResponse(
        id=pi.id,
        po_id=pi.po_id,
        pi_code=pi.pi_code,
        statement=pi.statement,
        is_active=pi.is_active,
        created_at=pi.created_at,
        po_code=po_code,
    )


@router.get("/api/performance-indicators", response_model=List[PIsGroupedByPOResponse])
async def list_all_performance_indicators(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all Performance Indicators grouped by Program Outcome."""
    po_res = await db.execute(
        select(ProgramOutcome)
        .where(ProgramOutcome.is_active == True)
        .order_by(ProgramOutcome.po_code)
    )
    pos = po_res.scalars().all()

    result = []
    for po in pos:
        pi_res = await db.execute(
            select(PerformanceIndicator)
            .where(PerformanceIndicator.po_id == po.id, PerformanceIndicator.is_active == True)
            .order_by(PerformanceIndicator.pi_code)
        )
        pis = pi_res.scalars().all()
        result.append(PIsGroupedByPOResponse(
            po_code=po.po_code,
            po_id=po.id,
            po_statement=po.statement,
            performance_indicators=[_pi_to_response(pi) for pi in pis],
        ))
    return result


@router.get("/api/program-outcomes/{po_id}/performance-indicators", response_model=List[PerformanceIndicatorResponse])
async def list_po_performance_indicators(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Performance Indicators for a specific Program Outcome."""
    po_res = await db.execute(select(ProgramOutcome).where(ProgramOutcome.id == po_id))
    if not po_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Program Outcome not found")

    pi_res = await db.execute(
        select(PerformanceIndicator)
        .where(PerformanceIndicator.po_id == po_id, PerformanceIndicator.is_active == True)
        .order_by(PerformanceIndicator.pi_code)
    )
    pis = pi_res.scalars().all()
    return [_pi_to_response(pi) for pi in pis]


@router.put("/api/performance-indicators/{pi_id}", response_model=PerformanceIndicatorResponse)
async def update_performance_indicator(
    pi_id: UUID,
    data: PerformanceIndicatorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a Performance Indicator statement or active status."""
    res = await db.execute(select(PerformanceIndicator).where(PerformanceIndicator.id == pi_id))
    pi = res.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=404, detail="Performance Indicator not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(pi, field, val)

    await db.commit()
    await db.refresh(pi)
    return _pi_to_response(pi)
