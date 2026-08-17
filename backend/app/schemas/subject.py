"""
ADAPT — Subject Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---- Request Schemas ----

class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    course_code: str = Field(..., min_length=1, max_length=50)
    credits: Optional[int] = None
    teaching_hours: Optional[int] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[List[str]] = []
    course_objectives: Optional[List[str]] = []


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    course_code: Optional[str] = None
    credits: Optional[int] = None
    teaching_hours: Optional[int] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    course_objectives: Optional[List[str]] = None
    status: Optional[str] = None


# ---- Response Schemas ----

class SubjectResponse(BaseModel):
    id: UUID
    created_by: UUID
    name: str
    course_code: str
    credits: Optional[int] = None
    teaching_hours: Optional[int] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[List[str]] = []
    course_objectives: Optional[List[str]] = []
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubjectDetailResponse(SubjectResponse):
    """Extended response with stats for the subject detail page."""
    syllabus_status: Optional[str] = None
    co_count: int = 0
    question_count: int = 0
    assignment_count: int = 0
    exam_count: int = 0
