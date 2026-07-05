"""Experiments API router for FastAPI."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/experiments")
async def get_experiments():
    return {"message": "Experiments API placeholder"}


@router.post("/experiments")
async def create_experiment():
    return {"message": "Create experiment placeholder"}
