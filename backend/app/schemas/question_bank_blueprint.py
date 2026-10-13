"""
ADAPT — Question Bank Blueprint Pydantic Schemas

User specifies marks × count configurations. System auto-calculates total marks.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class MarkConfig(BaseModel):
    """A single mark-count configuration entry."""
    marks: int = Field(..., ge=1, le=50, description="Marks per question (e.g. 2, 5, 10)")
    count: int = Field(..., ge=1, le=50, description="Number of questions at this mark level")


class QuestionBankBlueprintRequest(BaseModel):
    """Blueprint for generating a structured question bank."""
    units: List[int] = Field(default_factory=list, description="Target unit numbers")
    mark_configs: List[MarkConfig] = Field(..., min_length=1, description="List of marks × count configs")
    cos: List[str] = Field(default_factory=list, description="Target CO codes (optional filter)")
    lo_codes: List[str] = Field(default_factory=list, description="Target LO codes (optional filter)")
    bloom_levels: List[str] = Field(default_factory=list, description="Target Bloom levels (optional filter)")
    difficulty: Optional[str] = Field("MIXED", description="EASY | MEDIUM | HARD | MIXED")
    custom_guidelines: Optional[str] = None
    additional_file_paths: List[str] = Field(
        default_factory=list,
        description="Paths to temporarily uploaded reference files (optional)"
    )

    @property
    def total_marks(self) -> int:
        return sum(mc.marks * mc.count for mc in self.mark_configs)

    @property
    def total_questions(self) -> int:
        return sum(mc.count for mc in self.mark_configs)


class BlueprintPreviewResponse(BaseModel):
    """Preview before generation: shows calculated totals."""
    mark_configs: List[MarkConfig] = []
    total_marks: int = 0
    total_questions: int = 0
    units: List[int] = []
