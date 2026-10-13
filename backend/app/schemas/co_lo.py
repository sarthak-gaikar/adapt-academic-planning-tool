"""
ADAPT — CO-LO Mapping Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class COLOMappingCell(BaseModel):
    lo_code: str
    co_code: str
    mapping_strength: int = Field(..., ge=0, le=3, description="0=None, 1=Low, 2=Med, 3=High")
    rationale: Optional[str] = None


class COLOMappingResponseSchema(BaseModel):
    """Structured LLM output for CO-LO mapping generation."""
    mappings: List[COLOMappingCell] = Field(default_factory=list)


# ---- API Schemas ----

class COLOMappingItemResponse(BaseModel):
    id: UUID
    lo_id: UUID
    co_id: UUID
    lo_code: str
    co_code: str
    mapping_strength: int
    rationale: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class COLOMatrixResponse(BaseModel):
    subject_id: UUID
    lo_list: List[str] = []
    co_list: List[str] = []
    matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}  # {LO1.1: {CO1: {strength: 3, rationale: "..."}}


class COLOMappingUpdate(BaseModel):
    mapping_strength: int = Field(..., ge=0, le=3)
    rationale: Optional[str] = None
