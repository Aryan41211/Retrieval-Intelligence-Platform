"""Unit tests for the Ragas evaluation dataset schema."""

import pytest

from backend.evaluation.core.evaluator import EvaluationSample


class TestEvaluationSample:
    def test_valid_sample(self):
        s = EvaluationSample(
            question="What is the capital of France?",
            ground_truth="Paris",
            answer="Paris is the capital of France.",
            contexts=["Paris is the capital and most populous city of France."],
        )
        assert s.question == "What is the capital of France?"
        assert s.ground_truth == "Paris"
        assert s.answer == "Paris is the capital of France."
        assert s.contexts == ["Paris is the capital and most populous city of France."]
        assert s.metadata == {}

    def test_sample_with_metadata(self):
        s = EvaluationSample(
            question="Q",
            ground_truth="A",
            answer="A",
            contexts=["C"],
            metadata={"sample_id": "s1", "dataset": "test"},
        )
        assert s.metadata == {"sample_id": "s1", "dataset": "test"}

    def test_empty_contexts_default(self):
        s = EvaluationSample(question="Q", ground_truth="A", answer="A")
        assert s.contexts == []

    def test_contexts_coerced_to_strings(self):
        s = EvaluationSample(
            question="Q",
            ground_truth="A",
            answer="A",
            contexts=[1, 2.5, None],
        )
        assert s.contexts == ["1", "2.5", "None"]

    def test_missing_required_field(self):
        with pytest.raises(Exception):
            EvaluationSample(question="Q", answer="A")  # missing ground_truth
