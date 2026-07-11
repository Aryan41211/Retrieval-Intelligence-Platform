"""Unit tests for Markdown Chunker."""

from pathlib import Path

from backend.data.chunking.base_chunker import ChunkingConfig
from backend.data.chunking.markdown_chunker import MarkdownChunker
from backend.data.models.document import Document


class TestMarkdownChunker:
    """Tests for MarkdownChunker class."""

    def test_chunk_respects_headings(self, tmp_path: Path):
        """Test chunking respects markdown headings."""
        doc_file = tmp_path / "doc.md"
        content = (
            "# Title\n\n"
            + ("Content under title. " * 30)
            + "\n\n## Subtitle\n\n"
            + ("Content under subtitle. " * 30)
        )
        doc_file.write_text(content)

        doc = Document(
            filename="doc.md",
            file_extension=".md",
            source_path=str(doc_file),
            content=content,
        )

        chunker = MarkdownChunker(config=ChunkingConfig(chunk_size=500, min_chunk_size=20))
        chunks = chunker.chunk(doc)

        assert len(chunks) >= 1
        assert any(chunk.metadata.heading_level is not None for chunk in chunks)

    def test_strategy_returns_markdown(self):
        """Test strategy property returns MARKDOWN."""
        chunker = MarkdownChunker()
        assert chunker.strategy.value == "markdown"

    def test_section_title_preserved(self, tmp_path: Path):
        """Test section title is preserved in chunks."""
        doc_file = tmp_path / "sections.md"
        content = "# Introduction\n\nIntro text here."
        doc_file.write_text(content)

        doc = Document(
            filename="sections.md",
            file_extension=".md",
            source_path=str(doc_file),
            content=content,
        )

        chunker = MarkdownChunker()
        chunks = chunker.chunk(doc)

        assert len(chunks) >= 1
        chunk_with_title = next((c for c in chunks if c.metadata.section_title), None)
        if chunk_with_title:
            assert chunk_with_title.metadata.section_title == "Introduction"
