"""
API dependencies and service injection setup.

This module centralises dependency-injection helpers used by the API routers. It
wires the real Retrieval Pipeline and Generation Pipeline (and their supporting
embedding provider / vector store) into the request path, and re-exports the
enterprise authentication dependency so data-plane routers can enforce real auth.

Heavy objects (embedding model, vector store) are cached at process level so they
are constructed once and reused across requests.
"""

import logging
from functools import lru_cache
from typing import Any

import numpy as np

from backend.configs.settings import get_settings
from backend.data.chunking.factory import ChunkerFactory
from backend.data.embeddings.embedding_factory import EmbeddingFactory
from backend.data.models.chunk import ChunkingStrategy

# Real authentication dependency (JWT / bearer) provided by the enterprise layer.
from backend.enterprise.rbac import get_current_user  # noqa: F401  (re-exported for routers)
from backend.generation.generation_pipeline import GenerationPipeline
from backend.retrieval.exceptions import EmptyRetrievalResultError, RetrievalError
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_pipeline import RetrievalPipeline
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.vectorstore.exceptions import VectorStoreError
from backend.vectorstore.vector_store_factory import VectorStoreFactory

logger = logging.getLogger(__name__)

# Default FAISS index id used by the runtime knowledge base.
DEFAULT_INDEX_ID = "rip-default"


class RetrievalService:
    """Thin service that turns a natural-language query into real retrieved chunks.

    Embeds the query with the configured embedding provider and runs it through the
    Retrieval Pipeline (backed by the vector store). Failures (empty index, no
    results) degrade gracefully to an empty result set so the generation stage can
    answer honestly ("I don't know.") instead of returning fabricated context.
    """

    def __init__(
        self,
        *,
        embedding_provider: Any,
        retrieval_pipeline: RetrievalPipeline,
        top_k: int,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._retrieval_pipeline = retrieval_pipeline
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        threshold: float | None = None,
        correlation_id: str | None = None,
    ) -> tuple[list[Any], Any | None]:
        """Retrieve real chunks for a query.

        Returns:
            A tuple of ``(chunks, retrieval_metadata)``. ``chunks`` is empty when the
            knowledge base has no index or no matching results.
        """
        try:
            embedding = self._embedding_provider.embed_text(query)
            query_vector = list(embedding.embedding_vector)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Query embedding failed: %s", exc)
            return [], None

        request = RetrievalRequest(
            query_vector=query_vector,
            top_k=top_k or self._top_k,
            similarity_threshold=threshold,
            extra={"query_text": query},
            correlation_id=correlation_id,
        )

        try:
            chunks, metadata = self._retrieval_pipeline.run(request)
        except (EmptyRetrievalResultError, RetrievalError, VectorStoreError) as exc:
            logger.info("Retrieval returned no results: %s", exc)
            return [], None
        return chunks, metadata


@lru_cache(maxsize=1)
def get_embedding_provider() -> Any:
    """Return the cached sentence-transformers embedding provider."""
    return EmbeddingFactory.create_sentence_transformer()


@lru_cache(maxsize=1)
def get_vector_store() -> Any:
    """Return the cached runtime vector store, best-effort loading the default index."""
    settings = get_settings()
    store = VectorStoreFactory.create(
        settings.vector_store.provider,
        settings.vector_store.storage_dir,
    )
    if settings.vector_store.auto_load:
        try:
            if store.index_exists(DEFAULT_INDEX_ID):
                store.load_index(DEFAULT_INDEX_ID)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to pre-load vector index: %s", exc)
    return store


def get_retrieval_pipeline() -> RetrievalPipeline:
    """Build a Retrieval Pipeline backed by the runtime vector store."""
    engine = RetrievalEngine(get_vector_store())
    return RetrievalPipeline(engine)


def get_retrieval_service() -> RetrievalService:
    """Build the retrieval service used by the chat/retrieval routers."""
    settings = get_settings()
    return RetrievalService(
        embedding_provider=get_embedding_provider(),
        retrieval_pipeline=get_retrieval_pipeline(),
        top_k=settings.retrieval.top_k,
    )


def get_generation_pipeline() -> GenerationPipeline:
    """Build a Generation Pipeline from configuration."""
    return GenerationPipeline.from_config()


def get_chunker() -> Any:
    """Return a recursive chunker for document ingestion."""
    return ChunkerFactory.create_chunker(ChunkingStrategy.RECURSIVE)


__all__ = [
    "DEFAULT_INDEX_ID",
    "RetrievalService",
    "get_embedding_provider",
    "get_vector_store",
    "get_retrieval_pipeline",
    "get_retrieval_service",
    "get_generation_pipeline",
    "get_chunker",
    "get_current_user",
    "np",
]
