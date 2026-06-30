"""Compatibility wrapper for embedding metadata utilities (Phase 3)."""

from backend.data.embeddings.embedding_metadata import (  # noqa: F401
    EmbeddingMetadataBuilder,
    create_embedding_metadata,
    ModelRegistry,
)

__all__ = ["EmbeddingMetadataBuilder", "create_embedding_metadata", "ModelRegistry"]
