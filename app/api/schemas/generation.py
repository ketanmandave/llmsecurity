"""Grounded RAG answer API schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RAGQueryRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"question": "What is the employee leave policy?", "top_k": 5}]
        }
    )

    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)
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


class CitationResponse(BaseModel):
    source_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None


class RAGQueryResponse(BaseModel):
    request_id: uuid.UUID
    answer: str
    grounded: bool
    sources: list[CitationResponse]
    model: str
