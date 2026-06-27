"""Plain text document loader."""

from pathlib import Path
from typing import Any, Optional

from backend.core.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
)
from backend.data.models.document import Document
from backend.data.loaders.base_loader import BaseLoader


class TXTLoader(BaseLoader):
    """Load plain text documents."""

    def get_supported_extensions(self) -> list[str]:
        return [".txt"]

    def load(self, file_path: str | Path) -> Document:
        """Load a plain text document.

        Args:
            file_path: Path to the text file.

        Returns:
            Document object with text content.

        Raises:
            DocumentLoadError: If the file cannot be read.
            EmptyDocumentError: If the file is empty.
        """
        path = self.validate_file(file_path)
        checksum = self.compute_checksum(path)
        file_extension = path.suffix.lower()

        encoding = self.detect_encoding(path)

        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try common fallback encodings
            for fallback in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(path, "r", encoding=fallback) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise DocumentLoadError(f"Could not decode file with any encoding: {path}")

        if not content.strip():
            raise EmptyDocumentError(f"File is empty or contains only whitespace: {path}")

        metadata = self.build_metadata(
            char_count=len(content),
            word_count=len(content.split()),
        )

        source = self.build_source(path, checksum)

        return Document(
            filename=path.name,
            file_extension=file_extension,
            source_path=str(path),
            content=content,
            metadata=metadata,
            checksum=checksum,
            file_size=path.stat().st_size,
            source=source,
        )