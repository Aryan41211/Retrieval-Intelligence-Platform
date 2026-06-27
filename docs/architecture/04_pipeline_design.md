# Pipeline Design

## Overview

This document details the design of each pipeline in the Retrieval Intelligence Platform, including component interfaces, configuration, error handling, and extension points.

## Pipeline Types

| Pipeline | Trigger | Purpose | Latency Target |
|----------|---------|---------|----------------|
| **Ingestion** | Scheduled, API, Event | Index documents | Minutes-hours |
| **Query** | HTTP Request | Answer questions | <2s (p95) |
| **Evaluation** | Scheduled, API, CI | Measure quality | Minutes |
| **Experiment** | Manual, Scheduled | Track iterations | Variable |

---

## Ingestion Pipeline Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INGESTION PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────┐    ┌──────────────┐    ┌──────────┐    ┌────────────┐    ┌────────────┐  │
│  │ Source  │───▶│  Loader      │───▶│ Preproc  │───▶│ Chunker    │───▶│ Embedder   │  │
│  │ Registry│    │  Factory     │    │ Pipeline │    │ Factory    │    │ Factory    │  │
│  └─────────┘    └──────────────┘    └──────────┘    └────────────┘    └──────┬─────┘  │
│                                                                                │        │
│                                                                                ▼        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                          VECTOR STORE FACTORY                                     │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                │  │
│  │  │  FAISS  │  │ Chroma  │  │ Pinecone│  │ Weaviate│  │  Qdrant │                │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘                │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Interfaces

#### Document Loader Factory
```python
# backend/data/loaders/factory.py
class LoaderFactory:
    _registry: dict[DocumentSourceType, type[DocumentLoader]] = {}
    
    @classmethod
    def register(cls, source_type: DocumentSourceType, loader_class: type[DocumentLoader]):
        cls._registry[source_type] = loader_class
    
    @classmethod
    def create(cls, source_type: DocumentSourceType, config: LoaderConfig) -> DocumentLoader:
        if source_type not in cls._registry:
            raise LoaderError(f"No loader for {source_type}")
        return cls._registry[source_type](config)
```

#### Preprocessing Pipeline
```python
# backend/data/preprocessing/pipeline.py
class PreprocessingPipeline:
    def __init__(self, steps: list[TextPreprocessor]):
        self.steps = steps
    
    def process(self, document: Document) -> Document:
        for step in self.steps:
            document = step.process(document)
        return document

# Default pipeline construction
def create_default_pipeline(config: PreprocessingConfig) -> PreprocessingPipeline:
    steps = [
        UnicodeNormalizer(config.unicode),
        WhitespaceNormalizer(config.whitespace),
        BoilerplateRemover(config.boilerplate_patterns),
        LanguageDetector(config.language),
        StructureExtractor(config.structure),
    ]
    return PreprocessingPipeline(steps)
```

#### Chunker Factory
```python
# backend/data/chunking/factory.py
class ChunkerFactory:
    _strategies: dict[ChunkingStrategy, type[Chunker]] = {}
    
    @classmethod
    def create(cls, strategy: ChunkingStrategy, config: ChunkingConfig) -> Chunker:
        if strategy == ChunkingStrategy.FIXED:
            return FixedChunker(config)
        elif strategy == ChunkingStrategy.RECURSIVE:
            return RecursiveChunker(config)
        elif strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(config)
        elif strategy == ChunkingStrategy.MARKDOWN:
            return MarkdownChunker(config)
        elif strategy == ChunkingStrategy.SENTENCE:
            return SentenceChunker(config)
        raise ChunkingError(f"Unknown strategy: {strategy}")
```

#### Embedder Factory
```python
# backend/data/embeddings/factory.py
class EmbedderFactory:
    _providers: dict[EmbeddingProvider, type[EmbeddingProvider]] = {}
    
    @classmethod
    def create(cls, provider: EmbeddingProvider, config: EmbeddingConfig) -> EmbeddingProvider:
        if provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbedder(config)
        elif provider == EmbeddingProvider.COHERE:
            return CohereEmbedder(config)
        elif provider == EmbeddingProvider.VOYAGE:
            return VoyageEmbedder(config)
        elif provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            return SentenceTransformerEmbedder(config)
        raise EmbeddingError(f"Unknown provider: {provider}")
```

