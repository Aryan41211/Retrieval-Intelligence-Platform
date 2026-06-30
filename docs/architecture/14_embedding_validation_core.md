# Embedding Validation Core Lifecycle

## Overview

The Embedding Validation Core (Phase 4.1) provides a provider-agnostic validation framework that verifies embedding integrity, metadata consistency, and duplicate detection before embeddings are stored in a vector database.

This phase focuses solely on validation logic and does not include benchmarking, profiling, visualization, or vector database operations.

## Validation Workflow

The validation workflow processes embeddings through multiple quality checks:

```
Embedding Input
       │
       ▼
┌─────────────────┐
│  Empty Vector   │  Check for empty/none vectors
│  Detection      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Numeric Check  │  Verify all values are numeric (int/float)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NaN Detection  │  Identify NaN values (errors or warnings based on config)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Inf Detection  │  Identify infinite values (errors or warnings based on config)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Zero Vector    │  Warn on zero vectors (may indicate empty content)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dimension      │  Verify declared dimension matches vector length
│  Validation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Metadata       │  Validate metadata structure and completeness
│  Check          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ID Validation  │  Check for missing/invalid document_id and chunk_id
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Checksum       │  Verify checksum is present for integrity
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Timestamp      │  Validate timestamp is present and timezone-aware
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Duplicate      │  Detect exact duplicates by checksum
│  Detection      │
└─────────────────┘
```

## Module Structure

```
backend/embedding_validation/
├── __init__.py              # Package exports
├── embedding_validator.py   # Core validation logic (EmbeddingValidator)
├── validation_result.py     # Structured validation results
├── validation_runner.py     # Orchestration runner
└── exceptions.py            # Validation-specific exceptions
```

## Validation Checks

| Check | Validation Name | Severity | Description |
|-------|-----------------|----------|-------------|
| Empty vector | `empty_vector` | ERROR | Vector must not be empty |
| Non-numeric | `numeric_values` | ERROR | All values must be int or float |
| NaN values | `nan_values` | ERROR/WARNING | Based on `allow_nan` config |
| Infinite | `inf_values` | ERROR/WARNING | Based on `allow_inf` config |
| Zero vector | `zero_vector` | WARNING | All values near zero |
| Dimension | `dimension` | ERROR/WARNING | Based on mismatch/expected |
| Metadata | `metadata` | ERROR/WARNING | Must be valid dict or have value |
| Document ID | `document_id` | ERROR | Must be valid UUID |
| Chunk ID | `chunk_id` | ERROR | Must be valid UUID |
| Checksum | `checksum` | WARNING | Recommended for integrity |
| Timestamp | `timestamp` | WARNING/ERROR | Should be timezone-aware |

## Configuration

All validation behavior is configurable via `EmbeddingValidationSettings`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `expected_dimension` | int \| None | None | Required embedding dimension |
| `duplicate_tolerance` | float | 0.0 | Threshold for duplicate detection |
| `validation_enabled` | bool | True | Enable/disable validation |
| `strict_mode` | bool | False | Raise exceptions on failures |
| `warning_mode` | bool | False | Treat all failures as warnings |

Environment variables (via pydantic-settings):
- `EMBEDDING_VALIDATION_EXPECTED_DIMENSION`
- `EMBEDDING_VALIDATION_DUPLICATE_TOLERANCE`
- `EMBEDDING_VALIDATION_VALIDATION_ENABLED`
- `EMBEDDING_VALIDATION_STRICT_MODE`
- `EMBEDDING_VALIDATION_WARNING_MODE`

## Usage

### Single Embedding Validation

```python
from backend.embedding_validation import EmbeddingValidator, ValidationStatus

validator = EmbeddingValidator(expected_dimension=1536, strict_mode=True)

embedding = Embedding(
    chunk_id=chunk.chunk_id,
    document_id=chunk.document_id,
    model_name="text-embedding-3-small",
    model_version="1.0",
    embedding_dimension=1536,
    embedding_vector=[0.1] * 1536,
)

result = validator.validate(embedding)

if not result.is_valid:
    for check in result.failed_checks:
        print(f"{check.validation_name}: {check.message}")
        print(f"  Recommendation: {check.recommendation}")
```

### Batch Validation

```python
from backend.embedding_validation import ValidationRunner

runner = ValidationRunner(expected_dimension=1536)
summary = runner.validate(embeddings)

print(f"Validated {summary.total_embeddings} embeddings")
print(f"Pass rate: {summary.valid_embeddings / summary.total_embeddings:.1%}")

if summary.recommendations:
    for rec in summary.recommendations:
        print(f"Recommendation: {rec}")
```

### Configuration-Driven Validation

```python
from backend.configs.settings import get_settings

settings = get_settings()
validator = EmbeddingValidator(
    expected_dimension=settings.embedding_validation.expected_dimension,
    allow_nan=not settings.embedding_validation.strict_mode,
    strict_mode=settings.embedding_validation.strict_mode,
)
```

## Exception Hierarchy

```
EmbeddingError (base)
├── EmbeddingDimensionError
├── EmbeddingValidationError
│   ├── DuplicateEmbeddingError
│   └── InvalidEmbeddingMetadataError
```

- `EmbeddingError`: Base exception for all embedding-related errors
- `EmbeddingDimensionError`: Dimension mismatch or invalid dimension
- `EmbeddingValidationError`: Generic validation failure
- `DuplicateEmbeddingError`: Exact duplicate embeddings detected
- `InvalidEmbeddingMetadataError`: Missing/invalid metadata fields

## Extension Points

### Adding New Validation Checks

Extend `EmbeddingValidator` with additional validation methods:

```python
class CustomValidator(EmbeddingValidator):
    def validate_custom(self, embedding: Embedding, checks: list[ValidationCheckResult]) -> None:
        if some_custom_condition:
            checks.append(
                ValidationCheckResult(
                    validation_name="custom_check",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.ERROR,
                    message="Custom validation failed",
                    recommendation="Fix the custom issue",
                )
            )
```

## Future Extensibility

Phase 4.1 intentionally excludes:

- **Near-duplicate similarity clustering**: Phase 4.2
- **Statistical analysis**: Phase 4.3
- **Benchmarking**: Phase 4.4
- **Profiling**: Phase 4.5
- **Visualization**: Phase 4.6
- **Report generation**: Phase 4.7

These will be added in subsequent phases to maintain clean separation of concerns.