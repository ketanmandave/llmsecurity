"""Deterministic first-pass scanning for PII and document prompt injection."""

import hashlib
import re
from dataclasses import dataclass

from app.ingestion.parser import ExtractedPage
from app.models.enums import Severity


@dataclass(frozen=True, slots=True)
class ScanFinding:
    category: str
    severity: Severity
    confidence: float
    evidence_hash: str
    description: str
    page_number: int


@dataclass(frozen=True, slots=True)
class ScanResult:
    sanitized_pages: list[ExtractedPage]
    findings: list[ScanFinding]
    should_quarantine: bool


PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "email",
        re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w-])", re.I),
        "[EMAIL_REDACTED]",
    ),
    (
        "phone",
        re.compile(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)(?!\w)"),
        "[PHONE_REDACTED]",
    ),
    (
        "payment_card",
        re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)"),
        "[PAYMENT_CARD_REDACTED]",
    ),
)

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|system)\s+instructions?\b", re.I),
    re.compile(r"\breveal\s+(?:the\s+)?(?:system\s+prompt|hidden\s+instructions?|secrets?)\b", re.I),
    re.compile(r"\b(?:override|bypass)\s+(?:the\s+)?(?:security|policy|permissions?|rules?)\b", re.I),
    re.compile(r"\bdo\s+not\s+follow\s+(?:the\s+)?(?:system|developer|previous)\s+instructions?\b", re.I),
)


def _evidence_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan_and_redact_pages(pages: list[ExtractedPage]) -> ScanResult:
    """Redact common PII and flag strong indirect-prompt-injection signals."""

    findings: list[ScanFinding] = []
    sanitized_pages: list[ExtractedPage] = []
    injection_matches = 0

    for page in pages:
        sanitized = page.text
        for entity_type, pattern, replacement in PII_PATTERNS:
            matches = list(pattern.finditer(sanitized))
            for match in matches:
                findings.append(
                    ScanFinding(
                        category=f"pii_{entity_type}",
                        severity=Severity.MEDIUM,
                        confidence=0.85,
                        evidence_hash=_evidence_hash(match.group(0)),
                        description=f"Potential {entity_type} value was redacted",
                        page_number=page.page_number,
                    )
                )
            sanitized = pattern.sub(replacement, sanitized)

        for pattern in INJECTION_PATTERNS:
            for match in pattern.finditer(sanitized):
                injection_matches += 1
                findings.append(
                    ScanFinding(
                        category="prompt_injection",
                        severity=Severity.HIGH,
                        confidence=0.9,
                        evidence_hash=_evidence_hash(match.group(0)),
                        description="Document contains an instruction-like injection pattern",
                        page_number=page.page_number,
                    )
                )

        sanitized_pages.append(ExtractedPage(page_number=page.page_number, text=sanitized))

    return ScanResult(
        sanitized_pages=sanitized_pages,
        findings=findings,
        should_quarantine=injection_matches > 0,
    )
