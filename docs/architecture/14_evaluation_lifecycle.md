# Evaluation Lifecycle

## Purpose

Evaluation measures RAG pipeline quality using automated metrics, providing feedback for iteration and ensuring consistent answer quality.

## Sequence Diagram

```
sequenceDiagram
    participant API as Evaluation API
    participant Runner as EvaluationRunner
    participant Dataset as DatasetLoader
    participant Pipeline as QueryPipeline
    participant Metrics as MetricsComputer
    participant Tracker as ExperimentTracker
    
    API->>Runner: evaluate(dataset_path)
    
    Runner->>Dataset: load(dataset_path)
    Dataset-->>Runner: EvaluationDataset
    
    Runner->>Pipeline: query(sample)
    Pipeline-->>Runner: QueryResponse
    
    Runner->>Metrics: compute(dataset_samples, predictions)
    Metrics-->>Runner: EvaluationResult
    
    alt Track Experiment
        Runner->>Tracker: log_metrics(result)
        Runner->>Tracker: log_artifact(predictions)
    end
    
    Runner-->>API: EvaluationResult
```

## Flowchart

```
flowchart TD
    A[Evaluation Request] --> B[Load Dataset]
    B --> C[Initialize Query Pipeline]
    C --> D[Run Batch Queries]
    
    D --> E{Concurrency Control}
    E --> F[Semaphore Limit]
    F --> G[Execute Query]
    
    G --> H[Collect Predictions]
    H --> I[Compute Metrics]
    
    I --> J{Ragas Available?}
    J -->|Yes| K[Ragas Metrics]
    J -->|No| L[Custom Metrics]
    
    K --> M[Faithfulness]
    K --> N[Answer Relevancy]
    K --> O[Context Precision]
    K --> P[Context Recall]
    
    L --> Q[Simple Heuristics]
    
    M --> R[Aggregate Results]
    N --> R
    O --> R
    P --> R
    Q --> R
    
    R --> S{Track Experiment?}
    S -->|Yes| T[Log to Tracker]
    S -->|No| U[Skip Tracking]
    
    T --> V[Return EvaluationResult]
    U --> V
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `dataset` | `EvaluationDataset` | Test set of queries |
| `dataset.samples` | `EvaluationSample[]` | Query + ground truth pairs |
| `config.metrics` | `list[str]` | Metrics to compute |
| `config.batch_concurrency` | `int` | Parallel query executions |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `EvaluationResult` | Model | Aggregated metrics |
| `result.metrics` | `dict` | Name → MetricResult mapping |
| `result.per_sample` | `list` | Per-query metric values |
| `result.sample_count` | `int` | Number of samples evaluated |

## Built-in Metrics

### RAGAS Metrics (LLM-based)

| Metric | Description | Range |
|--------|-------------|-------|
| Faithfulness | Answer grounded in context | 0-1 |
| Answer Relevancy | Answer addresses query | 0-1 |
| Context Precision | Relevant chunks ranked high | 0-1 |
| Context Recall | All relevant chunks retrieved | 0-1 |
| Context Relevancy | Chunks relevant to query | 0-1 |
| Answer Correctness | Semantic match to expected | 0-1 |

### Custom Metrics (Heuristic)

| Metric | Description | Range |
|--------|-------------|-------|
| Hallucination Rate | Claims without supporting evidence | 0-1 |
| Citation Accuracy | Citations match source content | 0-1 |
| Citation Coverage | Fraction of sentences cited | 0-1 |

### Performance Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| Latency p50/p95/p99 | Response time percentiles | ms |
| Tokens per query | Average token usage | count |
| Cost per query | API cost | USD |

## Metric Computation Flow

### Faithfulness
```
1. Extract claims from answer
2. Check each claim against context
3. Compute fraction supported by context
```

### Context Precision
```
1. For each retrieved chunk
2. Check if chunk is relevant to query
3. Compute precision at each rank
4. Average across ranks
```

### Context Recall
```
1. Identify relevant chunks in dataset
2. Check if retrieved chunks overlap
3. Compute fraction found
```

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Dataset not found | `EvaluationError` | Fail fast |
| Query pipeline error | `EvaluationError` | Log, continue with other samples |
| Metric computation fails | `EvaluationError` | Log error, set metric to None |
| Tracker unavailable | `ExperimentError` | Continue without tracking |
| Out of memory | `EvaluationError` | Process in smaller batches |
| Timeout | `EvaluationError` | Track partial results |

## Recovery Strategy

### Resume on Failure
```python
checkpoint = load_checkpoint()
for sample in dataset.samples[checkpoint.last_index:]:
    try:
        process_sample(sample)
        checkpoint.update(sample.index)
    except:
        continue  # Skip failed samples
```

### Idempotent Results
- Each metric computed independently
- No shared state between samples
- Can rerun subset without side effects

### Graceful Degradation
- If LLM metrics fail, use heuristic fallbacks
- Partial results still useful
- Report which metrics were computed

## Performance Considerations

### Batch Execution
```python
# Run queries concurrently but bounded
semaphore = asyncio.Semaphore(config.batch_concurrency)

async def evaluate_sample(sample):
    async with semaphore:
        return await pipeline.query(sample.query)
```

### Metric Caching
- Cache LLM responses for repeated queries
- Share context across metrics
- Parallel metric computation

### Sampling for Large Datasets
- `sample_limit` config option
- Stratified sampling by query type
- Representative subset for quick feedback

## Future Scalability

### Continuous Evaluation
```
Production Queries
        │
        ▼
┌─────────────────┐
│  Feedback Loop  │
│  (Collect GT)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Auto-Evaluate  │
│  (Nightly runs) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Alert if       │
│  Metrics Drop   │
└─────────────────┘
```

### Human Evaluation Integration
- Label studio for human labels
- Inter-annotator agreement
- Calibration of automatic metrics