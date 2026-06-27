# Folder Structure

## Overview

This document provides a detailed breakdown of the complete folder structure for the Retrieval Intelligence Platform, explaining the purpose and contents of each directory and file.

---

## Root Directory

```
retrieval-intelligence-platform/
├── backend/                    # Backend application (Python)
├── frontend/                   # Frontend application (Streamlit/Next.js)
├── docs/                       # Documentation
├── scripts/                    # Operational scripts
├── assets/                     # Static assets (images, logos)
├── notebooks/                  # Jupyter notebooks for exploration
├── .github/                    # GitHub Actions workflows
├── .gitignore                  # Git ignore rules
├── .env.example                # Environment variable template
├── README.md                   # Project overview
├── LICENSE                     # MIT License
├── CHANGELOG.md                # Keep a Changelog format
├── CLAUDE.md                   # Development guide for AI assistants
├── pyproject.toml              # Project metadata, tool config
├── requirements.txt            # Pinned dependencies
└── Makefile                    # Common commands (optional)
```

---

## Backend Structure

```
backend/
├── api/                        # FastAPI HTTP layer
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ingestion.py        # POST /ingest, GET /ingest/{id}
│   │   ├── query.py            # POST /query, POST /query/stream
│   │   ├── evaluation.py       # POST /evaluate, GET /evaluate/{run_id}
│   │   ├── experiments.py      # Experiment/run CRUD
│   │   └── health.py           # GET /health, /ready, /metrics
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ingestion.py        # Ingestion request/response
│   │   ├── query.py            # Query request/response
│   │   ├── evaluation.py       # Evaluation request/response
│   │   ├── experiments.py      # Experiment request/response
│   │   └── common.py           # Shared schemas (ErrorResponse, etc.)
│   ├── dependencies.py         # FastAPI dependency providers
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── correlation_id.py   # Request correlation ID
│   │   ├── logging.py          # Request/response logging
│   │   ├── error_handling.py   # Global exception handlers
│   │   └── rate_limit.py       # Rate limiting
│   └── openapi.py              # OpenAPI customization
│
├── core/                       # Core contracts (zero dependencies)
│   ├── __init__.py
│   ├── protocols.py            # All component interfaces (Protocols)
│   ├── exceptions.py           # Exception hierarchy
│   ├── events.py               # Event definitions
│   ├── types.py                # Type variables, generics
│   └── utils.py                # Pure utilities (no I/O)
│
├── configs/                    # Configuration management
│   ├── __init__.py
│   ├── settings.py             # Main Settings class
│   ├── validation.py           # Custom validators
│   ├── feature_flags.py        # Feature flag definitions
│   └── logging_config.py       # Structlog configuration
│
├── data/                       # Data pipeline (separated by stage)
│   ├── __init__.py
│   ├── models/                 # Domain models (Pydantic)
│   │   ├── __init__.py
│   │   ├── document.py         # Document, DocumentMetadata, DocumentSource
│   │   ├── chunk.py            # Chunk, ChunkMetadata
│   │   ├── retrieval.py        # RetrievalResult, ExpandedQuery
│   │   ├── generation.py       # GenerationResult, Citation
│   │   ├── query.py            # QueryRequest, QueryResponse
│   │   ├── evaluation.py       # EvaluationSample, EvaluationResult
│   │   ├── experiment.py       # ExperimentConfig, ExperimentRun
│   │   ├── vector.py           # Vector, VectorRecord, IndexMetadata
│   │   └── enums.py            # All enumerations
│   │
│   ├── loaders/                # Document loading
│   │   ├── __init__.py
│   │   ├── base.py             # BaseLoader
│   │   ├── pdf.py              # PDFLoader
│   │   ├── docx.py             # DocxLoader
│   │   ├── pptx.py             # PptxLoader
│   │   ├── xlsx.py             # XlsxLoader
│   │   ├── html.py             # HtmlLoader
│   │   ├── markdown.py         # MarkdownLoader
│   │   ├── text.py             # TextLoader
│   │   ├── factory.py          # LoaderFactory
│   │   └── registry.py         # Loader registration
│   │
│   ├── preprocessing/          # Text cleaning & enrichment
│   │   ├── __init__.py
│   │   ├── pipeline.py         # PreprocessingPipeline
│   │   ├── normalize.py        # Unicode, whitespace normalization
│   │   ├── boilerplate.py      # Header/footer removal
│   │   ├── language.py         # Language detection
│   │   ├── structure.py                      # Structure extraction
│   │   ├── pii.py              # PII detection/redaction
│   │   └── factory.py          # Pipeline construction
│   │
│   ├── chunking/               # Document segmentation
│   │   ├── __init__.py
│   │   ├── base.py             # BaseChunker
│   │   ├── fixed.py            # FixedChunker
│   │   ├── recursive.py        # RecursiveChunker
│   │   ├── semantic.py         # SemanticChunker
│   │   ├── markdown.py         # MarkdownChunker
│   │   ├── sentence.py         # SentenceChunker
│   │   ├── hierarchical.py     # HierarchicalChunker
│   │   └── factory.py          # ChunkerFactory
│   │
│   ├── embeddings/             # Vector generation
│   │   ├── __init__.py
│   │   ├── base.py             # BaseEmbedder
│   │   ├── openai.py           # OpenAIEmbedder
│   │   ├── cohere.py           # CohereEmbedder
│   │   ├── voyage.py           # VoyageEmbedder
│   │   ├── sentence_transformers.py  # SentenceTransformerEmbedder
│   │   ├── huggingface.py      # HuggingFaceEmbedder
│   │   ├── factory.py          # EmbedderFactory
│   │   └── cache.py            # Embedding cache (Redis/memory)
│   │
│   ├── vectorstore/            # Vector persistence & search
│   │   ├── __init__.py
│   │   ├── base.py             # BaseVectorStore
│   │   ├── faiss.py            # FAISSVectorStore
│   │   ├── chroma.py           # ChromaVectorStore
│   │   ├── pinecone.py         # PineconeVectorStore
│   │   ├── weaviate.py         # WeaviateVectorStore
│   │   ├── qdrant.py           # QdrantVectorStore
│   │   ├── lancedb.py          # LanceDBVectorStore
│   │   ├── factory.py          # VectorStoreFactory
│   │   └── bm25.py             # BM25 index management
│   │
│   ├── retrieval/              # Search algorithms
│   │   ├── __init__.py
│   │   ├── dense.py            # DenseRetriever
│   │   ├── sparse.py           # SparseRetriever (BM25)
│   │   ├── hybrid.py           # HybridRetriever
│   │   ├── multi_vector.py     # MultiVectorRetriever (ColBERT)
│   │   ├── query_expansion/
│   │   │   ├── __init__.py
│   │   │   ├── rewrite.py      # LLMQueryRewriter
│   │   │   ├── decompose.py    # QueryDecomposer
│   │   │   └── hyde.py         # HyDEExpander
│   │   └── factory.py          # RetrieverFactory
│   │
│   ├── reranking/              # Result re-scoring
│   │   ├── __init__.py
│   │   ├── cohere.py           # CohereReranker
│   │   ├── jina.py             # JinaReranker
│   │   ├── cross_encoder.py    # CrossEncoderReranker
│   │   ├── bge_reranker.py     # BGEReranker
│   │   ├── llm_reranker.py     # LLMReranker
│   │   └── factory.py          # RerankerFactory
│   │
│   ├── generation/             # LLM answer generation
│   │   ├── __init__.py
│   │   ├── base.py             # BaseGenerator
│   │   ├── openai.py           # OpenAIGenerator
│   │   ├── anthropic.py        # AnthropicGenerator
│   │   ├── ollama.py           # OllamaGenerator
│   │   ├── vllm.py             # VLLMGenerator
│   │   ├── tgi.py              # TGIGenerator
│   │   ├── factory.py          # GeneratorFactory
│   │   ├── citation.py         # CitationExtractor
│   │   ├── verification.py     # GroundingVerifier
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── system.j2       # System prompt template
│   │       ├── few_shot.j2     # Few-shot examples
│   │       └── registry.py     # PromptRegistry
│   │
│   ├── evaluation/             # Quality measurement
│   │   ├── __init__.py
│   │   ├── datasets/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py       # EvaluationDatasetLoader
│   │   │   ├── ragas.py        # RAGAS dataset format
│   │   │   └── custom.py       # Custom dataset formats
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Metric protocol
│   │   │   ├── ragas_metrics.py # RAGAS metrics
│   │   │   ├── deepeval_metrics.py # DeepEval metrics
│   │   │   ├── custom.py       # Custom metrics
│   │   │   └── registry.py     # MetricRegistry
│   │   ├── computer.py         # MetricsComputer
│   │   ├── runner.py           # EvaluationRunner
│   │   ├── factory.py          # Metric/Dataset factory
│   │   └── reporting.py        # Report generation
│   │
│   ├── experiments/            # Experiment tracking
│   │   ├── __init__.py
│   │   ├── tracker.py          # ExperimentTracker protocol
│   │   ├── mlflow_tracker.py   # MLflowTracker
│   │   ├── wandb_tracker.py    # WandbTracker
│   │   ├── factory.py          # TrackerFactory
│   │   └── context.py          # TrackedPipeline context manager
│   │
│   ├── prompts/                # Prompt template management
│   │   ├── __init__.py
│   │   ├── templates/
│   │   │   ├── generation/
│   │   │   │   ├── system.j2
│   │   │   │   ├── few_shot.j2
│   │   │   │   └── citation.j2
│   │   │   ├── evaluation/
│   │   │   │   ├── faithfulness.j2
│   │   │   │   └── relevancy.j2
│   │   │   └── reranking/
│   │   │       └── pairwise.j2
│   │   ├── registry.py         # PromptRegistry
│   │   └── versioning.py       # Prompt version management
│   │
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── tokenize.py         # Token counting, truncation
│       ├── hash.py             # Content hashing
│       ├── text.py             # Text utilities
│       ├── async.py            # Async utilities
│       ├── metrics.py          # Prometheus helpers
│       ├── logging.py          # Structured logging helpers
│       └── validation.py       # Common validators
│
└── tests/                      # Test suite (mirrors backend)
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── unit/
    │   ├── __init__.py
    │   ├── test_core/
    │   │   ├── test_protocols.py
    │   │   ├── test_exceptions.py
    │   │   └── test_events.py
    │   ├── test_configs/
    │   │   ├── test_settings.py
    │   │   └── test_feature_flags.py
    │   ├── test_data/
    │   │   ├── test_models/
    │   │   ├── test_loaders/
    │   │   │   ├── test_pdf.py
    │   │   │   ├── test_docx.py
    │   │   │   └── ...
    │   │   ├── test_preprocessing/
    │   │   ├── test_chunking/
    │   │   ├── test_embeddings/
    │   │   ├── test_vectorstore/
    │   │   ├── test_retrieval/
    │   │   ├── test_reranking/
    │   │   ├── test_generation/
    │   │   ├── test_evaluation/
    │   │   ├── test_experiments/
    │   │   └── test_prompts/
    │   └── test_utils/
    ├── integration/
    │   ├── __init__.py
    │   ├── test_ingestion_pipeline.py
    │   ├── test_query_pipeline.py
    │   ├── test_evaluation_pipeline.py
    │   └── test_experiment_tracking.py
    ├── fixtures/
    │   ├── documents/
    │   │   ├── sample.pdf
    │   │   ├── sample.docx
    │   │   ├── sample.md
    │   │   └── sample.html
    │   ├── expected/
    │   │   ├── chunks.json
    │   │   ├── embeddings.npy
    │   │   └── retrieval_results.json
    │   └── datasets/
    │       ├── hotpotqa_sample.json
    │       ├── nq_sample.json
    │       └── custom_eval.json
    └── e2e/
        ├── __init__.py
        └── test_full_pipeline.py
```

