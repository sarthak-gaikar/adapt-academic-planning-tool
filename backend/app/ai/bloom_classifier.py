"""
ADAPT — Bloom's Taxonomy Classifier Abstraction

Supports multiple classification backends:
1. Rule/Keyword-based (Baseline)
2. LLM-based (Few-shot context)
3. Extensible to TF-IDF / Fine-tuned models for research experimentation
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.ai.factory import get_llm_provider
from app.core.logging import get_logger

logger = get_logger("ai.bloom")


class BloomClassificationResult(BaseModel):
    level: str  # Remember | Understand | Apply | Analyze | Evaluate | Create
    level_number: int  # 1 - 6
    confidence: float  # 0.0 - 1.0
    action_verb: Optional[str] = None
    rationale: Optional[str] = None
    model_used: str


class BloomClassifier(ABC):
    """Abstract classifier interface for Bloom taxonomy levels."""

    @abstractmethod
    async def classify(self, text: str) -> BloomClassificationResult:
        pass


class KeywordBloomClassifier(BloomClassifier):
    """Fast deterministic rule/verb baseline classifier."""

    def __init__(self):
        self.levels_map = self._load_taxonomy()

    def _load_taxonomy(self) -> Dict[str, Dict]:
        path = Path("data/knowledge_base/bloom_taxonomy.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {lvl["name"]: lvl for lvl in data.get("bloom_levels", [])}
        return {}

    async def classify(self, text: str) -> BloomClassificationResult:
        words = text.lower().split()
        first_verb = words[0] if words else ""

        best_level = "Understand"
        best_num = 2
        best_conf = 0.5
        matched_verb = None

        for lvl_name, lvl_data in self.levels_map.items():
            verbs = lvl_data.get("verbs", [])
            for v in verbs:
                if v in words:
                    best_level = lvl_name
                    best_num = lvl_data.get("level", 2)
                    best_conf = 0.85 if words and words[0] == v else 0.70
                    matched_verb = v
                    break

        return BloomClassificationResult(
            level=best_level,
            level_number=best_num,
            confidence=best_conf,
            action_verb=matched_verb,
            rationale=f"Rule match on verb '{matched_verb}'" if matched_verb else "Default fallback",
            model_used="KEYWORD_BASELINE",
        )


class LLMBloomClassifier(BloomClassifier):
    """High-accuracy LLM cognitive level classifier."""

    class LLMClassificationSchema(BaseModel):
        level: str
        level_number: int
        confidence: float
        action_verb: Optional[str] = None
        rationale: str

    async def classify(self, text: str) -> BloomClassificationResult:
        llm = get_llm_provider()
        sys_prompt = (
            "You are a cognitive psychology and Bloom's Taxonomy evaluation expert. "
            "Analyze the given statement or question and classify it into one of the 6 cognitive domains:\n"
            "1. Remember (recall facts)\n"
            "2. Understand (explain ideas/concepts)\n"
            "3. Apply (use information in new situations/calculate/implement)\n"
            "4. Analyze (draw connections/compare/contrast/deconstruct)\n"
            "5. Evaluate (justify/critique/assess decisions)\n"
            "6. Create (produce new or original work/design/architect)\n"
        )
        user_prompt = f"Classify this academic statement/question:\n\n\"{text}\""

        try:
            res = await llm.generate_structured(
                prompt=user_prompt,
                schema=self.LLMClassificationSchema,
                system_prompt=sys_prompt,
                temperature=0.0,
            )
            return BloomClassificationResult(
                level=res.level,
                level_number=res.level_number,
                confidence=res.confidence,
                action_verb=res.action_verb,
                rationale=res.rationale,
                model_used="LLM_GPT4O",
            )
        except Exception as e:
            logger.warning(f"LLM Bloom classification failed ({e}), falling back to keyword classifier.")
            return await KeywordBloomClassifier().classify(text)
