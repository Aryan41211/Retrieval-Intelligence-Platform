"""Embedding validation specific exceptions."""

from typing import Any

from backend.data.embeddings.base_embedding_provider import EmbeddingError


class DuplicateEmbeddingError(EmbeddingError):
    """Raised when duplicate embeddings are detected.

    This error is used when exact duplicates are found and strict mode
    is enabled, or when the duplicate tolerance threshold is exceeded.
    """

    code = "DUPLICATE_EMBEDDING_ERROR"

    def __init__(
        self,
        message: str,
        duplicate_pairs: list[tuple[int, int]] | None = None,
        details: dict[str, Any] | None = None,
    ):
        final_details = details or {}
        if duplicate_pairs:
            final_details["duplicate_pairs"] = duplicate_pairs
        super().__init__(message, final_details)


class InvalidEmbeddingMetadataError(EmbeddingError):
    """Raised when embedding metadata is invalid or malformed.

    This includes validation failures for:
    - Missing or invalid document IDs
    - Missing or invalid chunk IDs
    - Missing checksums
    - Invalid timestamps
    """

    code = "INVALID_EMBEDDING_METADATA_ERROR"

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        expected: Any = None,
        actual: Any = None,
        details: dict[str, Any] | None = None,
    ):
        final_details = details or {}
        if field_name:
            final_details["field_name"] = field_name
        if expected is not None:
            final_details["expected"] = str(expected)
        if actual is not None:
            final_details["actual"] = str(actual)
        super().__init__(message, final_details)
