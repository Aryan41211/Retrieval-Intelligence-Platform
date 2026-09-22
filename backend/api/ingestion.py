"""Document ingestion service.

Chunking, embedding and vector-index mutation are CPU-bound, synchronous
operations. Calling them directly from an ``async def`` route blocked the event
loop for the whole duration, serialising the entire API behind one upload. They
also mutated a process-global FAISS store with no mutual exclusion, so
overlapping uploads could discard each other's writes.

This module runs the whole sequence in a worker thread under a single lock, so
the event loop stays responsive and index mutations are serialised.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# Guards the create/load/remove/save sequence against the shared vector store.
# A threading.Lock (not asyncio.Lock) because the critical section executes
# inside a worker thread and must not be bound to a particular event loop.
INDEX_WRITE_LOCK = threading.Lock()


class IngestionError(RuntimeError):
    """Raised when a document cannot be ingested."""


class DuplicateDocumentError(IngestionError):
    """Raised when a document with identical content is already indexed."""


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of ingesting a single document."""

    chunks_created: int
    chunks_indexed: int


def _build_metadata(
    *,
    embedding: Any,
    chunk: Any,
    document: Any,
    filename: str,
) -> dict[str, Any]:
    """Build the vector-store metadata record for one chunk."""
    return {
        "chunk_id": str(embedding.chunk_id),
        "document_id": str(embedding.document_id),
        "chunk_text": chunk.text,
        "source_file": filename,
        "source_filename": filename,
        "embedding_model": embedding.model_name,
        "language": document.language,
        "metadata": {
            "document_id": str(document.document_id),
            "filename": filename,
            "checksum": getattr(document, "checksum", "") or "",
        },
        "custom": {},
    }


def _is_duplicate(indexed: dict[str, Any], document: Any) -> bool:
    """Return whether any indexed record shares the document's content checksum."""
    checksum = getattr(document, "checksum", "") or ""
    if not checksum:
        return False
    for record in indexed.values():
        meta = record.get("metadata") or {}
        if meta.get("checksum") == checksum:
            return True
    return False


def _ingest_sync(
    *,
    document: Any,
    chunker: Any,
    embedding_provider: Any,
    vector_store: Any,
    index_id: str,
    auto_save: bool,
) -> IngestionResult:
    """Chunk, embed and index a document. Blocking; run in a worker thread.

    Args:
        document: The document to ingest.
        chunker: Chunking strategy implementation.
        embedding_provider: Provider used to embed chunks.
        vector_store: Target vector store.
        index_id: Index to write into, created on first use.
        auto_save: Persist the index after the write.

    Returns:
        Counts of chunks created and successfully indexed.

    Raises:
        IngestionError: If the document produces no chunks, no embeddings, or no
            embedding can be matched back to its source chunk.
        DuplicateDocumentError: If a document with identical content is already
            indexed in this namespace.
    """
    from backend.configs.settings import get_settings

    max_chunks = get_settings().ingestion.max_chunks
    chunks = chunker.chunk(document)
    if not chunks:
        raise IngestionError("Document produced no chunks")
    if len(chunks) > max_chunks:
        raise IngestionError(f"Document produced {len(chunks)} chunks; the limit is {max_chunks}")

    # Serialise against index mutations before reading the existing records, so
    # the duplicate scan sees a stable index for the namespace.
    with INDEX_WRITE_LOCK:
        indexed = getattr(vector_store, "_vector_records", {}) or {}
        if _is_duplicate(indexed, document):
            raise DuplicateDocumentError(
                f"Document '{document.filename}' is already indexed in this knowledge base"
            )

    batch = embedding_provider.embed_chunks(chunks)
    embeddings = batch.successful_embeddings
    if not embeddings:
        raise IngestionError("Embedding generation produced no vectors")

    # Pair each successful embedding with its own chunk by id. Zipping the
    # successful embeddings against *all* chunks raised ValueError whenever a
    # single chunk failed to embed.
    chunks_by_id = {str(chunk.chunk_id): chunk for chunk in chunks}
    paired = []
    for embedding in embeddings:
        chunk = chunks_by_id.get(str(embedding.chunk_id))
        if chunk is None:  # pragma: no cover - provider returned an unknown id
            logger.warning("Skipping embedding for unknown chunk id %s", embedding.chunk_id)
            continue
        paired.append((embedding, chunk))

    if not paired:
        raise IngestionError("No embedding could be matched to its source chunk")

    vectors = np.array([e.embedding_vector for e, _ in paired], dtype=np.float32)
    ids = [str(e.chunk_id) for e, _ in paired]
    metadatas = [
        _build_metadata(
            embedding=embedding,
            chunk=chunk,
            document=document,
            filename=document.filename,
        )
        for embedding, chunk in paired
    ]

    # Serialise every index mutation. Without this, two concurrent uploads
    # interleaved create/load/add/save and one silently discarded the other's
    # embeddings by reloading the on-disk state.
    with INDEX_WRITE_LOCK:
        if not vector_store.index_exists(index_id):
            vector_store.create_index(index_id, dimension=embedding_provider.dimension)
        elif getattr(vector_store, "_index", None) is None:
            # Only read from disk when nothing is loaded yet. Reloading on every
            # upload threw away in-memory additions that had not been saved.
            vector_store.load_index(index_id)

        current_dim = getattr(getattr(vector_store, "_index", None), "d", None)
        provider_dim = embedding_provider.dimension
        if current_dim is not None and provider_dim is not None and current_dim != provider_dim:
            raise IngestionError(
                "Embedding model dimension mismatch: the index stores "
                f"{current_dim}-dimensional vectors but the configured model "
                f"produces {provider_dim}. Re-index the knowledge base or restore "
                "the original embedding model."
            )

        added = vector_store.add_embeddings(vectors, ids=ids, metadata=metadatas)

        if auto_save:
            vector_store.save_index(index_id)

    return IngestionResult(chunks_created=len(chunks), chunks_indexed=added)


