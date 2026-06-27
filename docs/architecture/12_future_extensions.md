# Future Extensions

## Overview

This document outlines planned and potential future extensions for the Retrieval Intelligence Platform. These extensions are organized by priority and complexity, with clear integration points in the existing architecture.

---

## Extension Categories

| Category | Priority | Complexity | Timeline |
|----------|----------|------------|----------|
| **Core RAG Enhancements** | High | Medium | Q3 2026 |
| **Multi-Modal Support** | High | High | Q4 2026 |
| **Advanced Retrieval** | High | Medium | Q3 2026 |
| **Enterprise Features** | Medium | High | Q1 2027 |
| **MLOps & Automation** | Medium | Medium | Q4 2026 |
| **Developer Experience** | Low | Low | Ongoing |

---

## 1. Core RAG Enhancements

### 1.1 OCR & Document Intelligence

**Purpose**: Extract text from scanned documents, images, and complex layouts.

**Integration Point**: `backend/data/loaders/` - New loader implementations

```python
# New loaders to add
class OCRPDFLoader(DocumentLoader):
    """PDF loader with OCR fallback for scanned pages."""
    def __init__(self, config: OCRConfig):
        self.ocr_engine = OCREngine(config.engine)  # Tesseract, PaddleOCR, Azure
    
    async def load(self, source: DocumentSource) -> list[Document]:
        # Try standard extraction first
        docs = await standard_pdf_load(source)
        
        # Detect scanned pages (low text density)
        for doc in docs:
            if self._is_scanned(doc):
                ocr_text = await self.ocr_engine.process(doc.content)
                doc.content = ocr_text
                doc.metadata.ocr_applied = True
        
        return docs

class ImageLoader(DocumentLoader):
    """Load text from images (PNG, JPG, TIFF)."""
    
class TableExtractor(DocumentLoader):
    """Extract structured tables as separate documents."""
```

**Configuration**:
```python
class OCRConfig(BaseModel):
    engine: OCREngine = OCREngine.PADDLE_OCR  # TESSERACT, PADDLE_OCR, AZURE, AWS
    languages: list[str] = ["en"]
    dpi: int = 300
    detect_orientation: bool = True
    extract_tables: bool = True
    table_format: TableFormat = TableFormat.MARKDOWN  # MARKDOWN, CSV, JSON
```

**Dependencies**: `paddleocr`, `tesseract`, `pdf2image`, `opencv-python`

---

### 1.2 Multi-Vector Retrieval (ColBERT, SPLADE)

**Purpose**: Late interaction models for fine-grained relevance scoring.

**Integration Point**: `backend/data/retrieval/multi_vector.py`, `backend/data/vectorstore/`

```python
# New retriever
class ColBERTRetriever(Retriever):
    """ColBERT-style late interaction retrieval."""
    
    def __init__(self, config: ColBERTConfig, vector_store: VectorStore):
        self.model = ColBERTModel(config.model_name)
        self.vector_store = vector_store  # Must support multi-vector
    
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]:
        # Encode query into token-level vectors
        query_vectors = self.model.encode_query(query.original_query)
        
        # Search using MaxSim or similar
        results = await self.vector_store.maxsim_search(
            query_vectors=query_vectors,
            top_k=config.top_k
        )
        
        return results

# Vector store extension
class MultiVectorStore(VectorStore):
    """Vector store supporting multiple vectors per document."""
    
    async def upsert_multi_vector(self, chunks: list[MultiVectorChunk]) -> UpsertResult:
        # Store token-level embeddings
        ...
    
    async def maxsim_search(self, query_vectors: list[Vector], top_k: int) -> list[Chunk]:
        # Late interaction scoring
        ...
```

**Supported Stores**: LanceDB, Vespa, custom FAISS with inverted index

---

### 1.3 Hybrid Search Enhancements

**Purpose**: Advanced fusion methods and learned sparse retrieval.

