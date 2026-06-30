"""Tests for similarity analyzer."""

from uuid import uuid4

import pytest
import numpy as np

from backend.data.models.embedding import Embedding
from backend.embedding_validation.similarity_analyzer import (
    SimilarityAnalyzer,
    SimilarityMetrics,
)


class TestSimilarityAnalyzer:
    """Tests for SimilarityAnalyzer class."""

    def test_compute_pairwise_similarities(self):
        analyzer = SimilarityAnalyzer()
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

        matrix = analyzer.compute_pairwise_similarities(embeddings)

        assert isinstance(matrix, np.ndarray)
        assert matrix.shape == (2, 2)
        assert matrix[0, 0] == pytest.approx(1.0)
        assert matrix[0, 1] == pytest.approx(0.0)

    def test_compute_pairwise_similarities_empty(self):
        analyzer = SimilarityAnalyzer()
        matrix = analyzer.compute_pairwise_similarities([])
        assert matrix.shape == (0,)

    def test_compute_pairwise_similarities_mixed_dimensions(self):
        analyzer = SimilarityAnalyzer()
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
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
        ]

        with pytest.raises(ValueError, match="Inconsistent dimensions"):
            analyzer.compute_pairwise_similarities(embeddings)

    def test_find_top_k_similar(self):
        analyzer = SimilarityAnalyzer()
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
                embedding_vector=[0.99, 0.01, 0.01],
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

        top_k = analyzer.find_top_k_similar(embeddings, k=2)

        assert len(top_k) == 3
        for item in top_k:
            assert len(item) <= 2

    def test_find_top_k_similar_insufficient(self):
        analyzer = SimilarityAnalyzer()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
        ]

        top_k = analyzer.find_top_k_similar(embeddings, k=2)
        assert top_k == []

    def test_compute_nearest_neighbor_stats(self):
        analyzer = SimilarityAnalyzer()
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
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 0.0, 1.0],
            ),
        ]

        stats = analyzer.compute_nearest_neighbor_stats(embeddings)

        assert "mean_nn_distance" in stats
        assert "std_nn_distance" in stats
        assert stats["mean_nn_distance"] == pytest.approx(1.0, rel=0.1)

    def test_detect_outlier_embeddings(self):
        analyzer = SimilarityAnalyzer()
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

        outliers = analyzer.detect_outlier_embeddings(embeddings)
        assert isinstance(outliers, list)

    def test_compute_similarity_metrics(self):
        analyzer = SimilarityAnalyzer()
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

        metrics = analyzer.compute_similarity_metrics(embeddings)

        assert isinstance(metrics, SimilarityMetrics)
        assert metrics.average_similarity == pytest.approx(0.0)
        assert "similarity_distribution" in metrics.__dict__

    def test_compute_similarity_metrics_insufficient(self):
        analyzer = SimilarityAnalyzer()
        metrics = analyzer.compute_similarity_metrics([])
        assert isinstance(metrics, SimilarityMetrics)

    def test_compute_cluster_quality(self):
        analyzer = SimilarityAnalyzer()
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

        quality = analyzer.compute_cluster_quality(embeddings)

        assert "silhouette_estimate" in quality
        assert "embedding_diversity" in quality

    def test_analyze_content_overlap(self):
        analyzer = SimilarityAnalyzer()
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
        ]

        overlap = analyzer.analyze_content_overlap(embeddings, threshold=0.99)
        assert len(overlap) >= 1

    def test_analyze_content_overlap_no_matches(self):
        analyzer = SimilarityAnalyzer()
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

        overlap = analyzer.analyze_content_overlap(embeddings, threshold=0.999)
        assert len(overlap) == 0