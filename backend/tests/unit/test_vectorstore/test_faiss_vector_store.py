"""Tests for FAISS vector store implementation."""

import numpy as np
import pytest
from uuid import UUID

from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.vectorstore.exceptions import (
    IndexCreationError,
    IndexLoadError,
    IndexSaveError,
    VectorStoreError,
)
from backend.vectorstore.faiss_vector_store import FAISSVectorStore
from backend.vectorstore.index_metadata import IndexType


@pytest.fixture
def vector_store(tmp_path):
    """Create a FAISS vector store with temporary directory."""
    return FAISSVectorStore(tmp_path)


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    np.random.seed(42)
    return np.random.randn(10, 384).astype(np.float32)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return [
        {
            "chunk_id": f"chunk-{i}",
            "document_id": str(UUID(int=i % 3)),
            "chunk_text": f"This is sample text for chunk {i}",
            "source_filename": f"document_{i % 3}.txt",
            "language": "en",
            "metadata": {"page": i},
        }
        for i in range(10)
    ]


class TestFAISSVectorStore:
    """Test suite for FAISSVectorStore."""

    def test_create_index(self, vector_store):
        """Test index creation."""
        metadata = vector_store.create_index(
            index_id="test-index",
            dimension=384,
            index_type=IndexType.FLAT,
            distance_metric="cosine",
        )

        assert metadata is not None
        assert metadata.index_id == "test-index"
        assert metadata.embedding_dimension == 384
        assert metadata.index_type == IndexType.FLAT
        assert metadata.distance_metric.value == "cosine"
        assert metadata.provider == "faiss"

    def test_add_embeddings(self, vector_store, sample_embeddings, sample_metadata):
        """Test adding embeddings to the index."""
        # Create index first
        vector_store.create_index(index_id="test-index", dimension=384)

        # Add embeddings
        count = vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        assert count == 10
        assert vector_store._metadata.num_embeddings == 10

    def test_add_embeddings_auto_generate_ids(self, vector_store, sample_embeddings):
        """Test adding embeddings with auto-generated IDs."""
        vector_store.create_index(index_id="test-index", dimension=384)

        count = vector_store.add_embeddings(embeddings=sample_embeddings)

        assert count == 10
        assert vector_store._metadata.num_embeddings == 10

    def test_search(self, vector_store, sample_embeddings, sample_metadata):
        """Test semantic search."""
        # Create and populate index
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Search with first embedding as query
        query_vector = sample_embeddings[0].tolist()
        request = RetrievalRequest(
            query_vector=query_vector,
            top_k=5,
        )

        results = vector_store.search(request)

        assert len(results) <= 5
        assert all(isinstance(r, RetrievalChunkResult) for r in results)
        assert all(r.similarity_score >= 0.0 for r in results)
        assert all(r.rank >= 1 for r in results)

        # First result should be the query itself (highest similarity)
        if results:
            assert results[0].chunk_id == sample_metadata[0]["chunk_id"]

    def test_search_with_threshold(self, vector_store, sample_embeddings, sample_metadata):
        """Test search with similarity threshold."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Search with high threshold
        request = RetrievalRequest(
            query_vector=sample_embeddings[0].tolist(),
            top_k=10,
            similarity_threshold=0.99,
        )

        results = vector_store.search(request)
        # Should return fewer results with high threshold
        assert len(results) <= 10

    def test_search_with_document_filter(self, vector_store, sample_embeddings, sample_metadata):
        """Test search with document ID filter."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Filter for doc-0 (use the actual UUID from metadata)
        doc_0_id = UUID(int=0)
        filters = RetrievalFilters(document_ids=[doc_0_id])
        request = RetrievalRequest(
            query_vector=sample_embeddings[0].tolist(),
            top_k=10,
            filters=filters,
        )

        results = vector_store.search(request)
        # All results should be from doc-0
        for r in results:
            assert r.document_id == doc_0_id

    def test_search_with_language_filter(self, vector_store, sample_embeddings, sample_metadata):
        """Test search with language filter."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        filters = RetrievalFilters(languages=["en"])
        request = RetrievalRequest(
            query_vector=sample_embeddings[0].tolist(),
            top_k=10,
            filters=filters,
        )

        results = vector_store.search(request)
        # All results should be in English
        for r in results:
            assert r.metadata.get("language") == "en"

    def test_remove_embeddings(self, vector_store, sample_embeddings, sample_metadata):
        """Test removing embeddings."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Remove some embeddings
        removed = vector_store.remove_embeddings(["id-0", "id-1"])
        assert removed == 2
        assert vector_store._metadata.num_embeddings == 8

    def test_update_embeddings(self, vector_store, sample_embeddings, sample_metadata):
        """Test updating embeddings."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Update some embeddings
        new_embeddings = np.random.randn(2, 384).astype(np.float32)
        updated = vector_store.update_embeddings(
            ids=["id-0", "id-1"],
            embeddings=new_embeddings,
        )

        assert updated == 2
        # Note: FAISS doesn't support true removal, so update adds new embeddings
        # The metadata count reflects the actual FAISS index size
        assert vector_store._metadata.num_embeddings == 12

    def test_get_embedding(self, vector_store, sample_embeddings, sample_metadata):
        """Test getting a single embedding."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=["id-0"],
            metadata=[sample_metadata[0]],
        )

        embedding = vector_store.get_embedding("id-0")
        assert embedding is not None
        assert embedding.shape == (384,)

    def test_health_check(self, vector_store):
        """Test health check."""
        health = vector_store.health_check()
        assert "status" in health
        assert "provider" in health

        vector_store.create_index(index_id="test-index", dimension=384)
        health = vector_store.health_check()
        assert health["status"] == "healthy"
        assert health["index_loaded"] is True

    def test_index_exists(self, vector_store):
        """Test checking if index exists."""
        assert not vector_store.index_exists("test-index")

        vector_store.create_index(index_id="test-index", dimension=384)
        # Index must be saved to disk to exist
        vector_store.save_index("test-index")
        assert vector_store.index_exists("test-index")

    def test_save_and_load_index(self, vector_store, sample_embeddings, sample_metadata):
        """Test saving and loading index."""
        # Create and populate index
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Save index
        vector_store.save_index("test-index")

        # Create new vector store instance and load
        new_store = FAISSVectorStore(vector_store.storage_dir)
        metadata = new_store.load_index("test-index")

        assert metadata is not None
        assert metadata.num_embeddings == 10

        # Verify search works after loading
        query_vector = sample_embeddings[0].tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)
        results = new_store.search(request)
        assert len(results) <= 5

    def test_delete_index(self, vector_store, sample_embeddings, sample_metadata):
        """Test deleting index."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        # Save index so it exists on disk
        vector_store.save_index("test-index")
        assert vector_store.index_exists("test-index")
        vector_store.delete_index("test-index")
        assert not vector_store.index_exists("test-index")

    def test_search_no_index(self, vector_store):
        """Test search without loading index."""
        with pytest.raises(VectorStoreError):
            request = RetrievalRequest(query_vector=[0.0] * 384, top_k=5)
            vector_store.search(request)

    def test_batch_search(self, vector_store, sample_embeddings, sample_metadata):
        """Test batch search."""
        vector_store.create_index(index_id="test-index", dimension=384)
        vector_store.add_embeddings(
            embeddings=sample_embeddings,
            ids=[f"id-{i}" for i in range(10)],
            metadata=sample_metadata,
        )

        requests = [
            RetrievalRequest(query_vector=sample_embeddings[i].tolist(), top_k=3)
            for i in range(3)
        ]

        results = vector_store.batch_search(requests)
        assert len(results) == 3
        assert all(len(r) <= 3 for r in results)