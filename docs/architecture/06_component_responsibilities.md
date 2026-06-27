# Component Responsibilities

## Overview

This document defines the responsibilities, interfaces, and boundaries of every backend module in the Retrieval Intelligence Platform. Each module follows the single responsibility principle and communicates through well-defined protocols.

---

## Module Map

```
backend/
├── api/              # HTTP layer
├── core/             # Contracts, exceptions, events
├── configs/          # Configuration management
├── data/
│   ├── loaders/          # Document ingestion
│   ├── preprocessing/    # Text cleaning
│   ├── chunking/         # Document segmentation
│   ├── embeddings/       # Vector generation
│   ├── vectorstore/      # Vector persistence
│   ├── retrieval/        # Search algorithms
│   ├── reranking/        # Result re-scoring
│   ├── generation/       # LLM answer generation
│   ├── evaluation/       # Quality measurement
│   ├── experiments/      # Experiment tracking
│   ├── prompts/          # Prompt management
│   ├── models/           # Domain models
│   └── utils/            # Shared utilities
└── tests/            # Test suite
```

---

## backend/api/

### Responsibility
HTTP interface layer. Handles request/response serialization, validation, authentication, rate limiting, and routing to pipeline services.

### Components

| Component | Responsibility |
|-----------|----------------|
| `routes/ingestion.py` | POST /ingest, GET /ingest/{id}, DELETE /ingest/{id} |
| `routes/query.py` | POST /query, POST /query/stream |
| `routes/evaluation.py` | POST /evaluate, GET /evaluate/{run_id} |
| `routes/experiments.py` | CRUD for experiments/runs |
| `routes/health.py` | GET /health, GET /ready, GET /metrics |
| `schemas/` | Request/response Pydantic models (API contracts) |
| `dependencies.py` | FastAPI dependency injection providers |
| `middleware/` | Correlation ID, logging, error handling, CORS |

### Interfaces
```python
# No direct external interfaces - consumes pipeline services via DI
```

### Dependencies
- `backend.core.protocols` (for type hints)
- `backend.configs.settings` (for config)
- Pipeline services (injected)

### Configuration
- `api.host`, `api.port`, `api.workers`
- `security.cors_origins`, `security.rate_limit`
- `observability.log_level`

---

## backend/core/

### Responsibility
Core contracts and shared primitives. Zero external dependencies. Defines the "language" of the system.

### Components

| Component | Responsibility |
|-----------|----------------|
| `protocols.py` | All component interfaces (Protocols/ABCs) |
| `exceptions.py` | Exception hierarchy (`RipError` base) |
| `events.py` | Event definitions for observability |
| `types.py` | Type variables, generics, shared types |
| `utils.py` | Pure utility functions (no I/O) |

### Key Protocols
```python
# backend/core/protocols.py
class DocumentLoader(Protocol):
    async def load(self, source: DocumentSource) -> list[Document]: ...

class TextPreprocessor(Protocol):
    def process(self, document: Document) -> Document: ...

class Chunker(Protocol):
    def chunk(self, document: Document) -> list[Chunk]: ...

class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[Vector]: ...
    async def embed_query(self, text: str) -> Vector: ...

class VectorStore(Protocol):
    async def upsert(self, chunks: list[Chunk]) -> UpsertResult: ...
    async def search(self, query: Vector, top_k: int, filter: Optional[MetadataFilter]) -> list[Chunk]: ...
    async def delete(self, ids: list[UUID]) -> DeleteResult: ...

class Retriever(Protocol):
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]: ...

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
    def log_artifact(self, path: str, name: Optional[str] = None) -> None: ...
```

### Exception Hierarchy
```python
RipError
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

### Events
```python
# backend/core/events.py
@dataclass
class IngestionStarted:
    document_id: UUID
    source_type: DocumentSourceType
    timestamp: datetime

@dataclass
class IngestionCompleted:
    document_id: UUID
    chunks_created: int
    vectors_upserted: int
    duration_ms: int
    timestamp: datetime

