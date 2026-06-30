"""Tests for embedding benchmark."""

import time
from uuid import uuid4

import pytest

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding
from backend.embedding_validation.embedding_benchmark import (
    EmbeddingBenchmark,
    LatencyMetrics,
    ThroughputMetrics,
    BatchMetrics,
    ResourceMetrics,
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


class TestEmbeddingBenchmark:
    """Tests for EmbeddingBenchmark class."""

    def test_benchmark_sequential(self):
        benchmark = EmbeddingBenchmark()
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i, "start_offset": 0, "end_offset": len(f"Text {i}")},
            )
            for i in range(5)
        ]

        provider = MockEmbeddingProvider()
        result = benchmark.benchmark_sequential(chunks, provider.embed_chunks)

        assert result.total_chunks == 5
        assert result.total_embeddings == 5
        assert result.model_name == "mock-model"

    def test_benchmark_batch(self):
        benchmark = EmbeddingBenchmark()
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i, "start_offset": 0, "end_offset": len(f"Text {i}")},
            )
            for i in range(10)
        ]

        provider = MockEmbeddingProvider()
        result = benchmark.benchmark_batch(chunks, provider.embed_chunks, batch_size=5)

        assert result.total_chunks == 10
        assert result.total_embeddings == 10
        assert result.batch_metrics.total_batches == 2

    def test_benchmark_warmup(self):
        benchmark = EmbeddingBenchmark()
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i, "start_offset": 0, "end_offset": len(f"Text {i}")},
            )
            for i in range(3)
        ]

        provider = MockEmbeddingProvider()
        result = benchmark.benchmark_warmup(chunks, provider.embed_chunks, warmup_runs=1)

        assert result.total_chunks == 3

    def test_compute_latency_metrics(self):
        benchmark = EmbeddingBenchmark()
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = benchmark.compute_latency_metrics(latencies)

        assert isinstance(result, LatencyMetrics)
        assert result.average_latency_ms == 30.0
        assert result.median_latency_ms == 30.0
        assert result.p95_latency_ms == 48.0
        assert result.p99_latency_ms == pytest.approx(49.6, rel=0.01)

    def test_compute_latency_metrics_empty(self):
        benchmark = EmbeddingBenchmark()
        result = benchmark.compute_latency_metrics([])

        assert isinstance(result, LatencyMetrics)
        assert result.average_latency_ms == 0.0

    def test_compute_throughput_metrics(self):
        benchmark = EmbeddingBenchmark()
        result = benchmark.compute_throughput_metrics(1000.0, 100, 100)

        assert isinstance(result, ThroughputMetrics)
        assert result.embeddings_per_second == 100.0
        assert result.chunks_per_second == 100.0

    def test_compute_throughput_metrics_zero_time(self):
        benchmark = EmbeddingBenchmark()
        result = benchmark.compute_throughput_metrics(0.0, 100, 100)

        assert result.embeddings_per_second == 0.0

    def test_get_cache_stats(self):
        benchmark = EmbeddingBenchmark()
        stats = benchmark.get_cache_stats(80, 20)

        assert stats["hits"] == 80
        assert stats["misses"] == 20
        assert stats["hit_rate"] == 0.8