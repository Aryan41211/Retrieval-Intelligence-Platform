"""Sentence-aware chunking strategy."""

import re
from typing import Any

from backend.data.chunking.base_chunker import BaseChunker
from backend.data.models.chunk import Chunk, ChunkingStrategy
from backend.data.models.document import Document


class SentenceChunker(BaseChunker):
    """Sentence-aware chunker that preserves sentence boundaries."""

    SEARCH_WINDOW_SIZE = 50

    SENTENCE_PATTERN = re.compile(
        r"[.!?]+(?:\s+|\s*$)|(?:\b(?:[A-Z][a-z]+){2,}\s*\.)",
        re.MULTILINE
    )

    @property
    def strategy(self) -> ChunkingStrategy:
        """Return the chunking strategy.

        Returns:
            Chunking strategy enum value.
        """
        return ChunkingStrategy.SENTENCE

    def chunk(self, document: Document) -> list[Chunk]:
        """Chunk a document preserving sentence boundaries.

        Args:
            document: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        chunks: list[Chunk] = []
        text = document.content

        if not text or len(text) < self.config.min_chunk_size:
            return [self._create_chunk(document, text, 0, 0, len(text))]

        sentences = self._split_sentences(text)
        segments = self._merge_sentences(sentences)

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

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Text to split.

        Returns:
            List of sentences.
        """
        sentences = re.split(r"([.!?]+(?:\s+|\s*$))", text)
        result = []

        i = 0
        while i < len(sentences):
            if sentences[i]:
                if i + 1 < len(sentences) and sentences[i + 1]:
                    result.append(sentences[i] + sentences[i + 1])
                    i += 2
                else:
                    result.append(sentences[i])
                    i += 1

        return result if result else [text]

    def _merge_sentences(self, sentences: list[str]) -> list[str]:
        """Merge sentences into chunks respecting size limits.

        Args:
            sentences: List of sentences.

        Returns:
            List of merged segments.
        """
        segments = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) <= self.config.chunk_size:
                current += sentence
            else:
                if current:
                    segments.append(current)
                current = sentence

        if current:
            segments.append(current)

        return segments

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
        pos = original.find(segment[:search_len])
        return pos if pos >= 0 else 0

    def _config_to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration as dictionary.
        """
        return {
            "chunk_size": self.config.chunk_size,
            "min_chunk_size": self.config.min_chunk_size,
            "sentence_overlap": self.config.sentence_overlap,
        }
