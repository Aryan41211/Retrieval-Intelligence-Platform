from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult


@dataclass
class DynamicTopKResult:
    k: int
    confidence: float
    score_spread: float
    strategy: str
    extra: dict[str, Any] = field(default_factory=dict)


class DynamicTopKSelector:
    """
    Adaptive Top-K selection based on retrieval confidence.

    Lightweight heuristic:
    - Use score spread (max - min normalized) from candidate similarity_score.
    - Map spread to confidence in [0,1].
    - Convert confidence to k between min_k and max_k.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        min_k: int,
        max_k: int,
        min_confidence: float,
        max_confidence: float,
    ):
        self._enabled = bool(enabled)
        self._min_k = int(min_k)
        self._max_k = int(max_k)
        self._min_confidence = float(min_confidence)
        self._max_confidence = float(max_confidence)

    def select(
        self,
        *,
        candidates: list[RetrievalChunkResult],
        request: RetrievalRequest,
    ) -> tuple[list[RetrievalChunkResult], dict[str, Any]]:
        if not self._enabled:
            k = min(len(candidates), int(request.top_k))
            return candidates[:k], {"enabled": False, "k": k}

        if not candidates:
            return [], {"enabled": True, "k": 0, "confidence": 0.0}

        scores = [float(getattr(c, "similarity_score", 0.0) or 0.0) for c in candidates]
        score_min = min(scores)
        score_max = max(scores)
        spread = score_max - score_min

        # Normalize spread to [0,1] using a soft scaling.
        # similarity_score is expected in [0,1] but RRF/fusion may keep it as-is;
        # still clamp to be safe.
        spread_clamped = max(0.0, min(1.0, float(spread)))
        confidence = self._confidence_from_spread(spread_clamped)

        k = self._k_from_confidence(confidence)

        # Ensure at least min_k (unless fewer candidates) and at most max_k.
        k = max(self._min_k, min(k, self._max_k))
        k = min(k, len(candidates))

        out_meta: dict[str, Any] = {
            "enabled": True,
            "k": k,
            "confidence": confidence,
            "score_spread": spread,
            "strategy": "score_spread_confidence",
        }
        return candidates[:k], out_meta

    def _confidence_from_spread(self, spread_clamped: float) -> float:
        if self._max_confidence <= self._min_confidence:
            return self._min_confidence
        # Linear map from spread [0..1] to confidence range.
        # confidence increases as spread increases.
        conf = self._min_confidence + (self._max_confidence - self._min_confidence) * spread_clamped
        return max(0.0, min(1.0, conf))

    def _k_from_confidence(self, confidence: float) -> int:
        if self._max_k <= self._min_k:
            return self._min_k
        # confidence 0 => min_k, confidence 1 => max_k
        ratio = max(0.0, min(1.0, confidence))
        val = self._min_k + int(round((self._max_k - self._min_k) * ratio))
        return int(val)
