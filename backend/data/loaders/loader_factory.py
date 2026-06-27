"""Factory for creating document loaders."""

from backend.core.exceptions import UnsupportedDocumentTypeError
from backend.data.loaders.base_loader import BaseLoader
from backend.data.loaders.docx_loader import DOCXLoader
from backend.data.loaders.markdown_loader import MarkdownLoader
from backend.data.loaders.pdf_loader import PDFLoader
from backend.data.loaders.txt_loader import TXTLoader
from backend.data.models.document import Document


class LoaderFactory:
    """Factory for creating appropriate document loader."""

    # Registry of loaders by extension
    _loaders: dict[str, type[BaseLoader]] = {
        ".pdf": PDFLoader,
        ".docx": DOCXLoader,
        ".txt": TXTLoader,
        ".md": MarkdownLoader,
        ".markdown": MarkdownLoader,
    }

    @classmethod
    def get_loader(cls, extension: str) -> BaseLoader:
        """Get a loader instance for the given file extension.

        Args:
            extension: File extension (with leading dot, e.g., '.pdf').

        Returns:
            Loader instance.

        Raises:
            UnsupportedDocumentTypeError: If no loader exists for the extension.
        """
        extension = extension.lower()
        if extension not in cls._loaders:
            raise UnsupportedDocumentTypeError(
                f"No loader for extension: {extension}. " f"Supported: {list(cls._loaders.keys())}"
            )

        return cls._loaders[extension]()

    @classmethod
    def register_loader(cls, extension: str, loader_class: type[BaseLoader]) -> None:
        """Register a new loader for an extension.

        Args:
            extension: File extension (with leading dot).
            loader_class: Loader class to register.
        """
        cls._loaders[extension.lower()] = loader_class

    @classmethod
    def load_document(
        cls,
        file_path: str,
        encoding: str | None = None,
    ) -> Document:
        """Load a document from file path.

        Args:
            file_path: Path to the document.
            encoding: Optional encoding override.

        Returns:
            Loaded Document.

        Raises:
            DocumentLoadError: If loading fails.
        """
        from pathlib import Path

        path = Path(file_path)
        extension = path.suffix.lower()

        loader = cls.get_loader(extension)
        if encoding:
            loader.config["default_encoding"] = encoding

        return loader.load(file_path)

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get all supported file extensions.

        Returns:
            List of supported extensions.
        """
        return list(cls._loaders.keys())
