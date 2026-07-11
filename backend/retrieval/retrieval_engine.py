from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from backend.retrieval.exceptions import (
    EmptyRetrievalResultError,
    RetrievalConfigurationError,
    RetrievalError,
)
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_ranker import RetrievalRanker, VectorSimilarityRanker
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.vectorstore.base_vector_store import BaseVectorStore

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    Provider-independent semantic retrieval engine.

    It communicates ONLY with BaseVectorStore (via search/batch_search),
    never with FAISS/Chroma/etc directly.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        ranker: RetrievalRanker | None = None,
    ):
        self._vector_store = vector_store
        self._ranker = ranker or VectorSimilarityRanker()

        if self._vector_store is None:
            raise RetrievalConfigurationError("vector_store must be provided")

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalChunkResult]:
        """
        Retrieve top-k chunks for a single query vector.

        Note: similarity threshold and metadata filtering are applied by the vector store,
        but this engine still enforces empty-result handling and ranking extensibility.
        """
        t0 = time.perf_counter()
        try:
            raw_results = self._vector_store.search(request)
        except Exception as e:
            raise RetrievalError(f"Vector store search failed: {e}") from e

        # Vector store contract: returns ranked by similarity.
        ranked = self._ranker.rank(request.query_vector, raw_results, request.top_k)

        latency_ms = int((time.perf_counter() - t0) * 1000)

        if not ranked:
            raise EmptyRetrievalResultError(
                details={"top_k": request.top_k, "latency_ms": latency_ms}
            )

        # Stash latency in result-level timestamp already; metadata is returned by pipeline normally.
        return ranked

    def retrieve_batch(
        self,
        requests: list[RetrievalRequest],
    ) -> list[list[RetrievalChunkResult]]:
        if not requests:
            return []

        t0 = time.perf_counter()
        try:
            raw_batch = self._vector_store.batch_search(requests)
        except Exception as e:
            raise RetrievalError(f"Vector store batch_search failed: {e}") from e

        if len(raw_batch) != len(requests):
            raise RetrievalError(
                "Vector store batch_search returned mismatched batch sizes",
                details={"expected": len(requests), "actual": len(raw_batch)},
            )

        out: list[list[RetrievalChunkResult]] = []
        for req, raw_results in zip(requests, raw_batch, strict=False):
            ranked = self._ranker.rank(req.query_vector, raw_results, req.top_k)
            out.append(ranked)

        _ = int((time.perf_counter() - t0) * 1000)
        return out

    def retrieve_with_filters(
        self,
        query_vector: list[float],
        top_k: int,
        similarity_threshold: float | None = None,
        filters: RetrievalFilters | None = None,
        *,
        correlation_id: str | None = None,
        retrieval_timestamp: datetime | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[RetrievalChunkResult]:
        request = RetrievalRequest(
            query_vector=query_vector,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id,
            retrieval_timestamp=retrieval_timestamp or datetime.now(UTC),
            extra=extra or {},
        )
        return self.retrieve(request)

    def retrieve_by_document(
        self,
        query_vector: list[float],
        top_k: int,
        document_ids: list[UUID],
        similarity_threshold: float | None = None,
        *,
        correlation_id: str | None = None,
        retrieval_timestamp: datetime | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[RetrievalChunkResult]:
        filters = RetrievalFilters(document_ids=document_ids)
        return self.retrieve_with_filters(
            query_vector=query_vector,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id,
            retrieval_timestamp=retrieval_timestamp,
            extra=extra,
        )

    def retrieve_by_chunk(
        self,
        query_vector: list[float],
        top_k: int,
        chunk_ids: list[UUID],
        similarity_threshold: float | None = None,
        *,
        correlation_id: str | None = None,
        retrieval_timestamp: datetime | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[RetrievalChunkResult]:
        # Current RetrievalFilters model has no explicit chunk_ids field.
        # We use custom metadata filtering as a provider-agnostic hook.
        filters = RetrievalFilters(custom={"chunk_id": [str(c) for c in chunk_ids]})
        return self.retrieve_with_filters(
            query_vector=query_vector,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id,
            retrieval_timestamp=retrieval_timestamp,
            extra=extra,
        )
