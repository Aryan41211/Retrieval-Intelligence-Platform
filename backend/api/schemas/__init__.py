"""
Schema definitions for API requests and responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


# Document schemas
class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""

    filename: str
    content: str
    metadata: dict[str, Any] | None = None


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: UUID
    filename: str
    status: str
    message: str


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

    query: str
    conversation_id: str | None = None
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

    query: str
    top_k: int = 10
    threshold: float | None = None
    filters: dict[str, Any] | None = None
    strategy: str | None = None


class RetrievalResponse(BaseModel):
    """Response model for retrieval operation."""

    results: list[RetrievalResult]
    total_found: int
    processing_time_ms: float
    strategy: str | None = None


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
