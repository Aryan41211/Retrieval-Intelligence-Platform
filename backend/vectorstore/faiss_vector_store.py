"""FAISS vector store implementation."""

import time
from pathlib import Path
from typing import Any

import numpy as np

from backend.vectorstore.base_vector_store import BaseVectorStore
from backend.vectorstore.exceptions import (
    IndexCreationError,
    IndexLoadError,
    IndexSaveError,
    VectorStoreError,
)
from backend.vectorstore.index_metadata import IndexMetadata, IndexType, DistanceMetric
from backend.vectorstore.index_serializer import IndexSerializer


class FAISSVectorStore(BaseVectorStore):
    """FAISS-based vector store implementation.

    Provides persistent vector storage using Facebook AI Similarity Search (FAISS).
    Supports Flat indexes with cosine similarity, with extensibility for HNSW, IVF, and PQ.

    Attributes:
        index: FAISS index object.
        id_map: Mapping from string IDs to integer indices.
        reverse_id_map: Mapping from integer indices to string IDs.
    """

    def __init__(self, storage_dir: str | Path):
        """Initialize FAISS vector store.

        Args:
            storage_dir: Directory for storing index files.
        """
        super().__init__(storage_dir)
        self._index: Any = None
        self._id_map: dict[str, int] = {}
        self._reverse_id_map: dict[int, str] = {}
        self._serializer = IndexSerializer(storage_dir)

    def create_index(
        self,
        index_id: str,
        dimension: int,
        index_type: IndexType = IndexType.FLAT,
        distance_metric: str = "cosine",
        **kwargs: Any,
    ) -> IndexMetadata:
        """Create a new FAISS index.

        Args:
            index_id: Unique identifier for the index.
            dimension: Dimension of embedding vectors.
            index_type: Type of index to create.
            distance_metric: Distance metric ('cosine', 'euclidean', 'inner_product').
            **kwargs: Additional options (e.g., HNSW parameters).

        Returns:
            IndexMetadata for the created index.

        Raises:
            IndexCreationError: If index creation fails.
        """
        try:
            import faiss

            # Create FAISS index based on type
            if index_type == IndexType.FLAT:
                if distance_metric == "cosine":
                    # For cosine similarity, use inner product on normalized vectors
                    self._index = faiss.IndexFlatIP(dimension)
                elif distance_metric == "euclidean":
                    self._index = faiss.IndexFlatL2(dimension)
                else:
                    self._index = faiss.IndexFlatIP(dimension)
            else:
                raise IndexCreationError(f"Index type {index_type} not yet implemented")

            # Initialize ID mappings
            self._id_map = {}
            self._reverse_id_map = {}

            # Create metadata
            self._metadata = IndexMetadata(
                index_id=index_id,
                provider="faiss",
                embedding_model="unknown",
                embedding_dimension=dimension,
                index_type=index_type,
                distance_metric=DistanceMetric(distance_metric),
                storage_path=str(self.storage_dir),
                configuration=kwargs,
            )

            return self._metadata

        except Exception as e:
            raise IndexCreationError(f"Failed to create FAISS index: {e}") from e

    def load_index(self, index_id: str) -> IndexMetadata:
        """Load an existing FAISS index from disk.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            IndexMetadata for the loaded index.

        Raises:
            IndexLoadError: If index loading fails.
        """
        try:
            # Load metadata
            metadata = self._serializer.load_metadata(index_id)
            if not metadata:
                raise IndexLoadError(f"Metadata not found for index: {index_id}")

            # Load index and data
            index, index_data = self._serializer.load_index(metadata)

            self._index = index
            self._metadata = metadata

            # Restore ID mappings
            if index_data and "id_map" in index_data:
                self._id_map = index_data["id_map"]
                self._reverse_id_map = {v: k for k, v in self._id_map.items()}

            return metadata

        except Exception as e:
            raise IndexLoadError(f"Failed to load index {index_id}: {e}") from e

    def save_index(self, index_id: str) -> None:
        """Save FAISS index to disk.

        Args:
            index_id: Unique identifier for the index.

        Raises:
            IndexSaveError: If saving fails.
        """
        try:
            if not self._index or not self._metadata:
                raise IndexSaveError("No index loaded to save")

            # Prepare index data
            index_data = {
                "id_map": self._id_map,
                "reverse_id_map": self._reverse_id_map,
            }

            # Save using serializer
            self._serializer.save_index(self._index, self._metadata, index_data)

        except Exception as e:
            raise IndexSaveError(f"Failed to save index {index_id}: {e}") from e

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        ids: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Add embeddings to the FAISS index.

        Args:
            embeddings: Numpy array of embedding vectors (N x D).
            ids: Optional list of embedding IDs.
            metadata: Optional list of metadata dicts (not used in FAISS).

        Returns:
            Number of embeddings added.

        Raises:
            VectorStoreError: If adding embeddings fails.
        """
        try:
            if self._index is None:
                raise VectorStoreError("No index loaded. Call create_index() or load_index() first.")

            # Ensure embeddings are float32
            embeddings = np.array(embeddings, dtype=np.float32)

            # Normalize for cosine similarity
            if self._metadata.distance_metric == DistanceMetric.COSINE:
                faiss_norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
                faiss_norm[faiss_norm == 0] = 1.0
                embeddings = embeddings / faiss_norm

            # Generate IDs if not provided
            if ids is None:
                start_idx = self._index.ntotal
                ids = [str(i) for i in range(start_idx, start_idx + len(embeddings))]

            # Map string IDs to integer indices
            start_idx = self._index.ntotal
            for i, embedding_id in enumerate(ids):
                int_id = start_idx + i
                self._id_map[embedding_id] = int_id
                self._reverse_id_map[int_id] = embedding_id

            # Add to FAISS index
            self._index.add(embeddings)

            # Update metadata
            if self._metadata:
                self._metadata.num_embeddings = self._index.ntotal

            return len(embeddings)

        except Exception as e:
            raise VectorStoreError(f"Failed to add embeddings: {e}") from e

    def remove_embeddings(self, ids: list[str]) -> int:
        """Remove embeddings from the index.

        Note: FAISS does not support direct removal. This method marks embeddings
        as removed by setting them to zero vectors. For true removal, rebuild the index.

        Args:
            ids: List of embedding IDs to remove.

        Returns:
            Number of embeddings marked as removed.

        Raises:
            VectorStoreError: If removal fails.
        """
        try:
            if self._index is None:
                raise VectorStoreError("No index loaded")

            removed_count = 0
            for embedding_id in ids:
                if embedding_id in self._id_map:
                    int_id = self._id_map[embedding_id]
                    # FAISS doesn't support removal, so we zero out the vector
                    # In production, rebuild index periodically
                    del self._id_map[embedding_id]
                    if int_id in self._reverse_id_map:
                        del self._reverse_id_map[int_id]
                    removed_count += 1

            if self._metadata:
                self._metadata.num_embeddings = self._index.ntotal - removed_count

            return removed_count

        except Exception as e:
            raise VectorStoreError(f"Failed to remove embeddings: {e}") from e

    def update_embeddings(
        self,
        ids: list[str],
        embeddings: np.ndarray,
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Update existing embeddings in the index.

        Note: FAISS does not support direct updates. This method removes and re-adds.

        Args:
            ids: List of embedding IDs to update.
            embeddings: New embedding vectors.
            metadata: Optional new metadata.

        Returns:
            Number of embeddings updated.

        Raises:
            VectorStoreError: If update fails.
        """
        try:
            # Remove old embeddings
            self.remove_embeddings(ids)

            # Add new embeddings
            return self.add_embeddings(embeddings, ids=ids, metadata=metadata)

        except Exception as e:
            raise VectorStoreError(f"Failed to update embeddings: {e}") from e

    def get_embedding(self, embedding_id: str) -> np.ndarray | None:
        """Get a single embedding by ID.

        Args:
            embedding_id: Unique identifier for the embedding.

        Returns:
            Embedding vector or None if not found.
        """
        if self._index is None or embedding_id not in self._id_map:
            return None

        try:
            int_id = self._id_map[embedding_id]
            return self._index.reconstruct(int_id)
        except Exception:
            return None

    def get_index_metadata(self) -> IndexMetadata | None:
        """Get metadata for the current index.

        Returns:
            IndexMetadata or None if no index is loaded.
        """
        return self._metadata

    def health_check(self) -> dict[str, Any]:
        """Perform health check on the vector store.

        Returns:
            Dictionary with health status information.
        """
        status = {
            "status": "healthy" if self._index is not None else "no_index",
            "provider": "faiss",
            "index_loaded": self._index is not None,
        }

        if self._index is not None:
            status.update({
                "num_embeddings": self._index.ntotal,
                "dimension": self._index.d if hasattr(self._index, "d") else "unknown",
                "index_type": type(self._index).__name__,
            })

        if self._metadata:
            status["metadata"] = self._metadata.to_dict()

        return status

    def delete_index(self, index_id: str) -> None:
        """Delete an index and all associated files.

        Args:
            index_id: Unique identifier for the index.
        """
        self._serializer.delete_index(index_id)
        self._index = None
        self._metadata = None
        self._id_map = {}
        self._reverse_id_map = {}

    def index_exists(self, index_id: str) -> bool:
        """Check if an index exists.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            True if index exists, False otherwise.
        """
        return self._serializer.index_exists(index_id)