---

## Frontend Structure

```
frontend/
├── streamlit/                  # Streamlit app (development/internal)
│   ├── app.py                  # Main entry point
│   ├── pages/
│   │   ├── 1_📥_Ingest.py
│   │   ├── 2_🔍_Query.py
│   │   ├── 3_📊_Evaluate.py
│   │   ├── 4_🧪_Experiments.py
│   │   └── 5_⚙️_Settings.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── citation_display.py
│   │   ├── metrics_chart.py
│   │   └── config_editor.py
│   └── utils/
│       ├── api_client.py
│       └── session_state.py
│
└── nextjs/                     # Next.js app (production - planned)
    ├── package.json
    ├── tsconfig.json
    ├── next.config.js
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   ├── query/
    │   │   ├── ingestion/
    │   │   ├── evaluation/
    │   │   └── experiments/
    │   ├── components/
    │   ├── lib/
    │   └── hooks/
    └── public/
```

---

## Documentation Structure

```
docs/
├── architecture/               # Architecture documentation (this folder)
│   ├── 01_system_overview.md
│   ├── 02_project_architecture.md
│   ├── 03_data_flow.md
│   ├── 04_pipeline_design.md
│   ├── 05_metadata_schema.md
│   ├── 06_component_responsibilities.md
│   ├── 07_folder_structure.md
│   ├── 08_retrieval_lifecycle.md
│   ├── 09_generation_lifecycle.md
│   ├── 10_evaluation_lifecycle.md
│   ├── 11_experiment_tracking.md
│   └── 12_future_extensions.md
├── adr/                        # Architecture Decision Records
│   ├── template.md
│   └── (YYYY-MM-DD-short-description.md)
├── api/                        # API documentation
│   ├── openapi.yaml
│   └── endpoints.md
├── user-guide/                 # User documentation
│   ├── getting-started.md
│   ├── ingestion-guide.md
│   ├── query-guide.md
│   ├── evaluation-guide.md
│   └── experiment-guide.md
├── developer-guide/            # Developer documentation
│   ├── contributing.md
│   ├── coding-standards.md
│   ├── testing-guide.md
│   ├── deployment.md
│   └── adding-components.md
└── operations/                 # Operations documentation
    ├── monitoring.md
    ├── troubleshooting.md
    ├── backup-recovery.md
    └── scaling.md
```

