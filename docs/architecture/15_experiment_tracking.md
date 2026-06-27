# Experiment Tracking Lifecycle

## Purpose

Experiment tracking captures the full lineage of RAG pipeline iterations, enabling reproducible research and systematic optimization.

## Sequence Diagram

```
sequenceDiagram
    participant API as Experiment API
    participant Context as TrackedPipeline
    participant Tracker as ExperimentTracker
    participant Pipeline as Query/Ingestion/Eval Pipeline
    participant Storage as MLflow/W&B
    
    API->>Context: run(name, config)
    Context->>Tracker: create_experiment(name)
    Tracker->>Storage: POST /experiments
    Storage-->>Tracker: experiment_id
    
    Tracker->>Context: start_run(experiment_id)
    Context->>Pipeline: execute()
    Pipeline-->>Context: results
    
    loop Per Stage
        Context->>Tracker: log_metrics(metrics)
        Tracker->>Storage: POST /metrics
    end
    
    Context->>Tracker: log_artifact(path)
    Tracker->>Storage: Upload artifact
    
    Context->>Tracker: end_run(status)
    Tracker->>Storage: PATCH /runs/{id}
    Storage-->>API: Run completed
```

## Flowchart

```
flowchart TD
    A[Run Initialization] --> B[Create Experiment]
    B --> C[Start Run]
    C --> D[Log Config Snapshot]
    
    D --> E{Pipeline Stage}
    E --> F[Execute Stage]
    F --> G[Measure Metrics]
    G --> H[Log to Tracker]
    
    H --> I{More Stages?}
    I -->|Yes| J[Next Stage]
    I -->|No| K[Finalize Run]
    
    J --> F
    K --> L[Log Final Metrics]
    L --> M{Artifacts to Log?}
    
    M -->|Yes| N[Upload Artifacts]
    M -->|No| O[End Run]
    
    N --> O
    O --> P[Return Run Result]
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `experiment_name` | `str` | Name for experiment group |
| `run_name` | `str` | Unique run identifier |
| `config` | `IngestionConfig/QueryConfig/EvalConfig` | Full config snapshot |
| `params` | `dict` | Flat parameter dict |
| `metrics` | `dict[str, float]` | Metric name → value |
| `artifacts` | `list[str]` | File paths to log |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `run_id` | `str` | Unique run identifier |
| `experiment_id` | `str` | Parent experiment |
| `status` | `RunStatus` | RUNNING, COMPLETED, FAILED |
| `metrics` | `dict` | Logged metrics |

## Tracked Entities

### Experiment
```python
{
    "name": "chunking-strategy-comparison",
    "tags": {"team": "research", "priority": "high"},
    "config": {"chunking.strategy": "recursive", ...},
    "created_at": "2026-06-28T00:00:00Z"
}
```

### Run
```python
{
    "run_id": "abc-123",
    "experiment_name": "chunking-strategy-comparison",
    "status": "completed",
    "config": {"chunking.strategy": "recursive", ...},
    "metrics": {"faithfulness": 0.85, "context_precision": 0.78},
    "start_time": "2026-06-28T00:01:00Z",
    "end_time": "2026-06-28T00:15:00Z"
}
```

### Artifact
```python
{
    "name": "evaluation-predictions",
    "path": "s3://bucket/experiments/run_abc/predictions.json",
    "type": "predictions",
    "size_bytes": 1024000,
    "checksum": "sha256:..."
}
```

## Tracking Providers

### MLflow
- Local file store (dev)
- S3 artifact store (prod)
- REST API for remote tracking
- UI for comparison

### Weights & Biases
- Cloud native
- Collaboration features
- Advanced visualization
- Sweep integration

## Lifecycle Hooks

### Pre-execution
```python
# Log config, git commit, start time
tracker.log_params(params)
tracker.log_tags(tags)
```

### Per-stage
```python
# Log intermediate metrics
tracker.log_metrics({"chunking_duration_ms": 150})
tracker.log_metrics({"embedding_cache_rate": 0.75})
```

### Post-execution
```python
# Log final metrics, artifacts
tracker.log_metrics(final_metrics)
tracker.log_artifact("results.json")
tracker.end_run(status="completed")
```

## Metadata Tracking

| Entity | Tracked Fields |
|--------|---------------|
| **Run Config** | All pipeline settings |
| **Environment** | Python version, package versions, git commit |
| **Hardware** | CPU count, GPU type, memory |
| **Metrics** | All evaluation metrics, performance metrics |
| **Artifacts** | Predictions, datasets, reports |

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Tracker unavailable | `ExperimentError` | Log locally, continue |
| Artifact too large | `ExperimentError` | Upload to object storage |
| Run conflicts | `ExperimentError` | Generate new run name |
| Quota exceeded | `ExperimentError` | Pause, alert, resume later |

## Recovery Strategy

### Local Fallback
```python
try:
    tracker.log_metrics(metrics)
except TrackerUnavailable:
    local_tracker = LocalFileTracker()
    local_tracker.log_metrics(metrics)
    queue_for_sync()
```

### Orphan Recovery
- Runs missing end marker marked as "running"
- Manual recovery via API
- Cleanup TTL for abandoned runs

### Offline Mode
- Queue events to file
- Sync when tracker available
- Conflict resolution

## Performance Considerations

### Async Logging
- Don't block pipeline on tracking calls
- Fire-and-forget logging
- Batch metric updates

### Artifact Strategy
- Large artifacts → object storage
- Small → direct upload
- Metadata always logged

## Future Scalability

### Automated Comparison
```
Run A: metrics = {faithfulness: 0.85}
Run B: metrics = {faithfulness: 0.87}
        │
        ▼
┌─────────────────┐
│  Statistical    │
│  Significance   │
│  Test           │
└─────────────────┘
```

### Model Registry Integration
- Log embeddings model versions
- Track data drift
- Automatic retraining triggers