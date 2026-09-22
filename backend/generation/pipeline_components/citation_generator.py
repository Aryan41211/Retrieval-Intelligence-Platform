from __future__ import annotations

import logging
import re

from backend.generation.models import Citation, ContextItem

logger = logging.getLogger(__name__)


class CitationGenerator:
    """Extract citations from generated answer text."""

    def __init__(self, *, marker_pattern: str = r"\[doc_(\d+)\]"):
        self._marker_pattern = re.compile(marker_pattern)
        self._marker_to_index: dict[int, int] = {}

    def generate(self, *, answer: str, context_items: list[ContextItem]) -> list[Citation]:
        if not context_items:
            return []

        # Sort numerically: a lexicographic sort maps "10" before "2", which
        # attached every multi-digit marker to the wrong context chunk.
        markers = sorted({int(m) for m in self._marker_pattern.findall(answer)})
        if not markers:
            return []

        self._marker_to_index = {m: m for m in markers}

        citations: list[Citation] = []
        for doc_idx in markers:
            if doc_idx < 1 or doc_idx > len(context_items):
                logger.warning(
                    "Citation marker [doc_%d] out of range for %d context items",
                    doc_idx,
                    len(context_items),
                )
                continue

            item = context_items[doc_idx - 1]
            citations.append(
                Citation(
                    doc_index=doc_idx,
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    chunk_text=item.chunk_text,
                    confidence=item.similarity_score,
                    page_number=item.page_number,
                    extra={"source_filename": item.source_filename} if item.source_filename else {},
                )
            )

        return citations
