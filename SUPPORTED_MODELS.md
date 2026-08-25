# Supported Models & Providers

## LLM Providers

| Provider | Implementation | Status | Configuration |
|----------|---------------|--------|---------------|
| OpenAI | `OpenAICompatibleProvider` | ✅ Production | `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4o`) |
| Anthropic | `AnthropicProvider` | ✅ Production | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default: `claude-3-5-sonnet-20241022`) |
| Ollama | `OllamaProvider` | ✅ Production | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| NVIDIA NIM | `NIMProvider` | ✅ Production | `NIM_API_KEY`, `NIM_MODEL` |
| Fake | `FakeProvider` | ✅ Testing | Used in unit tests; no API key required |

**Provider architecture:** All providers implement the `LLMProvider` abstract
base class and are instantiated through `ProviderFactory`. Adding a new
provider requires implementing the base class and registering it in the factory.

## Embedding Providers

| Provider | Implementation | Status | Configuration |
|----------|---------------|--------|---------------|
| Sentence Transformers | `SentenceTransformerProvider` | ✅ Production | `EMBEDDING_MODEL` (default: `all-MiniLM-L6-v2`) |

**Planned embedding providers** (enums defined, not yet implemented):

| Provider | Status | Notes |
|----------|--------|-------|
| OpenAI | 📋 Planned | `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-small`) |
| Cohere | 📋 Planned | `COHERE_EMBEDDING_MODEL` (default: `embed-english-v3.0`) |
| VoyageAI | 📋 Planned | `VOYAGE_EMBEDDING_MODEL` (default: `voyage-2`) |
| Jina | 📋 Planned | `JINA_EMBEDDING_MODEL` (default: `jina-embeddings-v2-base-en`) |
| Instructor | 📋 Planned | `INSTRUCTOR_EMBEDDING_MODEL` (default: `hkunlp/instructor-xl`) |
| E5 | 📋 Planned | `E5_EMBEDDING_MODEL` (default: `intfloat/e5-large-v2`) |

## Vector Stores

| Store | Implementation | Status |
|-------|---------------|--------|
| FAISS | `FAISSVectorStore` | ✅ Production (in-memory with on-disk serialization) |

The `VectorStoreFactory` is extensible for additional stores (Chroma,
Pinecone, Weaviate, Qdrant) without modifying core retrieval logic.

## Chunking Strategies

| Strategy | Implementation | Status |
|----------|---------------|--------|
| Recursive | `RecursiveChunker` | ✅ Production (sentence/paragraph boundaries) |
| Sentence | `SentenceChunker` | ✅ Production (NLTK-based sentence splitting) |
| Markdown | `MarkdownChunker` | ✅ Production (header-aware section splitting) |

**Planned chunking strategies** (enums defined, not yet implemented): Fixed,
Semantic (embedding-based), Hierarchical.

## Retrieval

| Component | Implementation | Status |
|-----------|---------------|--------|
| Dense retrieval | FAISS vector similarity | ✅ Production |
| Sparse retrieval | `BM25Retriever` | ✅ Production |
| Hybrid fusion | `RRFFuser` (Reciprocal Rank Fusion) | ✅ Production |
| Reranking | `CrossEncoderReranker` | ✅ Production |
| Query expansion | `QueryExpander` | ✅ Production |
| Dynamic Top-K | `DynamicTopKSelector` | ✅ Production |

## Evaluation

| Framework | Integration | Status |
|-----------|-------------|--------|
| Ragas | Faithfulness, Relevancy, Precision, Recall | ✅ Production |
| DeepEval | Evaluation metrics | ✅ Production |

## Experiment Tracking

| Platform | Status |
|----------|--------|
| MLflow | ✅ Integrated (API-level, backend module setup planned) |
| Weights & Biases | ✅ Integrated (API-level, backend module setup planned) |

## Embedding Validation Framework

| Component | Status |
|-----------|--------|
| `EmbeddingBenchmark` | ✅ Production |
| `EmbeddingProfiler` | ✅ Production |
| `SimilarityAnalyzer` | ✅ Production |
| `DuplicateDetector` | ✅ Production |
| `EmbeddingStatistics` | ✅ Production |
| `EmbeddingVisualizer` | ✅ Production |
| `ValidationRunner` | ✅ Production |

## Document Formats

| Format | Extension | Loader | Status |
|--------|-----------|--------|--------|
| Plain Text | `.txt` | `TXTLoader` | ✅ Production |
| Markdown | `.md`, `.markdown` | `MarkdownLoader` | ✅ Production |
| PDF | `.pdf` | `PDFLoader` | ✅ Production |
| Word | `.docx` | `DOCXLoader` | ✅ Production |
