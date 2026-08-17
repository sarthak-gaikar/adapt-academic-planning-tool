"""
ADAPT — Duplicate & Similarity Detector

Uses cosine similarity on embeddings (>0.85 threshold) and string fuzzy checks
to prevent duplicate questions in question banks and exam papers.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.ai.factory import get_embedding_provider
from app.core.logging import get_logger

logger = get_logger("validators.duplicate_detector")


class DuplicateDetectionResult:
    def __init__(self, is_duplicate: bool, similarity_score: float, matched_question: Optional[str] = None):
        self.is_duplicate = is_duplicate
        self.similarity_score = similarity_score
        self.matched_question = matched_question


class DuplicateDetector:
    """Detects semantically identical or near-identical questions."""

    SIMILARITY_THRESHOLD = 0.85

    @staticmethod
    async def check_duplicates_against_bank(
        candidate_question: str,
        existing_questions: List[str],
    ) -> DuplicateDetectionResult:
        if not existing_questions:
            return DuplicateDetectionResult(is_duplicate=False, similarity_score=0.0)

        # 1. Exact string normalization check
        cand_norm = candidate_question.lower().strip()
        for eq in existing_questions:
            if cand_norm == eq.lower().strip():
                return DuplicateDetectionResult(is_duplicate=True, similarity_score=1.0, matched_question=eq)

        # 2. Embedding cosine similarity check
        try:
            embed_provider = get_embedding_provider()
            cand_emb = await embed_provider.embed_text(candidate_question)
            bank_embs = await embed_provider.embed_batch(existing_questions)

            cand_vec = np.array(cand_emb)
            cand_norm_val = np.linalg.norm(cand_vec)
            if cand_norm_val == 0:
                return DuplicateDetectionResult(is_duplicate=False, similarity_score=0.0)

            max_sim = 0.0
            best_match = None

            for eq, b_emb in zip(existing_questions, bank_embs):
                b_vec = np.array(b_emb)
                b_norm = np.linalg.norm(b_vec)
                if b_norm == 0:
                    continue
                cos_sim = float(np.dot(cand_vec, b_vec) / (cand_norm_val * b_norm))
                if cos_sim > max_sim:
                    max_sim = cos_sim
                    best_match = eq

            is_dup = max_sim >= DuplicateDetector.SIMILARITY_THRESHOLD
            return DuplicateDetectionResult(
                is_duplicate=is_dup,
                similarity_score=round(max_sim, 4),
                matched_question=best_match if is_dup else None,
            )

        except Exception as e:
            logger.warning(f"Embedding duplicate check failed ({e}), relying on exact match.")
            return DuplicateDetectionResult(is_duplicate=False, similarity_score=0.0)