```python
# Learned sparse retrieval (SPLADE)
class SPLADERetriever(Retriever):
    """SPLADE - Learned sparse representations."""
    
    def __init__(self, config: SPLADEConfig):
        self.model = SpladeModel(config.model_name)
    
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]:
        # Encode query as sparse vector
        sparse_query = self.model.encode_query(query.original_query)
        
        # Search sparse index
        results = await self.sparse_index.search(sparse_query, top_k=config.top_k)
        return results

# Advanced fusion
class LearnedFusionRetriever(Retriever):
    """Learn optimal fusion weights from relevance judgments."""
    
    def __init__(self, config: LearnedFusionConfig):
        self.fusion_model = FusionModel.load(config.model_path)
    
    def fuse(self, dense_results, sparse_results, multi_vector_results) -> list[RetrievalResult]:
        # Use learned model to combine scores
        features = self._extract_features(dense_results, sparse_results, multi_vector_results)
        weights = self.fusion_model.predict(features)
        return self._apply_weights(dense_results, sparse_results, multi_vector_results, weights)
```

---

### 1.4 Multiple Embedding Models

**Purpose**: Ensemble embeddings, task-specific models, fallback chains.

```python
# Ensemble embedder
class EnsembleEmbedder(EmbeddingProvider):
    """Combine multiple embedding providers."""
    
    def __init__(self, providers: list[EmbeddingProvider], weights: list[float]):
        self.providers = providers
        self.weights = weights
    
    async def embed_documents(self, texts: list[str]) -> list[Vector]:
        all_embeddings = await asyncio.gather(*[p.embed_documents(texts) for p in self.providers])
        
        # Weighted concatenation or averaging
        if self.config.strategy == "concat":
            return [np.concatenate([e[i] * w for e, w in zip(all_embeddings, self.weights)]) for i in range(len(texts))]
        elif self.config.strategy == "average":
            return [np.average([e[i] for e in all_embeddings], axis=0, weights=self.weights) for i in range(len(texts))]

# Task-specific routing
class RoutedEmbedder(EmbeddingProvider):
    """Route to different models based on content type."""
    
    def __init__(self, routers: dict[str, EmbeddingProvider], classifier: ContentClassifier):
        self.routers = routers
        self.classifier = classifier
    
    async def embed_documents(self, texts: list[str]) -> list[Vector]:
        # Classify each text
        categories = self.classifier.classify(texts)
        
        # Route to appropriate embedder
        results = []
        for text, category in zip(texts, categories):
            embedder = self.routers.get(category, self.routers["default"])
            results.append(await embedder.embed_documents([text])[0])
        return results
```

**Configuration**:
```python
class EmbeddingEnsembleConfig(BaseModel):
    strategy: EnsembleStrategy = EnsembleStrategy.CONCAT  # CONCAT, AVERAGE, MAX
    providers: list[EmbeddingProviderConfig] = []
    weights: list[float] = []

class RoutedEmbeddingConfig(BaseModel):
    default_provider: EmbeddingProviderConfig
    routes: dict[str, EmbeddingProviderConfig] = {}  # category -> provider
```

---

### 1.5 Query Understanding & Intent Classification

**Purpose**: Route queries to specialized pipelines based on intent.

```python
class QueryClassifier:
    """Classify query intent for pipeline routing."""
    
    INTENTS = [
        "factoid",           # "What is X?"
        "comparison",        # "Compare X and Y"
        "multi_hop",         # "Who is the CEO of the company that acquired X?"
        "summarization",     # "Summarize the Q3 report"
        "extraction",        # "Extract all dates from the contract"
        "reasoning",         # "Why did revenue decrease?"
        "creative",          # "Write a blog post about..."
        "code_generation",   # "Write a Python function..."
    ]
    
    async def classify(self, query: str) -> QueryIntent:
        # Use lightweight classifier or LLM
        ...
    
    def route_pipeline(self, intent: QueryIntent) -> PipelineConfig:
        routing = {
            "factoid": PipelineConfig(retrieval_top_k=5, rerank=True),
            "multi_hop": PipelineConfig(retrieval_top_k=20, query_decompose=True),
            "summarization": PipelineConfig(retrieval_top_k=10, generation_max_tokens=4096),
            "code_generation": PipelineConfig(generation_model="codellama"),
        }
        return routing.get(intent, PipelineConfig())
```

---

## 2. Multi-Modal Support

### 2.1 Image Retrieval & Generation

