"""
ADAPT — Google Gemini LLM Provider

Implements LLMProvider using the official Google GenAI SDK (google-genai / google-generativeai).
Supports structured JSON output matching Pydantic schemas and schema validation repair.
"""

import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.ai.llm_provider import LLMProvider, LLMResponse
from app.config import get_settings
from app.core.exceptions import LLMError, LLMOutputError
from app.core.logging import get_logger

logger = get_logger("ai.gemini")
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Google Gemini model provider with native structured output support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self.default_temperature = temperature if temperature is not None else settings.gemini_temperature
        self.default_max_tokens = max_tokens or settings.gemini_max_tokens

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini API calls will fail without an API key.")
        else:
            genai.configure(api_key=self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        start_time = time.time()
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt or "You are an expert academic curriculum and assessment specialist.",
                generation_config=genai.GenerationConfig(
                    temperature=temperature if temperature is not None else self.default_temperature,
                    max_output_tokens=max_tokens or self.default_max_tokens,
                ),
            )

            # google-generativeai async call
            response = await model.generate_content_async(prompt)
            latency = time.time() - start_time
            content = response.text or ""

            return LLMResponse(
                content=content,
                model=self.model_name,
                latency_seconds=latency,
            )

        except Exception as e:
            logger.error(f"Gemini generate_text failed: {e}")
            raise LLMError(f"Gemini text generation failed: {str(e)}")

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generates structured JSON adhering strictly to a Pydantic schema using Gemini JSON mode.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        sys_instruction = (
            f"{system_prompt or 'You are an expert academic curriculum and assessment specialist.'}\n\n"
            f"CRITICAL REQUIREMENT: You MUST return ONLY valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any conversational preamble, explanation, or unescaped markdown."
        )

        start_time = time.time()
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=sys_instruction,
                generation_config=genai.GenerationConfig(
                    temperature=temperature if temperature is not None else 0.2,
                    response_mime_type="application/json",
                ),
            )

            response = await model.generate_content_async(prompt)
            raw_text = response.text or "{}"

            try:
                data = json.loads(raw_text)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(f"Initial Gemini JSON validation failed: {parse_err}. Attempting 1 repair retry...")
                # Single repair attempt
                repair_prompt = (
                    f"The previous output failed validation:\n{raw_text}\n\n"
                    f"Validation error:\n{str(parse_err)}\n\n"
                    f"Fix the JSON so it strictly matches this schema:\n{schema_json}"
                )
                repair_resp = await model.generate_content_async(repair_prompt)
                repaired_text = repair_resp.text or "{}"
                repaired_data = json.loads(repaired_text)
                return schema.model_validate(repaired_data)

        except Exception as e:
            logger.error(f"Gemini structured generation failed for {schema.__name__}: {e}")
            raise LLMOutputError(f"Failed to generate structured data with Gemini: {str(e)}")
