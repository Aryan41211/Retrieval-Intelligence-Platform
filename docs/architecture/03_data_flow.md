# Data Flow Architecture

## Overview

This document describes the complete data flow through the Retrieval Intelligence Platform, covering both the **ingestion pipeline** (index time) and **query pipeline** (request time), with detailed stage-by-stage specifications.

## Ingestion Pipeline (Index Time)

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           INGESTION PIPELINE                                           │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Source          Loader           Preprocessor         Chunker           Embedder          Vector    │
│  ─────────────▶  ─────────────▶  ──────────────────▶  ─────────────▶   ─────────────▶   ────────   │
│  Files/URLs      Raw Document     Cleaned Document    Chunks            Vector Chunks     Index     │
│                                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Document Loading

**Purpose**: Extract text and metadata from various source formats into a unified `Document` model.

**Inputs**:
- `DocumentSource` (file path, URL, bytes, stream)
- Source type detection (extension, MIME, content inspection)

**Outputs**:
- `list[Document]` with:
  - `id`: UUID (generated)
  - `content`: Raw extracted text
  - `metadata`: `DocumentMetadata` (source-specific fields)
  - `source`: `DocumentSource` (type, path, URI, checksum)
  - `created_at`: Timestamp

**Dependencies**:
- `unstructured` for complex formats (PDF, DOCX, PPTX, XLSX)
- `pypdf` for PDF text extraction
- `python-docx` for Word documents
- `python-pptx` for PowerPoint
- `openpyxl` for Excel
- Custom loaders for HTML, Markdown, plain text

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Unsupported format | `LoaderError` with list of supported formats |
| Corrupted file | `LoaderError` with file path, skip/continue option |
| Password-protected | `LoaderError` with hint to provide password |
| Empty document | Warning log, return empty content Document |
| Encoding errors | Replace invalid chars, log warning |

**Future Improvements**:
- OCR integration for scanned PDFs/images
- Cloud storage loaders (S3, GCS, Azure Blob)
- Confluence, Notion, SharePoint connectors
- Incremental loading (modified time tracking)
- Parallel loading with configurable concurrency

---

### Stage 2: Preprocessing

**Purpose**: Clean and normalize text content, enrich metadata.

**Inputs**:
- `list[Document]` from Loader

**Outputs**:
- `list[Document]` with:
  - `content`: Cleaned, normalized text
  - `metadata`: Enriched `DocumentMetadata` (language, stats, structure)

**Processing Steps**:
1. **Unicode normalization**: NFC form, replace control characters
2. **Whitespace normalization**: Collapse multiple spaces, normalize line endings
3. **Boilerplate removal**: Headers, footers, page numbers (configurable patterns)
4. **Language detection**: `langdetect` or `fasttext`, store in metadata
5. **Structure preservation**: Markdown headings, code blocks, tables → metadata
6. **Statistics**: Character count, word count, estimated tokens

**Dependencies**:
- `ftfy` for text fixing
- `langdetect` or `fasttext` for language ID
- `markdown-it-py` for Markdown structure extraction

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Language detection fails | Default to `en`, log warning |
| Text too long for processing | Chunk preprocessing, log metric |
| Memory pressure | Stream processing, configurable batch size |

**Future Improvements**:
- PII detection and redaction (spaCy, Presidio)
- Translation to canonical language (English)
- Custom regex/pattern cleaning rules
- HTML/XML entity decoding
- Table extraction to structured format

---

### Stage 3: Chunking

**Purpose**: Split documents into semantically meaningful chunks with overlap for retrieval.

**Inputs**:
- `list[Document]` from Preprocessor

**Outputs**:
- `list[Chunk]` with:
  - `id`: UUID
  - `document_id`: Reference to parent Document
  - `content`: Chunk text
  - `start_char`, `end_char`: Position in original document
  - `chunk_index`: Sequential index within document
  - `metadata`: `ChunkMetadata` (strategy, token count, overlap info)

**Strategies**:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `fixed` | Fixed character/token size with overlap | Simple, predictable |
| `recursive` | Recursively split by separators (`\n\n`, `\n`, `. `, ` `) | General purpose |
| `semantic` | Embedding-based semantic boundary detection | High-quality retrieval |
| `markdown` | Split on heading hierarchy, preserve code blocks | Technical docs |
| `sentence` | Sentence-boundary aware (NLTK/spaCy) | Narrative text |

