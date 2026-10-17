"""Deterministic first-pass scanning for PII and document prompt injection."""

import hashlib
import re
from dataclasses import dataclass

from app.rag.ingestion.content import ContentType, ExtractedContent, SourceType
from app.rag.ingestion.parser import ExtractedPage
from app.rag.models.enums import Severity


@dataclass(frozen=True, slots=True)
class ScanFinding:
    """Privacy-safe detection record containing only a hash of matched evidence."""

    category: str
    severity: Severity
    confidence: float
    evidence_hash: str
    description: str
    page_number: int
    content_type: str = ContentType.TEXT.value
    source_type: str = SourceType.PYMUPDF.value


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Sanitized content, findings, and the final quarantine recommendation."""

    sanitized_contents: list[ExtractedContent]
    findings: list[ScanFinding]
    should_quarantine: bool

    @property
    def sanitized_pages(self) -> list[ExtractedPage]:
        """Adapt normalized scanner output back into page objects for chunking."""

        return [
            ExtractedPage(page_number=item.page_number, text=item.content)
            for item in self.sanitized_contents
        ]


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
    (
        "aadhaar",
        re.compile(r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)"),
        "[AADHAAR_REDACTED]",
    ),
    (
        "pan",
        re.compile(r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])", re.I),
        "[PAN_REDACTED]",
    ),
)

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|system)\s+instructions?\b", re.I),
    re.compile(r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior)\s+(?:authorization|security)\s+rules?\b", re.I),
    re.compile(r"\breveal\s+(?:the\s+)?(?:system\s+prompt|hidden\s+instructions?|secrets?)\b", re.I),
    re.compile(r"\b(?:override|bypass)\s+(?:the\s+)?(?:security|policy|permissions?|rules?)\b", re.I),
    re.compile(r"\bdo\s+not\s+follow\s+(?:the\s+)?(?:system|developer|previous)\s+instructions?\b", re.I),
    re.compile(r"\b(?:act|behave)\s+as\s+(?:an?\s+)?administrator\b", re.I),
    re.compile(r"\breturn\s+(?:all\s+)?(?:database|vector\s+database)\s+contents?\b", re.I),
    re.compile(r"\bforget\s+(?:all\s+)?previous\s+(?:rules?|instructions?)\b", re.I),
)


def _evidence_hash(value: str) -> str:
    """Hash sensitive evidence so raw PII is never written to findings."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan_contents(contents: list[ExtractedContent]) -> ScanResult:
    """Redact PII and scan every normalized representation before embedding."""

    findings: list[ScanFinding] = []
    sanitized_contents: list[ExtractedContent] = []
    injection_matches = 0

    for item in contents:
        sanitized = item.content
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
                        page_number=item.page_number,
                        content_type=item.content_type.value,
                        source_type=item.source_type.value,
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
                        page_number=item.page_number,
                        content_type=item.content_type.value,
                        source_type=item.source_type.value,
                    )
                )

        sanitized_contents.append(item.model_copy(update={"content": sanitized}))

    return ScanResult(
        sanitized_contents=sanitized_contents,
        findings=findings,
        should_quarantine=injection_matches > 0,
    )


def scan_and_redact_pages(pages: list[ExtractedPage]) -> ScanResult:
    """Compatibility adapter for native-text callers."""

    return scan_contents(
        [
            ExtractedContent(
                page_number=page.page_number,
                content=page.text,
                content_type=ContentType.TEXT,
                source_type=SourceType.PYMUPDF,
            )
            for page in pages
        ]
    )
