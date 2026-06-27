# Experiment Tracking

## Overview

This document describes the complete experiment tracking workflow in the Retrieval Intelligence Platform, covering experiment design, run execution, parameter/metric/artifact logging, comparison, and reproducibility.

---

## Experiment Tracking Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        EXPERIMENT TRACKING                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                EXPERIMENT TRACKER INTERFACE                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐    │   │
│  │  │  MLflow Tracker │  │  W&B Tracker    │  │  ClearML Tracker│  │  Custom Tracker   │    │   │
│  │  │  (Local/Remote) │  │  (Cloud)        │  │  (Optional)     │  │  (Extensible)     │    │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                    │                                               │
│                    ┌─────────────────────────────┼─────────────────────────────┐                 │
│                    ▼                             ▼                             ▼                 │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐ │
│  │       EXPERIMENT            │ │           RUN               │ │         ARTIFACT            │ │
│  │  • Name, tags               │ │  • Config snapshot          │ │  • Model checkpoints      │ │
│  │  • Description              │ │  • Parameters (flat)        │ │  • Datasets               │ │
│  │  • Default artifact loc     │ │  • Metrics (time-series)    │ │  • Reports                │ │
│  │  • Lifecycle management     │ │  • Artifacts                │ │  • Logs                   │ │
│  └─────────────────────────────┘ └─────────────────────────────┘ └─────────────────────────────┘ │
│                                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tracker Interface

### Core Protocol
```python
class ExperimentTracker(Protocol):
    # Experiment management
    def create_experiment(self, name: str, tags: dict[str, str] = None) -> str: ...
    def get_experiment(self, experiment_id: str) -> Experiment: ...
    def list_experiments(self, filter: str = None) -> list[Experiment]: ...
    
    # Run management
    def start_run(
        self, 
        experiment_id: str, 
        run_name: str, 
        config: dict,
        tags: dict[str, str] = None
    ) -> Run: ...
    def end_run(self, run_id: str, status: RunStatus) -> None: ...
    def get_run(self, run_id: str) -> Run: ...
    def search_runs(
        self, 
        experiment_ids: list[str], 
        filter: str = None,
        max_results: int = 100
    ) -> list[Run]: ...
    
    # Parameter logging
    def log_params(self, run_id: str, params: dict) -> None: ...
    
    # Metric logging
    def log_metrics(
        self, 
        run_id: str, 
        metrics: dict[str, float], 
        step: Optional[int] = None
    ) -> None: ...
    
    # Artifact logging
    def log_artifact(
        self, 
        run_id: str, 
        path: str, 
        name: Optional[str] = None,
        artifact_type: ArtifactType = ArtifactType.LOG
    ) -> None: ...
    def log_artifacts(self, run_id: str, dir_path: str) -> None: ...
    
    # Model logging (MLflow-specific)
    def log_model(
        self, 
        run_id: str, 
        model: Any, 
        artifact_path: str,
        signature: Optional[ModelSignature] = None
    ) -> None: ...
```

---

## MLflow Tracker Implementation

### Configuration
```python
class MLflowConfig(BaseModel):
    tracking_uri: str = "sqlite:///mlflow.db"
    artifact_root: str = "mlruns"
    registry_uri: Optional[str] = None
    experiment_name: str = "retrieval-intelligence"
    create_experiment_if_missing: bool = True
```