**Configuration** (per strategy):
```python
class ChunkingConfig(BaseModel):
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 512          # Target tokens/chars
    chunk_overlap: int = 50        # Overlap between chunks
    min_chunk_size: int = 50       # Discard smaller
    respect_boundaries: bool = True # Don't split mid-sentence/paragraph
```

**Dependencies**:
- `tiktoken` for token counting
- `sentence-transformers` for semantic chunking
- `markdown-it-py` for Markdown strategy
- `nltk`/`spacy` for sentence strategy

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Chunk exceeds model context | Auto-split with warning |
| Empty chunks produced | Filter out, log metric |
| Semantic chunking OOM | Fallback to recursive, log warning |

**Future Improvements**:
- Hierarchical chunking (parent-child relationships)
- Dynamic chunk sizing by content density
- Table-aware chunking (keep tables intact)
- Figure/caption association
- Chunk quality scoring

---

### Stage 4: Embedding

**Purpose**: Convert chunk text into dense vector representations for similarity search.

**Inputs**:
- `list[Chunk]` from Chunker (text content)

**Outputs**:
- `list[Chunk]` with `embedding: Vector` populated (same objects, mutated)

**Providers**:

| Provider | Models | Dimensions | Latency | Cost |
|----------|--------|------------|---------|------|
| OpenAI | `text-embedding-3-small`, `text-embedding-3-large` | 1536, 3072 | Low | Per-token |
| Cohere | `embed-english-v3.0`, `embed-multilingual-v3.0` | 1024 | Low | Per-token |
| Voyage AI | `voyage-3`, `voyage-3-large`, `voyage-code-2` | 1024, 2048 | Low | Per-token |
| Sentence Transformers | `BAAI/bge-*`, `intfloat/e5-*`, `sentence-transformers/*` | 384-1024 | Medium (GPU) | Free (local) |

**Processing**:
1. Batch chunks (configurable batch size, default 32)
2. Call provider `embed_documents(texts: list[str]) -> list[Vector]`
3. Attach vectors to chunks
4. Cache embeddings (Redis, keyed by content hash)
5. Emit metrics: batch latency, token count, cache hit rate

**Dependencies**:
- Provider SDKs (`openai`, `cohere`, `voyageai`, `sentence-transformers`)
- `torch` for local models
- Redis for caching (optional)

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| API rate limit | Exponential backoff, retry (tenacity) |
| Invalid API key | `EmbeddingError` with provider name |
| Token limit exceeded | Auto-truncate with warning |
| Provider unavailable | Circuit breaker, fallback provider (config) |
| Dimension mismatch | Validation error at startup |

**Future Improvements**:
- Multi-vector embeddings (ColBERT, SPLADE)
- Late interaction embeddings
- Embedding quantization (int8, binary)
- Asynchronous batch processing with queue
- Embedding versioning for reprocessing

---

### Stage 5: Vector Store Upsert

**Purpose**: Store chunks with embeddings and metadata for efficient retrieval.

**Inputs**:
- `list[Chunk]` with embeddings from Embedder

**Outputs**:
- `UpsertResult`: `success_count`, `failed_ids`, `latency_ms`

**Operations**:
1. Prepare vectors + metadata payload
2. Batch upsert to vector store
3. Build/update BM25 index (if hybrid enabled)
4. Update document-chunk mapping in metadata DB
5. Emit metrics: upsert latency, vector count, index size

**Vector Stores**:

| Store | Type | Hybrid Support | Metadata Filtering | Scale |
|-------|------|----------------|-------------------|-------|
| FAISS | In-memory | Manual BM25 | Limited | 10M+ |
| Chroma | Embedded | Native | Good | 1M+ |
| Pinecone | Managed | Native | Excellent | 100M+ |
| Weaviate | Managed | Native | Excellent | 100M+ |
| Qdrant | Self-managed | Native | Excellent | 100M+ |

