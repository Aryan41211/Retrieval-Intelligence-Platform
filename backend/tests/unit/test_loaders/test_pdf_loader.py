"""Unit tests for PDF loader."""

from pathlib import Path

import pytest

from backend.core.exceptions import DocumentLoadError
from backend.data.loaders.pdf_loader import PDFLoader

SHA256_HEX_LENGTH = 64


class TestPDFLoader:
    """Tests for PDFLoader class."""

    def test_supported_extensions(self):
        """Test get_supported_extensions returns correct list."""
        loader = PDFLoader()
        assert loader.get_supported_extensions() == [".pdf"]

    def test_load_empty_pdf_raises_error(self, tmp_path: Path):
        """Test that empty or corrupted PDF raises DocumentLoadError."""
        # Create a minimal invalid PDF
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"")

        loader = PDFLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(pdf_file)

    def test_checksum_is_deterministic(self, tmp_path: Path):
        """Test that checksums are deterministic for same content."""
        # Create a minimal valid PDF with text
        pdf_file = tmp_path / "checksum.pdf"
        # Minimal PDF with text "Hello" - this is a valid but minimal PDF
        pdf_file.write_bytes(
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \n0000000115 00000 n \ntrailer\n"
            b"<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        )

        loader = PDFLoader()
        checksum1 = loader.compute_checksum(pdf_file)
        checksum2 = loader.compute_checksum(pdf_file)

        assert checksum1 == checksum2
        assert len(checksum1) == SHA256_HEX_LENGTH


class TestPDFLoaderErrors:
    """Tests for PDF loader error handling."""

    def test_file_not_found_raises_error(self, tmp_path: Path):
        """Test that missing files raise error."""
        loader = PDFLoader()

        with pytest.raises(DocumentLoadError):
            loader.load(tmp_path / "nonexistent.pdf")

    def test_unsupported_file_raises_error(self, tmp_path: Path):
        """Test that corrupted PDF raises error."""
        # Create a file that's not a valid PDF
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_bytes(b"This is not a PDF at all")

        loader = PDFLoader()

        # Should raise an error when trying to read
        with pytest.raises(DocumentLoadError):
            loader.load(fake_pdf)
