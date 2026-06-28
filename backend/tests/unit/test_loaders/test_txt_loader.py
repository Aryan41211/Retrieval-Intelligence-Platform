"""Unit tests for TXT loader."""

from pathlib import Path

import pytest

from backend.core.exceptions import DocumentLoadError, EmptyDocumentError
from backend.data.loaders.txt_loader import TXTLoader

SHA256_HEX_LENGTH = 64


class TestTXTLoader:
    """Tests for TXTLoader class."""

    def test_load_simple_txt(self, tmp_path: Path):
        """Test loading a simple text file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello, World!\nThis is a test.")

        loader = TXTLoader()
        doc = loader.load(txt_file)

        assert doc.filename == "test.txt"
        assert doc.file_extension == ".txt"
        assert "Hello, World!" in doc.content
        assert doc.metadata.char_count > 0
        assert doc.metadata.word_count > 0
        assert doc.checksum != ""

    def test_load_utf8_with_bom(self, tmp_path: Path):
        """Test loading UTF-8 file with BOM."""
        txt_file = tmp_path / "test_bom.txt"
        txt_file.write_bytes(b"\xef\xbb\xbfHello with BOM")

        loader = TXTLoader()
        doc = loader.load(txt_file)

        assert "Hello with BOM" in doc.content

    def test_empty_file_raises_error(self, tmp_path: Path):
        """Test that empty files raise EmptyDocumentError."""
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("")

        loader = TXTLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(txt_file)

    def test_whitespace_only_file_raises_error(self, tmp_path: Path):
        """Test that whitespace-only files raise EmptyDocumentError."""
        txt_file = tmp_path / "whitespace.txt"
        txt_file.write_text("   \n\n   \n")

        loader = TXTLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(txt_file)

    def test_file_not_found_raises_error(self, tmp_path: Path):
        """Test that missing files raise error."""
        loader = TXTLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(tmp_path / "nonexistent.txt")

    def test_checksum_is_deterministic(self, tmp_path: Path):
        """Test that checksums are deterministic."""
        txt_file = tmp_path / "checksum.txt"
        txt_file.write_text("test content")

        loader = TXTLoader()
        checksum1 = loader.compute_checksum(txt_file)
        checksum2 = loader.compute_checksum(txt_file)

        assert checksum1 == checksum2
        assert len(checksum1) == SHA256_HEX_LENGTH

    def test_supported_extensions(self):
        """Test get_supported_extensions returns correct list."""
        loader = TXTLoader()
        assert loader.get_supported_extensions() == [".txt"]
