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
import threading
from collections import OrderedDict
from functools import lru_cache
from typing import Any

from starlette.concurrency import run_in_threadpool

from backend.configs.settings import get_settings
from backend.data.chunking.factory import ChunkerFactory
from backend.data.embeddings.embedding_factory import EmbeddingFactory
from backend.data.models.chunk import ChunkingStrategy

# Real authentication dependency (JWT / bearer) provided by the enterprise layer.
from backend.enterprise.rbac import (  # noqa: F401  (re-exported for routers)
    get_current_active_user,
    get_current_user,
)
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

    async def retrieve_async(
        self,
        query: str,
        *,
        top_k: int | None = None,
        threshold: float | None = None,
        correlation_id: str | None = None,
    ) -> tuple[list[Any], Any | None]:
        """Retrieve chunks without blocking the event loop.

        Embedding the query and searching FAISS are CPU-bound and synchronous.
        Calling :meth:`retrieve` directly from an async route stalled the whole
        event loop for the duration of every search.

        Returns:
            A tuple of ``(chunks, retrieval_metadata)``.
        """
        return await run_in_threadpool(
            self.retrieve,
            query,
            top_k=top_k,
            threshold=threshold,
            correlation_id=correlation_id,
        )

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        threshold: float | None = None,
        correlation_id: str | None = None,
    ) -> tuple[list[Any], Any | None]:
        """Retrieve real chunks for a query (blocking).

        Prefer :meth:`retrieve_async` from request handlers.

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
    """Return the cached embedding provider built from configuration."""
    embedding = get_settings().embedding
    config: dict[str, Any] = {}
    if embedding.device:
        config["device"] = embedding.device
    if embedding.batch_size:
        config["batch_size"] = embedding.batch_size
    return EmbeddingFactory.create_sentence_transformer(
        model_name=embedding.model_name,
        config=config or None,
    )


# One vector store per namespace. The FAISS store keeps a single index in
# ``self._index``, so isolating tenants means isolating store instances rather
# than teaching one store about many indices.
#
# The cache is bounded: each entry holds a FAISS index in memory, so an
# unbounded map would grow with the number of active users. Evicting an entry is
# safe because every write is persisted to disk (``auto_save``) before the lock
# is released; the store is simply rebuilt from disk on next use.
_STORE_CACHE_MAX = 32
_store_cache: OrderedDict[str, Any] = OrderedDict()
_store_cache_lock = threading.Lock()


def _create_store(index_id: str) -> Any:
    """Build a vector store bound to a single namespace index."""
    settings = get_settings()
    store = VectorStoreFactory.create(
        settings.vector_store.provider,
        settings.vector_store.storage_dir,
    )
    if settings.vector_store.auto_load:
        try:
            if store.index_exists(index_id):
                store.load_index(index_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to pre-load vector index %s: %s", index_id, exc)
    return store


def get_namespace_store(index_id: str) -> Any:
    """Return the cached vector store for a namespace, creating it on first use.

    Args:
        index_id: Validated namespace index id (see :mod:`backend.api.namespaces`).

    Returns:
        A vector store whose loaded index belongs solely to that namespace.
    """
    with _store_cache_lock:
        store = _store_cache.get(index_id)
        if store is not None:
            _store_cache.move_to_end(index_id)
            return store

    # Build outside the lock: loading an index from disk is slow, and holding
    # the cache lock would serialise every unrelated namespace behind it.
    store = _create_store(index_id)

    with _store_cache_lock:
        existing = _store_cache.get(index_id)
        if existing is not None:
            # Another request built it first; keep the shared instance so the
            # ingestion write lock still guards a single object per namespace.
            _store_cache.move_to_end(index_id)
            return existing
        _store_cache[index_id] = store
        while len(_store_cache) > _STORE_CACHE_MAX:
            _store_cache.popitem(last=False)
    return store


def reset_store_cache() -> None:
    """Drop all cached stores. Used by tests and after configuration changes."""
    with _store_cache_lock:
        _store_cache.clear()


def get_vector_store() -> Any:
    """Return the store for the legacy shared index.

    Deprecated: retained only so existing callers keep working. New code must
    use :func:`get_namespace_store` with a namespace resolved from the caller,
    because this index is shared by every user.
    """
    return get_namespace_store(DEFAULT_INDEX_ID)


def _build_intelligent_pipeline(store: Any) -> Any:
    """Assemble the hybrid retrieval pipeline from configuration.

    Args:
        store: The runtime vector store; its records back the BM25 index.

    Returns:
        A configured :class:`IntelligentRetrievalPipeline`.
    """
    from backend.retrieval.fusion.rrf_fusion import RRFFuser
    from backend.retrieval.intelligent_retrieval_pipeline import IntelligentRetrievalPipeline
    from backend.retrieval.query_expansion.query_expander import QueryExpander
    from backend.retrieval.rerank.cross_encoder_reranker import CrossEncoderReranker
    from backend.retrieval.sparse.bm25_retriever import BM25Retriever
    from backend.retrieval.topk.dynamic_topk import DynamicTopKSelector

    intelligent = get_settings().retrieval.intelligent

    bm25 = BM25Retriever(
        # BM25 scores the same records the dense index holds, so the sparse and
        # dense views stay consistent without a second corpus copy.
        vector_records=getattr(store, "_vector_records", {}) or {},
        enabled=intelligent.sparse_enabled and intelligent.bm25.enabled,
        k1=intelligent.bm25.k1,
        b=intelligent.bm25.b,
        lowercase=intelligent.bm25.lowercase,
    )
    fusion = RRFFuser(
        k=intelligent.rrf.k,
        remove_duplicates=intelligent.rrf.remove_duplicates,
        stable_ranking=intelligent.rrf.stable_ranking,
    )
    reranker = (
        CrossEncoderReranker(
            enabled=True,
            model_name=intelligent.rerank.model_name,
            top_n=intelligent.rerank.top_n,
            batch_size=intelligent.rerank.batch_size,
            max_length=intelligent.rerank.max_length,
            provider=intelligent.rerank.provider,
        )
        if intelligent.rerank.enabled
        else None
    )
    return IntelligentRetrievalPipeline(
        dense_engine=RetrievalEngine(store),
        bm25_retriever=bm25,
        fusion=fusion,
        reranker=reranker,
        query_expander=QueryExpander(settings=intelligent.query_expansion),
        topk_selector=DynamicTopKSelector(
            enabled=intelligent.dynamic_top_k.enabled,
            min_k=intelligent.dynamic_top_k.min_k,
            max_k=intelligent.dynamic_top_k.max_k,
            min_confidence=intelligent.dynamic_top_k.min_confidence,
            max_confidence=intelligent.dynamic_top_k.max_confidence,
        ),
    )


def build_pipeline_for_index(index_id: str) -> Any:
    """Build a retrieval pipeline scoped to a single namespace index.

    Returns the hybrid :class:`IntelligentRetrievalPipeline` when
    ``INTELLIGENT_RETRIEVAL_ENABLED`` is set, otherwise the dense-only pipeline.
    Both expose the same ``run(request) -> (chunks, metadata)`` contract.
    """
    store = get_namespace_store(index_id)
    if get_settings().retrieval.intelligent.enabled:
        try:
            return _build_intelligent_pipeline(store)
        except Exception as exc:
            # Never take the API down because an optional stage (e.g. the
            # cross-encoder model) is unavailable; fall back to dense retrieval
            # and make the downgrade explicit in the logs.
            logger.error("Falling back to dense retrieval: hybrid pipeline unavailable: %s", exc)
    return RetrievalPipeline(RetrievalEngine(store))


def get_retrieval_pipeline() -> Any:
    """Build a pipeline over the legacy shared index (deprecated)."""
    return build_pipeline_for_index(DEFAULT_INDEX_ID)


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


def active_retrieval_strategy() -> str:
    """Return the retrieval strategy currently in effect."""
    return "hybrid" if get_settings().retrieval.intelligent.enabled else "dense"


def warm_up_caches() -> None:
    """Eagerly construct the expensive singletons.

    Without this the sentence-transformers model is loaded lazily inside the
    first request, which stalls that request for seconds and skews latency
    metrics. Failures are logged and left to surface per-request.
    """
    try:
        # Only the embedding model is warmed: vector stores are per namespace and
        # created on first use by the request that needs them.
        get_embedding_provider()
    except Exception as exc:  # pragma: no cover - defensive startup path
        logger.warning("Cache warm-up failed; falling back to lazy init: %s", exc)


def get_chunker() -> Any:
    """Return a recursive chunker for document ingestion."""
    return ChunkerFactory.create_chunker(ChunkingStrategy.RECURSIVE)


__all__ = [
    "DEFAULT_INDEX_ID",
    "RetrievalService",
    "get_embedding_provider",
    "get_vector_store",
    "get_namespace_store",
    "build_pipeline_for_index",
    "reset_store_cache",
    "get_retrieval_pipeline",
    "get_retrieval_service",
    "get_generation_pipeline",
    "get_chunker",
    "get_current_user",
    "get_current_active_user",
    "warm_up_caches",
    "active_retrieval_strategy",
]
