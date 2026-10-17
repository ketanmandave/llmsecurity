"""Page-aware overlapping document chunking."""

import hashlib
from dataclasses import dataclass
from typing import Any

from app.rag.ingestion.content import ContentType, ExtractedContent, SourceType
from app.rag.ingestion.parser import ExtractedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Deterministic searchable unit with page, hash, and provenance metadata."""

    page_number: int
    chunk_index: int
    content: str
    content_hash: str
    content_type: str = ContentType.TEXT.value
    source_type: str = SourceType.PYMUPDF.value
    token_count: int = 0
    metadata: dict[str, Any] | None = None


def chunk_contents(
    contents: list[ExtractedContent],
    chunk_size_words: int,
    overlap_words: int,
) -> list[TextChunk]:
    """Chunk normalized content while preserving source and extraction metadata."""

    if chunk_size_words < 1:
        raise ValueError("chunk_size_words must be positive")
    if overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be between 0 and chunk_size_words - 1")

    chunks: list[TextChunk] = []
    step = chunk_size_words - overlap_words
    chunk_index = 0
    for item in contents:
        words = item.content.split()
        starts = range(0, len(words), step)
        for start in starts:
            content = " ".join(words[start : start + chunk_size_words]).strip()
            if not content:
                continue
            chunks.append(
                TextChunk(
                    page_number=item.page_number,
                    chunk_index=chunk_index,
                    content=content,
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    content_type=item.content_type.value,
                    source_type=item.source_type.value,
                    token_count=len(content.split()),
                    metadata=dict(item.metadata),
                )
            )
            chunk_index += 1
            if start + chunk_size_words >= len(words):
                break
    return chunks


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size_words: int,
    overlap_words: int,
) -> list[TextChunk]:
    """Split each page into deterministic overlapping word windows."""

    return chunk_contents(
        [
            ExtractedContent(
                page_number=page.page_number,
                content=page.text,
                content_type=ContentType.TEXT,
                source_type=SourceType.PYMUPDF,
            )
            for page in pages
        ],
        chunk_size_words,
        overlap_words,
    )
