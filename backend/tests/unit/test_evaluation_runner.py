"""Unit tests for the Ragas evaluation runner (not-configured path)."""

from backend.evaluation.core.evaluator import (
    EvaluationReport,
    EvaluationSample,
    RagasEvaluator,
    run_evaluation,
)


def test_evaluator_not_configured_without_provider(monkeypatch):
    monkeypatch.setenv("GENERATION_PROVIDER", "fake")
    monkeypatch.delenv("GENERATION_API_KEY", raising=False)

    evaluator = RagasEvaluator()
    assert evaluator._configured is False
    assert evaluator._provider_name == "fake"

    report = evaluator.evaluate(
        [
            EvaluationSample(
                question="Q1",
                ground_truth="A1",
                answer="A1",
                contexts=["C1"],
            )
        ]
    )
    assert isinstance(report, EvaluationReport)
    assert report.total_samples == 1
    assert report.successful_evaluations == 0
    assert report.failed_evaluations == 0
    assert report.metrics == {}
    assert report.provider == "fake"
    assert report.note is not None
    assert "not configured" in report.note.lower()

    # Per-sample result should carry the error.
    ps = report.per_sample[0]
    assert ps.question == "Q1"
    assert ps.error is not None
    assert ps.metrics == {}


def test_run_evaluation_convenience_wrapper(monkeypatch):
    monkeypatch.setenv("GENERATION_PROVIDER", "fake")
    monkeypatch.delenv("GENERATION_API_KEY", raising=False)

    report = run_evaluation(
        [
            EvaluationSample(
                question="Q1",
                ground_truth="A1",
                answer="A1",
                contexts=["C1"],
            ),
            EvaluationSample(
                question="Q2",
                ground_truth="A2",
                answer="A2",
                contexts=["C2"],
            ),
        ]
    )
    assert report.total_samples == 2
    assert report.successful_evaluations == 0
    assert report.failed_evaluations == 0
    assert len(report.per_sample) == 2


def test_empty_sample_list(monkeypatch):
    monkeypatch.setenv("GENERATION_PROVIDER", "fake")
    monkeypatch.delenv("GENERATION_API_KEY", raising=False)

    report = run_evaluation([])
    assert report.total_samples == 0
    assert report.successful_evaluations == 0
    assert report.failed_evaluations == 0
    assert report.per_sample == []
