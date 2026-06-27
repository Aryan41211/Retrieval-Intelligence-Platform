# Folder Structure

## Overview

This document explains the directory layout of the Retrieval Intelligence Platform, including the purpose of each folder, its contents, and the rules governing what should and should NOT be placed inside.

## Root Directory

```
retrieval-intelligence-platform/
├── backend/               # Core Python application
├── frontend/              # Streamlit/Next.js UI
├── docs/                  # Documentation
├── scripts/               # Operational scripts
├── notebooks/             # Exploration and prototyping
├── assets/                # Static assets
├── tests/                 # Integration/E2E tests (optional)
├── .env.example           # Environment variable template
├── pyproject.toml         # Python project configuration
├── requirements.txt       # Pinned dependencies
└── README.md              # Project overview
```

## Backend Structure

### `backend/` - Core Application

```
backend/
├── api/                   # HTTP interface layer
├── core/                  # Protocols, exceptions, types
├── configs/               # Configuration management
├── data/                  # Pipeline stage implementations
│   ├── loaders/           # Document loading
│   ├── preprocessing/     # Text cleaning
│   ├── chunking/          # Document segmentation
│   ├── embeddings/        # Embedding providers
│   ├── vectorstore/       # Vector database abstractions
│   ├── retrieval/         # Search algorithms
│   ├── reranking/         # Result re-scoring
│   ├── generation/        # LLM generation
│   ├── evaluation/        # Quality metrics
│   ├── experiments/       # Experiment tracking
│   ├── prompts/           # Prompt templates
│   ├── models/            # Domain models
│   └── utils/             # Shared utilities
└── tests/                 # Test suite
```

---

## Detailed Folder Specifications

### `backend/api/` - API Layer

**Purpose**: HTTP interface, request validation, response formatting, authentication, and rate limiting.

**Contents**:
- `routes/` - FastAPI endpoint definitions
- `schemas/` - Request/response Pydantic models (API contracts)
- `dependencies.py` - Dependency injection providers
- `middleware/` - Custom middleware (correlation ID, logging, errors)
- `main.py` - FastAPI application entry point

**What GOES inside**:
- Route handlers (one file per resource)
- Schema models for API serialization
- Dependency providers
- Middleware implementations
- API versioning logic

**What NEVER goes inside**:
- Business logic (belongs in data layer)
- Direct database/vector store calls
- Model definitions (use `backend/data/models/`)
- Configuration loading logic (use `backend/configs/`)

---

### `backend/core/` - Core Layer

**Purpose**: Zero-dependency core contracts. Defines the "language" of the system.

**Contents**:
- `protocols.py` - Abstract base classes (interfaces)
- `exceptions.py` - Exception hierarchy
- `events.py` - Event definitions for observability
- `types.py` - Type variables, generics, shared types
- `utils.py` - Pure utility functions (no I/O)

**What GOES inside**:
- Protocol/ABC definitions only
- Exception classes
- Event dataclasses
- Type aliases and generics
- Stateless utility functions

**What NEVER goes inside**:
- Any external library imports
- Configuration dependencies
- Business logic
- I/O operations (file, network, database)
- Concrete implementations

---

### `backend/configs/` - Configuration Layer

**Purpose**: Settings management with validation, feature flags, and environment variable handling.

**Contents**:
- `settings.py` - Main Settings class with nested configs
- `validation.py` - Custom validators and cross-field validation
- `feature_flags.py` - Feature flag definitions
- `logging_config.py` - Structlog configuration
- `__init__.py` - Settings accessor functions

**What GOES inside**:
- Pydantic Settings models
- Environment variable parsing
- Custom validators
- Feature flag helpers
- Logging configuration

**What NEVER goes inside**:
- Business logic
- I/O operations (except reading env vars)
- Secret defaults (must fail if not provided)

---

### `backend/data/loaders/` - Document Loading

**Purpose**: Extract text and metadata from various source formats.

**Contents**:
- `base.py` - Base loader with common logic
- `pdf.py`, `docx.py`, `pptx.py`, `xlsx.py` - Format-specific loaders
- `html.py`, `markdown.py`, `text.py` - Text-based loaders
- `factory.py` - LoaderFactory for instantiation
- `registry.py` - Loader registration/auto-discovery

**What GOES inside**:
- One file per document format
- Loader implementations
- Factory and registry patterns
- Format-specific error handling

**What NEVER goes inside**:
- Generic preprocessing (belongs in `preprocessing/`)
- Chunking logic
- Embedding calls

