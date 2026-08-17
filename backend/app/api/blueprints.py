"""
ADAPT — Exam Blueprints API

POST /api/subjects/{id}/blueprints — Create blueprint
GET  /api/subjects/{id}/blueprints — List blueprints
GET  /api/blueprints/{bid}         — Get blueprint details
PUT  /api/blueprints/{bid}         — Update blueprint
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.exam import ExamBlueprint
from app.models.subject import Subject
from app.models.user import User
from app.schemas.exam import BlueprintCreate, BlueprintResponse

router = APIRouter(tags=["Exam Blueprints"])


@router.post("/api/subjects/{subject_id}/blueprints", response_model=BlueprintResponse, status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    subject_id: UUID,
    data: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new exam blueprint (MSE / ESE)."""
    res = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    bp = ExamBlueprint(
        subject_id=subject_id,
        created_by=current_user.id,
        exam_type=data.exam_type,
        total_marks=data.total_marks,
        units_covered=data.units_covered,
        difficulty_distribution=data.difficulty_distribution,
        bloom_distribution=data.bloom_distribution,
        co_distribution=data.co_distribution,
        section_structure=[s.model_dump() for s in data.section_structure],
        has_internal_choice=data.has_internal_choice,
        status="APPROVED",
    )
    db.add(bp)
    await db.commit()
    await db.refresh(bp)
    return BlueprintResponse.model_validate(bp)


@router.get("/api/subjects/{subject_id}/blueprints", response_model=List[BlueprintResponse])
async def list_blueprints(
    subject_id: UUID,
    exam_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List exam blueprints for a subject."""
    filters = [ExamBlueprint.subject_id == subject_id]
    if exam_type:
        filters.append(ExamBlueprint.exam_type == exam_type)

    res = await db.execute(select(ExamBlueprint).where(*filters).order_by(ExamBlueprint.created_at.desc()))
    blueprints = res.scalars().all()

    # If no blueprint exists, generate default MSE & ESE blueprints on the fly
    if not blueprints:
        default_mse = ExamBlueprint(
            subject_id=subject_id,
            created_by=current_user.id,
            exam_type="MSE",
            total_marks=30,
            units_covered=[1, 2, 3],
            difficulty_distribution={"EASY": 30, "MEDIUM": 50, "HARD": 20},
            bloom_distribution={"Remember": 10, "Understand": 30, "Apply": 40, "Analyze": 20},
            section_structure=[
                {"name": "Section A", "total_marks": 10, "marks_per_question": 2, "num_questions_to_answer": 5, "num_questions_given": 5, "question_type": "SHORT"},
                {"name": "Section B", "total_marks": 20, "marks_per_question": 10, "num_questions_to_answer": 2, "num_questions_given": 3, "question_type": "LONG"},
            ],
            has_internal_choice=False,
            status="APPROVED",
        )
        default_ese = ExamBlueprint(
            subject_id=subject_id,
            created_by=current_user.id,
            exam_type="ESE",
            total_marks=50,
            units_covered=[1, 2, 3, 4, 5],
            difficulty_distribution={"EASY": 20, "MEDIUM": 60, "HARD": 20},
            bloom_distribution={"Remember": 10, "Understand": 25, "Apply": 35, "Analyze": 20, "Evaluate": 10},
            section_structure=[
                {"name": "Section A", "total_marks": 10, "marks_per_question": 2, "num_questions_to_answer": 5, "num_questions_given": 5, "question_type": "SHORT"},
                {"name": "Section B", "total_marks": 20, "marks_per_question": 5, "num_questions_to_answer": 4, "num_questions_given": 6, "question_type": "MEDIUM"},
                {"name": "Section C", "total_marks": 20, "marks_per_question": 10, "num_questions_to_answer": 2, "num_questions_given": 4, "question_type": "LONG"},
            ],
            has_internal_choice=True,
            status="APPROVED",
        )
        db.add(default_mse)
        db.add(default_ese)
        await db.commit()
        blueprints = [default_mse, default_ese]
        if exam_type:
            blueprints = [b for b in blueprints if b.exam_type == exam_type]

    return [BlueprintResponse.model_validate(b) for b in blueprints]
