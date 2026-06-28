"""Unit tests for DOCX loader."""

from pathlib import Path

import pytest

from backend.core.exceptions import DocumentLoadError, EmptyDocumentError
from backend.data.loaders.docx_loader import DOCXLoader

HAS_DOCX = True
try:
    import docx  # noqa: F401
except ImportError:
    HAS_DOCX = False


class TestDOCXLoader:
    """Tests for DOCXLoader class."""

    def test_supported_extensions(self):
        """Test get_supported_extensions returns correct list."""
        loader = DOCXLoader()
        assert loader.get_supported_extensions() == [".docx"]

    @pytest.mark.skipif(not HAS_DOCX, reason="python-docx not installed")
    def test_load_empty_docx_raises_error(self, tmp_path: Path):
        """Test that empty DOCX raises EmptyDocumentError."""
        import zipfile

        docx_file = tmp_path / "empty.docx"
        with zipfile.ZipFile(docx_file, "w") as zf:
            zf.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types/>')
            zf.writestr("word/document.xml", b'<?xml version="1.0"?><w:document/>')

        loader = DOCXLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(docx_file)

    def test_file_not_found_raises_error(self, tmp_path: Path):
        """Test that missing files raise error."""
        loader = DOCXLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(tmp_path / "nonexistent.docx")


class TestDOCXLoaderErrors:
    """Tests for DOCX loader error handling."""

    def test_corrupted_docx_raises_error(self, tmp_path: Path):
        """Test that corrupted DOCX raises error."""
        fake_docx = tmp_path / "fake.docx"
        fake_docx.write_bytes(b"This is not a DOCX file")

        loader = DOCXLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(fake_docx)
