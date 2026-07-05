"""Chat API router for FastAPI."""

from fastapi import FastAPI

# Initialize FastAPI app
app = FastAPI()

@app.get("/v1/chat")
async def get_chat():
    return {"message": "Chat API placeholder"}

@app.post("/v1/chat")
async def chat_with_context():
    return {"message": "Chat placeholder"}
