"""
ADAPT — Program Outcome Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProgramOutcomeResponse(BaseModel):
    id: UUID
    po_code: str
    statement: str
    category: Optional[str] = "PO"
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgramOutcomeCreate(BaseModel):
    po_code: str = Field(..., description="PO1, PO2, PSO1, etc.")
    statement: str = Field(..., description="Program Outcome statement")
    category: Optional[str] = "PO"