#### Vector Store Factory
```python
# backend/data/vectorstore/factory.py
class VectorStoreFactory:
    _stores: dict[VectorStoreProvider, type[VectorStore]] = {}
    
    @classmethod
    def create(cls, provider: VectorStoreProvider, config: VectorStoreConfig) -> VectorStore:
        if provider == VectorStoreProvider.FAISS:
            return FAISSVectorStore(config)
        elif provider == VectorStoreProvider.CHROMA:
            return ChromaVectorStore(config)
        elif provider == VectorStoreProvider.PINECONE:
            return PineconeVectorStore(config)
        elif provider == VectorStoreProvider.WEAVIATE:
            return WeaviateVectorStore(config)
        elif provider == VectorStoreProvider.QDRANT:
            return QdrantVectorStore(config)
        raise VectorStoreError(f"Unknown provider: {provider}")
```

### Pipeline Orchestration

```python
# backend/data/ingestion/orchestrator.py
class IngestionPipeline:
    def __init__(
        self,
        loader_factory: LoaderFactory,
        preprocessing_pipeline: PreprocessingPipeline,
        chunker_factory: ChunkerFactory,
        embedder_factory: EmbedderFactory,
        vector_store_factory: VectorStoreFactory,
        config: IngestionConfig,
    ):
        self.loader_factory = loader_factory
        self.preprocessing = preprocessing_pipeline
        self.chunker_factory = chunker_factory
        self.embedder_factory = embedder_factory
        self.vector_store_factory = vector_store_factory
        self.config = config
    
    async def ingest(self, sources: list[DocumentSource]) -> IngestionResult:
        results = []
        for source in sources:
            try:
                result = await self._ingest_single(source)
                results.append(result)
            except Exception as e:
                results.append(IngestionResult.failed(source, e))
        return IngestionBatchResult(results=results)
    
    async def _ingest_single(self, source: DocumentSource) -> IngestionResult:
        # 1. Load
        loader = self.loader_factory.create(source.type, self.config.loader)
        documents = await loader.load(source)
        
        # 2. Preprocess
        documents = [self.preprocessing.process(doc) for doc in documents]
        
        # 3. Chunk
        chunker = self.chunker_factory.create(self.config.chunking.strategy, self.config.chunking)
        all_chunks = []
        for doc in documents:
            chunks = chunker.chunk(doc)
            all_chunks.extend(chunks)
        
        # 4. Embed
        embedder = self.embedder_factory.create(self.config.embeddings.provider, self.config.embeddings)
        chunks_with_embeddings = await embedder.embed_chunks(all_chunks)
        
        # 5. Store
        vector_store = self.vector_store_factory.create(self.config.vector_store.provider, self.config.vector_store)
        upsert_result = await vector_store.upsert(chunks_with_embeddings)
        
        return IngestionResult(
            source=source,
            documents=len(documents),
            chunks=len(chunks_with_embeddings),
            vectors_upserted=upsert_result.success_count,
            failed_chunks=upsert_result.failed_ids,
        )
```

### Configuration

```python
# backend/configs/settings.py (excerpt)
class IngestionConfig(BaseModel):
    loader: LoaderConfig = LoaderConfig()
    preprocessing: PreprocessingConfig = PreprocessingConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    embeddings: EmbeddingConfig = EmbeddingConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    batch_size: int = 32
    max_concurrency: int = 4
    checkpoint_interval: int = 100
    skip_failed: bool = True
```

### Error Handling

| Stage | Error Type | Recovery |
|-------|------------|----------|
| Loader | `LoaderError` | Skip document, continue batch |
| Preprocessing | `PreprocessingError` | Skip document, log warning |
| Chunking | `ChunkingError` | Fallback to recursive, log |
| Embedding | `EmbeddingError` | Retry with backoff, circuit break |
| Vector Store | `VectorStoreError` | Retry, then fail batch |

### Monitoring

```python
# Metrics emitted per document
ingestion_documents_total{status="success|failed"}
ingestion_chunks_created_total
ingestion_embedding_latency_seconds{provider}
ingestion_upsert_latency_seconds{store}
ingestion_batch_duration_seconds
```

