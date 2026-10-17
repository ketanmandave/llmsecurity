"""Groq-backed, schema-constrained answer generation."""

import json
from dataclasses import dataclass
from functools import lru_cache

from groq import AsyncGroq
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.rag.config import Settings, get_settings


class LLMConfigurationError(RuntimeError):
    """Raised when the Groq integration is not configured."""


class LLMGenerationError(RuntimeError):
    """Raised when Groq cannot return a valid answer contract."""


class ModelAnswer(BaseModel):
    """Strict JSON structure that Groq must return before it is trusted."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=8000)
    citations: list[str] = Field(max_length=20)
    grounded: bool


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    """Validated model output passed from the LLM adapter to query orchestration."""

    answer: str
    citations: list[str]
    grounded: bool


def parse_model_answer(content: str) -> GeneratedAnswer:
    """Parse Groq JSON and reject output that violates the answer contract."""

    try:
        parsed = ModelAnswer.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMGenerationError("Groq returned an invalid answer structure") from exc
    return GeneratedAnswer(
        answer=parsed.answer.strip(),
        citations=parsed.citations,
        grounded=parsed.grounded,
    )


class GroqLLMService:
    """Lazy asynchronous client for schema-constrained Groq generation."""

    def __init__(self, settings: Settings) -> None:
        """Copy non-secret generation settings and defer client construction."""

        self.api_key = (
            settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
        )
        self.model = settings.groq_model
        self.max_completion_tokens = settings.groq_max_completion_tokens
        self.timeout_seconds = settings.groq_timeout_seconds
        self.client: AsyncGroq | None = None

    async def generate(self, messages: list[dict[str, str]]) -> GeneratedAnswer:
        """Send grounded messages to Groq and return validated structured output."""

        if not self.api_key:
            raise LLMConfigurationError("GROQ_API_KEY is not configured")
        if self.client is None:
            self.client = AsyncGroq(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
                max_retries=2,
            )
        schema = ModelAnswer.model_json_schema()
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self.max_completion_tokens,
                reasoning_effort="low",
                reasoning_format="hidden",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "grounded_rag_answer",
                        "strict": True,
                        "schema": schema,
                    },
                },
            )
        except Exception as exc:
            raise LLMGenerationError("Groq generation request failed") from exc

        content = completion.choices[0].message.content
        if not content:
            raise LLMGenerationError("Groq returned an empty answer")
        return parse_model_answer(content)


@lru_cache
def get_llm_service() -> GroqLLMService:
    """Return the process-wide cached Groq service configured from the environment."""

    return GroqLLMService(get_settings())
