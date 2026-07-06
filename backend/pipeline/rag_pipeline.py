from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from backend.generation.generation_pipeline import GenerationPipeline
from backend.generation.models import GenerationResult
from backend.retrieval.intelligent_retrieval_pipeline import IntelligentRetrievalPipeline
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_metadata import RetrievalMetadata
from backend.retrieval.retrieval_pipeline import RetrievalPipeline
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    query: str
    retrieval_results: list[RetrievalChunkResult] = field(default_factory=list)
    retrieval_metadata: RetrievalMetadata | None = None
    generation_result: GenerationResult | None = None
    total_latency_ms: int = 0
    correlation_id: str | None = None
    error: str | None = None


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline.

    Orchestrates:
        query text -> retrieval -> context building -> prompt building -> generation -> citations -> validation
    """

    def __init__(
        self,
        *,
        retrieval_pipeline: IntelligentRetrievalPipeline | RetrievalPipeline,
        generation_pipeline: GenerationPipeline,
        embedding_provider: Any | None = None,
    ):
        self._retrieval_pipeline = retrieval_pipeline
        self._generation_pipeline = generation_pipeline
        self._embedding_provider = embedding_provider

    async def query(
        self,
        *,
        query_text: str,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        filters: RetrievalFilters | None = None,
        correlation_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> RAGResult:
        t0 = time.perf_counter()
        result = RAGResult(query=query_text, correlation_id=correlation_id)

        try:
            retrieval_results, retrieval_metadata = self._retrieve(
                query_text=query_text,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                correlation_id=correlation_id,
                extra=extra,
            )
            result.retrieval_results = retrieval_results
            result.retrieval_metadata = retrieval_metadata
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("Retrieval failed: %s", str(exc), exc_info=True)
            result.total_latency_ms = latency_ms
            result.error = str(exc)
            return result

        try:
            generation_result = await self._generation_pipeline.generate(
                query=query_text,
                retrieved_chunks=retrieval_results,
                correlation_id=correlation_id,
            )
            result.generation_result = generation_result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("Generation failed: %s", str(exc), exc_info=True)
            result.total_latency_ms = latency_ms
            result.error = str(exc)
            return result

        latency_ms = int((time.perf_counter() - t0) * 1000)
        result.total_latency_ms = latency_ms
        return result

    def _retrieve(
        self,
        *,
        query_text: str,
        top_k: int,
        similarity_threshold: float | None,
        filters: RetrievalFilters | None,
        correlation_id: str | None,
        extra: dict[str, Any] | None,
    ) -> tuple[list[RetrievalChunkResult], RetrievalMetadata]:
        if self._embedding_provider is not None:
            embedding_result = self._embedding_provider.embed_text(query_text)
            query_vector = embedding_result.vector
        else:
            query_vector = [0.0] * 384

        request = RetrievalRequest(
            query_vector=query_vector,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id,
            extra={**(extra or {}), "query_text": query_text},
        )

        if isinstance(self._retrieval_pipeline, IntelligentRetrievalPipeline):
            return self._retrieval_pipeline.run(request)

        return self._retrieval_pipeline.run(request)
