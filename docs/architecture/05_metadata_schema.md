# Metadata Schema

## Overview

This document defines the complete metadata schema for all entities in the Retrieval Intelligence Platform. Metadata enables filtering, debugging, evaluation, and experiment tracking throughout the pipeline.

## Core Principles

1. **Immutable Identifiers**: All entities have UUIDv7 (time-ordered) primary keys
2. **Traceability**: Every chunk links back to its source document and original position
3. **Extensibility**: Custom fields allowed via `custom: dict[str, Any]`
4. **Versioning**: Schema version tracked on all entities
5. **Privacy**: No PII in metadata; content stored separately

---

## Document Metadata

### DocumentSource
```python
class DocumentSource(BaseModel):
    """Identifies the origin of a document."""
    type: DocumentSourceType  # FILE, URL, API, DATABASE, STREAM
    path: Optional[str] = None           # Local file path
    url: Optional[str] = None            # Source URL
    api_endpoint: Optional[str] = None   # API identifier
    database_query: Optional[str] = None # SQL/query reference
    checksum: str                        # SHA256 of raw content
    size_bytes: int                      # Raw content size
    mime_type: Optional[str] = None      # Detected MIME type
    encoding: Optional[str] = None       # Character encoding
    last_modified: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)  # Source-specific extras
```

### DocumentMetadata
```python
class DocumentMetadata(BaseModel):
    """Enriched metadata about a document."""
    # Core identification
    title: Optional[str] = None
    author: Optional[str] = None
    creators: list[str] = Field(default_factory=list)
    subject: Optional[str] = None
    description: Optional[str] = None
    
    # Temporal
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    
    # Content characteristics
    language: Optional[str] = None           # ISO 639-1 code (e.g., "en")
    languages: list[str] = Field(default_factory=list)  # Multi-lang docs
    page_count: Optional[int] = None
    char_count: int = 0
    word_count: int = 0
    token_count_estimate: int = 0            # For LLM context budgeting
    
    # Structure
    structure: Optional[DocumentStructure] = None
    has_tables: bool = False
    has_images: bool = False
    has_code: bool = False
    has_math: bool = False
    
    # Classification
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    sensitivity: SensitivityLevel = SensitivityLevel.PUBLIC
    
    # Processing
    loader_version: str = "1.0"
    preprocessor_version: str = "1.0"
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_duration_ms: int = 0
    
    # Extensibility
    custom: dict[str, Any] = Field(default_factory=dict)
```

### DocumentStructure
```python
class DocumentStructure(BaseModel):
    """Captured document structure for smart chunking."""
    headings: list[Heading] = Field(default_factory=list)
    tables: list[TableInfo] = Field(default_factory=list)
    code_blocks: list[CodeBlock] = Field(default_factory=list)
    lists: list[ListInfo] = Field(default_factory=list)
    links: list[LinkInfo] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)

class Heading(BaseModel):
    level: int              # 1-6
    text: str
    start_char: int
    end_char: int
    page: Optional[int] = None

class TableInfo(BaseModel):
    start_char: int
    end_char: int
    rows: int
    cols: int
    has_header: bool
    caption: Optional[str] = None
    page: Optional[int] = None
```

### Document (Complete)
```python
class Document(BaseModel):
    """Complete document entity."""
    id: UUID = Field(default_factory=uuid7)
    content: str
    metadata: DocumentMetadata
    source: DocumentSource
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Chunk Metadata

### ChunkMetadata
```python
class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    # Chunking strategy
    chunking_strategy: ChunkingStrategy
    chunking_config: dict = Field(default_factory=dict)  # Strategy-specific params
    
    # Position in document
    chunk_index: int = 0                    # Sequential index
    start_char: int = 0                     # Inclusive
    end_char: int = 0                       # Exclusive
    start_token: Optional[int] = None       # Token position
    end_token: Optional[int] = None
    
    # Content stats
    char_count: int = 0
    word_count: int = 0
    token_count: int = 0
    
    # Overlap
    overlap_prev_tokens: int = 0            # Tokens shared with previous
    overlap_next_tokens: int = 0            # Tokens shared with next
    overlap_prev_chars: int = 0
    overlap_next_chars: int = 0
    
    # Hierarchy (for hierarchical chunking)
    parent_chunk_id: Optional[UUID] = None
    child_chunk_ids: list[UUID] = Field(default_factory=list)
    depth: int = 0                          # 0 = top level
    
    # Structure context
    heading_path: list[str] = Field(default_factory=list)  # e.g., ["Chapter 1", "1.2 Overview"]
    heading_level: Optional[int] = None
    contains_table: bool = False
    contains_code: bool = False
    contains_image: bool = False
    
    # Quality
    quality_score: Optional[float] = None   # 0-1, heuristic or learned
    is_boilerplate: bool = False
    is_continuation: bool = False           # Mid-sentence/paragraph
    
    # Embedding
    embedding_model: Optional[str] = None
    embedding_version: Optional[str] = None
    embedding_dim: Optional[int] = None
    embedded_at: Optional[datetime] = None
    embedding_duration_ms: Optional[int] = None
    
    # Extensibility
    custom: dict[str, Any] = Field(default_factory=dict)
