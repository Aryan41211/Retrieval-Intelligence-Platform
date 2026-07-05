"""Document API router for FastAPI."""

from fastapi import FastAPI

# Initialize FastAPI app
app = FastAPI()

@app.get("/v1/documents")
async def get_documents():
    return {"message": "Document API placeholder"}

@app.post("/v1/documents/upload")
async def upload_document():
    return {"message": "Document upload placeholder"}
