"""Evaluation API router for FastAPI."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/evaluation")
async def get_evaluation():
    return {"message": "Evaluation API placeholder"}


@router.post("/evaluation/run")
async def run_evaluation():
    return {"message": "Evaluation run placeholder"}


@router.get("/evaluation/history")
async def get_evaluation_history():
    return {"message": "Evaluation history placeholder"}