```

### Chunk (Complete)
```python
class Chunk(BaseModel):
    """Complete chunk entity."""
    id: UUID = Field(default_factory=uuid7)
    document_id: UUID
    content: str
    metadata: ChunkMetadata
    embedding: Optional[Vector] = None      # Populated after embedding
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Vector Store Metadata

### VectorRecord
```python
class VectorRecord(BaseModel):
    """Record stored in vector database."""
    # Primary
    id: str                              # String UUID for vector DB compatibility
    vector: list[float]                  # Dense embedding
    
    # Metadata payload (stored alongside vector)
    chunk_id: str                        # UUID string
    document_id: str                     # UUID string
    document_title: Optional[str] = None
    content: str                         # Chunk text (for BM25, debugging)
    chunk_index: int = 0
    
    # Filterable fields
    source_type: str                     # DocumentSourceType value
    source_path: Optional[str] = None
    language: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    sensitivity: str = "public"
    
    # Temporal
    created_at: str                      # ISO8601
    document_created_at: Optional[str] = None
    
    # Search optimization
    token_count: int = 0
    heading_path: str = ""               # Joined for keyword search
    
    # Custom (JSON-serializable)
    custom: dict = Field(default_factory=dict)
```

### IndexMetadata
```python
class IndexMetadata(BaseModel):
    """Vector index metadata for management."""
    index_name: str
    provider: VectorStoreProvider
    dimension: int
    metric: DistanceMetric              # COSINE, DOT_PRODUCT, L2
    vector_count: int = 0
    index_size_bytes: int = 0
    created_at: datetime
    updated_at: datetime
    config_hash: str                    # Hash of index config for change detection
    schema_version: str = "1.0"
```

---

## Retrieval Metadata

### RetrievalResult
```python
class RetrievalResult(BaseModel):
    """Result from retrieval stage."""
    chunk: Chunk
    score: float = Field(ge=0.0, le=1.0)  # Normalized similarity score
    retrieval_method: RetrievalMethod
    rank: int = 0                         # 1-based rank in result set
    
    # Component scores (for hybrid)
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    rerank_score: Optional[float] = None
    
    # Explanation
    explanation: Optional[RetrievalExplanation] = None
```

### RetrievalExplanation
```python
class RetrievalExplanation(BaseModel):
    """Explainable retrieval information."""
    method: RetrievalMethod
    query_vector: Optional[list[float]] = None  # For debugging
    matched_terms: list[str] = Field(default_factory=list)  # For BM25
    vector_neighbors: list[NeighborInfo] = Field(default_factory=list)
    fusion_details: Optional[FusionDetails] = None

class NeighborInfo(BaseModel):
    chunk_id: str
    score: float
    rank: int

class FusionDetails(BaseModel):
    """Hybrid fusion breakdown."""
    method: HybridFusionMethod
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    rrf_k: Optional[int] = None
    weights: Optional[dict[str, float]] = None
```

