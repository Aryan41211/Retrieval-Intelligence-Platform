"""Embedding pipeline public API (Phase 3).

This package is a compatibility layer that re-exports the current implementation
from `backend.data.embeddings` under the requested `backend.embeddings` path.
"""

from backend.data.embeddings.base_embedding_provider import (
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingDimensionError,
    EmbeddingValidationError,
    ModelNotFoundError,
)
from backend.data.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from backend.data.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingPipelineConfig,
)
from backend.data.embeddings.embedding_cache import EmbeddingCache
from backend.data.embeddings.embedding_factory import EmbeddingFactory, EmbeddingProviderType
from backend.data.embeddings.embedding_validator import EmbeddingValidator
from backend.data.embeddings.embedding_batch_processor import (
    EmbeddingBatchProcessor,
    BatchProcessingConfig,
)
from backend.data.embeddings.embedding_metadata import (
    EmbeddingMetadataBuilder,
    create_embedding_metadata,
    ModelRegistry,
)

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingError",
    "EmbeddingDimensionError",
    "EmbeddingValidationError",
    "ModelNotFoundError",
    "SentenceTransformerProvider",
    "EmbeddingPipeline",
    "EmbeddingPipelineConfig",
    "EmbeddingCache",
    "EmbeddingFactory",
    "EmbeddingProviderType",
    "EmbeddingValidator",
    "EmbeddingBatchProcessor",
    "BatchProcessingConfig",
    "EmbeddingMetadataBuilder",
    "create_embedding_metadata",
    "ModelRegistry",
]
