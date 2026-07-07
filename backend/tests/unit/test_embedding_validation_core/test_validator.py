"""Tests for embedding validation core modules."""

import math
from uuid import uuid4

from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_validator import EmbeddingValidator
from backend.embedding_validation.exceptions import (
    DuplicateEmbeddingError,
    InvalidEmbeddingMetadataError,
)
from backend.embedding_validation.validation_result import (
    ValidationCheckResult,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from backend.embedding_validation.validation_runner import ValidationRunner, ValidationSummary


class TestValidationCheckResult:
    """Tests for ValidationCheckResult dataclass."""

    def test_create_check_result(self):
        check = ValidationCheckResult(
            validation_name="test_check",
            status=ValidationStatus.FAILED,
            severity=ValidationSeverity.ERROR,
            message="Test error message",
            recommendation="Test recommendation",
        )
        assert check.validation_name == "test_check"
        assert check.status == ValidationStatus.FAILED
        assert check.severity == ValidationSeverity.ERROR
        assert check.message == "Test error message"
        assert check.recommendation == "Test recommendation"
        assert check.details is None

    def test_check_result_with_details(self):
        check = ValidationCheckResult(
            validation_name="dimension",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
            message="Unexpected dimension",
            details={"expected": 1536, "actual": 384},
        )
        assert check.details == {"expected": 1536, "actual": 384}


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_initial_state(self):
        result = ValidationResult()
        assert result.is_valid is True
        assert result.total_embeddings == 0
        assert result.valid_embeddings == 0
        assert result.checks == []

    def test_validation_rate_no_embeddings(self):
        result = ValidationResult()
        assert result.validation_rate == 0.0

    def test_validation_rate_with_embeddings(self):
        result = ValidationResult(total_embeddings=10, valid_embeddings=8)
        assert result.validation_rate == 0.8

    def test_add_check_passed(self):
        result = ValidationResult()
        check = ValidationCheckResult(
            validation_name="test",
            status=ValidationStatus.PASSED,
            severity=ValidationSeverity.INFO,
            message="Passed check",
        )
        result.add_check(check)
        assert result.is_valid is True
        assert check in result.checks

    def test_add_check_failed(self):
        result = ValidationResult()
        check = ValidationCheckResult(
            validation_name="test",
            status=ValidationStatus.FAILED,
            severity=ValidationSeverity.ERROR,
            message="Failed check",
        )
        result.add_check(check)
        assert result.is_valid is False
        assert "Failed check" in result.errors

    def test_add_check_warning(self):
        result = ValidationResult()
        check = ValidationCheckResult(
            validation_name="test",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
            message="Warning check",
        )
        result.add_check(check)
        assert result.is_valid is True
        assert "Warning check" in result.warnings


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
        result = validator.validate(embedding)
        assert result.is_valid is True
        assert len(result.errors) == 0

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
        result = validator.validate(embedding)
        assert result.is_valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_validate_nan_values_disallowed(self):
        validator = EmbeddingValidator(allow_nan=False)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("nan"), 0.3],
        )
        result = validator.validate(embedding)
        assert result.is_valid is False
        assert any("nan" in c.validation_name for c in result.failed_checks)

    def test_validate_nan_values_allowed(self):
        validator = EmbeddingValidator(allow_nan=True)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("nan"), 0.3],
        )
        result = validator.validate(embedding)
        assert result.is_valid is True
        assert any(
            c.severity == ValidationSeverity.WARNING
            for c in result.warning_checks
            if c.validation_name == "nan_values"
        )

    def test_validate_inf_values_disallowed(self):
        validator = EmbeddingValidator(allow_inf=False)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1, float("inf"), 0.3],
        )
        result = validator.validate(embedding)
        assert result.is_valid is False
        assert any("inf" in c.validation_name for c in result.failed_checks)

    def test_validate_zero_vector(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.0, 0.0, 0.0],
        )
        result = validator.validate(embedding)
        assert result.is_valid is True
        assert any(c.validation_name == "zero_vector" for c in result.warning_checks)

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
        result = validator.validate(embedding)
        assert result.is_valid is False
        assert any(c.validation_name == "dimension" for c in result.failed_checks)

    def test_validate_expected_dimension_warning(self):
        validator = EmbeddingValidator(expected_dimension=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=384,
            embedding_vector=[0.1] * 384,
        )
        result = validator.validate(embedding)
        assert any(
            c.validation_name == "dimension" and c.severity == ValidationSeverity.WARNING
            for c in result.warning_checks
        )

    def test_validate_missing_checksum(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1] * 3,
            checksum="",
        )
        result = validator.validate(embedding)
        assert any(c.validation_name == "checksum" for c in result.warning_checks)

    def test_validate_missing_timestamp(self):
        validator = EmbeddingValidator()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1] * 3,
        )
        embedding.generation_timestamp = None  # type: ignore
        result = validator.validate(embedding)
        assert any(c.validation_name == "timestamp" for c in result.warning_checks)

    def test_validate_all_multiple_embeddings(self):
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
        result = validator.validate_all(embeddings)
        assert result.total_embeddings == 2
        assert result.valid_embeddings == 2
        assert result.validation_rate == 1.0

    def test_check_duplicates_same_checksum(self):
        validator = EmbeddingValidator()
        vector = [1.0, 0.0, 0.0]
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
                checksum="same-checksum",
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
                checksum="same-checksum",
            ),
        ]
        duplicates = validator.check_duplicates(embeddings)
        assert len(duplicates) == 1

    def test_is_normalized_true(self):
        validator = EmbeddingValidator()
        normalized = [1.0 / math.sqrt(3)] * 3
        assert validator.is_normalized(normalized) is True

    def test_is_normalized_false(self):
        validator = EmbeddingValidator()
        assert validator.is_normalized([0.1] * 3) is False

    def test_normalize(self):
        validator = EmbeddingValidator()
        vector = [0.1, 0.2, 0.3]
        normalized = validator.normalize(vector)
        magnitude = math.sqrt(sum(v * v for v in normalized))
        assert abs(magnitude - 1.0) < 1e-6


