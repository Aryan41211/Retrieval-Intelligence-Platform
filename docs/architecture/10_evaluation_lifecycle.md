# Evaluation Lifecycle

## Overview

This document describes the complete lifecycle of the evaluation pipeline in the Retrieval Intelligence Platform, from dataset loading through metric computation, experiment tracking, and report generation.

---

## Evaluation Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         EVALUATION LIFECYCLE                                           │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌─────────────────────┐                                                                             │
│  │  Dataset Loading    │  Load evaluation dataset (RAGAS, custom, synthetic)                        │
│  └──────────┬──────────┘                                                                             │
│             │                                                                                         │
│             ▼                                                                                         │
│  ┌─────────────────────┐                                                                             │
│  │  Sample Selection   │  Filter, sample, limit dataset                                             │
│  └──────────┬──────────┘                                                                             │
│             │                                                                                         │
│             ▼                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              BATCH QUERY EXECUTION                                             │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐     │    │
│  │  │  For each sample (parallel with concurrency control):                              │     │    │
│  │  │    1. QueryPipeline.query(sample.query)                                            │     │    │
│  │  │    2. Collect QueryResponse                                                         │     │    │
│  │  │    3. Store prediction + metadata                                                   │     │    │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘    │
│             │                                                                                         │
│             ▼                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              METRICS COMPUTATION                                               │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │    │
│  │  │ Faithful-   │ │ Answer      │ │ Context     │ │ Context     │ │ Custom Metrics      │   │    │
│  │  │ ness        │ │ Relevancy   │ │ Precision   │ │ Recall      │ │ (Hallucination,     │   │    │
│  │  │ (RAGAS)     │ │ (RAGAS)     │ │ (RAGAS)     │ │ (RAGAS)     │ │  Citation, etc.)    │   │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │    │
│  │         │               │               │               │               │                    │    │
│  │         └───────────────┼───────────────┼───────────────┼───────────────┘                    │    │
│  │                         ▼               ▼               ▼                                    │    │
│  │              ┌─────────────────────────────────────────────────────────┐                    │    │
│  │              │              AGGREGATION & STATISTICS                   │                    │    │
│  │              │  Mean, Std, Min, Max, Percentiles, Pass/Fail rates    │                    │    │
│  │              └─────────────────────────────────────────────────────────┘                    │    │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘    │
│             │                                                                                         │
│             ▼                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              EXPERIMENT TRACKING                                              │    │
│  │  • Log config snapshot                                                                          │    │
│  │  • Log metrics (per-sample + aggregated)                                                       │    │
│  │  • Log artifacts (predictions, dataset, report)                                                │    │
│  │  • Link to git commit, environment                                                              │    │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘    │
│             │                                                                                         │
│             ▼                                                                                         │
│  ┌─────────────────────┐                                                                             │
│  │  Report Generation  │  HTML, JSON, Markdown reports                                              │
│  └─────────────────────┘                                                                             │
│                                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Dataset Loading

### Purpose
Load evaluation datasets from various formats into unified `EvaluationDataset`.

### Supported Formats

#### RAGAS Format
```json
{
  "name": "hotpotqa",
  "version": "1.0",
  "samples": [
    {
      "id": "sample_001",
      "query": "What is the capital of France?",
      "expected_answer": "Paris is the capital of France.",
      "expected_chunk_ids": ["chunk_123", "chunk_456"],
      "metadata": {"difficulty": "easy", "category": "geography"}
    }
  ]
}
```

#### Custom JSONL Format
```jsonl
{"id": "1", "query": "Who won the 2020 election?", "expected_answer": "Joe Biden", "ground_truth_chunks": ["c1", "c2"]}
{"id": "2", "query": "What is photosynthesis?", "expected_answer": "Process by which plants...", "ground_truth_chunks": ["c3"]}
```

