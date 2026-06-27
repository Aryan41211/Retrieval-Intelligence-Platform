# System Overview

## Purpose

The Retrieval Intelligence Platform (RIP) is a production-grade Retrieval-Augmented Generation system designed for enterprise deployment. It provides a modular, observable, and extensible architecture for building RAG applications with emphasis on explainability, evaluation, and reproducibility.

## System Context

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          EXTERNAL SYSTEMS                                            │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│   │   Document   │    │   LLM        │    │   Embedding  │    │   Vector     │    │  Experiment│  │
│   │   Sources    │    │   Providers  │    │   Providers  │    │   Databases  │    │  Trackers  │  │
│   │  (Files,     │    │  (OpenAI,    │    │  (OpenAI,    │    │  (FAISS,     │    │  (MLflow,  │  │
│   │   URLs,      │    │   Anthropic, │    │   Cohere,    │    │   Chroma,    │    │   W&B)     │  │
│   │   APIs)      │    │   Ollama)    │    │   Voyage,    │    │   Pinecone,  │    │            │  │
│   │              │    │              │    │   Local)     │    │   Weaviate)  │    │            │  │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └─────┬──────┘  │
│          │                   │                   │                   │                   │         │
└──────────┼───────────────────┼───────────────────┼───────────────────┼───────────────────┼─────────┘
           │                   │                   │                   │                   │
           ▼                   ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RETRIEVAL INTELLIGENCE PLATFORM                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                        APPLICATION LAYER                                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐    │   │
│  │  │  Ingestion  │ │   Query     │ │ Evaluation  │ │ Experiment  │ │  Admin/Monitoring   │    │   │
│  │  │   API       │ │   API       │ │   API       │ │   API       │ │  (Health, Metrics)  │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                        ORCHESTRATION LAYER                                     │   │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────────────────┐  │   │
│  │  │ Ingestion       │ │ Query           │ │ Evaluation      │ │ Experiment Tracking       │  │   │
│  │  │ Pipeline        │ │ Pipeline        │ │ Pipeline        │ │ Service                   │  │   │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘ └───────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                        COMPONENT LAYER                                        │   │
│  │  ┌────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────────┐  │   │
│  │  │Loaders │ │Preprocess │ │Chunkers │ │Embedders │ │Vector   │ │Retriev │ │Generators  │  │   │
│  │  │        │ │ors        │ │         │ │          │ │Stores   │ │ers     │ │            │  │   │
│  │  └────────┘ └───────────┘ └─────────┘ └──────────┘ └─────────┘ └────────┘ └────────────┘  │   │
│  │  ┌────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────────────────────────┐  │   │
│  │  │Rerank- │ │Evaluators │ │Prompt   │ │Experiment│ │  Observability (Logging,         │  │   │
│  │  │ers     │ │           │ │Templates│ │Trackers  │ │  Metrics, Tracing)              │  │   │
│  │  └────────┘ └───────────┘ └─────────┘ └──────────┘ └───────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                        CORE LAYER                                             │   │
│  │  Interfaces (Protocols) • Domain Models • Exceptions • Events • Configuration • Utilities   │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Multi-format Ingestion** | PDF, DOCX, PPTX, XLSX, HTML, Markdown, Text, with extensible loader framework |
| **Flexible Preprocessing** | Unicode normalization, boilerplate removal, language detection, structure extraction |
| **Multiple Chunking Strategies** | Fixed, recursive, semantic, Markdown-aware, sentence-boundary |
| **Multi-provider Embeddings** | OpenAI, Cohere, Voyage AI, Sentence Transformers (local), with caching |
| **Pluggable Vector Stores** | FAISS, Chroma, Pinecone, Weaviate, Qdrant with unified interface |
| **Hybrid Retrieval** | Dense + sparse (BM25) with RRF/weighted fusion |
| **Reranking** | Cross-encoder, Cohere, Jina, BGE rerankers |
| **Grounded Generation** | Citations, hallucination detection, streaming support |
| **Automated Evaluation** | RAGAS, DeepEval, custom metrics with batch processing |
| **Experiment Tracking** | MLflow, Weights & Biases with full lineage |
| **Observability** | Structured logging, Prometheus metrics, OpenTelemetry tracing |

## Design Principles

