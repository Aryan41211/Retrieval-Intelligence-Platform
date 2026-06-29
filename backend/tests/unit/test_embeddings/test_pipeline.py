"""Tests for embedding pipeline."""

from unittest.mock import Mock

import pytest

from backend.data.models.chunk import Chunk, ChunkMetadata, ChunkingStrategy
from backend.data.models.embedding import Embedding, EmbeddingResult, EmbeddingBatchResult
from backend.data.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingPipelineConfig,
)


class TestEmbeddingPipelineConfig:
    """Tests for EmbeddingPipelineConfig."""

    def test_default_values(self):
        config = EmbeddingPipelineConfig()
        assert config.batch_size == 32
        assert config.cache_enabled is True
        assert config.validate_embeddings is True

    def test_from_dict(self):
        config = EmbeddingPipelineConfig.from_dict({"batch_size": 64, "cache_enabled": False})
        assert config.batch_size == 64
        assert config.cache_enabled is False


class TestEmbeddingPipeline:
    """Tests for EmbeddingPipeline class."""

    def test_empty_chunks(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.model_info = Mock(version="1.0")
        pipeline = EmbeddingPipeline(mock_provider)
        result = pipeline.embed_chunks([])
        assert result.results == []
        assert result.cache_hits == 0

    def test_embed_single_chunk(self):
        doc_id = uuid4()
        chunk = Chunk(
            text="test content",
            document_id=doc_id,
            metadata=ChunkMetadata(
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                char_count=12,
                token_count=2,
            ),
        )
        result = EmbeddingResult(chunk=chunk, cache_hit=False)
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.model_info = Mock(version="1.0")
        mock_provider.embed_chunks.return_value = EmbeddingBatchResult(
            results=[result],
            cache_hits=0,
            cache_misses=1,
            total_processing_time_ms=10.5,
        )
        pipeline = EmbeddingPipeline(mock_provider, config=EmbeddingPipelineConfig())
        result = pipeline.embed_chunks([chunk])
        assert len(result.results) == 1

    def test_cache_enabled(self):
        doc_id = uuid4()
        chunk = Chunk(
            text="cached content",
            document_id=doc_id,
            metadata=ChunkMetadata(
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                char_count=14,
                token_count=2,
            ),
        )
        cached_embedding = Embedding(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            model_name="test",
            model_version="1.0",
            embedding_dimension=384,
            embedding_vector=[0.1] * 384,
        )
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.model_info = Mock(version="1.0")
        pipeline = EmbeddingPipeline(
            mock_provider,
            config=EmbeddingPipelineConfig(cache_enabled=True),
        )
        pipeline.cache.set(cached_embedding, chunk_checksum="hash123", config={})
        result = pipeline.embed_chunks([chunk])
        assert result.cache_hits == 1

    def test_get_stats(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.model_info = Mock(version="1.0", model_dump=lambda: {})
        pipeline = EmbeddingPipeline(mock_provider)
        stats = pipeline.get_stats()
        assert "total_chunks" in stats
        assert "cache_stats" in stats

    def test_reset_stats(self):
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        pipeline = EmbeddingPipeline(mock_provider)
        pipeline.reset_stats()
        stats = pipeline.get_stats()
        assert stats["total_chunks"] == 0


def uuid4():
    from uuid import uuid4 as _uuid4

    return _uuid4()