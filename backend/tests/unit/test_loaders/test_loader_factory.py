"""Unit tests for loader factory."""

from pathlib import Path

import pytest

from backend.core.exceptions import UnsupportedDocumentTypeError
from backend.data.loaders.loader_factory import LoaderFactory


class TestLoaderFactory:
    """Tests for LoaderFactory class."""

    def test_get_loader_for_txt(self):
        """Test getting loader for txt extension."""
        loader = LoaderFactory.get_loader(".txt")
        assert loader.__class__.__name__ == "TXTLoader"

    def test_get_loader_for_md(self):
        """Test getting loader for markdown."""
        loader = LoaderFactory.get_loader(".md")
        from backend.data.loaders.markdown_loader import MarkdownLoader
        assert isinstance(loader, MarkdownLoader)

    def test_get_loader_for_docx(self):
        """Test getting loader for docx."""
        loader = LoaderFactory.get_loader(".docx")
        from backend.data.loaders.docx_loader import DOCXLoader
        assert isinstance(loader, DOCXLoader)

    def test_get_loader_for_pdf(self):
        """Test getting loader for pdf."""
        loader = LoaderFactory.get_loader(".pdf")
        from backend.data.loaders.pdf_loader import PDFLoader
        assert isinstance(loader, PDFLoader)

    def test_unsupported_extension_raises_error(self):
        """Test that unsupported extensions raise errors."""
        with pytest.raises(UnsupportedDocumentTypeError):
            LoaderFactory.get_loader(".xyz")

    def test_get_supported_extensions(self):
        """Test getting all supported extensions."""
        extensions = LoaderFactory.get_supported_extensions()
        assert ".txt" in extensions
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".md" in extensions

    def test_case_insensitive_extension(self):
        """Test that extensions are case-insensitive."""
        loader = LoaderFactory.get_loader(".PDF")
        from backend.data.loaders.pdf_loader import PDFLoader
        assert isinstance(loader, PDFLoader)