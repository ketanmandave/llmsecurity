import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("sentinelai.llm_provider")


class OpenAIServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.status_code = status_code
        super().__init__(message)


class OpenAIService:
    """OpenAI-compatible assistant provider with a Groq fallback.

    The historical class name is retained so existing gateway injection tests
    and integrations remain compatible.
    """

    def chat(self, messages: list[dict[str, str]]) -> str:
        if settings.openai_api_key:
            provider = "openai"
            api_key = settings.openai_api_key
            endpoint = "https://api.openai.com/v1/chat/completions"
            model = settings.openai_model
            timeout_seconds = settings.openai_timeout_seconds
            retry_count = settings.openai_retry_count
            request_body: dict[str, Any] = {"model": model, "messages": messages}
        elif settings.groq_api_key:
            provider = "groq"
            api_key = settings.groq_api_key
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            model = settings.groq_model
            timeout_seconds = settings.groq_timeout_seconds
            retry_count = settings.groq_retry_count
            request_body = {
                "model": model,
                "messages": messages,
                "max_completion_tokens": settings.groq_max_completion_tokens,
            }
        else:
            raise OpenAIServiceError("No assistant LLM provider is configured", 503)

        started = time.perf_counter()
        for attempt in range(retry_count + 1):
            try:
                with httpx.Client(timeout=timeout_seconds) as client:
                    response = client.post(
                        endpoint,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json=request_body,
                    )
                if response.status_code >= 500 and attempt < retry_count:
                    self._log_provider_error(response, attempt, provider)
                    continue
                if response.is_error:
                    self._raise_provider_error(response, attempt, provider)
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Provider returned empty content")
                logger.info("llm_chat_completed provider=%s model=%s latency_ms=%s", provider, model, round((time.perf_counter() - started) * 1000, 2))
                return content
            except httpx.TimeoutException as exc:
                if attempt < retry_count:
                    logger.warning("llm_request_timeout provider=%s attempt=%s exception=%r", provider, attempt + 1, exc)
                    continue
                logger.exception("llm_request_timeout provider=%s attempt=%s exception=%r", provider, attempt + 1, exc)
                raise OpenAIServiceError(f"{provider.title()} request timed out", 504) from exc
            except httpx.HTTPError as exc:
                if attempt < retry_count:
                    logger.warning("llm_transport_error provider=%s attempt=%s exception=%r", provider, attempt + 1, exc)
                    continue
                logger.exception("llm_transport_error provider=%s attempt=%s exception=%r", provider, attempt + 1, exc)
                raise OpenAIServiceError(f"{provider.title()} is unavailable", 502) from exc
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                logger.exception("llm_invalid_response provider=%s exception=%r", provider, exc)
                raise OpenAIServiceError(f"{provider.title()} returned an invalid response", 502) from exc
        raise OpenAIServiceError(f"{provider.title()} is unavailable", 502)

    @staticmethod
    def _provider_error_message(response: httpx.Response) -> str:
        try:
            payload: Any = response.json()
            error = payload.get("error", payload) if isinstance(payload, dict) else payload
            if isinstance(error, dict):
                return str(error.get("message") or error)
            return str(error)
        except ValueError:
            return response.text

    def _log_provider_error(self, response: httpx.Response, attempt: int, provider: str) -> str:
        message = self._provider_error_message(response)
        logger.error(
            "llm_provider_error provider=%s status_code=%s attempt=%s error_message=%r",
            provider,
            response.status_code,
            attempt + 1,
            message,
        )
        return message

    def _raise_provider_error(self, response: httpx.Response, attempt: int, provider: str) -> None:
        self._log_provider_error(response, attempt, provider)
        if response.status_code in {401, 403}:
            raise OpenAIServiceError(f"{provider.title()} authentication failed", 502)
        if response.status_code == 429:
            raise OpenAIServiceError(f"{provider.title()} is rate limited", 429)
        raise OpenAIServiceError(f"{provider.title()} request failed", 502)
