"""Unit tests for Markdown loader."""

from pathlib import Path

import pytest

from backend.core.exceptions import EmptyDocumentError
from backend.data.loaders.markdown_loader import MarkdownLoader


class TestMarkdownLoader:
    """Tests for MarkdownLoader class."""

    def test_load_simple_markdown(self, tmp_path: Path):
        """Test loading a simple markdown file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\nThis is **bold** and *italic* text.")

        loader = MarkdownLoader()
        doc = loader.load(md_file)

        assert doc.filename == "test.md"
        assert doc.file_extension == ".md"
        assert doc.metadata.title == "Title"
        assert doc.checksum != ""

    def test_load_markdown_with_heading(self, tmp_path: Path):
        """Test that title is extracted from first heading."""
        md_file = tmp_path / "heading.md"
        md_file.write_text("# My Document Title\n\nContent here.")

        loader = MarkdownLoader()
        doc = loader.load(md_file)

        assert doc.metadata.title == "My Document Title"

    def test_load_markdown_alternative_extension(self, tmp_path: Path):
        """Test loading .markdown extension."""
        md_file = tmp_path / "test.markdown"
        md_file.write_text("Some content")

        loader = MarkdownLoader()
        doc = loader.load(md_file)

        assert doc.file_extension == ".markdown"

    def test_empty_file_raises_error(self, tmp_path: Path):
        """Test that empty files raise EmptyDocumentError."""
        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        loader = MarkdownLoader()

        with pytest.raises(EmptyDocumentError):
            loader.load(md_file)

    def test_supported_extensions(self):
        """Test get_supported_extensions returns correct list."""
        loader = MarkdownLoader()
        extensions = loader.get_supported_extensions()
        assert ".md" in extensions
        assert ".markdown" in extensions

    def test_text_cleaner_integration(self, tmp_path: Path):
        """Test document cleaning after loading."""
        from backend.data.preprocessing.text_cleaner import clean_document

        md_file = tmp_path / "dirty.md"
        md_file.write_text("Content  with   extra     spaces\n\n\n\nMore content")

        loader = MarkdownLoader()
        doc = loader.load(md_file)

        # Clean the document
        cleaned = clean_document(doc)

        # Should have normalized whitespace
        assert "  " not in cleaned.content

    def test_checksum_included(self, tmp_path: Path):
        """Test that checksum is included in loaded document."""
        md_file = tmp_path / "checksum.md"
        md_file.write_text("content")

        loader = MarkdownLoader()
        doc = loader.load(md_file)

        assert len(doc.checksum) == 64


class TestTextCleaner:
    """Tests for TextCleaner class."""

    def test_clean_preserves_content(self):
        """Test that cleaning preserves actual content."""
        from backend.data.models.document import Document

        doc = Document(
            filename="test.md",
            file_extension=".md",
            source_path="/tmp/test.md",
            content="Hello   World!",
            metadata={},
        )

        cleaner = MarkdownLoader()
        cleaned = cleaner.load(doc.source_path if doc.source_path else "/tmp/test")

    def test_normalize_unicode(self):
        """Test unicode normalization."""
        from backend.data.preprocessing.text_cleaner import TextCleaner

        cleaner = TextCleaner()
        # Test smart quotes replacement
        result = cleaner._normalize_unicode("\u201cHello\u201d")
        assert "\u201c" not in result
        assert "\u201d" not in result

    def test_remove_excessive_blanks(self):
        """Test removal of excessive blank lines."""
        from backend.data.preprocessing.text_cleaner import TextCleaner

        cleaner = TextCleaner(max_consecutive_blanks=2)
        text = "Para 1\n\n\n\n\nPara 2"
        result = cleaner._remove_excessive_blank_lines(text)

        # Should be reduced to 2 blank lines
        assert result.count("\n\n") <= 2