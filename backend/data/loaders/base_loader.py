"""Base loader for document ingestion."""

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        ...

    @abstractmethod
    def load(self, file_path: str | Path):
        """Load a document from the given file path.

        Args:
            file_path: Path to the document file.

        Returns:
            Document object with content and metadata.

        Raises:
            DocumentLoadError: If the document cannot be loaded.
            UnsupportedDocumentTypeError: If the file type is not supported.
            EmptyDocumentError: If the document has no content.
        """
        ...

    def validate_file(self, file_path: str | Path) -> Path:
        """Validate file exists and is within size limits.

        Args:
            file_path: Path to validate.

        Returns:
            Path object for the file.

        Raises:
            ValidationError: If file validation fails.
        """
        path = Path(file_path)

        if not path.exists():
            raise ValueError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        max_size = self.config.get("max_file_size_mb", 100) * 1024 * 1024
        file_size = path.stat().st_size

        if file_size == 0:
            raise ValueError(f"File is empty: {path}")

        if file_size > max_size:
            raise ValueError(f"File exceeds maximum size ({file_size} > {max_size} bytes): {path}")

        return path

    def compute_checksum(self, file_path: str | Path) -> str:
        """Compute SHA256 checksum of file.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal checksum string.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_content_hash(self, content: str) -> str:
        """Compute hash of document content.

        Args:
            content: Document text content.

        Returns:
            SHA256 hash of content.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def detect_encoding(self, file_path: str | Path) -> str:
        """Detect file encoding (fallback to default).

        Args:
            file_path: Path to the file.

        Returns:
            Detected encoding name.
        """
        return self.config.get("default_encoding", "utf-8")
