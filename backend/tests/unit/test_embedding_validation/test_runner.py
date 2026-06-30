"""Tests for validation runner."""

import time
from uuid import uuid4

import pytest

from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding
from backend.embedding_validation.validation_runner import (
    ValidationRunner,
    ValidationSummary,
)


class MockEmbeddingProvider:
    """Mock provider for testing."""

    def __init__(self, dimension: int = 100):
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


class TestValidationRunner:
    """Tests for ValidationRunner class."""

    def test_validate_and_benchmark(self):
        runner = ValidationRunner(
            expected_dimension=100,
            enable_benchmark=True,
            enable_profiling=True,
        )
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
        summary = runner.validate_and_benchmark(chunks, provider.embed_chunks)

        assert isinstance(summary, ValidationSummary)
        assert summary.is_valid is True
        assert summary.total_chunks == 5
        assert summary.total_embeddings == 5

    def test_validate_and_benchmark_with_errors(self):
        runner = ValidationRunner(expected_dimension=50)
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i},
            )
            for i in range(3)
        ]

        provider = MockEmbeddingProvider(dimension=100)
        summary = runner.validate_and_benchmark(chunks, provider.embed_chunks)

        assert len(summary.warnings) > 0

    def test_save_reports(self, tmp_path):
        runner = ValidationRunner(
            enable_benchmark=True,
            enable_profiling=False,
        )
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                text=f"Text {i}",
                metadata={"chunk_index": i},
            )
            for i in range(3)
        ]

        provider = MockEmbeddingProvider()
        runner.validate_and_benchmark(chunks, provider.embed_chunks)

        md_path, json_path = runner.save_reports(tmp_path)

        assert md_path.exists()
        assert json_path.exists()

    def test_get_report(self):
        runner = ValidationRunner()
        report = runner.get_report()

        assert report is not None

    def test_reset(self):
        runner = ValidationRunner()
        runner.reset()
        assert runner.get_report() is not None

    def test_summary_properties(self):
        summary = ValidationSummary(
            is_valid=True,
            total_chunks=10,
            total_embeddings=10,
        )
        assert summary.is_valid is True
        assert summary.total_chunks == 10