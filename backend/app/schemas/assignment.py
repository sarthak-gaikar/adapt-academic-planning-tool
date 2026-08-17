"""
ADAPT — Assignment Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.question import QuestionResponse


class AssignmentGenerateRequest(BaseModel):
    title: str = Field(..., description="Assignment title (e.g. Assignment 1: Text Preprocessing & POS Tagging)")
    description: Optional[str] = None
    units: List[int] = Field(default_factory=list, description="Target units to cover")
    cos: List[str] = Field(default_factory=list, description="Target COs")
    bloom_levels: List[str] = Field(default_factory=list, description="Target cognitive levels")
    difficulty: str = Field("MEDIUM", description="EASY | MEDIUM | HARD | MIXED")
    total_marks: int = Field(20, ge=5, le=100, description="Total assignment marks")
    num_questions: int = Field(4, ge=1, le=15, description="Number of questions")
    question_types: List[str] = Field(default_factory=list)


class AssignmentQuestionItem(BaseModel):
    id: UUID
    sequence_order: int
    marks: int
    question: QuestionResponse


class AssignmentResponse(BaseModel):
    id: UUID
    subject_id: UUID
    generation_run_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    total_marks: int
    config: Dict[str, Any] = {}
    status: str
    version: int
    validation_report: Dict[str, Any] = {}
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    questions: List[AssignmentQuestionItem] = []

    model_config = {"from_attributes": True}


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
