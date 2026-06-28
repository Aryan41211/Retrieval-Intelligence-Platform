"""Unit tests for Recursive Chunker."""

from pathlib import Path

from backend.data.chunking.recursive_chunker import RecursiveChunker
from backend.data.models.document import Document


class TestRecursiveChunker:
    """Tests for RecursiveChunker class."""

    def test_chunk_small_document(self, tmp_path: Path):
        """Test chunking a small document returns single chunk."""
        doc_file = tmp_path / "test.txt"
        doc_file.write_text("Hello, World!")

        doc = Document(
            filename="test.txt",
            file_extension=".txt",
            source_path=str(doc_file),
            content="Hello, World!",
        )

        chunker = RecursiveChunker()
        chunks = chunker.chunk(doc)

        assert len(chunks) == 1
        assert chunks[0].text == "Hello, World!"

    def test_strategy_returns_recursive(self):
        """Test strategy property returns RECURSIVE."""
        chunker = RecursiveChunker()
        assert chunker.strategy.value == "recursive"

    def test_metadata_preserved(self, tmp_path: Path):
        """Test document metadata is preserved in chunks."""
        doc_file = tmp_path / "meta.txt"
        doc_file.write_text("Test content for metadata.")

        doc = Document(
            filename="meta.txt",
            file_extension=".txt",
            source_path=str(doc_file),
            content="Test content for metadata.",
        )

        chunker = RecursiveChunker()
        chunks = chunker.chunk(doc)

        assert chunks[0].document_id == doc.document_id
        assert chunks[0].metadata.source_file == str(doc_file)
        assert chunks[0].metadata.chunking_strategy.value == "recursive"