---

## Query Pipeline Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     QUERY PIPELINE                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Query      │───▶│  Query Expander │───▶│  Retriever   │───▶│  Reranker    │      │
│  │  Validator   │    │   Factory       │    │   Factory    │    │   Factory    │      │
│  └──────────────┘    └─────────────────┘    └──────┬───────┘    └──────┬───────┘      │
│                                                     │                   │               │
│                                                     ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              GENERATOR FACTORY                                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │   │
│  │  │ OpenAI  │  │Anthropic│  │ Ollama  │  │  vLLM   │  │   TGI   │               │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Interfaces

#### Query Expander Factory
```python
# backend/data/retrieval/query_expansion/factory.py
class QueryExpanderFactory:
    @classmethod
    def create(cls, config: QueryExpansionConfig) -> QueryExpander:
        expanders = []
        if config.rewrite_enabled:
            expanders.append(LLMQueryRewriter(config.rewrite))
        if config.decompose_enabled:
            expanders.append(QueryDecomposer(config.decompose))
        if config.hyde_enabled:
            expanders.append(HyDEExpander(config.hyde))
        return CompositeQueryExpander(expanders)
```

#### Retriever Factory
```python
# backend/data/retrieval/factory.py
class RetrieverFactory:
    @classmethod
    def create(cls, config: RetrievalConfig, vector_store: VectorStore, embedder: EmbeddingProvider) -> Retriever:
        retrievers = []
        
        if config.dense_enabled:
            retrievers.append(DenseRetriever(vector_store, embedder, config.dense))
        
        if config.sparse_enabled:
            retrievers.append(SparseRetriever(vector_store, config.sparse))
        
        if len(retrievers) == 1:
            return retrievers[0]
        
        return HybridRetriever(retrievers, config.hybrid)
```

#### Reranker Factory
```python
# backend/data/reranking/factory.py
class RerankerFactory:
    @classmethod
    def create(cls, config: RerankConfig) -> Reranker:
        if config.provider == RerankerProvider.COHERE:
            return CohereReranker(config)
        elif config.provider == RerankerProvider.JINA:
            return JinaReranker(config)
        elif config.provider == RerankerProvider.CROSS_ENCODER:
            return CrossEncoderReranker(config)
        elif config.provider == RerankerProvider.BGE_RERANKER:
            return BGEReranker(config)
        raise RerankError(f"Unknown reranker: {config.provider}")
```

#### Generator Factory
```python
# backend/data/generation/factory.py
class GeneratorFactory:
    @classmethod
    def create(cls, config: GenerationConfig) -> Generator:
        if config.provider == LLMProvider.OPENAI:
            return OpenAIGenerator(config)
        elif config.provider == LLMProvider.ANTHROPIC:
            return AnthropicGenerator(config)
        elif config.provider == LLMProvider.OLLAMA:
            return OllamaGenerator(config)
        elif config.provider == LLMProvider.VLLM:
            return VLLMGenerator(config)
        elif config.provider == LLMProvider.TGI:
            return TGIGenerator(config)
        raise GenerationError(f"Unknown provider: {config.provider}")
```

### Pipeline Orchestration