class TestValidationRunner:
    """Tests for ValidationRunner class."""

    def test_validate_returns_summary(self):
        runner = ValidationRunner()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.1] * 3,
            ),
        ]
        summary = runner.validate(embeddings)
        assert isinstance(summary, ValidationSummary)
        assert summary.is_valid is True
        assert summary.total_embeddings == 1

    def test_validate_expected_dimension_warning(self):
        runner = ValidationRunner(expected_dimension=100)
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=384,
                embedding_vector=[0.1] * 384,
            ),
        ]
        result = runner.validator.validate_all(embeddings)
        assert any(c.validation_name == "dimension" for c in result.warning_checks)

    def test_validate_single_returns_result(self):
        runner = ValidationRunner()
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=3,
            embedding_vector=[0.1] * 3,
        )
        result = runner.validate_single(embedding)
        assert isinstance(result, ValidationResult)

    def test_strict_mode_duplicates(self):
        runner = ValidationRunner(strict_mode=True)
        vector = [1.0, 0.0, 0.0]
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
                checksum="same-checksum",
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
                checksum="same-checksum",
            ),
        ]
        summary = runner.validate(embeddings)
        assert len(summary.errors) > 0


class TestDuplicateEmbeddingError:
    """Tests for DuplicateEmbeddingError exception."""

    def test_exception_creation(self):
        error = DuplicateEmbeddingError(
            "Duplicate embeddings detected",
            duplicate_pairs=[(0, 1), (2, 3)],
        )
        assert error.code == "DUPLICATE_EMBEDDING_ERROR"
        assert "Duplicate embeddings" in str(error)
        assert error.details is not None
        assert error.details["duplicate_pairs"] == [(0, 1), (2, 3)]


class TestInvalidEmbeddingMetadataError:
    """Tests for InvalidEmbeddingMetadataError exception."""

    def test_exception_creation(self):
        error = InvalidEmbeddingMetadataError(
            "Invalid metadata",
            field_name="document_id",
            expected="UUID",
            actual="None",
        )
        assert error.code == "INVALID_EMBEDDING_METADATA_ERROR"
        assert "Invalid metadata" in str(error)
        assert error.details is not None
        assert error.details["field_name"] == "document_id"
