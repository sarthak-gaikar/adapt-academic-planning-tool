"""
ADAPT — Document Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, AliasChoices


class DocumentResponse(BaseModel):
    id: UUID
    subject_id: UUID
    uploaded_by: UUID
    filename: str
    file_type: str
    document_type: str
    file_size: Optional[int] = None
    processing_status: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    task_id: Optional[str] = None
    message: str = "Document uploaded successfully"
