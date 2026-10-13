"""
ADAPT — Learning Outcome Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class LOItem(BaseModel):
    lo_code: str = Field(..., description="LO1.1, LO1.2, LO2.1, etc.")
    unit_number: int = Field(..., description="Unit this LO belongs to")
    statement: str = Field(..., description="Measurable action-oriented LO statement")
    bloom_level: str = Field(..., description="Bloom level: Remember|Understand|Apply|Analyze|Evaluate|Create")
    mapped_cos: List[str] = Field(default_factory=list, description="CO codes this LO maps to (e.g. ['CO1', 'CO2'])")
    rationale: Optional[str] = Field(None, description="Pedagogical rationale")


class LOGenerationRequest(BaseModel):
    unit_numbers: Optional[List[int]] = Field(None, description="Specific units to generate LOs for. None = all units.")
    num_los_per_unit: Optional[int] = Field(None, description="Number of LOs per unit (typically 3-5)")
    guidelines: Optional[str] = Field(None, description="Optional faculty guidelines")


class LOGenerationResponseSchema(BaseModel):
    """LLM Structured output schema for LO generation."""
    learning_outcomes: List[LOItem] = Field(default_factory=list)


# ---- Response Schemas ----

class LearningOutcomeResponse(BaseModel):
    id: UUID
    subject_id: UUID
    unit_id: UUID
    generation_run_id: Optional[UUID] = None
    lo_code: str
    statement: str
    bloom_level: Optional[str] = None
    bloom_order: Optional[int] = None
    bloom_confidence: Optional[float] = None
    rationale: Optional[str] = None
    status: str
    version: int
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Embedded relationships
    unit_number: Optional[int] = None
    unit_title: Optional[str] = None
    mapped_cos: List[str] = []

    model_config = {"from_attributes": True}


class LearningOutcomeUpdate(BaseModel):
    statement: Optional[str] = None
    bloom_level: Optional[str] = None
    rationale: Optional[str] = None


class LOsByUnitResponse(BaseModel):
    unit_number: int
    unit_title: str
    unit_id: UUID
    learning_outcomes: List[LearningOutcomeResponse] = []