@dataclass
class QueryCompleted:
    correlation_id: str
    query: str
    retrieval_latency_ms: int
    generation_latency_ms: int
    total_latency_ms: int
    chunks_retrieved: int
    citations_generated: int
    timestamp: datetime
```

---

## backend/configs/

### Responsibility
Configuration management. Loads, validates, and provides access to all settings via Pydantic Settings.

### Components

| Component | Responsibility |
|-----------|----------------|
| `settings.py` | Main `Settings` class with nested config models |
| `validation.py` | Cross-field validators, custom validation logic |
| `feature_flags.py` | Feature flag definitions, runtime checks |
| `logging_config.py` | Structlog configuration, JSON formatting |

### Settings Structure
```python
class Settings(BaseSettings):
    app: AppSettings = AppSettings()
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
```

### Feature Flags
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
```

### Dependencies
- `pydantic-settings`, `python-dotenv`, `pyyaml`
- No backend dependencies (leaf module)

---

## backend/data/models/

### Responsibility
Canonical domain models (Pydantic). Single source of truth for data contracts between all pipeline stages.

### Components

| Component | Responsibility |
|-----------|----------------|
| `document.py` | `Document`, `DocumentMetadata`, `DocumentSource`, `DocumentStructure` |
| `chunk.py` | `Chunk`, `ChunkMetadata` |
| `retrieval.py` | `RetrievalResult`, `RetrievalMethod`, `ExpandedQuery`, `RetrievalExplanation` |
| `generation.py` | `GenerationResult`, `Citation`, `GenerationMetadata`, `HallucinationFlag` |
| `query.py` | `QueryRequest`, `QueryParams`, `QueryResponse`, `QueryMetadata` |
| `evaluation.py` | `EvaluationSample`, `EvaluationDataset`, `EvaluationResult`, `MetricResult` |
| `experiment.py` | `ExperimentConfig`, `ExperimentRun`, `Artifact`, `RunStatus` |
| `enums.py` | All enumerations (`DocumentSourceType`, `ChunkingStrategy`, etc.) |
| `vector.py` | `Vector`, `VectorRecord`, `IndexMetadata`, `DistanceMetric` |

### Design Rules
- No methods (pure data)
- All fields typed with validation constraints
- `custom: dict[str, Any]` for extensibility
- `schema_version` on all root entities
- UUIDv7 for all IDs (time-ordered)

---

## backend/data/loaders/

### Responsibility
Extract text and metadata from source formats into `Document` objects.

### Components

| Component | Responsibility |
|-----------|----------------|
| `base.py` | `BaseLoader` with common logic (checksum, metadata) |
| `pdf.py` | PDF loading via `pypdf` + `unstructured` |
| `docx.py` | Word documents via `python-docx` |
| `pptx.py` | PowerPoint via `python-pptx` |
| `xlsx.py` | Excel via `openpyxl` |
| `html.py` | HTML via `unstructured` / `beautifulsoup4` |
| `markdown.py` | Markdown via `markdown-it-py` |
| `text.py` | Plain text files |
| `factory.py` | `LoaderFactory.create(source_type, config)` |
| `registry.py` | Loader registration, auto-discovery |

### Interface
```python
class DocumentLoader(Protocol):
    async def load(self, source: DocumentSource) -> list[Document]: ...
    
    # Optional: streaming for large files
    async def load_stream(self, source: DocumentSource) -> AsyncIterator[Document]: ...
```

### Supported Formats
| Format | Loader | Dependencies |
|--------|--------|--------------|
| PDF | `PDFLoader` | `pypdf`, `unstructured` |
| DOCX | `DocxLoader` | `python-docx` |
| PPTX | `PptxLoader` | `python-pptx` |
| XLSX | `XlsxLoader` | `openpyxl` |
| HTML | `HtmlLoader` | `unstructured`, `beautifulsoup4` |
| Markdown | `MarkdownLoader` | `markdown-it-py` |
| Text | `TextLoader` | stdlib |

