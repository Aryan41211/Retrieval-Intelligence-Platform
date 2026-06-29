"""Tests for embedding batch processor."""

from unittest.mock import Mock, patch

import pytest

from backend.data.models.chunk import Chunk
from backend.data.embeddings.embedding_batch_processor import (
    EmbeddingBatchProcessor,
    BatchProcessingConfig,
)


class TestBatchProcessingConfig:
    """Tests for BatchProcessingConfig."""

    def test_default_values(self):
        config = BatchProcessingConfig()
        assert config.batch_size == 32
        assert config.max_workers == 1
        assert config.retry_attempts == 3
        assert config.show_progress is True

    def test_custom_values(self):
        config = BatchProcessingConfig(
            batch_size=64,
            max_workers=4,
            show_progress=False,
        )
        assert config.batch_size == 64
        assert config.max_workers == 4
        assert config.show_progress is False


class TestEmbeddingBatchProcessor:
    """Tests for EmbeddingBatchProcessor class."""

    def test_empty_chunks(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        processor = EmbeddingBatchProcessor(mock_provider)
        result = processor.process([])
        assert result.results == []

    def test_creates_batches(self):
        config = BatchProcessingConfig(batch_size=2)
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.embed_chunks.return_value = Mock(
            results=[], cache_hits=0, cache_misses=0
        )
        processor = EmbeddingBatchProcessor(mock_provider, config)
        chunks = [Mock() for _ in range(5)]
        processor.process(chunks)

    def test_get_stats(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.model_info = Mock(
            name="test-model", version="1.0", dimension=384
        )
        mock_provider.embed_chunks.return_value = Mock(
            results=[], cache_hits=0, cache_misses=0
        )
        processor = EmbeddingBatchProcessor(mock_provider)
        stats = processor.get_stats()
        assert "total_processed" in stats
        assert "provider" in stats

    def test_reset_stats(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        processor = EmbeddingBatchProcessor(mock_provider)
        processor.reset_stats()
        stats = processor.get_stats()
        assert stats["total_processed"] == 0