```python
# Multi-modal document
class MultiModalDocument(Document):
    images: list[ImageContent] = Field(default_factory=list)
    tables: list[TableContent] = Field(default_factory=list)
    charts: list[ChartContent] = Field(default_factory=list)

class ImageContent(BaseModel):
    image_id: UUID
    caption: Optional[str] = None
    embedding: Optional[Vector] = None  # CLIP embedding
    bbox: Optional[BoundingBox] = None  # Position in document
    page: int

# Multi-modal retriever
class MultiModalRetriever(Retriever):
    """Retrieve text and images jointly."""
    
    def __init__(self, text_store: VectorStore, image_store: VectorStore, clip_model: CLIPModel):
        self.text_store = text_store
        self.image_store = image_store
        self.clip = clip_model
    
    async def retrieve(self, query: ExpandedQuery) -> MultiModalRetrievalResult:
        # Text search
        text_results = await self.text_store.search(query.query_vector, top_k=20)
        
        # Image search (embed query with CLIP text encoder)
        query_image_emb = self.clip.encode_text(query.original_query)
        image_results = await self.image_store.search(query_image_emb, top_k=10)
        
        return MultiModalRetrievalResult(
            text_results=text_results,
            image_results=image_results
        )
```

### 2.2 Vision-Language Generation

```python
class MultiModalGenerator(Generator):
    """Generate answers with image references."""
    
    async def generate(self, query: str, context: MultiModalRetrievalResult) -> GenerationResult:
        # Build prompt with image placeholders
        prompt = self.build_multimodal_prompt(query, context)
        
        # Call vision-language model (GPT-4V, LLaVA, etc.)
        response = await self.vlm_client.generate(
            prompt=prompt,
            images=[img.data for img in context.image_results]
        )
        
        return self.parse_multimodal_response(response, context)
```

---

## 3. Advanced Retrieval

### 3.1 Knowledge Graph Integration

```python
class GraphRAGRetriever(Retriever):
    """Combine vector search with knowledge graph traversal."""
    
    def __init__(self, vector_store: VectorStore, graph_store: GraphStore, config: GraphRAGConfig):
        self.vector_store = vector_store
        self.graph = graph_store
    
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]:
        # 1. Vector search for seed entities
        seeds = await self.vector_store.search(query.query_vector, top_k=5)
        
        # 2. Graph traversal from seeds
        expanded = await self.graph.traverse(
            start_nodes=[s.chunk.metadata.entity_ids for s in seeds],
            max_hops=config.max_hops,
            relation_types=config.relation_types
        )
        
        # 3. Fetch chunks for expanded entities
        entity_chunks = await self.vector_store.get_by_entities(expanded)
        
        # 4. Merge and rerank
        return self._merge_and_rank(seeds, entity_chunks)
```

### 3.2 Recursive Retrieval / Agentic RAG

```python
class AgenticRetriever(Retriever):
    """Multi-step retrieval with reasoning."""
    
    def __init__(self, base_retriever: Retriever, planner: QueryPlanner, max_steps: int = 3):
        self.base = base_retriever
        self.planner = planner
        self.max_steps = max_steps
    
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]:
        all_results = []
        current_query = query.original_query
        
        for step in range(self.max_steps):
            # Plan next action
            plan = await self.planner.plan(current_query, all_results)
            
            if plan.action == "search":
                results = await self.base.retrieve(ExpandedQuery(original_query=plan.sub_query))
                all_results.extend(results)
            
            elif plan.action == "answer":
                break
            
            current_query = plan.next_query
        
        return self._deduplicate_and_rank(all_results)
```

### 3.3 Temporal & Versioned Retrieval

```python
class TemporalRetriever(Retriever):
    """Retrieve with time-awareness."""
    
    async def retrieve(self, query: ExpandedQuery) -> list[RetrievalResult]:
        # Extract time intent from query
        time_filter = self._extract_time_filter(query.original_query)
        
        # Apply temporal boost
        results = await self.base.retrieve(query)
        
        for result in results:
            doc_time = result.chunk.metadata.document_created_at
            result.score *= self._temporal_decay(doc_time, time_filter)
        
        return sorted(results, key=lambda r: r.score, reverse=True)
```

---

## 4. Enterprise Features

### 4.1 Multi-Tenancy & Access Control

```python
# Tenant-aware models
class TenantDocument(Document):
    tenant_id: str
    access_control: AccessControl

class AccessControl(BaseModel):
    owner: str
    readers: list[str] = Field(default_factory=list)
    writers: list[str] = Field(default_factory=list)
    public: bool = False

# Tenant isolation in vector store
class TenantVectorStore(VectorStore):
    """Vector store with tenant isolation."""
    
    def __init__(self, base_store: VectorStore):
        self.base = base_store
    
    def _tenant_filter(self, tenant_id: str) -> MetadataFilter:
        return MetadataFilter(custom={"tenant_id": tenant_id})
    
    async def search(self, query: Vector, top_k: int, filter: MetadataFilter) -> list[Chunk]:
        # Enforce tenant filter
        tenant_filter = self._tenant_filter(get_current_tenant())
        combined = filter.combine(tenant_filter) if filter else tenant_filter
        return await self.base.search(query, top_k, combined)
```

### 4.2 Row-Level Security & Data Governance

```python
class DataGovernanceLayer:
    """Enforce data policies at query time."""
    
    def __init__(self, policies: list[DataPolicy]):
        self.policies = policies
    
    def apply(self, request: QueryRequest, user: UserContext) -> QueryRequest:
        # Apply sensitivity filters
        for policy in self.policies:
            if policy.applies_to(user, request):
                request = policy.enforce(request, user)
        return request

class DataPolicy:
    def applies_to(self, user: UserContext, request: QueryRequest) -> bool:
        ...
    
    def enforce(self, request: QueryRequest, user: UserContext) -> QueryRequest:
        # Add sensitivity filter, redact results, etc.
        ...
```

### 4.3 Audit Logging & Compliance

```python
class AuditLogger:
    """Comprehensive audit trail for all operations."""
    
    async def log_query(self, event: QueryAuditEvent):
        # Immutable log entry
        await self.store.append(AuditEntry(
            timestamp=datetime.utcnow(),
            user_id=event.user_id,
            action="query",
            query_hash=hash_query(event.query),
            filters=event.filters,
            results_count=event.results_count,
            latency_ms=event.latency_ms,
            ip_address=event.ip_address,
            user_agent=event.user_agent
        ))
    
    async def log_ingestion(self, event: IngestionAuditEvent):
        ...
    
    async def log_export(self, event: ExportAuditEvent):
        ...
```

---

## 5. MLOps & Automation

### 5.1 Automated Retraining Pipeline

```python
class RetrainingPipeline:
    """Automatically retrain embedding/reranker models on new data."""
    
    def __init__(self, config: RetrainingConfig):
        self.config = config
        self.trigger = RetrainingTrigger(config.trigger)
    
    async def check_and_retrain(self):
        if await self.trigger.should_retrain():
            # 1. Collect new training data
            train_data = await self._collect_training_data()
            
            # 2. Train new model
            new_model = await self._train_model(train_data)
            
            # 3. Evaluate against current
            eval_result = await self._evaluate(new_model)
            
            # 4. Deploy if better
            if eval_result.improvement > self.config.min_improvement:
                await self._deploy_model(new_model)
```

### 5.2 Continuous Evaluation

```python
class ContinuousEvaluator:
    """Run evaluations on schedule or trigger."""
    
    def __init__(self, config: ContinuousEvalConfig):
        self.scheduler = AsyncScheduler()
        self.evaluation_runner = EvaluationRunner(...)
    
    def schedule(self):
        # Daily full evaluation
        self.scheduler.every().day.at("02:00").do(self.run_full_evaluation)
        
        # Hourly smoke test
        self.scheduler.every().hour.do(self.run_smoke_test)
        
        # On deployment
        self.scheduler.on_event("deployment").do(self.run_regression_test)
```

### 5.3 Model Registry & Versioning

```python
class ModelRegistry:
    """Central registry for all ML models."""
    
    def register(
        self,
        model_type: ModelType,
        model: Any,
        metadata: ModelMetadata
    ) -> ModelVersion:
        version = self._generate_version(model_type)
        
        # Store model artifact
        artifact_path = self.store.save(model, version)
        
        # Record metadata
        self.db.insert(ModelRecord(
            model_type=model_type,
            version=version,
            artifact_path=artifact_path,
            metadata=metadata,
            registered_at=datetime.utcnow()
        ))
        
        return ModelVersion(model_type=model_type, version=version)
    
    def promote(self, model_type: ModelType, version: str, stage: ModelStage):
        """Promote model to staging/production."""
        ...
```

