from __future__ import annotations

import time
import logging
from typing import Any

from backend.retrieval.exceptions import RetrievalConfigurationError
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.retrieval.rerank.base_reranker import CrossEncoderLikeReranker


logger = logging.getLogger(__name__)


class CrossEncoderReranker(CrossEncoderLikeReranker):
    """
    Optional cross-encoder reranking stage.

    Uses sentence_transformers.CrossEncoder if available.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        model_name: str,
        top_n: int,
        batch_size: int = 16,
        max_length: int = 512,
        provider: str = "sentence_transformers",
    ):
        self._enabled = bool(enabled)
        self._model_name = model_name
        self._top_n = int(top_n)
        self._batch_size = int(batch_size)
        self._max_length = int(max_length)
        self._provider = provider

        self._model: Any | None = None
        if self._enabled:
            self._load_model()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def top_n(self) -> int:
        return self._top_n

    def _load_model(self) -> None:
        if self._provider != "sentence_transformers":
            raise RetrievalConfigurationError(f"Unsupported reranker provider: {self._provider}")

        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self._model = CrossEncoder(
                self._model_name,
                max_length=self._max_length,
            )
        except Exception as e:
            raise RetrievalConfigurationError(f"Failed to load CrossEncoder model: {e}") from e

    def rerank(
        self,
        *,
        query_text: str,
        candidates: list[RetrievalChunkResult],
        top_n: int,
    ) -> list[RetrievalChunkResult]:
        if not self._enabled:
            return candidates[:top_n]

        if not candidates:
            return []

        if self._model is None:
            raise RetrievalConfigurationError("CrossEncoder model is not loaded")

        pairs = [(query_text, c.chunk_text) for c in candidates[:top_n]]
        t0 = time.perf_counter()
        scores = self._model.predict(pairs, batch_size=self._batch_size)
        rerank_latency_ms = int((time.perf_counter() - t0) * 1000)

        # Stable sort by score desc, tie by original order.
        indexed = list(enumerate(candidates[:top_n]))
        indexed_sorted = sorted(
            indexed,
            key=lambda it: (float(scores[it[0]]), -it[0]),
            reverse=True,
        )

        out: list[RetrievalChunkResult] = []
        for new_rank, (old_idx, cand) in enumerate(indexed_sorted, start=1):
            meta = dict(cand.metadata or {})
            meta["rerank_score"] = float(scores[old_idx])
            meta["rerank_type"] = "cross_encoder"
            meta["rerank_latency_ms"] = rerank_latency_ms

            out.append(
                RetrievalChunkResult(
                    **cand.model_dump(exclude={"metadata", "similarity_score", "rank"}),
                    metadata=meta,
                    # keep similarity_score but update rank to rerank order
                    rank=new_rank,
                )
            )
        return out
