"""Tests for retrieval engine."""

from uuid import UUID

import numpy as np
import pytest

from backend.retrieval.exceptions import EmptyRetrievalResultError
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.vectorstore.faiss_vector_store import FAISSVectorStore


@pytest.fixture
def vector_store(tmp_path):
    """Create a FAISS vector store with temporary directory."""
    store = FAISSVectorStore(tmp_path)
    store.create_index(index_id="test-index", dimension=384)
    return store


@pytest.fixture
def populated_vector_store(tmp_path):
    """Create a populated FAISS vector store."""
    np.random.seed(42)
    embeddings = np.random.randn(20, 384).astype(np.float32)
    metadata = [
        {
            "chunk_id": f"chunk-{i}",
            "document_id": f"doc-{i % 3}",
            "chunk_text": f"Sample text for chunk {i}",
            "source_filename": f"doc_{i % 3}.txt",
            "language": "en",
            "metadata": {"index": i},
        }
        for i in range(20)
    ]

    store = FAISSVectorStore(tmp_path)
    store.create_index(index_id="test-index", dimension=384)
    store.add_embeddings(
        embeddings=embeddings,
        ids=[f"id-{i}" for i in range(20)],
        metadata=metadata,
    )
    return store


class TestRetrievalEngine:
    """Test suite for RetrievalEngine."""

    def test_create_engine(self, vector_store):
        """Test creating retrieval engine."""
        engine = RetrievalEngine(vector_store=vector_store)
        assert engine is not None
        assert engine._vector_store is vector_store

    def test_create_engine_no_vector_store(self):
        """Test creating engine without vector store raises error."""
        with pytest.raises(Exception):  # RetrievalConfigurationError
            RetrievalEngine(vector_store=None)

    def test_retrieve(self, populated_vector_store):
        """Test basic retrieval."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)

        results = engine.retrieve(request)

        assert isinstance(results, list)
        assert len(results) <= 5
        assert all(isinstance(r, RetrievalChunkResult) for r in results)

    def test_retrieve_with_filters(self, populated_vector_store):
        """Test retrieval with filters."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        filters = RetrievalFilters(document_ids=[UUID("doc-0")])
        request = RetrievalRequest(
            query_vector=query_vector, top_k=10, filters=filters
        )

        results = engine.retrieve(request)

        # All results should be from doc-0
        for r in results:
            assert str(r.document_id) == "doc-0"

    def test_retrieve_with_threshold(self, populated_vector_store):
        """Test retrieval with similarity threshold."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(
            query_vector=query_vector, top_k=10, similarity_threshold=0.5
        )

        results = engine.retrieve(request)

        # All results should meet threshold
        for r in results:
            assert r.similarity_score >= 0.5

    def test_retrieve_empty_result(self, populated_vector_store):
        """Test retrieval with no matching results."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        # Use a very high threshold that no results will meet
        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(
            query_vector=query_vector, top_k=5, similarity_threshold=0.999
        )

        with pytest.raises(EmptyRetrievalResultError):
            engine.retrieve(request)

    def test_retrieve_batch(self, populated_vector_store):
        """Test batch retrieval."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        requests = [
            RetrievalRequest(
                query_vector=np.random.randn(384).astype(np.float32).tolist(), top_k=3
            )
            for _ in range(5)
        ]

        results = engine.retrieve_batch(requests)

        assert len(results) == 5
        assert all(isinstance(r, list) for r in results)
        assert all(len(r) <= 3 for r in results)

    def test_retrieve_by_document(self, populated_vector_store):
        """Test retrieve_by_document method."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        results = engine.retrieve_by_document(
            query_vector=query_vector,
            top_k=5,
            document_ids=[UUID("doc-1")],
        )

        for r in results:
            assert str(r.document_id) == "doc-1"

    def test_retrieve_with_filters_method(self, populated_vector_store):
        """Test retrieve_with_filters convenience method."""
        engine = RetrievalEngine(vector_store=populated_vector_store)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        results = engine.retrieve_with_filters(
            query_vector=query_vector,
            top_k=5,
            similarity_threshold=0.3,
            filters=RetrievalFilters(languages=["en"]),
        )

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_retrieve_vector_store_error(self, vector_store):
        """Test handling of vector store errors."""
        engine = RetrievalEngine(vector_store=vector_store)

        # Don't add any embeddings, search should work but return empty
        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)

        with pytest.raises(EmptyRetrievalResultError):
            engine.retrieve(request)
