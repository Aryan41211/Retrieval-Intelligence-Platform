"""Tests for embedding profiler."""

import time
from unittest import mock
from uuid import uuid4

import pytest

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_profiler import (
    EmbeddingProfiler,
    ProfilerMetrics,
)


class MockEmbeddingProvider:
    """Mock provider for testing."""

    def __init__(self, dimension: int = 10):
        self._dimension = dimension

    def embed_chunks(self, chunks):
        embeddings = []
        for chunk in chunks:
            time.sleep(0.001)
            embeddings.append(
                Embedding(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    model_name="mock-model",
                    model_version="1.0",
                    embedding_dimension=self._dimension,
                    embedding_vector=[0.1] * self._dimension,
                )
            )
        return embeddings


class TestEmbeddingProfiler:
    """Tests for EmbeddingProfiler class."""

    def test_profile_sync(self):
        profiler = EmbeddingProfiler()
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i},
            )
            for i in range(5)
        ]

        provider = MockEmbeddingProvider()
        metrics = profiler.profile_sync(chunks, provider.embed_chunks)

        assert isinstance(metrics, ProfilerMetrics)
        assert metrics.total_embeddings == 5
        assert len(metrics.latencies_ms) == 5

    def test_profile_batch(self):
        profiler = EmbeddingProfiler()
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i},
            )
            for i in range(10)
        ]

        provider = MockEmbeddingProvider()
        metrics = profiler.profile_batch(chunks, provider.embed_chunks, batch_size=5)

        assert isinstance(metrics, ProfilerMetrics)
        assert metrics.total_embeddings == 10
        assert len(metrics.batch_sizes) == 2

    def test_metrics_properties(self):
        profiler = EmbeddingProfiler()
        profiler._metrics = ProfilerMetrics(
            latencies_ms=[10.0, 20.0, 30.0],
            total_time_ms=60.0,
            total_embeddings=3,
        )

        assert profiler.metrics.average_latency_ms == 20.0
        assert profiler.metrics.median_latency_ms == 20.0
        assert profiler.metrics.p95_latency_ms == 29.0

    def test_get_summary(self):
        profiler = EmbeddingProfiler()
        profiler._metrics = ProfilerMetrics(
            latencies_ms=[10.0, 20.0, 30.0],
            total_time_ms=60.0,
            total_embeddings=3,
            memory_samples_mb=[100.0, 110.0],
            cpu_samples_percent=[20.0, 25.0],
        )

        summary = profiler.get_summary()

        assert summary["total_embeddings"] == 3
        assert summary["average_latency_ms"] == 20.0
        assert summary["peak_memory_mb"] == 110.0

    def test_reset(self):
        profiler = EmbeddingProfiler()
        profiler._metrics = ProfilerMetrics(total_embeddings=10)
        profiler.reset()

        assert profiler.metrics.total_embeddings == 0

    def test_detect_gpu_not_available(self):
        """GPU detection reports False when CUDA is unavailable.

        ``torch.cuda.is_available`` is patched so the result does not depend on
        whether the machine running the suite happens to have a GPU.
        """
        torch = pytest.importorskip("torch")
        profiler = EmbeddingProfiler()
        with mock.patch.object(torch.cuda, "is_available", return_value=False):
            assert profiler.detect_gpu() is False

    def test_detect_gpu_available(self):
        """GPU detection reports True when CUDA reports a device."""
        torch = pytest.importorskip("torch")
        profiler = EmbeddingProfiler()
        with mock.patch.object(torch.cuda, "is_available", return_value=True):
            assert profiler.detect_gpu() is True

    def test_get_gpu_metrics_unavailable(self):
        """Metrics collapse to a single 'available' flag with no GPU present."""
        torch = pytest.importorskip("torch")
        profiler = EmbeddingProfiler()
        with mock.patch.object(torch.cuda, "is_available", return_value=False):
            assert profiler.get_gpu_metrics() == {"available": False}

    def test_get_gpu_metrics_available(self):
        """Metrics include device details when CUDA reports a device."""
        torch = pytest.importorskip("torch")
        profiler = EmbeddingProfiler()
        with (
            mock.patch.object(torch.cuda, "is_available", return_value=True),
            mock.patch.object(torch.cuda, "device_count", return_value=1),
            mock.patch.object(torch.cuda, "current_device", return_value=0),
            mock.patch.object(torch.cuda, "get_device_name", return_value="TestGPU"),
            mock.patch.object(torch.cuda, "memory_allocated", return_value=512 * 1024 * 1024),
            mock.patch.object(torch.cuda, "memory_reserved", return_value=1024 * 1024 * 1024),
            mock.patch.object(torch.cuda, "max_memory_allocated", return_value=1024 * 1024 * 1024),
        ):
            metrics = profiler.get_gpu_metrics()

        assert metrics["available"] is True
        assert metrics["device_name"] == "TestGPU"
        assert metrics["memory_allocated_mb"] == 512.0
        assert metrics["utilization_percent"] == 50.0
