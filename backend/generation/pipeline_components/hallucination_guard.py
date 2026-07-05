from __future__ import annotations

import logging
from typing import Any

from backend.generation.models import ContextItem, GenerationResult

logger = logging.getLogger(__name__)


class HallucinationGuard:
    """Basic hallucination detection for generated responses."""

    def __init__(self, *, response_validator: Any, threshold: float = 0.3):
        self._response_validator = response_validator
        self._threshold = threshold

    def apply(
        self,
        *,
        query: str,
        result: GenerationResult,
        context_items: list[ContextItem],
    ) -> GenerationResult:
        if context_items and not result.citations:
            score = result.metadata.groundedness_score or 0.0
            if score < self._threshold:
                result.incomplete = True
                result.metadata.extra = result.metadata.extra or {}
                result.metadata.extra["hallucination_guard"] = {
                    "triggered": True,
                    "reason": "no_citations_provided",
                    "groundedness_score": score,
                }
                logger.warning(
                    "Hallucination guard triggered: no citations with low groundedness %.2f",
                    score,
                )
                return result

        result.metadata.extra = result.metadata.extra or {}
        result.metadata.extra["hallucination_guard"] = {
            "triggered": False,
        }
        return result