### Configuration
```python
class LoaderConfig(BaseModel):
    pdf: PDFLoaderConfig = PDFLoaderConfig()
    docx: DocxLoaderConfig = DocxLoaderConfig()
    # ... per-format config
    max_file_size_mb: int = 100
    encoding_fallback: str = "utf-8"
    extract_images: bool = False
    extract_tables: bool = True
```

---

## backend/data/preprocessing/

### Responsibility
Clean, normalize, and enrich document text and metadata.

### Components

| Component | Responsibility |
|-----------|----------------|
| `pipeline.py` | `PreprocessingPipeline` composes steps |
| `normalize.py` | Unicode, whitespace, control char normalization |
| `boilerplate.py` | Header/footer/page number removal |
| `language.py` | Language detection (`langdetect`, `fasttext`) |
| `structure.py` | Markdown/HTML structure extraction |
| `pii.py` | PII detection/redaction (optional, `spacy`, `presidio`) |
| `factory.py` | Pipeline construction from config |

### Interface
```python
class TextPreprocessor(Protocol):
    def process(self, document: Document) -> Document: ...

class PreprocessingPipeline:
    def __init__(self, steps: list[TextPreprocessor]):
        self.steps = steps
    
    def process(self, document: Document) -> Document:
        for step in self.steps:
            document = step.process(document)
        return document
```

### Default Pipeline Steps
1. `UnicodeNormalizer` - NFC, replace control chars
2. `WhitespaceNormalizer` - Collapse spaces, normalize newlines
3. `BoilerplateRemover` - Configurable regex patterns
4. `LanguageDetector` - Detect, store in metadata
4. `StructureExtractor` - Headings, tables, code blocks
5. `StatisticsCalculator` - Char/word/token counts

### Configuration
```python
class PreprocessingConfig(BaseModel):
    unicode_normalization: bool = True
    whitespace_normalization: bool = True
    boilerplate_patterns: list[str] = Field(default_factory=list)
    language_detection: bool = True
    language_min_confidence: float = 0.8
    structure_extraction: bool = True
    pii_redaction: bool = False
    pii_entities: list[str] = ["PERSON", "EMAIL", "PHONE", "ADDRESS"]
```

---

## backend/data/chunking/

### Responsibility
Split documents into chunks for embedding and retrieval.

### Components

| Component | Responsibility |
|-----------|----------------|
| `base.py` | `BaseChunker` with overlap handling, token counting |
| `fixed.py` | `FixedChunker` - fixed size with overlap |
| `recursive.py` | `RecursiveChunker` - hierarchical separators |
| `semantic.py` | `SemanticChunker` - embedding-based boundaries |
| `markdown.py` | `MarkdownChunker` - heading-aware |
| `sentence.py` | `SentenceChunker` - NLTK/spaCy sentence boundaries |
| `hierarchical.py` | `HierarchicalChunker` - parent-child chunks |
| `factory.py` | `ChunkerFactory.create(strategy, config)` |

### Interface
```python
class Chunker(Protocol):
    def chunk(self, document: Document) -> list[Chunk]: ...
    
    # Optional: chunk single text (for testing)
    def chunk_text(self, text: str, metadata: ChunkMetadata) -> list[Chunk]: ...
```

### Strategies

| Strategy | Best For | Complexity |
|----------|----------|------------|
| `fixed` | Uniform content, predictable size | O(n) |
| `recursive` | General purpose, mixed content | O(n) |
| `semantic` | High-quality retrieval, semantic coherence | O(n²) or O(n log n) |
| `markdown` | Technical docs, structured content | O(n) |
| `sentence` | Narrative text, legal docs | O(n) |
| `hierarchical` | Multi-granularity retrieval | O(n) |

