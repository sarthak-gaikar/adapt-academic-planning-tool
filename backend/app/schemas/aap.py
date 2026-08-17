"""
ADAPT — AAP Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AAPRowSchema(BaseModel):
    week_number: int = Field(..., ge=1, description="Academic week index (1 to 16)")
    unit_number: int = Field(..., ge=1, description="Unit number covered")
    topics_covered: List[str] = Field(default_factory=list, description="Specific topics/subtopics planned")
    teaching_method: str = Field(..., description="Chalk & Board, Interactive PPT, Lab Demonstration, Case Study, etc.")
    co_mapped: str = Field(..., description="Target CO (e.g. CO1, CO2)")
    planned_hours: int = Field(..., ge=1, le=10, description="Contact/lecture hours for this week")
    activity_type: str = Field("Lecture", description="Lecture | Tutorial | Quiz | Lab Session | Discussion")


class AAPPlanDataSchema(BaseModel):
    """Structured LLM output for Academic Activity Plan."""
    total_weeks: int = Field(..., description="Total planned teaching weeks (typically 14-16)")
    total_hours: int = Field(..., description="Total sum of planned hours")
    weeks: List[AAPRowSchema] = Field(default_factory=list)


class AAPGenerationRequest(BaseModel):
    total_weeks: Optional[int] = Field(15, description="Number of instructional weeks in semester")
    hours_per_week: Optional[int] = Field(3, description="Standard lecture hours per week")
    template_config: Optional[Dict[str, Any]] = None


# ---- API Responses ----

class AAPPlanResponse(BaseModel):
    id: UUID
    subject_id: UUID
    generation_run_id: Optional[UUID] = None
    template_config: Dict[str, Any] = {}
    plan_data: Optional[AAPPlanDataSchema] = None
    total_weeks: Optional[int] = None
    total_hours: Optional[int] = None
    status: str
    version: int
    validation_report: Dict[str, Any] = {}
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AAPPlanUpdateRequest(BaseModel):
    plan_data: AAPPlanDataSchema
