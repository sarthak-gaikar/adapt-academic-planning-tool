"""
ADAPT — Answer Key Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AnswerKeyItem(BaseModel):
    question_id: str
    sequence_order: int
    marks: int
    model_answer: str = Field(..., description="Concise, faculty-usable model solution")
    key_points: List[str] = Field(default_factory=list, description="Core keywords and bullet concepts")
    expected_steps: List[str] = Field(default_factory=list, description="Sequential steps for problem solving/code")
    marking_scheme: str = Field(..., description="Mark breakdown (e.g. 2 marks for diagram, 3 marks for derivation)")


class AnswerKeyResponseSchema(BaseModel):
    answers: List[AnswerKeyItem] = Field(default_factory=list)


class AnswerKeyResponse(BaseModel):
    id: UUID
    exam_paper_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    answers: List[Dict[str, Any]] = []
    status: str
    version: int
    approved_by: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
