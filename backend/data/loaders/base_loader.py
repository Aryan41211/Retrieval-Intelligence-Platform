"""Base loader for document ingestion."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.core.exceptions import (
    DocumentLoadError,
    EncodingError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
    ValidationError,
)
from backend.data.models.document import (
    Document,
    DocumentMetadata,
    DocumentSource,
    DocumentSourceType,
)


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        ...

    @abstractmethod
    def load(self, file_path: str | Path) -> Document:
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
            raise ValidationError(f"File not found: {path}")

        if not path.is_file():
            raise ValidationError(f"Not a file: {path}")

        max_size = self.config.get("max_file_size_mb", 100) * 1024 * 1024
        file_size = path.stat().st_size

        if file_size == 0:
            raise EmptyDocumentError(f"File is empty: {path}")

        if file_size > max_size:
            raise ValidationError(
                f"File exceeds maximum size ({file_size} > {max_size} bytes): {path}"
            )

        return path

    def compute_checksum(self, file_path: str | Path) -> str:
        """Compute SHA256 checksum of file.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal checksum string.
        """
        import hashlib

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
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def detect_encoding(self, file_path: str | Path) -> str:
        """Detect file encoding (fallback to default).

        Args:
            file_path: Path to the file.

        Returns:
            Detected encoding name.
        """
        default = self.config.get("default_encoding", "utf-8")
        return default

    def build_source(self, path: Path, checksum: str) -> DocumentSource:
        """Build DocumentSource from file path.

        Args:
            path: File path.
            checksum: File checksum.

        Returns:
            DocumentSource object.
        """
        return DocumentSource(
            type=DocumentSourceType.FILE,
            path=str(path),
            checksum=checksum,
            size_bytes=path.stat().st_size,
            last_modified=datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None,
        )

    def build_metadata(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        language: Optional[str] = None,
        page_count: Optional[int] = None,
        char_count: int = 0,
        word_count: int = 0,
    ) -> DocumentMetadata:
        """Build DocumentMetadata object.

        Args:
            title: Document title.
            author: Document author.
            language: Detected language.
            page_count: Number of pages.
            char_count: Character count.
            word_count: Word count.

        Returns:
            DocumentMetadata object.
        """
        return DocumentMetadata(
            title=title,
            author=author,
            language=language or self.config.get("default_language", "en"),
            char_count=char_count,
            word_count=word_count,
            page_count=page_count,
        )
