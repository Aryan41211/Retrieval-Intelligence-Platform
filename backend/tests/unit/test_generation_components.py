"""Unit tests for grounded generation pipeline components.

Covers citation extraction, response validation, and hallucination guard
behavior with deterministic inputs (no LLM calls).
"""

import pytest

from backend.generation.models import ContextItem
from backend.generation.pipeline_components.citation_generator import CitationGenerator
from backend.generation.pipeline_components.hallucination_guard import HallucinationGuard
from backend.generation.pipeline_components.response_validator import ResponseValidator


class TestCitationGenerator:
    def test_extracts_citations_from_markers(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="The capital of France is Paris.",
                rank=1,
                similarity_score=0.9,
                source_filename="france.txt",
            ),
            ContextItem(
                chunk_id="c2",
                document_id="d2",
                chunk_text="The capital of Germany is Berlin.",
                rank=2,
                similarity_score=0.8,
                source_filename="germany.txt",
            ),
        ]

        gen = CitationGenerator()
        citations = gen.generate(
            answer="Paris [doc_1] and Berlin [doc_2] are capitals.",
            context_items=items,
        )

        assert len(citations) == 2
        assert citations[0].doc_index == 1
        assert citations[0].chunk_id == "c1"
        assert citations[0].document_id == "d1"
        assert citations[1].doc_index == 2
        assert citations[1].chunk_id == "c2"

    def test_ignores_out_of_range_markers(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Paris",
                rank=1,
                similarity_score=0.9,
            )
        ]

        gen = CitationGenerator()
        citations = gen.generate(
            answer="See [doc_1] and [doc_5].",
            context_items=items,
        )
        assert len(citations) == 1
        assert citations[0].doc_index == 1

    def test_returns_empty_for_no_markers(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Paris",
                rank=1,
                similarity_score=0.9,
            )
        ]

        gen = CitationGenerator()
        citations = gen.generate(answer="No citations here.", context_items=items)
        assert citations == []

    def test_returns_empty_for_no_context(self):
        gen = CitationGenerator()
        citations = gen.generate(answer="Some answer.", context_items=[])
        assert citations == []


class TestResponseValidator:
    def test_validates_grounded_answer(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Paris is the capital of France.",
                rank=1,
                similarity_score=0.9,
            )
        ]

        validator = ResponseValidator()
        result = validator.validate(
            query="What is the capital of France?",
            answer="Paris is the capital of France. [doc_1]",
            context_items=items,
            citations=[],
        )

        assert result.incomplete is False
        assert result.answer == "Paris is the capital of France. [doc_1]"
        assert 0.0 <= result.metadata.groundedness_score <= 1.0

    def test_rejects_empty_answer(self):
        validator = ResponseValidator()
        with pytest.raises(Exception):
            validator.validate(
                query="Q",
                answer="",
                context_items=[],
                citations=[],
            )


class TestHallucinationGuard:
    def test_no_citations_with_low_groundedness_triggers_guard(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Paris is the capital of France.",
                rank=1,
                similarity_score=0.9,
            )
        ]

        from backend.generation.models import GenerationResult, GenerationMetadata

        result = GenerationResult(
            answer="The capital of France is Paris.",
            citations=[],
            metadata=GenerationMetadata(groundedness_score=0.05),
        )

        guard = HallucinationGuard(response_validator=None)  # type: ignore[arg-type]
        output = guard.apply(
            query="What is the capital of France?",
            result=result,
            context_items=items,
        )

        assert output.metadata.extra["hallucination_guard"]["triggered"] is True
        assert output.incomplete is True

    def test_refusal_not_flagged(self):
        items = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Paris is the capital of France.",
                rank=1,
                similarity_score=0.9,
            )
        ]

        from backend.generation.models import GenerationResult, GenerationMetadata

        result = GenerationResult(
            answer="I don't know.",
            citations=[],
            metadata=GenerationMetadata(groundedness_score=0.0),
        )

        guard = HallucinationGuard(response_validator=None)  # type: ignore[arg-type]
        output = guard.apply(
            query="What is the capital of France?",
            result=result,
            context_items=items,
        )

        assert output.metadata.extra["hallucination_guard"]["triggered"] is False
        assert output.incomplete is False

    def test_evidence_coverage_score(self):
        guard = HallucinationGuard(response_validator=None)  # type: ignore[arg-type]

        coverage = guard._evidence_coverage(
            answer="Paris is the capital of France.",
            context_items=[
                ContextItem(
                    chunk_id="c1",
                    document_id="d1",
                    chunk_text="Paris is the capital of France.",
                    rank=1,
                    similarity_score=0.9,
                )
            ],
        )
        assert coverage > 0.5

        coverage_empty = guard._evidence_coverage(
            answer="The moon is made of green cheese.",
            context_items=[
                ContextItem(
                    chunk_id="c1",
                    document_id="d1",
                    chunk_text="Paris is the capital of France.",
                    rank=1,
                    similarity_score=0.9,
                )
            ],
        )
        assert coverage_empty < 0.5
