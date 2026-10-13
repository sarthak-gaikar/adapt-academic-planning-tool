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


class ExamMarkConfig(BaseModel):
    """Marks × count config for exam sections."""
    marks: int = Field(..., ge=1, le=50)
    count: int = Field(..., ge=1, le=20)
    question_type: str = Field("DESCRIPTIVE", description="MCQ | SHORT | LONG | DESCRIPTIVE")


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
    lo_distribution: Dict[str, int] = Field(default_factory=dict, description="LO coverage percentages e.g. {'LO1.1': 20, 'LO2.1': 30}")
    section_structure: List[SectionConfigSchema] = Field(default_factory=list)
    mark_configs: List[ExamMarkConfig] = Field(default_factory=list, description="Marks × count configs for structured question generation")
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


class UnifiedPaperGenerateRequest(BaseModel):
    """Request schema for the unified Generate Paper endpoint."""
    paper_type: str = Field(..., description="MSE or ESE")
    unit_ids: List[int] = Field(..., min_length=1, description="Selected unit numbers")
    total_marks: int = Field(..., ge=10, le=150, description="Requested total marks")
    question_counts: Dict[str, int] = Field(
        ...,
        description="Marks → count mapping, e.g. {'2': 5, '5': 2, '10': 1}"
    )
    additional_file_paths: List[str] = Field(
        default_factory=list,
        description="Paths to temporarily uploaded reference files (optional)"
    )
    custom_title: Optional[str] = None
    custom_instructions: Optional[str] = None

    @property
    def question_counts_int(self) -> Dict[int, int]:
        """Convert string keys to int keys."""
        return {int(k): v for k, v in self.question_counts.items()}

    @property
    def calculated_marks(self) -> int:
        """Auto-calculated total from question counts."""
        return sum(int(k) * v for k, v in self.question_counts.items())

    @property
    def total_questions(self) -> int:
        return sum(self.question_counts.values())

