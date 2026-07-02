"""Index lifecycle management for vector stores."""

from typing import Any

from backend.vectorstore.base_vector_store import BaseVectorStore
from backend.vectorstore.exceptions import (
    IndexCreationError,
    IndexLoadError,
    IndexSaveError,
    VectorStoreError,
)
from backend.vectorstore.index_metadata import IndexMetadata, IndexType


class IndexManager:
    """Manages vector index lifecycle operations.

    Provides high-level operations for creating, loading, saving, and managing
    vector indexes. Coordinates between the vector store and serializer.
    """

    def __init__(self, vector_store: BaseVectorStore):
        """Initialize index manager.

        Args:
            vector_store: Vector store instance to manage.
        """
        self._vector_store = vector_store
        self._current_index_id: str | None = None

    def create_index(
        self,
        index_id: str,
        dimension: int,
        index_type: IndexType = IndexType.FLAT,
        distance_metric: str = "cosine",
        auto_save: bool = True,
        **kwargs: Any,
    ) -> IndexMetadata:
        """Create a new index and optionally save it.

        Args:
            index_id: Unique identifier for the index.
            dimension: Dimension of embedding vectors.
            index_type: Type of index to create.
            distance_metric: Distance metric to use.
            auto_save: Whether to save index immediately after creation.
            **kwargs: Additional provider-specific options.

        Returns:
            IndexMetadata for the created index.

        Raises:
            IndexCreationError: If index creation fails.
        """
        metadata = self._vector_store.create_index(
            index_id, dimension, index_type, distance_metric, **kwargs
        )
        self._current_index_id = index_id

        if auto_save:
            self._vector_store.save_index(index_id)

        return metadata

    def load_index(self, index_id: str) -> IndexMetadata:
        """Load an existing index.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            IndexMetadata for the loaded index.

        Raises:
            IndexLoadError: If index loading fails.
        """
        metadata = self._vector_store.load_index(index_id)
        self._current_index_id = index_id
        return metadata

    def save_index(self, index_id: str | None = None) -> None:
        """Save index to disk.

        Args:
            index_id: Unique identifier for the index. Uses current index if not provided.

        Raises:
            IndexSaveError: If saving fails.
        """
        target_id = index_id or self._current_index_id
        if not target_id:
            raise IndexSaveError("No index ID provided and no current index")

        self._vector_store.save_index(target_id)

    def add_embeddings(
        self,
        embeddings: Any,
        ids: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
        auto_save: bool = False,
    ) -> int:
        """Add embeddings to the current index.

        Args:
            embeddings: Embedding vectors (numpy array or list).
            ids: Optional list of embedding IDs.
            metadata: Optional list of metadata dicts.
            auto_save: Whether to save index after adding.

        Returns:
            Number of embeddings added.

        Raises:
            VectorStoreError: If adding embeddings fails.
        """
        import numpy as np

        if isinstance(embeddings, list):
            embeddings = np.array(embeddings, dtype=np.float32)

        count = self._vector_store.add_embeddings(embeddings, ids, metadata)

        if auto_save and self._current_index_id:
            self._vector_store.save_index(self._current_index_id)

        return count

    def remove_embeddings(self, ids: list[str], auto_save: bool = False) -> int:
        """Remove embeddings from the current index.

        Args:
            ids: List of embedding IDs to remove.
            auto_save: Whether to save index after removal.

        Returns:
            Number of embeddings removed.

        Raises:
            VectorStoreError: If removal fails.
        """
        count = self._vector_store.remove_embeddings(ids)

        if auto_save and self._current_index_id:
            self._vector_store.save_index(self._current_index_id)

        return count

    def update_embeddings(
        self,
        ids: list[str],
        embeddings: Any,
        metadata: list[dict[str, Any]] | None = None,
        auto_save: bool = False,
    ) -> int:
        """Update embeddings in the current index.

        Args:
            ids: List of embedding IDs to update.
            embeddings: New embedding vectors.
            metadata: Optional new metadata.
            auto_save: Whether to save index after update.

        Returns:
            Number of embeddings updated.

        Raises:
            VectorStoreError: If update fails.
        """
        import numpy as np

        if isinstance(embeddings, list):
            embeddings = np.array(embeddings, dtype=np.float32)

        count = self._vector_store.update_embeddings(ids, embeddings, metadata)

        if auto_save and self._current_index_id:
            self._vector_store.save_index(self._current_index_id)

        return count

    def get_embedding(self, embedding_id: str) -> Any:
        """Get a single embedding by ID.

        Args:
            embedding_id: Unique identifier for the embedding.

        Returns:
            Embedding vector or None if not found.
        """
        return self._vector_store.get_embedding(embedding_id)

    def get_metadata(self) -> IndexMetadata | None:
        """Get metadata for the current index.

        Returns:
            IndexMetadata or None if no index is loaded.
        """
        return self._vector_store.get_index_metadata()

    def health_check(self) -> dict[str, Any]:
        """Perform health check on the current index.

        Returns:
            Dictionary with health status information.
        """
        return self._vector_store.health_check()

    def delete_index(self, index_id: str) -> None:
        """Delete an index.

        Args:
            index_id: Unique identifier for the index.
        """
        self._vector_store.delete_index(index_id)
        if self._current_index_id == index_id:
            self._current_index_id = None

    def index_exists(self, index_id: str) -> bool:
        """Check if an index exists.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            True if index exists, False otherwise.
        """
        return self._vector_store.index_exists(index_id)

    @property
    def current_index_id(self) -> str | None:
        """Get the current index ID."""
        return self._current_index_id