"""Core evaluation engine implementing comprehensive quality assessment for RAG pipelines.

This module provides the main evaluation pipeline that integrates:
- RAGAS metrics (faithfulness, relevance, precision, recall)
- DeepEval metrics (hallucination, response quality, context utilization)
- Custom metrics (latency, performance, coverage)
- Experiment tracking and comparison capabilities

Built on top of the existing embedding_validation framework to maintain
consistency and leverage established patterns.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from backend.data.evaluation import EvaluationResult, EvaluationSample

from .core.evaluators.base_evaluator import BaseEvaluator
from .core.evaluators.deepeval_evaluator import DeepEvalEvaluator
from .core.evaluators.ragas_evaluator import RAGASEvaluator

logger = logging.getLogger(__name__)


@dataclass
class EvaluationConfig:
    """Configuration for evaluation pipeline."""

    # RAGAS metrics
    faithfulness: bool = True
    answer_relevancy: bool = True
    context_precision: bool = True
    context_recall: bool = True
    context_relevancy: bool = True
    answer_correctness: bool = True

    # DeepEval metrics
    hallucination: bool = True
    answer_quality: bool = True
    context_utilization: bool = True

    # Custom metrics
    latency_metrics: bool = True
    performance_metrics: bool = True
    coverage_metrics: bool = True
    cost_metrics: bool = True

    # Experiment tracking
    track_experiment: bool = True
    auto_log_config: bool = True
    save_predictions: bool = True

    # Performance
    batch_concurrency: int = 10
    max_workers: int = 4
    timeout_seconds: float | None = None

    # Filtering
    sample_limit: int | None = None
    experiment_filter: str | None = None


@dataclass
class EvaluationMetrics:
    """Container for all evaluation metrics."""

    # RAGAS metrics
    faithfulness_score: float | None = None
    answer_relevancy_score: float | None = None
    context_precision_score: float | None = None
    context_recall_score: float | None = None
    context_relevancy_score: float | None = None
    answer_correctness_score: float | None = None

    # DeepEval metrics
    hallucination_score: float | None = None
    answer_quality_score: float | None = None
    context_utilization_score: float | None = None

    # Custom metrics
    average_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    p99_latency_ms: float | None = None
    throughput_qps: float | None = None
    token_usage_total: int | None = None
    citation_coverage: float | None = None
    source_coverage: float | None = None
    hit_rate: float | None = None
    cost_estimate: float | None = None

    # Overall scores
    overall_faithfulness: float | None = None
    overall_quality: float | None = None

    # Metadata
    timestamp: datetime | None = None
    sample_count: int = 0

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        result = {}
        for field_name, value in asdict(self).items():
            if value is not None:
                result[field_name] = value
        return result

    @classmethod
    def from_ragas(cls, ragas_results: dict, ragas_samples: int) -> EvaluationMetrics:
        """Create metrics from RAGAS results."""
        metrics = cls()
        metrics.sample_count = ragas_samples

        # Map RAGAS metric names to field names
        ragas_mapping = {
            "faithfulness": "faithfulness_score",
            "answer_relevancy": "answer_relevancy_score",
            "context_precision": "context_precision_score",
            "context_recall": "context_recall_score",
            "context_relevancy": "context_relevancy_score",
            "answer_correctness": "answer_correctness_score",
        }

        for ragas_name, value in ragas_results.items():
            if ragas_name in ragas_mapping and value is not None:
                setattr(metrics, ragas_mapping[ragas_name], value)

        # Calculate weighted average
        ragas_scores = [
            v
            for k, v in vars(metrics).items()
            if v is not None and k.endswith("_score") and "deep" not in k
        ]
        if ragas_scores:
            metrics.overall_faithfulness = sum(ragas_scores) / len(ragas_scores)

        return metrics

    @classmethod
    def from_deepeval(cls, deepeval_results: dict, deepeval_samples: int) -> EvaluationMetrics:
        """Create metrics from DeepEval results."""
        metrics = cls()
        metrics.sample_count = deepeval_samples

        # Map DeepEval metric names to field names
        deepeval_mapping = {
            "hallucination": "hallucination_score",
            "answer_quality": "answer_quality_score",
            "context_utilization": "context_utilization_score",
        }

        for metric_name, value in deepeval_results.items():
            if metric_name in deepeval_mapping and value is not None:
                setattr(metrics, deepeval_mapping[metric_name], value)

        # Calculate overall quality
        deepeval_scores = [
            v
            for k, v in vars(metrics).items()
            if v is not None and k.endswith("_score") and "deep" in k
        ]
        if deepeval_scores:
            metrics.overall_quality = sum(deepeval_scores) / len(deepeval_scores)

        return metrics


class EvaluationEngine:
    """Comprehensive evaluation engine for RAG pipelines."""

    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.evaluators: list[BaseEvaluator] = []
        self._initialize_evaluators()

        # Internal metrics storage
        self._ragas_metrics: list[EvaluationMetrics] = []
        self._deepeval_metrics: list[EvaluationMetrics] = []
        self._custom_metrics: list[EvaluationMetrics] = []

    def _initialize_evaluators(self):
        """Initialize all enabled evaluators."""

        # RAGAS evaluators
        if self.config.faithfulness:
            self.evaluators.append(RAGASEvaluator("faithfulness"))

        if self.config.answer_relevancy:
            self.evaluators.append(RAGASEvaluator("answer_relevancy"))

        if self.config.context_precision:
            self.evaluators.append(RAGASEvaluator("context_precision"))

        if self.config.context_recall:
            self.evaluators.append(RAGASEvaluator("context_recall"))

        if self.config.context_relevancy:
            self.evaluators.append(RAGASEvaluator("context_relevancy"))

        if self.config.answer_correctness:
            self.evaluators.append(RAGASEvaluator("answer_correctness"))

        # DeepEval evaluators
        if self.config.hallucination:
            try:
                self.evaluators.append(DeepEvalEvaluator("hallucination"))
            except Exception as e:
                logger.warning(f"Failed to initialize DeepEval hallucination evaluator: {e}")

        if self.config.answer_quality:
            try:
                self.evaluators.append(DeepEvalEvaluator("answer_quality"))
            except Exception as e:
                logger.warning(f"Failed to initialize DeepEval answer quality evaluator: {e}")

        if self.config.context_utilization:
            try:
                self.evaluators.append(DeepEvalEvaluator("context_utilization"))
            except Exception as e:
                logger.warning(f"Failed to initialize DeepEval context utilization evaluator: {e}")

    def evaluate(self, dataset: list[Any]) -> EvaluationResult:
        """Evaluate a dataset with all configured evaluators."""
        t0 = time.perf_counter()

        logger.info(f"Starting evaluation with {len(self.evaluators)} evaluators")

        # Convert dataset to EvaluationSample format
        evaluation_samples: list[EvaluationSample] = []
        for sample in dataset:
            sample_obj = EvaluationSample(
                query=sample.get("query", ""),
                context=sample.get("context", []),
                answer=sample.get("answer", ""),
                citations=sample.get("citations", []),
                ground_truth=sample.get("ground_truth"),
                metadata=sample.get("metadata", {}),
            )
            evaluation_samples.append(sample_obj)

        # Initialize result container
        ragas_results: list[dict] = []
        deepeval_results: list[dict] = []

        # Run each evaluator
        for evaluator in self.evaluators:
            try:
                evaluator_name = evaluator.name
                logger.info(f"Running evaluator: {evaluator_name}")

                t_evaluator = time.perf_counter()
                results = evaluator.evaluate(evaluation_samples)
                evaluator_latency = time.perf_counter() - t_evaluator

                # Store results by evaluator type
                if hasattr(evaluator, "evaluator_type"):
                    if evaluator.evaluator_type == "ragas":
                        ragas_results.append(results)
                    elif evaluator.evaluator_type == "deepeval":
                        deepeval_results.append(results)
                # Default classification
                elif evaluator_name in [
                    "faithfulness",
                    "answer_relevancy",
                    "context_precision",
                    "context_recall",
                    "context_relevancy",
                    "answer_correctness",
                ]:
                    ragas_results.append(results)
                else:
                    deepeval_results.append(results)

                logger.info(f"Evaluator {evaluator_name} completed in {evaluator_latency:.2f}s")

            except Exception as e:
                logger.error(f"Evaluator {evaluator.name} failed: {e}")
                raise

        # Convert results to EvaluationMetrics
        ragas_metric = EvaluationMetrics.from_ragas(
            self._aggregate_ragas_results(ragas_results), len(evaluation_samples)
        )

        deepeval_metric = EvaluationMetrics.from_deepeval(
            self._aggregate_deepeval_results(deepeval_results), len(evaluation_samples)
        )

        # Store metrics
        self._ragas_metrics.append(ragas_metric)
        self._deepeval_metrics.append(deepeval_metric)

        # Create overall evaluation result
        total_evaluation_time = time.perf_counter() - t0

        evaluation_result = EvaluationResult(
            ragas_metrics=ragas_results,
            deepeval_metrics=deepeval_results,
            custom_metrics={"latency": total_evaluation_time * 1000},  # ms
            overall_status="completed",
            experiment_id=None,
            dataset_hash=None,
            evaluator_configs=[asdict(config) for config in self.evaluators],
            evaluation_timestamp=datetime.now(UTC),
            metadata={
                "sample_count": len(evaluation_samples),
                "evaluators_used": len(self.evaluators),
                "total_evaluation_time_ms": total_evaluation_time * 1000,
                "ragas_results_count": len(ragas_results),
                "deepeval_results_count": len(deepeval_results),
            },
        )

        logger.info(
            f"Evaluation completed in {total_evaluation_time:.2f}s for {len(evaluation_samples)} samples"
        )

        return evaluation_result

    def _aggregate_ragas_results(self, results: list[dict]) -> dict:
        """Aggregate RAGAS results from multiple runs."""
        if not results:
            return {}

        # Combine results by averaging
        aggregated = {}
        for result in results:
            for metric_name, value in result.items():
                if metric_name not in aggregated:
                    aggregated[metric_name] = []
                aggregated[metric_name].append(value)

        # Average arrays
        final_result = {}
        for metric_name, values in aggregated.items():
            if values and all(v is not None for v in values):
                final_result[metric_name] = sum(values) / len(values)
            elif values:
                final_result[metric_name] = values[0]

        return final_result

    def _aggregate_deepeval_results(self, results: list[dict]) -> dict:
        """Aggregate DeepEval results from multiple runs."""
        if not results:
            return {}

        # Combine results by averaging
        aggregated = {}
        for result in results:
            for metric_name, value in result.items():
                if metric_name not in aggregated:
                    aggregated[metric_name] = []
                aggregated[metric_name].append(value)

        # Average arrays
        final_result = {}
        for metric_name, values in aggregated.items():
            if values and all(v is not None for v in values):
                final_result[metric_name] = sum(values) / len(values)
            elif values:
                final_result[metric_name] = values[0]

        return final_result

    def get_latest_metrics(self) -> dict[str, Any]:
        """Get the latest evaluation metrics."""
        if not self._ragas_metrics and not self._deepeval_metrics:
            return {}

        latest_ragas = self._ragas_metrics[-1] if self._ragas_metrics else None
        latest_deepeval = self._deepeval_metrics[-1] if self._deepeval_metrics else None

        result = {}

        if latest_ragas:
            result.update(
                {
                    "ragas": latest_ragas.to_dict(),
                    "overall_faithfulness": latest_ragas.overall_faithfulness,
                    "sample_count": latest_ragas.sample_count,
                }
            )

        if latest_deepeval:
            result.update(
                {
                    "deepeval": latest_deepeval.to_dict(),
                    "overall_quality": latest_deepeval.overall_quality,
                    "sample_count": latest_deepeval.sample_count,
                }
            )

        return result

    def get_metrics_history(self) -> list[dict[str, Any]]:
        """Get evaluation metrics history."""
        history = []

        for i, ragas_metrics in enumerate(self._ragas_metrics):
            entry = {
                "evaluation_number": i + 1,
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "ragas",
                "metrics": ragas_metrics.to_dict(),
            }
            history.append(entry)

        for i, deepeval_metrics in enumerate(self._deepeval_metrics):
            entry = {
                "evaluation_number": i + 1 + len(self._ragas_metrics),
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "deepeval",
                "metrics": deepeval_metrics.to_dict(),
            }
            history.append(entry)

        return sorted(history, key=lambda x: x["evaluation_number"])
