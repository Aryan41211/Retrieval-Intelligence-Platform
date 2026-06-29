"""Embedding package for vector generation."""

from backend.data.embeddings.base_embedding_provider import (
    BaseEmbeddingProvider,
    EmbeddingDimensionError,
    EmbeddingError,
    EmbeddingValidationError,
    ModelNotFoundError,
)
from backend.data.embeddings.embedding_batch_processor import (
    BatchProcessingConfig,
    EmbeddingBatchProcessor,
)
from backend.data.embeddings.embedding_cache import EmbeddingCache
from backend.data.embeddings.embedding_factory import (
    EmbeddingFactory,
    EmbeddingProviderType,
)
from backend.data.embeddings.embedding_metadata import (
    EmbeddingMetadataBuilder,
    ModelRegistry,
)
from backend.data.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingPipelineConfig,
)
from backend.data.embeddings.embedding_validator import EmbeddingValidator

__all__ = [
    "BaseEmbeddingProvider",
    "SentenceTransformerProvider",
    "EmbeddingCache",
    "EmbeddingValidator",
    "EmbeddingBatchProcessor",
    "BatchProcessingConfig",
    "EmbeddingMetadataBuilder",
    "ModelRegistry",
    "EmbeddingFactory",
    "EmbeddingProviderType",
    "EmbeddingPipeline",
    "EmbeddingPipelineConfig",
    "EmbeddingError",
    "EmbeddingValidationError",
    "EmbeddingDimensionError",
    "ModelNotFoundError",
]


def __getattr__(name: str):
    if name == "SentenceTransformerProvider":
        try:
            from backend.data.embeddings.sentence_transformer_provider import (
                SentenceTransformerProvider,
            )

            return SentenceTransformerProvider
        except ImportError as e:
            raise ImportError(
                f"SentenceTransformerProvider requires sentence-transformers: {e}"
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")