```python
# backend/data/query/orchestrator.py
class QueryPipeline:
    def __init__(
        self,
        query_expander: QueryExpander,
        retriever: Retriever,
        reranker: Optional[Reranker],
        generator: Generator,
        citation_extractor: CitationExtractor,
        config: QueryConfig,
    ):
        self.query_expander = query_expander
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.citation_extractor = citation_extractor
        self.config = config
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        correlation_id = request.correlation_id or uuid4()
        start_time = time.time()
        
        # 1. Validate & Expand
        expanded = await self.query_expander.expand(request.query, request.filters)
        
        # 2. Retrieve
        retrieval_start = time.time()
        results = await self.retriever.retrieve(expanded)
        retrieval_latency = time.time() - retrieval_start
        
        # 3. Rerank (optional)
        rerank_latency = 0
        if self.reranker and results:
            rerank_start = time.time()
            results = await self.reranker.rerank(request.query, results, self.config.rerank_top_n)
            rerank_latency = time.time() - rerank_start
        
        # 4. Generate
        generation_start = time.time()
        generation_result = await self.generator.generate(request.query, results)
        generation_latency = time.time() - generation_start
        
        # 5. Extract citations
        citations = self.citation_extractor.extract(
            generation_result.answer, 
            results
        )
        
        # 6. Assemble response
        return QueryResponse(
            answer=generation_result.answer,
            citations=citations,
            retrieval_metadata=RetrievalMetadata(
                total_candidates=len(results),
                retrieval_latency_ms=int(retrieval_latency * 1000),
                rerank_latency_ms=int(rerank_latency * 1000),
                methods_used=[r.retrieval_method for r in results[:5]],
            ),
            generation_metadata=GenerationMetadata(
                model=generation_result.metadata.model,
                prompt_tokens=generation_result.metadata.prompt_tokens,
                completion_tokens=generation_result.metadata.completion_tokens,
                latency_ms=int(generation_latency * 1000),
            ),
            query_metadata=QueryMetadata(
                expanded_queries=expanded.sub_queries,
                hyde_used=expanded.hypothetical_doc_embeddings is not None,
            ),
            correlation_id=correlation_id,
            timestamp=datetime.utcnow(),
        )
```

### Configuration

```python
class QueryConfig(BaseModel):
    expansion: QueryExpansionConfig = QueryExpansionConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    rerank: RerankConfig = RerankConfig()
    generation: GenerationConfig = GenerationConfig()
    citation: CitationConfig = CitationConfig()
    timeout_seconds: float = 30.0
    max_context_tokens: int = 8192
```

### Circuit Breakers

```python
# Applied per external dependency
class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    expected_exception: type[Exception] = Exception

# Usage in pipeline
@circuit_breaker(config=embedding_circuit_breaker)
async def embed_query(self, query: str) -> Vector:
    ...

@circuit_breaker(config=llm_circuit_breaker)
async def generate(self, prompt: str) -> GenerationResult:
    ...
```

### Monitoring

```python
# Per-request metrics
query_latency_seconds{stage="expansion|retrieval|rerank|generation|total"}
query_retrieval_candidates{method="dense|sparse|hybrid"}
query_rerank_input_count
query_generation_tokens{prompt|completion|total}
query_citation_coverage
query_errors_total{stage,error_type}
```

---

## Evaluation Pipeline Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    EVALUATION PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Dataset    │───▶│  Query Pipeline │───▶│  Metrics        │───▶│  Experiment     │  │
│  │  Loader     │    │  (Batch Mode)   │    │  Computer       │    │  Tracker        │  │
│  └─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│        │                                       │                                       │  │
│        ▼                                       ▼                                       ▼  │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           METRICS REGISTRY                                       │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │   │
│  │  │ Faithful-  │ │ Answer     │ │ Context    │ │ Context    │ │ Custom     │    │   │
│  │  │ ness       │ │ Relevancy  │ │ Precision  │ │ Recall     │ │ Metrics    │    │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Interfaces

#### Dataset Loader
```python
# backend/data/evaluation/datasets/loader.py
class EvaluationDatasetLoader(Protocol):
    def load(self, path: str) -> EvaluationDataset: ...

class EvaluationDataset(BaseModel):
    name: str
    version: str
    samples: list[EvaluationSample]
    metadata: dict

class EvaluationSample(BaseModel):
    id: str
    query: str
    expected_answer: Optional[str] = None
    expected_chunks: Optional[list[str]] = None  # chunk IDs
    metadata: dict = Field(default_factory=dict)
```

#### Metrics Computer
```python
# backend/data/evaluation/metrics/computer.py
class MetricsComputer:
    def __init__(self, metrics: list[Metric], evaluator: Evaluator):
        self.metrics = metrics
        self.evaluator = evaluator  # RAGAS, DeepEval, or custom
    
    async def compute(
        self, 
        samples: list[EvaluationSample], 
        predictions: list[QueryResponse]
    ) -> EvaluationResult:
        results = {}
        for metric in self.metrics:
            results[metric.name] = await metric.compute(samples, predictions)
        return EvaluationResult(
            dataset_name=samples[0].dataset_name if samples else "unknown",
            metrics=results,
            sample_count=len(samples),
            timestamp=datetime.utcnow(),
        )
```

