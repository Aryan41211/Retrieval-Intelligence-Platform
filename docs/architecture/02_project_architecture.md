# Project Architecture

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         RETRIEVAL INTELLIGENCE PLATFORM                            │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                        API LAYER                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   /ingest   │  │  /query     │  │  /evaluate  │  │ /experiments│  │  /health    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                             │
│                                                    ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                       CORE LAYER                                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
│  │  │  Interfaces  │ │  Exceptions  │ │   Events     │ │  Utilities   │ │   Types      │   │   │
│  │  │  (Protocols) │ │              │ │              │ │              │ │              │   │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                             │
│                    ┌─────────────────────────────┼─────────────────────────────┐               │
│                    ▼                             ▼                             ▼               │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐ │
│  │      INGESTION PIPELINE      │ │      QUERY PIPELINE          │ │   EVALUATION PIPELINE       │ │
│  │  ┌───────────────────────┐  │ │  ┌───────────────────────┐  │ │  ┌───────────────────────┐  │ │
│  │  │ Data Loaders          │  │ │  │ Query Expansion       │  │ │  │ Metrics Computation   │  │ │
│  │  │ - PDF, DOCX, HTML...  │  │ │  │ - Rewrite, HyDE       │  │ │  │ - RAGAS, DeepEval     │  │ │
│  │  └───────────────────────┘  │ │  └───────────────────────┘  │ │  └───────────────────────┘  │ │
│  │  ┌───────────────────────┐  │ │  ┌───────────────────────┐  │ │  ┌───────────────────────┐  │ │
│  │  │ Preprocessing         │  │ │  │ Retrieval             │  │ │  │ Experiment Tracking   │  │ │
│  │  │ - Clean, normalize    │  │ │  │ - Dense + Sparse      │  │ │  │ - MLflow, W&B         │  │ │
│  │  └───────────────────────┘  │ │  │ - Hybrid fusion       │  │ │  └───────────────────────┘  │ │
│  │  ┌───────────────────────┐  │ │  └───────────────────────┘  │ │  ┌───────────────────────┐  │ │
│  │  │ Chunking              │  │ │  ┌───────────────────────┐  │ │  │ Reporting             │  │ │
│  │  │ - Fixed, recursive,   │  │ │  │ Reranking             │  │ │  │ - Dashboards, exports │  │ │
│  │  │   semantic, markdown  │  │ │  │ - Cross-encoder       │  │ │  └───────────────────────┘  │ │
│  │  └───────────────────────┘  │ │  │ - Cohere, Jina        │  │ └─────────────────────────────┘ │
│  │  ┌───────────────────────┐  │ │  └───────────────────────┘  │ │                               │
│  │  │ Embeddings            │  │ │  ┌───────────────────────┐  │ │                               │
│  │  │ - Multiple providers  │  │ │  │ Generation            │  │ │                               │
│  │  │ - Batch, cache        │  │ │  │ - Grounded, streaming │  │ │                               │
│  │  └───────────────────────┘  │ │  │ - Citations           │  │ │                               │
│  │  ┌───────────────────────┐  │ │  │ - Verification        │  │ │                               │
│  │  │ Vector Store          │  │ │  └───────────────────────┘  │ │                               │
│  │  │ - Upsert, index       │  │ └─────────────────────────────┘ │                               │
│  │  │ - Metadata, BM25      │  │                                │                               │
│  │  └───────────────────────┘  │                                │                               │
│  └─────────────────────────────┘                                │                               │
│                                    │                             │                               │
│                                    └─────────────────────────────┘                               │
│                                                   │                                             │
│                                                   ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                     INFRASTRUCTURE LAYER                                    │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
│  │  │  PostgreSQL  │ │    Redis     │ │ Vector Store │ │ Object Store │ │  Message     │   │   │
│  │  │  (Metadata)  │ │   (Cache)    │ │  (FAISS,     │ │  (S3/MinIO)  │ │  Queue       │   │   │
│  │  │              │ │              │ │   Chroma,    │ │              │ │  (Celery/    │   │   │
│  │  │              │ │              │ │   Pinecone)  │ │              │ │   RabbitMQ)  │   │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (`backend/api/`)
- **Routes**: REST endpoints for ingestion, query, evaluation, experiments
- **Schemas**: Request/response Pydantic models (separate from domain models)
- **Dependencies**: FastAPI dependency injection for services, auth, rate limiting
- **Middleware**: Correlation ID, request logging, error handling, CORS

### Core Layer (`backend/core/`)
- **Protocols**: Abstract base classes defining component interfaces
- **Exceptions**: Domain-specific exception hierarchy
- **Events**: Event definitions for observability (ingestion_started, retrieval_completed, etc.)
- **Types**: Shared type definitions, type variables, generic bases

