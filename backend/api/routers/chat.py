"""Chat API router for FastAPI.

This module provides the integrated chat endpoint that connects the FastAPI API with the
Generation Pipeline and the real Retrieval Pipeline to enable complete RAG (Retrieval-
Augmented Generation) functionality.

The endpoint authenticates the caller (Bearer JWT) and retrieves real chunks from the
vector store before generating a grounded answer — it never fabricates context.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import (
    get_current_active_user,
    get_generation_pipeline,
)
from backend.api.namespaces import readable_namespaces
from backend.api.observability import get_correlation_id
from backend.api.schemas import ChatMessage, ChatRequest, ChatResponse
from backend.api.scoped_retrieval import (
    ScopedRetrievalService,
    get_scoped_retrieval_service,
)
from backend.enterprise.database import get_db
from backend.enterprise.models import User
from backend.generation.generation_pipeline import GenerationPipeline
from backend.retrieval.retrieval_result import RetrievalChunkResult

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def create_chat_message_from_result(result: Any) -> ChatMessage:
    """Map a generation result to the chat message schema."""
    return ChatMessage(
        role="assistant",
        content=result.answer,
        timestamp=result.generation_timestamp,
    )


async def stream_chat_response(
    pipeline: GenerationPipeline,
    query: str,
    context_chunks: list[RetrievalChunkResult],
    conversation_id: str | None = None,
    start_time: float | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat response through the generation pipeline.

    Emits one ``meta:`` frame (retrieval stats, parity with real-time status)
    before generation starts, then a single ``data:`` frame carrying the full
    grounded answer. The X-Processing-Time response header is deliberately not
    used here: for an SSE response the headers are written before the body is
    produced, so any header value would misreport end-to-end time. Accurate
    total latency is delivered inside the data frame as ``processing_time_ms``.
    """
    request_started = start_time or time.time()

    def elapsed_ms() -> int:
        return int((time.time() - request_started) * 1000)

    correlation_id = get_correlation_id() or conversation_id or "default_conversation"

    meta_frame = {
        "status": "processing",
        "correlation_id": correlation_id,
        "conversation_id": conversation_id or "default_conversation",
        "retrieved_chunks_count": len(context_chunks),
        "retrieval_time_ms": elapsed_ms(),
    }
    yield f"meta: {json.dumps(meta_frame)}\n\n"

    try:
        result = await pipeline.generate(
            query=query,
            retrieved_chunks=context_chunks,
            correlation_id=correlation_id,
        )

        response = ChatResponse(
            message=create_chat_message_from_result(result),
            conversation_id=conversation_id or "default_conversation",
            retrieved_chunks=[
                {
                    "chunk_id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.chunk_text,
                    "similarity_score": chunk.similarity_score,
                    "rank": chunk.rank,
                    "source_filename": chunk.source_filename,
                    "metadata": chunk.metadata,
                }
                for chunk in context_chunks
            ],
            citations=(
                [
                    {
                        "doc_index": citation.doc_index,
                        "chunk_id": citation.chunk_id,
                        "document_id": citation.document_id,
                        "chunk_text": citation.chunk_text,
                        "confidence": citation.confidence,
                        "page_number": citation.page_number,
                        "extra": citation.extra,
                    }
                    for citation in result.citations
                ]
                if result.citations
                else None
            ),
            token_usage=result.metadata.extra.get("token_usage"),
            processing_time_ms=elapsed_ms(),
        )

        yield f"data: {json.dumps(response.model_dump(mode='json'))}\n\n"

    except Exception:
        # Never surface raw exception text: provider errors embed upstream
        # response bodies, which can carry endpoint and credential detail. The
        # full traceback goes to the log, keyed by correlation id.
        logger.exception(
            "Chat generation failed",
            extra={"correlation_id": correlation_id},
        )
        error_response = {
            "error": "Generation failed. Please retry.",
            "correlation_id": correlation_id,
            "conversation_id": conversation_id or "error",
            "timestamp": time.time(),
        }
        yield f"data: {json.dumps(error_response)}\n\n"


@router.get("/chat")
async def get_chat() -> dict[str, str]:
    """Get chat API status."""
    return {"message": "Chat API is running"}


@router.post("/chat")
async def chat_with_context(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    retrieval_service: ScopedRetrievalService = Depends(get_scoped_retrieval_service),
    generation_pipeline: GenerationPipeline = Depends(get_generation_pipeline),
) -> StreamingResponse:
    """Generate a grounded RAG response using the real retrieval + generation pipelines.

    Retrieval is scoped to the caller's own knowledge base plus the workspaces
    they belong to, so an answer can never be grounded in another tenant's
    documents.
    """
    start_time = time.time()

    namespaces = await readable_namespaces(db, current_user)
    outcome = await retrieval_service.retrieve_async(
        request.query,
        namespaces,
        correlation_id=request.conversation_id,
    )
    context_chunks = outcome.chunks

    async def generate_stream() -> AsyncGenerator[str, None]:
        async for chunk_data in stream_chat_response(
            pipeline=generation_pipeline,
            query=request.query,
            context_chunks=context_chunks,
            conversation_id=request.conversation_id,
            start_time=start_time,
        ):
            yield chunk_data

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
