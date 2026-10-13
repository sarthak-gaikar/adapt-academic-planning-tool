"""
ADAPT — Groq LLM Provider

Implements LLMProvider using the official Groq Python SDK (OpenAI-compatible).
Supports structured JSON parsing with Pydantic, retry with exponential backoff
for rate-limit (429) and timeout errors, and clear user-facing error messages.

Embeddings are NOT handled here — the existing embedding provider is unchanged.
"""

import asyncio
import json
import time
from typing import Optional, Type, TypeVar

from groq import AsyncGroq, RateLimitError, APITimeoutError, APIStatusError
from pydantic import BaseModel, ValidationError

from app.ai.llm_provider import LLMProvider, LLMResponse
from app.config import get_settings
from app.core.exceptions import LLMError, LLMOutputError
from app.core.logging import get_logger

logger = get_logger("ai.groq")
T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
_MAX_RETRIES = 4          # total attempts (1 initial + 3 retries)
_INITIAL_BACKOFF = 2.0    # seconds before first retry
_BACKOFF_MULTIPLIER = 2.0 # exponential multiplier
_MAX_BACKOFF = 30.0       # cap per sleep


def _backoff(attempt: int) -> float:
    return min(_INITIAL_BACKOFF * (_BACKOFF_MULTIPLIER ** attempt), _MAX_BACKOFF)


class GroqProvider(LLMProvider):
    """Groq API integration using the official Groq Python SDK (OpenAI-compatible)."""

    def __init__(self, api_key=None, model=None, temperature=None, max_tokens=None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.default_temperature = temperature if temperature is not None else settings.groq_temperature
        self.default_max_tokens = max_tokens or settings.groq_max_tokens

        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Groq calls will fail without an API key.")

        self.client = AsyncGroq(api_key=self.api_key or "mock-key")

    async def _call_with_retry(self, call_fn, context="Groq API"):
        for attempt in range(_MAX_RETRIES):
            try:
                return await call_fn()
            except RateLimitError as e:
                wait = _backoff(attempt)
                logger.warning(f"{context}: rate limited (attempt {attempt+1}/{_MAX_RETRIES}). Retrying in {wait:.1f}s")
                if attempt + 1 >= _MAX_RETRIES:
                    raise LLMError(f"Groq rate limit exceeded after {_MAX_RETRIES} attempts. Please wait and try again.") from e
                await asyncio.sleep(wait)
            except APITimeoutError as e:
                wait = _backoff(attempt)
                logger.warning(f"{context}: timed out (attempt {attempt+1}/{_MAX_RETRIES}). Retrying in {wait:.1f}s")
                if attempt + 1 >= _MAX_RETRIES:
                    raise LLMError(f"Groq request timed out after {_MAX_RETRIES} attempts. Please try again later.") from e
                await asyncio.sleep(wait)
            except APIStatusError as e:
                if e.status_code >= 500:
                    wait = _backoff(attempt)
                    logger.warning(f"{context}: server error {e.status_code} (attempt {attempt+1}/{_MAX_RETRIES}). Retrying in {wait:.1f}s")
                    if attempt + 1 >= _MAX_RETRIES:
                        raise LLMError(f"Groq server error {e.status_code}: {str(e)}") from e
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"{context}: API error {e.status_code}: {e}")
                    raise LLMError(f"Groq API error {e.status_code}: {str(e)}") from e
            except Exception as e:
                logger.error(f"{context}: unexpected error: {e}")
                raise LLMError(f"Groq generation failed: {str(e)}") from e
        raise LLMError(f"{context}: exhausted retries.")

    async def generate_text(self, prompt, system_prompt=None, temperature=None, max_tokens=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        start_time = time.time()

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens,
            )

        response = await self._call_with_retry(_call, context="generate_text")
        latency = time.time() - start_time
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=response.model,
            latency_seconds=latency,
        )

    async def generate_structured(self, prompt, schema, system_prompt=None, temperature=None):
        sys_msg = system_prompt or "You are an expert academic curriculum and assessment specialist."
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"{sys_msg}\n\n"
            f"CRITICAL: You MUST respond ONLY with valid JSON matching this exact JSON Schema:\n"
            f"`json\n{schema_json}\n`\n"
            f"Do not include any conversational preamble, explanation, or markdown backticks unless they wrap valid JSON."
        )
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ]

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.2,
                response_format={"type": "json_object"},
            )

        try:
            response = await self._call_with_retry(_call, context=f"generate_structured<{schema.__name__}>")
            raw_text = response.choices[0].message.content or "{}"
            stripped = raw_text.strip()
            if stripped.startswith("`"):
                stripped = stripped.split("`", 2)[1]
                if stripped.startswith("json"):
                    stripped = stripped[4:]
                stripped = stripped.rsplit("`", 1)[0].strip()
            try:
                data = json.loads(stripped)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(f"generate_structured<{schema.__name__}>: parse failed: {parse_err}. Attempting repair retry…")
                repair_prompt = (
                    f"The previous output failed validation:\n{raw_text}\n\n"
                    f"Validation error:\n{str(parse_err)}\n\n"
                    f"Fix the JSON so it strictly matches schema:\n{schema_json}"
                )
                async def _repair():
                    return await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": repair_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                repair_resp = await self._call_with_retry(_repair, context=f"generate_structured<{schema.__name__}> repair")
                repaired_data = json.loads(repair_resp.choices[0].message.content or "{}")
                return schema.model_validate(repaired_data)
        except (LLMError, LLMOutputError):
            raise
        except Exception as e:
            logger.error(f"generate_structured<{schema.__name__}> failed: {e}")
            raise LLMOutputError(f"Failed to generate structured data for {schema.__name__}: {str(e)}")
