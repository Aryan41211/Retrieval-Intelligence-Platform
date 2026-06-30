"""Benchmarking for embedding performance metrics."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding


@dataclass
class LatencyMetrics:
    """Latency metrics for embedding generation."""

    average_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)


@dataclass
class ThroughputMetrics:
    """Throughput metrics for embedding generation."""

    embeddings_per_second: float = 0.0
    chunks_per_second: float = 0.0
    batch_throughput_ms: float = 0.0


@dataclass
class BatchMetrics:
    """Metrics for batch processing."""

    total_batches: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    average_batch_size: float = 0.0


@dataclass
class ResourceMetrics:
    """Resource utilization metrics."""

    memory_usage_mb: float = 0.0
    cpu_utilization_percent: float = 0.0
    gpu_utilization_percent: float | None = None
    gpu_memory_mb: float | None = None


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""

    provider_name: str
    model_name: str
    model_version: str
    embedding_dimension: int
    total_embeddings: int
    total_chunks: int
    latency_metrics: LatencyMetrics = field(default_factory=LatencyMetrics)
    throughput_metrics: ThroughputMetrics = field(default_factory=ThroughputMetrics)
    batch_metrics: BatchMetrics = field(default_factory=BatchMetrics)
    resource_metrics: ResourceMetrics = field(default_factory=ResourceMetrics)
    cache_hits: int = 0
    cache_misses: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EmbeddingBenchmark:
    """Benchmark embedding generation performance."""

    def __init__(self, embedder: Callable | None = None):
        self.embedder = embedder
        self._latencies: list[float] = []
        self._batch_times: list[float] = []
        self._start_time: float = 0

    def benchmark_sequential(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
    ) -> BenchmarkResult:
        """Benchmark sequential embedding generation.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.

        Returns:
            BenchmarkResult with performance metrics.
        """
        latencies = []
        embeddings = []

        for chunk in chunks:
            start = time.perf_counter()
            try:
                result = embed_fn([chunk])
                embeddings.extend(result)
            except Exception:
                latencies.append(0.0)
            else:
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)

        return self._build_result(embeddings, len(chunks), latencies, [])

    def benchmark_batch(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        batch_size: int = 32,
    ) -> BenchmarkResult:
        """Benchmark batch embedding generation.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.
            batch_size: Batch size for processing.

        Returns:
            BenchmarkResult with performance metrics.
        """
        latencies = []
        embeddings = []
        batch_times: list[float] = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            start = time.perf_counter()
            try:
                result = embed_fn(batch)
                embeddings.extend(result)
            except Exception:
                latencies.extend([0.0] * len(batch))
            else:
                elapsed = (time.perf_counter() - start) * 1000
                batch_times.append(elapsed)
                per_item_latency = elapsed / len(batch) if batch else 0
                latencies.extend([per_item_latency] * len(batch))

        batch_metrics = BatchMetrics(
            total_batches=len(batch_times),
            successful_batches=len(batch_times),
            failed_batches=0,
            average_batch_size=batch_size if batch_times else 0,
        )

        return self._build_result(embeddings, len(chunks), latencies, batch_times, batch_metrics)

    def benchmark_warmup(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        warmup_runs: int = 3,
    ) -> BenchmarkResult:
        """Run warmup runs before actual benchmark.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.
            warmup_runs: Number of warmup runs.

        Returns:
            BenchmarkResult after warmup.
        """
        for _ in range(warmup_runs):
            try:
                embed_fn(chunks[: min(10, len(chunks))])
            except Exception:
                pass

        return self.benchmark_batch(chunks, embed_fn)

    def compute_latency_metrics(self, latencies: list[float]) -> LatencyMetrics:
        """Compute latency statistics from raw latency data."""
        if not latencies:
            return LatencyMetrics()

        latencies_array = np.array(latencies, dtype=np.float64)

        return LatencyMetrics(
            average_latency_ms=float(np.mean(latencies_array)),
            median_latency_ms=float(np.median(latencies_array)),
            p95_latency_ms=float(np.percentile(latencies_array, 95)),
            p99_latency_ms=float(np.percentile(latencies_array, 99)),
            min_latency_ms=float(np.min(latencies_array)),
            max_latency_ms=float(np.max(latencies_array)),
            latencies=latencies,
        )

    def compute_throughput_metrics(
        self,
        total_time_ms: float,
        total_embeddings: int,
        total_chunks: int,
    ) -> ThroughputMetrics:
        """Compute throughput metrics."""
        total_time_s = total_time_ms / 1000
        embeddings_per_s = total_embeddings / total_time_s if total_time_s > 0 else 0
        chunks_per_s = total_chunks / total_time_s if total_time_s > 0 else 0

        return ThroughputMetrics(
            embeddings_per_second=embeddings_per_s,
            chunks_per_second=chunks_per_s,
            batch_throughput_ms=total_time_ms,
        )

    def _build_result(
        self,
        embeddings: list[Embedding],
        total_chunks: int,
        latencies: list[float],
        batch_times: list[float],
        batch_metrics: BatchMetrics | None = None,
        cache_hits: int = 0,
        cache_misses: int = 0,
        errors: list[str] | None = None,
    ) -> BenchmarkResult:
        """Build BenchmarkResult from collected metrics."""
        latency_metrics = self.compute_latency_metrics(latencies)

        total_time = sum(latencies)
        throughput_metrics = self.compute_throughput_metrics(
            total_time, len(embeddings), total_chunks
        )

        model_name = ""
        model_version = ""
        dimension = 0
        provider_name = ""

        if embeddings:
            first = embeddings[0]
            model_name = first.model_name
            model_version = first.model_version
            dimension = first.embedding_dimension

        return BenchmarkResult(
            provider_name=provider_name,
            model_name=model_name,
            model_version=model_version,
            embedding_dimension=dimension,
            total_embeddings=len(embeddings),
            total_chunks=total_chunks,
            latency_metrics=latency_metrics,
            throughput_metrics=throughput_metrics,
            batch_metrics=batch_metrics or BatchMetrics(),
            resource_metrics=self._get_resource_metrics(),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            errors=errors or [],
        )

    def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource utilization metrics."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)

            return ResourceMetrics(
                memory_usage_mb=memory_mb,
                cpu_utilization_percent=cpu_percent,
            )
        except ImportError:
            return ResourceMetrics(
                memory_usage_mb=0.0,
                cpu_utilization_percent=0.0,
            )

    def get_cache_stats(self, cache_hits: int, cache_misses: int) -> dict[str, Any]:
        """Compute cache statistics."""
        total = cache_hits + cache_misses
        hit_rate = cache_hits / total if total > 0 else 0.0

        return {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total,
        }
