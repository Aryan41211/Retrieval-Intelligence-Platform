"""Base chunker for document chunking."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from backend.data.models.chunk import Chunk, ChunkingStrategy, ChunkMetadata
from backend.data.models.document import Document


class ChunkingConfig(BaseModel):
    """Configuration for chunking strategies."""

    chunk_size: int = Field(default=512, ge=100, le=2048)
    chunk_overlap: int = Field(default=50, ge=0)
    min_chunk_size: int = Field(default=50, ge=10)
    max_chunk_size: int = Field(default=1024, ge=200)
    sentence_overlap: int = Field(default=1, ge=0)
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE

    separators: list[str] = Field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])

    model_config = {"extra": "ignore"}


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Chunk a document into segments.

        Args:
            document: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        ...

    @property
    @abstractmethod
    def strategy(self) -> ChunkingStrategy:
        """Return the chunking strategy.

        Returns:
            Chunking strategy enum value.
        """
        ...

    def _create_chunk(
        self,
        document: Document,
        text: str,
        chunk_index: int,
        start_offset: int,
        end_offset: int,
    ) -> Chunk:
        """Create a chunk with proper metadata.

        Args:
            document: Source document.
            text: Chunk text content.
            chunk_index: Position in chunk sequence.
            start_offset: Character offset in source.
            end_offset: Character offset in source.

        Returns:
            Chunk with metadata.
        """
        token_count = len(text.split())

        metadata = ChunkMetadata(
            chunking_strategy=self.strategy,
            chunking_config=self._config_to_dict(),
            chunk_index=chunk_index,
            start_offset=start_offset,
            end_offset=end_offset,
            character_count=len(text),
            token_count=token_count,
            source_file=document.source_path,
            custom={"filename": document.filename},
        )

        return Chunk(
            document_id=document.document_id,
            text=text,
            metadata=metadata,
        )

    def _config_to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization.

        Returns:
            Configuration as dictionary.
        """
        return {
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "min_chunk_size": self.config.min_chunk_size,
        }

    def _find_chunk_boundaries(
        self,
        text: str,
        chunk_size: int,
        separators: list[str],
    ) -> list[tuple[int, int]]:
        """Find chunk boundaries using separators.

        Args:
            text: Text to analyze.
            chunk_size: Target chunk size.
            separators: List of separators to try.

        Returns:
            List of (start, end) offset tuples.
        """
        if len(text) <= chunk_size:
            return [(0, len(text))]

        boundaries = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            if end < len(text) and separators:
                best_separator = separators[0]
                search_pos = start + self.config.chunk_overlap

                while search_pos < end:
                    if best_separator:
                        pos = text.rfind(best_separator, search_pos, end + len(best_separator))
                        if pos > search_pos:
                            end = pos + len(best_separator)
                            break
                    search_pos += 1

            boundaries.append((start, end))
            start = max(end - self.config.chunk_overlap, end - 1)

        return boundaries
