"""Evaluation core package — Ragas-backed grounded-generation evaluation."""

from backend.evaluation.core.evaluator import (
    EvaluationConfig,
    EvaluationReport,
    EvaluationResult,
    EvaluationSample,
    RagasEvaluator,
    run_evaluation,
)

__all__ = [
    "EvaluationConfig",
    "EvaluationReport",
    "EvaluationResult",
    "EvaluationSample",
    "RagasEvaluator",
    "run_evaluation",
]
