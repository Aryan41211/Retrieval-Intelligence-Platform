"""Batch processor for embedding generation with progress reporting."""

import time
from typing import Any

from tqdm import tqdm

from backend.data.embeddings.base_embedding_provider import BaseEmbeddingProvider, EmbeddingError
from backend.data.models.chunk import Chunk
from backend.data.models.embedding import EmbeddingBatchResult


class BatchProcessingConfig:
    def __init__(
        self,
        batch_size: int = 32,
        max_workers: int = 1,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 300.0,
        show_progress: bool = True,
    ):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.show_progress = show_progress


class EmbeddingBatchProcessor:
    """Processes chunks in batches with retry and progress tracking."""

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        config: BatchProcessingConfig | None = None,
    ):
        self.provider = provider
        self.config = config or BatchProcessingConfig()
        self._total_processed = 0
        self._total_errors = 0
        self._total_time_ms = 0.0

    def process(self, chunks: list[Chunk]) -> EmbeddingBatchResult:
        if not chunks:
            return EmbeddingBatchResult(results=[])

        batches = self._create_batches(chunks)
        all_results = []
        cache_hits = 0
        cache_misses = 0

        iterator = tqdm(batches, disable=not self.config.show_progress, desc="Embedding batches")

        for batch in iterator:
            result = self._process_batch_with_retry(batch)
            all_results.extend(result.results)
            cache_hits += result.cache_hits
            cache_misses += result.cache_misses
            self._total_processed += len(batch)

        self._total_time_ms = sum(
            r.embedding.processing_time_ms for r in all_results if r.embedding
        )

        return EmbeddingBatchResult(
            results=all_results,
            total_processing_time_ms=self._total_time_ms,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

    def _create_batches(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        batches = []
        for i in range(0, len(chunks), self.config.batch_size):
            batches.append(chunks[i : i + self.config.batch_size])
        return batches

    def _process_batch_with_retry(self, batch: list[Chunk]) -> EmbeddingBatchResult:
        last_error = None
        for attempt in range(self.config.retry_attempts):
            try:
                return self.provider.embed_chunks(batch)
            except (EmbeddingError, Exception) as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    self._total_errors += 1
                else:
                    break

        failed_results = [
            type("EmbeddingResult", (), {"chunk": c, "embedding": None, "error": str(last_error)})
            for c in batch
        ]
        return EmbeddingBatchResult(results=failed_results)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "total_time_ms": self._total_time_ms,
            "avg_processing_time_ms": (
                self._total_time_ms / self._total_processed if self._total_processed > 0 else 0
            ),
            "provider": self.provider.name,
            "batch_size": self.config.batch_size,
        }

    def reset_stats(self) -> None:
        self._total_processed = 0
        self._total_errors = 0
        self._total_time_ms = 0.0


def create_batch_processor(
    provider: BaseEmbeddingProvider,
    batch_size: int = 32,
    max_workers: int = 1,
    show_progress: bool = True,
) -> EmbeddingBatchProcessor:
    config = BatchProcessingConfig(
        batch_size=batch_size,
        max_workers=max_workers,
        show_progress=show_progress,
    )
    return EmbeddingBatchProcessor(provider, config)
