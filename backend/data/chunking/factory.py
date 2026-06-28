"""Factory for creating chunkers."""

from typing import TYPE_CHECKING

from backend.data.chunking.base_chunker import BaseChunker, ChunkingConfig
from backend.data.chunking.markdown_chunker import MarkdownChunker
from backend.data.chunking.recursive_chunker import RecursiveChunker
from backend.data.chunking.sentence_chunker import SentenceChunker
from backend.data.models.chunk import ChunkingStrategy

if TYPE_CHECKING:
    from backend.data.models.chunk import Chunk
    from backend.data.models.document import Document


class ChunkerFactory:
    """Factory for creating appropriate chunker."""

    _chunkers: dict[ChunkingStrategy, type[BaseChunker]] = {
        ChunkingStrategy.RECURSIVE: RecursiveChunker,
        ChunkingStrategy.SENTENCE: SentenceChunker,
        ChunkingStrategy.MARKDOWN: MarkdownChunker,
    }

    @classmethod
    def create_chunker(
        cls,
        strategy: ChunkingStrategy | None = None,
        config: ChunkingConfig | None = None,
    ) -> BaseChunker:
        """Create a chunker for the given strategy.

        Args:
            strategy: Chunking strategy to use.
            config: Optional configuration override.

        Returns:
            Chunker instance.

        Raises:
            ValueError: If strategy is not supported.
        """
        strategy = strategy or ChunkingStrategy.RECURSIVE

        if strategy not in cls._chunkers:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")

        chunker = cls._chunkers[strategy](config)
        return chunker

    @classmethod
    def register_chunker(
        cls,
        strategy: ChunkingStrategy,
        chunker_class: type[BaseChunker],
    ) -> None:
        """Register a new chunker strategy.

        Args:
            strategy: Strategy enum value.
            chunker_class: Chunker class to register.
        """
        cls._chunkers[strategy] = chunker_class

    @classmethod
    def get_supported_strategies(cls) -> list[ChunkingStrategy]:
        """Get all supported chunking strategies.

        Returns:
            List of supported strategies.
        """
        return list(cls._chunkers.keys())

    @classmethod
    def chunk(
        cls,
        document: "Document",
        strategy: ChunkingStrategy | None = None,
        config: ChunkingConfig | None = None,
    ) -> list["Chunk"]:
        """Chunk a document using the specified strategy.

        Args:
            document: Document to chunk.
            strategy: Chunking strategy to use.
            config: Optional configuration.

        Returns:
            List of Chunk objects.
        """

        chunker = cls.create_chunker(strategy, config)
        return chunker.chunk(document)