---

## Scripts Structure

```
scripts/
├── setup/
│   ├── install_dev.sh          # Development environment setup
│   ├── install_prod.sh         # Production dependencies
│   └── precommit_install.sh    # Pre-commit hooks
├── data/
│   ├── ingest.py               # CLI ingestion
│   ├── reindex.py              # Rebuild vector index
│   ├── export.py               # Export data
│   └── cleanup.py              # Clean old data
├── evaluation/
│   ├── run_eval.py             # Run evaluation
│   ├── compare_runs.py         # Compare experiment runs
│   └── generate_report.py      # Generate evaluation report
├── experiments/
│   ├── list_runs.py            # List experiment runs
│   ├── delete_run.py           # Delete run
│   └── export_run.py           # Export run artifacts
├── maintenance/
│   ├── vacuum_db.py            # Database maintenance
│   ├── compact_index.py        # Vector index compaction
│   └── rotate_logs.py          # Log rotation
├── deployment/
│   ├── build_docker.sh         # Build Docker image
│   ├── deploy_k8s.sh           # Deploy to Kubernetes
│   └── rollback.sh             # Rollback deployment
└── utils/
    ├── generate_uuid.py        # Generate UUIDv7
    ├── hash_content.py         # Hash file content
    └── check_config.py         # Validate configuration
```

