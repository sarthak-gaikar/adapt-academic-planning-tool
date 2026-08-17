"""
ADAPT — CO-PO Mapping Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class COPOMappingCell(BaseModel):
    co_code: str
    po_code: str
    suggested_level: int = Field(..., ge=0, le=3, description="0=None, 1=Low, 2=Med, 3=High")
    rationale: Optional[str] = None


class COPOMappingResponseSchema(BaseModel):
    """Structured LLM output for CO-PO matrix generation."""
    mappings: List[COPOMappingCell] = Field(default_factory=list)


# ---- API Schemas ----

class COPOMappingItemResponse(BaseModel):
    id: UUID
    subject_id: UUID
    co_id: UUID
    po_id: UUID
    co_code: str
    po_code: str
    suggested_level: int
    approved_level: Optional[int] = None
    rationale: Optional[str] = None
    status: str
    version: int


class COPOMatrixResponse(BaseModel):
    subject_id: UUID
    co_list: List[str] = []
    po_list: List[str] = []
    matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}  # {CO1: {PO1: {suggested: 3, approved: 3, rationale: "..."}}}


class COPOMappingUpdate(BaseModel):
    approved_level: int = Field(..., ge=0, le=3)
    rationale: Optional[str] = None
