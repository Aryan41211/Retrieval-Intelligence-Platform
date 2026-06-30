"""Benchmark report generation in Markdown and JSON formats."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.embedding_validation.duplicate_detector import DuplicateReport
from backend.embedding_validation.embedding_benchmark import BenchmarkResult
from backend.embedding_validation.embedding_statistics import EmbeddingQualityReport
from backend.embedding_validation.similarity_analyzer import SimilarityMetrics


class BenchmarkReport:
    """Generate benchmark reports in multiple formats."""

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
        """Add a benchmark result to the report."""
        self.results[name] = result

    def add_statistics(self, name: str, stats: EmbeddingQualityReport) -> None:
        """Add statistics to the report."""
        self.statistics[name] = stats

    def add_similarity_metrics(self, name: str, metrics: SimilarityMetrics) -> None:
        """Add similarity metrics to the report."""
        self.similarity_metrics[name] = metrics

    def add_duplicate_report(self, name: str, report: DuplicateReport) -> None:
        """Add duplicate report to the report."""
        self.duplicate_reports[name] = report

    def generate_markdown(self) -> str:
        """Generate Markdown format report."""
        lines = [
            f"# {self.title}",
            "",
            f"**Generated:** {self.generated_at.isoformat()}",
            "",
        ]

        for name, result in self.results.items():
            lines.extend(self._format_benchmark_section(name, result))

        for name, stats in self.statistics.items():
            lines.extend(self._format_statistics_section(name, stats))

        lines.extend(self._format_recommendations())

        return "\n".join(lines)

    def generate_json(self) -> dict[str, Any]:
        """Generate JSON format report."""
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "benchmarks": {
                name: self._benchmark_to_dict(result)
                for name, result in self.results.items()
            },
            "statistics": {
                name: self._statistics_to_dict(stats)
                for name, stats in self.statistics.items()
            },
            "similarity_metrics": {
                name: self._similarity_to_dict(metrics)
                for name, metrics in self.similarity_metrics.items()
            },
            "duplicate_reports": {
                name: self._duplicate_to_dict(report)
                for name, report in self.duplicate_reports.items()
            },
        }

    def save_markdown(self, path: str | Path) -> None:
        """Save Markdown report to file."""
        Path(path).write_text(self.generate_markdown(), encoding="utf-8")

    def save_json(self, path: str | Path) -> None:
        """Save JSON report to file."""
        Path(path).write_text(
            json.dumps(self.generate_json(), indent=2),
            encoding="utf-8",
        )

    def _format_benchmark_section(self, name: str, result: BenchmarkResult) -> list[str]:
        lines = [
            f"## {name}",
            "",
            "### Model Information",
            f"- **Provider:** {result.provider_name}",
            f"- **Model:** {result.model_name}",
            f"- **Version:** {result.model_version}",
            f"- **Dimension:** {result.embedding_dimension}",
            "",
            "### Performance Metrics",
            f"- **Total Chunks:** {result.total_chunks}",
            f"- **Total Embeddings:** {result.total_embeddings}",
            f"- **Average Latency:** {result.latency_metrics.average_latency_ms:.2f} ms",
            f"- **Median Latency:** {result.latency_metrics.median_latency_ms:.2f} ms",
            f"- **P95 Latency:** {result.latency_metrics.p95_latency_ms:.2f} ms",
            f"- **P99 Latency:** {result.latency_metrics.p99_latency_ms:.2f} ms",
            "",
            "### Throughput",
            f"- **Embeddings/second:** {result.throughput_metrics.embeddings_per_second:.2f}",
            f"- **Chunks/second:** {result.throughput_metrics.chunks_per_second:.2f}",
            "",
            "### Cache Statistics",
            f"- **Hits:** {result.cache_hits}",
            f"- **Misses:** {result.cache_misses}",
            f"- **Hit Rate:** {result.cache_hits / (result.cache_hits + result.cache_misses) * 100:.1f}%"
            if (result.cache_hits + result.cache_misses) > 0
            else "- **Hit Rate:** N/A",
            "",
        ]

        if result.errors:
            lines.extend(["### Errors", "".join(f"- {e}\n" for e in result.errors)])

        return lines

    def _format_statistics_section(
        self, name: str, stats: EmbeddingQualityReport
    ) -> list[str]:
        lines = [
            f"## Statistics: {name}",
            "",
            "### Embedding Properties",
            f"- **Total Embeddings:** {stats.total_embeddings}",
            f"- **Dimension:** {stats.embedding_dimension}",
            "",
        ]

        if stats.norm_statistics:
            ns = stats.norm_statistics
            lines.extend(
                [
                    "### Norm Statistics",
                    f"- **Mean Norm:** {ns.mean_norm:.6f}",
                    f"- **Std Norm:** {ns.std_norm:.6f}",
                    f"- **Min Norm:** {ns.min_norm:.6f}",
                    f"- **Max Norm:** {ns.max_norm:.6f}",
                    "",
                ]
            )

        if stats.warnings:
            lines.extend(["### Warnings", "".join(f"- {w}\n" for w in stats.warnings)])

        return lines

    def _format_recommendations(self) -> list[str]:
        """Generate recommendations section."""
        recommendations: list[str] = []

        for _name, stats in self.statistics.items():
            recommendations.extend(stats.recommendations)

        if recommendations:
            return ["## Recommendations", "".join(f"- {r}\n" for r in recommendations)]

        return ["## Recommendations", "No recommendations at this time."]

    def _benchmark_to_dict(self, result: BenchmarkResult) -> dict[str, Any]:
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
            "cache": {
                "hits": result.cache_hits,
                "misses": result.cache_misses,
            },
            "errors": result.errors,
        }

    def _statistics_to_dict(self, stats: EmbeddingQualityReport) -> dict[str, Any]:
        return {
            "total_embeddings": stats.total_embeddings,
            "embedding_dimension": stats.embedding_dimension,
            "norm_statistics": (
                {
                    "mean_norm": stats.norm_statistics.mean_norm if stats.norm_statistics else 0,
                    "std_norm": stats.norm_statistics.std_norm if stats.norm_statistics else 0,
                }
                if stats.norm_statistics
                else None
            ),
            "similarity_distribution": stats.similarity_distribution,
            "warnings": stats.warnings,
            "recommendations": stats.recommendations,
        }

    def _similarity_to_dict(self, metrics: SimilarityMetrics) -> dict[str, Any]:
        return {
            "average_similarity": metrics.average_similarity,
            "median_similarity": metrics.median_similarity,
            "std_similarity": metrics.std_similarity,
            "similarity_distribution": metrics.similarity_distribution,
            "top_k_similarities": metrics.top_k_similarities,
        }

    def _duplicate_to_dict(self, report: DuplicateReport) -> dict[str, Any]:
        return {
            "total_checked": report.total_checked,
            "total_duplicates": report.total_duplicates,
            "duplicate_rate": report.duplicate_rate,
            "exact_duplicates": len(report.exact_duplicates),
            "near_duplicates": len(report.near_duplicates),
            "clusters": len(report.duplicate_clusters),
        }
