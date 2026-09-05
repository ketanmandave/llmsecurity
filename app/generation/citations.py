"""Citation validation and public source construction."""

import uuid
from dataclasses import dataclass

from app.generation.llm import GeneratedAnswer, LLMGenerationError
from app.retrieval.retriever import RetrievedChunk


@dataclass(frozen=True, slots=True)
class Citation:
    source_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None


def validate_and_build_citations(
    answer: GeneratedAnswer,
    source_map: dict[str, RetrievedChunk],
) -> list[Citation]:
    """Reject hallucinated citations and map valid IDs to authorized sources."""

    unique_ids = list(dict.fromkeys(answer.citations))
    invalid_ids = [source_id for source_id in unique_ids if source_id not in source_map]
    if invalid_ids:
        raise LLMGenerationError("Groq cited a source that was not supplied")
    if answer.grounded and not unique_ids:
        raise LLMGenerationError("Grounded answer did not contain any citations")

    return [
        Citation(
            source_id=source_id,
            chunk_id=source_map[source_id].chunk_id,
            document_id=source_map[source_id].document_id,
            document_name=source_map[source_id].document_name,
            page_number=source_map[source_id].page_number,
        )
        for source_id in unique_ids
    ]
