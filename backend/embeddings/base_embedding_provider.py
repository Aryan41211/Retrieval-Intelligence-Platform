"""Compatibility wrapper for embedding provider interfaces (Phase 3)."""

from backend.data.embeddings.base_embedding_provider import (  # noqa: F401
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingDimensionError,
    EmbeddingValidationError,
    ModelNotFoundError,
)

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingError",
    "EmbeddingDimensionError",
    "EmbeddingValidationError",
    "ModelNotFoundError",
]
