"""Main embedding pipeline orchestrating the embedding process."""

import hashlib
from typing import Any

from backend.data.embeddings.base_embedding_provider import BaseEmbeddingProvider
from backend.data.embeddings.embedding_batch_processor import (
    BatchProcessingConfig,
    EmbeddingBatchProcessor,
)
from backend.data.embeddings.embedding_cache import EmbeddingCache
from backend.data.embeddings.embedding_validator import EmbeddingValidator
from backend.data.models.chunk import Chunk
from backend.data.models.embedding import Embedding, EmbeddingBatchResult


class EmbeddingPipelineConfig:
    """Configuration for the embedding pipeline."""

    def __init__(
        self,
        batch_size: int = 32,
        max_workers: int = 1,
        cache_enabled: bool = True,
        cache_ttl: int = 86400,
        cache_max_size: int = 10000,
        show_progress: bool = True,
        validate_embeddings: bool = True,
    ):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_max_size = cache_max_size
        self.show_progress = show_progress
        self.validate_embeddings = validate_embeddings

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmbeddingPipelineConfig":
        return cls(
            batch_size=data.get("batch_size", 32),
            max_workers=data.get("max_workers", 1),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl=data.get("cache_ttl", 86400),
            cache_max_size=data.get("cache_max_size", 10000),
            show_progress=data.get("show_progress", True),
            validate_embeddings=data.get("validate_embeddings", True),
        )


class EmbeddingPipeline:
    """Pipeline for generating embeddings from document chunks."""

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        config: EmbeddingPipelineConfig | None = None,
        cache: EmbeddingCache | None = None,
    ):
        self.provider = provider
        self.config = config or EmbeddingPipelineConfig()
        self.cache = cache or EmbeddingCache(
            max_size=self.config.cache_max_size,
            ttl_seconds=self.config.cache_ttl if self.config.cache_enabled else None,
        )
        self.validator = EmbeddingValidator()
        self._processor = EmbeddingBatchProcessor(
            provider=provider,
            config=BatchProcessingConfig(
                batch_size=self.config.batch_size,
                max_workers=self.config.max_workers,
                show_progress=self.config.show_progress,
            ),
        )
        self._stats = {
            "total_chunks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_ms": 0.0,
            "errors": 0,
        }

    def embed_chunks(
        self, chunks: list[Chunk], provider_config: dict[str, Any] | None = None
    ) -> EmbeddingBatchResult:
        if not chunks:
            return EmbeddingBatchResult(results=[])

        chunks_to_embed, cached_results = self._get_cached_chunks(chunks, provider_config)

        if cached_results:
            for _r in cached_results:
                self._stats["cache_hits"] += 1

        if chunks_to_embed:
            result = self._processor.process(chunks_to_embed)
            for r in result.results:
                if r.cache_hit:
                    self._stats["cache_hits"] += 1
                else:
                    self._stats["cache_misses"] += 1
                if r.error:
                    self._stats["errors"] += 1

        all_results = cached_results + (result.results if chunks_to_embed else [])
        self._stats["total_chunks"] += len(chunks)

        if self.config.validate_embeddings and all_results:
            self._validate_results(all_results)

        return EmbeddingBatchResult(
            results=all_results,
            total_processing_time_ms=result.total_processing_time_ms if chunks_to_embed else 0,
            cache_hits=self._stats["cache_hits"],
            cache_misses=self._stats["cache_misses"],
        )

    def _get_cached_chunks(
        self, chunks: list[Chunk], config: dict[str, Any] | None
    ) -> tuple[list[Chunk], list]:
        if not self.config.cache_enabled:
            return chunks, []

        chunks_to_embed = []
        cached_results = []

        for chunk in chunks:
            checksum = self._compute_chunk_checksum(chunk.text)
            cached = self.cache.get(
                chunk_checksum=checksum,
                model_name=self.provider.name,
                model_version=self.provider.model_info.version,
                config=config,
            )

            if cached:
                from backend.data.models.embedding import EmbeddingResult

                cached_results.append(
                    EmbeddingResult(chunk=chunk, embedding=cached, cache_hit=True)
                )
            else:
                chunks_to_embed.append(chunk)

        return chunks_to_embed, cached_results

    def _compute_chunk_checksum(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _validate_results(self, results: list) -> None:
        for r in results:
            if r.embedding:
                self.validator.validate(r.embedding)

    def get_stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "cache_stats": self.cache.get_stats(),
            "provider_stats": self.provider.model_info.model_dump() if self.provider.model_info else {},
            "success_rate": (self._stats["total_chunks"] - self._stats["errors"])
            / self._stats["total_chunks"]
            if self._stats["total_chunks"] > 0
            else 0,
        }

    def reset_stats(self) -> None:
        self._stats = {
            "total_chunks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_ms": 0.0,
            "errors": 0,
        }
        self._processor.reset_stats()

    def embed_text(self, text: str) -> Embedding:
        return self.provider.embed_text(text)

    def embed_texts(self, texts: list[str]) -> list[Embedding]:
        return self.provider.embed_texts(texts)
