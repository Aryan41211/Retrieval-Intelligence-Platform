"""Markdown-aware chunking strategy."""

import re
from typing import Any

from backend.data.chunking.base_chunker import BaseChunker
from backend.data.models.chunk import Chunk, ChunkingStrategy
from backend.data.models.document import Document


class MarkdownChunker(BaseChunker):
    """Markdown-aware chunker that respects heading hierarchy."""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r"(```.*?```)", re.DOTALL)

    @property
    def strategy(self) -> ChunkingStrategy:
        """Return the chunking strategy.

        Returns:
            Chunking strategy enum value.
        """
        return ChunkingStrategy.MARKDOWN

    def chunk(self, document: Document) -> list[Chunk]:
        """Chunk a markdown document respecting headings.

        Args:
            document: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        chunks: list[Chunk] = []
        text = document.content

        if not text or len(text) < self.config.min_chunk_size:
            return [self._create_chunk(document, text, 0, 0, len(text))]

        sections = self._extract_sections(text)

        chunk_index = 0
        for section in sections:
            if self._is_valid_segment(section["text"]):
                chunk = self._create_chunk_with_heading(
                    document,
                    section["text"],
                    section.get("title"),
                    section.get("level"),
                    chunk_index,
                    section["start"],
                    section["end"],
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks if chunks else [self._create_chunk(document, text, 0, 0, len(text))]

    def _extract_sections(self, text: str) -> list[dict[str, Any]]:
        """Extract sections from markdown preserving heading context.

        Args:
            text: Markdown text.

        Returns:
            List of section dictionaries.
        """
        sections = []
        lines = text.split("\n")
        current_section = {"text": "", "start": 0, "end": 0, "title": None, "level": None}

        for i, line in enumerate(lines):
            heading_match = self.HEADING_PATTERN.match(line)

            if heading_match:
                if current_section["text"].strip():
                    current_section["end"] = i
                    sections.append(current_section)

                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_pos = sum(len(line_item) + 1 for line_item in lines[:i])

                current_section = {
                    "text": line + "\n",
                    "start": current_pos,
                    "end": current_pos + len(line),
                    "title": title,
                    "level": level,
                }
            else:
                current_section["text"] += line + "\n"

        if current_section["text"].strip():
            sections.append(current_section)

        return sections if sections else [{"text": text, "start": 0, "end": len(text), "title": None, "level": None}]

    def _create_chunk_with_heading(
        self,
        document: Document,
        text: str,
        section_title: str | None,
        heading_level: int | None,
        chunk_index: int,
        start_offset: int,
        end_offset: int,
    ) -> Chunk:
        """Create a chunk with heading metadata.

        Args:
            document: Source document.
            text: Chunk text content.
            section_title: Section title from heading.
            heading_level: Heading level (1-6).
            chunk_index: Position in chunk sequence.
            start_offset: Character offset in source.
            end_offset: Character offset in source.

        Returns:
            Chunk with metadata.
        """
        token_count = len(text.split())

        metadata = self._create_chunk_metadata(
            document=document,
            text=text,
            chunk_index=chunk_index,
            start_offset=start_offset,
            end_offset=end_offset,
            section_title=section_title,
            heading_level=heading_level,
            token_count=token_count,
        )

        return Chunk(
            document_id=document.document_id,
            text=text,
            metadata=metadata,
        )

    def _create_chunk_metadata(
        self,
        document: Document,
        text: str,
        chunk_index: int,
        start_offset: int,
        end_offset: int,
        section_title: str | None,
        heading_level: int | None,
        token_count: int,
    ) -> Any:
        """Create chunk metadata with heading info.

        Returns:
            ChunkMetadata instance.
        """
        from backend.data.models.chunk import ChunkMetadata

        return ChunkMetadata(
            chunking_strategy=self.strategy,
            chunking_config=self._config_to_dict(),
            chunk_index=chunk_index,
            start_offset=start_offset,
            end_offset=end_offset,
            character_count=len(text),
            token_count=token_count,
            source_file=document.source_path,
            section_title=section_title,
            heading_level=heading_level,
            custom={"filename": document.filename},
        )

    def _is_valid_segment(self, segment: str) -> bool:
        """Check if segment meets minimum size requirements.

        Args:
            segment: Text segment to check.

        Returns:
            True if valid.
        """
        return len(segment.strip()) >= self.config.min_chunk_size

    def _config_to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration as dictionary.
        """
        return {
            "chunk_size": self.config.chunk_size,
            "min_chunk_size": self.config.min_chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
        }
