"""
ADAPT — Academic Activity Plan (AAP) API

POST /api/subjects/{id}/aap/generate — Generate semester lesson plan with constraints
GET  /api/subjects/{id}/aap          — Get active AAP plan & validation report
PUT  /api/subjects/{id}/aap          — Faculty edit of plan data
POST /api/subjects/{id}/aap/approve  — Officially approve AAP
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.aap_generator import AAPGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.aap import AAPPlan
from app.models.subject import Subject
from app.models.user import User
from app.schemas.aap import (
    AAPGenerationRequest,
    AAPPlanDataSchema,
    AAPPlanResponse,
    AAPPlanUpdateRequest,
)
from app.validators.aap_validator import AAPValidator

router = APIRouter(prefix="/api/subjects", tags=["Academic Activity Plan"])


async def _run_bg_aap_generation(task_info, subject_id: UUID, user_id: UUID, req: AAPGenerationRequest):
    async with async_session_factory() as session:
        generator = AAPGenerator(session)
        plan = await generator.generate_aap(subject_id, user_id, req)
        return {"weeks_planned": plan.total_weeks, "total_hours": plan.total_hours}


@router.post("/{subject_id}/aap/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_aap(
    subject_id: UUID,
    req: AAPGenerationRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of semester Academic Activity Plan."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate AAP for subject {subject_id}",
        _run_bg_aap_generation,
        subject_id,
        current_user.id,
        req or AAPGenerationRequest(),
    )
    return {"task_id": task_id, "message": "AAP generation started in background."}


@router.get("/{subject_id}/aap", response_model=AAPPlanResponse)
async def get_aap_plan(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the active Academic Activity Plan and validation checks."""
    res = await db.execute(
        select(AAPPlan)
        .where(AAPPlan.subject_id == subject_id)
        .order_by(AAPPlan.version.desc())
        .limit(1)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No AAP plan found. Please generate one first.")

    return AAPPlanResponse(
        id=plan.id,
        subject_id=plan.subject_id,
        generation_run_id=plan.generation_run_id,
        template_config=plan.template_config or {},
        plan_data=AAPPlanDataSchema.model_validate(plan.plan_data) if plan.plan_data else None,
        total_weeks=plan.total_weeks,
        total_hours=plan.total_hours,
        status=plan.status,
        version=plan.version,
        validation_report=plan.validation_report or {},
        approved_by=plan.approved_by,
        approved_at=plan.approved_at,
        created_at=plan.created_at,
    )


@router.put("/{subject_id}/aap", response_model=AAPPlanResponse)
async def update_aap_plan(
    subject_id: UUID,
    req: AAPPlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edits rows of the AAP plan with re-validation."""
    res = await db.execute(
        select(AAPPlan)
        .where(AAPPlan.subject_id == subject_id)
        .order_by(AAPPlan.version.desc())
        .limit(1)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No AAP plan found to edit")

    plan_data = req.plan_data
    plan.plan_data = plan_data.model_dump()
    plan.total_weeks = plan_data.total_weeks
    plan.total_hours = sum(w.planned_hours for w in plan_data.weeks)

    # Re-run validation
    subj_res = await db.execute(select(Subject).where(Subject.id == subject_id))
    subj = subj_res.scalar_one_or_none()
    expected_hours = (subj.teaching_hours if subj and subj.teaching_hours else 45)

    val_report = AAPValidator.validate(plan=plan_data, expected_total_hours=expected_hours)
    plan.validation_report = val_report

    await db.commit()
    return await get_aap_plan(subject_id, db, current_user)


@router.post("/{subject_id}/aap/approve", response_model=AAPPlanResponse)
async def approve_aap_plan(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve the Academic Activity Plan."""
    res = await db.execute(
        select(AAPPlan)
        .where(AAPPlan.subject_id == subject_id)
        .order_by(AAPPlan.version.desc())
        .limit(1)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No AAP plan found")

    plan.status = "APPROVED"
    plan.approved_by = current_user.id
    plan.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return await get_aap_plan(subject_id, db, current_user)
