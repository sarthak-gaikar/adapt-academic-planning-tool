"""
ADAPT — LO-PI Mapping Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class LOPIMappingCell(BaseModel):
    lo_code: str
    pi_code: str
    po_code: str
    mapping_level: int = Field(..., ge=0, le=3, description="0=None, 1=Low, 2=Med, 3=High")
    rationale: Optional[str] = None


class LOPIMappingResponseSchema(BaseModel):
    """Structured LLM output for LO-PI mapping generation."""
    mappings: List[LOPIMappingCell] = Field(default_factory=list)


# ---- API Schemas ----

class LOPIMappingItemResponse(BaseModel):
    id: UUID
    lo_id: UUID
    pi_id: UUID
    po_id: UUID
    lo_code: str
    pi_code: str
    po_code: str
    mapping_level: int
    rationale: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class LOPIMatrixResponse(BaseModel):
    subject_id: UUID
    lo_list: List[str] = []
    pi_list: List[str] = []
    po_list: List[str] = []
    matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}  # {LO1.1: {PI1.1: {level: 2, po_code: "PO1", ...}}}


class LOPIMappingUpdate(BaseModel):
    mapping_level: int = Field(..., ge=0, le=3)
    rationale: Optional[str] = None
