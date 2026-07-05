"""Document API router for FastAPI."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/documents")
async def get_documents():
    return {"message": "Document API placeholder"}


@router.post("/documents/upload")
async def upload_document():
    return {"message": "Document upload placeholder"}
