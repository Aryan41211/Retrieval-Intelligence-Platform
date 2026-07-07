"""Index metadata management for vector stores."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IndexType(str, Enum):
    """Supported FAISS index types."""

    FLAT = "flat"
    HNSW = "hnsw"
    IVF = "ivf"
    PQ = "pq"


class DistanceMetric(str, Enum):
    """Supported distance metrics."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    INNER_PRODUCT = "inner_product"


class IndexMetadata(BaseModel):
    """Metadata for a vector index."""

    index_id: str = Field(description="Unique identifier for the index")
    provider: str = Field(description="Vector store provider (e.g., 'faiss')")
    embedding_model: str = Field(description="Name of the embedding model")
    embedding_dimension: int = Field(description="Dimension of embedding vectors")
    num_embeddings: int = Field(default=0, description="Number of embeddings in the index")
    index_type: IndexType = Field(description="Type of FAISS index")
    distance_metric: DistanceMetric = Field(description="Distance metric used")
    creation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checksum: str = Field(default="", description="Checksum of the index file")
    version: str = Field(default="1.0.0", description="Index format version")
    storage_path: str = Field(description="Path to the stored index file")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")

    model_config = {"protected_namespaces": ()}

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp to now."""
        self.last_updated = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "index_id": self.index_id,
            "provider": self.provider,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "num_embeddings": self.num_embeddings,
            "index_type": self.index_type.value,
            "distance_metric": self.distance_metric.value,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "checksum": self.checksum,
            "version": self.version,
            "storage_path": self.storage_path,
            "configuration": self.configuration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexMetadata":
        """Create metadata from dictionary."""
        data = data.copy()
        data["index_type"] = IndexType(data["index_type"])
        data["distance_metric"] = DistanceMetric(data["distance_metric"])
        data["creation_timestamp"] = datetime.fromisoformat(data["creation_timestamp"])
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)
