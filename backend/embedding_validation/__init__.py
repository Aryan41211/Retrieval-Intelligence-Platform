"""Embedding validation core framework for the Retrieval Intelligence Platform.

This package provides:
- Embedding validation for quality control
- Structured validation results
- Duplicate detection for data integrity
- Orchestration runner for validation pipeline
"""

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
from backend.embedding_validation.validation_runner import ValidationRunner

# Backward compatibility alias
ExtendedEmbeddingValidator = EmbeddingValidator

__all__ = [
    "EmbeddingValidator",
    "ExtendedEmbeddingValidator",
    "ValidationRunner",
    "ValidationResult",
    "ValidationCheckResult",
    "ValidationStatus",
    "ValidationSeverity",
    "DuplicateEmbeddingError",
    "InvalidEmbeddingMetadataError",
]