**Metadata Schema** (stored with vectors):
```json
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "document_title": "string",
  "document_source": "string",
  "chunk_index": 0,
  "start_char": 0,
  "end_char": 512,
  "token_count": 128,
  "language": "en",
  "created_at": "ISO8601",
  "custom_fields": {}
}
```

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Vector dimension mismatch | Validation at startup |
| Index full | Auto-resize (FAISS) or error (managed) |
| Metadata too large | Truncate, log warning |
| Network timeout | Retry with backoff |
| Duplicate IDs | Upsert (replace) or error (config) |

**Future Improvements**:
- Namespaces/collections for multi-tenancy
- Incremental index updates
- Index versioning and rollback
- Distributed indexing (sharding)
- Compressed vectors (PQ, SQ)

---

## Query Pipeline (Request Time)

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            QUERY PIPELINE                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Query          Expansion        Retrieval           Reranking           Generation          Response │
│  ──────────▶  ─────────────▶  ────────────────▶  ────────────────▶  ─────────────────▶  ─────────   │
│  Request      Expanded         Candidates         Ranked              Grounded            Formatted  │
│  Query        Queries          (Dense+Sparse)     Results             Answer              Answer     │
│                                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Query Expansion (Optional)

**Purpose**: Improve recall by generating alternative query representations.

**Inputs**:
- `QueryRequest`: `query: str`, `filters: MetadataFilter`, `params: QueryParams`

**Outputs**:
- `ExpandedQuery`:
  - `original_query: str`
  - `sub_queries: list[str]` (decomposed questions)
  - `rewritten_query: str` (LLM-rewritten for clarity)
  - `hypothetical_doc_embeddings: list[Vector]` (HyDE)

**Methods**:
| Method | Description | Configuration |
|--------|-------------|---------------|
| `none` | No expansion | Default |
| `rewrite` | LLM rewrites query | `generation.rewrite_model` |
| `decompose` | Break into sub-questions | `generation.decompose_model` |
| `hyde` | Generate hypothetical doc, embed | `embeddings.hyde_model` |
| `multi` | Combine multiple | All enabled |

**Dependencies**:
- Generator for rewrite/decompose
- Embedder for HyDE

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| LLM timeout | Skip expansion, use original |
| Expansion produces empty | Log warning, continue |
| Too many sub-queries | Cap at `max_sub_queries` (default 5) |

**Future Improvements**:
- Query classification (factoid, exploratory, etc.)
- Conversation context integration
- Query intent detection
- Learned expansion from feedback

---

### Stage 2: Retrieval

**Purpose**: Find top-K relevant chunks from vector store using dense, sparse, or hybrid search.

**Inputs**:
- `ExpandedQuery` from Query Expander

**Outputs**:
- `list[RetrievalResult]`:
  - `chunk: Chunk`
  - `score: float` (normalized 0-1)
  - `retrieval_method: RetrievalMethod` (DENSE, SPARSE, HYBRID)
  - `rank: int`

**Search Modes**:

```python
class RetrievalConfig(BaseModel):
    dense_enabled: bool = True
    sparse_enabled: bool = True
    hybrid_fusion: HybridFusion = HybridFusion.RRF  # RRF, WEIGHTED, DBSF
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    top_k: int = 20
    similarity_threshold: float = 0.0
    metadata_filter: Optional[MetadataFilter] = None
```

**Dense Search**: Vector similarity (cosine, dot product, L2)
**Sparse Search**: BM25 on chunk content (stored in vector store or separate index)
**Hybrid Fusion**:
- **RRF** (Reciprocal Rank Fusion): `score = 1/(k + rank_dense) + 1/(k + rank_sparse)`
- **Weighted**: `score = w_dense * norm(score_dense) + w_sparse * norm(score_sparse)`
- **DBSF** (Distribution-Based Score Fusion): Normalize by score distribution

**Dependencies**:
- Vector store `search()` method
- Embedder for query embedding
- BM25 index (if sparse enabled)

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| No results | Return empty, log metric |
| Vector store timeout | Return partial results, degrade gracefully |
| Embedding failure | Fallback to sparse only |
| Filter yields no results | Relax filter, log warning |

**Future Improvements**:
- Multi-vector retrieval (ColBERT)
- Learned sparse retrieval (SPLADE)
- Query-time filtering pushdown
- Approximate nearest neighbor tuning
- Retrieval caching for repeated queries

