# Architecture Overview

## System Context

The Retrieval Intelligence Platform (RIP) is a modular, production-grade Retrieval-Augmented Generation (RAG) system designed for enterprise deployment. It separates concerns across distinct pipeline stages, enabling independent scaling, testing, and replacement of components.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL INTELLIGENCE PLATFORM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌────────────┐           │
│  │  Data    │   │ Preprocessing│   │ Chunking │   │ Embeddings │           │
│  │ Ingestion│──▶│  & Cleaning  │──▶│          │──▶│            │           │
│  └──────────┘   └──────────────┘   └──────────┘   └──────┬─────┘           │
│                                                           │                  │
│                                                           ▼                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────┐   ┌────────────┐      │
│  │ Vector Store │◀──│  Retrieval   │◀──│  Query   │   │ Generation │      │
│  │              │   │              │   │ Expand   │   │ (Grounded) │      │
│  └──────┬───────┘   └──────┬───────┘   └──────────┘   └──────┬─────┘      │
│         │                  │                                 │             │
│         │                  ▼                                 ▼             │
│         │           ┌──────────────┐                 ┌────────────┐       │
│         │           │  Reranking   │                 │  Evaluation│       │
│         │           └──────────────┘                 │  & Metrics │       │
│         │                                            └────────────┘       │
│         ▼                                                 │              │
│  ┌──────────────┐                                         ▼              │
│  │ Experiment   │                                ┌────────────┐         │
│  │ Tracking     │                                │ Citation & │         │
│  │ (MLflow/W&B) │                                │ Explain    │         │
│  └──────────────┘                                └────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. Separation of Concerns
Each pipeline stage is an independent module with well-defined interfaces. Stages communicate only through validated data contracts (Pydantic models).

### 2. Interface-Driven Development
Abstract base classes in `backend/core/` define contracts. Concrete implementations live in `backend/data/<stage>/`. This enables:
- Swapping implementations without changing downstream code
- Testing with mock implementations
- Running multiple implementations in parallel (A/B testing)

### 3. Configuration Over Convention
All behavior is controlled via environment variables (`.env`) validated by Pydantic Settings. No hardcoded values in business logic.

### 4. Observability by Default
Every stage emits structured logs, metrics, and traces. Experiment tracking captures full lineage: config → data → model → metrics.

### 5. Failure Isolation
Stage failures are caught, logged, and converted to structured error responses. Downstream stages receive explicit failure signals rather than exceptions.

## Module Boundaries

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **API** | `backend/api/` | HTTP endpoints, request/response validation, auth |
| **Core** | `backend/core/` | Abstract interfaces, base classes, domain exceptions |
| **Configs** | `backend/configs/` | Settings management, validation, feature flags |
| **Data Pipeline** | `backend/data/<stage>/` | Stage implementations, processors, utilities |
| **Models** | `backend/data/models/` | Pydantic schemas for data contracts |
| **Tests** | `backend/tests/` | Mirrors backend structure; unit + integration |

## Data Contracts

All inter-stage communication uses Pydantic models defined in `backend/data/models/`:

```python
# Example: Document schema
class Document(BaseModel):
    id: UUID
    content: str
    metadata: DocumentMetadata
    source: DocumentSource
    created_at: datetime
    updated_at: datetime

# Example: Chunk schema
class Chunk(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    start_char: int
    end_char: int
    metadata: ChunkMetadata
    embedding: Optional[Vector] = None
```

## Dependency Flow

```
backend/core (interfaces)
       ▲
       │ implements
       │
backend/data/loaders          backend/data/preprocessing
backend/data/chunking         backend/data/embeddings
backend/data/vectorstore      backend/data/retrieval
backend/data/reranking        backend/data/generation
backend/data/evaluation       backend/data/experiments
backend/data/prompts          backend/data/models
backend/data/utils
       │
       │ uses
       ▼
backend/configs (settings)
       │
       │ configures
       ▼
backend/api (routes, dependencies)
```

## Runtime Architecture

### Request Flow (Query Time)

```
HTTP Request
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI)                                         │
│  - Validate request                                          │
│  - Extract correlation ID                                    │
│  - Inject dependencies                                       │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Query Expansion (optional)                                  │
│  - Rewrite query                                             │
│  - Generate sub-queries                                      │
│  - Hypothetical document embeddings (HyDE)                   │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Retrieval                                                    │
│  - Dense vector search                                       │
│  - Sparse (BM25) search                                      │
│  - Hybrid fusion (RRF, weighted)                             │
│  - Return top-K candidates                                   │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Reranking (optional)                                         │
│  - Cross-encoder scoring                                     │
│  - Cohere/Jina rerankers                                     │
│  - Return top-N                                              │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Generation                                                   │
│  - Build prompt with citations                               │
│  - Call LLM (streaming or sync)                              │
│  - Post-process: extract citations, verify grounding         │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Response Assembly                                            │
│  - Format answer with citations                              │
│  - Include retrieval metadata (explanations)                 │
│  - Emit metrics                                              │
└──────────────────────────────────────────────────────────────┘
```