### RetrievalMetadata (Query-level)
```python
class RetrievalMetadata(BaseModel):
    """Aggregated retrieval metadata for response."""
    query_embedding_model: str
    query_embedding_dim: int
    total_candidates_dense: int = 0
    total_candidates_sparse: int = 0
    total_candidates_hybrid: int = 0
    retrieval_latency_ms: int = 0
    rerank_latency_ms: int = 0
    methods_used: list[RetrievalMethod] = Field(default_factory=list)
    top_scores: list[float] = Field(default_factory=list)
    score_distribution: ScoreDistribution = Field(default_factory=ScoreDistribution)
    
class ScoreDistribution(BaseModel):
    min: float = 0.0
    max: float = 1.0
    mean: float = 0.0
    median: float = 0.0
    std: float = 0.0
    percentiles: dict[str, float] = Field(default_factory=dict)  # p25, p50, p75, p90, p95
```

---

## Generation Metadata

### GenerationResult
```python
class GenerationResult(BaseModel):
    """Result from generation stage."""
    answer: str
    citations: list[Citation]
    metadata: GenerationMetadata
```

### Citation
```python
class Citation(BaseModel):
    """Citation linking answer to source."""
    chunk_id: UUID
    document_id: UUID
    document_title: Optional[str] = None
    text: str                           # Exact text span cited
    char_start: int                     # In answer string
    char_end: int                       # In answer string
    confidence: Optional[float] = None  # 0-1, from citation extractor
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
```

### GenerationMetadata
```python
class GenerationMetadata(BaseModel):
    """Metadata about generation process."""
    # Model
    model: str
    model_provider: LLMProvider
    model_version: Optional[str] = None
    
    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0              # For providers supporting caching
    
    # Timing
    latency_ms: int = 0
    time_to_first_token_ms: Optional[int] = None
    
    # Parameters
    temperature: float
    top_p: float
    max_tokens: int
    seed: Optional[int] = None
    
    # Context
    context_chunks_used: int = 0
    context_tokens_used: int = 0
    context_truncated: bool = False
    
    # Quality
    groundedness_score: Optional[float] = None    # 0-1, from verifier
    citation_coverage: float = 0.0                # Fraction of sentences cited
    citation_precision: Optional[float] = None    # Fraction of citations valid
    hallucination_flags: list[HallucinationFlag] = Field(default_factory=list)
    
    # Streaming
    streamed: bool = False
    chunks_streamed: int = 0
```

### HallucinationFlag
```python
class HallucinationFlag(BaseModel):
    """Detected potential hallucination."""
    claim: str                          # Text span in answer
    claim_span: tuple[int, int]         # Character positions
    reason: str                         # "no_supporting_evidence", "contradicts_context", etc.
    severity: Severity = Severity.WARNING
    suggested_correction: Optional[str] = None
```

---

## Query Metadata

### QueryRequest
```python
class QueryRequest(BaseModel):
    """Incoming query request."""
    query: str = Field(min_length=1, max_length=8192)
    filters: Optional[MetadataFilter] = None
    params: Optional[QueryParams] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
```

### QueryParams
```python
class QueryParams(BaseModel):
    """Runtime query parameters (override config)."""
    top_k: Optional[int] = None
    rerank_top_n: Optional[int] = None
    similarity_threshold: Optional[float] = None
    enable_expansion: Optional[bool] = None
    enable_rerank: Optional[bool] = None
    enable_citations: Optional[bool] = None
    response_format: ResponseFormat = ResponseFormat.TEXT  # TEXT, JSON, STREAM
    custom: dict[str, Any] = Field(default_factory=dict)
```

### QueryMetadata (Response)
```python
class QueryMetadata(BaseModel):
    """Aggregated query metadata for response."""
    original_query: str
    expanded_queries: list[str] = Field(default_factory=list)
    rewritten_query: Optional[str] = None
    hyde_used: bool = False
    expansion_latency_ms: int = 0
    total_latency_ms: int = 0
    pipeline_version: str = "1.0"
```

---

## Evaluation Metadata

### EvaluationSample
```python
class EvaluationSample(BaseModel):
    """Single evaluation sample."""
    id: str
    query: str
    expected_answer: Optional[str] = None
    expected_chunk_ids: list[str] = Field(default_factory=list)  # Ground truth chunks
    metadata: dict = Field(default_factory=dict)
    dataset_name: Optional[str] = None
    dataset_version: Optional[str] = None
```

