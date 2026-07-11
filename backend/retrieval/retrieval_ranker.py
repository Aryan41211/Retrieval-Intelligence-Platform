from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.retrieval.retrieval_result import RetrievalChunkResult


class RetrievalRanker(ABC):
    """
    Ranker interface for future extension (BM25/RRF/Cross-Encoder/etc).

    Current Phase 5.2 uses vector similarity only, so the default implementation
    preserves the provided ordering.
    """

    @abstractmethod
    def rank(
        self, query: Any, candidates: list[RetrievalChunkResult], top_k: int
    ) -> list[RetrievalChunkResult]:
        raise NotImplementedError


class VectorSimilarityRanker(RetrievalRanker):
    """Initial ranker using vector similarity only."""

    def rank(
        self,
        query: Any,
        candidates: list[RetrievalChunkResult],
        top_k: int,
    ) -> list[RetrievalChunkResult]:
        # Candidates are expected to be already ordered by similarity_score desc.
        return candidates[:top_k]
