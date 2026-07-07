"""Embedding cache for avoiding redundant embedding generation."""

import json
import os
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from backend.data.models.embedding import Embedding


class EmbeddingCache:
    """LRU cache for embeddings with optional persistence.

    Cache key considerations:
    - chunk checksum
    - embedding model name + model version
    - configuration snapshot (provider config, batch settings, etc.)
    """

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

        self._load_from_disk()

    @staticmethod
    def _stable_json(config: dict[str, Any] | None) -> str:
        return json.dumps(config or {}, sort_keys=True, default=str)

    def _compute_key(
        self,
        chunk_checksum: str,
        model_name: str,
        model_version: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        # Use a deterministic string representation to avoid collisions.
        key_content = f"{chunk_checksum}:{model_name}:{model_version}:{self._stable_json(config)}"
        import hashlib

        return hashlib.sha256(key_content.encode("utf-8")).hexdigest()

    def _load_from_disk(self) -> None:
        if not self._persist_path:
            return
        if not os.path.exists(self._persist_path):
            return

        try:
            with open(self._persist_path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            # Corrupt cache should not fail embeddings.
            return

        items = payload.get("items", [])
        for item in items:
            key = item.get("key")
            embedding_data = item.get("embedding")
            stored_at_ts = item.get("stored_at")
            if not key or not embedding_data or not stored_at_ts:
                continue

            try:
                embedding = Embedding.model_validate(embedding_data)
                stored_at = datetime.fromtimestamp(float(stored_at_ts), tz=UTC)
            except Exception:
                continue

            self._cache[key] = (embedding, stored_at)

        # Enforce max size after load.
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def _persist_to_disk(self) -> None:
        if not self._persist_path:
            return

        # Persist a bounded number of items to avoid unbounded file growth.
        items = []
        for key, (embedding, stored_at) in list(self._cache.items())[-self._max_size :]:
            items.append(
                {
                    "key": key,
                    "embedding": embedding.model_dump(),
                    "stored_at": stored_at.timestamp(),
                }
            )

        payload = {"items": items}
        try:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except OSError:
            # Persistence failure should not break embedding generation.
            return

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
                self._persist_to_disk()
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

        self._persist_to_disk()

    def _is_expired(self, stored_at: datetime) -> bool:
        if self._ttl_seconds is None:
            return False
        age_seconds = (datetime.now(UTC) - stored_at).total_seconds()
        return age_seconds > self._ttl_seconds

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._persist_to_disk()

    def get_stats(self) -> dict[str, float]:
        hit_rate = self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }

    def has_key(self, key: str) -> bool:
        return key in self._cache

    def get_by_chunk_id(self, chunk_id: UUID) -> Embedding | None:
        # O(n) scan; only intended for debugging/inspection.
        for embedding, _ in self._cache.values():
            if embedding.chunk_id == chunk_id:
                return embedding
        return None