---

## 6. Developer Experience

### 6.1 SDK & Client Libraries

```python
# Python SDK
class RIPClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
    
    async def ingest(self, files: list[Path], **kwargs) -> IngestionResult:
        ...
    
    async def query(self, question: str, **kwargs) -> QueryResponse:
        ...
    
    async def evaluate(self, dataset: str, **kwargs) -> EvaluationResult:
        ...

# TypeScript SDK (for Next.js frontend)
class RIPClient {
    constructor(baseUrl: string, apiKey: string) { ... }
    
    async query(question: string, options?: QueryOptions): Promise<QueryResponse> { ... }
    async *streamQuery(question: string, options?: QueryOptions): AsyncIterator<StreamEvent> { ... }
}
```

### 6.2 CLI Enhancements

```bash
# Rich CLI with subcommands
rip ingest ./docs --recursive --watch
rip query "What is revenue?" --stream --citations
rip evaluate ./eval_data --metrics faithfulness,relevancy --compare baseline
rip experiment list --filter "metric.faithfulness > 0.8"
rip experiment diff run_123 run_456
rip deploy --env staging --config production.yaml
```

### 6.3 Visual Debugging Tools

```python
# Retrieval visualizer
class RetrievalVisualizer:
    def visualize(self, query: str, results: list[RetrievalResult]) -> Visualization:
        return Visualization(
            query=query,
            score_distribution=plot_scores(results),
            method_contribution=plot_method_mix(results),
            chunk_positions=plot_document_positions(results),
            rerank_changes=plot_rerank_delta(results)
        )

# Prompt debugger
class PromptDebugger:
    def debug(self, prompt: str, response: str) -> PromptAnalysis:
        return PromptAnalysis(
            token_breakdown=analyze_tokens(prompt),
            attention_viz=get_attention(response) if available else None,
            citation_map=map_citations(response),
            grounding_check=check_grounding(response, context)
        )
```

---

## 7. Cloud & Scale

### 7.1 Cloud Vector Database Integrations

| Provider | Status | Features |
|----------|--------|----------|
| Pinecone | Planned | Serverless, hybrid search, namespaces |
| Weaviate | Planned | GraphQL, multi-modal, generative search |
| Qdrant | Planned | Payload filtering, quantization, replication |
| Milvus | Planned | Distributed, GPU acceleration, multi-tenancy |
| Elasticsearch | Planned | Hybrid search, BM25, semantic search |
| OpenSearch | Planned | k-NN, neural search, security |

### 7.2 Kubernetes-Native Deployment

```yaml
# K8s resources
apiVersion: v1
kind: ConfigMap
metadata:
  name: rip-config
data:
  settings.yaml: |
    # Injected from secrets/ConfigMaps
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rip-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: rip/api:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rip-worker
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: worker
        image: rip/worker:latest
        resources:
          requests:
            nvidia.com/gpu: 1
            memory: "8Gi"
```

### 7.3 Auto-Scaling Policies

```python
class AutoScaler:
    """KEDA-compatible scaling triggers."""
    
    TRIGGERS = {
        "api": [
            {"type": "cpu", "threshold": 70},
            {"type": "memory", "threshold": 80},
            {"type": "http_requests", "threshold": 100},  # per pod
        ],
        "worker": [
            {"type": "queue_length", "threshold": 10},  # per worker
            {"type": "gpu_utilization", "threshold": 80},
        ],
        "embedding": [
            {"type": "batch_queue_depth", "threshold": 50},
        ]
    }
```

---

## 8. Advanced Evaluation

### 8.1 LLM-as-a-Judge Enhancements

