"""Tests for embedding visualizer."""

import math
from uuid import uuid4

import pytest

from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_visualizer import EmbeddingVisualizer


class TestEmbeddingVisualizer:
    """Tests for EmbeddingVisualizer class."""

    def test_compute_norm_distribution(self):
        visualizer = EmbeddingVisualizer()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=2,
                embedding_vector=[1.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=2,
                embedding_vector=[0.0, 1.0],
            ),
        ]

        result = visualizer.compute_norm_distribution(embeddings)

        assert "histogram" in result
        assert "mean" in result
        assert result["mean"] == 1.0
        assert len(result["histogram"]) > 0

    def test_compute_norm_distribution_empty(self):
        visualizer = EmbeddingVisualizer()
        result = visualizer.compute_norm_distribution([])

        assert result["mean"] == 0

    def test_compute_similarity_histogram(self):
        visualizer = EmbeddingVisualizer()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 1.0, 0.0],
            ),
        ]

        result = visualizer.compute_similarity_histogram(embeddings)

        assert "histogram" in result
        assert "mean" in result
        assert result["mean"] == pytest.approx(0.0)

    def test_compute_similarity_histogram_empty(self):
        visualizer = EmbeddingVisualizer()
        result = visualizer.compute_similarity_histogram([])

        assert result["mean"] == 0

    def test_compute_latency_histogram(self):
        visualizer = EmbeddingVisualizer()
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = visualizer.compute_latency_histogram(latencies)

        assert "histogram" in result
        assert result["mean"] == 30.0
        assert result["median"] == 30.0

    def test_compute_latency_histogram_empty(self):
        visualizer = EmbeddingVisualizer()
        result = visualizer.compute_latency_histogram([])

        assert result["mean"] == 0

    def test_compute_duplicate_clusters(self):
        visualizer = EmbeddingVisualizer()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.999, 0.01, 0.01],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 0.0, 1.0],
            ),
        ]

        result = visualizer.compute_duplicate_clusters(embeddings, threshold=0.99)

        assert "cluster_count" in result
        assert result["cluster_count"] >= 1

    def test_generate_quality_summary(self):
        visualizer = EmbeddingVisualizer()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=100,
                embedding_vector=[0.1] * 100,
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=100,
                embedding_vector=[0.1] * 100,
            ),
        ]

        result = visualizer.generate_quality_summary(embeddings)

        assert result["total_embeddings"] == 2
        assert result["embedding_dimension"] == 100
        assert "norm_distribution" in result
        assert "similarity_distribution" in result

    def test_generate_quality_summary_empty(self):
        visualizer = EmbeddingVisualizer()
        result = visualizer.generate_quality_summary([])

        assert result["total_embeddings"] == 0