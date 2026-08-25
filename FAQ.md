# Frequently Asked Questions

## General

### What is the Retrieval Intelligence Platform?

The Retrieval Intelligence Platform (RIP) is an open-source, production-grade
Retrieval-Augmented Generation (RAG) system. It provides a complete pipeline
for document ingestion, chunking, embedding, retrieval, and grounded generation
with citations, plus enterprise features like authentication, RBAC, workspaces,
and persistent chat.

### What does "RAG" mean?

Retrieval-Augmented Generation (RAG) is a technique that combines information
retrieval with large language models. Instead of relying solely on the model's
internal knowledge, RAG first retrieves relevant documents from a knowledge
base and then generates answers grounded in those documents. This reduces
hallucination and enables the system to answer questions about proprietary or
recent information.

### What's the license?

MIT License — free to use, modify, and distribute for any purpose.

## Installation & Setup

### What are the system requirements?

- Python 3.11+
- Node.js 18+ (for the frontend)
- 4 GB RAM minimum (8 GB+ recommended for local embedding models)

### Do I need a GPU?

No. The platform runs entirely on CPU. GPU acceleration is beneficial for
large-scale embedding generation but is not required.

### Do I need an API key?

For the full RAG pipeline with grounded generation, you need at least one LLM
provider key (OpenAI, Anthropic, etc.). For just the retrieval pipeline
(without generation), no external API keys are required.

## Architecture

### How does the RAG pipeline work?

```
Document -> Loader -> Cleaner -> Chunker -> Embedder -> Vector Store
                                                              |
Query   -> Expander -> Retriever (Dense + Sparse) -> Reranker -> Generator -> Answer
```

Documents are ingested, chunked, and embedded into a vector store. Queries go
through expansion, hybrid retrieval (dense + BM25), fusion, reranking, and
dynamic top-k selection before being passed to an LLM for grounded generation.

### Can I use just the retrieval part without generation?

Yes. The retrieval pipeline (`RetrievalEngine`, `RetrievalPipeline`) operates
independently of the generation pipeline. Use it for search or as a building
block for your own application.

### What databases does the platform use?

Default local development uses SQLite (via aiosqlite). Production deployments
should use PostgreSQL. Redis is used for caching and rate limiting.

## Usage

### How do I add my own documents?

Use the document upload API at `POST /api/v1/documents` or use the
`LoaderFactory` directly in Python:

```python
from backend.data.loaders.loader_factory import LoaderFactory
doc = LoaderFactory.load_document("/path/to/document.pdf")
```

Supported formats: TXT, Markdown, PDF, DOCX.

### Can I use a different embedding model?

Yes. Set the `EMBEDDING_MODEL` environment variable to any
Sentence-Transformers model name from Hugging Face.

### Can I use OpenAI embeddings instead of local models?

Not yet. The `EmbeddingProviderType` enum includes OpenAI, Cohere, and other
cloud providers, but only the Sentence-Transformers provider is currently
implemented. Contributions are welcome.

## Deployment

### How do I deploy to production?

See [DEPLOYMENT.md](DEPLOYMENT.md) for guides on Railway, Render, AWS (ECS
Fargate), and Azure (Container Apps). The platform ships with a production-ready
multi-stage Dockerfile.

### Can I scale horizontally?

Yes. The API is stateless (sessions are in Redis, metadata in Postgres). Scale
by adding API replicas behind a load balancer. Vector store indexes are
in-memory per-replica; for large-scale deployments, use a shared vector store.

### What environment variables are required?

At minimum:
- `ENTERPRISE_JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
- `DATABASE_URL` — SQLAlchemy connection string
- One LLM provider key (e.g., `OPENAI_API_KEY`)

See `.env.example` for the full list.

## Contributing

### How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions are welcome —
features, bug fixes, tests, documentation, and provider implementations.

### How do I add a new LLM provider?

1. Create a new file in `backend/generation/providers/`
2. Implement the `LLMProvider` abstract base class
3. Register your provider in `ProviderFactory`
4. Add tests in `backend/tests/`

### How do I add a new embedding provider?

1. Create a new file in `backend/data/embeddings/`
2. Implement the `BaseEmbeddingProvider` abstract base class
3. Register your provider in `EmbeddingFactory`
4. Add tests in `backend/tests/`
