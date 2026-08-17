"""
ADAPT — OpenAI Embedding Provider
"""

from typing import List, Optional
from openai import AsyncOpenAI

from app.ai.llm_provider import EmbeddingProvider
from app.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger("ai.embedding")


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings using OpenAI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model
        self._dimension = dimension or settings.embedding_dimension
        self.client = AsyncOpenAI(api_key=self.api_key or "mock-key")

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        try:
            # Truncate text if too long
            cleaned_text = text.replace("\n", " ").strip()[:8000]
            if not cleaned_text:
                return [0.0] * self._dimension

            response = await self.client.embeddings.create(
                input=cleaned_text,
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            cleaned_texts = [t.replace("\n", " ").strip()[:8000] or " " for t in texts]
            response = await self.client.embeddings.create(
                input=cleaned_texts,
                model=self.model,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {str(e)}")
