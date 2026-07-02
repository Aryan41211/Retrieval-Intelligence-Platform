from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

from backend.retrieval.exceptions import EmptyRetrievalResultError, RetrievalError
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_metadata import RetrievalMetadata
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Semantic retrieval pipeline: executes engine + returns structured metadata.

    Note: This phase intentionally implements ONLY semantic/dense retrieval.
    """

    def __init__(self, engine: RetrievalEngine):
        self._engine = engine

    def run(self, request: RetrievalRequest) -> tuple[list[RetrievalChunkResult], RetrievalMetadata]:
        correlation_id = request.correlation_id
        t0 = time.perf_counter()

        try:
            results = self._engine.retrieve(request)
        except EmptyRetrievalResultError:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning(
                json.dumps(
                    {
                        "event": "retrieval.empty",
                        "correlation_id": correlation_id,
                        "latency_ms": latency_ms,
                        "top_k": request.top_k,
                        "similarity_threshold": request.similarity_threshold,
                    }
                )
            )
            raise
        except RetrievalError:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error(
                json.dumps(
                    {
                        "event": "retrieval.error",
                        "correlation_id": correlation_id,
                        "latency_ms": latency_ms,
                        "top_k": request.top_k,
                    }
                ),
                exc_info=True,
            )
            raise

        latency_ms = int((time.perf_counter() - t0) * 1000)

        metadata = RetrievalMetadata(
            retrieval_latency_ms=latency_ms,
            total_candidates=len(results),
            retrieved_chunks=len(results),
            similarity_threshold=request.similarity_threshold,
            methods_used=["vector_similarity"],
            retrieval_timestamp=request.retrieval_timestamp or datetime.now(UTC),
        )

        # Top scores are helpful for debugging/observability.
        if results:
            metadata.top_scores = [r.similarity_score for r in results[: min(len(results), request.top_k)]]

        logger.info(
            json.dumps(
                {
                    "event": "retrieval.success",
                    "correlation_id": correlation_id,
                    "retrieved_chunks": len(results),
                    "latency_ms": latency_ms,
                    "top_k": request.top_k,
                    "filters": request.filters.model_dump() if request.filters else None,
                    "top_scores": metadata.top_scores,
                }
            )
        )

        return results, metadata
