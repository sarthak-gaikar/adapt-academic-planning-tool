"""
ADAPT — Exam Pydantic Schemas

Blueprints, Exam Papers, Sections, and Questions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.question import QuestionResponse


# ---- Blueprints ----

class SectionConfigSchema(BaseModel):
    name: str = Field(..., description="Section A, Section B, etc.")
    title: Optional[str] = None
    total_marks: int
    num_questions_to_answer: int
    num_questions_given: int
    question_type: str = "SHORT"  # MCQ | SHORT | LONG | DESCRIPTIVE
    marks_per_question: int
    has_internal_choice: bool = False


class BlueprintCreate(BaseModel):
    exam_type: str = Field("MSE", description="MSE | ESE")
    total_marks: int = Field(30, ge=10, le=150)
    units_covered: List[int] = Field(default_factory=lambda: [1, 2, 3])
    difficulty_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"EASY": 30, "MEDIUM": 50, "HARD": 20}
    )
    bloom_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"Remember": 10, "Understand": 30, "Apply": 40, "Analyze": 20}
    )
    co_distribution: Dict[str, int] = Field(default_factory=dict)
    section_structure: List[SectionConfigSchema] = Field(default_factory=list)
    has_internal_choice: bool = False


class BlueprintResponse(BaseModel):
    id: UUID
    subject_id: UUID
    exam_type: str
    total_marks: int
    units_covered: List[int] = []
    difficulty_distribution: Dict[str, int] = {}
    bloom_distribution: Dict[str, int] = {}
    co_distribution: Dict[str, int] = {}
    section_structure: List[Dict[str, Any]] = []
    has_internal_choice: bool
    status: str
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Exam Paper ----

class ExamQuestionItem(BaseModel):
    id: UUID
    section: Optional[str] = None
    sequence_order: int
    marks: int
    is_compulsory: bool = True
    choice_group: Optional[str] = None
    question: QuestionResponse


class ExamPaperResponse(BaseModel):
    id: UUID
    subject_id: UUID
    blueprint_id: UUID
    generation_run_id: Optional[UUID] = None
    exam_type: str
    title: str
    instructions: Optional[str] = None
    total_marks: int
    status: str
    version: int
    validation_report: Dict[str, Any] = {}
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    questions: List[ExamQuestionItem] = []

    model_config = {"from_attributes": True}


class ExamGenerateRequest(BaseModel):
    blueprint_id: Optional[UUID] = None
    custom_title: Optional[str] = None
    custom_instructions: Optional[str] = None
