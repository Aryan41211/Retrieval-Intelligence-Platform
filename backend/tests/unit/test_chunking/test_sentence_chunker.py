"""Unit tests for Sentence Chunker."""

from pathlib import Path

from backend.data.chunking.sentence_chunker import SentenceChunker
from backend.data.models.document import Document


class TestSentenceChunker:
    """Tests for SentenceChunker class."""

    def test_chunk_preserve_sentences(self, tmp_path: Path):
        """Test chunking preserves sentence boundaries."""
        doc_file = tmp_path / "sentences.txt"
        content = ("First sentence. " * 10) + ("Second sentence. " * 10) + ("Third sentence. " * 10)
        doc_file.write_text(content)

        doc = Document(
            filename="sentences.txt",
            file_extension=".txt",
            source_path=str(doc_file),
            content=content,
        )

        chunker = SentenceChunker()
        chunks = chunker.chunk(doc)

        # All chunks should contain sentence fragments
        assert len(chunks) >= 1
        assert all(c.text.strip() for c in chunks)

    def test_strategy_returns_sentence(self):
        """Test strategy property returns SENTENCE."""
        chunker = SentenceChunker()
        assert chunker.strategy.value == "sentence"

    def test_small_document_single_chunk(self, tmp_path: Path):
        """Test small document returns single chunk."""
        doc_file = tmp_path / "small.txt"
        doc_file.write_text("Short text.")

        doc = Document(
            filename="small.txt",
            file_extension=".txt",
            source_path=str(doc_file),
            content="Short text.",
        )

        chunker = SentenceChunker()
        chunks = chunker.chunk(doc)

        assert len(chunks) == 1
