"""Tests for embedding statistics."""

from uuid import uuid4

from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_statistics import (
    DensityStatistics,
    EmbeddingStatistics,
    EmbeddingStats,
    NormStatistics,
)


class TestEmbeddingStatistics:
    """Tests for EmbeddingStatistics class."""

    def test_compute_norm_statistics(self):
        stats = EmbeddingStatistics()
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
        result = stats.compute_norm_statistics(embeddings)
        assert isinstance(result, NormStatistics)
        assert result.mean_norm == 1.0
        assert len(result.norms) == 2

    def test_compute_norm_statistics_empty(self):
        stats = EmbeddingStatistics()
        result = stats.compute_norm_statistics([])
        assert isinstance(result, NormStatistics)
        assert result.mean_norm == 0.0

    def test_compute_value_statistics(self):
        stats = EmbeddingStatistics()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=2,
                embedding_vector=[1.0, 2.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=2,
                embedding_vector=[3.0, 4.0],
            ),
        ]
        result = stats.compute_value_statistics(embeddings)
        assert isinstance(result, EmbeddingStats)
        assert result.mean == 2.5
        assert result.count == 4

    def test_compute_density_statistics(self):
        stats = EmbeddingStatistics()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=4,
                embedding_vector=[1.0, 0.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=4,
                embedding_vector=[1.0, 1.0, 1.0, 1.0],
            ),
        ]
        result = stats.compute_density_statistics(embeddings)

        assert isinstance(result, DensityStatistics)
        assert result.mean_density == 0.625
        assert result.outlier_count == 0

    def test_compute_similarity_distribution(self):
        stats = EmbeddingStatistics()
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
        result = stats.compute_similarity_distribution(embeddings)
        assert "mean" in result
        assert "std" in result
        assert result["mean"] < 0.5

    def test_compute_similarity_distribution_empty(self):
        stats = EmbeddingStatistics()
        result = stats.compute_similarity_distribution([])
        assert result == {"mean": 0, "std": 0, "min": 0, "max": 0}

    def test_generate_quality_report(self):
        stats = EmbeddingStatistics()
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
                embedding_vector=[0.2] * 100,
            ),
        ]
        result = stats.generate_quality_report(embeddings, expected_dimension=100)
        assert result.total_embeddings == 2
        assert result.embedding_dimension == 100

    def test_generate_quality_report_dimension_mismatch(self):
        stats = EmbeddingStatistics()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=100,
                embedding_vector=[0.1] * 100,
            ),
        ]
        result = stats.generate_quality_report(embeddings, expected_dimension=200)
        assert len(result.warnings) > 0

    def test_generate_quality_report_empty(self):
        stats = EmbeddingStatistics()
        result = stats.generate_quality_report([])
        assert result.total_embeddings == 0