#### Synthetic Dataset Generation
```python
class SyntheticDatasetGenerator:
    def generate(
        self,
        documents: list[Document],
        num_samples: int = 100,
        question_types: list[QuestionType] = [FACTOID, COMPARISON, MULTI_HOP]
    ) -> EvaluationDataset:
        # Use LLM to generate questions from documents
        # Verify with human-in-the-loop or LLM judge
        ...
```

### Dataset Loader Interface
```python
class EvaluationDatasetLoader(Protocol):
    def load(self, path: str) -> EvaluationDataset: ...

class RAGASDatasetLoader:
    def load(self, path: str) -> EvaluationDataset:
        with open(path) as f:
            data = json.load(f)
        return EvaluationDataset(**data)

class JSONLDatasetLoader:
    def load(self, path: str) -> EvaluationDataset:
        samples = []
        with open(path) as f:
            for line in f:
                samples.append(EvaluationSample(**json.loads(line)))
        return EvaluationDataset(samples=samples)
```

### Configuration
```python
class EvaluationConfig(BaseModel):
    dataset_path: str
    dataset_format: DatasetFormat = DatasetFormat.RAGAS  # RAGAS, JSONL, CUSTOM
    sample_limit: Optional[int] = None
    sample_filter: Optional[dict] = None  # e.g., {"difficulty": "hard"}
    random_seed: int = 42
```

---

## Stage 2: Batch Query Execution

### Purpose
Run the query pipeline on all evaluation samples to generate predictions.

### Execution Strategy
```python
class EvaluationRunner:
    def __init__(
        self,
        query_pipeline: QueryPipeline,
        config: EvaluationConfig,
        experiment_tracker: Optional[ExperimentTracker] = None
    ):
        self.query_pipeline = query_pipeline
        self.config = config
        self.tracker = experiment_tracker
    
    async def run(self, dataset: EvaluationDataset) -> EvaluationResult:
        # 1. Apply sampling/filtering
        samples = self._prepare_samples(dataset)
        
        # 2. Run queries in batches with concurrency control
        predictions = await self._run_batch_queries(samples)
        
        # 3. Compute metrics
        result = await self.metrics_computer.compute(samples, predictions)
        
        # 4. Track experiment
        if self.tracker and self.config.track_experiment:
            self._log_experiment(dataset, predictions, result)
        
        # 5. Generate report
        if self.config.generate_report:
            self._generate_report(result)
        
        return result
    
    async def _run_batch_queries(self, samples: list[EvaluationSample]) -> list[QueryResponse]:
        semaphore = asyncio.Semaphore(self.config.batch_concurrency)
        
        async def run_one(sample: EvaluationSample) -> QueryResponse:
            async with semaphore:
                request = QueryRequest(
                    query=sample.query,
                    correlation_id=f"eval-{sample.id}"
                )
                try:
                    return await self.query_pipeline.query(request)
                except Exception as e:
                    logger.error(f"Query failed for {sample.id}: {e}")
                    return QueryResponse.error(sample.query, str(e))
        
        return await asyncio.gather(*[run_one(s) for s in samples])
```

### Concurrency Control
```python
class BatchQueryConfig(BaseModel):
    concurrency: int = 10
    timeout_per_query: float = 30.0
    retry_failed: bool = True
    max_retries: int = 1
    save_predictions: bool = True
    predictions_output_dir: str = "evaluation_results/predictions"
```

### Progress Tracking
```python
# Progress callback for long-running evaluations
class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
    
    def update(self, success: bool):
        self.completed += 1
        if not success:
            self.failed += 1
        
        if self.completed % 10 == 0:
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed
            eta = (self.total - self.completed) / rate if rate > 0 else 0
            logger.info(f"Evaluation progress: {self.completed}/{self.total} "
                       f"({100*self.completed/self.total:.1f}%) "
                       f"failed: {self.failed} ETA: {eta:.0f}s")
```

---

## Stage 3: Metrics Computation

