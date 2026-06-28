"""PDF document loader."""

from pathlib import Path

from backend.core.exceptions import EmptyDocumentError
from backend.data.loaders.base_loader import BaseLoader
from backend.data.models.document import Document


class PDFLoader(BaseLoader):
    """Load PDF documents using pypdf."""

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported extensions.

        Returns:
            List of supported file extensions.
        """
        return [".pdf"]

    def load(self, file_path: str | Path) -> Document:
        """Load a PDF document.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Document object with extracted text.

        Raises:
            DocumentLoadError: If the PDF cannot be loaded.
            EmptyDocumentError: If the PDF has no text content.
        """
        from backend.core.exceptions import DocumentLoadError

        path = self.validate_file(file_path)
        checksum = self.compute_checksum(path)
        file_extension = path.suffix.lower()

        # Check for empty file
        if path.stat().st_size == 0:
            raise DocumentLoadError(f"File is empty: {path}")

        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
        except Exception as e:
            raise DocumentLoadError(f"Failed to read PDF: {e}") from e

        # Extract text from all pages
        pages_text = []
        for _page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                pages_text.append(text)
            except Exception:
                continue

        content = "\n\n".join(pages_text)

        if not content.strip():
            raise EmptyDocumentError(f"PDF contains no extractable text: {path}")

        page_count = len(reader.pages)

        title = None
        if reader.metadata and hasattr(reader.metadata, "title"):
            title = reader.metadata.title

        author = None
        if reader.metadata and hasattr(reader.metadata, "author"):
            author = reader.metadata.author

        metadata = self.build_metadata(
            title=title,
            author=author,
            char_count=len(content),
            word_count=len(content.split()),
            page_count=page_count,
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