### 1. Interface-Driven Architecture
All components implement protocols defined in `backend/core/protocols.py`. This enables:
- Zero-dependency core layer
- Runtime swapping of implementations
- Testability with mocks
- A/B testing multiple implementations

### 2. Configuration as Code
All behavior controlled via Pydantic Settings validated at startup:
- Environment variables for secrets
- YAML/JSON for complex config
- Feature flags for gradual rollout
- No hardcoded values in business logic

### 3. Explicit Data Contracts
Inter-component communication uses Pydantic models:
- Validation at boundaries
- Self-documenting schemas
- Versioning support
- IDE autocomplete

### 4. Observability by Default
Every pipeline stage emits:
- Structured JSON logs with correlation IDs
- Prometheus metrics (latency, throughput, errors)
- OpenTelemetry spans for distributed tracing
- Experiment tracking events

### 5. Failure Isolation
- Circuit breakers for external dependencies
- Graceful degradation (skip optional stages)
- Explicit error types per domain
- No silent failures

## Deployment Architecture

### Development
```
Single Process (uvicorn)
├── API Server
├── All Pipeline Components (in-process)
├── SQLite (metadata)
├── FAISS (vector store)
└── File-based MLflow
```

### Staging/Production
```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Load       │────▶│  API Pods        │────▶│  Worker Pool     │
│  Balancer   │     │  (FastAPI,       │     │  (Celery +       │
│  (NGINX)    │     │   stateless)     │     │   Redis)         │
└─────────────┘     └────────┬─────────┘     └────────┬─────────┘
                             │                        │
              ┌──────────────┼──────────────┐         │
              ▼              ▼              ▼         ▼
         ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐
         │PostgreSQL│ │  Redis    │ │  Vector  │ │  Object  │
         │(Metadata)│ │ (Cache,   │ │  Store   │ │  Storage │
         │          │ │  Queue)   │ │          │ │  (S3)    │
         └──────────┘ └───────────┘ └──────────┘ └──────────┘
```

## Scaling Characteristics

| Component | Scaling Model | Bottleneck |
|-----------|---------------|------------|
| API | Horizontal (stateless) | CPU (serialization) |
| Loaders | Horizontal (per document) | I/O, CPU (parsing) |
| Preprocessing | Horizontal | CPU (regex, NLP) |
| Chunking | Horizontal | CPU (tokenization) |
| Embedding | Horizontal (batch) | GPU/CPU (model inference) |
| Vector Store | Vertical (sharding) | Memory, Disk I/O |
| Retrieval | Horizontal (read replicas) | Vector search latency |
| Reranking | Horizontal (batch) | Model inference latency |
| Generation | Horizontal (vLLM/TGI) | GPU memory, queue depth |

## Security Model

