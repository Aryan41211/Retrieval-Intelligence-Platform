"""Compatibility wrapper for EmbeddingFactory (Phase 3)."""

from backend.data.embeddings.embedding_factory import (  # noqa: F401
    EmbeddingFactory,
    EmbeddingProviderType,
)

__all__ = ["EmbeddingFactory", "EmbeddingProviderType"]
