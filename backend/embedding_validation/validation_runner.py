"""Orchestration runner for embedding validation, benchmarking, and reporting.

This module provides a comprehensive runner that coordinates:
- Embedding validation (quality checks)
- Performance benchmarking
- Resource profiling
- Report generation

Integrates all framework components for end-to-end validation workflows.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding
from backend.embedding_validation.benchmark_report import BenchmarkReport
from backend.embedding_validation.embedding_benchmark import EmbeddingBenchmark
from backend.embedding_validation.embedding_profiler import EmbeddingProfiler
from backend.embedding_validation.embedding_statistics import EmbeddingStatistics
from backend.embedding_validation.embedding_validator import EmbeddingValidator
from backend.embedding_validation.similarity_analyzer import SimilarityAnalyzer
from backend.embedding_validation.validation_result import ValidationResult


@dataclass
class ValidationSummary:
    """Summary of validation results for embeddings."""

    is_valid: bool = True
    total_embeddings: int = 0
    valid_embeddings: int = 0
    invalid_embeddings: int = 0
    total_chunks: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ValidationRunner:
    """Orchestrate embedding validation with optional benchmarking and profiling.

    Coordinates the complete validation pipeline including quality checks,
    performance benchmarking, resource profiling, and report generation.

    Usage:
        runner = ValidationRunner(expected_dimension=1536, enable_benchmark=True)
        summary = runner.validate_and_benchmark(chunks, embed_fn)
        runner.save_reports("output/")
    """

    def __init__(
        self,
        expected_dimension: int | None = None,
        allow_nan: bool = False,
        allow_inf: bool = False,
        strict_mode: bool = False,
        enable_benchmark: bool = False,
        enable_profiling: bool = False,
    ):
        self.validator = EmbeddingValidator(
            expected_dimension=expected_dimension,
            allow_nan=allow_nan,
            allow_inf=allow_inf,
            strict_mode=strict_mode,
        )
        self.enable_benchmark = enable_benchmark
        self.enable_profiling = enable_profiling

        self._benchmark = EmbeddingBenchmark() if enable_benchmark else None
        self._profiler = EmbeddingProfiler() if enable_profiling else None
        self._report = BenchmarkReport()
        self._last_summary: ValidationSummary | None = None

    def validate(self, embeddings: list[Embedding]) -> ValidationSummary:
        """Run validation on embeddings.

        Args:
            embeddings: List of embeddings to validate.

        Returns:
            ValidationSummary with all validation findings.
        """
        result = self.validator.validate_all(embeddings)

        recommendations = self._generate_recommendations(result)

        self._last_summary = ValidationSummary(
            is_valid=result.is_valid,
            total_embeddings=result.total_embeddings,
            valid_embeddings=result.valid_embeddings,
            invalid_embeddings=result.invalid_embeddings,
            errors=result.errors,
            warnings=result.warnings,
            recommendations=recommendations,
        )

        return self._last_summary

    def validate_and_benchmark(
        self,
        chunks: list[Chunk],
        embed_fn: Any,
    ) -> ValidationSummary:
        """Run validation and benchmarking on chunks.

        Generates embeddings via embed_fn, validates them, and optionally
        runs performance benchmarking and profiling.

        Args:
            chunks: List of chunks to embed and validate.
            embed_fn: Function that takes chunks and returns embeddings.

        Returns:
            ValidationSummary with validation and benchmark results.
        """
        # Generate embeddings
        embeddings = embed_fn(chunks)

        # Run validation
        val_summary = self.validate(embeddings)
        val_summary.total_chunks = len(chunks)

        # Get validation result for statistics
        validation_result = self.validator.validate_all(embeddings)

        # Run benchmark if enabled
        if self.enable_benchmark and self._benchmark:
            benchmark_result = self._benchmark.benchmark_batch(
                chunks, embed_fn, provider_name="benchmarked-provider"
            )
            self._report.add_benchmark_result("benchmark", benchmark_result)

        # Run profiler if enabled
        if self.enable_profiling and self._profiler:
            self._profiler.profile_batch(chunks, embed_fn)

        # Add statistics to report
        stats = EmbeddingStatistics(embeddings)
        stats_report = stats.generate_quality_report(
            embeddings,
            duplicate_count=validation_result.duplicate_count,
            invalid_count=validation_result.invalid_embeddings,
            total_validated=len(embeddings),
        )
        self._report.add_statistics("quality", stats_report)

        # Add similarity metrics
        analyzer = SimilarityAnalyzer()
        sim_metrics = analyzer.compute_similarity_metrics(embeddings)
        self._report.add_similarity_metrics("similarity", sim_metrics)

        return val_summary

    def save_reports(self, output_dir: str | Path) -> tuple[Path, Path]:
        """Save benchmark reports to files.

        Args:
            output_dir: Directory to save reports.

        Returns:
            Tuple of (markdown_path, json_path).
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        md_path = output_path / "validation_report.md"
        json_path = output_path / "validation_report.json"

        self._report.save_markdown(md_path)
        self._report.save_json(json_path)

        return md_path, json_path

    def get_report(self) -> BenchmarkReport:
        """Get the current benchmark report.

        Returns:
            BenchmarkReport with all collected data.
        """
        return self._report

    def reset(self) -> None:
        """Reset runner state.

        Clears all collected data for a fresh validation run.
        """
        self._report = BenchmarkReport()
        self._last_summary = None
        if self._profiler:
            self._profiler.reset()

    def _generate_recommendations(self, result: ValidationResult) -> list[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        if result.nan_count > 0:
            recommendations.append(
                f"Found {result.nan_count} NaN values. Consider enabling data cleaning."
            )
        if result.inf_count > 0:
            recommendations.append(
                f"Found {result.inf_count} infinite values. Check embedding range."
            )
        if result.zero_vector_count > 0:
            recommendations.append(
                f"Found {result.zero_vector_count} zero vectors. "
                "Review source content for empty chunks."
            )
        if result.duplicate_count > 0:
            recommendations.append(
                f"Found {result.duplicate_count} duplicate embeddings. "
                "Check for duplicate source documents."
            )
        return recommendations

    def validate_single(self, embedding: Embedding) -> ValidationResult:
        """Validate a single embedding.

        Args:
            embedding: Embedding to validate.

        Returns:
            ValidationResult for the single embedding.
        """
        return self.validator.validate(embedding)
