"""
ADAPT — Assignments API

POST /api/subjects/{id}/assignments/generate — Generate assignment with balanced marks
GET  /api/subjects/{id}/assignments          — List subject assignments
GET  /api/assignments/{aid}                  — Get assignment details with questions
PUT  /api/assignments/{aid}                  — Edit assignment
POST /api/assignments/{aid}/approve          — Officially approve assignment
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assignment_generator import AssignmentGenerator
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.schemas.assignment import (
    AssignmentGenerateRequest,
    AssignmentQuestionItem,
    AssignmentResponse,
    AssignmentUpdate,
)
from app.schemas.question import QuestionResponse

router = APIRouter(tags=["Assignments"])


async def _run_bg_assignment_gen(task_info, subject_id: UUID, user_id: UUID, req: AssignmentGenerateRequest):
    async with async_session_factory() as session:
        generator = AssignmentGenerator(session)
        assignment = await generator.generate_assignment(subject_id, user_id, req)
        return {"assignment_id": str(assignment.id), "title": assignment.title}


@router.post("/api/subjects/{subject_id}/assignments/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_assignment_endpoint(
    subject_id: UUID,
    req: AssignmentGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background generation of a structured assignment."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Generate Assignment '{req.title}'",
        _run_bg_assignment_gen,
        subject_id,
        current_user.id,
        req,
    )
    return {"task_id": task_id, "message": "Assignment generation started in background."}


@router.get("/api/subjects/{subject_id}/assignments", response_model=List[AssignmentResponse])
async def list_assignments(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all assignments for a subject."""
    res = await db.execute(
        select(Assignment)
        .where(Assignment.subject_id == subject_id, Assignment.status != "ARCHIVED")
        .order_by(Assignment.created_at.desc())
    )
    assignments = res.scalars().all()
    out = []
    for a in assignments:
        resp = await _build_assignment_response(a, db)
        out.append(resp)
    return out


@router.get("/api/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get complete assignment with all questions and answers."""
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return await _build_assignment_response(assignment, db)


@router.put("/api/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(assignment, field, val)

    await db.commit()
    return await _build_assignment_response(assignment, db)


@router.post("/api/assignments/{assignment_id}/approve", response_model=AssignmentResponse)
async def approve_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially approve an assignment."""
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.status = "APPROVED"
    assignment.approved_by = current_user.id
    assignment.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return await _build_assignment_response(assignment, db)


# ---- Helper ----

async def _build_assignment_response(assignment: Assignment, db: AsyncSession) -> AssignmentResponse:
    aq_res = await db.execute(
        select(AssignmentQuestion, Question)
        .join(Question, AssignmentQuestion.question_id == Question.id)
        .where(AssignmentQuestion.assignment_id == assignment.id)
        .order_by(AssignmentQuestion.sequence_order)
    )
    rows = aq_res.all()
    q_items = []
    for aq, q in rows:
        q_items.append(
            AssignmentQuestionItem(
                id=aq.id,
                sequence_order=aq.sequence_order,
                marks=aq.marks,
                question=QuestionResponse.model_validate(q),
            )
        )

    resp = AssignmentResponse.model_validate(assignment)
    resp.questions = q_items
    return resp
