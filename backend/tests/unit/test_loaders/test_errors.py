"""Unit tests for error handling in document loaders."""

from pathlib import Path

import pytest

from backend.core.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
    FileSizeError,
    UnsupportedDocumentTypeError,
)
from backend.data.loaders.loader_factory import LoaderFactory
from backend.data.loaders.txt_loader import TXTLoader


class TestUnsupportedExtension:
    """Tests for unsupported document type handling."""

    def test_unsupported_extension_raises_error(self):
        """Test that unsupported extensions raise UnsupportedDocumentTypeError."""
        with pytest.raises(UnsupportedDocumentTypeError) as exc_info:
            LoaderFactory.get_loader(".xyz")

        assert "No loader for extension" in str(exc_info.value)

    def test_unsupported_extension_raises_error_uppercase(self):
        """Test that uppercase unsupported extensions raise error."""
        with pytest.raises(UnsupportedDocumentTypeError):
            LoaderFactory.get_loader(".XYZ")


class TestEmptyDocument:
    """Tests for empty document handling."""

    def test_empty_txt_raises_error(self, tmp_path: Path):
        """Test that empty text file raises EmptyDocumentError."""
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("")

        loader = TXTLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(txt_file)

    def test_whitespace_only_raises_error(self, tmp_path: Path):
        """Test that whitespace-only file raises EmptyDocumentError."""
        txt_file = tmp_path / "whitespace.txt"
        txt_file.write_text("   \n\n\t\n   ")

        loader = TXTLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(txt_file)


class TestLargeDocument:
    """Tests for large document validation."""

    def test_large_file_exceeds_limit(self, tmp_path: Path):
        """Test that files exceeding size limit raise FileSizeError."""
        loader = TXTLoader(config={"max_file_size_mb": 0.0001})  # ~100 bytes

        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1024)

        with pytest.raises(FileSizeError) as exc_info:
            loader.load(large_file)

        assert "exceeds maximum size" in str(exc_info.value)

    def test_large_file_with_default_limit(self, tmp_path: Path):
        """Test that default limit allows reasonable files."""
        loader = TXTLoader()
        normal_file = tmp_path / "normal.txt"
        normal_file.write_text("Hello, World!")

        doc = loader.load(normal_file)
        assert doc.content == "Hello, World!"


class TestCorruptedDocument:
    """Tests for corrupted document handling."""

    def test_missing_file_raises_error(self, tmp_path: Path):
        """Test that missing files raise DocumentLoadError."""
        loader = TXTLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(tmp_path / "nonexistent.txt")
