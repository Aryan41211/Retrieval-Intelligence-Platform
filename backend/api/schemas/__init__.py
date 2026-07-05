"""
Schema definitions for API requests and responses.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

# Document schemas
class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    filename: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

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
    chunk_count: Optional[int] = None

# Chat schemas
class ChatMessage(BaseModel):
    """Model for chat message."""
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    """Request model for chat completion."""
    query: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """Response model for chat completion."""
    message: ChatMessage
    conversation_id: str
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None

# Retrieval schemas
class RetrievalResult(BaseModel):
    """Model for retrieval result."""
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    rank: int
    source_filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RetrievalRequest(BaseModel):
    """Request model for retrieval operation."""
    query: str
    top_k: int = 10
    threshold: Optional[float] = None
    filters: Optional[Dict[str, Any]] = None
    strategy: Optional[str] = None

class RetrievalResponse(BaseModel):
    """Response model for retrieval operation."""
    results: List[RetrievalResult]
    total_found: int
    processing_time_ms: float
    strategy: Optional[str] = None

# Evaluation schemas
class EvaluationResult(BaseModel):
    """Model for evaluation result."""
    evaluation_type: str
    score: float
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

class EvaluationRequest(BaseModel):
    """Request model for evaluation operation."""
    dataset_id: Optional[str] = None
    dataset: Optional[List[Dict[str, Any]]] = None
    evaluation_types: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None

class EvaluationResponse(BaseModel):
    """Response model for evaluation operation."""
    evaluation_id: str
    results: List[EvaluationResult]
    overall_score: float
    total_items: int
    execution_time_ms: float

# Experiment schemas
class ExperimentResult(BaseModel):
    """Model for experiment result."""
    experiment_id: str
    configuration: Dict[str, Any]
    results: List[Dict[str, Any]]
    metrics: Dict[str, float]
    timestamp: datetime

class ExperimentRequest(BaseModel):
    """Request model for experiment operation."""
    name: str
    description: Optional[str] = None
    configuration: Dict[str, Any]
    dataset_id: Optional[str] = None

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
    llm_provider: Dict[str, Any]
    embedding_model: Dict[str, Any]
    retrieval_strategy: Dict[str, Any]
    top_k: int
    temperature: float
    prompt_version: str
