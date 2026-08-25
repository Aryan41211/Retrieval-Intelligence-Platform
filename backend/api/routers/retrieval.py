"""Retrieval API router.

Runs a real semantic search, scoped to the knowledge bases the caller is allowed
to read: their own private namespace plus every workspace they belong to.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import active_retrieval_strategy, get_current_user
from backend.api.namespaces import readable_namespaces
from backend.api.schemas import RetrievalRequest, RetrievalResponse, RetrievalResult
from backend.api.scoped_retrieval import (
    ScopedRetrievalService,
    get_scoped_retrieval_service,
)
from backend.enterprise.database import get_db
from backend.enterprise.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/retrieval")
async def get_retrieval() -> dict[str, str]:
    """Retrieval API status."""
    return {"message": "Retrieval API is running"}


@router.post("/retrieval/search", response_model=RetrievalResponse)
async def search_retrieval(
    payload: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    retrieval_service: ScopedRetrievalService = Depends(get_scoped_retrieval_service),
) -> RetrievalResponse:
    """Run a semantic retrieval over the caller's accessible knowledge bases."""
    namespaces = await readable_namespaces(db, current_user)

    outcome = await retrieval_service.retrieve_async(
        payload.query,
        namespaces,
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
        for chunk in outcome.chunks
    ]

    return RetrievalResponse(
        results=results,
        total_found=len(results),
        processing_time_ms=outcome.latency_ms,
        strategy=active_retrieval_strategy(),
        namespaces_searched=outcome.namespaces_searched,
    )


@router.post("/retrieval/inspect")
async def inspect_retrieval(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Report the retrieval configuration in effect for the caller."""
    namespaces = await readable_namespaces(db, current_user)
    return {
        "strategy": active_retrieval_strategy(),
        "namespaces": [ns.label for ns in namespaces],
    }
