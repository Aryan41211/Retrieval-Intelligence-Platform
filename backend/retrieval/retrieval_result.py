from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetrievalChunkResult(BaseModel):
    """
    Strongly typed semantic retrieval result for a single matched chunk.
    """

    chunk_id: UUID
    document_id: UUID
    chunk_text: str

    similarity_score: float = Field(ge=0.0)
    rank: int = Field(ge=1)

    source_filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    embedding_model: str | None = None

    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