```
┌─────────────────────────────────────────────────────────────────┐
│                      SECURITY BOUNDARIES                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Internet                                                        │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │  WAF/NGINX  │───▶│  API Gateway│───▶│  App Pods   │          │
│  │  (TLS,      │    │  (Auth,     │    │  (Validated │          │
│  │   Rate      │    │   CORS,     │    │   Input,    │          │
│  │   Limit)    │    │   SSL Term) │    │   No Secrets)          │
│  └─────────────┘    └─────────────┘    └──────┬──────┘          │
│                                                │                 │
│         ┌──────────────────────────────────────┼──────────────┐  │
│         ▼                                      ▼              ▼  │
│  ┌─────────────┐                        ┌─────────────┐ ┌──────────┐
│  │  Secrets    │                        │  Vector     │ │ Metadata │
│  │  Manager    │                        │  Store      │ │  DB      │
│  │  (Vault,    │                        │  (Network   │ │  (Auth,  │
│  │   AWS SM)   │                        │   Policies) │ │   Audit) │
│  └─────────────┘                        └─────────────┘ └──────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

- **Secrets**: Never in code/config, only in secret manager
- **Network**: Private subnets, security groups, mTLS for service-to-service
- **Data**: Encryption at rest (DB, object store), in transit (TLS 1.3)
- **Access**: RBAC for API, row-level security for multi-tenancy (planned)
- **Audit**: All queries logged with user ID, correlation ID, timestamp

## Compliance Considerations

| Requirement | Implementation |
|-------------|----------------|
| **GDPR** | Right to deletion (document/chunk removal), data minimization, consent tracking |
| **SOC 2** | Audit logging, access controls, encryption, incident response |
| **HIPAA** | BAAs with providers, PHI detection/redaction, audit trails (planned) |
| **Data Residency** | Configurable regions for vector stores, metadata DB, object storage |

## Operational Requirements

| Requirement | Target |
|-------------|--------|
| **Availability** | 99.9% (multi-AZ deployment) |
| **Query Latency (p95)** | < 2 seconds |
| **Ingestion Throughput** | 1000 docs/min (horizontal scaling) |
| **Index Freshness** | < 5 minutes (streaming ingestion) |
| **Recovery Time (RTO)** | < 15 minutes |
| **Recovery Point (RPO)** | < 1 minute (async replication) |

## Technology Stack Summary

| Layer | Technologies |
|-------|--------------|
| **Runtime** | Python 3.11+, asyncio |
| **API** | FastAPI, Pydantic v2, Uvicorn |
| **Data** | Polars, Pandas, NumPy, PyArrow |
| **ML** | PyTorch, Transformers, Sentence-Transformers |
| **Vector Search** | FAISS, Chroma, Pinecone, Weaviate, Qdrant |
| **Sparse Search** | rank-bm25 |
| **LLM** | OpenAI, Anthropic, Ollama, vLLM, TGI |
| **Evaluation** | RAGAS, DeepEval |
| **Tracking** | MLflow, Weights & Biases |
| **Observability** | structlog, Prometheus, OpenTelemetry, Grafana |
| **Orchestration** | Celery + Redis (async), Prefect (planned) |
| **Database** | PostgreSQL (prod), SQLite (dev), SQLAlchemy 2.0 |
| **Cache/Queue** | Redis |
| **Config** | Pydantic Settings, python-dotenv |
| **Quality** | Ruff, Black, MyPy, Pytest, Hypothesis |
| **CI/CD** | GitHub Actions, Docker, Helm (planned) |

## Project Structure

```
retrieval-intelligence-platform/
├── backend/
│   ├── api/              # FastAPI routes, schemas, dependencies
│   ├── core/             # Protocols, exceptions, events, types
│   ├── configs/          # Settings, validation, feature flags
│   ├── data/
│   │   ├── loaders/          # Document loading implementations
│   │   ├── preprocessing/    # Text cleaning, normalization
│   │   ├── chunking/         # Chunking strategies
│   │   ├── embeddings/       # Embedding providers
│   │   ├── vectorstore/      # Vector store abstractions
│   │   ├── retrieval/        # Retrieval algorithms
│   │   ├── reranking/        # Reranking implementations
│   │   ├── generation/       # LLM generation pipelines
│   │   ├── evaluation/       # Metrics, datasets, runners
│   │   ├── experiments/      # Experiment tracking
│   │   ├── prompts/          # Prompt templates
│   │   ├── models/           # Domain models (Pydantic)
│   │   └── utils/            # Shared utilities
│   └── tests/            # Unit + integration tests
├── frontend/             # Streamlit (dev), Next.js (prod planned)
├── docs/
│   ├── architecture/     # This documentation
│   └── adr/              # Architecture Decision Records
├── scripts/              # Operational scripts
├── notebooks/            # Exploration, prototyping
├── assets/               # Static assets
└── .github/              # CI/CD workflows
```

## Glossary

| Term | Definition |
|------|------------|
| **Document** | Source unit (PDF, web page, etc.) with content and metadata |
| **Chunk** | Sub-division of a document for embedding and retrieval |
| **Embedding** | Dense vector representation of text |
| **Vector Store** | Database optimized for vector similarity search |
| **Retrieval** | Finding relevant chunks for a query |
| **Reranking** | Re-scoring retrieval results for precision |
| **Generation** | LLM producing grounded answer with citations |
| **Grounding** | Verifying answer claims against retrieved context |
| **Citation** | Reference linking answer span to source chunk |
| **Hybrid Search** | Combining dense (vector) and sparse (BM25) retrieval |
| **RRF** | Reciprocal Rank Fusion for hybrid result merging |
| **HyDE** | Hypothetical Document Embeddings for query expansion |
| **Experiment** | Tracked pipeline run with config, metrics, artifacts |
| **Correlation ID** | Unique identifier tracing a request through all stages |