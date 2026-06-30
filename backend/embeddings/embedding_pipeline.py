"""Compatibility wrapper for EmbeddingPipeline (Phase 3)."""

from backend.data.embeddings.embedding_pipeline import (  # noqa: F401
    EmbeddingPipeline,
    EmbeddingPipelineConfig,
)

__all__ = ["EmbeddingPipeline", "EmbeddingPipelineConfig"]