---

### `backend/data/preprocessing/` - Text Preprocessing

**Purpose**: Clean, normalize, and enrich document text.

**Contents**:
- `pipeline.py` - PreprocessingPipeline orchestrator
- `normalize.py` - Unicode/whitespace normalization
- `boilerplate.py` - Header/footer removal
- `language.py` - Language detection
- `structure.py` - Markdown/HTML structure extraction
- `pii.py` - PII detection/redaction (optional)
- `factory.py` - Pipeline construction

**What GOES inside**:
- Atomic preprocessing steps (one per file)
- Pipeline composition logic
- Text transformation utilities
- Pattern-based cleaners

**What NEVER goes inside**:
- Chunk boundary detection
- Embedding generation
- File I/O (beyond reading patterns)

---

### `backend/data/chunking/` - Document Chunking

**Purpose**: Split documents into retrieval-ready chunks.

**Contents**:
- `base.py` - BaseChunker with overlap handling
- `fixed.py` - Fixed-size chunking
- `recursive.py` - Recursive character splitting
- `semantic.py` - Semantic boundary detection
- `markdown.py` - Heading-aware splitting
- `sentence.py` - Sentence-boundary aware
- `factory.py` - ChunkerFactory

**What GOES inside**:
- One file per chunking strategy
- Strategy implementations
- Token counting logic
- Overlap calculation

**What NEVER goes inside**:
- Embedding calls
- Vector operations
- Document loading

---

### `backend/data/embeddings/` - Embedding Generation

**Purpose**: Generate dense vector representations for text.

**Contents**:
- `base.py` - BaseEmbedder with batching/caching
- `openai.py`, `cohere.py`, `voyage.py` - API providers
- `sentence_transformers.py` - Local model provider
- `cache.py` - Redis/in-memory caching layer
- `factory.py` - EmbedderFactory

**What GOES inside**:
- Provider-specific implementations
- Batching logic
- Caching mechanisms
- Normalization utilities

**What NEVER goes inside**:
- Vector store operations
- Chunking logic
- Business rules about what to embed

---

### `backend/data/vectorstore/` - Vector Storage

**Purpose**: Persist and query vector embeddings with metadata.

**Contents**:
- `base.py` - BaseVectorStore interface
- `faiss.py`, `chroma.py`, `pinecone.py`, `weaviate.py`, `qdrant.py` - Provider implementations
- `bm25.py` - Sparse index management
- `factory.py` - VectorStoreFactory
- `schema.py` - Vector record definitions

**What GOES inside**:
- One file per vector store provider
- CRUD operations
- Hybrid search coordination
- Index management

**What NEVER goes inside**:
- Embedding generation
- Chunking logic
- Retrieval algorithm implementation (beyond fusion)

---

### `backend/data/retrieval/` - Retrieval Engine

**Purpose**: Find relevant chunks for queries using search algorithms.

**Contents**:
- `dense.py` - Dense vector retrieval
- `sparse.py` - BM25 sparse retrieval
- `hybrid.py` - Hybrid fusion algorithms
- `query_expansion/` - Query expansion subpackage
- `factory.py` - RetrieverFactory

**What GOES inside**:
- Search algorithm implementations
- Query expansion subpackage
- Hybrid fusion logic (RRF, weighted)

**What NEVER goes inside**:
- LLM calls (except for query expansion)
- Citation generation
- Response formatting

---

### `backend/data/reranking/` - Reranking

**Purpose**: Re-score retrieval results for higher precision.

**Contents**:
- `cohere.py`, `jina.py` - API rerankers
- `cross_encoder.py` - Sentence-transformers reranker
- `bge_reranker.py` - BGE reranker
- `factory.py` - RerankerFactory

**What GOES inside**:
- Reranker implementations
- Score normalization utilities
- Batch processing logic

**What NEVER goes inside**:
- Retrieval logic
- Generation code

---

### `backend/data/generation/` - Answer Generation

**Purpose**: Generate grounded answers with citations using LLMs.

**Contents**:
- `base.py` - BaseGenerator with prompt building
- `openai.py`, `anthropic.py`, `ollama.py`, `vllm.py`, `tgi.py` - Provider implementations
- `citation.py` - CitationExtractor
- `verification.py` - GroundingVerifier
- `factory.py` - GeneratorFactory

**What GOES inside**:
- LLM provider implementations
- Prompt building and rendering
- Citation extraction
- Streaming support

