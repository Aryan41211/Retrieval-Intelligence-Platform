"""Tests for embedding validator."""

import math

import pytest

from backend.data.embeddings.embedding_validator import (
    EmbeddingDimensionError,
    EmbeddingValidationError,
    EmbeddingValidator,
)
from backend.data.models.embedding import Embedding


class TestEmbeddingValidator:
    """Tests for EmbeddingValidator class."""

    def test_validate_valid_embedding(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        validator.validate(embedding)

    def test_validate_empty_vector(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=0,
            embedding_vector=[],
        )
        with pytest.raises(EmbeddingValidationError, match="empty"):
            validator.validate(embedding)

    def test_validate_nan_values(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("nan"), 0.3],
        )
        with pytest.raises(EmbeddingValidationError, match="NaN"):
            validator.validate(embedding)

    def test_validate_inf_values(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("inf"), 0.3],
        )
        with pytest.raises(EmbeddingValidationError, match="Inf"):
            validator.validate(embedding)

    def test_validate_dimension_mismatch(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=5,
            embedding_vector=[0.1] * 3,
        )
        with pytest.raises(EmbeddingDimensionError, match="mismatch"):
            validator.validate(embedding)

    def test_expected_dimension_validation(self):
        validator = EmbeddingValidator(expected_dimension=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=384,
            embedding_vector=[0.1] * 384,
        )
        with pytest.raises(EmbeddingDimensionError, match="Unexpected dimension"):
            validator.validate(embedding)

    def test_validate_all_embeddings(self):
        validator = EmbeddingValidator()
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
        errors = validator.validate_all(embeddings)
        assert errors == []

    def test_is_normalized(self):
        validator = EmbeddingValidator()
        normalized = [1.0 / math.sqrt(3)] * 3
        assert validator.is_normalized(normalized) is True
        assert validator.is_normalized([0.1] * 3) is False

    def test_normalize(self):
        validator = EmbeddingValidator()
        vector = [0.1, 0.2, 0.3]
        normalized = validator.normalize(vector)
        magnitude = math.sqrt(sum(v * v for v in normalized))
        assert abs(magnitude - 1.0) < 1e-6

    def test_compute_similarity(self):
        validator = EmbeddingValidator()
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
        emb3 = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.0, 1.0, 0.0],
        )
        assert validator.compute_similarity(emb1, emb2) == 1.0
        assert validator.compute_similarity(emb1, emb3) == 0.0

    def test_check_duplicates(self):
        validator = EmbeddingValidator()
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


def uuid4():
    from uuid import uuid4 as _uuid4

    return _uuid4()
