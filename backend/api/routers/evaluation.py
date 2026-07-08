"""Evaluation API router for FastAPI.

The platform's evaluation capability depends on RAGAS/DeepEval integration, which is not
configured in this build. Per the release policy, these endpoints report evaluation as
*unavailable* rather than returning simulated scores.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

_UNAVAILABLE_DETAIL = (
    "Evaluation is not available: RAGAS/DeepEval integration is not configured in this build."
)


@router.get("/evaluation")
async def get_evaluation() -> dict[str, str]:
    """Report evaluation availability."""
    return {"status": "unavailable", "reason": _UNAVAILABLE_DETAIL}


@router.post("/evaluation/run")
async def run_evaluation() -> None:
    """Reject evaluation runs with a clear, honest 501 (no simulated results)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_UNAVAILABLE_DETAIL)


@router.get("/evaluation/history")
async def get_evaluation_history() -> None:
    """Reject evaluation history with a clear, honest 501 (no simulated results)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_UNAVAILABLE_DETAIL)
