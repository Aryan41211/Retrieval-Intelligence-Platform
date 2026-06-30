"""Compatibility wrapper for EmbeddingBatchProcessor (Phase 3)."""

from backend.data.embeddings.embedding_batch_processor import (  # noqa: F401
    BatchProcessingConfig,
    EmbeddingBatchProcessor,
)

__all__ = ["EmbeddingBatchProcessor", "BatchProcessingConfig"]