### Configuration
```python
class ChunkingConfig(BaseModel):
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 512              # Target tokens
    chunk_overlap: int = 50            # Overlap tokens
    min_chunk_size: int = 50           # Discard smaller
    max_chunk_size: Optional[int] = None
    respect_boundaries: bool = True    # Sentence/paragraph
    use_tokens: bool = True            # vs characters
    encoding_name: str = "cl100k_base" # tiktoken encoding
```

### Token Counting
- Uses `tiktoken` for accurate token counts
- Fallback to character estimation if unavailable
- Stored in `ChunkMetadata.token_count`

---

## backend/data/embeddings/

### Responsibility
Generate dense vector embeddings for chunks and queries.

### Components

| Component | Responsibility |
|-----------|----------------|
| `base.py` | `BaseEmbedder` with batching, caching, retry logic |
| `openai.py` | `OpenAIEmbedder` - OpenAI API |
| `cohere.py` | `CohereEmbedder` - Cohere API |
| `voyage.py` | `VoyageEmbedder` - Voyage AI API |
| `sentence_transformers.py` | `SentenceTransformerEmbedder` - Local models |
| `huggingface.py` | `HuggingFaceEmbedder` - Transformers models |
| `factory.py` | `EmbedderFactory.create(provider, config)` |
| `cache.py` | Redis/memory caching layer |

### Interface
```python
class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[Vector]: ...
    async def embed_query(self, text: str) -> Vector: ...
    
    # Properties
    @property
    def dimension(self) -> int: ...
    @property
    def model_name(self) -> str: ...
    @property
    def max_batch_size(self) -> int: ...
```

### Providers

| Provider | Models | Dim | Latency | Cost |
|----------|--------|-----|---------|------|
| OpenAI | `text-embedding-3-small`, `text-embedding-3-large` | 1536, 3072 | Low | $/1M tokens |
| Cohere | `embed-english-v3.0`, `embed-multilingual-v3.0` | 1024 | Low | $/1M tokens |
| Voyage | `voyage-3`, `voyage-3-large`, `voyage-code-2` | 1024, 2048 | Low | $/1M tokens |
| Sentence Transformers | `BAAI/bge-*`, `intfloat/e5-*`, `sentence-transformers/*` | 384-1024 | Med (GPU) | Free |
| HuggingFace | Any HF model | Varies | Med (GPU) | Free |

### Configuration
```python
class EmbeddingConfig(BaseModel):
    provider: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    model: str = "BAAI/bge-small-en-v1.5"
    batch_size: int = 32
    max_retries: int = 3
    timeout_seconds: float = 30.0
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 86400
    
    # Local model settings
    device: str = "auto"  # auto, cpu, cuda, mps
    normalize_embeddings: bool = True
    
    # API settings
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    organization: Optional[str] = None
```

### Caching
- Key: `sha256(model + text)`
- Store: Redis (prod) or in-memory (dev)
- TTL: Configurable (default 24h)
- Metrics: Hit rate, size, evictions

---

## backend/data/vectorstore/

### Responsibility
Persist and search vector embeddings with metadata.

### Components

| Component | Responsibility |
|-----------|----------------|
| `base.py` | `BaseVectorStore` with common ops |
| `faiss.py` | `FAISSVectorStore` - In-memory, file-backed |
| `chroma.py` | `ChromaVectorStore` - Embedded SQLite |
| `pinecone.py` | `PineconeVectorStore` - Managed cloud |
| `weaviate.py` | `WeaviateVectorStore` - Managed/self-hosted |
| `qdrant.py` | `QdrantVectorStore` - Self-hosted/managed |
| `lancedb.py` | `LanceDBVectorStore` - Columnar, embedded |
| `factory.py` | `VectorStoreFactory.create(provider, config)` |
| `bm25.py` | BM25 index management (sparse search) |

