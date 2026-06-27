# Future Extensions

## Overview

This document outlines how the architecture will support future extensions without breaking changes or major refactoring.

## OCR Integration

### Architecture
```
Document (Scanned PDF/Image)
        │
        ▼
┌─────────────────┐
│  OCR Provider   │
│  (Tesseract,    │
│   Google Vision,│
│   Azure Form)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Loader    │ (existing pipeline continues)
│  (existing)     │
└─────────────────┘
```

### Extension Point
- New `OCRDocumentLoader` implements `DocumentLoader`
- Config flag `ocr.enabled`
- Pre-chunking OCR step

## Hybrid Search Enhancements

### BM25 Integration
- Already supported in `backend/data/retrieval/sparse.py`
- Configure via `retrieval.sparse_enabled`
- Fusion in `backend/data/retrieval/hybrid.py`

### SPLADE Sparse Embeddings
```python
class SPLADEProvider(EmbeddingProvider):
    # Late interaction sparse vectors
    # No separate BM25 index needed
```

## Cross-Encoder Re-ranking

### Current State
- Supported via `CohereReranker`, `CrossEncoderReranker`
- `rerank.reranker_provider` config

### Future Enhancements
- Cascade reranking (fast → slow)
- LLM-based listwise reranking
- Diversity-aware reranking (MMR)

## Multi-Vector Retrieval

### ColBERT Architecture
```
Query Token Vectors → Multiple Vector Searches
         │
         ▼
┌─────────────────┐
│  Late Interaction│
│  Scoring         │
└─────────────────┘
```

### Extension Points
- New `MultiVectorRetriever` protocol
- `ColBERTRetriever` implementation
- Token-level vector storage

## Vector Store Extensions

### ChromaDB
- Already supported via `ChromaVectorStore`
- Native sparse + dense support
- Good for embedded deployments

### Pinecone
- Already supported via `PineconeVectorStore`
- Managed, scales to 100M+ vectors
- Namespaces for multi-tenancy

### Weaviate
- Already supported via `WeaviateVectorStore`
- GraphQL API
- Multi-tenancy built-in

### Milvus
```python
class MilvusVectorStore(VectorStore):
    # Async Python SDK
    # Partitioned collections
    # Built-in sparse vectors
```

## Multi-LLM Support

### Current Architecture
- Multiple providers via `GeneratorFactory`
- Feature flag for swapping models
- A/B testing supported

### Future Enhancements
- Ensemble generation (multiple models)
- Fallback chains
- Model selection by query type

### Routing Strategy
```python
class LLMRouter:
    def select_provider(self, query: str, context: list[Chunk]) -> LLMProvider:
        if self._is_factoid(query):
            return LLMProvider.OPENAI
        elif self._is_creative(context):
            return LLMProvider.ANTHROPIC
        else:
            return LLMProvider.GPT4O_MINI
```

## Authentication & Authorization

### Architecture Addition
```
Internet
    │
    ▼
┌─────────────────┐
│  Auth Layer     │
│  (OAuth2, JWT)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Layer      │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Authorization  │
│  (RBAC)         │
└────────┬────────┘
         │
         ▼
   Existing Pipeline
```

### Implementation Plan
- OAuth2/JWT middleware in `backend/api/middleware/auth.py`
- RBAC decorator for routes
- User context in correlation ID

## User Accounts & Multi-Tenancy

### Data Model Extension
```python
class User(BaseModel):
    id: UUID
    email: str
    preferences: UserPreferences
    created_at: datetime

class Tenant(BaseModel):
    id: UUID
    name: str
    settings: TenantSettings
```

### Isolation Strategies
- Namespace/collection per tenant (vector store)
- Row-level security (PostgreSQL)
- API key-based tenant resolution

## Cloud Storage Integration

### Object Storage Layer
```python
class CloudStorage(Protocol):
    async def upload(self, path: str, content: bytes) -> URL: ...
    async def download(self, url: str) -> bytes: ...
    async def list(self, prefix: str) -> list[str]: ...
    async def delete(self, url: str) -> None: ...
```

### Providers
- AWS S3 via `aioboto3`
- Google Cloud Storage
- Azure Blob Storage
- MinIO (self-hosted)

### Use Cases
- Large document storage
- Artifact storage
- Backup/recovery

## REST API Extensions

### Current State
- FastAPI with automatic OpenAPI docs
- Async throughout

### Planned Enhancements
- GraphQL API (Strawberry)
- gRPC endpoints (for streaming)
- WebSocket for real-time updates

### API Versioning
```
/v1/query
/v2/query (with new features)
```

## Docker Support

### Architecture
```
┌─────────────────┐
│  load balancer  │
└────────┬────────┘
         │
┌────────┴────────┐
│  API Container  │
│  (FastAPI)      │
└────────┬────────┘
         │
┌────────┴────────┐
│  Worker Pool    │
│  (Celery)       │
└────────┬────────┘
         │
┌────────┴────────┐
│  Redis Queue    │
└─────────────────┘
```

### Docker Compose
- `docker-compose.dev.yml` for local development
- `docker-compose.prod.yml` for production
- Environment-specific configs

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# On PR:
# - Lint (ruff, black, mypy)
# - Unit tests (pytest)
# - Security scan (pip-audit, bandit)

# On merge to main:
# - Integration tests
# - Build and push Docker image
# - Deploy to staging

# On tag:
# - Deploy to production
# - Run post-deploy smoke tests
```

### Build Pipeline
- Multi-arch builds (amd64, arm64)
- SBOM generation
- Vulnerability scanning
- Image signing

## Kubernetes Deployment

### Helm Chart Structure
```
charts/retrieval-intelligence-platform/
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── secret.yaml
│   └── configmap.yaml
├── values.yaml
└── Chart.yaml
```

### Scaling Configuration
- HPA based on CPU and queue depth
- Pod disruption budgets
- Read replica deployments
- Worker autoscaling

## Implementation Priority

| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| OCR | Medium | Medium | Additional OCR libraries |
| Hybrid Search | High | Low | Already supported |
| Cross-Encoder | High | Low | Already supported |
| Multi-Vector | Low | High | New protocols |
| ChromaDB | Medium | Low | Already supported |
| Pinecone | Medium | Low | Already supported |
| Weaviate | Medium | Medium | Already supported |
| Multi-LLM | High | Medium | Router logic |
| Authentication | High | Medium | Auth provider |
| Multi-tenancy | High | High | DB schema changes |
| Cloud Storage | Medium | Medium | Storage SDKs |
| REST API v2 | Medium | Low | Versioning |
| Docker | High | Low | Build config |
| CI/CD | High | Medium | GitHub Actions |
| Kubernetes | Low | High | Helm charts |