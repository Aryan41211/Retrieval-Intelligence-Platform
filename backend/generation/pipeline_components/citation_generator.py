from __future__ import annotations

import logging
import re

from backend.generation.models import Citation, ContextItem

logger = logging.getLogger(__name__)


class CitationGenerator:
    """Extract citations from generated answer text."""

    def __init__(self, *, marker_pattern: str = r"\[doc_(\d+)\]"):
        self._marker_pattern = re.compile(marker_pattern)
        self._marker_to_index: dict[str, int] = {}

    def generate(self, *, answer: str, context_items: list[ContextItem]) -> list[Citation]:
        if not context_items:
            return []

        markers = sorted(set(self._marker_pattern.findall(answer)))
        if not markers:
            return []

        self._marker_to_index = {m: idx + 1 for idx, m in enumerate(markers)}

        citations: list[Citation] = []
        for marker in markers:
            doc_idx = self._marker_to_index[marker]
            if doc_idx < 1 or doc_idx > len(context_items):
                logger.warning("Citation marker [doc_%s] out of range for %d context items", marker, len(context_items))
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