### EvaluationResult
```python
class EvaluationResult(BaseModel):
    """Complete evaluation run result."""
    run_id: UUID = Field(default_factory=uuid7)
    dataset_name: str
    dataset_version: str
    config_snapshot: dict                   # Full pipeline config
    sample_count: int
    metrics: dict[str, MetricResult]        # Aggregated metrics
    per_sample: list[SampleResult] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    experiment_run_id: Optional[str] = None  # Link to experiment tracker
```

### SampleResult
```python
class SampleResult(BaseModel):
    """Per-sample evaluation result."""
    sample_id: str
    query: str
    prediction: QueryResponse
    metrics: dict[str, float]               # Per-sample metric values
    passed: bool                            # Overall pass/fail
```

### MetricResult
```python
class MetricResult(BaseModel):
    """Aggregated metric result."""
    name: str
    value: float                            # Mean/aggregate
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    per_sample: Optional[list[float]] = None
    details: dict = Field(default_factory=dict)  # Metric-specific details
    threshold: Optional[float] = None       # Pass/fail threshold
    passed: Optional[bool] = None
```

---

## Experiment Metadata

### ExperimentConfig
```python
class ExperimentConfig(BaseModel):
    """Full configuration snapshot for reproducibility."""
    # Pipeline config
    ingestion: IngestionConfig
    query: QueryConfig
    evaluation: EvaluationConfig
    
    # Environment
    python_version: str
    package_versions: dict[str, str]        # Key dependencies
    git_commit: Optional[str] = None
    git_dirty: bool = False
    git_branch: Optional[str] = None
    
    # Hardware
    cpu_count: int
    gpu_count: int = 0
    gpu_type: Optional[str] = None
    memory_gb: float
    
    # Timestamp
    captured_at: datetime = Field(default_factory=datetime.utcnow)
```

### ExperimentRun
```python
class ExperimentRun(BaseModel):
    """Single experiment run."""
    run_id: str
    experiment_name: str
    run_name: Optional[str] = None
    status: RunStatus = RunStatus.RUNNING
    config: ExperimentConfig
    params: dict = Field(default_factory=dict)      # Flat params for tracking
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
```

### Artifact
```python
class Artifact(BaseModel):
    """Experiment artifact."""
    name: str
    path: str                                 # Local or remote URI
    type: ArtifactType                        # MODEL, DATASET, REPORT, LOG, PREDICTIONS, CONFIG
    size_bytes: int
    checksum: str                             # SHA256
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Enumerations

### DocumentSourceType
```python
class DocumentSourceType(str, Enum):
    FILE = "file"
    URL = "url"
    API = "api"
    DATABASE = "database"
    STREAM = "stream"
