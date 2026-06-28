"""DOCX document loader."""

from pathlib import Path

from backend.core.exceptions import DocumentLoadError, EmptyDocumentError
from backend.data.loaders.base_loader import BaseLoader
from backend.data.models.document import Document


class DOCXLoader(BaseLoader):
    """Load DOCX (Word) documents."""

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported extensions.

        Returns:
            List of supported file extensions.
        """
        return [".docx"]

    def load(self, file_path: str | Path) -> Document:
        """Load a DOCX document.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Document object with extracted text.

        Raises:
            DocumentLoadError: If the document cannot be loaded.
            EmptyDocumentError: If the document has no text content.
        """
        path = self.validate_file(file_path)
        checksum = self.compute_checksum(path)
        file_extension = path.suffix.lower()

        if path.stat().st_size == 0:
            raise DocumentLoadError(f"File is empty: {path}")

        try:
            import docx  # python-docx
        except ImportError:
            raise DocumentLoadError(
                "python-docx not installed. Install with: pip install python-docx"
            ) from None

        try:
            doc = docx.Document(str(path))
        except Exception as e:
            raise DocumentLoadError(f"Failed to read DOCX: {e}") from e

        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        content = "\n\n".join(paragraphs)

        if not content.strip():
            raise EmptyDocumentError(f"DOCX contains no text content: {path}")

        title = None
        author = None
        created_at = None

        if doc.core_properties:
            title = doc.core_properties.title or None
            author = doc.core_properties.author or None
            if doc.core_properties.created:
                created_at = doc.core_properties.created

        page_count = None

        metadata = self.build_metadata(
            title=title,
            author=author,
            char_count=len(content),
            word_count=len(content.split()),
            page_count=page_count,
        )

        source = self.build_source(path, checksum)

        document = Document(
            filename=path.name,
            file_extension=file_extension,
            source_path=str(path),
            content=content,
            metadata=metadata,
            checksum=checksum,
            file_size=path.stat().st_size,
            source=source,
        )

        if created_at:
            document = document.model_copy(update={"created_at": created_at})

        return document
