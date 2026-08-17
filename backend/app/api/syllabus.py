"""
ADAPT — Structured Syllabus API

GET  /api/subjects/{id}/syllabus — Get latest structured syllabus
PUT  /api/subjects/{id}/syllabus — Edit structured syllabus units and topics
POST /api/subjects/{id}/syllabus/confirm — Finalize and confirm syllabus
POST /api/subjects/{id}/syllabus/analyze — Trigger re-analysis
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.document import Document
from app.models.subject import Subject
from app.models.syllabus import Syllabus, SyllabusUnit, Topic
from app.models.user import User
from app.rag.ingestion import IngestionPipeline
from app.schemas.syllabus import (
    SyllabusResponse,
    SyllabusUpdateRequest,
    SyllabusUnitResponse,
    TopicResponse,
)

router = APIRouter(prefix="/api/subjects", tags=["Syllabus"])


@router.get("/{subject_id}/syllabus", response_model=SyllabusResponse)
async def get_subject_syllabus(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the active structured syllabus for a subject."""
    res = await db.execute(
        select(Syllabus)
        .where(Syllabus.subject_id == subject_id)
        .order_by(Syllabus.version.desc())
        .limit(1)
    )
    syllabus = res.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(
            status_code=404,
            detail="No syllabus found for this subject. Please upload a syllabus document first.",
        )

    # Build response with units and topics
    units_res = await db.execute(
        select(SyllabusUnit)
        .where(SyllabusUnit.syllabus_id == syllabus.id)
        .order_by(SyllabusUnit.unit_number)
    )
    units = units_res.scalars().all()

    unit_responses = []
    for u in units:
        topics_res = await db.execute(
            select(Topic)
            .where(Topic.unit_id == u.id)
            .order_by(Topic.sequence_order)
        )
        topics = topics_res.scalars().all()
        unit_responses.append(
            SyllabusUnitResponse(
                id=u.id,
                unit_number=u.unit_number,
                title=u.title,
                hours=u.hours,
                topics=[TopicResponse.model_validate(t) for t in topics],
            )
        )

    resp = SyllabusResponse.model_validate(syllabus)
    resp.units = unit_responses
    return resp


@router.put("/{subject_id}/syllabus", response_model=SyllabusResponse)
async def update_syllabus(
    subject_id: UUID,
    req: SyllabusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty edit for structured syllabus units and topics."""
    res = await db.execute(
        select(Syllabus)
        .where(Syllabus.subject_id == subject_id)
        .order_by(Syllabus.version.desc())
        .limit(1)
    )
    syllabus = res.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(status_code=404, detail="No syllabus exists to edit")

    # Update structured_data json
    data = req.structured_data
    syllabus.structured_data = data.model_dump()

    # Re-sync SyllabusUnit and Topic tables
    # Delete old units for this syllabus
    old_units_res = await db.execute(
        select(SyllabusUnit).where(SyllabusUnit.syllabus_id == syllabus.id)
    )
    old_units = old_units_res.scalars().all()
    for u in old_units:
        await db.delete(u)
    await db.flush()

    # Add new units
    for u in data.units:
        unit_obj = SyllabusUnit(
            syllabus_id=syllabus.id,
            unit_number=u.unit_number,
            title=u.title,
            hours=u.hours,
        )
        db.add(unit_obj)
        await db.flush()
        await db.refresh(unit_obj)

        for idx, t in enumerate(u.topics):
            topic_obj = Topic(
                unit_id=unit_obj.id,
                name=t.name,
                sequence_order=idx + 1,
                subtopics=t.subtopics,
            )
            db.add(topic_obj)

    # Sync subject header info
    subj_res = await db.execute(select(Subject).where(Subject.id == subject_id))
    subj = subj_res.scalar_one_or_none()
    if subj:
        if data.credits:
            subj.credits = data.credits
        if data.teaching_hours:
            subj.teaching_hours = data.teaching_hours
        if data.prerequisites:
            subj.prerequisites = data.prerequisites
        if data.course_objectives:
            subj.course_objectives = data.course_objectives

    await db.commit()

    return await get_subject_syllabus(subject_id, db, current_user)


@router.post("/{subject_id}/syllabus/confirm", response_model=SyllabusResponse)
async def confirm_syllabus(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty officially approves/confirms the syllabus representation."""
    res = await db.execute(
        select(Syllabus)
        .where(Syllabus.subject_id == subject_id)
        .order_by(Syllabus.version.desc())
        .limit(1)
    )
    syllabus = res.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(status_code=404, detail="No syllabus found")

    syllabus.status = "CONFIRMED"
    syllabus.confirmed_by = current_user.id
    syllabus.confirmed_at = datetime.now(timezone.utc)
    await db.commit()

    return await get_subject_syllabus(subject_id, db, current_user)
