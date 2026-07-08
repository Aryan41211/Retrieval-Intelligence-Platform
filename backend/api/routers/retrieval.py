"""Retrieval API router for FastAPI.

Exposes the real retrieval pipeline: a query is embedded and searched against the vector
store, returning ranked, citation-ready chunks.
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import (
    RetrievalService,
    get_current_user,
    get_retrieval_service,
)
from backend.api.schemas import RetrievalRequest, RetrievalResponse, RetrievalResult

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/retrieval")
async def get_retrieval() -> dict[str, str]:
    """Retrieval API status."""
    return {"message": "Retrieval API is running"}


@router.post("/retrieval/search", response_model=RetrievalResponse)
async def search_retrieval(
    payload: RetrievalRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    """Run a real semantic retrieval over the knowledge base."""
    chunks, metadata = retrieval_service.retrieve(
        payload.query,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )

    results = [
        RetrievalResult(
            chunk_id=str(chunk.chunk_id),
            document_id=str(chunk.document_id),
            content=chunk.chunk_text,
            similarity_score=chunk.similarity_score,
            rank=chunk.rank,
            source_filename=chunk.source_filename,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]

    return RetrievalResponse(
        results=results,
        total_found=len(results),
        processing_time_ms=metadata.retrieval_latency_ms if metadata else 0.0,
        strategy="dense",
    )


@router.post("/retrieval/inspect")
async def inspect_retrieval() -> dict[str, str]:
    """Inspect retrieval configuration/status."""
    return {"message": "Retrieval inspection is available via /retrieval/search"}