```

### SensitivityLevel
```python
class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
```

### ChunkingStrategy
```python
class ChunkingStrategy(str, Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    MARKDOWN = "markdown"
    SENTENCE = "sentence"
    HIERARCHICAL = "hierarchical"
```

### RetrievalMethod
```python
class RetrievalMethod(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID_RRF = "hybrid_rrf"
    HYBRID_WEIGHTED = "hybrid_weighted"
    HYBRID_DBSF = "hybrid_dbsf"
    MULTI_VECTOR = "multi_vector"
```

### HybridFusionMethod
```python
class HybridFusionMethod(str, Enum):
    RRF = "rrf"
    WEIGHTED = "weighted"
    DBSF = "dbsf"
    LINEAR = "linear"
```

### LLMProvider
```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"
    TGI = "tgi"
    COHERE = "cohere"
    AZURE = "azure"
```

### EmbeddingProvider
```python
class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    COHERE = "cohere"
    VOYAGE = "voyage"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    HUGGINGFACE = "huggingface"
```

### VectorStoreProvider
```python
class VectorStoreProvider(str, Enum):
    FAISS = "faiss"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    LANCEDB = "lancedb"
    MILVUS = "milvus"
```

### DistanceMetric
```python
class DistanceMetric(str, Enum):
    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    L2 = "l2"
    MAX_INNER_PRODUCT = "max_inner_product"
```

### RerankerProvider
```python
class RerankerProvider(str, Enum):
    COHERE = "cohere"
    JINA = "jina"
    CROSS_ENCODER = "cross_encoder"
    BGE_RERANKER = "bge_reranker"
    LLM = "llm"
```

### VerificationStatus
```python
class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PARTIAL = "partial"
    CONTRADICTED = "contradicted"
```

### RunStatus
```python
class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### ArtifactType
```python
class ArtifactType(str, Enum):
    MODEL = "model"
    DATASET = "dataset"
    REPORT = "report"
    LOG = "log"
    PREDICTIONS = "predictions"
    CONFIG = "config"
    CHECKPOINT = "checkpoint"
```

### ResponseFormat
```python
class ResponseFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    STREAM = "stream"
```

### Severity
```python
class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

---

## Metadata Storage Strategy

### In Vector Store (for filtering)
- Only filterable, low-cardinality fields
- `chunk_id`, `document_id`, `source_type`, `language`, `tags`, `categories`, `sensitivity`, `created_at`
- `content` for BM25 index

### In Metadata Database (PostgreSQL)
- Full Document, Chunk, Query, Evaluation, Experiment records
- JSONB columns for `custom` fields and flexible metadata
- Indexed fields: `document_id`, `created_at`, `source_type`, `tags` (GIN), `language`

### In Experiment Tracker (MLflow/W&B)
- Config snapshots, metrics, artifacts
- Run-level tags for filtering experiments

### In Object Storage (S3/MinIO)
- Large artifacts: datasets, model checkpoints, full prediction logs
- Partitioned by `experiment_name/run_id/`

---

## Schema Evolution

### Versioning
- Each entity has `schema_version: str` (semver)
- Backward compatible changes: MINOR version bump
- Breaking changes: MAJOR version bump, migration required

### Migration Strategy
```python
# backend/data/models/migrations.py
MIGRATIONS = {
    "1.0": lambda doc: doc,  # Identity
    "1.1": migrate_v1_0_to_v1_1,
    "1.2": migrate_v1_1_to_v1_2,
}

def migrate_document(doc: dict, target_version: str) -> dict:
    current = doc.get("schema_version", "1.0")
    for version in sorted(MIGRATIONS.keys()):
        if version > current:
            doc = MIGRATIONS[version](doc)
    doc["schema_version"] = target_version
    return doc
```

### Deprecation Policy
- Fields marked `deprecated: true` in schema
- Removed after 2 minor versions
- Migration scripts provided

---

## Example: Complete Document Lifecycle Metadata

```json
{
  "document": {
    "id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b6",
    "content": "Full document text...",
    "metadata": {
      "title": "Annual Report 2025",
      "author": "Finance Team",
      "language": "en",
      "char_count": 45231,
      "token_count_estimate": 11308,
      "structure": {
        "headings": [
          {"level": 1, "text": "Executive Summary", "start_char": 0, "end_char": 18},
          {"level": 2, "text": "Financial Highlights", "start_char": 1245, "end_char": 1265}
        ]
      },
      "tags": ["finance", "annual-report", "2025"],
      "custom": {"department": "finance", "fiscal_year": 2025}
    },
    "source": {
      "type": "FILE",
      "path": "/data/reports/annual_2025.pdf",
      "checksum": "a1b2c3d4e5f6...",
      "size_bytes": 2048576,
      "mime_type": "application/pdf"
    }
  },
  "chunks": [
    {
      "id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b7",
      "document_id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b6",
      "content": "Executive Summary\n\nThe fiscal year 2025...",
      "metadata": {
        "chunking_strategy": "markdown",
        "chunk_index": 0,
        "start_char": 0,
        "end_char": 512,
        "token_count": 128,
        "heading_path": ["Executive Summary"],
        "heading_level": 1,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536
      }
    }
  ],
  "vector_record": {
    "id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b7",
    "vector": [0.023, -0.045, ...],
    "chunk_id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b7",
    "document_id": "018f1a2b-3c4d-7e8f-9a0b-c1d2e3f4a5b6",
    "document_title": "Annual Report 2025",
    "content": "Executive Summary\n\nThe fiscal year 2025...",
    "chunk_index": 0,
    "source_type": "FILE",
    "language": "en",
    "tags": ["finance", "annual-report", "2025"],
    "created_at": "2026-01-15T10:30:00Z"
  }
}
```