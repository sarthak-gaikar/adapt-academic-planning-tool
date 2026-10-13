"""
ADAPT — AI Factory

Provides singleton access to configured LLM and Embedding providers
(Google Gemini / OpenAI / Groq).
"""

from functools import lru_cache
from typing import Optional

from app.ai.gemini_embeddings import GeminiEmbeddingProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.llm_provider import EmbeddingProvider, LLMProvider
from app.ai.openai_embeddings import OpenAIEmbeddingProvider
from app.ai.openai_provider import OpenAIProvider
from app.config import get_settings


@lru_cache()
def get_llm_provider() -> LLMProvider:
    """Factory method to get the configured LLM provider instance."""
    settings = get_settings()
    provider_name = (settings.llm_provider or "groq").lower()

    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "groq":
        return GroqProvider()

    # Default to Groq
    return GroqProvider()


@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    """Factory method to get the configured Embedding provider instance."""
    settings = get_settings()
    provider_name = (settings.embedding_provider or "gemini").lower()

    if provider_name == "gemini":
        return GeminiEmbeddingProvider()
    elif provider_name == "openai":
        return OpenAIEmbeddingProvider()

    # Default to Gemini
    return GeminiEmbeddingProvider()
