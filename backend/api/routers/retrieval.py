"""Retrieval API router for FastAPI."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/retrieval")
async def get_retrieval():
    return {"message": "Retrieval API placeholder"}


@router.post("/retrieval/search")
async def search_retrieval():
    return {"message": "Retrieval search placeholder"}


@router.post("/retrieval/inspect")
async def inspect_retrieval():
    return {"message": "Retrieval inspection placeholder"}
