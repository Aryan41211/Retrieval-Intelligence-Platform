from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RetrievalMetadata(BaseModel):
    """
    Aggregated retrieval metadata for responses.
    """

    query_embedding_model: str | None = None
    query_embedding_dim: int | None = None

    retrieval_latency_ms: int = 0
    vector_search_latency_ms: int | None = None

    total_candidates: int = 0
    retrieved_chunks: int = 0

    similarity_threshold: float | None = None

    methods_used: list[str] = Field(default_factory=list)

    # Debug/analysis: keep top scores
    top_scores: list[float] = Field(default_factory=list)

    # Timestamp for observability
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Extensibility
    extra: dict[str, Any] = Field(default_factory=dict)