### Implementation
```python
class MLflowTracker:
    def __init__(self, config: MLflowConfig):
        self.config = config
        mlflow.set_tracking_uri(config.tracking_uri)
        
        if config.registry_uri:
            mlflow.set_registry_uri(config.registry_uri)
        
        # Ensure experiment exists
        exp = mlflow.get_experiment_by_name(config.experiment_name)
        if exp is None:
            if config.create_experiment_if_missing:
                self.experiment_id = mlflow.create_experiment(
                    config.experiment_name,
                    artifact_location=config.artifact_root
                )
            else:
                raise ExperimentError(f"Experiment not found: {config.experiment_name}")
        else:
            self.experiment_id = exp.experiment_id
    
    def create_experiment(self, name: str, tags: dict = None) -> str:
        return mlflow.create_experiment(name, tags=tags or {})
    
    def start_run(self, experiment_id: str, run_name: str, config: dict, tags: dict = None) -> Run:
        mlflow.set_experiment(experiment_id)
        run = mlflow.start_run(run_name=run_name, tags=tags or {})
        
        # Log full config as params (flattened)
        flat_config = flatten_dict(config)
        mlflow.log_params(flat_config)
        
        # Log git info if available
        git_info = get_git_info()
        if git_info:
            mlflow.log_params(git_info)
        
        return Run(
            run_id=run.info.run_id,
            experiment_id=experiment_id,
            name=run_name,
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow()
        )
    
    def log_params(self, run_id: str, params: dict) -> None:
        with mlflow.start_run(run_id=run_id):
            mlflow.log_params(flatten_dict(params))
    
    def log_metrics(self, run_id: str, metrics: dict, step: Optional[int] = None) -> None:
        with mlflow.start_run(run_id=run_id):
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
    
    def log_artifact(self, run_id: str, path: str, name: Optional[str] = None, artifact_type: ArtifactType = ArtifactType.LOG) -> None:
        with mlflow.start_run(run_id=run_id):
            artifact_path = name or os.path.basename(path)
            mlflow.log_artifact(path, artifact_path)
    
    def log_artifacts(self, run_id: str, dir_path: str) -> None:
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifacts(dir_path)
    
    def end_run(self, run_id: str, status: RunStatus) -> None:
        mlflow.end_run(status=status.value if hasattr(status, 'value') else status)
    
    def get_run(self, run_id: str) -> Run:
        mlflow_run = mlflow.get_run(run_id)
        return self._convert_run(mlflow_run)
    
    def search_runs(self, experiment_ids: list[str], filter: str = None, max_results: int = 100) -> list[Run]:
        runs = mlflow.search_runs(
            experiment_ids=experiment_ids,
            filter_string=filter,
            max_results=max_results
        )
        return [self._convert_run(r) for r in runs]
```

---

## Weights & Biases Tracker Implementation

### Configuration
```python
class WandbConfig(BaseModel):
    project: str = "retrieval-intelligence"
    entity: Optional[str] = None
    api_key: Optional[str] = None
    mode: str = "online"  # online, offline, disabled
    tags: list[str] = Field(default_factory=list)
```

### Implementation
```python
class WandbTracker:
    def __init__(self, config: WandbConfig):
        self.config = config
        if config.api_key:
            wandb.login(key=config.api_key)
    
    def start_run(self, experiment_id: str, run_name: str, config: dict, tags: dict = None) -> Run:
        run = wandb.init(
            project=experiment_id,  # Use experiment_id as project
            name=run_name,
            config=config,
            tags=(self.config.tags or []) + (list(tags.keys()) if tags else []),
            mode=self.config.mode,
            reinit=True
        )
        
        return Run(
            run_id=run.id,
            experiment_id=experiment_id,
            name=run_name,
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow()
        )
    
    def log_params(self, run_id: str, params: dict) -> None:
        # W&B doesn't support logging to existing run by ID easily
        # Use wandb.config.update or run.log
        wandb.config.update(flatten_dict(params), allow_val_change=True)
    
    def log_metrics(self, run_id: str, metrics: dict, step: Optional[int] = None) -> None:
        wandb.log(metrics, step=step)
    
    def log_artifact(self, run_id: str, path: str, name: Optional[str] = None, artifact_type: ArtifactType = ArtifactType.LOG) -> None:
        artifact = wandb.Artifact(
            name=name or os.path.basename(path),
            type=artifact_type.value
        )
        artifact.add_file(path)
        wandb.log_artifact(artifact)
    
    def end_run(self, run_id: str, status: RunStatus) -> None:
        wandb.finish(exit_code=0 if status == RunStatus.COMPLETED else 1)
```

---

## Tracked Entities

### Experiment
```python
class Experiment(BaseModel):
    experiment_id: str
    name: str
    tags: dict[str, str] = Field(default_factory=dict)
    artifact_location: str
    created_at: datetime
    lifecycle_stage: Literal["active", "deleted"] = "active"
```

### Run
```python
class Run(BaseModel):
    run_id: str
    experiment_id: str
    name: Optional[str] = None
    status: RunStatus = RunStatus.RUNNING
    
    # Config & params
    config: dict = Field(default_factory=dict)      # Full nested config
    params: dict = Field(default_factory=dict)      # Flattened params for querying
    
    # Metrics (time-series)
    metrics: dict[str, list[MetricPoint]] = Field(default_factory=dict)
    
    # Artifacts
    artifacts: list[Artifact] = Field(default_factory=list)
    
    # Metadata
    tags: dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Error info
    error: Optional[str] = None

class MetricPoint(BaseModel):
    key: str
    value: float
    step: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Artifact
```python
class Artifact(BaseModel):
    artifact_id: str
    run_id: str
    name: str
    path: str  # Local or remote URI
    type: ArtifactType
    size_bytes: int
    checksum: str  # SHA256
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Config Snapshot for Reproducibility