### Interface
```python
class VectorStore(Protocol):
    async def upsert(self, chunks: list[Chunk]) -> UpsertResult: ...
    async def search(
        self, 
        query: Vector, 
        top_k: int, 
        filter: Optional[MetadataFilter] = None
    ) -> list[Chunk]: ...
    async def delete(self, ids: list[UUID]) -> DeleteResult: ...
    async def get(self, ids: list[UUID]) -> list[Chunk]: ...
    async def count(self, filter: Optional[MetadataFilter] = None) -> int: ...
    
    # Properties
    @property
    def dimension(self) -> int: ...
    @property
    def metric(self) -> DistanceMetric: ...
```

### Metadata Filtering
```python
class MetadataFilter(BaseModel):
    # Exact match
    document_ids: Optional[list[UUID]] = None
    source_types: Optional[list[DocumentSourceType]] = None
    languages: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    sensitivity: Optional[SensitivityLevel] = None
    
    # Range
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Text search (for BM25)
    text_query: Optional[str] = None
    
    # Custom (provider-specific)
    custom: dict[str, Any] = Field(default_factory=dict)
```

### Hybrid Search Support
- Dense: Vector similarity search
- Sparse: BM25 index (separate or integrated)
- Fusion: Handled by retriever, not vector store

### Configuration
```python
class VectorStoreConfig(BaseModel):
    provider: VectorStoreProvider = VectorStoreProvider.FAISS
    
    # FAISS
    faiss: FAISSConfig = FAISSConfig()
    
    # Chroma
    chroma: ChromaConfig = ChromaConfig()
    
    # Pinecone
    pinecone: PineconeConfig = PineconeConfig()
    
    # Weaviate
    weaviate: WeaviateConfig = WeaviateConfig()
    
    # Qdrant
    qdrant: QdrantConfig = QdrantConfig()
    
    # Common
    collection_name: str = "documents"
    dimension: int = 1536
    metric: DistanceMetric = DistanceMetric.COSINE
```

---

## backend/data/retrieval/

### Responsibility
Find relevant chunks for a query using various search strategies.

### Components

| Component | Responsibility |
|-----------|----------------|
| `dense.py` | `DenseRetriever` - Vector similarity search |
| `sparse.py` | `SparseRetriever` - BM25 keyword search |
| `hybrid.py` | `HybridRetriever` - Fusion of dense + sparse |
| `multi_vector.py` | `MultiVectorRetriever` - ColBERT, late interaction |
| `query_expansion/` | Query rewriting, decomposition, HyDE |
| `factory.py` | `RetrieverFactory.create(config, vector_store, embedder)` |

### Interface
```python
class Retriever(Protocol):
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]: ...
```

### Retrieval Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| `DenseRetriever` | Embed query, search vector store | Semantic similarity |
| `SparseRetriever` | BM25 on chunk content | Exact keyword matching |
| `HybridRetriever` | RRF/weighted fusion | Best of both |
| `MultiVectorRetriever` | ColBERT/late interaction | Fine-grained matching |

### Hybrid Fusion Algorithms

#### RRF (Reciprocal Rank Fusion)
```python
def rrf_fusion(dense_results, sparse_results, k=60):
    scores = defaultdict(float)
    for rank, result in enumerate(dense_results):
        scores[result.chunk.id] += 1 / (k + rank + 1)
    for rank, result in enumerate(sparse_results):
        scores[result.chunk.id] += 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### Weighted Fusion
```python
def weighted_fusion(dense_results, sparse_results, w_dense=0.7, w_sparse=0.3):
    # Normalize scores to [0,1] per method
    dense_norm = normalize([r.score for r in dense_results])
    sparse_norm = normalize([r.score for r in sparse_results])
    # Combine
    ...
```

### Configuration
```python
class RetrievalConfig(BaseModel):
    dense_enabled: bool = True
    sparse_enabled: bool = True
    hybrid_fusion: HybridFusionMethod = HybridFusionMethod.RRF
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    top_k: int = 20
    similarity_threshold: float = 0.0
    rrf_k: int = 60
