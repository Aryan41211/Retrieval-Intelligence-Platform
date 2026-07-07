"""Tests for embedding cache."""

import time

from backend.data.embeddings.embedding_cache import EmbeddingCache
from backend.data.models.embedding import Embedding


class TestEmbeddingCache:
    """Tests for EmbeddingCache class."""

    def test_cache_set_and_get(self):
        cache = EmbeddingCache(max_size=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        cache.set(embedding, chunk_checksum="abc123", config={})
        result = cache.get(
            chunk_checksum="abc123",
            model_name="test-model",
            model_version="1.0",
            config={},
        )
        assert result is not None
        assert result.embedding_vector == embedding.embedding_vector

    def test_cache_miss(self):
        cache = EmbeddingCache(max_size=100)
        result = cache.get(
            chunk_checksum="not-exist",
            model_name="test-model",
            model_version="1.0",
            config={},
        )
        assert result is None

    def test_cache_stats(self):
        cache = EmbeddingCache(max_size=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        cache.set(embedding, chunk_checksum="abc", config={})
        cache.get(chunk_checksum="abc", model_name="test-model", model_version="1.0", config={})
        cache.get(chunk_checksum="xyz", model_name="test-model", model_version="1.0", config={})
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_lru_eviction(self):
        cache = EmbeddingCache(max_size=3)
        for i in range(5):
            embedding = Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test-model",
                model_version="1.0",
                embedding_dimension=10,
                embedding_vector=[float(i)] * 10,
            )
            cache.set(embedding, chunk_checksum=f"key{i}", config={})
        stats = cache.get_stats()
        assert stats["size"] == 3

    def test_cache_ttl_expiration(self):
        cache = EmbeddingCache(max_size=100, ttl_seconds=1)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        cache.set(embedding, chunk_checksum="abc", config={})
        time.sleep(1.1)
        result = cache.get(
            chunk_checksum="abc",
            model_name="test-model",
            model_version="1.0",
            config={},
        )
        assert result is None

    def test_cache_key_uniqueness(self):
        cache = EmbeddingCache(max_size=100)
        embedding = Embedding(
            chunk_id=uuid4(),
            document_id=uuid4(),
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=10,
            embedding_vector=[0.1] * 10,
        )
        cache.set(embedding, chunk_checksum="abc", config={"key": "v1"})
        result = cache.get(
            chunk_checksum="abc",
            model_name="test-model",
            model_version="2.0",
            config={"key": "v1"},
        )
        assert result is None


def uuid4():
    from uuid import uuid4 as _uuid4

    return _uuid4()