async def ingest_document(
    *,
    document: Any,
    chunker: Any,
    embedding_provider: Any,
    vector_store: Any,
    index_id: str,
    auto_save: bool,
) -> IngestionResult:
    """Ingest a document without blocking the event loop.

    Args:
        document: The document to ingest.
        chunker: Chunking strategy implementation.
        embedding_provider: Provider used to embed chunks.
        vector_store: Target vector store.
        index_id: Index to write into.
        auto_save: Persist the index after the write.

    Returns:
        Counts of chunks created and indexed.

    Raises:
        IngestionError: Propagated from the synchronous stage.
    """
    return await run_in_threadpool(
        _ingest_sync,
        document=document,
        chunker=chunker,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        index_id=index_id,
        auto_save=auto_save,
    )


def _remove_document_sync(
    *,
    vector_store: Any,
    index_id: str,
    document_id: str,
    auto_save: bool,
) -> int:
    """Remove every chunk of a document, serialised against other mutations.

    Deletion mutates the same shared FAISS store as ingestion, so it must run
    under the same write lock. Without this, a concurrent upload could reload
    or write state while a delete was mid-flight.

    Args:
        vector_store: Target vector store.
        index_id: Index to remove from.
        document_id: Document whose chunks should be removed.
        auto_save: Persist the index after the write.

    Returns:
        Number of embeddings removed, or 0 if the document was not found.
    """
    with INDEX_WRITE_LOCK:
        records = getattr(vector_store, "_vector_records", {}) or {}
        doomed = [
            embedding_id
            for embedding_id, record in records.items()
            if str(record.get("document_id") or "") == document_id
        ]
        if not doomed:
            return 0
        removed = vector_store.remove_embeddings(doomed)
        if auto_save:
            vector_store.save_index(index_id)
        return removed


async def remove_document(
    *,
    vector_store: Any,
    index_id: str,
    document_id: str,
    auto_save: bool,
) -> int:
    """Remove a document's chunks without blocking the event loop.

    Args:
        vector_store: Target vector store.
        index_id: Index to remove from.
        document_id: Document whose chunks should be removed.
        auto_save: Persist the index after the write.

    Returns:
        Number of embeddings removed, or 0 if the document was not found.
    """
    return await run_in_threadpool(
        _remove_document_sync,
        vector_store=vector_store,
        index_id=index_id,
        document_id=document_id,
        auto_save=auto_save,
    )
