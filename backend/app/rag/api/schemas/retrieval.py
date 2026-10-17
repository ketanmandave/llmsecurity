"""Authorized-retrieval API schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RetrievalRequest(BaseModel):
    """Question and optional document scope for retrieval without generation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"question": "What is polymorphism?", "top_k": 5}]
        }
    )

    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_ids: list[uuid.UUID] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description=(
            "Optional scope using real IDs supplied by your backend; omit this field "
            "to search all role-authorized documents"
        ),
    )


class RetrievedChunkResponse(BaseModel):
    """Authorized source chunk with provenance and relevance diagnostics."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None
    content: str
    content_type: str
    source_type: str
    metadata: dict
    score: float
    vector_score: float
    lexical_score: float
    title_score: float
    reranker_score: float | None


class RetrievalResponse(BaseModel):
    """Request identifier and ranked chunks returned by the retrieval API."""

    request_id: uuid.UUID
    results: list[RetrievedChunkResponse]
