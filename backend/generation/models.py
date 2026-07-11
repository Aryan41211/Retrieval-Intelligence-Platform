from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation mapping answer markers to retrieval chunks."""

    doc_index: int = Field(
        ge=1, description="1-based doc index used in prompt markers like [doc_1]."
    )
    chunk_id: str | None = None
    document_id: str | None = None
    chunk_text: str | None = None

    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    page_number: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerationMetadata(BaseModel):
    prompt_latency_ms: int = 0
    llm_latency_ms: int = 0
    total_latency_ms: int = 0

    provider: str | None = None
    model: str | None = None

    token_estimate_prompt: int | None = None
    token_estimate_completion: int | None = None

    citations_generated: int = 0
    groundedness_score: float | None = None

    extra: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """Grounded answer plus citations and validation metadata."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    incomplete: bool = False

    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)

    generation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextItem(BaseModel):
    """A single context chunk prepared for prompt rendering."""

    chunk_id: str
    document_id: str
    chunk_text: str

    rank: int
    similarity_score: float = Field(ge=0.0)

    source_filename: str | None = None
    page_number: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