---

### Stage 3: Reranking (Optional)

**Purpose**: Improve precision by re-scoring retrieval candidates with cross-encoder or API rerankers.

**Inputs**:
- `list[RetrievalResult]` from Retriever (top-K, default 20)

**Outputs**:
- `list[RetrievalResult]` reranked, truncated to `top_n` (default 5)

**Rerankers**:

| Reranker | Type | Latency | Quality |
|----------|------|---------|---------|
| `cross-encoder` | Local (sentence-transformers) | Medium | High |
| `cohere` | API (rerank-english-v3.0) | Low | Very High |
| `jina` | API (jina-reranker-v2) | Low | Very High |
| `bge-reranker` | Local (BAAI/bge-reranker-*) | Medium | High |

**Configuration**:
```python
class RerankConfig(BaseModel):
    enabled: bool = True
    provider: RerankerProvider = RerankerProvider.COHERE
    model: str = "rerank-english-v3.0"
    top_n: int = 5
    batch_size: int = 32
```

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Reranker timeout | Return original ranking |
| API quota exceeded | Disable reranking, log alert |
| Model not loaded | Lazy load, cache in memory |

**Future Improvements**:
- Listwise reranking (LLM-based)
- Diversity-aware reranking (MMR)
- Personalized reranking
- Cascade reranking (fast → slow)

---

### Stage 4: Generation

**Purpose**: Produce grounded answer with citations from retrieved context.

**Inputs**:
- `query: str` (original)
- `context: list[RetrievalResult]` (reranked, top-N)

**Outputs**:
- `GenerationResult`:
  - `answer: str`
  - `citations: list[Citation]` (chunk_id, text_span, char_start, char_end)
  - `metadata: GenerationMetadata` (tokens, latency, model, groundedness_score)

**Process**:
1. **Context Building**: Format chunks with citation markers `[doc_1]`, `[doc_2]`
2. **Prompt Construction**: System prompt + few-shot + query + context
3. **LLM Call**: Streaming or synchronous
4. **Citation Extraction**: Parse answer for citation markers, map to chunks
5. **Grounding Verification**: Check claims against context (optional)
6. **Post-processing**: Clean formatting, validate citations

**Configuration**:
```python
class GenerationConfig(BaseModel):
    model: str = "gpt-4o-mini"
    max_context_tokens: int = 8192
    max_output_tokens: int = 2048
    temperature: float = 0.1
    top_p: float = 0.95
    citation_enabled: bool = True
    grounding_check: bool = False
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
```

**Providers**:
- OpenAI (Chat Completions, Responses API)
- Anthropic (Messages API)
- Ollama (local)
- vLLM / TGI (self-hosted)

**Failure Cases**:
| Scenario | Handling |
|----------|----------|
| Context exceeds limit | Truncate lowest-ranked chunks |
| LLM timeout | Return partial answer, mark incomplete |
| Citation parsing fails | Return answer without citations |
| Grounding check fails | Flag in metadata, don't block |
| Safety filter triggers | Return refusal with explanation |

**Future Improvements**:
- Structured output (JSON schema)
- Chain-of-thought prompting
- Self-consistency sampling
- Citation verification with entailment
- Streaming with progressive citations

---

### Stage 5: Response Assembly

**Purpose**: Format final response with all metadata for client and observability.

**Inputs**:
- `GenerationResult` from Generator
- `RetrievalMetadata` from Retriever/Reranker
- `QueryMetadata` (expansion, timing)

**Outputs**:
- `QueryResponse`:
  - `answer: str`
  - `citations: list[CitationResponse]`
  - `retrieval_metadata: RetrievalMetadata`
  - `generation_metadata: GenerationMetadata`
  - `query_metadata: QueryMetadata`
  - `correlation_id: str`
  - `timestamp: datetime`

**Metrics Emitted**:
- End-to-end latency (p50, p95, p99)
- Stage latencies (retrieval, rerank, generation)
- Token counts (prompt, completion)
- Retrieval scores distribution
- Citation coverage

---

## Data Contracts Summary

### Core Models (`backend/data/models/`)