```python
class LLMJudgeEnsemble:
    """Multiple LLM judges with consensus."""
    
    def __init__(self, judges: list[LLMJudge], aggregation: AggregationMethod):
        self.judges = judges
        self.aggregation = aggregation
    
    async def judge(self, premise: str, hypothesis: str) -> JudgeResult:
        results = await asyncio.gather(*[j.judge(premise, hypothesis) for j in self.judges])
        
        if self.aggregation == AggregationMethod.MAJORITY:
            return majority_vote(results)
        elif self.aggregation == AggregationMethod.WEIGHTED:
            return weighted_vote(results, self.weights)
        elif self.aggregation == AggregationMethod.UNANIMOUS:
            return unanimous_vote(results)
```

### 8.2 Human Feedback Integration

```python
class FeedbackCollector:
    """Collect and incorporate human feedback."""
    
    async def collect(self, feedback: HumanFeedback):
        # Store feedback
        await self.db.insert(FeedbackRecord(**feedback.model_dump()))
        
        # Update preference dataset
        await self.preference_dataset.add(feedback)
        
        # Trigger reward model update if enough feedback
        if len(self.preference_dataset) % self.config.update_threshold == 0:
            await self.reward_model_trainer.update()
```

### 8.3 Adversarial Evaluation

```python
class AdversarialEvaluator:
    """Generate adversarial queries to test robustness."""
    
    def generate_adversarial(self, base_queries: list[str]) -> list[AdversarialQuery]:
        attacks = [
            self._typo_injection,
            self._synonym_substitution,
            self._negation_insertion,
            self._distractor_addition,
            self._prompt_injection,
            self._context_switching,
        ]
        
        adversarial = []
        for query in base_queries:
            for attack in attacks:
                adversarial.append(attack(query))
        
        return adversarial
```

---

## 9. Integration Priorities

### Phase 1 (Q3 2026) - Core Enhancements
1. OCR support for scanned documents
2. Multiple embedding models with routing
3. Advanced hybrid fusion (learned weights)
4. Query intent classification
5. Basic multi-tenancy

### Phase 2 (Q4 2026) - Multi-Modal & Advanced Retrieval
1. Image retrieval with CLIP
2. Vision-language generation
3. ColBERT/SPLADE retrieval
3. GraphRAG integration
4. Agentic/recursive retrieval

### Phase 3 (Q1 2027) - Enterprise & MLOps
1. Full RBAC & data governance
2. Audit logging & compliance
3. Automated retraining pipeline
4. Model registry & versioning
5. Continuous evaluation

### Phase 4 (Q2 2027+) - Scale & Ecosystem
1. Cloud vector database integrations
2. Kubernetes-native deployment
3. SDKs (Python, TypeScript, Go)
4. Marketplace for components
5. Federated learning support

---

## Extension Integration Points

| Extension | Primary Module | Config Section | New Files |
|-----------|----------------|----------------|-----------|
| OCR | `loaders` | `loader.ocr` | `ocr.py`, `image.py` |
| Multi-vector | `retrieval`, `vectorstore` | `retrieval.multi_vector` | `colbert.py`, `splade.py` |
| Ensemble embeddings | `embeddings` | `embeddings.ensemble` | `ensemble.py`, `routed.py` |
| Multi-modal | `loaders`, `retrieval`, `generation` | `multimodal` | `clip.py`, `vlm.py` |
| GraphRAG | `retrieval` | `retrieval.graph` | `graphrag.py` |
| Multi-tenancy | `core`, `vectorstore`, `api` | `security.tenancy` | `tenant.py`, `rbac.py` |
| MLOps | `experiments`, new `mlops` | `mlops` | `retraining.py`, `registry.py` |

---

## Decision Framework for New Extensions

Before adding any extension, evaluate:

1. **User Value**: Does it solve a real user problem?
2. **Architectural Fit**: Does it follow existing patterns?
3. **Maintenance Burden**: Can we maintain it long-term?
4. **Dependency Risk**: Are new dependencies stable/secure?
5. **Performance Impact**: Does it slow the critical path?
6. **Configuration Complexity**: Is it configurable without code changes?
7. **Testing Strategy**: Can we test it thoroughly?
8. **Documentation**: Can we document it clearly?

**Approval Process**:
- RFC in `docs/adr/` for major extensions
- Prototype in `notebooks/prototyping/`
- Review by architecture team
- Merge behind feature flag
- Gradual rollout with monitoring