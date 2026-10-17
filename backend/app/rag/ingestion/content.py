"""Normalized native-text content models used during ingestion."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContentType(str, Enum):
    """Kinds of searchable content supported by the text-only pipeline."""

    TEXT = "text"


class SourceType(str, Enum):
    """Extractor provenance stored with every searchable chunk."""

    PYMUPDF = "pymupdf"


class ExtractedContent(BaseModel):
    """Normalized page content passed through scanning and chunking."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)
    content_type: ContentType
    source_type: SourceType
    metadata: dict[str, Any] = Field(default_factory=dict)