### Complete Config Capture
```python
def capture_config_snapshot() -> ExperimentConfig:
    settings = get_settings()
    
    return ExperimentConfig(
        # Pipeline configs
        ingestion=settings.ingestion.model_dump(),
        query=settings.query.model_dump(),
        evaluation=settings.evaluation.model_dump(),
        
        # Environment
        python_version=sys.version,
        package_versions=get_key_package_versions(),
        git_commit=get_git_commit(),
        git_dirty=is_git_dirty(),
        git_branch=get_git_branch(),
        
        # Hardware
        cpu_count=psutil.cpu_count(),
        gpu_count=get_gpu_count(),
        gpu_type=get_gpu_type(),
        memory_gb=psutil.virtual_memory().total / (1024**3),
        
        captured_at=datetime.utcnow()
    )

def get_key_package_versions() -> dict[str, str]:
    key_packages = [
        "fastapi", "pydantic", "langchain", "sentence-transformers",
        "transformers", "torch", "faiss-cpu", "chromadb",
        "openai", "anthropic", "ragas", "deepeval",
        "mlflow", "wandb", "numpy", "pandas", "polars"
    ]
    versions = {}
    for pkg in key_packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "not_installed"
    return versions
```

### Config Logging
```python
def log_config_to_tracker(tracker: ExperimentTracker, run_id: str, config: ExperimentConfig):
    # Log full nested config as JSON artifact
    config_path = f"/tmp/config_{run_id}.json"
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2, default=str)
    
    tracker.log_artifact(run_id, config_path, "config.json", ArtifactType.CONFIG)
    
    # Log flattened params for querying
    flat_params = flatten_dict(config.model_dump())
    tracker.log_params(run_id, flat_params)
```

---

## Automatic Experiment Tracking

### Context Manager for Pipelines
```python
class TrackedPipeline:
    """Context manager that automatically tracks pipeline runs."""
    
    def __init__(
        self, 
        tracker: ExperimentTracker, 
        experiment_name: str,
        pipeline_name: str  # "ingestion", "query", "evaluation"
    ):
        self.tracker = tracker
        self.experiment_name = experiment_name
        self.pipeline_name = pipeline_name
        self.run: Optional[Run] = None
    
    @asynccontextmanager
    async def run(self, run_name: str, config: dict, tags: dict = None):
        experiment_id = self.tracker.create_experiment(self.experiment_name, {})
        
        self.run = self.tracker.start_run(
            experiment_id=experiment_id,
            run_name=f"{self.pipeline_name}-{run_name}",
            config=config,
            tags={**(tags or {}), "pipeline": self.pipeline_name}
        )
        
        try:
            yield self
            self.tracker.end_run(self.run.run_id, RunStatus.COMPLETED)
        except Exception as e:
            self.tracker.end_run(self.run.run_id, RunStatus.FAILED)
            raise
    
    def log_metrics(self, metrics: dict, step: Optional[int] = None):
        if self.run:
            self.tracker.log_metrics(self.run.run_id, metrics, step)
    
    def log_artifact(self, path: str, name: Optional[str] = None, artifact_type: ArtifactType = ArtifactType.LOG):
        if self.run:
            self.tracker.log_artifact(self.run.run_id, path, name, artifact_type)
    
    def set_tag(self, key: str, value: str):
        if self.run:
            self.run.tags[key] = value
            # Note: MLflow requires separate API for tag updates
```

### Usage in Pipeline Orchestration
```python
class QueryPipeline:
    def __init__(self, tracker: ExperimentTracker, ...):
        self.tracked = TrackedPipeline(tracker, "rag-queries", "query")
        ...
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        async with self.tracked.run(
            run_name=request.correlation_id or "adhoc",
            config={"query": request.query, "params": request.params.model_dump() if request.params else {}},
            tags={"user_id": request.user_id, "session_id": request.session_id}
        ) as tracked:
            # Execute pipeline
            result = await self._execute_query(request)
            
            # Log metrics
            tracked.log_metrics({
                "query/latency_total_ms": result.query_metadata.total_latency_ms,
                "query/retrieval_latency_ms": result.retrieval_metadata.retrieval_latency_ms,
                "query/generation_latency_ms": result.generation_metadata.latency_ms,
                "query/tokens_total": result.generation_metadata.total_tokens,
                "query/citations_count": len(result.citations),
            })
            
            return result
```

