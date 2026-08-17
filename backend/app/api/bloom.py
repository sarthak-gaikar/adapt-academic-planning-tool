"""
ADAPT — Bloom's Taxonomy Classifier API

POST /api/bloom/classify       — Classify single question/text
POST /api/bloom/classify-batch — Batch classify multiple texts
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.bloom_classifier import (
    BloomClassificationResult,
    KeywordBloomClassifier,
    LLMBloomClassifier,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/bloom", tags=["Bloom Taxonomy"])


class BloomClassifyRequest(BaseModel):
    text: str
    model: Optional[str] = "llm"  # "llm" or "baseline"


class BloomBatchClassifyRequest(BaseModel):
    texts: List[str]
    model: Optional[str] = "llm"


@router.post("/classify", response_model=BloomClassificationResult)
async def classify_bloom(
    req: BloomClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Classify a question or learning outcome statement into Bloom's Taxonomy."""
    if req.model == "baseline":
        classifier = KeywordBloomClassifier()
    else:
        classifier = LLMBloomClassifier()

    return await classifier.classify(req.text)


@router.post("/classify-batch", response_model=List[BloomClassificationResult])
async def classify_bloom_batch(
    req: BloomBatchClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Classify a batch of questions or statements."""
    if req.model == "baseline":
        classifier = KeywordBloomClassifier()
    else:
        classifier = LLMBloomClassifier()

    results = []
    for t in req.texts:
        res = await classifier.classify(t)
        results.append(res)
    return results
