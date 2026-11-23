"""Evaluation core — Ragas-backed grounded-generation evaluation.

This module provides the evaluation infrastructure for the Retrieval
Intelligence Platform. It defines the evaluation dataset schema and a
runner that executes Ragas metrics (faithfulness, answer relevancy,
context precision, context recall) against a labeled evaluation set.

Actual Ragas execution requires an LLM provider and an embeddings provider
to be configured (``GENERATION_PROVIDER`` plus provider credentials). Until
those are configured, the runner reports ``not_available`` rather than
fabricating scores.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvaluationSample(BaseModel):
    """A single labeled evaluation sample for Ragas.

    Fields mirror the Ragas dataset schema:
    - ``question``: the user query
    - ``ground_truth``: the reference answer
    - ``answer``: the model-generated answer under test
    - ``contexts``: retrieved context chunks used to ground the answer
    """

    question: str = Field(..., description="User query")
    ground_truth: str = Field(..., description="Reference answer")
    answer: str = Field(..., description="Model-generated answer")
    contexts: list[str] = Field(
        default_factory=list, description="Retrieved context chunks"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contexts", mode="before")
    @classmethod
    def _contexts_must_be_strings(cls, v):
        return [str(c) for c in v]


class EvaluationResult(BaseModel):
    """Result of evaluating a single sample or an entire dataset."""

    sample_id: str | None = None
    question: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    error: str | None = None
    latency_ms: float = 0.0


class EvaluationReport(BaseModel):
    """Aggregate report for an evaluation run."""

    total_samples: int = 0
    successful_evaluations: int = 0
    failed_evaluations: int = 0
    metrics: dict[str, float] = Field(default_factory=dict)
    per_sample: list[EvaluationResult] = Field(default_factory=list)
    latency_ms: float = 0.0
    provider: str | None = None
    note: str | None = None


# ---------------------------------------------------------------------------
# Ragas runner
# ---------------------------------------------------------------------------


class RagasEvaluator:
    """Executes Ragas evaluation against a labeled dataset.

    Ragas 0.4.x requires:
    - An LLM provider (for faithfulness, answer_relevancy)
    - An embeddings provider (for context_precision, context_recall)

    These are resolved from environment configuration. If no provider is
    configured, :meth:`evaluate` returns a report with all metrics set to
    ``None`` and a ``note`` explaining the missing configuration.
    """

    METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")

    def __init__(self) -> None:
        self._provider_name: str | None = None
        self._embedding_provider: str | None = None
        self._configured = self._check_configuration()

    def _check_configuration(self) -> bool:
        """Return True if Ragas can run with the current environment."""
        provider = os.getenv("GENERATION_PROVIDER", "fake").lower()
        self._provider_name = provider
        if provider == "fake":
            return False
        # Ragas needs an LLM and an embedding model. Without API keys for a
        # real provider, evaluation cannot proceed.
        if provider in ("openai", "anthropic", "ollama", "nim"):
            if not os.getenv("GENERATION_API_KEY") and provider != "ollama":
                return False
        return True

    def evaluate(self, samples: list[EvaluationSample]) -> EvaluationReport:
        """Run Ragas evaluation on the provided samples.

        Args:
            samples: Labeled evaluation samples.

        Returns:
            EvaluationReport with per-sample and aggregate metrics. When
            Ragas is not configured, all metrics are absent and
            ``report.note`` explains why.
        """
        t0 = time.perf_counter()

        if not self._configured:
            return EvaluationReport(
                total_samples=len(samples),
                successful_evaluations=0,
                failed_evaluations=0,
                metrics={},
                per_sample=[
                    EvaluationResult(
                        sample_id=s.metadata.get("sample_id") if s.metadata else None,
                        question=s.question,
                        error="Ragas not configured: set GENERATION_PROVIDER and GENERATION_API_KEY",
                        latency_ms=0.0,
                    )
                    for s in samples
                ],
                latency_ms=int((time.perf_counter() - t0) * 1000),
                provider=self._provider_name,
                note=(
                    "Ragas evaluation is not configured. Set GENERATION_PROVIDER to a real "
                    "provider (openai/anthropic/ollama/nim) and provide GENERATION_API_KEY. "
                    "No metrics were computed."
                ),
            )

        # --- Real Ragas execution path ---
        try:
            from ragas import evaluate as ragas_evaluate
            from ragas.dataset_schema import SingleTurnSample
            from ragas.metrics import (
                Faithfulness,
                AnswerRelevancy,
                ContextPrecision,
                ContextRecall,
            )
        except ImportError as exc:  # pragma: no cover - ragas always installed
            return EvaluationReport(
                total_samples=len(samples),
                successful_evaluations=0,
                failed_evaluations=len(samples),
                metrics={},
                per_sample=[
                    EvaluationResult(
                        question=s.question,
                        error=f"Ragas import failed: {exc}",
                        latency_ms=0.0,
                    )
                    for s in samples
                ],
                latency_ms=int((time.perf_counter() - t0) * 1000),
                provider=self._provider_name,
                note="Ragas library import failed.",
            )

        # Convert to Ragas SingleTurnSample format.
        ragas_samples = []
        for s in samples:
            ragas_samples.append(
                SingleTurnSample(
                    user_input=s.question,
                    response=s.answer,
                    reference=s.ground_truth,
                    retrieved_contexts=s.contexts,
                )
            )

        metric_instances = [
            Faithfulness(),
            AnswerRelevancy(),
            ContextPrecision(),
            ContextRecall(),
        ]

        per_sample: list[EvaluationResult] = []
        successful = 0
        failed = 0

        try:
            # Ragas evaluates the full dataset at once.
            result = ragas_evaluate(
                dataset=ragas_samples,
                metrics=metric_instances,
            )

            # Ragas returns a pandas DataFrame; extract per-sample scores.
            import pandas as pd

            df = result.to_pandas() if hasattr(result, "to_pandas") else result

            for i, s in enumerate(samples):
                row = df.iloc[i] if hasattr(df, "iloc") else df[i]
                sample_metrics: dict[str, float] = {}
                for m in self.METRICS:
                    val = row.get(m) if hasattr(row, "get") else None
                    if val is not None:
                        try:
                            sample_metrics[m] = float(val)
                        except (TypeError, ValueError):
                            pass
                per_sample.append(
                    EvaluationResult(
                        sample_id=s.metadata.get("sample_id") if s.metadata else None,
                        question=s.question,
                        metrics=sample_metrics,
                        latency_ms=0.0,
                    )
                )
                successful += 1

        except Exception as exc:  # pragma: no cover - ragas runtime errors
            failed = len(samples)
            per_sample = [
                EvaluationResult(
                    question=s.question,
                    error=str(exc),
                    latency_ms=0.0,
                )
                for s in samples
            ]

        # Aggregate metrics: mean across samples.
        agg_metrics: dict[str, float] = {}
        for m in self.METRICS:
            values = [
                p.metrics[m]
                for p in per_sample
                if p.metrics and m in p.metrics and p.metrics[m] is not None
            ]
            if values:
                agg_metrics[m] = round(sum(values) / len(values), 4)

        return EvaluationReport(
            total_samples=len(samples),
            successful_evaluations=successful,
            failed_evaluations=failed,
            metrics=agg_metrics,
            per_sample=per_sample,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            provider=self._provider_name,
        )


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------


@dataclass
class EvaluationConfig:
    """Configuration for an evaluation run."""

    samples: list[EvaluationSample] = field(default_factory=list)
    provider: str | None = None


def run_evaluation(samples: list[EvaluationSample]) -> EvaluationReport:
    """Run Ragas evaluation on the provided samples.

    Convenience wrapper around :class:`RagasEvaluator`.

    Args:
        samples: Labeled evaluation samples.

    Returns:
        EvaluationReport with aggregate and per-sample metrics.
    """
    evaluator = RagasEvaluator()
    return evaluator.evaluate(samples)
