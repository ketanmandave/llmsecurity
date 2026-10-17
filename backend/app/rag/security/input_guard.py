"""Deterministic security inspection before retrieval."""

import re
from dataclasses import dataclass

from app.rag.ingestion.scanner import INJECTION_PATTERNS, PII_PATTERNS
from app.rag.models.enums import PolicyDecision


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "api_key",
        re.compile(r"\b(?:gsk|sk)-[A-Za-z0-9_-]{16,}\b"),
        "[API_KEY_REDACTED]",
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "[AWS_KEY_REDACTED]",
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "[TOKEN_REDACTED]",
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "[PRIVATE_KEY_REDACTED]",
    ),
)


@dataclass(frozen=True, slots=True)
class GuardResult:
    """Sanitized text, detected categories, and resulting security decision."""

    text: str
    decision: PolicyDecision
    findings: tuple[str, ...]


def redact_sensitive_text(text: str) -> GuardResult:
    """Redact common PII and secret patterns without retaining matched values."""

    sanitized = text
    findings: list[str] = []
    for entity_type, pattern, replacement in PII_PATTERNS:
        if pattern.search(sanitized):
            findings.append(f"pii_{entity_type}")
            sanitized = pattern.sub(replacement, sanitized)
    for category, pattern, replacement in SECRET_PATTERNS:
        if pattern.search(sanitized):
            findings.append(category)
            sanitized = pattern.sub(replacement, sanitized)
    return GuardResult(
        text=sanitized,
        decision=PolicyDecision.MODIFY if findings else PolicyDecision.ALLOW,
        findings=tuple(dict.fromkeys(findings)),
    )


def inspect_user_input(text: str) -> GuardResult:
    """Block direct prompt injection and redact sensitive values."""

    injection_findings = [
        "prompt_injection" for pattern in INJECTION_PATTERNS if pattern.search(text)
    ]
    if injection_findings:
        return GuardResult(
            text="",
            decision=PolicyDecision.BLOCK,
            findings=("prompt_injection",),
        )
    return redact_sensitive_text(text)