```

---

## backend/data/reranking/

### Responsibility
Re-score retrieval results for higher precision using cross-encoders or API rerankers.

### Components

| Component | Responsibility |
|-----------|----------------|
| `cohere.py` | `CohereReranker` - Cohere rerank API |
| `jina.py` | `JinaReranker` - Jina AI rerank API |
| `cross_encoder.py` | `CrossEncoderReranker` - Local sentence-transformers |
| `bge_reranker.py` | `BGEReranker` - BAAI/bge-reranker-* models |
| `llm_reranker.py` | `LLMReranker` - LLM-based listwise reranking |
| `factory.py` | `RerankerFactory.create(config)` |

### Interface
```python
class Reranker(Protocol):
    async def rerank(
        self, 
        query: str, 
        results: list[RetrievalResult], 
        top_n: int
    ) -> list[RetrievalResult]: ...
```

### Rerankers

| Reranker | Type | Latency | Quality | Cost |
|----------|------|---------|---------|------|
| Cohere | API | Low | Very High | $/1K docs |
| Jina | API | Low | Very High | $/1K docs |
| CrossEncoder | Local | Med | High | Free (GPU) |
| BGE-Reranker | Local | Med | High | Free (GPU) |
| LLM | API | High | Highest | $/1K tokens |

### Configuration
```python
class RerankConfig(BaseModel):
    enabled: bool = True
    provider: RerankerProvider = RerankerProvider.COHERE
    model: str = "rerank-english-v3.0"
    top_n: int = 5
    batch_size: int = 32
    timeout_seconds: float = 10.0
```

---

## backend/data/generation/

### Responsibility
Generate grounded answers with citations using LLMs.

### Components

| Component | Responsibility |
|-----------|----------------|
| `base.py` | `BaseGenerator` with prompt building, citation extraction |
| `openai.py` | `OpenAIGenerator` - OpenAI Chat/Responses API |
| `anthropic.py` | `AnthropicGenerator` - Anthropic Messages API |
| `ollama.py` | `OllamaGenerator` - Local Ollama |
| `vllm.py` | `VLLMGenerator` - Self-hosted vLLM |
| `tgi.py` | `TGIGenerator` - Text Generation Inference |
| `factory.py` | `GeneratorFactory.create(config)` |
| `prompts/` | System prompts, few-shot examples |
| `citation.py` | `CitationExtractor` - Parse citations from answer |
| `verification.py` | `GroundingVerifier` - Check claims against context |

### Interface
```python
class Generator(Protocol):
    async def generate(self, query: str, context: list[RetrievalResult]) -> GenerationResult: ...
    async def stream_generate(self, query: str, context: list[RetrievalResult]) -> AsyncIterator[str]: ...
```

### Generation Flow
```
1. Build context string with citation markers [doc_1], [doc_2]...
2. Construct prompt: system + few-shot + query + context
3. Call LLM (streaming or sync)
4. Extract citations from answer (regex for [doc_N])
5. Map citation markers to source chunks
6. (Optional) Verify grounding
7. Return GenerationResult
```

### Configuration
```python
class GenerationConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    max_context_tokens: int = 8192
    max_output_tokens: int = 2048
    temperature: float = 0.1
    top_p: float = 0.95
    citation_enabled: bool = True
    grounding_check: bool = False
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)
```

### Citation Format
```
Answer text [doc_1] more text [doc_2, doc_3].
```
Maps to:
```python
Citation(chunk_id=..., document_id=..., text="...", char_start=10, char_end=18)
```

---

## backend/data/evaluation/

### Responsibility
Automated quality evaluation using standard and custom metrics.

### Components

| Component | Responsibility |
|-----------|----------------|
| `datasets/` | Dataset loaders (RAGAS, custom formats) |
| `metrics/` | Metric implementations (RAGAS, DeepEval, custom) |
| `computer.py` | `MetricsComputer` - Batch metric computation |
| `runner.py` | `EvaluationRunner` - Orchestrates eval pipeline |
| `factory.py` | Metric/dataset factory |
| `reporting.py` | Report generation (HTML, JSON, Markdown) |

### Interface
```python
class Evaluator(Protocol):
    async def evaluate(self, dataset: EvaluationDataset) -> EvaluationResult: ...

