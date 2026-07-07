"""Performance profiling for embedding generation.

Supports large datasets by minimizing memory allocations and avoiding
unnecessary recomputation. Reuses existing caches when available.

Captures:
- Latency samples (per-embedding generation time)
- Memory samples (RSS memory usage over time)
- CPU samples (CPU utilization percentage)
- GPU detection and metrics (if available)
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding


@dataclass
class ProfilerMetrics:
    """Metrics collected during profiling session.

    Contains time-series samples of latency, memory, CPU, and GPU usage
    during embedding generation profiling.
    """

    timestamps: list[float] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)
    memory_samples_mb: list[float] = field(default_factory=list)
    cpu_samples_percent: list[float] = field(default_factory=list)
    embedding_dimensions: list[int] = field(default_factory=list)
    batch_sizes: list[int] = field(default_factory=list)

    total_time_ms: float = 0.0
    total_embeddings: int = 0

    @property
    def average_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.mean(self.latencies_ms))

    @property
    def median_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.median(self.latencies_ms))

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.percentile(self.latencies_ms, 95))

    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.percentile(self.latencies_ms, 99))

    @property
    def throughput_per_second(self) -> float:
        total_s = self.total_time_ms / 1000
        if total_s == 0:
            return 0.0
        return self.total_embeddings / total_s

    @property
    def peak_memory_mb(self) -> float:
        if not self.memory_samples_mb:
            return 0.0
        return float(max(self.memory_samples_mb))

    @property
    def average_cpu_percent(self) -> float:
        if not self.cpu_samples_percent:
            return 0.0
        return float(np.mean(self.cpu_samples_percent))


class EmbeddingProfiler:
    """Profile embedding generation performance.

    Measures latency, memory, CPU, and GPU utilization during embedding
    generation. Supports both sync and batch profiling modes.

    Designed for large datasets:
    - Periodic resource sampling to minimize overhead
    - Efficient memory usage with incremental collection
    - Optional GPU detection and monitoring

    Usage:
        profiler = EmbeddingProfiler()
        metrics = profiler.profile_batch(chunks, embed_fn, batch_size=32)
        print(f"Peak memory: {metrics.peak_memory_mb:.1f}MB")
    """

    def __init__(self):
        self._metrics = ProfilerMetrics()
        self._start_time: float = 0
        self._sampling_interval: float = 0.1

    @property
    def metrics(self) -> ProfilerMetrics:
        return self._metrics

    def profile_sync(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
    ) -> ProfilerMetrics:
        """Profile synchronous (per-chunk) embedding generation.

        Measures each chunk individually for fine-grained latency analysis.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Embedding function to profile.

        Returns:
            ProfilerMetrics with per-chunk measurements.
        """
        self._metrics = ProfilerMetrics()
        self._start_time = time.perf_counter()

        for chunk in chunks:
            start = time.perf_counter()

            if self._should_sample():
                self._sample_resources()

            try:
                result = embed_fn([chunk])
            except Exception:
                pass
            else:
                elapsed = (time.perf_counter() - start) * 1000
                self._metrics.latencies_ms.append(elapsed)
                self._metrics.embedding_dimensions.append(
                    result[0].embedding_dimension if result else 0
                )
                self._metrics.total_embeddings += 1

        self._metrics.total_time_ms = (time.perf_counter() - self._start_time) * 1000
        return self._metrics

    def profile_batch(
        self,
        chunks: list[Chunk],
        embed_fn: Callable[[list[Chunk]], list[Embedding]],
        batch_size: int = 32,
    ) -> ProfilerMetrics:
        """Profile batch embedding generation.

        Processes chunks in batches for throughput measurement. Suitable for
        large datasets as it minimizes per-item overhead.

        Args:
            chunks: List of chunks to embed.
            embed_fn: Embedding function to profile.
            batch_size: Batch size for processing.

        Returns:
            ProfilerMetrics with batch-level measurements.
        """
        self._metrics = ProfilerMetrics()
        self._start_time = time.perf_counter()

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            start = time.perf_counter()

            if self._should_sample():
                self._sample_resources()

            try:
                result = embed_fn(batch)
            except Exception:
                pass
            else:
                elapsed = (time.perf_counter() - start) * 1000
                self._metrics.latencies_ms.append(elapsed)
                self._metrics.batch_sizes.append(len(batch))
                self._metrics.total_embeddings += len(result)

                if result:
                    self._metrics.embedding_dimensions.append(
                        result[0].embedding_dimension
                    )

        self._metrics.total_time_ms = (time.perf_counter() - self._start_time) * 1000
        return self._metrics

    def reset(self) -> None:
        """Reset collected metrics to initial state.

        Clears all collected samples for a fresh profiling session.
        """
        self._metrics = ProfilerMetrics()

    def get_summary(self) -> dict[str, Any]:
        """Get summary of profiling session.

        Returns a dictionary with key metrics including latency percentiles,
        throughput, peak memory, and average CPU usage.

        Returns:
            Dictionary with summary statistics.
        """
        return {
            "total_embeddings": self._metrics.total_embeddings,
            "total_time_ms": self._metrics.total_time_ms,
            "average_latency_ms": self._metrics.average_latency_ms,
            "median_latency_ms": self._metrics.median_latency_ms,
            "p95_latency_ms": self._metrics.p95_latency_ms,
            "p99_latency_ms": self._metrics.p99_latency_ms,
            "throughput_per_second": self._metrics.throughput_per_second,
            "peak_memory_mb": self._metrics.peak_memory_mb,
            "average_cpu_percent": self._metrics.average_cpu_percent,
            "gpu_detected": self._detect_gpu(),
        }

    def get_detailed_metrics(self) -> dict[str, Any]:
        """Get detailed metrics including raw samples.

        Returns a comprehensive dictionary with all raw sample data
        for in-depth analysis and visualization.

        Returns:
            Dictionary with all metrics including raw samples.
        """
        return {
            "total_embeddings": self._metrics.total_embeddings,
            "total_time_ms": self._metrics.total_time_ms,
            "average_latency_ms": self._metrics.average_latency_ms,
            "median_latency_ms": self._metrics.median_latency_ms,
            "p95_latency_ms": self._metrics.p95_latency_ms,
            "p99_latency_ms": self._metrics.p99_latency_ms,
            "throughput_per_second": self._metrics.throughput_per_second,
            "peak_memory_mb": self._metrics.peak_memory_mb,
            "average_cpu_percent": self._metrics.average_cpu_percent,
            "latency_samples": self._metrics.latencies_ms,
            "memory_samples": self._metrics.memory_samples_mb,
            "cpu_samples": self._metrics.cpu_samples_percent,
            "timestamps": self._metrics.timestamps,
            "batch_sizes": self._metrics.batch_sizes,
            "gpu_detected": self._detect_gpu(),
            "gpu_metrics": self.get_gpu_metrics() if self._detect_gpu() else None,
        }

    def _should_sample(self) -> bool:
        """Determine if we should sample resources.

        Uses a configurable sampling interval to avoid excessive overhead
        from resource monitoring, especially important for large datasets.

        Returns:
            True if resource sampling should occur.
        """
        if not self._metrics.timestamps:
            return True
        elapsed = time.perf_counter() - self._metrics.timestamps[-1]
        return elapsed >= self._sampling_interval

    def _sample_resources(self) -> None:
        """Sample current resource usage.

        Records timestamp, memory, and CPU utilization. Gracefully handles
        missing psutil dependency.
        """
        self._metrics.timestamps.append(time.perf_counter())

        try:
            import psutil

            process = psutil.Process()
            self._metrics.memory_samples_mb.append(
                process.memory_info().rss / (1024 * 1024)
            )
            self._metrics.cpu_samples_percent.append(
                process.cpu_percent(interval=None)
            )
        except ImportError:
            pass

    def detect_gpu(self) -> bool:
        """Check if GPU is available for profiling.

        Attempts to detect CUDA-capable GPU via torch.

        Returns:
            True if GPU is detected, False otherwise.
        """
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _detect_gpu(self) -> bool:
        """Internal GPU detection (alias for detect_gpu)."""
        return self.detect_gpu()

    def get_gpu_metrics(self) -> dict[str, Any]:
        """Get GPU utilization metrics if available.

        Collects GPU device information and memory usage when CUDA is available.

        Returns:
            Dictionary with GPU metrics or {'available': False}.
        """
        if not self._detect_gpu():
            return {"available": False}

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
