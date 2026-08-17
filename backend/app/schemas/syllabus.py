"""
ADAPT — Structured Syllabus Schemas

Complete Pydantic models for extracted course syllabus representation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TopicSchema(BaseModel):
    name: str = Field(..., description="Name of the topic")
    subtopics: List[str] = Field(default_factory=list, description="List of granular subtopics")


class SyllabusUnitSchema(BaseModel):
    unit_number: int = Field(..., description="Unit number (1, 2, 3...)")
    title: str = Field(..., description="Unit title or theme")
    hours: Optional[int] = Field(None, description="Allocated teaching/lecture hours")
    topics: List[TopicSchema] = Field(default_factory=list, description="Topics within this unit")


class StructuredSyllabusExtraction(BaseModel):
    """Output schema for LLM syllabus analysis."""
    subject_name: str = Field(..., description="Full official course or subject name")
    course_code: Optional[str] = Field(None, description="Course code if mentioned (e.g. CS601, IT302)")
    credits: Optional[int] = Field(None, description="Course credits if specified")
    teaching_hours: Optional[int] = Field(None, description="Total teaching/lecture hours")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite subjects or skills")
    course_objectives: List[str] = Field(default_factory=list, description="Broad course objectives stated in the syllabus")
    units: List[SyllabusUnitSchema] = Field(default_factory=list, description="Units/Modules making up the syllabus")


# ---- Response Schemas ----

class TopicResponse(BaseModel):
    id: UUID
    name: str
    sequence_order: int
    subtopics: List[str] = []

    model_config = {"from_attributes": True}


class SyllabusUnitResponse(BaseModel):
    id: UUID
    unit_number: int
    title: str
    hours: Optional[int] = None
    topics: List[TopicResponse] = []

    model_config = {"from_attributes": True}


class SyllabusResponse(BaseModel):
    id: UUID
    subject_id: UUID
    document_id: Optional[UUID] = None
    version: int
    structured_data: Optional[StructuredSyllabusExtraction] = None
    status: str
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    units: List[SyllabusUnitResponse] = []

    model_config = {"from_attributes": True}


class SyllabusUpdateRequest(BaseModel):
    structured_data: StructuredSyllabusExtraction
