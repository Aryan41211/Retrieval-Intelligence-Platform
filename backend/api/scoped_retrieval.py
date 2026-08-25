"""Retrieval scoped to the namespaces a caller may read.

Retrieval used to run against one process-wide index, so results could include
documents belonging to other users. A search now fans out across the caller's
private namespace plus every workspace they belong to, and the per-namespace
results are merged into a single ranking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import (
    build_pipeline_for_index,
    get_embedding_provider,
    get_namespace_store,
)
from backend.api.namespaces import Namespace
from backend.configs.settings import get_settings
from backend.retrieval.exceptions import EmptyRetrievalResultError, RetrievalError
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.vectorstore.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScopedRetrievalResult:
    """Merged results plus the provenance of the search."""

    chunks: list[Any]
    latency_ms: float
    namespaces_searched: list[str]


def _search_namespace(
    namespace: Namespace,
    request: RetrievalRequest,
) -> list[Any]:
    """Run retrieval against one namespace, tolerating an absent index.

    A namespace with no documents yet simply has no index on disk; that is a
    normal state, not an error, so it contributes no results.
    """
    # A namespace with no documents has no index on disk. Skipping it here keeps
    # the normal "empty knowledge base" case off the exception path, which would
    # otherwise log a full ERROR traceback per namespace on every search.
    store = get_namespace_store(namespace.index_id)
    if getattr(store, "_index", None) is None and not store.index_exists(namespace.index_id):
        return []

    try:
        pipeline = build_pipeline_for_index(namespace.index_id)
        chunks, _ = pipeline.run(request)
    except (EmptyRetrievalResultError, RetrievalError, VectorStoreError) as exc:
        logger.debug("No results from namespace %s: %s", namespace.label, exc)
        return []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Retrieval failed for namespace %s: %s", namespace.label, exc)
        return []

    # Tag each chunk with the namespace it came from so callers can attribute a
    # result to a workspace rather than guessing from the filename.
    for chunk in chunks:
        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict):
            metadata.setdefault("namespace", namespace.label)
    return list(chunks)


def _merge(chunks: list[Any], top_k: int) -> list[Any]:
    """Merge per-namespace results into one ranking.

    Sorting is by similarity score descending. Ranks are then renumbered so the
    merged list is internally consistent; per-namespace ranks are meaningless
    once results from several indices are interleaved.
    """
    ordered = sorted(
        chunks,
        key=lambda c: getattr(c, "similarity_score", 0.0) or 0.0,
        reverse=True,
    )

    # Two namespaces can legitimately hold the same document (a user's private
    # copy and a workspace copy); keep the highest-scoring occurrence only.
    seen: set[str] = set()
    deduped: list[Any] = []
    for chunk in ordered:
        key = str(getattr(chunk, "chunk_id", id(chunk)))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)

    top = deduped[:top_k]
    for position, chunk in enumerate(top, start=1):
        try:
            chunk.rank = position
        except (AttributeError, TypeError):  # pragma: no cover - frozen results
            pass
    return top


class ScopedRetrievalService:
    """Retrieve chunks from every namespace a caller is permitted to read."""

    def __init__(self, *, embedding_provider: Any, top_k: int) -> None:
        self._embedding_provider = embedding_provider
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        namespaces: list[Namespace],
        *,
        top_k: int | None = None,
        threshold: float | None = None,
        correlation_id: str | None = None,
    ) -> ScopedRetrievalResult:
        """Search the given namespaces and return a merged ranking (blocking).

        Args:
            query: Natural-language query.
            namespaces: Namespaces the caller may read.
            top_k: Maximum results to return after merging.
            threshold: Optional minimum similarity score.
            correlation_id: Correlation id for logs.

        Returns:
            Merged chunks, total latency, and the namespaces consulted.
        """
        started = time.perf_counter()
        limit = top_k or self._top_k

        try:
            embedding = self._embedding_provider.embed_text(query)
            query_vector = list(embedding.embedding_vector)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Query embedding failed: %s", exc)
            return ScopedRetrievalResult([], 0.0, [])

        request = RetrievalRequest(
            query_vector=query_vector,
            top_k=limit,
            similarity_threshold=threshold,
            extra={"query_text": query},
            correlation_id=correlation_id,
        )

        collected: list[Any] = []
        for namespace in namespaces:
            collected.extend(_search_namespace(namespace, request))

        merged = _merge(collected, limit)
        latency_ms = (time.perf_counter() - started) * 1000
        return ScopedRetrievalResult(
            chunks=merged,
            latency_ms=round(latency_ms, 2),
            namespaces_searched=[ns.label for ns in namespaces],
        )

    async def retrieve_async(
        self,
        query: str,
        namespaces: list[Namespace],
        *,
        top_k: int | None = None,
        threshold: float | None = None,
        correlation_id: str | None = None,
    ) -> ScopedRetrievalResult:
        """Async wrapper: embedding and FAISS search are CPU-bound."""
        return await run_in_threadpool(
            self.retrieve,
            query,
            namespaces,
            top_k=top_k,
            threshold=threshold,
            correlation_id=correlation_id,
        )


def get_scoped_retrieval_service(
    embedding_provider: Any = Depends(get_embedding_provider),
) -> ScopedRetrievalService:
    """FastAPI dependency providing the namespace-aware retrieval service.

    The embedding provider is injected rather than fetched directly so tests can
    substitute it through ``app.dependency_overrides``; calling the cached
    factory inline would silently bypass those overrides.
    """
    return ScopedRetrievalService(
        embedding_provider=embedding_provider,
        top_k=get_settings().retrieval.top_k,
    )
