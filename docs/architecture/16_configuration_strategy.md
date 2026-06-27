# Configuration Strategy

## Overview

Configuration drives all behavior in the Retrieval Intelligence Platform. This document describes the settings hierarchy, environment management, and validation strategy.

## Environment Variables

All configuration is managed via environment variables validated at startup.

### Required Secrets
| Variable | Description | Validation |
|----------|-------------|------------|
| `OPENAI_API_KEY` | OpenAI API key | Required if `OPENAI` provider used |
| `COHERE_API_KEY` | Cohere API key | Required if `COHERE` provider used |
| `VOYAGE_API_KEY` | Voyage AI API key | Required if `VOYAGE` provider used |
| `PINECONE_API_KEY` | Pinecone API key | Required if `PINECONE` vector store used |

### Optional Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `DATABASE_URL` | `sqlite:///data.db` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |

## Settings Hierarchy

```
Environment Variables (.env)
        │
        ▼
┌─────────────────┐
│  Pydantic       │
│  Settings       │
│  (base)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Nested Config  │
│  Classes        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Feature Flags  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Runtime        │
│  Overrides      │
└─────────────────┘
```

## Settings Schema

```python
class Settings(BaseSettings):
    # Application settings
    app: AppSettings = AppSettings()
    
    # Pipeline configurations
    data: DataSettings = DataSettings()
    embeddings: EmbeddingSettings = EmbeddingSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    rerank: RerankSettings = RerankSettings()
    generation: GenerationSettings = GenerationSettings()
    evaluation: EvaluationSettings = EvaluationSettings()
    experiments: ExperimentSettings = ExperimentSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    security: SecuritySettings = SecuritySettings()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )
```

## Configuration by Profile

### Development Profile

**.env.development**
```bash
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///dev.db

# Local embedding model
EMBEDDINGS__PROVIDER=sentence_transformers
EMBEDDINGS__MODEL=BAAI/bge-small-en-v1.5
EMBEDDINGS__DEVICE=cpu

# FAISS for local testing
VECTOR_STORE__PROVIDER=faiss
VECTOR_STORE__DIMENSION=1536
```

### Testing Profile

**.env.test**
```bash
API_HOST=127.0.0.1
API_PORT=8001
LOG_LEVEL=WARNING

# Mock providers
EMBEDDINGS__PROVIDER=mock
GENERATION__PROVIDER=mock
```

### Production Profile

**.env.production**
```bash
API_HOST=0.0.0.0
LOG_LEVEL=INFO

# Managed services
EMBEDDINGS__PROVIDER=openai
EMBEDDINGS__MODEL=text-embedding-3-large

VECTOR_STORE__PROVIDER=pinecone
VECTOR_STORE__PINECONE__INDEX_NAME=production-index

DATABASE_URL=postgresql://user:pass@db:5432/rip

# Security
SECURITY__CORS_ORIGINS="https://app.example.com"
SECURITY__RATE_LIMIT="100/minute"
```

## Secrets Management

### Local Development
- `.env` file (never committed)
- `.env.example` for documentation
- python-dotenv loads at startup

### Staging/Production
- HashiCorp Vault integration
- AWS Secrets Manager
- Kubernetes secrets
- Environment variable injection

### Secret Rotation
- Key versioning in settings
- Graceful rotation window
- Alert on expired keys

## Configuration Validation

### Startup Validation
```python
def validate_settings(settings: Settings) -> None:
    # Validate provider compatibility
    if settings.embeddings.provider == "openai":
        if not settings.embeddings.api_key:
            raise ConfigurationError("OPENAI_API_KEY required")
    
    # Validate vector dimensions match
    if settings.embeddings.dimension != settings.vector_store.dimension:
        raise ConfigurationError("Dimension mismatch")
    
    # Validate file paths exist
    Path(settings.data.raw_path).mkdir(exist_ok=True)
```

### Runtime Validation
- Feature flags validated before use
- Circuit breaker configs checked
- Rate limit configs enforced

### Cross-Field Validation
```python
@model_validator
def validate_hybrid_search(self) -> Self:
    if self.hybrid_fusion != "none":
        if not self.dense_enabled and not self.sparse_enabled:
            raise ValueError("Hybrid requires dense or sparse")
    return self
```

## Feature Flags

```python
class FeatureFlag(str, Enum):
    HYBRID_SEARCH = "hybrid_search"
    RERANKING = "reranking"
    QUERY_EXPANSION = "query_expansion"
    CITATION_GENERATION = "citation_generation"
    EXPLAINABLE_RETRIEVAL = "explainable_retrieval"
    GROUNDING_CHECK = "grounding_check"
    STREAMING_GENERATION = "streaming_generation"
    BATCH_INGESTION = "batch_ingestion"
    EMBEDDING_CACHE = "embedding_cache"
    PII_REDACTION = "pii_redaction"

def is_enabled(flag: FeatureFlag) -> bool:
    return flag in settings.feature_flags.enabled
```

## Configuration Files

### Settings Source Priority
1. Environment variables (highest)
2. `.env` file
3. YAML config file (`config.yaml`)
4. Defaults (lowest)

### YAML Configuration
```yaml
# config.yaml
embeddings:
  provider: openai
  model: text-embedding-3-small
  batch_size: 32

chunking:
  strategy: recursive
  chunk_size: 512
  overlap: 50
```

## Dynamic Configuration

### Runtime Overrides
```python
# Query params can override config
class QueryParams(BaseModel):
    top_k: Optional[int] = None
    rerank_top_n: Optional[int] = None
    similarity_threshold: Optional[float] = None
    enable_expansion: Optional[bool] = None
    enable_rerank: Optional[bool] = None
```

### Hot Reload
- Watch settings file for changes
- Validate on change
- Graceful restart of affected components

## Validation Rules

| Field | Constraint | Error |
|-------|------------|-------|
| `chunk_size` | 50 <= x <= 2048 | ChunkingError |
| `temperature` | 0.0 <= x <= 2.0 | GenerationError |
| `top_k` | 1 <= x <= 1000 | RetrievalError |
| `batch_size` | 1 <= x <= provider max | EmbeddingError |
| `api_timeout` | 1 <= x <= 300 | ProviderError |

## Configuration Documentation

All settings must have docstrings in `.env.example`:
```bash
# Embedding configuration
# Provider: openai, cohere, voyage, sentence_transformers
EMBEDDINGS__PROVIDER=sentence_transformers

# Model name (provider-specific)
EMBEDDINGS__MODEL=BAAI/bge-small-en-v1.5

# Batch size for API calls (default: 32)
EMBEDDINGS__BATCH_SIZE=32
```

## Future Scalability

### Configuration Service
- Centralized config service
- Real-time updates
- A/B test config variants

### Schema Evolution
- Settings versioning
- Migration scripts
- Backward compatibility