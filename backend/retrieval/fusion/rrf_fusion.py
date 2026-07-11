from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from backend.retrieval.retrieval_result import RetrievalChunkResult

logger = logging.getLogger(__name__)


@dataclass
class RRFFusionStats:
    dense_count: int = 0
    sparse_count: int = 0
    fused_count: int = 0
    duplicate_removed: int = 0
    fusion_latency_ms: int = 0
    fusion_parameters: dict[str, Any] = field(default_factory=dict)


class RRFFuser:
    """
    Reciprocal Rank Fusion (RRF), independent from dense/sparse implementations.

    Stable ranking:
    - Uses RRF score primarily.
    - For ties, preserves the earliest occurrence among inputs (dense then sparse by default).
    """

    def __init__(
        self,
        *,
        k: int = 60,
        remove_duplicates: bool = True,
        stable_ranking: bool = True,
    ):
        self._k = int(k)
        self._remove_duplicates = bool(remove_duplicates)
        self._stable_ranking = bool(stable_ranking)
        self.stats = RRFFusionStats(fusion_parameters={"k": self._k})

    def fuse(
        self,
        *,
        dense_results: list[RetrievalChunkResult],
        sparse_results: list[RetrievalChunkResult],
    ) -> list[RetrievalChunkResult]:
        t0 = time.perf_counter()
        self.stats = RRFFusionStats(
            dense_count=len(dense_results),
            sparse_count=len(sparse_results),
            fusion_parameters={
                "k": self._k,
                "remove_duplicates": self._remove_duplicates,
                "stable_ranking": self._stable_ranking,
            },
        )

        # Key by chunk_id (stable and unique)
        fused: dict[str, RetrievalChunkResult] = {}
        rrf_scores: dict[str, float] = {}
        first_seen_order: dict[str, int] = {}

        def _rrf(rank: int) -> float:
            # rank is 1-based
            return 1.0 / (self._k + rank)

        # Dense contribution
        for idx, r in enumerate(dense_results, start=1):
            key = str(r.chunk_id)
            if key not in first_seen_order:
                first_seen_order[key] = idx  # dense order preference
            score_add = _rrf(r.rank if r.rank else idx)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + score_add
            fused.setdefault(key, r)

        # Sparse contribution
        for idx, r in enumerate(sparse_results, start=1):
            key = str(r.chunk_id)
            if key not in first_seen_order:
                first_seen_order[key] = len(dense_results) + idx
            score_add = _rrf(r.rank if r.rank else idx)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + score_add
            fused.setdefault(key, r)

        # Attach fusion scores into metadata for transparency
        for key, chunk in fused.items():
            existing_meta = chunk.metadata or {}
            existing_meta = dict(existing_meta)
            existing_meta["fusion_score"] = float(rrf_scores.get(key, 0.0))
            existing_meta["fusion_type"] = "rrf"
            # Keep chunk_text etc intact; we cannot mutate pydantic objects reliably,
            # so create a new object with updated metadata.
            fused[key] = RetrievalChunkResult(
                **chunk.model_dump(exclude={"metadata"}),
                metadata=existing_meta,
            )

        duplicates_removed = (
            0 if not self._remove_duplicates else max(0, len(fused) - len(set(fused.keys())))
        )

        # Sort: by fusion_score desc; for tie preserve stable order
        def sort_key(item: RetrievalChunkResult) -> tuple[float, int]:
            key = str(item.chunk_id)
            score = float(item.metadata.get("fusion_score", 0.0))
            # Higher score first, then earlier first_seen_order first
            return (-score, first_seen_order.get(key, 0))

        out = sorted(fused.values(), key=sort_key)

        self.stats.fused_count = len(out)
        self.stats.duplicate_removed = int(duplicates_removed)
        self.stats.fusion_latency_ms = int((time.perf_counter() - t0) * 1000)

        logger.debug(
            json.dumps(
                {
                    "event": "rrf.fusion",
                    "dense_count": self.stats.dense_count,
                    "sparse_count": self.stats.sparse_count,
                    "fused_count": self.stats.fused_count,
                    "latency_ms": self.stats.fusion_latency_ms,
                }
            )
        )

        return out
