"""
ADAPT — Program Outcomes API

GET  /api/program-outcomes — List all institutional POs
POST /api/program-outcomes — Create PO (Admin)
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.program_outcome import ProgramOutcome
from app.models.user import User
from app.schemas.program_outcome import ProgramOutcomeCreate, ProgramOutcomeResponse

router = APIRouter(prefix="/api/program-outcomes", tags=["Program Outcomes"])


@router.get("", response_model=List[ProgramOutcomeResponse])
async def list_program_outcomes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all institution Program Outcomes (POs and PSOs)."""
    res = await db.execute(
        select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
    )
    pos = res.scalars().all()
    return [ProgramOutcomeResponse.model_validate(po) for po in pos]


@router.post("", response_model=ProgramOutcomeResponse, status_code=status.HTTP_201_CREATED)
async def create_program_outcome(
    data: ProgramOutcomeCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Add a new Program Outcome (Admin only)."""
    res = await db.execute(select(ProgramOutcome).where(ProgramOutcome.po_code == data.po_code))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"PO {data.po_code} already exists")

    po = ProgramOutcome(**data.model_dump())
    db.add(po)
    await db.commit()
    await db.refresh(po)
    return ProgramOutcomeResponse.model_validate(po)
