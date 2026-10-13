"""
ADAPT — Performance Indicator Pydantic Schemas
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PerformanceIndicatorResponse(BaseModel):
    id: UUID
    po_id: UUID
    pi_code: str
    statement: str
    is_active: bool
    created_at: datetime
    # Denormalized for convenience
    po_code: Optional[str] = None

    model_config = {"from_attributes": True}


class PerformanceIndicatorCreate(BaseModel):
    po_code: str = Field(..., description="Parent PO code (e.g. PO1)")
    pi_code: str = Field(..., description="PI code (e.g. PI1.1)")
    statement: str = Field(..., description="Performance Indicator statement")


class PerformanceIndicatorUpdate(BaseModel):
    statement: Optional[str] = None
    is_active: Optional[bool] = None


class PIsGroupedByPOResponse(BaseModel):
    po_code: str
    po_id: UUID
    po_statement: str
    performance_indicators: List[PerformanceIndicatorResponse] = []
