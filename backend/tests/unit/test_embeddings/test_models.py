"""Tests for embedding models."""

import pytest
from uuid import uuid4

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import (
    Embedding,
    EmbeddingMetadata,
    EmbeddingModelInfo,
    EmbeddingResult,
    EmbeddingBatchResult,
)


class TestEmbeddingModelInfo:
    """Tests for EmbeddingModelInfo model."""

    def test_create_model_info(self):
        info = EmbeddingModelInfo(
            name="test-model",
            version="1.0.0",
            dimension=384,
            max_sequence_length=512,
            provider="test",
        )
        assert info.name == "test-model"
        assert info.dimension == 384

    def test_default_values(self):
        info = EmbeddingModelInfo(name="default")
        assert info.version == "1.0.0"
        assert info.dimension == 0
        assert info.provider == "unknown"


class TestEmbedding:
    """Tests for Embedding model."""

    def test_create_embedding(self):
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        assert embedding.model_name == "test-model"
        assert len(embedding.embedding_vector) == 10

    def test_compute_checksum(self):
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0.0",
            embedding_dimension=3,
            embedding_vector=[0.1, 0.2, 0.3],
        )
        checksum = embedding.compute_checksum()
        assert len(checksum) == 64

    def test_vector_property(self):
        import numpy as np

        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0.0",
            embedding_dimension=3,
            embedding_vector=[0.1, 0.2, 0.3],
        )
        vector = embedding.vector
        assert isinstance(vector, np.ndarray)
        assert vector.dtype == np.float32

    def test_to_numpy(self):
        import numpy as np

        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0.0",
            embedding_dimension=3,
            embedding_vector=[0.1, 0.2, 0.3],
        )
        arr = embedding.to_numpy()
        assert isinstance(arr, np.ndarray)


class TestEmbeddingResult:
    """Tests for EmbeddingResult model."""

    def test_successful_result(self):
        doc_id = uuid4()
        chunk = Chunk(text="test", document_id=doc_id)
        embedding = Embedding(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            model_name="test",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        result = EmbeddingResult(chunk=chunk, embedding=embedding)
        assert result.cache_hit is False
        assert result.error is None

    def test_failed_result(self):
        doc_id = uuid4()
        chunk = Chunk(text="test", document_id=doc_id)
        result = EmbeddingResult(chunk=chunk, error="Test error")
        assert result.embedding is None
        assert result.cache_hit is False


class TestEmbeddingBatchResult:
    """Tests for EmbeddingBatchResult model."""

    def test_empty_results(self):
        result = EmbeddingBatchResult(results=[])
        assert result.successful_embeddings == []
        assert result.failed_chunks == []
        assert result.success_rate == 0.0

    def test_success_rate(self):
        doc_id = uuid4()
        chunk = Chunk(text="test", document_id=doc_id)
        embedding = Embedding(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            model_name="test",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        results = [
            EmbeddingResult(chunk=chunk, embedding=embedding),
            EmbeddingResult(chunk=chunk, error="fail"),
        ]
        batch = EmbeddingBatchResult(results=results)
        assert batch.success_rate == 0.5