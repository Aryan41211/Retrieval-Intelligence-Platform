"""Chat API router for FastAPI.

This module provides the integrated chat endpoint that connects the FastAPI API with the existing
Generation Pipeline to enable complete RAG (Retrieval-Augmented Generation) functionality.
"""

import json
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.generation.generation_pipeline import GenerationPipeline
from backend.generation.models import ContextItem, GenerationResult
from backend.retrieval.retrieval_result import RetrievalChunkResult

from ..dependencies import get_generation_pipeline
from ..schemas import ChatMessage, ChatRequest, ChatResponse

router = APIRouter()


def create_context_item_from_chunk(chunk: RetrievalChunkResult) -> ContextItem:
    """Convert RetrievalChunkResult to ContextItem for generation."""
    return ContextItem(
        chunk_id=str(chunk.chunk_id),
        document_id=str(chunk.document_id),
        chunk_text=chunk.chunk_text,
        rank=chunk.rank,
        similarity_score=chunk.similarity_score,
        source_filename=chunk.source_filename,
        page_number=chunk.page_number,
        extra=chunk.metadata if chunk.metadata else {}
    )


def create_chat_message_from_result(result: GenerationResult) -> ChatMessage:
    """Convert GenerationResult to ChatMessage."""
    return ChatMessage(
        role="assistant",
        content=result.answer,
        timestamp=result.generation_timestamp
    )


async def stream_chat_response(
    pipeline: GenerationPipeline,
    query: str,
    context_chunks: list[RetrievalChunkResult],
    conversation_id: str | None = None
) -> AsyncGenerator[str, None]:
    """Stream chat response through generation pipeline."""
    try:
        # Convert chunks to ContextItems for generation pipeline
        context_items = [create_context_item_from_chunk(chunk) for chunk in context_chunks]

        # Extract raw chunks for generation pipeline (expects RetrievalChunk-like objects)
        # Use the chunk objects directly as they have the required attributes
        raw_chunks = context_chunks

        # Generate response using the existing generation pipeline
        result: GenerationResult = await pipeline.generate(
            query=query,
            retrieved_chunks=raw_chunks,
            correlation_id=conversation_id
        )

        # Create response using the existing schema
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
                    "metadata": chunk.metadata
                }
                for chunk in context_chunks
            ],
            citations=[
                {
                    "doc_index": citation.doc_index,
                    "chunk_id": citation.chunk_id,
                    "document_id": citation.document_id,
                    "chunk_text": citation.chunk_text,
                    "confidence": citation.confidence,
                    "page_number": citation.page_number,
                    "extra": citation.extra
                }
                for citation in result.citations
            ] if result.citations else None
        )

        # Stream the response as JSON
        yield f"data: {json.dumps(response.model_dump())}\n\n"

    except Exception as e:
        error_response = {
            "error": str(e),
            "conversation_id": conversation_id or "error",
            "timestamp": time.time()
        }
        yield f"data: {json.dumps(error_response)}\n\n"


@router.get("/chat")
async def get_chat():
    """Get chat API status."""
    return {"message": "Chat API is running"}


@router.post("/chat")
async def chat_with_context(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    pipeline: GenerationPipeline = Depends(get_generation_pipeline)
):
    """Generate a chat response using the RAG pipeline.
    
    This endpoint implements the complete RAG pipeline:
    1. Accepts a user query via ChatRequest
    2. Generates a response using the existing GenerationPipeline
    3. Returns structured response with citations and metadata
    """
    try:
        start_time = time.time()

        # Mock retrieval results - in complete implementation, this would call:
        # 1. RetrievalEngine to get relevant chunks based on query
        # 2. Process the chunks and convert to RetrievalChunkResult objects

        # For now, create realistic mock chunks that demonstrate the pipeline
        context_chunks = [
            RetrievalChunkResult(
                chunk_id="123e4567-e89b-12d3-a456-426614174000",
                document_id="123e4567-e89b-12d3-a456-426614174001",
                chunk_text="This is the first relevant document chunk about the topic of artificial intelligence and machine learning.",
                similarity_score=0.95,
                rank=1,
                source_filename="ai_documentation.txt",
                metadata={"source": "AI Documentation", "page": 1}
            ),
            RetrievalChunkResult(
                chunk_id="123e4567-e89b-12d3-a456-426614174002",
                document_id="123e4567-e89b-12d3-a456-426614174002",
                chunk_text="This is the second relevant document chunk providing additional context about neural networks and deep learning techniques.",
                similarity_score=0.87,
                rank=2,
                source_filename="ml_research_paper.md",
                metadata={"source": "ML Research", "page": 15}
            ),
            RetrievalChunkResult(
                chunk_id="123e4567-e89b-12d3-a456-426614174003",
                document_id="123e4567-e89b-12d3-a456-426614174003",
                chunk_text="The third chunk discusses applications of AI in healthcare and shows how models are trained on medical data.",
                similarity_score=0.82,
                rank=3,
                source_filename="healthcare_ai.txt",
                metadata={"source": "Healthcare AI", "page": 42}
            )
        ]

        # For the streaming response, create an async generator
        async def generate_stream():
            async for chunk_data in stream_chat_response(
                pipeline=pipeline,
                query=request.query,
                context_chunks=context_chunks,
                conversation_id=request.conversation_id
            ):
                yield chunk_data

        # Measure processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Processing-Time": f"{processing_time_ms}ms"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )
