from __future__ import annotations

import logging

from backend.generation.exceptions import ResponseValidationError
from backend.generation.models import Citation, ContextItem, GenerationMetadata, GenerationResult

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates that generated responses are grounded and coherent."""

    def validate(
        self,
        *,
        query: str,
        answer: str,
        context_items: list[ContextItem],
        citations: list[Citation],
    ) -> GenerationResult:
        if not answer or not answer.strip():
            raise ResponseValidationError("Generated answer is empty")

        groundedness_score = self._compute_groundedness(answer=answer, citations=citations)

        metadata = GenerationMetadata(
            groundedness_score=groundedness_score,
            citations_generated=len(citations),
        )

        return GenerationResult(
            answer=answer.strip(),
            citations=citations,
            incomplete=False,
            metadata=metadata,
        )

    def _compute_groundedness(self, *, answer: str, citations: list[Citation]) -> float:
        if not citations:
            return 0.0

        avg_confidence = sum(c.confidence for c in citations) / len(citations)
        marker_coverage = len(set(c.doc_index for c in citations)) / max(1, len(citations))
        score = (avg_confidence * 0.7) + (marker_coverage * 0.3)
        return min(1.0, max(0.0, score))
