"""Tests for chunking factory."""

from backend.data.chunking.factory import ChunkerFactory
from backend.data.chunking.markdown_chunker import MarkdownChunker
from backend.data.chunking.recursive_chunker import RecursiveChunker
from backend.data.chunking.sentence_chunker import SentenceChunker
from backend.data.models.chunk import ChunkingStrategy
from backend.data.models.document import Document


def test_create_recursive_chunker():
    """Test factory creates recursive chunker."""
    chunker = ChunkerFactory.create_chunker(ChunkingStrategy.RECURSIVE)
    assert isinstance(chunker, RecursiveChunker)


def test_create_sentence_chunker():
    """Test factory creates sentence chunker."""
    chunker = ChunkerFactory.create_chunker(ChunkingStrategy.SENTENCE)
    assert isinstance(chunker, SentenceChunker)


def test_create_markdown_chunker():
    """Test factory creates markdown chunker."""
    chunker = ChunkerFactory.create_chunker(ChunkingStrategy.MARKDOWN)
    assert isinstance(chunker, MarkdownChunker)


def test_get_supported_strategies():
    """Test factory returns supported strategies."""
    strategies = ChunkerFactory.get_supported_strategies()
    assert ChunkingStrategy.RECURSIVE in strategies
    assert ChunkingStrategy.SENTENCE in strategies
    assert ChunkingStrategy.MARKDOWN in strategies


def test_chunk_via_factory():
    """Test chunking via factory convenience method."""
    doc = Document(
        filename="test.txt",
        file_extension=".txt",
        source_path="/test.txt",
        content="Test content for chunking.",
    )

    chunks = ChunkerFactory.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "Test content for chunking."
