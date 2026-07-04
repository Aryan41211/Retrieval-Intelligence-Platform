from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.generation.exceptions import EmptyContextError
from backend.generation.models import ContextItem
from backend.retrieval.retrieval_result import RetrievalChunkResult


def _estimate_tokens(text: str) -> int:
    # Lightweight heuristic: average ~4 chars per token.
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class ContextBuildConfig:
    max_context_tokens: int = 2000
    dedupe_by_chunk_id: bool = True


class ContextBuilder:
    """Builds LLM-ready context from retrieved chunks.

    Responsibilities:
    - order chunks
    - remove duplicate context (by chunk_id)
    - estimate tokens
    - truncate to fit max_context_tokens
    """

    def __init__(self, config: ContextBuildConfig | None = None):
        self._config = config or ContextBuildConfig()

    def build(self, *, query: str, retrieved_chunks: list[Any]) -> list[ContextItem]:
        if not retrieved_chunks:
            raise EmptyContextError("No retrieved chunks provided")

        # Expect RetrievalChunkResult-like objects.
        items: list[ContextItem] = []
        for idx, c in enumerate(retrieved_chunks, start=1):
            chunk_id = str(getattr(c, "chunk_id"))
            document_id = str(getattr(c, "document_id"))
            chunk_text = getattr(c, "chunk_text") or ""
            rank = int(getattr(c, "rank", idx))
            similarity_score = float(getattr(c, "similarity_score", 0.0))
            source_filename = getattr(c, "source_filename", None)
            page_number = None

            items.append(
                ContextItem(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_text=chunk_text,
                    rank=rank,
                    similarity_score=similarity_score,
                    source_filename=source_filename,
                    page_number=page_number,
                    extra=getattr(c, "metadata", {}) or {},
                )
            )

        # Deduplicate by chunk_id.
        if self._config.dedupe_by_chunk_id:
            seen: set[str] = set()
            deduped: list[ContextItem] = []
            for it in items:
                if it.chunk_id in seen:
                    continue
                seen.add(it.chunk_id)
                deduped.append(it)
            items = deduped

        # Truncate by token estimate.
        total = 0
        out: list[ContextItem] = []
        for it in items:
            t = _estimate_tokens(it.chunk_text)
            if total + t > self._config.max_context_tokens:
                break
            out.append(it)
            total += t

        if not out:
            raise EmptyContextError("Context truncated to empty output")

        return out