#### Metric Interface
```python
# backend/data/evaluation/metrics/base.py
class Metric(Protocol):
    name: str
    
    async def compute(
        self, 
        samples: list[EvaluationSample], 
        predictions: list[QueryResponse]
    ) -> MetricResult: ...

class MetricResult(BaseModel):
    name: str
    value: float
    details: dict = Field(default_factory=dict)
    per_sample: Optional[list[float]] = None
```

### Built-in Metrics

| Metric | Source | Description |
|--------|--------|-------------|
| `faithfulness` | RAGAS | Answer grounded in context |
| `answer_relevancy` | RAGAS | Answer addresses query |
| `context_precision` | RAGAS | Relevant chunks ranked high |
| `context_recall` | RAGAS | All relevant chunks retrieved |
| `context_relevancy` | RAGAS | Chunks relevant to query |
| `answer_correctness` | RAGAS | Semantic match to expected |
| `hallucination_rate` | Custom | Unsupported claims in answer |
| `citation_accuracy` | Custom | Citations match sources |
| `latency_p50/p95/p99` | System | End-to-end latency |

### Pipeline Orchestration

```python
# backend/data/evaluation/orchestrator.py
class EvaluationPipeline:
    def __init__(
        self,
        dataset_loader: EvaluationDatasetLoader,
        query_pipeline: QueryPipeline,
        metrics_computer: MetricsComputer,
        experiment_tracker: ExperimentTracker,
        config: EvaluationConfig,
    ):
        self.dataset_loader = dataset_loader
        self.query_pipeline = query_pipeline
        self.metrics_computer = metrics_computer
        self.experiment_tracker = experiment_tracker
        self.config = config
    
    async def evaluate(self, dataset_path: str) -> EvaluationResult:
        # 1. Load dataset
        dataset = self.dataset_loader.load(dataset_path)
        
        # 2. Run queries (batch with concurrency control)
        predictions = await self._run_batch_queries(dataset.samples)
        
        # 3. Compute metrics
        result = await self.metrics_computer.compute(dataset.samples, predictions)
        
        # 4. Track experiment
        if self.config.track_experiment:
            self._log_to_experiment_tracker(dataset, predictions, result)
        
        return result
    
    async def _run_batch_queries(self, samples: list[EvaluationSample]) -> list[QueryResponse]:
        semaphore = asyncio.Semaphore(self.config.batch_concurrency)
        
        async def run_one(sample: EvaluationSample) -> QueryResponse:
            async with semaphore:
                request = QueryRequest(query=sample.query)
                return await self.query_pipeline.query(request)
        
        return await asyncio.gather(*[run_one(s) for s in samples])
```

### Configuration

```python
class EvaluationConfig(BaseModel):
    dataset_path: str
    metrics: list[str] = Field(default=["faithfulness", "answer_relevancy", "context_precision", "context_recall"])
    batch_concurrency: int = 10
    sample_limit: Optional[int] = None
    track_experiment: bool = True
    experiment_name: str = "evaluation"
    save_predictions: bool = True
    output_dir: str = "evaluation_results"
```

---

## Experiment Tracking Pipeline Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                  EXPERIMENT TRACKING                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Config     │───▶│  Pipeline Run   │───▶│  Metrics &      │───▶│  Tracker        │  │
│  │  Snapshot   │    │  (Ingestion/    │    │  Artifacts      │    │  (MLflow/W&B)   │  │
│  │             │    │   Query/Eval)   │    │                 │    │                 │  │
│  └─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tracked Entities

#### Experiment
```python
class Experiment(BaseModel):
    name: str
    tags: dict[str, str] = Field(default_factory=dict)
    config: dict  # Full pipeline config snapshot
    git_commit: Optional[str] = None
    git_dirty: bool = False
    created_at: datetime
```

#### Run
```python
class Run(BaseModel):
    experiment_name: str
    run_id: str
    name: Optional[str] = None
    status: RunStatus = RunStatus.RUNNING
    params: dict = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None
```

#### Artifact
```python
class Artifact(BaseModel):
    name: str
    path: str
    type: ArtifactType  # MODEL, DATASET, REPORT, LOG, PREDICTIONS
    metadata: dict = Field(default_factory=dict)
```

### Tracker Interface