---

## Experiment Comparison & Analysis

### Run Comparison
```python
class ExperimentAnalyzer:
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
    
    def compare_runs(
        self, 
        run_ids: list[str], 
        metrics: list[str] = None
    ) -> ComparisonResult:
        runs = [self.tracker.get_run(rid) for rid in run_ids]
        
        # Extract metric values
        comparison = {}
        for metric in metrics or []:
            comparison[metric] = {
                run.run_id: run.metrics.get(metric, [{}])[-1].value if run.metrics.get(metric) else None
                for run in runs
            }
        
        # Config diff
        configs = {run.run_id: run.config for run in runs}
        config_diff = self._diff_configs(configs)
        
        return ComparisonResult(
            runs=runs,
            metric_comparison=comparison,
            config_diff=config_diff
        )
    
    def _diff_configs(self, configs: dict[str, dict]) -> dict:
        """Find differences between run configs."""
        all_keys = set()
        for config in configs.values():
            all_keys.update(flatten_dict(config).keys())
        
        diff = {}
        for key in all_keys:
            values = {run_id: flatten_dict(config).get(key) for run_id, config in configs.items()}
            unique_values = set(values.values())
            if len(unique_values) > 1:
                diff[key] = values
        
        return diff
```

### Metric Trend Analysis
```python
def get_metric_history(
    self, 
    experiment_id: str, 
    metric: str, 
    days: int = 30
) -> list[MetricPoint]:
    filter_str = f"attributes.status = 'FINISHED' AND params.experiment_id = '{experiment_id}'"
    runs = self.tracker.search_runs([experiment_id], filter=filter_str)
    
    points = []
    for run in runs:
        if metric in run.metrics:
            for point in run.metrics[metric]:
                points.append(MetricPoint(
                    key=metric,
                    value=point.value,
                    step=point.step,
                    timestamp=point.timestamp
                ))
    
    return sorted(points, key=lambda p: p.timestamp)
```

---

## Artifact Management

### Artifact Types
```python
class ArtifactType(str, Enum):
    MODEL = "model"
    DATASET = "dataset"
    REPORT = "report"
    LOG = "log"
    PREDICTIONS = "predictions"
    CONFIG = "config"
    CHECKPOINT = "checkpoint"
    VISUALIZATION = "visualization"
```

### Artifact Storage
```python
class ArtifactStore:
    def __init__(self, base_path: str = "artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def store(self, run_id: str, artifact: Artifact) -> str:
        """Store artifact and return URI."""
        dest_dir = self.base_path / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / artifact.name
        shutil.copy2(artifact.path, dest_path)
        
        # Verify checksum
        if hashlib.sha256(dest_path.read_bytes()).hexdigest() != artifact.checksum:
            raise ArtifactError("Checksum mismatch after copy")
        
        return f"file://{dest_path.absolute()}"
    
    def retrieve(self, uri: str, dest: str) -> None:
        """Retrieve artifact from URI."""
        if uri.startswith("file://"):
            src = Path(uri[7:])
            shutil.copy2(src, dest)
        elif uri.startswith("s3://"):
            download_from_s3(uri, dest)
        elif uri.startswith("gs://"):
            download_from_gcs(uri, dest)
        else:
            raise ArtifactError(f"Unsupported URI scheme: {uri}")
```

---

## Reproducibility Guarantees

### What's Tracked for Reproducibility
| Category | Tracked |
|----------|---------|
| **Code** | Git commit, diff status, branch |
| **Config** | Full nested config snapshot |
| **Environment** | Python version, key package versions |
| **Hardware** | CPU count, GPU count/type, memory |
| **Data** | Dataset name, version, sample hashes |
| **Random Seeds** | All seeds used (numpy, torch, random) |
| **External APIs** | Model versions, API endpoints |

