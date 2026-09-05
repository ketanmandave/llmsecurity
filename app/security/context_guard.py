"""Security checks applied again after authorized retrieval."""

from dataclasses import dataclass, replace

from app.ingestion.parser import ExtractedPage
from app.ingestion.scanner import scan_and_redact_pages
from app.retrieval.retriever import RetrievedChunk


@dataclass(frozen=True, slots=True)
class ContextGuardResult:
    chunks: list[RetrievedChunk]
    dropped_chunks: int
    redacted_chunks: int
    findings: tuple[str, ...]


def inspect_retrieved_chunks(chunks: list[RetrievedChunk]) -> ContextGuardResult:
    """Drop injected chunks and re-redact PII before prompt construction."""

    safe_chunks: list[RetrievedChunk] = []
    dropped = 0
    redacted = 0
    findings: list[str] = []

    for chunk in chunks:
        scan = scan_and_redact_pages(
            [ExtractedPage(page_number=chunk.page_number or 1, text=chunk.content)]
        )
        findings.extend(finding.category for finding in scan.findings)
        if scan.should_quarantine:
            dropped += 1
            continue
        sanitized = scan.sanitized_pages[0].text
        if sanitized != chunk.content:
            redacted += 1
        safe_chunks.append(replace(chunk, content=sanitized))

    return ContextGuardResult(
        chunks=safe_chunks,
        dropped_chunks=dropped,
        redacted_chunks=redacted,
        findings=tuple(dict.fromkeys(findings)),
    )
