"""Orchestration runner for embedding validation core.

This module provides a validation-only runner without benchmarking,
profiling, or visualization capabilities (Phase 4.1 core only).
"""

from dataclasses import dataclass, field

from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_validator import EmbeddingValidator
from backend.embedding_validation.validation_result import ValidationResult


@dataclass
class ValidationSummary:
    """Summary of validation results for embeddings."""

    is_valid: bool = True
    total_embeddings: int = 0
    valid_embeddings: int = 0
    invalid_embeddings: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ValidationRunner:
    """Orchestrate embedding validation without benchmarking or profiling.

    This runner coordinates the validation pipeline for embeddings,
    checking integrity, consistency, and detecting duplicates.
    """

    def __init__(
        self,
        expected_dimension: int | None = None,
        allow_nan: bool = False,
        allow_inf: bool = False,
        strict_mode: bool = False,
    ):
        self.validator = EmbeddingValidator(
            expected_dimension=expected_dimension,
            allow_nan=allow_nan,
            allow_inf=allow_inf,
            strict_mode=strict_mode,
        )

    def validate(self, embeddings: list[Embedding]) -> ValidationSummary:
        """Run validation on embeddings.

        Args:
            embeddings: List of embeddings to validate.

        Returns:
            ValidationSummary with all validation findings.
        """
        result = self.validator.validate_all(embeddings)

        recommendations = []
        if result.nan_count > 0:
            recommendations.append(
                f"Found {result.nan_count} NaN values. Consider enabling data cleaning."
            )
        if result.inf_count > 0:
            recommendations.append(
                f"Found {result.inf_count} infinite values. Check embedding range."
            )
        if result.zero_vector_count > 0:
            recommendations.append(
                f"Found {result.zero_vector_count} zero vectors. "
                "Review source content for empty chunks."
            )
        if result.duplicate_count > 0:
            recommendations.append(
                f"Found {result.duplicate_count} duplicate embeddings. "
                "Check for duplicate source documents."
            )

        return ValidationSummary(
            is_valid=result.is_valid,
            total_embeddings=result.total_embeddings,
            valid_embeddings=result.valid_embeddings,
            invalid_embeddings=result.invalid_embeddings,
            errors=result.errors,
            warnings=result.warnings,
            recommendations=recommendations,
        )

    def validate_single(self, embedding: Embedding) -> ValidationResult:
        """Validate a single embedding.

        Args:
            embedding: Embedding to validate.

        Returns:
            ValidationResult for the single embedding.
        """
        return self.validator.validate(embedding)
