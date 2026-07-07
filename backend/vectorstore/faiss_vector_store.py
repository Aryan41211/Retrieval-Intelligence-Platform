
from pathlib import Path
from typing import Any

import numpy as np

from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.vectorstore.base_vector_store import BaseVectorStore
from backend.vectorstore.exceptions import (
    IndexCreationError,
    IndexLoadError,
    IndexSaveError,
    VectorStoreError,
)
from backend.vectorstore.index_metadata import DistanceMetric, IndexMetadata, IndexType
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

        # Retrieval-specific metadata repository (persisted alongside FAISS index).
        # Key: embedding_id (string)
        # Value: record dict used by semantic retrieval + filtering.
        self._vector_records: dict[str, dict[str, Any]] = {}

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

            # Restore ID mappings + retrieval records
            if index_data:
                if "id_map" in index_data:
                    self._id_map = index_data["id_map"]
                    self._reverse_id_map = {v: k for k, v in self._id_map.items()}

                if "vector_records" in index_data:
                    self._vector_records = index_data["vector_records"]

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
                "vector_records": self._vector_records,
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

        Note: FAISS is used only for vector indexing. Chunk text + metadata are stored
        in an internal retrieval metadata repository that is persisted alongside
        the FAISS index.

        Expected metadata item shape (provider-agnostic):
          - chunk_id: UUID (or str)
          - document_id: UUID (or str)
          - text/content: str (chunk text)
          - source_file/filename: str
          - embedding_model / embedding_model_name: str (optional)
          - embedding_model_version / embedding_model_version: str (optional)
          - language: str (optional)
          - custom: dict (optional)

        If `metadata` is omitted, records will be stored with only ids (filtering may not work).
        """
        try:
            if self._index is None or self._metadata is None:
                raise VectorStoreError("No index loaded. Call create_index() or load_index() first.")

            embeddings = np.array(embeddings, dtype=np.float32)

            # Normalize for cosine similarity so inner product == cosine similarity
            if self._metadata.distance_metric == DistanceMetric.COSINE:
                faiss_norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
                faiss_norm[faiss_norm == 0] = 1.0
                embeddings = embeddings / faiss_norm

            if ids is None:
                start_idx = self._index.ntotal
                ids = [str(i) for i in range(start_idx, start_idx + len(embeddings))]

            if metadata is None:
                metadata = [{} for _ in range(len(ids))]

            if len(metadata) != len(ids):
                raise VectorStoreError("metadata length must match ids length")

            start_idx = self._index.ntotal
            for i, embedding_id in enumerate(ids):
                int_id = start_idx + i
                self._id_map[embedding_id] = int_id
                self._reverse_id_map[int_id] = embedding_id

                m = metadata[i] or {}
                # Best-effort extraction with common keys
                chunk_text = (
                    m.get("chunk_text")
                    or m.get("text")
                    or m.get("content")
                    or m.get("chunk")
                    or ""
                )

                source_filename = (
                    m.get("source_file")
                    or m.get("filename")
                    or m.get("source_filename")
                    or ""
                )

                self._vector_records[str(embedding_id)] = {
                    "chunk_id": m.get("chunk_id"),
                    "document_id": m.get("document_id"),
                    "chunk_text": chunk_text,
                    "source_filename": source_filename,
                    "metadata": m.get("metadata", m.get("chunk_metadata", m.get("custom_metadata", m.get("custom", {})))),
                    "language": m.get("language") or m.get("lang"),
                    "custom": m.get("custom", {}),
                    "embedding_model": m.get("embedding_model") or m.get("model_name"),
                    "embedding_model_version": m.get("embedding_model_version") or m.get("model_version"),
                }

            self._index.add(embeddings)

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
                embedding_id = str(embedding_id)
                if embedding_id in self._id_map:
                    int_id = self._id_map[embedding_id]
                    # FAISS doesn't support direct removal; we remove mapping + records
                    del self._id_map[embedding_id]
                    if int_id in self._reverse_id_map:
                        del self._reverse_id_map[int_id]
                    if embedding_id in self._vector_records:
                        del self._vector_records[embedding_id]
                    removed_count += 1

            if self._metadata:
                # Keep metadata synchronized with the logical set of active vectors we can return.
                # FAISS itself doesn't support true deletions; we remove mappings + records.
                self._metadata.num_embeddings = len(self._vector_records)

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

    def get_vector_records(self) -> dict[str, dict[str, Any]]:
        """Capability method for sparse retrieval.

        Returns:
            Provider-internal vector records keyed by embedding_id string.
            Intended for building lightweight sparse indexes (e.g., BM25)
            without changing BaseVectorStore contract.
        """
        return self._vector_records

    def _record_matches_filters(self, record: dict[str, Any], request: RetrievalRequest) -> bool:
        filters: RetrievalFilters | None = request.filters

        # Explicit dimensions (request.*) should take precedence if provided
        document_ids = request.document_ids or (filters.document_ids if filters else None)
        source_filenames = request.source_filenames or (filters.source_filenames if filters else None)
        languages = request.languages or (filters.languages if filters else None)
        custom_filters = (filters.custom if filters else {}) or {}

        if document_ids:
            doc_id = record.get("document_id")
            if doc_id is None or str(doc_id) not in {str(d) for d in document_ids}:
                return False

        if source_filenames:
            sf = record.get("source_filename") or record.get("source_file")
            if sf not in set(source_filenames):
                return False

        if languages:
            lang = record.get("language")
            if lang not in set(languages):
                return False

        # Exact match custom filters:
        # - keys in custom can be either nested "custom.*" or direct metadata keys.
        record_custom = record.get("custom") or {}
        record_metadata = record.get("metadata") or {}

        for k, v in custom_filters.items():
            if k.startswith("custom."):
                kk = k.split("custom.", 1)[1]
                if record_custom.get(kk) != v:
                    return False
            else:
                # Try both metadata and custom
                if record_metadata.get(k) == v:
                    continue
                if record_custom.get(k) == v:
                    continue
                return False

        return True

    def search(self, request: RetrievalRequest) -> list[RetrievalChunkResult]:
        if self._index is None or self._metadata is None:
            raise VectorStoreError("No index loaded. Call create_index() or load_index() first.")

        query_vec = np.array([request.query_vector], dtype=np.float32)

        # Normalize if cosine similarity index
        if self._metadata.distance_metric == DistanceMetric.COSINE:
            norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
            norm[norm == 0] = 1.0
            query_vec = query_vec / norm

        top_k = int(request.top_k)
        if top_k <= 0:
            return []

        # FAISS search: returns distances and indices
        scores, int_ids = self._index.search(query_vec, top_k)
        scores = scores[0]
        int_ids = int_ids[0]

        results: list[RetrievalChunkResult] = []
        threshold = request.similarity_threshold

        for rank0, (score, int_id) in enumerate(zip(scores, int_ids, strict=False), start=1):
            if int_id < 0:
                continue

            embedding_id = self._reverse_id_map.get(int(int_id))
            if embedding_id is None:
                continue

            # Interpret similarity:
            # - cosine index uses normalized vectors + inner product => cosine similarity in [-1, 1]
            # - inner product distance: assume higher is more similar
            # - L2 distance not normalized: we convert using negative distance to match "higher is better"
            if self._metadata.distance_metric == DistanceMetric.EUCLIDEAN:
                similarity = float(-score)
            else:
                similarity = float(score)

            if threshold is not None and similarity < float(threshold):
                continue

            record = self._vector_records.get(str(embedding_id))
            if not record:
                # Still return a minimal record if we can't filter/construct text
                continue

            if not self._record_matches_filters(record, request):
                continue

            chunk_id_raw = record.get("chunk_id")
            document_id_raw = record.get("document_id")
            if not chunk_id_raw or not document_id_raw:
                continue

            try:
                from uuid import UUID

                chunk_uuid = UUID(str(chunk_id_raw))
                document_uuid = UUID(str(document_id_raw))
            except Exception:
                continue

            # RetrievalChunkResult enforces similarity_score >= 0.0
            similarity_score = max(0.0, float(similarity))

            results.append(
                RetrievalChunkResult(
                    chunk_id=chunk_uuid,
                    document_id=document_uuid,
                    chunk_text=record.get("chunk_text", "") or "",
                    similarity_score=similarity_score,
                    rank=rank0,
                    source_filename=record.get("source_filename") or None,
                    metadata=record.get("metadata") or record.get("custom") or {},
                    embedding_model=record.get("embedding_model") or None,
                    retrieval_timestamp=request.retrieval_timestamp,
                )
            )

        return results
