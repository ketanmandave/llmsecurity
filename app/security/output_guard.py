"""Sensitive-data redaction for generated responses."""

from app.security.input_guard import GuardResult, redact_sensitive_text


def inspect_model_output(text: str) -> GuardResult:
    """Redact PII and credential patterns before returning model text."""

    return redact_sensitive_text(text)
