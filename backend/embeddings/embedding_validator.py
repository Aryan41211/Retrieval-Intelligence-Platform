"""Compatibility wrapper for EmbeddingValidator (Phase 3)."""

from backend.data.embeddings.embedding_validator import (  # noqa: F401
    EmbeddingValidator,
)

from backend.data.embeddings.base_embedding_provider import (  # noqa: F401
    EmbeddingDimensionError,
    EmbeddingValidationError,
)

__all__ = ["EmbeddingValidator", "EmbeddingDimensionError", "EmbeddingValidationError"]
