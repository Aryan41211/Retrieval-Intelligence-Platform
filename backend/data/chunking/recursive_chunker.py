"""Recursive chunking strategy."""

import re
from typing import Any

from backend.data.chunking.base_chunker import BaseChunker
from backend.data.models.chunk import Chunk, ChunkingStrategy
from backend.data.models.document import Document


class RecursiveChunker(BaseChunker):
    """Recursive chunker that splits on multiple separators."""

    SEARCH_WINDOW_SIZE = 50
    """Recursive chunker that splits on multiple separators."""

    @property
    def strategy(self) -> ChunkingStrategy:
        """Return the chunking strategy.

        Returns:
            Chunking strategy enum value.
        """
        return ChunkingStrategy.RECURSIVE

    def chunk(self, document: Document) -> list[Chunk]:
        """Chunk a document recursively.

        Args:
            document: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        chunks: list[Chunk] = []
        text = document.content

        if not text or len(text) < self.config.min_chunk_size:
            return [self._create_chunk(document, text, 0, 0, len(text))]

        separators = self.config.separators or ["\n\n", "\n", ". ", " ", ""]
        segments = self._split_text(text, separators, self.config.chunk_size)

        chunk_index = 0
        for segment in segments:
            if self._is_valid_segment(segment):
                chunk = self._create_chunk(
                    document,
                    segment,
                    chunk_index,
                    self._find_offset(text, segment),
                    self._find_offset(text, segment) + len(segment),
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks if chunks else [self._create_chunk(document, text, 0, 0, len(text))]

    def _split_text(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
    ) -> list[str]:
        """Split text recursively using separators.

        Args:
            text: Text to split.
            separators: Separator patterns to try.
            chunk_size: Target chunk size.

        Returns:
            List of text segments.
        """
        if len(text) <= chunk_size:
            return [text] if text else []

        for separator in separators:
            if not separator:
                continue

            pattern = re.escape(separator)
            matches = list(re.finditer(f"(.{{1,{chunk_size}}}){pattern}", text))

            if matches:
                segments = []
                last_end = 0

                for match in matches:
                    if match.end() - match.start() >= self.config.min_chunk_size - len(separator):
                        segments.append(text[last_end : match.end()])
                        last_end = match.end()

                if last_end < len(text):
                    remaining = text[last_end:]
                    if len(remaining) >= self.config.min_chunk_size:
                        segments.append(remaining)
                    else:
                        segments.append(text)
                return segments if segments else [text]

        return [text]

    def _is_valid_segment(self, segment: str) -> bool:
        """Check if segment meets minimum size requirements.

        Args:
            segment: Text segment to check.

        Returns:
            True if valid.
        """
        return len(segment.strip()) >= self.config.min_chunk_size

    def _find_offset(self, original: str, segment: str) -> int:
        """Find offset of segment in original text.

        Args:
            original: Original document text.
            segment: Segment to find.

        Returns:
            Character offset.
        """
        search_len = min(self.SEARCH_WINDOW_SIZE, len(segment))
        pos = original.find(segment[:search_len] if search_len > 0 else "")
        return pos if pos >= 0 else 0

    def _config_to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration as dictionary.
        """
        return {
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "separators": self.config.separators,
        }
