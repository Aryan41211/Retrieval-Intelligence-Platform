"""Custom exceptions for vector store operations."""


class VectorStoreError(Exception):
    """Base exception for vector store errors."""

    def __init__(self, message: str = "Vector store operation failed"):
        self.message = message
        super().__init__(self.message)


class IndexCreationError(VectorStoreError):
    """Raised when index creation fails."""

    def __init__(self, message: str = "Failed to create vector index"):
        super().__init__(message)


class IndexLoadError(VectorStoreError):
    """Raised when index loading fails."""

    def __init__(self, message: str = "Failed to load vector index"):
        super().__init__(message)


class IndexSaveError(VectorStoreError):
    """Raised when index saving fails."""

    def __init__(self, message: str = "Failed to save vector index"):
        super().__init__(message)


class IndexCorruptionError(VectorStoreError):
    """Raised when index corruption is detected."""

    def __init__(self, message: str = "Vector index is corrupted"):
        super().__init__(message)


class EmbeddingNotFoundError(VectorStoreError):
    """Raised when an embedding is not found in the index."""

    def __init__(self, embedding_id: str):
        self.embedding_id = embedding_id
        super().__init__(f"Embedding not found: {embedding_id}")


class MetadataError(VectorStoreError):
    """Raised when metadata operations fail."""

    def __init__(self, message: str = "Metadata operation failed"):
        super().__init__(message)