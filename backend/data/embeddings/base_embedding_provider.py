"""Base embedding provider interface."""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import Any

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import (
    Embedding,
    EmbeddingBatchResult,
    EmbeddingModelInfo,
    EmbeddingResult,
)


class EmbeddingError(Exception):
    """Base exception for embedding-related errors."""

    code: str = "EMBEDDING_ERROR"
    details: dict[str, Any] | None = None

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details


class ModelNotFoundError(EmbeddingError):
    """Embedding model not found or unavailable."""

    code = "MODEL_NOT_FOUND"


class EmbeddingDimensionError(EmbeddingError):
    """Embedding dimension mismatch or invalid."""

    code = "EMBEDDING_DIMENSION_ERROR"


class EmbeddingValidationError(EmbeddingError):
    """Embedding validation failed."""

    code = "EMBEDDING_VALIDATION_ERROR"


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._model_info: EmbeddingModelInfo | None = None

    @property
    @abstractmethod
    def model_info(self) -> EmbeddingModelInfo:
        return self._model_info

    @property
    @abstractmethod
    def name(self) -> str:
        return self._model_info.name if self._model_info else "unknown"

    @property
    @abstractmethod
    def dimension(self) -> int:
        return self._model_info.dimension if self._model_info else 0

    @abstractmethod
    def embed_text(self, text: str) -> Embedding:
        if not text or not text.strip():
            raise EmbeddingValidationError("Cannot embed empty text")
        ...

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[Embedding]: ...

    @abstractmethod
    def embed_chunks(self, chunks: list[Chunk]) -> EmbeddingBatchResult: ...

    def get_device(self) -> str:
        return self.config.get("device", "cpu")

    def get_batch_size(self) -> int:
        return self.config.get("batch_size", 32)

    def validate_embedding_vector(self, vector: list[float]) -> None:
        if not vector:
            raise EmbeddingValidationError("Embedding vector cannot be empty")
        if any(not isinstance(v, int | float) for v in vector):
            raise EmbeddingValidationError("Embedding vector must contain only numeric values")

        if any(math.isnan(v) or math.isinf(v) for v in vector):
            raise EmbeddingValidationError("Embedding vector contains NaN or Inf values")

    def normalize_vector(self, vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0:
            return vector
        return [v / magnitude for v in vector]

    def _compute_cache_key(self, text: str) -> str:
        return hashlib.sha256(
            f"{self.name}:{self._model_info.version if self._model_info else 'unknown'}:{text}".encode()
        ).hexdigest()

    def _attach_embedding_to_chunk(self, chunk: Chunk, embedding: Embedding) -> EmbeddingResult:
        return EmbeddingResult(chunk=chunk, embedding=embedding)

    def _create_embedding(
        self,
        chunk: Chunk,
        vector: list[float],
        processing_time_ms: float,
    ) -> Embedding:
        checksum = hashlib.sha256("".join(str(v) for v in vector).encode()).hexdigest()
        return Embedding(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            model_name=self.name,
            model_version=self._model_info.version if self._model_info else "unknown",
            embedding_dimension=len(vector),
            embedding_vector=vector,
            processing_time_ms=processing_time_ms,
            checksum=checksum,
            metadata={
                "device": self.get_device(),
                "batch_size": self.get_batch_size(),
            },
        )
