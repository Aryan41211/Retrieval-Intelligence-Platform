"""Chunk domain model for the Retrieval Intelligence Platform."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    MARKDOWN = "markdown"
    SENTENCE = "sentence"
    HIERARCHICAL = "hierarchical"


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""

    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunking_config: dict[str, Any] = Field(default_factory=dict)

    chunk_index: int = 0
    start_offset: int = 0
    end_offset: int = 0
    page_number: int | None = None
    section_title: str | None = None
    heading_level: int | None = None

    character_count: int = 0
    token_count: int = 0

    source_file: str = ""

    custom: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """Complete chunk entity representing a document segment."""

    chunk_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    text: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __hash__(self) -> int:
        """Make Chunk hashable for set operations."""
        return hash(self.chunk_id)