### Reproduction Checklist
```python
def verify_reproducibility(original_run: Run, reproduced_run: Run) -> ReproducibilityReport:
    issues = []
    
    # Config match
    if original_run.config != reproduced_run.config:
        issues.append("Config mismatch")
    
    # Git commit match
    orig_commit = original_run.config.get("git_commit")
    repr_commit = reproduced_run.config.get("git_commit")
    if orig_commit != repr_commit:
        issues.append(f"Git commit differs: {orig_commit} vs {repr_commit}")
    
    # Package versions
    orig_pkgs = original_run.config.get("package_versions", {})
    repr_pkgs = reproduced_run.config.get("package_versions", {})
    for pkg, ver in orig_pkgs.items():
        if repr_pkgs.get(pkg) != ver:
            issues.append(f"Package version mismatch: {pkg} {ver} vs {repr_pkgs.get(pkg)}")
    
    # Metric similarity
    for metric in ["faithfulness", "answer_relevancy", "latency_p95"]:
        orig_val = original_run.metrics.get(metric, [{}])[-1].value if original_run.metrics.get(metric) else None
        repr_val = reproduced_run.metrics.get(metric, [{}])[-1].value if reproduced_run.metrics.get(metric) else None
        if orig_val and repr_val and abs(orig_val - repr_val) > 0.05:
            issues.append(f"Metric drift: {metric} {orig_val} vs {repr_val} (>5%)")
    
    return ReproducibilityReport(
        reproducible=len(issues) == 0,
        issues=issues
    )
```

---

## Querying & Dashboard

### Search Syntax
```python
# MLflow search filter examples
filters = [
    "params.embedding_provider = 'openai'",
    "metrics.faithfulness > 0.8",
    "tags.pipeline = 'evaluation'",
    "attributes.start_time > '2024-01-01'",
    "params.chunking_strategy = 'semantic' AND metrics.latency_p95 < 3000",
]

# Combined
filter_str = " AND ".join(filters)
runs = tracker.search_runs(experiment_ids, filter=filter_str)
```

### Dashboard Metrics
```python
DASHBOARD_METRICS = [
    # Quality
    "eval/faithfulness",
    "eval/answer_relevancy", 
    "eval/context_precision",
    "eval/context_recall",
    "eval/hallucination_rate",
    "eval/citation_accuracy",
    
    # Performance
    "query/latency_p50",
    "query/latency_p95",
    "query/latency_p99",
    "query/tokens_total",
    "query/citations_count",
    
    # Retrieval
    "retrieval/dense_candidates",
    "retrieval/sparse_candidates",
    "retrieval/rerank_improvement",
    
    # System
    "ingestion/documents_per_minute",
    "ingestion/embedding_latency",
    "system/gpu_utilization",
]
```

---

## Configuration Summary

```python
class ExperimentSettings(BaseModel):
    # Tracker
    tracker: ExperimentTrackerType = ExperimentTrackerType.MLFLOW
    mlflow: MLflowConfig = MLflowConfig()
    wandb: WandbConfig = WandbConfig()
    
    # Behavior
    auto_track: bool = True
    track_queries: bool = False  # High volume, sample instead
    track_evaluations: bool = True
    track_ingestions: bool = True
    
    # Logging
    log_config: bool = True
    log_artifacts: bool = True
    log_model: bool = False
    log_system_metrics: bool = True
    
    # Sampling (for high-volume tracking)
    query_sample_rate: float = 0.01  # Track 1% of queries
    query_sample_min_per_minute: int = 10
```

---

## Best Practices

### 1. Experiment Naming
```
Format: {pipeline}-{purpose}-{variant}-{date}
Examples:
  ingestion-baseline-v1-20240115
  query-hybrid-rrf-v2-20240115
  evaluation-hotpotqa-rerank-cohere-20240115
```

### 2. Tagging Strategy
```python
REQUIRED_TAGS = {
    "pipeline": "ingestion|query|evaluation|experiment",
    "variant": "baseline|experiment|production",
    "environment": "dev|staging|prod",
    "team": "team-name",
}

OPTIONAL_TAGS = {
    "ticket": "JIRA-123",
    "hypothesis": "What we're testing",
    "reviewer": "username",
}
```

### 3. Metric Naming Convention
```
{stage}/{metric_name}
Examples:
  ingestion/throughput_docs_per_min
  retrieval/latency_p95_ms
  generation/tokens_per_second
  evaluation/faithfulness
  evaluation/hallucination_rate
```

### 4. Artifact Organization
```
artifacts/
└── {run_id}/
    ├── config.json
    ├── predictions.json
    ├── evaluation_report.html
    ├── model_checkpoint.pt
    ├── dataset_sample.parquet
    └── visualizations/
        ├── metric_comparison.png
        └── latency_distribution.png
```

