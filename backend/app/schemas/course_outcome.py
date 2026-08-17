"""
ADAPT — Course Outcome Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class COItem(BaseModel):
    co_code: str = Field(..., description="CO1, CO2, etc.")
    statement: str = Field(..., description="Measurable action-oriented statement")
    bloom_level: str = Field(..., description="Bloom level name (e.g. Understand, Apply, Analyze)")
    supporting_units: List[int] = Field(default_factory=list, description="Unit numbers covered by this CO")
    rationale: Optional[str] = Field(None, description="Pedagogical rationale for this CO")


class COGenerationRequest(BaseModel):
    num_cos: Optional[int] = Field(None, description="Desired number of COs (typically 4-6)")
    guidelines: Optional[str] = Field(None, description="Optional custom faculty guidelines")


class COGenerationResponseSchema(BaseModel):
    """LLM Structured output schema for CO generation."""
    course_outcomes: List[COItem] = Field(default_factory=list)


# ---- Response Schemas ----

class CourseOutcomeResponse(BaseModel):
    id: UUID
    subject_id: UUID
    generation_run_id: Optional[UUID] = None
    co_code: str
    statement: str
    bloom_level: Optional[str] = None
    bloom_confidence: Optional[float] = None
    bloom_model_used: Optional[str] = None
    supporting_units: List[int] = []
    rationale: Optional[str] = None
    status: str
    version: int
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CourseOutcomeUpdate(BaseModel):
    statement: Optional[str] = None
    bloom_level: Optional[str] = None
    supporting_units: Optional[List[int]] = None
    rationale: Optional[str] = None
