"""
ADAPT — Google Gemini Embedding Provider

Implements EmbeddingProvider using Gemini's text-embedding-004 model.
"""

from typing import List, Optional
import google.generativeai as genai

from app.ai.llm_provider import EmbeddingProvider
from app.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger("ai.gemini_embedding")


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings using Google Gemini text-embedding-004."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_embedding_model
        self._dimension = dimension or settings.embedding_dimension

        if self.api_key:
            genai.configure(api_key=self.api_key)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        try:
            cleaned = text.replace("\n", " ").strip()[:9000]
            if not cleaned:
                return [0.0] * self._dimension

            result = genai.embed_content(
                model=f"models/{self.model_name}" if not self.model_name.startswith("models/") else self.model_name,
                content=cleaned,
                task_type="retrieval_document",
            )
            embedding = result.get("embedding", [])
            return embedding
        except Exception as e:
            logger.error(f"Gemini embed_text error: {e}")
            raise EmbeddingError(f"Gemini embedding generation failed: {str(e)}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            cleaned_texts = [t.replace("\n", " ").strip()[:9000] or " " for t in texts]
            # Gemini embed_content supports list of contents
            result = genai.embed_content(
                model=f"models/{self.model_name}" if not self.model_name.startswith("models/") else self.model_name,
                content=cleaned_texts,
                task_type="retrieval_document",
            )
            embeddings = result.get("embedding", [])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini batch embedding error: {e}")
            raise EmbeddingError(f"Gemini batch embedding generation failed: {str(e)}")
