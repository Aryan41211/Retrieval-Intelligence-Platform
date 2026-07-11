"""Embedding validation core framework for the Retrieval Intelligence Platform.

This package provides:
- Embedding validation for quality control
- Structured validation results
- Duplicate detection for data integrity
- Performance benchmarking and profiling
- Similarity analysis and outlier detection
- Comprehensive benchmark reports

Phase 4.2 - Embedding Benchmarking & Performance Analysis:
- embedding_statistics: Norm statistics, similarity distribution, quality reports
- embedding_benchmark: Latency/throughput benchmarking with provider support
- embedding_profiler: Resource profiling (CPU, memory, GPU)
- similarity_analyzer: Cosine similarity, top-K, outlier detection, density stats
- duplicate_detector: Exact and near-duplicate detection
- benchmark_report: Markdown and JSON report generation
"""

from backend.embedding_validation.benchmark_report import (
    BenchmarkReport,
)
from backend.embedding_validation.duplicate_detector import (
    DuplicateDetector,
    DuplicateReport,
)
from backend.embedding_validation.embedding_benchmark import (
    BatchMetrics,
    BenchmarkResult,
    EmbeddingBenchmark,
    LatencyMetrics,
    ResourceMetrics,
    ThroughputMetrics,
)
from backend.embedding_validation.embedding_profiler import (
    EmbeddingProfiler,
    ProfilerMetrics,
)
from backend.embedding_validation.embedding_statistics import (
    DensityStatistics,
    EmbeddingQualityReport,
    EmbeddingStatistics,
    EmbeddingStats,
    NormStatistics,
)
from backend.embedding_validation.embedding_validator import EmbeddingValidator
from backend.embedding_validation.exceptions import (
    DuplicateEmbeddingError,
    InvalidEmbeddingMetadataError,
)
from backend.embedding_validation.similarity_analyzer import (
    SimilarityAnalyzer,
    SimilarityMetrics,
)
from backend.embedding_validation.validation_result import (
    ValidationCheckResult,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from backend.embedding_validation.validation_runner import (
    ValidationRunner,
    ValidationSummary,
)

# Backward compatibility alias
ExtendedEmbeddingValidator = EmbeddingValidator

__all__ = [
    # Validators
    "EmbeddingValidator",
    "ExtendedEmbeddingValidator",
    "ValidationRunner",
    "ValidationSummary",
    # Validation Results
    "ValidationResult",
    "ValidationCheckResult",
    "ValidationStatus",
    "ValidationSeverity",
    # Statistics
    "EmbeddingStatistics",
    "EmbeddingStats",
    "NormStatistics",
    "DensityStatistics",
    "EmbeddingQualityReport",
    # Benchmarking
    "EmbeddingBenchmark",
    "BenchmarkResult",
    "LatencyMetrics",
    "ThroughputMetrics",
    "BatchMetrics",
    "ResourceMetrics",
    # Profiling
    "EmbeddingProfiler",
    "ProfilerMetrics",
    # Similarity Analysis
    "SimilarityAnalyzer",
    "SimilarityMetrics",
    # Duplicate Detection
    "DuplicateDetector",
    "DuplicateReport",
    # Reports
    "BenchmarkReport",
    # Exceptions
    "DuplicateEmbeddingError",
    "InvalidEmbeddingMetadataError",
]
