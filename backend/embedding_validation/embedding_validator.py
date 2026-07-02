"""Extended embedding validator for comprehensive quality control."""

import math
from datetime import datetime
from uuid import UUID

from backend.data.models.embedding import Embedding
from backend.embedding_validation.validation_result import (
    ValidationCheckResult,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)

# Constants for backward compatibility
ZERO_VECTOR_EPSILON = 1e-10
NORMALIZATION_EPSILON = 1e-6


class EmbeddingValidator:
    """Validates embedding vectors for correctness and quality.

    This class provides provider-agnostic validation for embedding integrity,
    checking for numeric validity, NaN/Inf values, zero vectors, dimension
    consistency, duplicates, and metadata completeness.
    """

    def __init__(
        self,
        expected_dimension: int | None = None,
        allow_nan: bool = False,
        allow_inf: bool = False,
        strict_mode: bool = False,
        nan_tolerance: float = 0.0,
        detect_near_duplicates: bool = True,
        near_duplicate_threshold: float = 0.99,
    ):
        self.expected_dimension = expected_dimension
        self.allow_nan = allow_nan
        self.allow_inf = allow_inf
        self.strict_mode = strict_mode
        self.nan_tolerance = nan_tolerance
        self.detect_near_duplicates = detect_near_duplicates
        self.near_duplicate_threshold = near_duplicate_threshold

    def validate_single(self, embedding: Embedding) -> tuple[bool, list[str], list[str]]:
        """Validate a single embedding (backward compatible interface).

        Args:
            embedding: Embedding to validate.

        Returns:
            Tuple of (is_valid, errors, warnings).
        """
        result = self.validate(embedding)
        return result.is_valid, result.errors, result.warnings

    def validate(self, embedding: Embedding) -> ValidationResult:
        """Validate a single embedding with structured results.

        Args:
            embedding: Embedding to validate.

        Returns:
            ValidationResult with detailed check results.
        """
        checks: list[ValidationCheckResult] = []

        self._check_empty_vector(embedding, checks)
        self._check_numeric_values(embedding, checks)
        self._check_nan_values(embedding, checks)
        self._check_inf_values(embedding, checks)
        self._check_zero_vector(embedding, checks)
        self._check_dimension(embedding, checks)
        self._check_metadata(embedding, checks)
        self._check_document_id(embedding, checks)
        self._check_chunk_id(embedding, checks)
        self._check_checksum(embedding, checks)
        self._check_timestamp(embedding, checks)

        is_valid = all(c.status != ValidationStatus.FAILED for c in checks)

        errors = [c.message for c in checks if c.status == ValidationStatus.FAILED]
        warnings = [
            c.message
            for c in checks
            if c.status == ValidationStatus.WARNING and c.severity == ValidationSeverity.WARNING
        ]

        return ValidationResult(
            is_valid=is_valid,
            total_embeddings=1,
            valid_embeddings=1 if is_valid else 0,
            invalid_embeddings=0 if is_valid else 1,
            checks=checks,
            errors=errors,
            warnings=warnings,
        )

    def validate_all(self, embeddings: list[Embedding]) -> ValidationResult:
        """Validate multiple embeddings comprehensively.

        Args:
            embeddings: List of embeddings to validate.

        Returns:
            ValidationResult with aggregated metrics and individual check results.
        """
        all_checks: list[ValidationCheckResult] = []
        all_errors: list[str] = []
        all_warnings: list[str] = []
        dimensions: set[int] = set()
        nan_count = 0
        inf_count = 0
        zero_vector_count = 0
        normalized_count = 0
        valid_count = 0

        for embedding in embeddings:
            result = self.validate(embedding)
            all_checks.extend(result.checks)

            if result.is_valid:
                valid_count += 1

            for c in result.checks:
                if c.status == ValidationStatus.WARNING:
                    all_warnings.append(c.message)
                if c.validation_name == "nan_values" and c.status == ValidationStatus.WARNING:
                    nan_count += 1
                if c.validation_name == "inf_values" and c.status == ValidationStatus.WARNING:
                    inf_count += 1

            if embedding.embedding_dimension:
                dimensions.add(embedding.embedding_dimension)

            if self._is_zero_vector(embedding.embedding_vector):
                zero_vector_count += 1

            if self.is_normalized(embedding.embedding_vector):
                normalized_count += 1

        duplicate_pairs = self.check_duplicates(embeddings)
        near_duplicate_pairs = (
            self._find_near_duplicates(embeddings) if self.detect_near_duplicates else []
        )

        for d in duplicate_pairs:
            all_checks.append(
                ValidationCheckResult(
                    validation_name="duplicate_detection",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate embeddings found at indices {d[0]} and {d[1]}",
                    recommendation="Review source documents for duplicate content",
                    details={"pair": d},
                )
            )
            if self.strict_mode:
                all_errors.append(f"Duplicate at indices {d[0]} and {d[1]}")

        is_valid = len(all_errors) == 0 and all(
            c.status != ValidationStatus.FAILED
            and (not self.strict_mode or c.severity != ValidationSeverity.ERROR)
            for c in all_checks
        )

        return ValidationResult(
            is_valid=is_valid,
            total_embeddings=len(embeddings),
            valid_embeddings=valid_count,
            invalid_embeddings=len(embeddings) - valid_count,
            checks=all_checks,
            errors=all_errors,
            warnings=all_warnings,
            dimensions=dimensions,
            duplicate_count=len(duplicate_pairs) + len(near_duplicate_pairs),
            near_duplicate_count=len(near_duplicate_pairs) if self.detect_near_duplicates else 0,
            nan_count=nan_count,
            inf_count=inf_count,
            zero_vector_count=zero_vector_count,
            normalized_count=normalized_count,
        )

    def _check_empty_vector(
        self, embedding: Embedding, checks: list[ValidationCheckResult]
    ) -> None:
        """Check for empty embedding vector."""
        if not embedding.embedding_vector:
            checks.append(
                ValidationCheckResult(
                    validation_name="empty_vector",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Embedding vector cannot be empty",
                    recommendation="Ensure embedding provider returns valid vectors",
                )
            )

    def _check_numeric_values(
        self, embedding: Embedding, checks: list[ValidationCheckResult]
    ) -> None:
        """Check for non-numeric values in embedding."""
        if embedding.embedding_vector:
            non_numeric = [
                i
                for i, v in enumerate(embedding.embedding_vector)
                if not isinstance(v, int | float)
            ]
            if non_numeric:
                checks.append(
                    ValidationCheckResult(
                        validation_name="numeric_values",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.ERROR,
                        message=f"Non-numeric values at indices: {non_numeric[:10]}",
                        recommendation="Verify embedding provider returns numeric vectors",
                    )
                )

    def _check_nan_values(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for NaN values in embedding."""
        if embedding.embedding_vector:
            nan_indices = [i for i, v in enumerate(embedding.embedding_vector) if math.isnan(v)]
            if nan_indices:
                status = ValidationStatus.WARNING if self.allow_nan else ValidationStatus.FAILED
                severity = (
                    ValidationSeverity.WARNING if self.allow_nan else ValidationSeverity.ERROR
                )
                checks.append(
                    ValidationCheckResult(
                        validation_name="nan_values",
                        status=status,
                        severity=severity,
                        message=f"NaN values at indices: {nan_indices[:10]}",
                        recommendation="Consider filtering or re-generating embeddings with NaN values",
                    )
                )

    def _check_inf_values(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for infinite values in embedding."""
        if embedding.embedding_vector:
            inf_indices = [i for i, v in enumerate(embedding.embedding_vector) if math.isinf(v)]
            if inf_indices:
                status = ValidationStatus.WARNING if self.allow_inf else ValidationStatus.FAILED
                severity = (
                    ValidationSeverity.WARNING if self.allow_inf else ValidationSeverity.ERROR
                )
                checks.append(
                    ValidationCheckResult(
                        validation_name="inf_values",
                        status=status,
                        severity=severity,
                        message=f"Infinite values at indices: {inf_indices[:10]}",
                        recommendation="Check for division by zero or overflow in embedding generation",
                    )
                )

    def _check_zero_vector(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for zero vectors."""
        if self._is_zero_vector(embedding.embedding_vector):
            checks.append(
                ValidationCheckResult(
                    validation_name="zero_vector",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.WARNING,
                    message="Embedding is a zero vector (all values near zero)",
                    recommendation="Review source text - may indicate empty or homogeneous content",
                )
            )

    def _check_dimension(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check dimension consistency and expected dimension."""
        actual_dim = len(embedding.embedding_vector) if embedding.embedding_vector else 0

        if embedding.embedding_dimension != actual_dim:
            checks.append(
                ValidationCheckResult(
                    validation_name="dimension",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message=f"Dimension mismatch: declared {embedding.embedding_dimension}, actual {actual_dim}",
                    recommendation="Ensure embedding vector length matches declared dimension",
                )
            )
        elif (
            self.expected_dimension is not None
            and embedding.embedding_dimension != self.expected_dimension
        ):
            checks.append(
                ValidationCheckResult(
                    validation_name="dimension",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.WARNING,
                    message=f"Unexpected dimension: expected {self.expected_dimension}, got {embedding.embedding_dimension}",
                    recommendation=f"Verify model configuration matches expected dimension of {self.expected_dimension}",
                )
            )

    def _check_metadata(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check embedding metadata validity."""
        if embedding.metadata is None:
            checks.append(
                ValidationCheckResult(
                    validation_name="metadata",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.INFO,
                    message="Metadata is empty or None",
                    recommendation="Consider adding metadata for traceability",
                )
            )
        elif not isinstance(embedding.metadata, dict):
            checks.append(
                ValidationCheckResult(
                    validation_name="metadata",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Metadata must be a dictionary",
                    recommendation="Provide valid metadata dictionary",
                )
            )

    def _check_document_id(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for missing document ID."""
        try:
            UUID(str(embedding.document_id))
        except (ValueError, TypeError, AttributeError):
            checks.append(
                ValidationCheckResult(
                    validation_name="document_id",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Missing or invalid document ID",
                    recommendation="Ensure embedding is created from a valid chunk with document ID",
                )
            )

    def _check_chunk_id(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for missing chunk ID."""
        try:
            UUID(str(embedding.chunk_id))
        except (ValueError, TypeError, AttributeError):
            checks.append(
                ValidationCheckResult(
                    validation_name="chunk_id",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Missing or invalid chunk ID",
                    recommendation="Ensure embedding is created from a valid chunk with chunk ID",
                )
            )

    def _check_checksum(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check for missing checksum."""
        if not embedding.checksum:
            checks.append(
                ValidationCheckResult(
                    validation_name="checksum",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.INFO,
                    message="Missing checksum for embedding",
                    recommendation="Compute and store checksum for data integrity verification",
                )
            )

    def _check_timestamp(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        """Check embedding timestamp validity."""
        if embedding.generation_timestamp is None:
            checks.append(
                ValidationCheckResult(
                    validation_name="timestamp",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.INFO,
                    message="Missing generation timestamp",
                    recommendation="Add timestamp for traceability and caching",
                )
            )
        elif not isinstance(embedding.generation_timestamp, datetime):
            checks.append(
                ValidationCheckResult(
                    validation_name="timestamp",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid timestamp type",
                    recommendation="Ensure timestamp is a valid datetime object",
                )
            )
        elif embedding.generation_timestamp.tzinfo is None:
            checks.append(
                ValidationCheckResult(
                    validation_name="timestamp",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.WARNING,
                    message="Timestamp lacks timezone info",
                    recommendation="Use timezone-aware datetime for consistency",
                )
            )

    def _is_zero_vector(self, vector: list[float]) -> bool:
        """Check if vector is a zero vector."""
        return all(abs(v) < ZERO_VECTOR_EPSILON for v in vector) if vector else True

    def check_duplicates(self, embeddings: list[Embedding]) -> list[tuple[int, int]]:
        """Find duplicate embeddings by checksum.

        Note: checksum may be unset; in that case we do not treat embeddings as duplicates.
        """
        duplicates: list[tuple[int, int]] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                ci = embeddings[i].checksum
                cj = embeddings[j].checksum
                if ci and cj and ci == cj:
                    duplicates.append((i, j))
        return duplicates

    def _find_near_duplicates(
        self, embeddings: list[Embedding], threshold: float | None = None
    ) -> list[tuple[int, int, float]]:
        """Find near-duplicate embeddings by cosine similarity.

        Args:
            embeddings: List of embeddings to compare.
            threshold: Similarity threshold (defaults to near_duplicate_threshold).

        Returns:
            List of tuples (index_i, index_j, similarity_score).
        """
        threshold = threshold or self.near_duplicate_threshold
        if threshold <= 0 or threshold >= 1:
            raise ValueError("Threshold must be between 0 and 1 (exclusive)")

        near_duplicates: list[tuple[int, int, float]] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                if len(embeddings[i].embedding_vector) != len(embeddings[j].embedding_vector):
                    continue
                try:
                    similarity = self.compute_cosine_similarity(embeddings[i], embeddings[j])
                    if similarity >= threshold:
                        near_duplicates.append((i, j, similarity))
                except ValueError:
                    continue

        return near_duplicates

    def check_near_duplicates(
        self, embeddings: list[Embedding], threshold: float | None = None
    ) -> list[tuple[int, int, float]]:
        """Find near-duplicate embeddings by cosine similarity.

        Args:
            embeddings: List of embeddings to compare.
            threshold: Similarity threshold (defaults to near_duplicate_threshold).

        Returns:
            List of tuples (index_i, index_j, similarity_score).
        """
        return self._find_near_duplicates(embeddings, threshold)

    def compute_cosine_similarity(self, embedding1: Embedding, embedding2: Embedding) -> float:
        """Compute cosine similarity between two embeddings."""
        if len(embedding1.embedding_vector) != len(embedding2.embedding_vector):
            raise ValueError(
                f"Cannot compute similarity: dimension mismatch "
                f"{len(embedding1.embedding_vector)} vs {len(embedding2.embedding_vector)}"
            )

        vec1 = embedding1.embedding_vector
        vec2 = embedding2.embedding_vector

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def is_normalized(self, vector: list[float]) -> bool:
        """Check if vector is normalized (unit magnitude)."""
        if not vector:
            return False
        magnitude = math.sqrt(sum(v * v for v in vector))
        return abs(magnitude - 1.0) < NORMALIZATION_EPSILON

    def normalize(self, vector: list[float]) -> list[float]:
        """Normalize vector to unit magnitude."""
        if not vector:
            return vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0:
            return vector
        return [v / magnitude for v in vector]


# Backward compatibility alias
ExtendedEmbeddingValidator = EmbeddingValidator