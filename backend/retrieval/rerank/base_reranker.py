from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.retrieval.exceptions import RetrievalConfigurationError
from backend.retrieval.retrieval_result import RetrievalChunkResult


class CrossEncoderLikeReranker(ABC):
    """Reranker interface for optional re-ranking stage."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def top_n(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def rerank(
        self,
        *,
        query_text: str,
        candidates: list[RetrievalChunkResult],
        top_n: int,
    ) -> list[RetrievalChunkResult]:
        raise NotImplementedError


def require_enabled(reranker: Any) -> None:
    if reranker is None or not getattr(reranker, "enabled", False):
        raise RetrievalConfigurationError("Reranker is disabled")
