"""
Schema definitions for API requests and responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Upper bounds for user-supplied input. Without these a single request could
# submit an unbounded query or document body, driving both memory use and
# per-token provider cost.
MAX_QUERY_LENGTH = 4000
MAX_DOCUMENT_BYTES = 5_000_000
MAX_FILENAME_LENGTH = 255
MAX_TOP_K = 100


# Document schemas
class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""

    filename: str = Field(min_length=1, max_length=MAX_FILENAME_LENGTH)
    content: str = Field(min_length=1, max_length=MAX_DOCUMENT_BYTES)
    metadata: dict[str, Any] | None = None
    workspace_id: str | None = Field(
        default=None,
        max_length=36,
        description="Target workspace. Omit to use your private knowledge base.",
    )


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: UUID
    filename: str
    status: str
    message: str
    namespace: str | None = Field(
        default=None, description="Knowledge base the document was written to."
    )
    chunks_indexed: int = Field(default=0, description="Number of chunks added to the index.")


class DocumentSummary(BaseModel):
    """One indexed document, aggregated from the vector store's records."""

    document_id: str
    filename: str
    namespace: str
    chunk_count: int
    status: str = "indexed"


class DocumentMetadata(BaseModel):
    """Model for document metadata."""

    document_id: UUID
    filename: str
    size_bytes: int
    uploaded_at: datetime
    status: str
    chunk_count: int | None = None


# Chat schemas
class ChatMessage(BaseModel):
    """Model for chat message."""

    role: str
    content: str
    timestamp: datetime | None = None


class ChatRequest(BaseModel):
    """Request model for chat completion."""

    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    conversation_id: str | None = Field(default=None, max_length=64)
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Response model for chat completion."""

    message: ChatMessage
    conversation_id: str
    retrieved_chunks: list[dict[str, Any]] | None = None
    citations: list[dict[str, Any]] | None = None


# Retrieval schemas
class RetrievalResult(BaseModel):
    """Model for retrieval result."""

    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    rank: int
    source_filename: str | None = None
    metadata: dict[str, Any] | None = None


class RetrievalRequest(BaseModel):
    """Request model for retrieval operation."""

    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    top_k: int = Field(default=10, ge=1, le=MAX_TOP_K)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    filters: dict[str, Any] | None = None
    strategy: str | None = Field(default=None, max_length=64)


class RetrievalResponse(BaseModel):
    """Response model for retrieval operation."""

    results: list[RetrievalResult]
    total_found: int
    processing_time_ms: float
    strategy: str | None = None
    namespaces_searched: list[str] = Field(
        default_factory=list,
        description="Knowledge bases consulted: the caller's own plus their workspaces.",
    )


# Evaluation schemas
class EvaluationResult(BaseModel):
    """Model for evaluation result."""

    evaluation_type: str
    score: float
    details: dict[str, Any] | None = None
    timestamp: datetime


class EvaluationRequest(BaseModel):
    """Request model for evaluation operation."""

    dataset_id: str | None = None
    dataset: list[dict[str, Any]] | None = None
    evaluation_types: list[str] | None = None
    metrics: dict[str, Any] | None = None


class EvaluationResponse(BaseModel):
    """Response model for evaluation operation."""

    evaluation_id: str
    results: list[EvaluationResult]
    overall_score: float
    total_items: int
    execution_time_ms: float


# Experiment schemas
class ExperimentResult(BaseModel):
    """Model for experiment result."""

    experiment_id: str
    configuration: dict[str, Any]
    results: list[dict[str, Any]]
    metrics: dict[str, float]
    timestamp: datetime


class ExperimentRequest(BaseModel):
    """Request model for experiment operation."""

    name: str
    description: str | None = None
    configuration: dict[str, Any]
    dataset_id: str | None = None


class ExperimentResponse(BaseModel):
    """Response model for experiment operation."""

    experiment_id: str
    name: str
    status: str
    created_at: datetime


# Settings schemas
class SettingsChange(BaseModel):
    """Model for settings change."""

    key: str
    value: Any


class SettingsResponse(BaseModel):
    """Response model for settings."""

    llm_provider: dict[str, Any]
    embedding_model: dict[str, Any]
    retrieval_strategy: dict[str, Any]
    top_k: int
    temperature: float
    prompt_version: str
