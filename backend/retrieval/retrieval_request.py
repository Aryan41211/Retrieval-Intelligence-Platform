from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.retrieval.retrieval_filters import RetrievalFilters


class RetrievalRequest(BaseModel):
    """
    Semantic retrieval request.

    This is provider-agnostic and intended to be consumed by the vector store abstraction
    (for searching over embedded query vectors) and by retrieval engines.
    """

    query_vector: list[float]

    top_k: int = Field(default=10, ge=1, le=1000)

    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)

    filters: RetrievalFilters | None = None

    # Optional filter dimensions (kept explicit for ease of use by callers)
    document_ids: list[UUID] | None = None
    source_filenames: list[str] | None = None
    languages: list[str] | None = None

    # Extensibility: provider-agnostic extra params
    extra: dict[str, Any] = Field(default_factory=dict)

    correlation_id: str | None = None

    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