### Ingestion Flow (Index Time)

```
Source Documents
       │
       ▼
┌──────────────────┐
│  Loader          │  (PDF, DOCX, HTML, MD, TXT, PPTX, XLSX)
│  - Extract text  │
│  - Preserve metadata (author, date, structure)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Preprocessor    │
│  - Clean text    │
│  - Normalize unicode, whitespace
│  - Remove boilerplate
│  - Language detection
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Chunker         │
│  - Fixed-size    │
│  - Recursive     │
│  - Semantic      │
│  - Markdown-aware│
│  - Preserve overlap
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Embedder        │
│  - Batch encode  │
│  - Multiple providers (OpenAI, ST, Cohere, Voyage)
│  - Cache embeddings
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Vector Store    │
│  - Upsert vectors│
│  - Store metadata│
│  - Build BM25 index (if hybrid)
└──────────────────┘
```

## Configuration Architecture

Settings are organized by domain in `backend/configs/settings.py`:

```python
class Settings(BaseSettings):
    app: AppSettings
    data: DataSettings
    embeddings: EmbeddingSettings
    vector_store: VectorStoreSettings
    retrieval: RetrievalSettings
    generation: GenerationSettings
    evaluation: EvaluationSettings
    experiments: ExperimentSettings
    observability: ObservabilitySettings
    security: SecuritySettings
```

Each domain group validates its own subsection. Feature flags control optional pipeline stages.

## Observability Stack

| Concern | Tool | Purpose |
|---------|------|---------|
| **Logging** | structlog + JSON | Structured logs with correlation IDs |
| **Metrics** | Prometheus Client | Counters, histograms, gauges per stage |
| **Tracing** | OpenTelemetry | Distributed traces across stages |
| **Experiments** | MLflow / W&B | Parameter/metric/artifact tracking |
| **Alerting** | Grafana (planned) | SLO monitoring, anomaly detection |

## Security Considerations

- **No secrets in code**: All credentials via environment variables
- **Input validation**: Pydantic models on all API boundaries
- **Rate limiting**: Token bucket per client (configurable)
- **CORS**: Explicit allowlist, no wildcards in production
- **PII handling**: No logging of document content or queries
- **Dependency scanning**: `pip-audit` in CI

## Deployment Topology (Planned)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Load       │     │  API Pods   │     │  Worker     │
│  Balancer   │────▶│  (FastAPI)  │────▶│  Pool       │
│  (NGINX)    │     │  x3+        │     │  (Celery)   │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
              ┌────────────┼────────────┐      │
              ▼            ▼            ▼      ▼
         ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐
         │PostgreSQL│ │  Redis   │ │ Vector   │ │ Object  │
         │(Metadata)│ │ (Cache)  │ │ Store    │ │ Storage │
         └─────────┘ └──────────┘ └──────────┘ └─────────┘
```

## Scaling Strategy

| Component | Scaling Approach |
|-----------|------------------|
| API | Horizontal (stateless), connection pooling |
| Embedding | Batch inference, GPU workers, model caching |
| Vector Store | Sharding (by namespace), read replicas |
| Retrieval | Parallel dense + sparse, async I/O |
| Generation | vLLM/TGI for throughput, streaming responses |
| Workers | Celery + Redis, priority queues for ingestion |

## Extension Points

New implementations can be added without modifying core logic:

| Extension Point | Interface | Example Implementations |
|-----------------|-----------|------------------------|
| Document Loader | `DocumentLoader` | PDF, DOCX, HTML, Notion, Confluence, S3 |
| Preprocessor | `TextPreprocessor` | Cleaning, PII redaction, translation |
| Chunker | `Chunker` | Fixed, recursive, semantic, markdown |
| Embedder | `EmbeddingProvider` | OpenAI, Cohere, Voyage, ST, BGE, E5 |
| Vector Store | `VectorStore` | FAISS, Chroma, Pinecone, Weaviate, Qdrant |
| Retriever | `Retriever` | Dense, sparse, hybrid, multi-vector |
| Reranker | `Reranker` | Cross-encoder, Cohere, Jina, BGE-reranker |
| Generator | `Generator` | OpenAI, Anthropic, Ollama, vLLM, TGI |
| Evaluator | `Evaluator` | RAGAS, DeepEval, custom metrics |
| Experiment Tracker | `ExperimentTracker` | MLflow, W&B, ClearML |

## Version Compatibility

| Component | Minimum Version | Notes |
|-----------|-----------------|-------|
| Python | 3.11 | Type hints, `exception-group` |
| Pydantic | 2.7 | V2 only, no V1 compat |
| FastAPI | 0.110 | Native lifespan, dependency overrides |
| NumPy | 1.26 | Array API standard |
| PyTorch | 2.3 | For local embeddings/reranking |

## Future Architecture Decisions (ADRs)

Major decisions will be recorded in `docs/adr/`:
- ADR-001: Vector store abstraction strategy
- ADR-002: Async vs sync pipeline execution
- ADR-003: Experiment tracking backend selection
- ADR-004: Multi-tenancy model