# Embedding Validation & Benchmarking Framework

## Overview

The `backend/embedding_validation/` module provides a production-grade validation framework that verifies embedding quality before they are indexed into any vector database.

## Module Structure

```
backend/embedding_validation/
├── __init__.py                  # Package exports
├── embedding_validator.py       # Extended validation (ExtendedEmbeddingValidator, ValidationResult)
├── embedding_statistics.py      # Statistics generation (EmbeddingStatistics, EmbeddingQualityReport)
├── embedding_benchmark.py       # Performance benchmarking (EmbeddingBenchmark, BenchmarkResult)
├── embedding_profiler.py        # Resource profiling (EmbeddingProfiler, ProfilerMetrics)
├── similarity_analyzer.py       # Similarity analysis (SimilarityAnalyzer, SimilarityMetrics)
├── duplicate_detector.py        # Duplicate/near-duplicate detection (DuplicateDetector, DuplicateReport)
├── embedding_visualizer.py      # Visualization data generation (EmbeddingVisualizer)
├── benchmark_report.py          # Report generation (BenchmarkReport)
└── validation_runner.py         # Orchestration runner (ValidationRunner, ValidationSummary)
```

## Validation Workflow

The validation workflow processes embeddings through multiple quality checks:

1. **Numeric Validation** - Checks that vectors contain only numeric values
2. **NaN/Inf Detection** - Detects NaN and Infinity values with configurable tolerance
3. **Zero Vector Detection** - Identifies zero vectors
4. **Dimension Validation** - Verifies expected dimensions
5. **Normalization Check** - Detects non-normalized vectors
6. **Duplicate Detection** - Finds exact and near-duplicate embeddings

```python
from backend.embedding_validation import ExtendedEmbeddingValidator

validator = ExtendedEmbeddingValidator(expected_dimension=1536)
result = validator.validate_all(embeddings)

if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
```

## Benchmark Workflow

The benchmarking workflow measures embedding generation performance:

1. **Sequential Benchmarking** - Measures per-chunk latency
2. **Batch Benchmarking** - Measures batch throughput
3. **Warmup Runs** - Optional warmup before benchmarking

```python
from backend.embedding_validation import EmbeddingBenchmark

benchmark = EmbeddingBenchmark()
result = benchmark.benchmark_batch(chunks, embed_fn, batch_size=32)

print(f"Average latency: {result.latency_metrics.average_latency_ms:.2f}ms")
print(f"Throughput: {result.throughput_metrics.embeddings_per_second:.2f} embeddings/sec")
```

## Statistics Generation

The statistics module computes embedding quality metrics:

- **Norm Statistics** - Mean, std, min, max of vector norms
- **Value Statistics** - Distribution of embedding values
- **Density Statistics** - Sparsity and outlier detection
- **Similarity Distribution** - Pairwise similarity distribution

```python
from backend.embedding_validation import EmbeddingStatistics

stats = EmbeddingStatistics()
report = stats.generate_quality_report(embeddings, expected_dimension=100)

print(f"Mean norm: {report.norm_statistics.mean_norm}")
print(f"Warnings: {report.warnings}")
```

## Similarity Analysis

The similarity analyzer provides semantic quality assessment:

- **Pairwise Similarities** - Full similarity matrix
- **Top-K Similar** - Nearest neighbors for each embedding
- **Nearest Neighbor Stats** - Distribution of NN distances
- **Outlier Detection** - Identifies anomalous embeddings
- **Cluster Quality** - Estimates embedding diversity

```python
from backend.embedding_validation import SimilarityAnalyzer

analyzer = SimilarityAnalyzer()
metrics = analyzer.compute_similarity_metrics(embeddings)

print(f"Average similarity: {metrics.average_similarity}")
print(f"Embedding diversity: {metrics.embedding_diversity}")
```

## Profiling

The profiler captures resource utilization:

- **Latency Samples** - Per-embedding generation time
- **Memory Samples** - RSS memory usage over time
- **CPU Samples** - CPU utilization percentage
- **GPU Detection** - Optional GPU metrics (if available)

```python
from backend.embedding_validation import EmbeddingProfiler

profiler = EmbeddingProfiler()
metrics = profiler.profile_batch(chunks, embed_fn)

print(f"Peak memory: {max(metrics.memory_samples_mb):.1f}MB")
```

## Duplicate Detection

Detects data integrity issues in embeddings:

- **Exact Duplicates** - Same checksum detection
- **Near Duplicates** - High similarity detection (configurable threshold)
- **Cluster Grouping** - Groups duplicates into clusters

```python
from backend.embedding_validation import DuplicateDetector

detector = DuplicateDetector(threshold=0.99)
report = detector.generate_report(embeddings)

print(f"Duplicate rate: {report.duplicate_rate:.2%}")
```

## Report Generation

Generates Markdown and JSON reports:

```python
from backend.embedding_validation import BenchmarkReport

report = BenchmarkReport()
report.add_benchmark_result("openai-small", benchmark_result)
report.add_statistics("quality", stats_report)

report.save_markdown("validation_report.md")
report.save_json("validation_report.json")
```

## Orchestration

The `ValidationRunner` coordinates all components:

```python
from backend.embedding_validation import ValidationRunner

runner = ValidationRunner(expected_dimension=1536)
summary = runner.validate_and_benchmark(chunks, embed_fn)

runner.save_reports("output/")
```

## Extension Points

### Adding New Validation Checks

Extend `ExtendedEmbeddingValidator` with additional validation methods:

```python
class CustomValidator(ExtendedEmbeddingValidator):
    def validate_custom(self, embedding: Embedding) -> list[str]:
        # Custom validation logic
        pass
```

### Adding New Similarity Metrics

Extend `SimilarityAnalyzer` with custom metrics:

```python
class CustomSimilarityAnalyzer(SimilarityAnalyzer):
    def compute_custom_metric(self, embeddings: list[Embedding]) -> float:
        # Custom similarity metric
        pass
```

### Adding New Profilers

Implement the profiling interface for custom resource monitoring:

```python
class CustomProfiler(EmbeddingProfiler):
    def _sample_resources(self) -> None:
        # Custom sampling logic
        pass
```

## Configuration

All components accept configuration via constructor parameters:

- `expected_dimension` - Expected embedding dimension
- `near_duplicate_threshold` - Similarity threshold for near-duplicate detection
- `batch_size` - Batch size for benchmarking
- `allow_nan` / `allow_inf` - Tolerance for special values

See individual module docstrings for complete configuration options.