### Data Pipeline Layers (`backend/data/<stage>/`)
Each stage follows the same pattern:
```
backend/data/<stage>/
├── __init__.py           # Exports public API
├── interfaces.py         # Stage-specific protocols (optional, usually in core)
├── base.py              # Base implementation with common logic
├── <impl1>.py           # Concrete implementation 1
├── <impl2>.py           # Concrete implementation 2
├── factory.py           # Factory for creating instances from config
├── schemas.py           # Stage-specific Pydantic models (if needed)
└── utils.py             # Stage-specific utilities
```

### Models Layer (`backend/data/models/`)
- **Domain models**: Canonical Pydantic models for documents, chunks, queries, results
- **Enums**: Shared enumerations (DocumentSource, ChunkingStrategy, etc.)
- **Validation**: Cross-field validators, computed fields

### Configs Layer (`backend/configs/`)
- **settings.py**: Pydantic Settings with nested config classes
- **validation.py**: Custom validators, cross-field validation
- **feature_flags.py**: Feature flag definitions and runtime checks

### Tests Layer (`backend/tests/`)
Mirrors backend structure:
```
backend/tests/
├── unit/
│   ├── test_core/
│   ├── test_data/
│   │   ├── test_loaders/
│   │   ├── test_preprocessing/
│   │   ├── test_chunking/
│   │   ├── test_embeddings/
│   │   ├── test_vectorstore/
│   │   ├── test_retrieval/
│   │   ├── test_generation/
│   │   ├── test_evaluation/
│   │   └── test_experiments/
│   └── test_configs/
├── integration/
│   ├── test_ingestion_pipeline.py
│   ├── test_query_pipeline.py
│   └── test_evaluation_pipeline.py
├── fixtures/
│   ├── documents/
│   └── expected/
└── conftest.py
```

## Interface Definitions

### Core Protocols (`backend/core/protocols.py`)

```python
from typing import Protocol, AsyncIterator, Generic, TypeVar
from backend.data.models import Document, Chunk, Query, RetrievalResult, GenerationResult

T = TypeVar('T')

class DocumentLoader(Protocol):
    async def load(self, source: DocumentSource) -> list[Document]: ...

class TextPreprocessor(Protocol):
    def process(self, text: str) -> str: ...

class Chunker(Protocol):
    def chunk(self, document: Document) -> list[Chunk]: ...

class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[Vector]: ...
    async def embed_query(self, text: str) -> Vector: ...

class VectorStore(Protocol):
    async def upsert(self, chunks: list[Chunk]) -> None: ...
    async def search(self, query: Vector, top_k: int, filter: Optional[MetadataFilter]) -> list[Chunk]: ...
    async def delete(self, ids: list[UUID]) -> None: ...

class Retriever(Protocol):
    async def retrieve(self, query: Query) -> list[RetrievalResult]: ...

class Reranker(Protocol):
    async def rerank(self, query: str, results: list[RetrievalResult], top_n: int) -> list[RetrievalResult]: ...

class Generator(Protocol):
    async def generate(self, query: str, context: list[RetrievalResult]) -> GenerationResult: ...
    async def stream_generate(self, query: str, context: list[RetrievalResult]) -> AsyncIterator[str]: ...

class Evaluator(Protocol):
    async def evaluate(self, dataset: EvaluationDataset) -> EvaluationResult: ...

class ExperimentTracker(Protocol):
    def log_params(self, params: dict) -> None: ...
    def log_metrics(self, metrics: dict, step: Optional[int] = None) -> None: ...
    def log_artifact(self, path: str) -> None: ...
```

## Data Flow Between Layers

### Ingestion Pipeline Data Flow

```
DocumentSource
      │
      ▼
┌─────────────┐     Document (id, content, metadata, source)
│  Loader     │──────────────────────────────────────────────▶
└─────────────┘
      │
      ▼
┌─────────────┐     Document (cleaned content, enriched metadata)
│ Preprocessor│──────────────────────────────────────────────▶
└─────────────┘
      │
      ▼
┌─────────────┐     List[Chunk] (id, document_id, content, position, metadata)
│  Chunker    │──────────────────────────────────────────────▶
└─────────────┘
      │
      ▼
┌─────────────┐     List[Chunk] (with embeddings populated)
│  Embedder   │──────────────────────────────────────────────▶
└─────────────┘
      │
      ▼
┌─────────────┐     UpsertResult (success_count, failed_ids)
│Vector Store │──────────────────────────────────────────────▶
└─────────────┘
```

### Query Pipeline Data Flow

