"""Abstract base class for vector store providers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from backend.vectorstore.index_metadata import IndexMetadata, IndexType
from backend.vectorstore.exceptions import VectorStoreError

from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult


class BaseVectorStore(ABC):
    """Abstract base class for vector store implementations.

    Defines the interface that all vector store providers must implement.
    The retrieval engine should only communicate with this interface,
    never with concrete implementations like FAISS directly.
    """

    def __init__(self, storage_dir: str | Path):
        """Initialize vector store.

        Args:
            storage_dir: Directory for storing index files.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._metadata: IndexMetadata | None = None

    @abstractmethod
    def create_index(
        self,
        index_id: str,
        dimension: int,
        index_type: IndexType = IndexType.FLAT,
        distance_metric: str = "cosine",
        **kwargs: Any,
    ) -> IndexMetadata:
        """Create a new vector index.

        Args:
            index_id: Unique identifier for the index.
            dimension: Dimension of embedding vectors.
            index_type: Type of index to create.
            distance_metric: Distance metric to use.
            **kwargs: Additional provider-specific options.

        Returns:
            IndexMetadata for the created index.

        Raises:
            IndexCreationError: If index creation fails.
        """
        pass

    @abstractmethod
    def load_index(self, index_id: str) -> IndexMetadata:
        """Load an existing index from disk.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            IndexMetadata for the loaded index.

        Raises:
            IndexLoadError: If index loading fails.
        """
        pass

    @abstractmethod
    def save_index(self, index_id: str) -> None:
        """Save index to disk.

        Args:
            index_id: Unique identifier for the index.

        Raises:
            IndexSaveError: If saving fails.
        """
        pass

    @abstractmethod
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        ids: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Add embeddings to the index.

        Args:
            embeddings: Numpy array of embedding vectors (N x D).
            ids: Optional list of embedding IDs.
            metadata: Optional list of metadata dicts.

        Returns:
            Number of embeddings added.

        Raises:
            VectorStoreError: If adding embeddings fails.
        """
        pass

    @abstractmethod
    def remove_embeddings(self, ids: list[str]) -> int:
        """Remove embeddings from the index.

        Args:
            ids: List of embedding IDs to remove.

        Returns:
            Number of embeddings removed.

        Raises:
            VectorStoreError: If removal fails.
        """
        pass

    @abstractmethod
    def update_embeddings(
        self,
        ids: list[str],
        embeddings: np.ndarray,
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Update existing embeddings in the index.

        Args:
            ids: List of embedding IDs to update.
            embeddings: New embedding vectors.
            metadata: Optional new metadata.

        Returns:
            Number of embeddings updated.

        Raises:
            VectorStoreError: If update fails.
        """
        pass

    @abstractmethod
    def get_embedding(self, embedding_id: str) -> np.ndarray | None:
        """Get a single embedding by ID.

        Args:
            embedding_id: Unique identifier for the embedding.

        Returns:
            Embedding vector or None if not found.
        """
        pass

    @abstractmethod
    def get_index_metadata(self) -> IndexMetadata | None:
        """Get metadata for the current index.

        Returns:
            IndexMetadata or None if no index is loaded.
        """
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform health check on the vector store.

        Returns:
            Dictionary with health status information.
        """
        pass

    @abstractmethod
    def delete_index(self, index_id: str) -> None:
        """Delete an index and all associated files.

        Args:
            index_id: Unique identifier for the index.
        """
        pass

    @abstractmethod
    def index_exists(self, index_id: str) -> bool:
        """Check if an index exists.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            True if index exists, False otherwise.
        """
        pass

    @abstractmethod
    def search(self, request: RetrievalRequest) -> list[RetrievalChunkResult]:
        """Search the current index for semantically similar chunks.

        Provider-agnostic retrieval contract.
        Implementations must never expose provider-specific vector/FAISS details.

        Args:
            request: RetrievalRequest including query_vector, top_k, similarity_threshold, filters.

        Returns:
            Ranked list of RetrievalChunkResult items (highest similarity first).
        """
        pass

    def batch_search(self, requests: list[RetrievalRequest]) -> list[list[RetrievalChunkResult]]:
        """Optional batch retrieval API.

        Default implementation falls back to single `search()`.
        Provider implementations may override for performance.

        Args:
            requests: List of RetrievalRequest objects.

        Returns:
            List of ranked result lists, one per request.
        """
        return [self.search(r) for r in requests]
