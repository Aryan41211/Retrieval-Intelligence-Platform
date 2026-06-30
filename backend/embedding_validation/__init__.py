"""Embedding validation and benchmarking framework for the Retrieval Intelligence Platform.

This package provides:
- Embedding validation for quality control
- Statistics generation for embedding analysis
- Benchmarking for performance metrics
- Profiling for resource utilization
- Similarity analysis for semantic quality
- Duplicate detection for data integrity
- Visualization for embedding quality insights
- Report generation for validation results
- Orchestration runner for end-to-end validation
"""

from backend.embedding_validation.benchmark_report import BenchmarkReport
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
from backend.embedding_validation.embedding_profiler import EmbeddingProfiler, ProfilerMetrics
from backend.embedding_validation.embedding_statistics import (
    DensityStatistics,
    EmbeddingQualityReport,
    EmbeddingStatistics,
    EmbeddingStats,
    NormStatistics,
)
from backend.embedding_validation.embedding_validator import (
    ExtendedEmbeddingValidator,
    ValidationResult,
)
from backend.embedding_validation.embedding_visualizer import EmbeddingVisualizer
from backend.embedding_validation.similarity_analyzer import (
    SimilarityAnalyzer,
    SimilarityMetrics,
)
from backend.embedding_validation.validation_runner import (
    ValidationRunner,
    ValidationSummary,
)

__all__ = [
    "ExtendedEmbeddingValidator",
    "ValidationResult",
    "EmbeddingStatistics",
    "EmbeddingQualityReport",
    "NormStatistics",
    "DensityStatistics",
    "EmbeddingStats",
    "EmbeddingBenchmark",
    "BenchmarkResult",
    "LatencyMetrics",
    "ThroughputMetrics",
    "BatchMetrics",
    "ResourceMetrics",
    "EmbeddingProfiler",
    "ProfilerMetrics",
    "SimilarityAnalyzer",
    "SimilarityMetrics",
    "DuplicateDetector",
    "DuplicateReport",
    "EmbeddingVisualizer",
    "BenchmarkReport",
    "ValidationRunner",
    "ValidationSummary",
]
