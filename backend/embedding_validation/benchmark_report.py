"""Benchmark report generation in Markdown and JSON formats.

Generates comprehensive reports containing:
- Model information (name, provider, version)
- Performance metrics (latency, throughput, cache stats)
- Similarity metrics (distribution, top-K, outliers)
- Validation summary (pass rates, errors, warnings)
- Actionable warnings and recommendations

Export formats: Markdown, JSON
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.embedding_validation.duplicate_detector import DuplicateReport
from backend.embedding_validation.embedding_benchmark import BenchmarkResult
from backend.embedding_validation.embedding_statistics import (
    EmbeddingQualityReport,
)
from backend.embedding_validation.similarity_analyzer import SimilarityMetrics


class BenchmarkReport:
    """Generate benchmark reports in multiple formats.

    Aggregates benchmark results, statistics, similarity metrics, and
    duplicate reports into cohesive Markdown and JSON documents.

    Usage:
        report = BenchmarkReport()
        report.add_benchmark_result("openai", benchmark_result)
        report.add_statistics("quality", stats_report)
        report.save_markdown("validation_report.md")
        report.save_json("validation_report.json")
    """

    def __init__(self, title: str = "Embedding Benchmark Report"):
        self.title = title
        self.generated_at = datetime.now(UTC)
        self.results: dict[str, BenchmarkResult] = {}
        self.statistics: dict[str, EmbeddingQualityReport] = {}
        self.similarity_metrics: dict[str, SimilarityMetrics] = {}
        self.duplicate_reports: dict[str, DuplicateReport] = {}

    def add_benchmark_result(
        self, name: str, result: BenchmarkResult
    ) -> None:
        """Add a benchmark result to the report.

        Args:
            name: Identifier for this benchmark (e.g., 'openai-small').
            result: BenchmarkResult with performance metrics.
        """
        self.results[name] = result

    def add_statistics(self, name: str, stats: EmbeddingQualityReport) -> None:
        """Add statistics to the report.

        Args:
            name: Identifier for this statistics set.
            stats: EmbeddingQualityReport with quality metrics.
        """
        self.statistics[name] = stats

    def add_similarity_metrics(
        self, name: str, metrics: SimilarityMetrics
    ) -> None:
        """Add similarity metrics to the report.

        Args:
            name: Identifier for this similarity analysis.
            metrics: SimilarityMetrics with similarity statistics.
        """
        self.similarity_metrics[name] = metrics

    def add_duplicate_report(
        self, name: str, report: DuplicateReport
    ) -> None:
        """Add duplicate report to the report.

        Args:
            name: Identifier for this duplicate analysis.
            report: DuplicateReport with duplicate detection results.
        """
        self.duplicate_reports[name] = report

    def generate_markdown(self) -> str:
        """Generate comprehensive Markdown format report.

        Returns:
            Complete Markdown string with all sections.
        """
        lines = [
            f"# {self.title}",
            "",
            f"**Generated:** {self.generated_at.isoformat()}",
            "",
            "---",
            "",
        ]

        # Benchmark results section
        if self.results:
            lines.append("## Benchmark Results")
            lines.append("")
            for name, result in self.results.items():
                lines.extend(self._format_benchmark_section(name, result))

        # Statistics section
        if self.statistics:
            lines.append("## Embedding Statistics")
            lines.append("")
            for name, stats in self.statistics.items():
                lines.extend(self._format_statistics_section(name, stats))

        # Similarity metrics section
        if self.similarity_metrics:
            lines.append("## Similarity Analysis")
            lines.append("")
            for name, metrics in self.similarity_metrics.items():
                lines.extend(
                    self._format_similarity_section(name, metrics)
                )

        # Duplicate detection section
        if self.duplicate_reports:
            lines.append("## Duplicate Detection")
            lines.append("")
            for name, report in self.duplicate_reports.items():
                lines.extend(self._format_duplicate_section(name, report))

        # Warnings section
        warnings_collected: list[str] = []
        for stats in self.statistics.values():
            warnings_collected.extend(stats.warnings)
        for result in self.results.values():
            warnings_collected.extend(result.warnings)

        if warnings_collected:
            lines.append("## Warnings")
            lines.append("")
            for w in warnings_collected:
                lines.append(f"- {w}")
            lines.append("")

        # Recommendations section
        lines.extend(self._format_recommendations())

        return "\n".join(lines)

    def generate_json(self) -> dict[str, Any]:
        """Generate JSON format report.

        Returns:
            Dictionary with all report data structured for JSON serialization.
        """
        data: dict[str, Any] = {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "report_type": "embedding_benchmark",
        }

        if self.results:
            data["benchmarks"] = {
                name: self._benchmark_to_dict(result)
                for name, result in self.results.items()
            }

        if self.statistics:
            data["statistics"] = {
                name: self._statistics_to_dict(stats)
                for name, stats in self.statistics.items()
            }

        if self.similarity_metrics:
            data["similarity_metrics"] = {
                name: self._similarity_to_dict(metrics)
                for name, metrics in self.similarity_metrics.items()
            }

        if self.duplicate_reports:
            data["duplicate_reports"] = {
                name: self._duplicate_to_dict(report)
                for name, report in self.duplicate_reports.items()
            }

        # Collect all warnings and recommendations
        all_warnings: list[str] = []
        all_recommendations: list[str] = []
        for stats in self.statistics.values():
            all_warnings.extend(stats.warnings)
            all_recommendations.extend(stats.recommendations)
        for result in self.results.values():
            all_warnings.extend(result.warnings)

        if all_warnings:
            data["warnings"] = all_warnings
        if all_recommendations:
            data["recommendations"] = all_recommendations

        return data

    def save_markdown(self, path: str | Path) -> None:
        """Save Markdown report to file.

        Args:
            path: File path for the Markdown output.
        """
        Path(path).write_text(self.generate_markdown(), encoding="utf-8")

    def save_json(self, path: str | Path) -> None:
        """Save JSON report to file.

        Args:
            path: File path for the JSON output.
        """
        Path(path).write_text(
            json.dumps(self.generate_json(), indent=2, default=str),
            encoding="utf-8",
        )

    def _format_benchmark_section(
        self, name: str, result: BenchmarkResult
    ) -> list[str]:
        """Format a single benchmark result as Markdown lines."""
        lines = [
            f"### {name}",
            "",
            "#### Model Information",
            f"- **Provider:** {result.provider_name or 'N/A'}",
            f"- **Model:** {result.model_name or 'N/A'}",
            f"- **Version:** {result.model_version or 'N/A'}",
            f"- **Dimension:** {result.embedding_dimension}",
            "",
            "#### Performance Metrics",
            f"- **Total Chunks:** {result.total_chunks}",
            f"- **Total Embeddings:** {result.total_embeddings}",
            f"- **Average Latency:** {result.latency_metrics.average_latency_ms:.2f} ms",
            f"- **Median Latency:** {result.latency_metrics.median_latency_ms:.2f} ms",
            f"- **P95 Latency:** {result.latency_metrics.p95_latency_ms:.2f} ms",
            f"- **P99 Latency:** {result.latency_metrics.p99_latency_ms:.2f} ms",
            f"- **Min Latency:** {result.latency_metrics.min_latency_ms:.2f} ms",
            f"- **Max Latency:** {result.latency_metrics.max_latency_ms:.2f} ms",
            "",
            "#### Throughput",
            f"- **Embeddings/second:** {result.throughput_metrics.embeddings_per_second:.2f}",
            f"- **Chunks/second:** {result.throughput_metrics.chunks_per_second:.2f}",
            "",
            "#### Resource Utilization",
            f"- **Memory Usage:** {result.resource_metrics.memory_usage_mb:.1f} MB",
            f"- **CPU Utilization:** {result.resource_metrics.cpu_utilization_percent:.1f}%",
        ]

        if result.resource_metrics.gpu_detected:
            lines.extend([
                f"- **GPU Utilization:** {result.resource_metrics.gpu_utilization_percent or 'N/A'}",
                f"- **GPU Memory:** {result.resource_metrics.gpu_memory_mb or 'N/A'} MB",
            ])

        lines.extend([
            "",
            "#### Cache Statistics",
        ])

        total_cache = result.cache_hits + result.cache_misses
        if total_cache > 0:
            lines.extend([
                f"- **Hits:** {result.cache_hits}",
                f"- **Misses:** {result.cache_misses}",
                f"- **Hit Rate:** {result.cache_hit_rate * 100:.1f}%",
            ])
        else:
            lines.append("- **Hit Rate:** N/A (no cache data)")

        if result.errors:
            lines.extend([
                "",
                "#### Errors",
                *[f"- {e}" for e in result.errors],
            ])

        if result.warnings:
            lines.extend([
                "",
                "#### Warnings",
                *[f"- {w}" for w in result.warnings],
            ])

        lines.append("")
        return lines

    def _format_statistics_section(
        self, name: str, stats: EmbeddingQualityReport
    ) -> list[str]:
        """Format a statistics report as Markdown lines."""
        lines = [
            f"### Statistics: {name}",
            "",
            "#### Embedding Properties",
            f"- **Total Embeddings:** {stats.total_embeddings}",
            f"- **Dimension:** {stats.embedding_dimension}",
            "",
            "#### Quality Metrics",
            f"- **Average Norm:** {stats.average_norm:.6f}",
            f"- **Norm Std Dev:** {stats.norm_std_dev:.6f}",
            f"- **Duplicate Rate:** {stats.duplicate_percentage:.2f}%",
            f"- **Invalid Rate:** {stats.invalid_embedding_percentage:.2f}%",
            f"- **Validation Pass Rate:** {stats.validation_pass_rate:.2f}%",
            "",
        ]

        if stats.norm_statistics:
            ns = stats.norm_statistics
            lines.extend([
                "#### Norm Statistics",
                f"- **Mean Norm:** {ns.mean_norm:.6f}",
                f"- **Std Norm:** {ns.std_norm:.6f}",
                f"- **Min Norm:** {ns.min_norm:.6f}",
                f"- **Max Norm:** {ns.max_norm:.6f}",
                "",
            ])

        if stats.similarity_distribution:
            sd = stats.similarity_distribution
            lines.extend([
                "#### Similarity Distribution",
                f"- **Mean Similarity:** {sd.get('mean', 0):.6f}",
                f"- **Std Similarity:** {sd.get('std', 0):.6f}",
                f"- **Median Similarity:** {sd.get('median', 0):.6f}",
                f"- **P95 Similarity:** {sd.get('p95', 0):.6f}",
                f"- **P99 Similarity:** {sd.get('p99', 0):.6f}",
                f"- **High Similarity Ratio:** {sd.get('high_similarity_ratio', 0):.2%}",
                "",
            ])

        if stats.warnings:
            lines.extend([
                "#### Warnings",
                *[f"- {w}" for w in stats.warnings],
                "",
            ])

        return lines

    def _format_similarity_section(
        self, name: str, metrics: SimilarityMetrics
    ) -> list[str]:
        """Format similarity metrics as Markdown lines."""
        lines = [
            f"### Similarity: {name}",
            "",
            "#### Similarity Statistics",
            f"- **Average Similarity:** {metrics.average_similarity:.6f}",
            f"- **Median Similarity:** {metrics.median_similarity:.6f}",
            f"- **Std Similarity:** {metrics.std_similarity:.6f}",
            f"- **Similarity Variance:** {metrics.similarity_variance:.6f}",
            f"- **Min Similarity:** {metrics.min_similarity:.6f}",
            f"- **Max Similarity:** {metrics.max_similarity:.6f}",
            "",
            "#### Distribution",
            *[
                f"- **{bin_name}:** {count}"
                for bin_name, count in sorted(
                    metrics.similarity_distribution.items()
                )
            ],
            "",
            "#### Top-K Similarities",
            *[
                f"- **Top-{k}:** {avg:.6f}"
                for k, avg in sorted(metrics.top_k_similarities.items())
            ],
            "",
            "#### Anomaly Detection",
            f"- **Outlier Count:** {metrics.outlier_count}",
            f"- **Embedding Density:** {metrics.embedding_density:.6f}",
            f"- **Duplicate Clusters:** {metrics.duplicate_clusters}",
            "",
        ]
        return lines

    def _format_duplicate_section(
        self, name: str, report: DuplicateReport
    ) -> list[str]:
        """Format duplicate report as Markdown lines."""
        lines = [
            f"### Duplicates: {name}",
            "",
            f"- **Total Checked:** {report.total_checked}",
            f"- **Total Duplicates:** {report.total_duplicates}",
            f"- **Duplicate Rate:** {report.duplicate_rate:.4%}",
            f"- **Exact Duplicates:** {report.exact_duplicate_count}",
            f"- **Near Duplicates:** {report.near_duplicate_count}",
            f"- **Duplicate Clusters:** {report.cluster_count}",
            "",
        ]
        return lines

    def _format_recommendations(self) -> list[str]:
        """Generate recommendations section.

        Collects recommendations from all statistics and deduplicates them.

        Returns:
            List of Markdown lines for the recommendations section.
        """
        recommendations: list[str] = []
        seen: set[str] = set()

        for _name, stats in self.statistics.items():
            for rec in stats.recommendations:
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

        for _name, result in self.results.items():
            for rec in result.warnings:
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

        lines = ["## Recommendations", ""]
        if recommendations:
            lines.extend(f"- {r}" for r in recommendations)
        else:
            lines.append("No recommendations at this time.")
        lines.append("")

        return lines

    def _benchmark_to_dict(
        self, result: BenchmarkResult
    ) -> dict[str, Any]:
        """Convert BenchmarkResult to JSON-compatible dictionary."""
        return {
            "provider_name": result.provider_name,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "embedding_dimension": result.embedding_dimension,
            "total_embeddings": result.total_embeddings,
            "total_chunks": result.total_chunks,
            "latency_ms": {
                "average": result.latency_metrics.average_latency_ms,
                "median": result.latency_metrics.median_latency_ms,
                "p95": result.latency_metrics.p95_latency_ms,
                "p99": result.latency_metrics.p99_latency_ms,
                "min": result.latency_metrics.min_latency_ms,
                "max": result.latency_metrics.max_latency_ms,
            },
            "throughput": {
                "embeddings_per_second": result.throughput_metrics.embeddings_per_second,
                "chunks_per_second": result.throughput_metrics.chunks_per_second,
            },
            "batch_metrics": {
                "total_batches": result.batch_metrics.total_batches,
                "successful_batches": result.batch_metrics.successful_batches,
                "failed_batches": result.batch_metrics.failed_batches,
                "average_batch_size": result.batch_metrics.average_batch_size,
            },
            "resource_metrics": {
                "memory_usage_mb": result.resource_metrics.memory_usage_mb,
                "cpu_utilization_percent": result.resource_metrics.cpu_utilization_percent,
                "gpu_detected": result.resource_metrics.gpu_detected,
                "gpu_utilization_percent": result.resource_metrics.gpu_utilization_percent,
                "gpu_memory_mb": result.resource_metrics.gpu_memory_mb,
            },
            "cache": {
                "hits": result.cache_hits,
                "misses": result.cache_misses,
                "hit_rate": result.cache_hit_rate,
            },
            "errors": result.errors,
            "warnings": result.warnings,
        }

    def _statistics_to_dict(
        self, stats: EmbeddingQualityReport
    ) -> dict[str, Any]:
        """Convert EmbeddingQualityReport to JSON-compatible dictionary."""
        data: dict[str, Any] = {
            "total_embeddings": stats.total_embeddings,
            "embedding_dimension": stats.embedding_dimension,
            "average_norm": stats.average_norm,
            "norm_std_dev": stats.norm_std_dev,
            "duplicate_percentage": stats.duplicate_percentage,
            "invalid_embedding_percentage": stats.invalid_embedding_percentage,
            "validation_pass_rate": stats.validation_pass_rate,
            "similarity_distribution": stats.similarity_distribution,
            "warnings": stats.warnings,
            "recommendations": stats.recommendations,
        }

        if stats.norm_statistics:
            data["norm_statistics"] = {
                "mean_norm": stats.norm_statistics.mean_norm,
                "std_norm": stats.norm_statistics.std_norm,
                "min_norm": stats.norm_statistics.min_norm,
                "max_norm": stats.norm_statistics.max_norm,
            }

        if stats.value_statistics:
            data["value_statistics"] = {
                "mean": stats.value_statistics.mean,
                "std": stats.value_statistics.std,
                "min": stats.value_statistics.min,
                "max": stats.value_statistics.max,
            }

        return data

    def _similarity_to_dict(
        self, metrics: SimilarityMetrics
    ) -> dict[str, Any]:
        """Convert SimilarityMetrics to JSON-compatible dictionary."""
        return {
            "average_similarity": metrics.average_similarity,
            "median_similarity": metrics.median_similarity,
            "std_similarity": metrics.std_similarity,
            "similarity_variance": metrics.similarity_variance,
            "min_similarity": metrics.min_similarity,
            "max_similarity": metrics.max_similarity,
            "similarity_distribution": metrics.similarity_distribution,
            "top_k_similarities": metrics.top_k_similarities,
            "outlier_count": metrics.outlier_count,
            "embedding_density": metrics.embedding_density,
            "duplicate_clusters": metrics.duplicate_clusters,
        }

    def _duplicate_to_dict(
        self, report: DuplicateReport
    ) -> dict[str, Any]:
        """Convert DuplicateReport to JSON-compatible dictionary."""
        return {
            "total_checked": report.total_checked,
            "total_duplicates": report.total_duplicates,
            "duplicate_rate": report.duplicate_rate,
            "exact_duplicates": report.exact_duplicate_count,
            "near_duplicates": report.near_duplicate_count,
            "clusters": report.cluster_count,
        }