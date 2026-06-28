"""Base loader for document ingestion."""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.data.models.document import Document, DocumentMetadata, DocumentSource


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of file extensions (e.g., ['.pdf', '.docx']).
        """
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
            DocumentLoadError: If file cannot be accessed.
            FileSizeError: If file exceeds maximum size.
        """
        from backend.core.exceptions import DocumentLoadError, FileSizeError

        path = Path(file_path)

        if not path.exists():
            raise DocumentLoadError(f"File not found: {path}")

        if not path.is_file():
            raise DocumentLoadError(f"Not a file: {path}")

        max_size = self.config.get("max_file_size_mb", 100) * 1024 * 1024
        if path.stat().st_size > max_size:
            raise FileSizeError(
                f"File exceeds maximum size: {path}"
            )

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
        default: str = self.config.get("default_encoding", "utf-8")
        return default

    def build_metadata(
        self,
        title: str | None = None,
        author: str | None = None,
        language: str | None = None,
        created_at: datetime | None = None,
        modified_at: datetime | None = None,
        char_count: int = 0,
        word_count: int = 0,
        page_count: int | None = None,
        tags: list[str] | None = None,
    ) -> DocumentMetadata:
        """Build DocumentMetadata with computed values.

        Args:
            title: Document title.
            author: Document author.
            language: Document language code.
            created_at: Creation timestamp.
            modified_at: Modification timestamp.
            char_count: Character count.
            word_count: Word count.
            page_count: Number of pages.
            tags: Document tags.

        Returns:
            DocumentMetadata instance.
        """
        if language is None:
            language = self.config.get("default_language", "en")

        return DocumentMetadata(
            title=title,
            author=author,
            language=language,
            char_count=char_count,
            word_count=word_count,
            page_count=page_count,
            tags=tags or [],
        )

    def build_source(
        self,
        path: Path,
        checksum: str,
        encoding: str | None = None,
    ) -> DocumentSource:
        """Build DocumentSource for a document.

        Args:
            path: Path to the document.
            checksum: SHA256 checksum.
            encoding: Character encoding detected.

        Returns:
            DocumentSource instance.
        """
        from backend.data.models.document import DocumentSourceType

        return DocumentSource(
            type=DocumentSourceType.FILE,
            path=str(path),
            checksum=checksum,
            size_bytes=path.stat().st_size,
            encoding=encoding or self.detect_encoding(path),
            last_modified=datetime.fromtimestamp(path.stat().st_mtime),
        )