**What NEVER goes inside**:
- Retrieval logic
- Embedding generation
- Vector operations

---

### `backend/data/evaluation/` - Evaluation Framework

**Purpose**: Automated quality assessment using standard and custom metrics.

**Contents**:
- `datasets/` - Dataset loading utilities
- `metrics/` - Metric implementations
- `computer.py` - MetricsComputer
- `runner.py` - EvaluationRunner
- `reporting.py` - Report generation
- `factory.py` - Factory for metrics/datasets

**What GOES inside**:
- Metric implementations (RAGAS, custom, etc.)
- Dataset loaders
- Report generators

**What NEVER goes inside**:
- Business logic about "good" vs "bad" results
- Data access beyond dataset loading

---

### `backend/data/experiments/` - Experiment Tracking

**Purpose**: Track experiments with full reproducibility.

**Contents**:
- `tracker.py` - Protocol definition
- `mlflow_tracker.py` - MLflow implementation
- `wandb_tracker.py` - W&B implementation
- `context.py` - TrackedPipeline context manager
- `factory.py` - TrackerFactory

**What GOES inside**:
- Tracker implementations
- Context management
- Run/artifact handling

**What NEVER goes inside**:
- Evaluation logic (only consumes results)
- Business logic

---

### `backend/data/prompts/` - Prompt Management

**Purpose**: Template and prompt configuration management.

**Contents**:
- `templates/` - Jinja2 template files
- `registry.py` - PromptRegistry
- `versioning.py` - Prompt version management
- `few_shot.py` - Few-shot example management

**What GOES inside**:
- Template files (.j2)
- Template loading/rendering logic
- Version management

**What NEVER goes inside**:
- LLM API calls
- Business rules

---

### `backend/data/models/` - Domain Models

**Purpose**: Canonical Pydantic models for data contracts.

**Contents**:
- `document.py` - Document, DocumentMetadata, DocumentSource
- `chunk.py` - Chunk, ChunkMetadata
- `retrieval.py` - RetrievalResult, ExpandedQuery
- `generation.py` - GenerationResult, Citation
- `query.py` - QueryRequest, QueryResponse
- `evaluation.py` - EvaluationDataset, EvaluationResult
- `experiment.py` - ExperimentRun, Artifact
- `enums.py` - All enumerations
- `vector.py` - Vector types

**What GOES inside**:
- Pydantic model definitions only
- Enumerations
- Type definitions

**What NEVER goes inside**:
- Methods that do I/O
- Business logic
- Configuration

---

### `backend/data/utils/` - Shared Utilities

**Purpose**: Reusable utilities used across multiple stages.

**Contents**:
- `tokenize.py` - Token counting, truncation
- `hash.py` - Content hashing
- `text.py` - Text utilities
- `async.py` - Async utilities
- `metrics.py` - Prometheus helpers
- `validation.py` - Common validators

**What GOES inside**:
- Pure functions
- Statistical utilities
- Hash functions
- Async helpers

**What NEVER goes inside**:
- Stage-specific logic
- I/O operations (except where unavoidable)

---

### `tests/` - Test Suite

**Purpose**: Comprehensive testing for all backend modules.

**Contents**:
- `unit/` - Unit tests (mirrors backend structure)
- `integration/` - Cross-module integration tests
- `fixtures/` - Test data and mock objects
- `conftest.py` - Pytest configuration and shared fixtures

**What GOES inside**:
- Test files only
- Test data, fixtures
- Mock implementations

**What NEVER goes inside**:
- Production code
- Development scripts

---

## Extension Guidelines

When adding new functionality:

1. **New format loader**: Add to `backend/data/loaders/`, register in factory
2. **New chunking strategy**: Add to `backend/data/chunking/`, register in factory
3. **New embedding provider**: Add to `backend/data/embeddings/`, register in factory
4. **New vector store**: Add to `backend/data/vectorstore/`, register in factory
5. **New retrieval method**: Add to `backend/data/retrieval/`, register in factory
6. **New LLM provider**: Add to `backend/data/generation/`, register in factory
7. **New metric**: Add to `backend/data/evaluation/metrics/`, register in registry
8. **New experiment tracker**: Add to `backend/data/experiments/`, register in factory

Each extension requires:
- Protocol implementation in `backend/data/<stage>/<name>.py`
- Factory registration in `backend/data/<stage>/factory.py`
- Config options in `backend/configs/settings.py`
- Tests in `backend/tests/unit/test_data/test_<stage>/`
- Documentation update in this file