"""Tests for extended embedding validator."""

import math

import pytest
from uuid import uuid4

from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_validator import (
    ExtendedEmbeddingValidator,
    ValidationResult,
)


class TestExtendedEmbeddingValidator:
    """Tests for ExtendedEmbeddingValidator class."""

    def test_validate_valid_embedding(self):
        validator = ExtendedEmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is True
        assert errors == []
        assert warnings == []

    def test_validate_empty_vector(self):
        validator = ExtendedEmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=0,
            embedding_vector=[],
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is False
        assert "empty" in errors[0]

    def test_validate_nan_values_disallowed(self):
        validator = ExtendedEmbeddingValidator(allow_nan=False)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("nan"), 0.3],
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is False
        assert any("NaN" in e for e in errors)

    def test_validate_nan_values_allowed(self):
        validator = ExtendedEmbeddingValidator(allow_nan=True)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("nan"), 0.3],
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is True
        assert any("NaN" in w for w in warnings)

    def test_validate_inf_values_disallowed(self):
        validator = ExtendedEmbeddingValidator(allow_inf=False)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("inf"), 0.3],
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is False
        assert any("Inf" in e for e in errors)

    def test_validate_zero_vector(self):
        validator = ExtendedEmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.0, 0.0, 0.0],
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert is_valid is True
        assert any("zero vector" in w.lower() for w in warnings)

    def test_expected_dimension_validation(self):
        validator = ExtendedEmbeddingValidator(expected_dimension=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=384,
            embedding_vector=[0.1] * 384,
        )
        is_valid, errors, warnings = validator.validate_single(embedding)
        assert "dimension" in str(warnings).lower()

    def test_validate_all_returns_result(self):
        validator = ExtendedEmbeddingValidator()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.1] * 3,
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.2] * 3,
            ),
        ]
        result = validator.validate_all(embeddings)
        assert isinstance(result, ValidationResult)
        assert result.total_embeddings == 2
        assert result.valid_embeddings == 2

    def test_is_normalized_true(self):
        validator = ExtendedEmbeddingValidator()
        normalized = [1.0 / math.sqrt(3)] * 3
        assert validator.is_normalized(normalized) is True

    def test_is_normalized_false(self):
        validator = ExtendedEmbeddingValidator()
        assert validator.is_normalized([0.1] * 3) is False

    def test_normalize_vector(self):
        validator = ExtendedEmbeddingValidator()
        vector = [0.1, 0.2, 0.3]
        normalized = validator.normalize(vector)
        magnitude = math.sqrt(sum(v * v for v in normalized))
        assert abs(magnitude - 1.0) < 1e-6

    def test_compute_cosine_similarity_identical(self):
        validator = ExtendedEmbeddingValidator()
        emb1 = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[1.0, 0.0, 0.0],
        )
        emb2 = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[1.0, 0.0, 0.0],
        )
        similarity = validator.compute_cosine_similarity(emb1, emb2)
        assert similarity == 1.0

    def test_compute_cosine_similarity_orthogonal(self):
        validator = ExtendedEmbeddingValidator()
        emb1 = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[1.0, 0.0, 0.0],
        )
        emb2 = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.0, 1.0, 0.0],
        )
        similarity = validator.compute_cosine_similarity(emb1, emb2)
        assert similarity == 0.0

    def test_check_duplicates_exact(self):
        validator = ExtendedEmbeddingValidator()
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
                embedding_vector=[1.0, 0.0],
            ),
        ]
        for e in embeddings:
            e.checksum = e.compute_checksum()
        duplicates = validator.check_duplicates(embeddings)
        assert len(duplicates) == 1

    def test_check_near_duplicates(self):
        validator = ExtendedEmbeddingValidator(near_duplicate_threshold=0.95, detect_near_duplicates=True)
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
        near_dups = validator.check_near_duplicates(embeddings, threshold=0.99)
        assert len(near_dups) >= 1

    def test_validation_rate(self):
        validator = ExtendedEmbeddingValidator()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.1] * 3,
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[float("nan"), 0.2, 0.3],
            ),
        ]
        result = validator.validate_all(embeddings)
        assert result.validation_rate == 0.5

    def test_duplicate_rate(self):
        validator = ExtendedEmbeddingValidator()
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
                embedding_vector=[1.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=2,
                embedding_vector=[0.5, 0.5],
            ),
        ]
        for e in embeddings:
            e.checksum = e.compute_checksum()
        result = validator.validate_all(embeddings)
        assert result.near_duplicate_count >= 1
        assert len(result.warnings) == 0
