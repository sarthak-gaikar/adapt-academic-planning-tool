"""
ADAPT — OpenAI LLM Provider

Implements LLMProvider using the official OpenAI async client.
Supports structured JSON parsing with Pydantic and fallback error repair.
"""

import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.ai.llm_provider import LLMProvider, LLMResponse
from app.config import get_settings
from app.core.exceptions import LLMError, LLMOutputError
from app.core.logging import get_logger

logger = get_logger("ai.openai")
T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """OpenAI API integration for text and structured generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.default_temperature = temperature or settings.openai_temperature
        self.default_max_tokens = max_tokens or settings.openai_max_tokens

        if not self.api_key:
            logger.warning("OPENAI_API_KEY is not set. OpenAI calls will fail without API key.")

        self.client = AsyncOpenAI(api_key=self.api_key or "mock-key")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens,
            )
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
        except Exception as e:
            logger.error(f"OpenAI generate_text error: {e}")
            raise LLMError(f"OpenAI text generation failed: {str(e)}")

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generates structured output adhering to the Pydantic schema.
        Uses JSON response format with schema specification in system instructions.
        """
        sys_msg = (
            system_prompt or "You are an expert academic curriculum and assessment specialist."
        )
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"{sys_msg}\n\n"
            f"CRITICAL: You MUST respond ONLY with valid JSON matching this exact JSON Schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any conversational preamble, explanation, or markdown backticks around the json unless valid."
        )

        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ]

        start_time = time.time()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.2,
                response_format={"type": "json_object"},
            )
            raw_text = response.choices[0].message.content or "{}"
            
            try:
                data = json.loads(raw_text)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(f"Initial schema validation failed: {parse_err}. Attempting 1 repair retry...")
                # Single repair attempt
                repair_prompt = (
                    f"The previous output failed validation:\n{raw_text}\n\n"
                    f"Validation error:\n{str(parse_err)}\n\n"
                    f"Fix the JSON so it strictly matches schema:\n{schema_json}"
                )
                repair_resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": repair_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                repaired_text = repair_resp.choices[0].message.content or "{}"
                repaired_data = json.loads(repaired_text)
                return schema.model_validate(repaired_data)

        except Exception as e:
            logger.error(f"OpenAI structured generation failed: {e}")
            raise LLMOutputError(f"Failed to generate structured data for {schema.__name__}: {str(e)}")
