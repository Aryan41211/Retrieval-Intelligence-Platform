"""Document domain model for the Retrieval Intelligence Platform."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentSourceType(str, Enum):
    """Type of document source."""

    FILE = "file"
    URL = "url"
    API = "api"
    DATABASE = "database"
    STREAM = "stream"


class DocumentSource(BaseModel):
    """Identifies the origin of a document."""

    type: DocumentSourceType
    path: str | None = None
    url: str | None = None
    api_endpoint: str | None = None
    database_query: str | None = None
    checksum: str
    size_bytes: int
    mime_type: str | None = None
    encoding: str | None = None
    last_modified: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    """Metadata about a document."""

    title: str | None = None
    author: str | None = None
    language: str | None = None
    char_count: int = 0
    word_count: int = 0
    page_count: int | None = None
    tags: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Complete document entity representing loaded source content."""

    document_id: UUID = Field(default_factory=uuid4)
    filename: str
    file_extension: str
    source_path: str
    title: str | None = None
    language: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    page_count: int | None = None
    content: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    checksum: str = ""
    file_size: int = 0
    source: DocumentSource | None = None

    def __hash__(self) -> int:
        """Make Document hashable for set operations."""
        return hash(self.document_id)


class DocumentLoadResult(BaseModel):
    """Result of loading a document."""

    success: bool
    document: Document | None = None
    error: str | None = None
    error_code: str | None = None