### Metric Interface
```python
class Metric(Protocol):
    name: str
    requires_ground_truth: bool = True
    requires_context: bool = False
    
    async def compute(
        self,
        samples: list[EvaluationSample],
        predictions: list[QueryResponse]
    ) -> MetricResult: ...
```

### RAGAS Metrics

#### Faithfulness
```python
class FaithfulnessMetric:
    name = "faithfulness"
    requires_ground_truth = False
    requires_context = True
    
    def __init__(self, llm_judge: LLMJudge):
        self.judge = llm_judge
    
    async def compute(self, samples, predictions) -> MetricResult:
        scores = []
        for sample, pred in zip(samples, predictions):
            # Extract claims from answer
            claims = extract_claims(pred.answer)
            
            # Check each claim against context
            claim_scores = []
            for claim in claims:
                supported = await self.judge.check_entailment(
                    premise=build_context(pred.retrieval_metadata.results),
                    hypothesis=claim
                )
                claim_scores.append(1.0 if supported else 0.0)
            
            scores.append(np.mean(claim_scores) if claim_scores else 1.0)
        
        return MetricResult(
            name=self.name,
            value=np.mean(scores),
            std=np.std(scores),
            per_sample=scores,
            details={"num_claims_total": sum(len(extract_claims(p.answer)) for p in predictions)}
        )
```

#### Answer Relevancy
```python
class AnswerRelevancyMetric:
    name = "answer_relevancy"
    requires_ground_truth = False
    requires_context = False
    
    async def compute(self, samples, predictions) -> MetricResult:
        scores = []
        for sample, pred in zip(samples, predictions):
            # Generate questions from answer, compare to original
            generated_questions = await self.llm.generate_questions(pred.answer)
            similarities = [
                cosine_similarity(embed(q), embed(sample.query))
                for q in generated_questions
            ]
            scores.append(np.mean(similarities))
        
        return MetricResult(name=self.name, value=np.mean(scores), std=np.std(scores), per_sample=scores)
```

#### Context Precision
```python
class ContextPrecisionMetric:
    name = "context_precision"
    requires_ground_truth = True
    requires_context = True
    
    async def compute(self, samples, predictions) -> MetricResult:
        scores = []
        for sample, pred in zip(samples, predictions):
            # Check if relevant chunks are ranked high
            retrieved_ids = [r.chunk.id for r in pred.retrieval_metadata.results]
            relevant_ids = set(sample.expected_chunk_ids)
            
            if not relevant_ids:
                scores.append(1.0)
                continue
            
            # Precision at k
            precision_at_k = []
            for k in [1, 3, 5, 10]:
                top_k = retrieved_ids[:k]
                relevant_in_top_k = len(set(top_k) & relevant_ids)
                precision_at_k.append(relevant_in_top_k / k if k > 0 else 0)
            
            scores.append(np.mean(precision_at_k))
        
        return MetricResult(name=self.name, value=np.mean(scores), std=np.std(scores), per_sample=scores)
```

#### Context Recall
```python
class ContextRecallMetric:
    name = "context_recall"
    requires_ground_truth = True
    requires_context = True
    
    async def compute(self, samples, predictions) -> MetricResult:
        scores = []
        for sample, pred in zip(samples, predictions):
            retrieved_ids = set(r.chunk.id for r in pred.retrieval_metadata.results)
            relevant_ids = set(sample.expected_chunk_ids)
            
            if not relevant_ids:
                scores.append(1.0)
                continue
            
            recalled = len(retrieved_ids & relevant_ids) / len(relevant_ids)
            scores.append(recalled)
        
        return MetricResult(name=self.name, value=np.mean(scores), std=np.std(scores), per_sample=scores)
```

### Custom Metrics

