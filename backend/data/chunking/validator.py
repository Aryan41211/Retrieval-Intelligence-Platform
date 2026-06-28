"""Chunk validation utilities."""

from backend.data.models.chunk import Chunk
from backend.data.models.document import Document


class ChunkValidator:
    """Validates chunk integrity and metadata."""

    def __init__(
        self,
        min_chunk_size: int = 50,
        max_chunk_size: int = 2048,
        max_token_count: int = 1024,
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.max_token_count = max_token_count

    def validate(self, chunk: Chunk, document: Document | None = None) -> list[str]:
        """Validate a single chunk.

        Args:
            chunk: Chunk to validate.
            document: Optional parent document for context checks.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not chunk.text or not chunk.text.strip():
            errors.append("Chunk text is empty")

        if len(chunk.text) < self.min_chunk_size:
            errors.append(f"Chunk size {len(chunk.text)} below minimum {self.min_chunk_size}")

        if len(chunk.text) > self.max_chunk_size:
            errors.append(f"Chunk size {len(chunk.text)} exceeds maximum {self.max_chunk_size}")

        if chunk.metadata.token_count > self.max_token_count:
            errors.append(
                f"Token count {chunk.metadata.token_count} exceeds maximum {self.max_token_count}"
            )

        if chunk.metadata.start_offset >= chunk.metadata.end_offset:
            errors.append("Invalid offsets: start >= end")

        if document and chunk.document_id != document.document_id:
            errors.append("Chunk document_id does not match parent document")

        return errors

    def validate_chunks(
        self,
        chunks: list[Chunk],
        document: Document | None = None,
    ) -> list[tuple[Chunk, list[str]]]:
        """Validate multiple chunks.

        Args:
            chunks: List of chunks to validate.
            document: Optional parent document.

        Returns:
            List of (chunk, errors) tuples for invalid chunks.
        """
        invalid = []
        for chunk in chunks:
            errors = self.validate(chunk, document)
            if errors:
                invalid.append((chunk, errors))
        return invalid

    def is_valid(self, chunk: Chunk, document: Document | None = None) -> bool:
        """Check if a chunk is valid.

        Args:
            chunk: Chunk to check.
            document: Optional parent document.

        Returns:
            True if valid.
        """
        return len(self.validate(chunk, document)) == 0