```
QueryRequest (query, filters, params)
      │
      ▼
┌─────────────────┐     ExpandedQuery (original, sub_queries, hypothetical_docs)
│ Query Expander  │──────────────────────────────────────────────────▶
└─────────────────┘
      │
      ▼
┌─────────────────┐     List[RetrievalResult] (chunk, score, retrieval_method)
│    Retriever    │──────────────────────────────────────────────────▶
└─────────────────┘
      │
      ▼
┌─────────────────┐     List[RetrievalResult] (reranked, top_n)
│    Reranker     │──────────────────────────────────────────────────▶
└─────────────────┘
      │
      ▼
┌─────────────────┐     GenerationResult (answer, citations, metadata)
│    Generator    │──────────────────────────────────────────────────▶
└─────────────────┘
      │
      ▼
QueryResponse (answer, citations, retrieval_metadata, generation_metadata)
```

## Dependency Injection Container

FastAPI dependencies provide instances based on configuration:

```python
# backend/api/dependencies.py
from functools import lru_cache
from backend.configs.settings import get_settings
from backend.data.loaders.factory import get_loader
from backend.data.embeddings.factory import get_embedding_provider
from backend.data.vectorstore.factory import get_vector_store
from backend.data.retrieval.factory import get_retriever
from backend.data.generation.factory import get_generator

@lru_cache()
def get_document_loader() -> DocumentLoader:
    settings = get_settings()
    return get_loader(settings.data.loader_type)

@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return get_embedding_provider(settings.embeddings.provider)

@lru_cache()
def get_vector_store() -> VectorStore:
    settings = get_settings()
    return get_vector_store(settings.vector_store.provider)

def get_retriever_service(
    vector_store: VectorStore = Depends(get_vector_store),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> Retriever:
    settings = get_settings()
    return get_retriever(settings.retrieval, vector_store, embedder)
```

## Configuration Structure

```
backend/configs/
├── __init__.py
├── settings.py           # Main Settings class with nested configs
├── validation.py         # Custom validators
├── feature_flags.py      # FeatureFlag enum, is_enabled()
└── logging_config.py     # Structlog configuration
```

Settings hierarchy:
```python
class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    data: DataSettings = DataSettings()
    embeddings: EmbeddingSettings = EmbeddingSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    generation: GenerationSettings = GenerationSettings()
    evaluation: EvaluationSettings = EvaluationSettings()
    experiments: ExperimentSettings = ExperimentSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    security: SecuritySettings = SecuritySettings()
```

## Error Handling Strategy

### Exception Hierarchy
```
RipError (base)
├── ConfigurationError
├── DataError
│   ├── LoaderError
│   ├── PreprocessingError
│   ├── ChunkingError
│   └── EmbeddingError
├── RetrievalError
│   ├── VectorStoreError
│   ├── SearchError
│   └── RerankError
├── GenerationError
│   ├── LLMError
│   ├── PromptError
│   └── CitationError
├── EvaluationError
└── ExperimentError
```

### Error Response Format
```json
{
  "error": {
    "code": "RETRIEVAL_SEARCH_FAILED",
    "message": "Vector search timeout after 5s",
    "details": {
      "stage": "retrieval",
      "operation": "dense_search",
      "latency_ms": 5000
    },
    "correlation_id": "abc-123",
    "timestamp": "2026-06-27T10:30:00Z"
  }
}
```

## Async Execution Model

- **API Layer**: Fully async (FastAPI native)
- **Pipeline Stages**: Async for I/O-bound operations (embeddings, vector search, LLM calls)
- **CPU-bound**: Run in thread pool (chunking, preprocessing, BM25)
- **Batching**: Automatic batching for embedding and generation where supported
- **Concurrency Control**: Semaphores for external API rate limits

## Testing Strategy by Layer

| Layer | Test Types | Coverage Target |
|-------|------------|-----------------|
| Core | Unit (interfaces, exceptions, types) | 100% |
| Loaders | Unit (mocked sources), Integration (real files) | 90% |
| Preprocessing | Unit (pure functions), Property-based | 95% |
| Chunking | Unit (strategy outputs), Golden files | 90% |
| Embeddings | Unit (mocked providers), Integration (real APIs) | 85% |
| Vector Store | Unit (mocked), Integration (real stores) | 90% |
| Retrieval | Unit (algorithms), Integration (end-to-end) | 85% |
| Generation | Unit (prompt building), Integration (real LLMs) | 80% |
| Evaluation | Unit (metrics), Integration (full datasets) | 85% |
| API | Contract tests, Integration (TestClient) | 90% |

## Module Communication Rules

1. **No direct imports** between `backend/data/<stage>/` modules
2. **Core protocols only** for cross-stage dependencies
3. **Factory pattern** for instantiation (config-driven)
4. **Domain models** from `backend/data/models/` for data exchange
5. **Events** for side effects (logging, metrics, experiment tracking)

## Extension Guidelines

To add a new implementation:
1. Create `<name>.py` in appropriate `backend/data/<stage>/`
2. Implement the protocol from `backend/core/protocols.py`
3. Register in `factory.py` with a string key
4. Add config option in `backend/configs/settings.py`
5. Write tests in `backend/tests/unit/test_data/test_<stage>/`
6. Update documentation in `docs/architecture/`