class Metric(Protocol):
    name: str
    async def compute(
        self, 
        samples: list[EvaluationSample], 
        predictions: list[QueryResponse]
    ) -> MetricResult: ...
```

### Built-in Metrics

| Metric | Source | Type | Description |
|--------|--------|------|-------------|
| `faithfulness` | RAGAS | LLM-based | Answer grounded in context |
| `answer_relevancy` | RAGAS | LLM-based | Answer addresses query |
| `context_precision` | RAGAS | LLM-based | Relevant chunks ranked high |
| `context_recall` | RAGAS | LLM-based | All relevant chunks retrieved |
| `context_relevancy` | RAGAS | LLM-based | Chunks relevant to query |
| `answer_correctness` | RAGAS | LLM-based | Semantic match to expected |
| `hallucination_rate` | Custom | Heuristic | Unsupported claims |
| `citation_accuracy` | Custom | Heuristic | Citations match sources |
| `latency_p50/p95/p99` | System | Observability | End-to-end latency |

### Configuration
```python
class EvaluationConfig(BaseModel):
    dataset_path: str
    metrics: list[str] = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    batch_concurrency: int = 10
    sample_limit: Optional[int] = None
    track_experiment: bool = True
    save_predictions: bool = True
```

---

## backend/data/experiments/

### Responsibility
Experiment tracking with full reproducibility (config, code, data, metrics, artifacts).

### Components

| Component | Responsibility |
|-----------|----------------|
| `tracker.py` | `ExperimentTracker` protocol + implementations |
| `mlflow_tracker.py` | `MLflowTracker` - MLflow backend |
| `wandb_tracker.py` | `WandbTracker` - Weights & Biases backend |
| `factory.py` | `TrackerFactory.create(config)` |
| `context.py` | `TrackedPipeline` - Context manager for auto-tracking |

### Interface
```python
class ExperimentTracker(Protocol):
    def create_experiment(self, name: str, tags: dict) -> str: ...
    def start_run(self, experiment_id: str, run_name: str, config: dict) -> Run: ...
    def log_params(self, run_id: str, params: dict) -> None: ...
    def log_metrics(self, run_id: str, metrics: dict, step: Optional[int] = None) -> None: ...
    def log_artifact(self, run_id: str, path: str, name: Optional[str] = None) -> None: ...
    def end_run(self, run_id: str, status: RunStatus) -> None: ...
    def get_run(self, run_id: str) -> Run: ...
    def search_runs(self, experiment_ids: list[str], filter: str) -> list[Run]: ...
```

### Tracked Entities
- **Experiment**: Name, tags, default config
- **Run**: Config snapshot, params, metrics, artifacts, status
- **Artifact**: Model, dataset, report, log, predictions, config

### Configuration
```python
class ExperimentSettings(BaseModel):
    tracker: ExperimentTrackerType = ExperimentTrackerType.MLFLOW
    mlflow: MLflowConfig = MLflowConfig()
    wandb: WandbConfig = WandbConfig()
    auto_track: bool = True
    log_config: bool = True
    log_artifacts: bool = True
