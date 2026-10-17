from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CitationOut(BaseModel):
    source_id: str
    chunk_id: UUID
    document_id: UUID
    document_name: str
    page_number: int | None = None
    content_type: str
    source_type: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    mode: Literal["assistant", "rag"] = "assistant"
    citations: list[CitationOut] = Field(default_factory=list)
    request_id: str | None = None
    grounded: bool | None = None
    model: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    mode: Literal["assistant", "rag"] = "assistant"
    document_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_mode_specific_fields(self) -> "ChatMessageRequest":
        """Keep RAG requests within retrieval limits and reject irrelevant scope."""

        if self.mode == "rag" and len(self.content) > 4000:
            raise ValueError("RAG questions cannot exceed 4000 characters")
        if self.mode == "assistant" and self.document_ids is not None:
            raise ValueError("document_ids can be used only in rag mode")
        return self


class ChatMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
