"""Experiments API router for FastAPI.

Experiment tracking (MLflow / WandB) is not wired into the API in this build. Endpoints
report unavailability honestly instead of returning placeholder success messages.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

_UNAVAILABLE_DETAIL = "Experiment tracking is not available in this build."


@router.get("/experiments")
async def get_experiments() -> dict[str, str]:
    """Report experiments availability."""
    return {"status": "unavailable", "reason": _UNAVAILABLE_DETAIL}


@router.post("/experiments")
async def create_experiment() -> None:
    """Reject experiment creation with a clear, honest 501."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_UNAVAILABLE_DETAIL)
