"""Page-aware overlapping document chunking."""

import hashlib
from dataclasses import dataclass

from app.ingestion.parser import ExtractedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str
    content_hash: str


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size_words: int,
    overlap_words: int,
) -> list[TextChunk]:
    """Split each page into deterministic overlapping word windows."""

    if chunk_size_words < 1:
        raise ValueError("chunk_size_words must be positive")
    if overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be between 0 and chunk_size_words - 1")

    chunks: list[TextChunk] = []
    step = chunk_size_words - overlap_words
    chunk_index = 0

    for page in pages:
        words = page.text.split()
        for start in range(0, len(words), step):
            content = " ".join(words[start : start + chunk_size_words]).strip()
            if not content:
                continue
            chunks.append(
                TextChunk(
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    content=content,
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                )
            )
            chunk_index += 1
            if start + chunk_size_words >= len(words):
                break

    return chunks
