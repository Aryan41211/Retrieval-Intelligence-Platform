"""Chat API router for FastAPI."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/chat")
async def get_chat():
    return {"message": "Chat API placeholder"}


@router.post("/chat")
async def chat_with_context():
    return {"message": "Chat placeholder"}