---

## Integration with CI/CD

### GitHub Actions Workflow
```yaml
# .github/workflows/evaluation.yml
name: Evaluation
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 2 * * *'  # Daily

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run evaluation
        run: |
          python scripts/evaluation/run_eval.py \
            --dataset data/eval/hotpotqa.json \
            --track \
            --experiment-name ci-evaluation
      - name: Compare with baseline
        run: |
          python scripts/evaluation/compare_runs.py \
            --current-run ${{ github.run_id }} \
            --baseline-tag production \
            --threshold faithfulness:0.7,answer_relevancy:0.7
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            // Post evaluation results as PR comment
```

---

## Migration Between Trackers

### Unified Migration Script
```python
def migrate_experiments(
    source_tracker: ExperimentTracker,
    target_tracker: ExperimentTracker,
    experiment_names: list[str] = None
) -> MigrationReport:
    migrated = 0
    failed = 0
    
    for exp in source_tracker.list_experiments():
        if experiment_names and exp.name not in experiment_names:
            continue
        
        # Create target experiment
        target_exp_id = target_tracker.create_experiment(exp.name, exp.tags)
        
        for run in source_tracker.search_runs([exp.experiment_id]):
            try:
                # Start new run
                target_run = target_tracker.start_run(
                    target_exp_id, run.name, run.config, run.tags
                )
                
                # Migrate params
                target_tracker.log_params(target_run.run_id, run.params)
                
                # Migrate metrics
                for metric_name, points in run.metrics.items():
                    for point in points:
                        target_tracker.log_metrics(
                            target_run.run_id,
                            {metric_name: point.value},
                            step=point.step
                        )
                
                # Migrate artifacts (copy files)
                for artifact in run.artifacts:
                    # Download from source, upload to target
                    with tempfile.TemporaryDirectory() as tmp:
                        source_tracker.download_artifact(run.run_id, artifact.name, tmp)
                        target_tracker.log_artifact(
                            target_run.run_id,
                            f"{tmp}/{artifact.name}",
                            artifact.name,
                            artifact.type
                        )
                
                target_tracker.end_run(target_run.run_id, run.status)
                migrated += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate run {run.run_id}: {e}")
                failed += 1
    
    return MigrationReport(migrated=migrated, failed=failed)
```

---

## Testing Experiment Tracking

### Unit Tests
```python
def test_mlflow_tracker_log_params():
    tracker = MLflowTracker(MLflowConfig(tracking_uri="sqlite:///:memory:"))
    exp_id = tracker.create_experiment("test")
    run = tracker.start_run(exp_id, "test-run", {"param1": "value1"})
    
    tracker.log_params(run.run_id, {"param2": "value2"})
    tracker.end_run(run.run_id, RunStatus.COMPLETED)
    
    retrieved = tracker.get_run(run.run_id)
    assert retrieved.params["param1"] == "value1"
    assert retrieved.params["param2"] == "value2"

def test_wandb_tracker_log_metrics():
    tracker = WandbTracker(WandbConfig(mode="disabled"))
    exp_id = tracker.create_experiment("test")
    run = tracker.start_run(exp_id, "test-run", {})
    
    tracker.log_metrics(run.run_id, {"metric1": 0.5}, step=1)
    tracker.log_metrics(run.run_id, {"metric1": 0.7}, step=2)
    tracker.end_run(run.run_id, RunStatus.COMPLETED)
    
    # In disabled mode, just verify no exceptions

def test_config_snapshot_capture():
    config = capture_config_snapshot()
    assert config.python_version == sys.version
    assert "fastapi" in config.package_versions
    assert config.git_commit is not None or config.git_dirty is False
```

### Integration Tests
```python
async def test_full_experiment_tracking():
    tracker = TrackerFactory.create(settings.experiments)
    pipeline = TrackedPipeline(tracker, "test-exp", "query")
    
    async with pipeline.run("test-run", {"test": "config"}) as tracked:
        tracked.log_metrics({"test_metric": 0.95})
        tracked.log_artifact("/tmp/test.txt", "test.txt")
    
    # Verify run completed
    runs = tracker.search_runs([tracker.experiment_id], filter="tags.pipeline = 'query'")
    assert len(runs) == 1
    assert runs[0].status == RunStatus.COMPLETED
```