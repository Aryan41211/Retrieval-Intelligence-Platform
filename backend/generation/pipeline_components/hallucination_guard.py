from __future__ import annotations

import logging
import re
from typing import Any

from backend.generation.models import ContextItem, GenerationResult

logger = logging.getLogger(__name__)


class HallucinationGuard:
    """Hallucination detection that grounds the answer against retrieved evidence.

    Previously the guard only flagged responses that omitted citations entirely;
    an answer that cited a plausible ``[doc_N]`` marker while fabricating claims
    sailed through. It now ALSO scores how much of the answer's substantive
    vocabulary is supported by the retrieved chunk text, so fabricated claims
    attached to real citations are caught.
    """

    def __init__(
        self, *, response_validator: Any, threshold: float = 0.3, lexical_threshold: float = 0.4
    ):
        self._response_validator = response_validator
        self._threshold = threshold
        self._lexical_threshold = lexical_threshold

    def apply(
        self,
        *,
        query: str,
        result: GenerationResult,
        context_items: list[ContextItem],
    ) -> GenerationResult:
        result.metadata.extra = result.metadata.extra or {}

        if not context_items:
            result.metadata.extra["hallucination_guard"] = {"triggered": False}
            return result

        answer = (result.answer or "").strip()
        evidence_coverage = self._evidence_coverage(answer, context_items)
        refusal = self._is_refusal(answer)

        guard: dict[str, Any] = {
            "triggered": False,
            "evidence_coverage": evidence_coverage,
        }

        if not result.citations and not refusal:
            score = result.metadata.groundedness_score or 0.0
            if score < self._threshold or evidence_coverage < self._lexical_threshold:
                guard.update(
                    {
                        "triggered": True,
                        "reason": "no_citations_or_unsubstantiated",
                        "groundedness_score": score,
                    }
                )
        elif result.citations and not refusal and evidence_coverage < self._lexical_threshold:
            guard.update(
                {
                    "triggered": True,
                    "reason": "claims_not_supported_by_evidence",
                }
            )

        result.metadata.extra["hallucination_guard"] = guard
        if guard["triggered"]:
            result.incomplete = True
            logger.warning(
                "Hallucination guard triggered: reason=%s coverage=%.2f",
                guard["reason"],
                evidence_coverage,
            )
        return result

    def _evidence_coverage(self, answer: str, context_items: list[ContextItem]) -> float:
        """Fraction of the answer's substantive tokens present in retrieved text.

        Deterministic lexical grounding: paraphrases still match many tokens, a
        fully fabricated sentence matches none. ``answer`` is untrusted model
        output and ``context`` is the retrieved evidence; we never compare the
        answer to itself or unrelated state.
        """
        answer_terms = _significant_terms(answer)
        if not answer_terms:
            return 1.0  # no substantive claims to verify
        corpus = " ".join(item.chunk_text for item in context_items)
        corpus_terms = _significant_terms(corpus)
        if not corpus_terms:
            return 0.0
        return len(answer_terms & corpus_terms) / len(answer_terms)

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        """Detect honest inability expressions that must not be flagged."""
        return bool(
            re.search(
                r"\b(i don'?t know|i am not sure|cannot answer|can'?t answer|"
                r"unable to answer|not enough information|insufficient information)\b",
                answer,
                flags=re.IGNORECASE,
            )
        )


_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")

# Common English function words carry no evidential signal; excluding them keeps
# the coverage score focused on substantive claims.
_STOPWORDS = frozenset(
    """
    a an and are as at be but by can could did do does for from had has have he
    her hers him his how i if in into is it its may me my no nor not of off on
    or our ours out over shall she should so some such than that the their theirs
    them then there these they this those to too was we were what when where which
    while who whom why will with would you your yours
    """.split()
)


def _significant_terms(text: str) -> set[str]:
    return {t for t in _TOKEN_PATTERN.findall(text.lower()) if t not in _STOPWORDS}
