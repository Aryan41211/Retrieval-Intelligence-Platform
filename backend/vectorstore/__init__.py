"""Vector store module for the Retrieval Intelligence Platform.

Provides provider-agnostic vector storage with persistent index management.
Currently supports FAISS with extensibility for future providers.
"""

from backend.vectorstore.base_vector_store import BaseVectorStore
from backend.vectorstore.exceptions import (
    EmbeddingNotFoundError,
    IndexCorruptionError,
    IndexCreationError,
    IndexLoadError,
    IndexSaveError,
    MetadataError,
    VectorStoreError,
)
from backend.vectorstore.faiss_vector_store import FAISSVectorStore
from backend.vectorstore.index_manager import IndexManager
from backend.vectorstore.index_metadata import DistanceMetric, IndexMetadata, IndexType
from backend.vectorstore.vector_store_factory import VectorStoreFactory

__all__ = [
    # Base
    "BaseVectorStore",
    # FAISS Implementation
    "FAISSVectorStore",
    # Management
    "IndexManager",
    "VectorStoreFactory",
    # Metadata
    "IndexMetadata",
    "IndexType",
    "DistanceMetric",
    # Exceptions
    "VectorStoreError",
    "IndexCreationError",
    "IndexLoadError",
    "IndexSaveError",
    "IndexCorruptionError",
    "EmbeddingNotFoundError",
    "MetadataError",
]
