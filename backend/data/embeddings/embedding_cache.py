"""Embedding cache for avoiding redundant embedding generation."""

import hashlib
import json
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.data.models.embedding import Embedding


class EmbeddingCache:
    """LRU cache for embeddings with optional persistence."""

    def __init__(
        self,
        max_size: int = 10000,
        ttl_seconds: int | None = None,
        persist_path: str | None = None,
    ):
        self._cache: OrderedDict[str, tuple[Embedding, datetime]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._persist_path = persist_path
        self._hits = 0
        self._misses = 0

    def _compute_key(
        self,
        chunk_checksum: str,
        model_name: str,
        model_version: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        config_str = json.dumps(config or {}, sort_keys=True, default=str)
        key_content = f"{chunk_checksum}:{model_name}:{model_version}:{config_str}"
        return hashlib.sha256(key_content.encode()).hexdigest()

    def get(
        self,
        chunk_checksum: str,
        model_name: str,
        model_version: str,
        config: dict[str, Any] | None = None,
    ) -> Embedding | None:
        key = self._compute_key(chunk_checksum, model_name, model_version, config)
        if key in self._cache:
            embedding, stored_at = self._cache[key]
            if self._is_expired(stored_at):
                del self._cache[key]
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return embedding
        self._misses += 1
        return None

    def set(
        self,
        embedding: Embedding,
        chunk_checksum: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        key = self._compute_key(
            chunk_checksum, embedding.model_name, embedding.model_version, config
        )
        self._cache[key] = (embedding, datetime.now(UTC))
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def _is_expired(self, stored_at: datetime) -> bool:
        if self._ttl_seconds is None:
            return False
        age_seconds = (datetime.now(UTC) - stored_at).total_seconds()
        return age_seconds > self._ttl_seconds

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, int]:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
        }

    def has(self, key: str) -> bool:
        return key in self._cache

    def get_embedding(self, chunk_id: str) -> Embedding | None:
        for key, (embedding, _) in self._cache.items():
            if embedding.chunk_id == uuid4().__class__(key.split(":")[0]):
                return embedding
        return None
