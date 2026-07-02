from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Keep filter model provider-agnostic. Filtering is applied after candidate retrieval.


class RetrievalFilters(BaseModel):
    """
    Provider-agnostic metadata filters for semantic retrieval.

    All fields are optional; empty filters should match everything.
    """

    document_ids: list[UUID] | None = None
    source_filenames: list[str] | None = None
    languages: list[str] | None = None

    # Custom key/value filters (exact match)
    # Example: {"custom.department": "finance"} or {"tags": ["finance"]} depending on stored metadata shape.
    custom: dict[str, Any] = Field(default_factory=dict)

    # Temporal range filters (optional)
    created_after: datetime | None = None
    created_before: datetime | None = None

    # Extensibility hook for provider-implemented additional filters.
    # Retriever should not rely on this field; vector store may ignore unknown constraints.
    extra: dict[str, Any] = Field(default_factory=dict)
