"""
ADAPT — Subjects API Endpoints

CRUD for subjects with ownership enforcement.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.subject import Subject
from app.models.syllabus import Syllabus
from app.models.course_outcome import CourseOutcome
from app.models.question import Question
from app.models.assignment import Assignment
from app.models.exam import ExamPaper
from app.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectDetailResponse,
    SubjectResponse,
    SubjectUpdate,
)

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new subject."""
    # Check duplicate course code
    result = await db.execute(
        select(Subject).where(Subject.course_code == data.course_code)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject with course code '{data.course_code}' already exists",
        )

    subject = Subject(
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List subjects accessible to the current user."""
    if current_user.role == "ADMIN":
        result = await db.execute(
            select(Subject).where(Subject.status == "ACTIVE").order_by(Subject.name)
        )
    else:
        result = await db.execute(
            select(Subject)
            .where(Subject.created_by == current_user.id, Subject.status == "ACTIVE")
            .order_by(Subject.name)
        )
    subjects = result.scalars().all()
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.get("/{subject_id}", response_model=SubjectDetailResponse)
async def get_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get subject details with stats."""
    subject = await _get_subject_with_access(subject_id, current_user, db)

    # Gather stats
    syllabus_result = await db.execute(
        select(Syllabus.status)
        .where(Syllabus.subject_id == subject_id)
        .order_by(Syllabus.version.desc())
        .limit(1)
    )
    syllabus_status = syllabus_result.scalar_one_or_none()

    co_count = await db.scalar(
        select(func.count()).where(
            CourseOutcome.subject_id == subject_id,
            CourseOutcome.status != "ARCHIVED",
        )
    )
    question_count = await db.scalar(
        select(func.count()).where(
            Question.subject_id == subject_id,
            Question.status != "ARCHIVED",
        )
    )
    assignment_count = await db.scalar(
        select(func.count()).where(
            Assignment.subject_id == subject_id,
            Assignment.status != "ARCHIVED",
        )
    )
    exam_count = await db.scalar(
        select(func.count()).where(
            ExamPaper.subject_id == subject_id,
            ExamPaper.status != "ARCHIVED",
        )
    )

    response = SubjectDetailResponse.model_validate(subject)
    response.syllabus_status = syllabus_status
    response.co_count = co_count or 0
    response.question_count = question_count or 0
    response.assignment_count = assignment_count or 0
    response.exam_count = exam_count or 0
    return response


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update subject details."""
    subject = await _get_subject_with_access(subject_id, current_user, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)

    await db.flush()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Soft-delete (archive) a subject. Admin only."""
    subject = await _get_subject_with_access(subject_id, current_user, db)
    subject.status = "ARCHIVED"
    await db.flush()


# ---- Helpers ----

async def _get_subject_with_access(
    subject_id: UUID,
    user: User,
    db: AsyncSession,
) -> Subject:
    """Fetch a subject and verify the user has access."""
    result = await db.execute(
        select(Subject).where(Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role != "ADMIN" and subject.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this subject")
    return subject
