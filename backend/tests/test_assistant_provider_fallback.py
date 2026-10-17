from typing import Any

import app.services.openai_service as provider_module
from app.core.config import settings
from app.services.openai_service import OpenAIService


class FakeResponse:
    status_code = 200
    is_error = False

    @staticmethod
    def json() -> dict[str, Any]:
        return {"choices": [{"message": {"content": "Groq assistant response"}}]}


class FakeClient:
    def __init__(self, capture: dict[str, Any], **_: Any) -> None:
        self.capture = capture

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.capture["url"] = url
        self.capture.update(kwargs)
        return FakeResponse()


def test_assistant_uses_groq_when_openai_key_is_absent(monkeypatch) -> None:
    capture: dict[str, Any] = {}
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", "test-groq-key")
    monkeypatch.setattr(
        provider_module.httpx,
        "Client",
        lambda **kwargs: FakeClient(capture, **kwargs),
    )

    response = OpenAIService().chat([{"role": "user", "content": "Hello"}])

    assert response == "Groq assistant response"
    assert capture["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert capture["json"]["model"] == settings.groq_model
    assert capture["headers"]["Authorization"] == "Bearer test-groq-key"