```python
# backend/data/experiments/tracker.py
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

### Implementations

#### MLflow Tracker
```python
class MLflowTracker:
    def __init__(self, tracking_uri: str, artifact_root: str):
        mlflow.set_tracking_uri(tracking_uri)
        self.artifact_root = artifact_root
    
    def start_run(self, experiment_id: str, run_name: str, config: dict) -> Run:
        mlflow.set_experiment(experiment_id)
        run = mlflow.start_run(run_name=run_name)
        mlflow.log_params(flatten_dict(config))
        return Run(run_id=run.info.run_id, ...)
```

#### W&B Tracker
```python
class WandbTracker:
    def __init__(self, project: str, entity: Optional[str]):
        wandb.init(project=project, entity=entity)
    
    def start_run(self, experiment_id: str, run_name: str, config: dict) -> Run:
        run = wandb.init(
            project=experiment_id,
            name=run_name,
            config=config,
            reinit=True,
        )
        return Run(run_id=run.id, ...)
```

### Pipeline Integration

```python
# Automatic tracking via context manager
class TrackedPipeline:
    def __init__(self, tracker: ExperimentTracker, experiment_name: str):
        self.tracker = tracker
        self.experiment_name = experiment_name
        self.current_run: Optional[Run] = None
    
    @asynccontextmanager
    async def run(self, run_name: str, config: dict):
        experiment_id = self.tracker.create_experiment(self.experiment_name, {})
        run = self.tracker.start_run(experiment_id, run_name, config)
        self.current_run = run
        try:
            yield run
            self.tracker.end_run(run.run_id, RunStatus.COMPLETED)
        except Exception as e:
            self.tracker.end_run(run.run_id, RunStatus.FAILED)
            raise
    
    def log_metrics(self, metrics: dict, step: Optional[int] = None):
        if self.current_run:
            self.tracker.log_metrics(self.current_run.run_id, metrics, step)
    
    def log_artifact(self, path: str, name: Optional[str] = None):
        if self.current_run:
            self.tracker.log_artifact(self.current_run.run_id, path, name)
```

---

## Pipeline Extension Points

### Adding a New Loader
1. Implement `DocumentLoader` protocol in `backend/data/loaders/<name>.py`
2. Register in `backend/data/loaders/factory.py`
3. Add config in `backend/configs/settings.py`
4. Add tests in `backend/tests/unit/test_data/test_loaders/`

### Adding a New Chunking Strategy
1. Implement `Chunker` protocol in `backend/data/chunking/<name>.py`
2. Add to `ChunkingStrategy` enum
3. Register in `backend/data/chunking/factory.py`
4. Add config options

### Adding a New Embedding Provider
1. Implement `EmbeddingProvider` protocol in `backend/data/embeddings/<name>.py`
2. Add to `EmbeddingProvider` enum
3. Register in `backend/data/embeddings/factory.py`
4. Add API key/config to settings

### Adding a New Vector Store
1. Implement `VectorStore` protocol in `backend/data/vectorstore/<name>.py`
2. Add to `VectorStoreProvider` enum
3. Register in `backend/data/vectorstore/factory.py`
4. Add connection config to settings

### Adding a New Retrieval Method
1. Implement `Retriever` protocol in `backend/data/retrieval/<name>.py`
2. Register in `backend/data/retrieval/factory.py`
3. Add to `RetrievalMethod` enum
4. Add config for fusion weights

### Adding a New Reranker
1. Implement `Reranker` protocol in `backend/data/reranking/<name>.py`
2. Add to `RerankerProvider` enum
3. Register in `backend/data/reranking/factory.py`

### Adding a New Generator
1. Implement `Generator` protocol in `backend/data/generation/<name>.py`
2. Add to `LLMProvider` enum
3. Register in `backend/data/generation/factory.py`

### Adding a New Metric
1. Implement `Metric` protocol in `backend/data/evaluation/metrics/<name>.py`
2. Register in `backend/data/evaluation/metrics/registry.py`
3. Add to available metrics list in config

### Adding a New Experiment Tracker
1. Implement `ExperimentTracker` protocol in `backend/data/experiments/<name>.py`
2. Register in `backend/data/experiments/factory.py`
3. Add config to `ExperimentSettings`