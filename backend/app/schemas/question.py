"""
ADAPT — Question Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class QuestionGeneratedItem(BaseModel):
    question_text: str = Field(..., description="The complete text of the question")
    question_type: str = Field("DESCRIPTIVE", description="MCQ | SHORT | LONG | NUMERICAL | CODING | DESCRIPTIVE")
    marks: int = Field(..., ge=1, le=50, description="Marks allocated")
    difficulty: str = Field("MEDIUM", description="EASY | MEDIUM | HARD")
    bloom_level: str = Field("Understand", description="Bloom level")
    co_code: Optional[str] = Field(None, description="Mapped CO code (e.g. CO1)")
    unit_number: Optional[int] = Field(None, description="Target syllabus unit")
    topic: Optional[str] = Field(None, description="Target syllabus topic")
    reference_answer: Optional[str] = Field(None, description="Concise model answer")
    marking_scheme: Optional[str] = Field(None, description="Point-by-point marking breakdown")


class QuestionBatchGenerationSchema(BaseModel):
    questions: List[QuestionGeneratedItem] = Field(default_factory=list)


class QuestionGenerateRequest(BaseModel):
    unit_number: Optional[int] = None
    topic: Optional[str] = None
    co_code: Optional[str] = None
    bloom_level: Optional[str] = None
    difficulty: Optional[str] = "MEDIUM"
    marks: Optional[int] = 5
    question_type: Optional[str] = "DESCRIPTIVE"
    count: Optional[int] = Field(3, ge=1, le=20, description="Number of questions to generate")
    custom_guidelines: Optional[str] = None


# ---- API Responses ----

class QuestionResponse(BaseModel):
    id: UUID
    subject_id: UUID
    generation_run_id: Optional[UUID] = None
    question_text: str
    question_type: str
    marks: int
    difficulty: str
    bloom_level: Optional[str] = None
    bloom_confidence: Optional[float] = None
    co_code: Optional[str] = None
    unit_number: Optional[int] = None
    topic: Optional[str] = None
    reference_answer: Optional[str] = None
    marking_scheme: Optional[str] = None
    source_context: Dict[str, Any] = {}
    status: str
    version: int
    academic_year: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    marks: Optional[int] = None
    difficulty: Optional[str] = None
    bloom_level: Optional[str] = None
    co_code: Optional[str] = None
    unit_number: Optional[int] = None
    topic: Optional[str] = None
    reference_answer: Optional[str] = None
    marking_scheme: Optional[str] = None