---

## Assets Structure

```
assets/
├── images/
│   ├── logo.png
│   ├── logo.svg
│   ├── architecture-overview.png
│   ├── pipeline-diagram.png
│   └── screenshots/
├── icons/
│   ├── favicon.ico
│   └── favicon.svg
└── styles/
    ├── theme.css
    └── variables.css
```

---

## Notebooks Structure

```
notebooks/
├── exploration/
│   ├── 01_data_exploration.ipynb
│   ├── 02_embedding_analysis.ipynb
│   ├── 03_retrieval_analysis.ipynb
│   └── 04_generation_analysis.ipynb
├── prototyping/
│   ├── chunking_strategies.ipynb
│   ├── hybrid_search_tuning.ipynb
│   ├── reranker_comparison.ipynb
│   └── prompt_engineering.ipynb
├── evaluation/
│   ├── metric_correlation.ipynb
│   └── dataset_analysis.ipynb
└── reporting/
    ├── monthly_report.ipynb
    └── experiment_dashboard.ipynb
```

---

## GitHub Structure

```
.github/
├── workflows/
│   ├── ci.yml                  # Main CI pipeline
│   ├── cd-staging.yml          # Staging deployment
│   ├── cd-production.yml       # Production deployment
│   ├── dependency-check.yml    # Dependency scanning
│   ├── security-scan.yml       # Security scanning
│   └── release.yml             # Release automation
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── feature_request.md
│   └── documentation.md
├── PULL_REQUEST_TEMPLATE.md
├── dependabot.yml              # Dependabot configuration
├── CODEOWNERS                  # Code ownership
└── release-drafter.yml         # Release notes automation
```

---