```

---

## backend/data/prompts/

### Responsibility
Prompt template management, versioning, and rendering.

### Components

| Component | Responsibility |
|-----------|----------------|
| `templates/` | Jinja2 prompt templates |
| `registry.py` | `PromptRegistry` - Load, version, render |
| `versioning.py` | Prompt version management |
| `few_shot.py` | Few-shot example management |

### Template Example
```jinja2
{# prompts/generation/system.j2 #}
You are a helpful assistant that answers questions using only the provided context.
Always cite your sources using [doc_N] format.

{% if few_shot_examples %}
Examples:
{% for ex in few_shot_examples %}
Q: {{ ex.query }}
Context: {{ ex.context }}
A: {{ ex.answer }}
{% endfor %}
{% endif %}

Context:
{% for i, chunk in enumerate(context) %}
[doc_{{ i+1 }}]: {{ chunk.content }}
{% endfor %}

Question: {{ query }}
Answer:
```

### Configuration
```python
class PromptConfig(BaseModel):
    template_dir: str = "backend/data/prompts/templates"
    version: str = "latest"
    default_system_prompt: str = "default"
    few_shot_k: int = 3
```

---

## backend/data/utils/

### Responsibility
Shared utilities used across multiple pipeline stages.

### Components

| Component | Responsibility |
|-----------|----------------|
| `tokenize.py` | Token counting, truncation (tiktoken) |
| `hash.py` | Content hashing (SHA256, xxhash) |
| `text.py` | Text utilities (truncate, split, clean) |
| `async.py` | Async utilities (gather_with_concurrency, retry) |
| `metrics.py` | Prometheus metric helpers |
| `logging.py` | Structured logging helpers |
| `validation.py` | Common validators |

### Key Utilities
```python
# Token management
def count_tokens(text: str, model: str = "cl100k_base") -> int: ...
def truncate_to_tokens(text: str, max_tokens: int, model: str) -> str: ...

# Hashing
def content_hash(text: str) -> str: ...
def dict_hash(d: dict) -> str: ...

# Async
async def gather_with_concurrency(n: int, *tasks) -> list: ...
async def retry_with_backoff(fn, max_retries=3, base_delay=1.0): ...
```

---

## Cross-Module Dependencies

```
backend/core/protocols.py
       ▲
       │ implements
       │
┌──────┴──────┐
│             │
│  backend/data/loaders
│  backend/data/preprocessing
│  backend/data/chunking
│  backend/data/embeddings
│  backend/data/vectorstore
│  backend/data/retrieval
│  backend/data/reranking
│  backend/data/generation
│  backend/data/evaluation
│  backend/data/experiments
│  backend/data/prompts
│             │
│             │ uses
│             ▼
│  backend/data/models (domain models)
│             │
│             │ configures
│             ▼
│  backend/configs/settings
│             │
│             │ injects into
│             ▼
│  backend/api/dependencies
```

---

## Module Communication Rules

1. **No direct imports** between `backend/data/<stage>/` modules
2. **Core protocols only** for cross-stage dependencies
3. **Factory pattern** for instantiation (config-driven)
4. **Domain models** from `backend/data/models/` for data exchange
5. **Events** for side effects (logging, metrics, experiment tracking)
6. **No circular dependencies** - enforced by import structure

---

## Testing Responsibilities

| Module | Unit Tests | Integration Tests |
|--------|------------|-------------------|
| `core` | 100% protocol compliance | N/A |
| `configs` | Validation, feature flags | N/A |
| `models` | Serialization, validation | N/A |
| `loaders` | Per-format parsing | Real file loading |
| `preprocessing` | Step-by-step, pipeline | End-to-end |
| `chunking` | Strategy outputs, golden files | Document chunking |
| `embeddings` | Mock providers, batching | Real API calls |
| `vectorstore` | Mock stores, CRUD | Real store ops |
| `retrieval` | Algorithm correctness | End-to-end search |
| `reranking` | Mock rerankers | Real reranking |
| `generation` | Prompt building, citations | Real LLM calls |
| `evaluation` | Metric computation | Full eval runs |
| `experiments` | Mock trackers | Real tracking |
| `api` | Schema validation | TestClient integration |

---

## Adding a New Module

1. Create `backend/data/<new_module>/`
2. Define protocol in `backend/core/protocols.py`
3. Implement base class and concrete implementations
4. Add factory with registration
5. Add config section in `backend/configs/settings.py`
6. Write tests in `backend/tests/unit/test_data/test_<new_module>/`
7. Document in `docs/architecture/06_component_responsibilities.md`