"""Tests for retrieval pipeline."""

import logging
from uuid import UUID

import numpy as np
import pytest

from backend.retrieval.exceptions import EmptyRetrievalResultError
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_pipeline import RetrievalPipeline
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.vectorstore.faiss_vector_store import FAISSVectorStore


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


class TestRetrievalPipeline:
    """Test suite for RetrievalPipeline."""

    def test_pipeline_run(self, populated_vector_store):
        """Test running the retrieval pipeline."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)

        results, metadata = pipeline.run(request)

        assert isinstance(results, list)
        assert isinstance(metadata, object)  # RetrievalMetadata
        assert len(results) <= 5
        assert metadata.retrieved_chunks == len(results)
        assert metadata.retrieval_latency_ms >= 0

    def test_pipeline_empty_result(self, populated_vector_store):
        """Test pipeline with empty results."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(
            query_vector=query_vector, top_k=5, similarity_threshold=0.999
        )

        with pytest.raises(EmptyRetrievalResultError):
            pipeline.run(request)

    def test_pipeline_with_filters(self, populated_vector_store):
        """Test pipeline with filters."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        filters = RetrievalFilters(document_ids=[UUID("doc-0")])
        request = RetrievalRequest(
            query_vector=query_vector, top_k=10, filters=filters
        )

        results, metadata = pipeline.run(request)

        # All results should be from doc-0
        for r in results:
            assert str(r.document_id) == "doc-0"

    def test_pipeline_logging(self, populated_vector_store, caplog):
        """Test pipeline logging."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)

        with caplog.at_level(logging.INFO):
            results, metadata = pipeline.run(request)

        # Check that logging occurred
        assert any("retrieval.success" in record.message for record in caplog.records)

    def test_pipeline_metadata_fields(self, populated_vector_store):
        """Test pipeline metadata contains expected fields."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(query_vector=query_vector, top_k=5)

        results, metadata = pipeline.run(request)

        assert metadata.retrieval_latency_ms >= 0
        assert metadata.total_candidates == len(results)
        assert metadata.retrieved_chunks == len(results)
        assert metadata.similarity_threshold == request.similarity_threshold
        assert "vector_similarity" in metadata.methods_used
        assert len(metadata.top_scores) <= 5

    def test_pipeline_correlation_id(self, populated_vector_store):
        """Test pipeline with correlation ID."""
        engine = RetrievalEngine(vector_store=populated_vector_store)
        pipeline = RetrievalPipeline(engine=engine)

        query_vector = np.random.randn(384).astype(np.float32).tolist()
        request = RetrievalRequest(
            query_vector=query_vector, top_k=5, correlation_id="test-123"
        )

        results, metadata = pipeline.run(request)

        assert isinstance(results, list)
        assert metadata.retrieved_chunks == len(results)