## File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Python modules | `snake_case.py` | `vector_store.py` |
| Python packages | `snake_case` | `vectorstore/` |
| Classes | `PascalCase` | `DocumentRetriever` |
| Functions | `snake_case` | `retrieve_documents` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_TOP_K` |
| Type variables | `PascalCase` with `T` prefix | `TDocument` |
| Private | `_leading_underscore` | `_internal_cache` |
| Test files | `test_<module>.py` | `test_retrieval_service.py` |
| Test functions | `test_<functionality>_<scenario>` | `test_retrieve_returns_top_k` |
| Config files | `<name>.yaml` / `.toml` | `settings.yaml` |
| Documentation | `kebab-case.md` | `retrieval-lifecycle.md` |
| Scripts | `snake_case.py` / `.sh` | `run_evaluation.py` |
| Notebooks | `kebab-case.ipynb` | `chunking-strategies.ipynb` |

---

## Import Conventions

### Internal Imports
```python
# Absolute imports from backend root
from backend.core.protocols import DocumentLoader, EmbeddingProvider
from backend.data.models import Document, Chunk, RetrievalResult
from backend.configs.settings import get_settings

# Relative imports within same package
from .base import BaseChunker
from .factory import ChunkerFactory
```

### External Imports
```python
# Standard library first
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Protocol

# Third-party
import pydantic
from pydantic import BaseModel, Field
import structlog

# Local application (only in api/ and tests/)
from backend.api.dependencies import get_vector_store
```

---

## Module Export Patterns

### Package `__init__.py`
```python
# backend/data/chunking/__init__.py
"""Chunking strategies for document segmentation."""

from .base import BaseChunker, ChunkingConfig
from .fixed import FixedChunker
from .recursive import RecursiveChunker
from .semantic import SemanticChunker
from .markdown import MarkdownChunker
from .sentence import SentenceChunker
from .factory import ChunkerFactory, ChunkingStrategy

__all__ = [
    "BaseChunker",
    "ChunkingConfig",
    "FixedChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "MarkdownChunker",
    "SentenceChunker",
    "ChunkerFactory",
    "ChunkingStrategy",
]
```

### Facade Pattern for Complex Modules
```python
# backend/data/retrieval/__init__.py
"""Retrieval algorithms and query expansion."""

from .dense import DenseRetriever
from .sparse import SparseRetriever
from .hybrid import HybridRetriever
from .multi_vector import MultiVectorRetriever
from .factory import RetrieverFactory
from .query_expansion import QueryExpander, QueryExpansionConfig

__all__ = [
    "DenseRetriever",
    "SparseRetriever",
    "HybridRetriever",
    "MultiVectorRetriever",
    "RetrieverFactory",
    "QueryExpander",
    "QueryExpansionConfig",
]
```

---

## Directory Purpose Summary

| Directory | Purpose | Stability |
|-----------|---------|-----------|
| `backend/api/` | HTTP interface | Stable |
| `backend/core/` | Contracts | Very Stable |
| `backend/configs/` | Configuration | Stable |
| `backend/data/models/` | Domain models | Very Stable |
| `backend/data/loaders/` | Document ingestion | Evolving |
| `backend/data/preprocessing/` | Text cleaning | Evolving |
| `backend/data/chunking/` | Segmentation | Evolving |
| `backend/data/embeddings/` | Vector generation | Evolving |
| `backend/data/vectorstore/` | Vector persistence | Evolving |
| `backend/data/retrieval/` | Search algorithms | Evolving |
| `backend/data/reranking/` | Re-scoring | Evolving |
| `backend/data/generation/` | Answer generation | Evolving |
| `backend/data/evaluation/` | Quality metrics | Evolving |
| `backend/data/experiments/` | Experiment tracking | Evolving |
| `backend/data/prompts/` | Prompt management | Evolving |
| `backend/data/utils/` | Shared utilities | Stable |
| `backend/tests/` | Test suite | Evolving |
| `frontend/streamlit/` | Dev UI | Evolving |
| `frontend/nextjs/` | Prod UI (planned) | Planned |
| `docs/architecture/` | Architecture docs | Stable |
| `docs/adr/` | Decision records | Append-only |
| `scripts/` | Operations | Evolving |
| `notebooks/` | Exploration | Ephemeral |
| `.github/workflows/` | CI/CD | Evolving |

---

## Adding New Directories

When adding a new pipeline stage:

1. Create `backend/data/<new_stage>/`
2. Add `__init__.py` with exports
3. Implement protocol in `backend/core/protocols.py`
4. Add factory module
5. Add config section in `backend/configs/settings.py`
6. Create test directory `backend/tests/unit/test_data/test_<new_stage>/`
7. Document in this file and `06_component_responsibilities.md`
8. Update `pyproject.toml` if new dependencies needed