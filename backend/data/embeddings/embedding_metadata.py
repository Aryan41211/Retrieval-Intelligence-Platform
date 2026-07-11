"""Embedding metadata utilities for tracking model and configuration info."""

from typing import Any
from uuid import UUID

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding, EmbeddingMetadata


class EmbeddingMetadataBuilder:
    """Builder for creating embedding metadata."""

    def __init__(self):
        self._metadata: dict[str, Any] = {}

    def with_model_info(
        self,
        model_name: str,
        model_version: str,
        dimension: int,
    ) -> "EmbeddingMetadataBuilder":
        self._metadata["model_name"] = model_name
        self._metadata["model_version"] = model_version
        self._metadata["embedding_dimension"] = dimension
        return self

    def with_chunk_info(self, chunk: Chunk, document_id: UUID) -> "EmbeddingMetadataBuilder":
        self._metadata["chunk_id"] = str(chunk.chunk_id)
        self._metadata["document_id"] = str(document_id)
        return self

    def with_performance(
        self,
        processing_time_ms: float,
        batch_size: int,
    ) -> "EmbeddingMetadataBuilder":
        self._metadata["processing_time_ms"] = processing_time_ms
        self._metadata["batch_size"] = batch_size
        return self

    def with_device(self, device: str) -> "EmbeddingMetadataBuilder":
        self._metadata["device"] = device
        return self

    def with_checksum(self, checksum: str) -> "EmbeddingMetadataBuilder":
        self._metadata["checksum"] = checksum
        return self

    def with_config(self, config: dict[str, Any]) -> "EmbeddingMetadataBuilder":
        self._metadata["configuration"] = config
        return self

    def build(self) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            model_name=self._metadata.get("model_name", "unknown"),
            model_version=self._metadata.get("model_version", "1.0.0"),
            embedding_dimension=self._metadata.get("embedding_dimension", 0),
            processing_time_ms=self._metadata.get("processing_time_ms", 0.0),
            checksum=self._metadata.get("checksum", ""),
            configuration=self._metadata,
        )

    def reset(self) -> None:
        self._metadata.clear()


def create_embedding_metadata(
    embedding: Embedding,
    chunk: Chunk,
    config: dict[str, Any] | None = None,
) -> EmbeddingMetadata:
    builder = EmbeddingMetadataBuilder()
    return (
        builder.with_model_info(
            model_name=embedding.model_name,
            model_version=embedding.model_version,
            dimension=embedding.embedding_dimension,
        )
        .with_chunk_info(chunk, chunk.document_id)
        .with_device(config.get("device", "cpu") if config else "cpu")
        .with_config(config or {})
        .build()
    )


class ModelRegistry:
    """Registry for embedding models and their metadata."""

    _models: dict[str, EmbeddingMetadata] = {}
    _default_model: str = "all-MiniLM-L6-v2"

    @classmethod
    def register(
        cls,
        name: str,
        dimension: int,
        version: str = "1.0.0",
        config: dict[str, Any] | None = None,
    ) -> None:
        cls._models[name] = EmbeddingMetadata(
            model_name=name,
            model_version=version,
            embedding_dimension=dimension,
            configuration=config or {},
        )

    @classmethod
    def get(cls, name: str) -> EmbeddingMetadata | None:
        return cls._models.get(name)

    @classmethod
    def list_models(cls) -> list[str]:
        return list(cls._models.keys())

    @classmethod
    def get_default(cls) -> str:
        return cls._default_model

    @classmethod
    def set_default(cls, name: str) -> None:
        if name not in cls._models:
            raise ValueError(f"Model {name} not registered")
        cls._default_model = name

    @classmethod
    def clear(cls) -> None:
        cls._models.clear()
        cls._default_model = "all-MiniLM-L6-v2"
