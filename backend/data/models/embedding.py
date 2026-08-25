"""Embedding domain model for the Retrieval Intelligence Platform."""

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from pydantic import BaseModel, Field

from backend.data.models.chunk import Chunk


class EmbeddingModelInfo(BaseModel):
    """Information about an embedding model."""

    name: str
    version: str = "1.0.0"
    dimension: int = 0
    max_sequence_length: int = 512
    provider: str = "unknown"

    model_config = {"frozen": True}


class EmbeddingMetadata(BaseModel):
    """Metadata for an embedding."""

    model_name: str
    model_version: str
    embedding_dimension: int
    generation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processing_time_ms: float = 0.0
    checksum: str = ""
    configuration: dict[str, Any] = Field(default_factory=dict)

    model_config = {"protected_namespaces": ()}


class Embedding(BaseModel):
    """Complete embedding entity representing a dense vector representation."""

    embedding_id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID
    document_id: UUID
    model_name: str
    model_version: str
    embedding_dimension: int
    embedding_vector: list[float]
    generation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processing_time_ms: float = 0.0
    checksum: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True, "protected_namespaces": ()}

    def __hash__(self) -> int:
        return hash(self.embedding_id)

    @property
    def vector(self) -> np.ndarray:
        return np.array(self.embedding_vector, dtype=np.float32)

    def compute_checksum(self) -> str:
        content = "".join(str(v) for v in self.embedding_vector)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_numpy(self) -> np.ndarray:
        return np.frombuffer(
            np.array(self.embedding_vector, dtype=np.float32).tobytes(),
            dtype=np.float32,
        )


class EmbeddingResult(BaseModel):
    """Result of embedding generation for a chunk."""

    chunk: Chunk
    embedding: Embedding | None = None
    error: str | None = None
    cache_hit: bool = False


class EmbeddingBatchResult(BaseModel):
    """Result of embedding generation for multiple chunks."""

    results: list[EmbeddingResult]
    total_processing_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def successful_embeddings(self) -> list[Embedding]:
        return [r.embedding for r in self.results if r.embedding is not None]

    @property
    def failed_chunks(self) -> list[Chunk]:
        return [r.chunk for r in self.results if r.error is not None]

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return len(self.successful_embeddings) / len(self.results)
