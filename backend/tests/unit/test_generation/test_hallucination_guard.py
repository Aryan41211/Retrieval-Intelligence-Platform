"""Unit tests for the evidence-aware hallucination guard."""

from backend.generation.models import ContextItem, GenerationResult
from backend.generation.pipeline_components.hallucination_guard import HallucinationGuard


def _ctx(*texts: str) -> list[ContextItem]:
    return [
        ContextItem(
            chunk_id=f"c{i}",
            document_id=f"d{i}",
            chunk_text=t,
            rank=i,
            similarity_score=0.8,
        )
        for i, t in enumerate(texts, start=1)
    ]


def _result(answer: str, *, citations: bool = True, groundedness: float = 0.8) -> GenerationResult:
    result = GenerationResult(
        answer=answer,
        citations=(
            [
                {
                    "doc_index": 1,
                    "chunk_id": "c1",
                    "document_id": "d1",
                    "chunk_text": "Python is a programming language.",
                    "confidence": 0.8,
                }
            ]
            if citations
            else []
        ),
    )
    result.metadata.groundedness_score = groundedness
    return result


def _guard(**kwargs) -> HallucinationGuard:
    return HallucinationGuard(response_validator=object(), **kwargs)


def test_supported_answer_not_flagged():
    guard = _guard()
    result = _result("Python is a programming language.")
    out = guard.apply(
        query="q", result=result, context_items=_ctx("Python is a programming language.")
    )
    assert not out.incomplete
    assert out.metadata.extra["hallucination_guard"]["triggered"] is False
    assert out.metadata.extra["hallucination_guard"]["evidence_coverage"] == 1.0


def test_fabricated_claim_with_citation_is_flagged():
    """A hallucinated elaboration attached to a real citation must be caught."""
    guard = _guard()
    result = _result("Python runs natively on Mars and the Moon.")
    out = guard.apply(
        query="q",
        result=result,
        context_items=_ctx("Python is a programming language."),
    )
    assert out.incomplete is True
    info = out.metadata.extra["hallucination_guard"]
    assert info["triggered"] is True
    assert info["reason"] == "claims_not_supported_by_evidence"
    assert info["evidence_coverage"] < 1.0


def test_no_citations_and_unsubstantiated_flagged():
    guard = _guard()
    result = _result("The answer is forty-two.", citations=False)
    out = guard.apply(
        query="q", result=result, context_items=_ctx("Python is a programming language.")
    )
    assert out.incomplete is True
    assert out.metadata.extra["hallucination_guard"]["triggered"] is True


def test_no_context_never_flagged():
    guard = _guard()
    result = _result("Anything at all.")
    out = guard.apply(query="q", result=result, context_items=[])
    assert not out.incomplete
    assert out.metadata.extra["hallucination_guard"]["triggered"] is False


def test_refusal_is_not_flagged_as_hallucination():
    guard = _guard()
    result = _result("I don't know.", citations=False)
    out = guard.apply(
        query="q", result=result, context_items=_ctx("Python is a programming language.")
    )
    assert not out.incomplete
    assert out.metadata.extra["hallucination_guard"]["triggered"] is False


def test_paraphrase_with_overlap_not_flagged():
    guard = _guard()
    result = _result("Python emphasizes readable code.", citations=True)
    out = guard.apply(
        query="q",
        result=result,
        context_items=_ctx("It emphasizes code readability.", "Python is a programming language."),
    )
    assert not out.incomplete


def test_lexical_threshold_respected():
    guard = _guard(lexical_threshold=0.9)
    result = _result("Python is a programming language with fast drones.")
    out = guard.apply(
        query="q",
        result=result,
        context_items=_ctx("Python is a programming language."),
    )
    assert out.incomplete is True
    assert out.metadata.extra["hallucination_guard"]["reason"] == "claims_not_supported_by_evidence"
