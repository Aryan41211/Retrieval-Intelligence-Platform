"""Orchestration runner for embedding validation framework."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding
from backend.embedding_validation.benchmark_report import BenchmarkReport
from backend.embedding_validation.duplicate_detector import (
    DuplicateDetector,
    DuplicateReport,
)
from backend.embedding_validation.embedding_benchmark import (
    BenchmarkResult,
    EmbeddingBenchmark,
)
from backend.embedding_validation.embedding_profiler import (
    EmbeddingProfiler,
    ProfilerMetrics,
)
from backend.embedding_validation.embedding_statistics import (
    EmbeddingQualityReport,
    EmbeddingStatistics,
)
from backend.embedding_validation.embedding_validator import (
    ExtendedEmbeddingValidator,
    ValidationResult,
)
from backend.embedding_validation.similarity_analyzer import (
    SimilarityAnalyzer,
    SimilarityMetrics,
)


@dataclass
class ValidationSummary:
    """Summary of validation results."""

    is_valid: bool = True
    total_chunks: int = 0
    total_embeddings: int = 0
    validation_result: ValidationResult | None = None
    quality_report: EmbeddingQualityReport | None = None
    similarity_metrics: SimilarityMetrics | None = None
    duplicate_report: DuplicateReport | None = None
    benchmark_result: BenchmarkResult | None = None
    profiler_metrics: ProfilerMetrics | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ValidationRunner:
    """Orchestrate embedding validation and benchmarking."""

    def __init__(
        self,
        expected_dimension: int | None = None,
        enable_benchmark: bool = True,
        enable_profiling: bool = True,
        enable_similarity_analysis: bool = True,
        enable_duplicate_detection: bool = True,
        near_duplicate_threshold: float = 0.99,
    ):
        self.validator = ExtendedEmbeddingValidator(expected_dimension=expected_dimension)
        self.statistics = EmbeddingStatistics()
        self.benchmark = EmbeddingBenchmark() if enable_benchmark else None
        self.profiler = EmbeddingProfiler() if enable_profiling else None
        self.similarity_analyzer = SimilarityAnalyzer() if enable_similarity_analysis else None
        self.duplicate_detector = (
            DuplicateDetector(threshold=near_duplicate_threshold)
            if enable_duplicate_detection
            else None
        )
        self._report = BenchmarkReport()

    def validate_and_benchmark(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        model_name: str = "unknown",
        model_version: str = "1.0",
        benchmark_runs: int = 1,
    ) -> ValidationSummary:
        """Run full validation and benchmark pipeline.

        Args:
            chunks: List of chunks to embed and validate.
            embed_fn: Function that takes chunks and returns embeddings.
            model_name: Name of the embedding model.
            model_version: Version of the embedding model.
            benchmark_runs: Number of benchmark runs.

        Returns:
            ValidationSummary with all results.
        """
        all_embeddings: list[Embedding] = []
        validation_result: ValidationResult | None = None
        quality_report: EmbeddingQualityReport | None = None
        similarity_metrics: SimilarityMetrics | None = None
        duplicate_report: DuplicateReport | None = None
        benchmark_result: BenchmarkResult | None = None
        profiler_metrics: ProfilerMetrics | None = None
        warnings: list[str] = []
        errors: list[str] = []

        if self.benchmark and benchmark_runs > 0:
            benchmark_result = self.benchmark.benchmark_batch(chunks, embed_fn)
            self._report.add_benchmark_result(f"benchmark_{model_name}", benchmark_result)

        if self.profiler:
            profiler_metrics = self.profiler.profile_batch(chunks, embed_fn)

        embeddings = embed_fn(chunks)
        all_embeddings.extend(embeddings)

        validation_result = self.validator.validate_all(all_embeddings)

        quality_report = self.statistics.generate_quality_report(
            all_embeddings, expected_dimension=self.validator.expected_dimension
        )
        self._report.add_statistics("quality", quality_report)

        if self.similarity_analyzer and len(all_embeddings) >= 2:
            similarity_metrics = self.similarity_analyzer.compute_similarity_metrics(
                all_embeddings
            )
            self._report.add_similarity_metrics("similarity", similarity_metrics)

            nn_stats = self.similarity_analyzer.compute_nearest_neighbor_stats(
                all_embeddings
            )
            if nn_stats.get("mean_nn_distance", 0) > 0.5:
                warnings.append(
                    f"High mean NN distance ({nn_stats['mean_nn_distance']:.3f}), "
                    "embeddings are well-separated"
                )

        if self.duplicate_detector and len(all_embeddings) >= 2:
            duplicate_report = self.duplicate_detector.generate_report(all_embeddings)
            self._report.add_duplicate_report("duplicates", duplicate_report)

        if not validation_result.is_valid:
            errors.extend(validation_result.errors)

        if benchmark_result and benchmark_result.errors:
            errors.extend(benchmark_result.errors)

        recommendations = list(quality_report.recommendations) if quality_report else []

        return ValidationSummary(
            is_valid=len(errors) == 0 and validation_result.is_valid,
            total_chunks=len(chunks),
            total_embeddings=len(all_embeddings),
            validation_result=validation_result,
            quality_report=quality_report,
            similarity_metrics=similarity_metrics,
            duplicate_report=duplicate_report,
            benchmark_result=benchmark_result,
            profiler_metrics=profiler_metrics,
            warnings=list(quality_report.warnings) if quality_report else [],
            errors=errors,
            recommendations=recommendations,
        )

    def save_reports(
        self,
        output_dir: str | Path,
        markdown_filename: str = "embedding_validation_report.md",
        json_filename: str = "embedding_validation_report.json",
    ) -> tuple[Path, Path]:
        """Save reports to files.

        Args:
            output_dir: Directory to save reports.
            markdown_filename: Markdown filename.
            json_filename: JSON filename.

        Returns:
            Tuple of (markdown_path, json_path).
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        md_path = output_path / markdown_filename
        json_path = output_path / json_filename

        self._report.save_markdown(md_path)
        self._report.save_json(json_path)

        return md_path, json_path

    def get_report(self) -> BenchmarkReport:
        """Get the underlying BenchmarkReport instance."""
        return self._report

    def reset(self) -> None:
        """Reset all collected state."""
        self.validator = ExtendedEmbeddingValidator(
            expected_dimension=self.validator.expected_dimension
        )
        self.statistics = EmbeddingStatistics()
        if self.profiler:
            self.profiler.reset()
        self._report = BenchmarkReport()
