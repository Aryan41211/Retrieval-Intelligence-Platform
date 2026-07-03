from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.retrieval.exceptions import (
    EmptyRetrievalResultError,
    RetrievalConfigurationError,
    RetrievalError,
)
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_metadata import RetrievalMetadata
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult

from backend.retrieval.rerank.cross_encoder_reranker import CrossEncoderReranker
from backend.retrieval.query_expansion.query_expander import QueryExpander
from backend.retrieval.sparse.bm25_retriever import BM25Retriever
from backend.retrieval.fusion.rrf_fusion import RRFFuser
from backend.retrieval.topk.dynamic_topk import DynamicTopKSelector
from backend.retrieval.utils.analytics import RetrievalAnalytics

logger = logging.getLogger(__name__)


class IntelligentRetrievalPipeline:
    """
    Intelligent retrieval pipeline:
    Query expansion → Dense retrieval → BM25 retrieval → RRF fusion → optional reranking → dynamic top-k.
    """

    def __init__(
        self,
        *,
        dense_engine: RetrievalEngine,
        bm25_retriever: BM25Retriever,
        fusion: RRFFuser,
        reranker: CrossEncoderReranker | None,
        query_expander: QueryExpander,
        topk_selector: DynamicTopKSelector,
        analytics: RetrievalAnalytics | None = None,
    ):
        self._dense_engine = dense_engine
        self._bm25_retriever = bm25_retriever
        self._fusion = fusion
        self._reranker = reranker
        self._query_expander = query_expander
        self._topk_selector = topk_selector
        self._analytics = analytics or RetrievalAnalytics()

    def run(self, request: RetrievalRequest) -> tuple[list[RetrievalChunkResult], RetrievalMetadata]:
        correlation_id = request.correlation_id
        t0_total = time.perf_counter()

        # Query text is required for expansion + reranking.
        query_text = request.extra.get("query_text")
        if not isinstance(query_text, str) or not query_text.strip():
            # We allow pipeline to still function (expansion/reranking may be skipped).
            logger.warning(
                json.dumps(
                    {
                        "event": "intelligent_retrieval.missing_query_text",
                        "correlation_id": correlation_id,
                    }
                )
            )

        expanded_query_text = query_text
        query_expand_meta: dict[str, Any] = {}
        if query_text:
            try:
                t_exp = time.perf_counter()
                expanded_query_text, query_expand_meta = self._query_expander.expand(query_text)
                self._analytics.add("query_expansion_latency_ms", int((time.perf_counter() - t_exp) * 1000))
            except Exception as e:
                logger.warning(
                    json.dumps(
                        {
                            "event": "intelligent_retrieval.query_expansion_failed",
                            "correlation_id": correlation_id,
                            "error": str(e),
                        }
                    )
                )

        # Stage: Dense retrieval
        dense_results: list[RetrievalChunkResult] = []
        dense_latency_ms = 0
        if self._dense_engine is not None:
            t_dense = time.perf_counter()
            dense_results = self._dense_engine.retrieve(request)
            dense_latency_ms = int((time.perf_counter() - t_dense) * 1000)

        # Stage: BM25 retrieval
        sparse_results: list[RetrievalChunkResult] = []
        bm25_latency_ms = 0
        bm25_query_for_scoring = expanded_query_text or query_text or ""
        if bm25_query_for_scoring.strip():
            try:
                t_bm25 = time.perf_counter()
                sparse_results = self._bm25_retriever.retrieve(
                    bm25_query_for_scoring,
                    top_k=request.top_k,
                    filters=request.filters,
                    base_request=request,
                )
                bm25_latency_ms = int((time.perf_counter() - t_bm25) * 1000)
            except Exception as e:
                logger.warning(
                    json.dumps(
                        {
                            "event": "intelligent_retrieval.bm25_failed_fallback_to_dense",
                            "correlation_id": correlation_id,
                            "error": str(e),
                        }
                    )
                )
                sparse_results = []
                bm25_latency_ms = 0

        # Fusion stage
        t_fusion = time.perf_counter()
        fused_candidates = self._fusion.fuse(
            dense_results=dense_results,
            sparse_results=sparse_results,
        )
        fusion_latency_ms = int((time.perf_counter() - t_fusion) * 1000)

        # Optional reranking stage (skip if missing/disabled)
        rerank_latency_ms = 0
        if self._reranker is not None and self._reranker.enabled:
            if expanded_query_text and expanded_query_text.strip():
                try:
                    t_rerank = time.perf_counter()
                    fused_candidates = self._reranker.rerank(
                        query_text=expanded_query_text,
                        candidates=fused_candidates,
                        top_n=min(self._reranker.top_n, len(fused_candidates)),
                    )
                    rerank_latency_ms = int((time.perf_counter() - t_rerank) * 1000)
                except RetrievalConfigurationError:
                    raise
                except Exception as e:
                    logger.warning(
                        json.dumps(
                            {
                                "event": "intelligent_retrieval.rerank_failed_skip",
                                "correlation_id": correlation_id,
                                "error": str(e),
                            }
                        )
                    )
                    rerank_latency_ms = 0

        # Dynamic Top-K selection
        t_topk = time.perf_counter()
        final_results, topk_meta = self._topk_selector.select(
            candidates=fused_candidates,
            request=request,
        )
        dynamic_topk_latency_ms = int((time.perf_counter() - t_topk) * 1000)

        if not final_results:
            latency_ms = int((time.perf_counter() - t0_total) * 1000)
            raise EmptyRetrievalResultError(
                details={
                    "correlation_id": correlation_id,
                    "latency_ms": latency_ms,
                    "top_k": request.top_k,
                }
            )

        # Build metadata
        total_latency_ms = int((time.perf_counter() - t0_total) * 1000)
        final_context_chars = sum(len(r.chunk_text or "") for r in final_results)

        retrieval_timestamp = request.retrieval_timestamp or datetime.now(UTC)

        metadata = RetrievalMetadata(
            retrieval_latency_ms=total_latency_ms,
            total_candidates=len(fused_candidates),
            retrieved_chunks=len(final_results),
            similarity_threshold=request.similarity_threshold,
            methods_used=self._build_methods_used(dense_results, sparse_results),
            retrieval_timestamp=retrieval_timestamp,
        )
        metadata.extra = {
            "analytics": {
                "dense_retrieval_latency_ms": dense_latency_ms,
                "bm25_latency_ms": bm25_latency_ms,
                "fusion_latency_ms": fusion_latency_ms,
                "reranking_latency_ms": rerank_latency_ms,
                "dynamic_topk_latency_ms": dynamic_topk_latency_ms,
                "total_retrieval_latency_ms": total_latency_ms,
                "candidate_count": len(fused_candidates),
                "final_context_size_chars": final_context_chars,
            },
            "query_expansion": query_expand_meta,
            "topk": topk_meta,
            # RRFFusion.stats may contain non-JSON-serializable dataclass instances; store as dict.
            "fusion": vars(self._fusion.stats) if hasattr(self._fusion, "stats") and self._fusion.stats is not None else {},
            "strategy": {
                "dense_enabled": True,
                "sparse_enabled": len(sparse_results) > 0,
                "rerank_enabled": self._reranker is not None and self._reranker.enabled,
            },
        }

        # Log summary + ranking changes (lightweight overlap signal)
        try:
            dense_chunk_ids = [str(r.chunk_id) for r in dense_results[: min(len(dense_results), request.top_k)]]
            final_chunk_ids = [str(r.chunk_id) for r in final_results]
            overlap = len(set(dense_chunk_ids).intersection(final_chunk_ids))
        except Exception:
            overlap = None

        logger.info(
            json.dumps(
                {
                    "event": "intelligent_retrieval.success",
                    "correlation_id": correlation_id,
                    "retrieved_chunks": len(final_results),
                    "total_candidates": len(fused_candidates),
                    "latency_ms": total_latency_ms,
                    "top_k": request.top_k,
                    "fusion": vars(self._fusion.stats) if hasattr(self._fusion, "stats") and self._fusion.stats is not None else {},
                    "overlap_dense_to_final": overlap,
                }
            )
        )

        return final_results, metadata

    @staticmethod
    def _build_methods_used(dense_results: list[RetrievalChunkResult], sparse_results: list[RetrievalChunkResult]) -> list[str]:
        methods: list[str] = []
        if dense_results:
            methods.append("vector_similarity")
        if sparse_results:
            methods.append("bm25")
        if len(methods) >= 2:
            methods.append("hybrid_rrf")
        return methods
