"""Evaluation API router for FastAPI.

The platform's evaluation capability is backed by Ragas. When Ragas is
configured (``GENERATION_PROVIDER`` set to a real provider plus
``GENERATION_API_KEY``), endpoints accept and run labeled evaluation
datasets. When not configured, endpoints report ``unavailable`` rather
than returning simulated scores.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from backend.api.dependencies import get_current_active_user
from backend.evaluation.core.evaluator import (
    EvaluationReport,
    EvaluationSample,
    RagasEvaluator,
    run_evaluation,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])

# In-memory history of evaluation runs (per-process). A production deployment
# would persist this to a database.
_evaluation_history: list[EvaluationReport] = []


@router.get("/evaluation")
async def get_evaluation() -> dict[str, str]:
    """Report evaluation availability."""
    evaluator = RagasEvaluator()
    if evaluator._configured:  # noqa: SLF001 - internal status check
        return {"status": "available", "provider": evaluator._provider_name or "unknown"}
    return {
        "status": "unavailable",
        "reason": (
            "Ragas evaluation is not configured. Set GENERATION_PROVIDER to a real "
            "provider (openai/anthropic/ollama/nim) and provide GENERATION_API_KEY."
        ),
    }


@router.post("/evaluation/run", response_model=EvaluationReport)
async def run_evaluation_endpoint(
    samples: list[EvaluationSample] = Body(
        ...,
        description="Labeled evaluation samples: question, ground_truth, answer, contexts.",
    ),
) -> EvaluationReport:
    """Run Ragas evaluation on the provided labeled samples.

    Returns ``unavailable``-style results (zero metrics, explanatory note)
    when Ragas is not configured. No scores are ever fabricated.
    """
    report = run_evaluation(samples)
    _evaluation_history.append(report)
    return report


@router.get("/evaluation/history", response_model=list[EvaluationReport])
async def get_evaluation_history() -> list[EvaluationReport]:
    """Return the history of evaluation runs (per-process memory)."""
    return list(_evaluation_history)
