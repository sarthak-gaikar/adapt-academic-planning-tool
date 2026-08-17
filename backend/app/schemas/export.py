"""
ADAPT — Document Export Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentExportRequest(BaseModel):
    source_id: UUID = Field(..., description="ID of ExamPaper, Assignment, AAP, or AnswerKey")
    source_type: str = Field(..., description="EXAM | ASSIGNMENT | AAP | ANSWER_KEY | CO_REPORT")
    format: str = Field("DOCX", description="DOCX | PDF")
    include_co_bloom_tags: bool = True
    include_answer_key: bool = False
    institution_header: Optional[str] = None


class DocumentExportResponse(BaseModel):
    export_id: UUID
    source_id: UUID
    source_type: str
    format: str
    filename: str
    download_url: str
    created_at: datetime