```python
# Document ingestion
class Document(BaseModel):
    id: UUID
    content: str
    metadata: DocumentMetadata
    source: DocumentSource
    created_at: datetime
    updated_at: datetime

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    mime_type: Optional[str] = None
    language: Optional[str] = None
    char_count: int
    word_count: int
    token_count_estimate: int
    structure: Optional[DocumentStructure] = None
    custom: dict[str, Any] = Field(default_factory=dict)

class DocumentSource(BaseModel):
    type: DocumentSourceType  # FILE, URL, API, DATABASE
    path: Optional[str] = None
    url: Optional[str] = None
    checksum: str  # SHA256 of content
    metadata: dict = Field(default_factory=dict)

# Chunking
class Chunk(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    start_char: int
    end_char: int
    chunk_index: int
    metadata: ChunkMetadata
    embedding: Optional[Vector] = None

class ChunkMetadata(BaseModel):
    chunking_strategy: ChunkingStrategy
    token_count: int
    overlap_tokens: int
    parent_chunk_id: Optional[UUID] = None  # For hierarchical
    child_chunk_ids: list[UUID] = Field(default_factory=list)

# Retrieval
class RetrievalResult(BaseModel):
    chunk: Chunk
    score: float = Field(ge=0.0, le=1.0)
    retrieval_method: RetrievalMethod
    rank: int

class RetrievalMethod(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID_RRF = "hybrid_rrf"
    HYBRID_WEIGHTED = "hybrid_weighted"

# Generation
class GenerationResult(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: GenerationMetadata

class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    text: str
    char_start: int
    char_end: int
    confidence: Optional[float] = None

class GenerationMetadata(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    groundedness_score: Optional[float] = None
    citation_coverage: float  # Fraction of sentences with citations

# API
class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4096)
    filters: Optional[MetadataFilter] = None
    params: Optional[QueryParams] = None

class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    retrieval_metadata: RetrievalMetadata
    generation_metadata: GenerationMetadata
    query_metadata: QueryMetadata
    correlation_id: str
    timestamp: datetime
```

---

## Pipeline Execution Modes

### Synchronous (Default)
- Each stage completes before next starts
- Simple, predictable latency
- Suitable for low-throughput, high-latency tolerance

### Asynchronous Pipeline
- Stages connected via async queues
- Overlapped execution (embed next batch while upserting current)
- Higher throughput, more complex error handling

### Streaming Generation
- Generator yields tokens incrementally
- Client receives progressive response
- Citations appended at end or via separate stream

### Batch Ingestion
- Process multiple documents in single pipeline run
- Shared embedding batches, vector store transactions
- Progress tracking, resumability

---

## Observability Data Flow

```
Each Stage
     │
     ├──▶ Structured Logs (JSON) ──▶ Log Aggregator (Loki/ELK)
     │
     ├──▶ Metrics (Prometheus) ────▶ Prometheus ──▶ Grafana
     │       - stage.latency_ms
     │       - stage.items_processed
     │       - stage.errors_total
     │       - stage.cache_hit_rate
     │
     ├──▶ Traces (OpenTelemetry) ──▶ Jaeger/Tempo
     │       - Span per stage
     │       - Attributes: counts, sizes, config
     │
     └──▶ Events (Experiment Tracker) ──▶ MLflow/W&B
             - ingestion.completed
             - query.completed
             - evaluation.completed
```

---

## Failure Recovery

| Pipeline | Recovery Strategy |
|----------|-------------------|
| Ingestion | Checkpoint per document; retry failed; skip poison pills |
| Query | Circuit breakers per stage; graceful degradation (skip rerank, sparse-only) |
| Evaluation | Resume from last completed sample; idempotent metric computation |
| Experiments | Atomic runs; manual re-run from config |

---

## Data Quality Gates

| Stage | Validation |
|-------|------------|
| Loader | Non-empty content, valid UTF-8, checksum computed |
| Preprocessor | Language detected, stats computed, no control chars |
| Chunker | All chunks within size bounds, no overlaps lost, coverage = 100% |
| Embedder | Vector dimension matches config, no NaN/Inf, cacheable |
| Vector Store | Upsert count matches input, metadata queryable |
| Retrieval | Scores in [0,1], ranks sequential, no duplicate chunks |
| Generation | Answer non-empty, citations valid chunk IDs, tokens counted |