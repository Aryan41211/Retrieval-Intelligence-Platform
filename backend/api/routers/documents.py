"""Document API router for FastAPI.

Implements real document ingestion: an uploaded document is chunked, embedded with the
configured embedding provider, and indexed into the runtime FAISS vector store so it
becomes retrievable by the chat/retrieval endpoints.
"""

from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import (
    DEFAULT_INDEX_ID,
    get_current_user,
    get_chunker,
    get_embedding_provider,
    get_vector_store,
)
from backend.api.schemas import DocumentUploadRequest, DocumentUploadResponse
from backend.data.models.document import Document

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/documents")
async def get_documents() -> dict[str, str]:
    """Document API status."""
    return {"message": "Document API is running"}


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    payload: DocumentUploadRequest,
    embedding_provider: object = Depends(get_embedding_provider),
    vector_store: object = Depends(get_vector_store),
    chunker: object = Depends(get_chunker),
) -> DocumentUploadResponse:
    """Ingest a document into the knowledge base.

    Steps: build a Document, chunk it, embed the chunks, and add them to the FAISS
    vector store (creating the index on first use).
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document content must be non-empty",
        )

    document = Document(
        filename=payload.filename,
        file_extension=Path(payload.filename).suffix or ".txt",
        source_path=payload.filename,
        title=payload.filename,
        language="en",
        content=payload.content,
        file_size=len(payload.content.encode("utf-8")),
    )

    chunks = chunker.chunk(document)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document produced no chunks",
        )

    batch = embedding_provider.embed_chunks(chunks)
    embeddings = batch.successful_embeddings
    if not embeddings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Embedding generation produced no vectors",
        )

    vectors = np.array([e.embedding_vector for e in embeddings], dtype=np.float32)
    ids = [str(e.chunk_id) for e in embeddings]
    metadatas = []
    for embedding, chunk in zip(embeddings, chunks, strict=True):
        metadatas.append(
            {
                "chunk_id": str(embedding.chunk_id),
                "document_id": str(embedding.document_id),
                "chunk_text": chunk.text,
                "source_file": payload.filename,
                "source_filename": payload.filename,
                "embedding_model": embedding.model_name,
                "language": document.language,
                "metadata": {
                    "document_id": str(document.document_id),
                    "filename": payload.filename,
                },
                "custom": {},
            }
        )

    if not vector_store.index_exists(DEFAULT_INDEX_ID):
        vector_store.create_index(DEFAULT_INDEX_ID, dimension=embedding_provider.dimension)
    else:
        vector_store.load_index(DEFAULT_INDEX_ID)

    added = vector_store.add_embeddings(vectors, ids=ids, metadata=metadatas)

    from backend.configs.settings import get_settings

    if get_settings().vector_store.auto_save:
        vector_store.save_index(DEFAULT_INDEX_ID)

    return DocumentUploadResponse(
        document_id=document.document_id,
        filename=payload.filename,
        status="ingested",
        message=f"Ingested {added} chunk(s) into the knowledge base.",
    )