#### Hallucination Rate
```python
class HallucinationRateMetric:
    name = "hallucination_rate"
    requires_ground_truth = False
    requires_context = True
    
    def __init__(self, verifier: GroundingVerifier):
        self.verifier = verifier
    
    async def compute(self, samples, predictions) -> MetricResult:
        rates = []
        for sample, pred in zip(samples, predictions):
            groundedness, flags = await self.verifier.verify(
                pred.answer,
                [r.chunk for r in pred.retrieval_metadata.results]
            )
            hallucination_rate = 1.0 - groundedness
            rates.append(hallucination_rate)
        
        return MetricResult(
            name=self.name,
            value=np.mean(rates),
            std=np.std(rates),
            per_sample=rates,
            details={"total_flags": sum(len(flags) for _, flags in results)}
        )
```

#### Citation Accuracy
```python
class CitationAccuracyMetric:
    name = "citation_accuracy"
    requires_ground_truth = False
    requires_context = True
    
    async def compute(self, samples, predictions) -> MetricResult:
        accuracies = []
        for sample, pred in zip(samples, predictions):
            if not pred.citations:
                accuracies.append(0.0)
                continue
            
            # Check each citation maps to retrieved context
            retrieved_chunk_ids = {r.chunk.id for r in pred.retrieval_metadata.results}
            valid_citations = sum(1 for c in pred.citations if c.chunk_id in retrieved_chunk_ids)
            accuracy = valid_citations / len(pred.citations)
            accuracies.append(accuracy)
        
        return MetricResult(name=self.name, value=np.mean(accuracies), std=np.std(accuracies), per_sample=accuracies)
```

#### Latency Metrics
```python
class LatencyMetrics:
    name = "latency"
    requires_ground_truth = False
    requires_context = False
    
    async def compute(self, samples, predictions) -> MetricResult:
        latencies = [p.query_metadata.total_latency_ms for p in predictions]
        
        return MetricResult(
            name=self.name,
            value=np.mean(latencies),
            std=np.std(latencies),
            min=np.min(latencies),
            max=np.max(latencies),
            per_sample=latencies,
            details={
                "p50": np.percentile(latencies, 50),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
            }
        )
```

### Metrics Computer
```python
class MetricsComputer:
    def __init__(self, metrics: list[Metric]):
        self.metrics = metrics
    
    async def compute(
        self,
        samples: list[EvaluationSample],
        predictions: list[QueryResponse]
    ) -> EvaluationResult:
        results = {}
        
        for metric in self.metrics:
            logger.info(f"Computing metric: {metric.name}")
            try:
                result = await metric.compute(samples, predictions)
                results[metric.name] = result
            except Exception as e:
                logger.error(f"Metric {metric.name} failed: {e}")
                results[metric.name] = MetricResult(
                    name=metric.name,
                    value=0.0,
                    details={"error": str(e)}
                )
        
        # Determine overall pass/fail
        passed = all(
            r.passed if r.passed is not None else True
            for r in results.values()
        )
        
        return EvaluationResult(
            dataset_name=samples[0].dataset_name if samples else "unknown",
            dataset_version=samples[0].dataset_version if samples else "unknown",
            config_snapshot=get_settings().model_dump(),
            sample_count=len(samples),
            metrics=results,
            per_sample=self._compute_per_sample(samples, predictions, results),
            started_at=self.start_time,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - self.start_time).total_seconds(),
            passed=passed
        )
```

---

## Stage 4: Experiment Tracking

### Tracked Data
```python
def _log_experiment(self, dataset, predictions, result):
    run = self.tracker.start_run(
        experiment_name=self.config.experiment_name,
        run_name=f"eval-{dataset.name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        config=result.config_snapshot
    )
    
    # Log params
    self.tracker.log_params(run.run_id, {
        "dataset": dataset.name,
        "dataset_version": dataset.version,
        "sample_count": len(dataset.samples),
        "metrics": list(result.metrics.keys()),
    })
    
    # Log aggregated metrics
    for name, metric in result.metrics.items():
        self.tracker.log_metrics(run.run_id, {
            f"eval/{name}": metric.value,
            f"eval/{name}_std": metric.std or 0,
        })
        
        # Log threshold if defined
        if metric.threshold is not None:
            self.tracker.log_metrics(run.run_id, {
                f"eval/{name}_threshold": metric.threshold,
                f"eval/{name}_passed": metric.passed or False,
            })
    
    # Log artifacts
    if self.config.save_predictions:
        pred_path = self._save_predictions(predictions)
        self.tracker.log_artifact(run.run_id, pred_path, "predictions.json")
    
    report_path = self._generate_report(result)
    self.tracker.log_artifact(run.run_id, report_path, "evaluation_report.html")
    
    self.tracker.end_run(run.run_id, RunStatus.COMPLETED)
```

---

## Stage 5: Report Generation

### HTML Report
```python
class ReportGenerator:
    def generate_html(self, result: EvaluationResult) -> str:
        template = load_template("evaluation/report.html.j2")
        
        return template.render(
            result=result,
            timestamp=datetime.utcnow().isoformat(),
            charts=self._generate_charts(result)
        )
    
    def _generate_charts(self, result: EvaluationResult) -> dict:
        charts = {}
        
        # Metric comparison bar chart
        charts["metrics_bar"] = {
            "type": "bar",
            "data": {
                "labels": list(result.metrics.keys()),
                "datasets": [{
                    "label": "Score",
                    "data": [m.value for m in result.metrics.values()],
                    "backgroundColor": "rgba(54, 162, 235, 0.6)"
                }]
            }
        }
        
        # Per-sample scatter
        if result.per_sample:
            charts["sample_scatter"] = {
                "type": "scatter",
                "data": {
                    "datasets": [{
                        "label": "Sample Scores",
                        "data": [
                            {"x": i, "y": s.metrics.get("faithfulness", 0)}
                            for i, s in enumerate(result.per_sample)
                        ]
                    }]
                }
            }
        
        # Latency distribution
        latencies = [s.metrics.get("latency", 0) for s in result.per_sample]
        charts["latency_histogram"] = {
            "type": "histogram",
            "data": latencies
        }
        
        return charts
```

### JSON Report
```python
def generate_json(self, result: EvaluationResult) -> str:
    return result.model_dump_json(indent=2)
```

### Markdown Summary
```python
def generate_markdown(self, result: EvaluationResult) -> str:
    lines = [
        f"# Evaluation Report: {result.dataset_name}",
        f"**Version:** {result.dataset_version}",
        f"**Samples:** {result.sample_count}",
        f"**Duration:** {result.duration_seconds:.1f}s",
        f"**Status:** {'✅ PASSED' if result.passed else '❌ FAILED'}",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Std | Threshold | Passed |",
        "|--------|-------|-----|-----------|--------|",
    ]
    
    for name, metric in result.metrics.items():
        threshold = f"{metric.threshold:.3f}" if metric.threshold else "N/A"
        passed = "✅" if metric.passed else ("❌" if metric.passed is False else "⚪")
        lines.append(f"| {name} | {metric.value:.3f} | {metric.std:.3f} | {threshold} | {passed} |")
    
    return "\n".join(lines)
```

---

## Complete Evaluation Lifecycle Metrics

### Execution Metrics
| Metric | Description |
|--------|-------------|
| `evaluation_runs_total` | Total evaluation runs |
| `evaluation_samples_processed` | Samples evaluated |
| `evaluation_duration_seconds` | Wall-clock time |
| `evaluation_batch_concurrency` | Actual concurrency used |
| `evaluation_query_failures` | Failed query count |
| `evaluation_query_retries` | Retry count |

### Metric Metrics
| Metric | Description |
|--------|-------------|
| `evaluation_metric_value{metric}` | Metric score |
| `evaluation_metric_std{metric}` | Standard deviation |
| `evaluation_metric_passed{metric}` | Pass/fail status |
| `evaluation_overall_passed` | Overall pass/fail |

