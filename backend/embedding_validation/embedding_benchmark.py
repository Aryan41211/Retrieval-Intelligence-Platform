"""Benchmarking for embedding performance metrics.

Measures:
- Embedding generation latency (average, median, P95, P99)
- Throughput (embeddings/sec, chunks/sec)
- Cache hit rate
- Memory usage
- CPU/GPU utilization

Supports benchmarking different embedding providers through the existing
provider abstraction.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding


@dataclass
class LatencyMetrics:
    """Latency metrics for embedding generation.

    Contains comprehensive latency statistics including distribution percentiles.
    """

    average_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)


@dataclass
class ThroughputMetrics:
    """Throughput metrics for embedding generation.

    Measures embeddings generated per second and batch processing throughput.
    """

    embeddings_per_second: float = 0.0
    chunks_per_second: float = 0.0
    batch_throughput_ms: float = 0.0


@dataclass
class BatchMetrics:
    """Metrics for batch processing performance.

    Tracks batch success/failure counts and average batch sizes.
    """

    total_batches: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    average_batch_size: float = 0.0


@dataclass
class ResourceMetrics:
    """Resource utilization metrics during benchmarking.

    Captures memory, CPU, and optional GPU utilization.
    """

    memory_usage_mb: float = 0.0
    cpu_utilization_percent: float = 0.0
    gpu_utilization_percent: float | None = None
    gpu_memory_mb: float | None = None
    gpu_detected: bool = False


@dataclass
class BenchmarkResult:
    """Complete benchmark result with all performance metrics.

    Contains model information, latency/throughput metrics, batch statistics,
    resource utilization, cache stats, and any errors/warnings encountered.
    """

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
    cache_hit_rate: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EmbeddingBenchmark:
    """Benchmark embedding generation performance.

    Supports sequential, batch, and warmup benchmarking modes.
    Can benchmark any embedding provider through the Callable interface.

    Usage:
        benchmark = EmbeddingBenchmark()
        result = benchmark.benchmark_batch(chunks, embed_fn, batch_size=32)
        print(f"Average latency: {result.latency_metrics.average_latency_ms:.2f}ms")
    """

    def __init__(self, embedder: Callable | None = None):
        self.embedder = embedder
        self._latencies: list[float] = []
        self._batch_times: list[float] = []
        self._start_time: float = 0

    def benchmark_sequential(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        provider_name: str | None = None,
    ) -> BenchmarkResult:
        """Benchmark sequential (per-chunk) embedding generation.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.
            provider_name: Optional provider name for the result.

        Returns:
            BenchmarkResult with per-chunk latency metrics.
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

        return self._build_result(
            embeddings, len(chunks), latencies, [],
            provider_name=provider_name,
        )

    def benchmark_batch(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        batch_size: int = 32,
        provider_name: str | None = None,
    ) -> BenchmarkResult:
        """Benchmark batch embedding generation.

        Measures batch-level throughput and per-item latency averages.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.
            batch_size: Batch size for processing.
            provider_name: Optional provider name for the result.

        Returns:
            BenchmarkResult with batch and latency metrics.
        """
        latencies = []
        embeddings = []
        batch_times: list[float] = []
        errors: list[str] = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            start = time.perf_counter()
            try:
                result = embed_fn(batch)
                embeddings.extend(result)
            except Exception as e:
                errors.append(f"Batch {i // batch_size}: {e!s}")
                latencies.extend([0.0] * len(batch))
            else:
                elapsed = (time.perf_counter() - start) * 1000
                batch_times.append(elapsed)
                per_item_latency = elapsed / len(batch) if batch else 0
                latencies.extend([per_item_latency] * len(batch))

        batch_metrics = BatchMetrics(
            total_batches=len(batch_times) + len(errors),
            successful_batches=len(batch_times),
            failed_batches=len(errors),
            average_batch_size=float(
                np.mean([min(batch_size, len(chunks) - i)
                        for i in range(0, len(chunks), batch_size)])
                if len(chunks) > 0
                else 0.0
            ),
        )

        return self._build_result(
            embeddings, len(chunks), latencies, batch_times,
            batch_metrics=batch_metrics,
            errors=errors or None,
            provider_name=provider_name,
        )

    def benchmark_warmup(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        warmup_runs: int = 3,
        provider_name: str | None = None,
    ) -> BenchmarkResult:
        """Run warmup runs before actual benchmark.

        Performs several warmup iterations to stabilize performance
        (e.g., model loading, cache warming) before collecting metrics.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Function that takes chunks and returns embeddings.
            warmup_runs: Number of warmup runs.
            provider_name: Optional provider name for the result.

        Returns:
            BenchmarkResult after warmup + actual benchmark batch.
        """
        for _ in range(warmup_runs):
            try:
                embed_fn(chunks[: min(10, len(chunks))])
            except Exception:
                pass

        return self.benchmark_batch(chunks, embed_fn, provider_name=provider_name)

    def compute_latency_metrics(self, latencies: list[float]) -> LatencyMetrics:
        """Compute latency statistics from raw latency data.

        Args:
            latencies: Raw latency measurements in milliseconds.

        Returns:
            LatencyMetrics with distribution statistics.
        """
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
        """Compute throughput metrics from timing data.

        Args:
            total_time_ms: Total processing time in milliseconds.
            total_embeddings: Number of embeddings generated.
            total_chunks: Number of chunks processed.

        Returns:
            ThroughputMetrics with embeddings/sec and chunks/sec.
        """
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
        provider_name: str | None = None,
    ) -> BenchmarkResult:
        """Build BenchmarkResult from collected metrics.

        Aggregates all metrics into a single BenchmarkResult dataclass.

        Args:
            embeddings: Generated embeddings.
            total_chunks: Total chunks processed.
            latencies: Per-item latency measurements.
            batch_times: Per-batch timing measurements.
            batch_metrics: Optional batch metrics.
            cache_hits: Number of cache hits.
            cache_misses: Number of cache misses.
            errors: Optional list of error messages.
            provider_name: Optional provider name override.

        Returns:
            BenchmarkResult with all metrics populated.
        """
        latency_metrics = self.compute_latency_metrics(latencies)

        total_time = sum(latencies)
        throughput_metrics = self.compute_throughput_metrics(
            total_time, len(embeddings), total_chunks
        )

        model_name = ""
        model_version = ""
        dimension = 0
        resolved_provider = provider_name or ""

        if embeddings:
            first = embeddings[0]
            model_name = first.model_name
            model_version = first.model_version
            dimension = first.embedding_dimension

        total_cache = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total_cache if total_cache > 0 else 0.0

        return BenchmarkResult(
            provider_name=resolved_provider,
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
            cache_hit_rate=cache_hit_rate,
            errors=errors or [],
        )

    def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource utilization metrics.

        Captures memory usage (RSS), CPU utilization, and detects GPU
        availability through optional dependencies (psutil, torch).

        Returns:
            ResourceMetrics with current utilization values.
        """
        gpu_detected = self._detect_gpu()
        gpu_util: float | None = None
        gpu_mem: float | None = None

        if gpu_detected:
            gpu_info = self._get_gpu_metrics()
            gpu_util = gpu_info.get("utilization_percent")
            gpu_mem = gpu_info.get("memory_allocated_mb")

        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)

            return ResourceMetrics(
                memory_usage_mb=memory_mb,
                cpu_utilization_percent=cpu_percent,
                gpu_utilization_percent=gpu_util,
                gpu_memory_mb=gpu_mem,
                gpu_detected=gpu_detected,
            )
        except ImportError:
            return ResourceMetrics(
                memory_usage_mb=0.0,
                cpu_utilization_percent=0.0,
                gpu_utilization_percent=gpu_util,
                gpu_memory_mb=gpu_mem,
                gpu_detected=gpu_detected,
            )

    def _detect_gpu(self) -> bool:
        """Check if GPU is available for embedding generation.

        Returns:
            True if GPU is detected, False otherwise.
        """
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _get_gpu_metrics(self) -> dict[str, Any]:
        """Get GPU utilization metrics if available.

        Returns:
            Dictionary with GPU metrics or {'available': False}.
        """
        try:
            import torch

            if torch.cuda.is_available():
                return {
                    "available": True,
                    "device_count": torch.cuda.device_count(),
                    "current_device": torch.cuda.current_device(),
                    "device_name": torch.cuda.get_device_name(0),
                    "memory_allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
                    "memory_reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
                    "utilization_percent": (
                        torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100
                        if torch.cuda.max_memory_allocated() > 0
                        else None
                    ),
                }
        except Exception:
            pass

        return {"available": False}

    def get_cache_stats(self, cache_hits: int, cache_misses: int) -> dict[str, Any]:
        """Compute cache statistics from hit/miss counts.

        Args:
            cache_hits: Number of cache hits.
            cache_misses: Number of cache misses.

        Returns:
            Dictionary with hits, misses, hit_rate, and total_requests.
        """
        total = cache_hits + cache_misses
        hit_rate = cache_hits / total if total > 0 else 0.0

        return {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total,
        }
