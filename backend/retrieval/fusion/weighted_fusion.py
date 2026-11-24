"""Weighted fusion for hybrid retrieval.

Combines dense and sparse retrieval results using configurable per-system weights,
rather than Reciprocal Rank Fusion which treats all systems equally.

Dense retrieval is typically more reliable for semantic queries, while sparse
(BM25) is better for exact keyword matches. Weighted fusion allows the system
to emphasize the more reliable signal.

Usage:
    fuser = WeightedFuser(weights={"dense": 0.7, "bm25": 0.2, "tfidf": 0.1})
    fused = fuser.fuse(dense_results=dense, sparse_results=sparse, tfidf_results=tfidf)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from backend.retrieval.retrieval_result import RetrievalChunkResult

logger = logging.getLogger(__name__)


@dataclass
class WeightedFusionStats:
    """Statistics for weighted fusion."""

    dense_count: int = 0
    sparse_count: int = 0
    tfidf_count: int = 0
    fused_count: int = 0
    duplicate_removed: int = 0
    fusion_latency_ms: float = 0.0
    fusion_weights: dict[str, float] = field(default_factory=dict)


class WeightedFuser:
    """
    Weighted score fusion for hybrid retrieval.

    Each system's raw scores are min-max normalized to [0, 1] independently,
    then combined as::

        fused = sum(w_sys * norm_score_sys) for each system containing the doc

    Documents appearing in multiple systems accumulate scores from each.
    This allows dense retrieval (typically more reliable for semantic queries)
    to be weighted higher than sparse BM25.
    """

    def __init__(
        self,
        *,
        weights: dict[str, float] | None = None,
        remove_duplicates: bool = True,
    ):
        """
        Args:
            weights: Weight per retrieval system. Keys are system names
                ("dense", "sparse", "tfidf"). Values are relative weights;
                they are normalized internally so they sum to 1.0.
            remove_duplicates: If True, duplicate chunks (same chunk_id)
                are merged, with scores accumulated across systems.
        """
        default_weights = {"dense": 0.7, "sparse": 0.2, "tfidf": 0.1}
        self.weights = dict(default_weights)
        if weights:
            self.weights.update(weights)
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        self._remove_duplicates = bool(remove_duplicates)
        self.stats = WeightedFusionStats(fusion_weights=dict(self.weights))

    def fuse(
        self,
        *,
        dense_results: list[RetrievalChunkResult],
        sparse_results: list[RetrievalChunkResult],
        tfidf_results: list[RetrievalChunkResult] | None = None,
    ) -> list[RetrievalChunkResult]:
        """Fuse results from multiple retrieval systems using weighted scores.

        Args:
            dense_results: Results from dense vector retrieval.
            sparse_results: Results from BM25 sparse retrieval.
            tfidf_results: Optional results from TF-IDF retrieval.

        Returns:
            Fused and ranked list of RetrievalChunkResult objects.
        """
        t0 = time.perf_counter()
        self.stats = WeightedFusionStats(
            dense_count=len(dense_results),
            sparse_count=len(sparse_results),
            tfidf_count=len(tfidf_results) if tfidf_results else 0,
            fusion_weights=dict(self.weights),
        )

        # Normalize scores within each system to [0, 1]
        normalized: dict[str, list[tuple[RetrievalChunkResult, float]]] = {}

        for sys_name, results in [
            ("dense", dense_results),
            ("sparse", sparse_results),
            ("tfidf", tfidf_results or []),
        ]:
            if not results:
                continue
            scores = [float(getattr(r, "similarity_score", 0.0) or 0.0) for r in results]
            s_min, s_max = min(scores), max(scores)
            span = s_max - s_min
            normed = []
            for r, s in zip(results, scores):
                norm = (s - s_min) / span if span > 0 else 0.0
                normed.append((r, norm))
            normalized[sys_name] = normed

        # Accumulate fused scores by chunk_id
        fused_scores: dict[str, float] = {}
        doc_map: dict[str, RetrievalChunkResult] = {}

        for sys_name, results in normalized.items():
            w = self.weights.get(sys_name, 0.0)
            for chunk, norm_score in results:
                key = str(chunk.chunk_id)
                fused_scores[key] = fused_scores.get(key, 0.0) + w * norm_score
                if key not in doc_map:
                    doc_map[key] = chunk

        # Sort by fused score descending
        sorted_keys = sorted(fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True)

        out: list[RetrievalChunkResult] = []
        for key in sorted_keys:
            chunk = doc_map[key]
            # Attach fusion score to metadata
            meta = dict(chunk.metadata or {})
            meta["fusion_score"] = float(fused_scores[key])
            meta["fusion_type"] = "weighted"
            out.append(
                RetrievalChunkResult(
                    **chunk.model_dump(exclude={"metadata"}),
                    metadata=meta,
                )
            )

        self.stats.fused_count = len(out)
        self.stats.fusion_latency_ms = int((time.perf_counter() - t0) * 1000)

        logger.debug(
            {
                "event": "weighted.fusion",
                "dense_count": self.stats.dense_count,
                "sparse_count": self.stats.sparse_count,
                "tfidf_count": self.stats.tfidf_count,
                "fused_count": self.stats.fused_count,
                "latency_ms": self.stats.fusion_latency_ms,
                "weights": self.weights,
            }
        )

        return out


def create_weighted_fuser(
    *,
    dense_weight: float = 0.7,
    sparse_weight: float = 0.2,
    tfidf_weight: float = 0.1,
    remove_duplicates: bool = True,
) -> WeightedFuser:
    """Factory function to create a WeightedFuser with common weight presets.

    Args:
        dense_weight: Weight for dense vector retrieval (default 0.7).
        sparse_weight: Weight for BM25 sparse retrieval (default 0.2).
        tfidf_weight: Weight for TF-IDF retrieval (default 0.1).
        remove_duplicates: If True, merge duplicate chunks across systems.

    Returns:
        Configured WeightedFuser instance.
    """
    total = dense_weight + sparse_weight + tfidf_weight
    if total <= 0:
        raise ValueError("At least one weight must be positive")
    return WeightedFuser(
        weights={
            "dense": dense_weight / total,
            "sparse": sparse_weight / total,
            "tfidf": tfidf_weight / total,
        },
        remove_duplicates=remove_duplicates,
    )