### Quality Metrics
| Metric | Description |
|--------|-------------|
| `evaluation_faithfulness` | Faithfulness score |
| `evaluation_answer_relevancy` | Answer relevancy score |
| `evaluation_context_precision` | Context precision |
| `evaluation_context_recall` | Context recall |
| `evaluation_hallucination_rate` | Hallucination rate |
| `evaluation_citation_accuracy` | Citation accuracy |

---

## Configuration Summary

```python
class EvaluationConfig(BaseModel):
    # Dataset
    dataset_path: str
    dataset_format: DatasetFormat = DatasetFormat.RAGAS
    sample_limit: Optional[int] = None
    sample_filter: Optional[dict] = None
    random_seed: int = 42
    
    # Execution
    batch_concurrency: int = 10
    timeout_per_query: float = 30.0
    retry_failed: bool = True
    max_retries: int = 1
    
    # Metrics
    metrics: list[str] = Field(default=[
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "hallucination_rate",
        "citation_accuracy",
        "latency"
    ])
    metric_thresholds: dict[str, float] = Field(default_factory=dict)
    
    # Experiment tracking
    track_experiment: bool = True
    experiment_name: str = "rag-evaluation"
    
    # Output
    save_predictions: bool = True
    generate_report: bool = True
    report_formats: list[ReportFormat] = [ReportFormat.HTML, ReportFormat.JSON, ReportFormat.MARKDOWN]
    output_dir: str = "evaluation_results"
```

---

## Evaluation Thresholds (Default)

| Metric | Default Threshold | Rationale |
|--------|-------------------|-----------|
| `faithfulness` | 0.7 | Answer should be mostly grounded |
| `answer_relevancy` | 0.7 | Answer should address query |
| `context_precision` | 0.5 | Relevant chunks in top-5 |
| `context_recall` | 0.5 | Retrieve half of relevant |
| `hallucination_rate` | 0.3 | Less than 30% hallucination |
| `citation_accuracy` | 0.9 | Citations should be valid |
| `latency_p95` | 5000ms | Under 5 seconds |

---

## Testing the Evaluation Lifecycle

### Unit Tests
```python
async def test_faithfulness_metric():
    metric = FaithfulnessMetric(mock_llm_judge)
    samples = [sample_with_context()]
    predictions = [prediction_with_grounded_answer()]
    
    result = await metric.compute(samples, predictions)
    assert 0 <= result.value <= 1
    assert result.name == "faithfulness"

async def test_context_precision():
    metric = ContextPrecisionMetric()
    sample = EvaluationSample(
        expected_chunk_ids=["chunk_1", "chunk_2"]
    )
    pred = QueryResponse(
        retrieval_metadata=RetrievalMetadata(
            results=[chunk_1, chunk_3, chunk_2, ...]  # chunk_1 at rank 1, chunk_2 at rank 3
        )
    )
    result = await metric.compute([sample], [pred])
    # Precision should reflect relevant chunks in top-k
    assert result.value > 0

async def test_batch_query_execution():
    runner = EvaluationRunner(mock_pipeline, config)
    samples = [sample() for _ in range(5)]
    predictions = await runner._run_batch_queries(samples)
    assert len(predictions) == 5
```

### Integration Tests
```python
async def test_full_evaluation_pipeline():
    runner = EvaluationRunner(pipeline, config, mock_tracker)
    dataset = load_test_dataset()
    result = await runner.run(dataset)
    
    assert result.sample_count == len(dataset.samples)
    assert "faithfulness" in result.metrics
    assert result.duration_seconds > 0
    
    # Check experiment tracking called
    mock_tracker.start_run.assert_called_once()
    mock_tracker.log_metrics.assert_called()
```

### Golden File Tests
```python
async def test_metrics_match_golden():
    """Ensure metric computations are deterministic."""
    runner = EvaluationRunner(pipeline, config)
    dataset = load_golden_dataset()
    result = await runner.run(dataset)
    
    golden = load_golden_metrics()
    for name, expected in golden.items():
        actual = result.metrics[name].value
        assert abs(actual - expected) < 0.001, f"{name} drifted: {actual} vs {expected}"
```