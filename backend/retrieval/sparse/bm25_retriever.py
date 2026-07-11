from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any

from backend.retrieval.exceptions import RetrievalError
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult

_WORD_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text or "")


@dataclass
class BM25Index:
    doc_freq: dict[str, int]
    token_freqs: list[dict[str, int]]  # aligned with doc_ids list
    doc_lens: list[int]
    avgdl: float
    doc_ids: list[str]  # embedding_id keys from FAISSVectorStore records


class BM25Retriever:
    """
    Lightweight pure-python BM25 retriever.

    Builds an in-memory BM25 index over FAISSVectorStore's stored `chunk_text` records.
    Designed to be swappable with a faster implementation later.
    """

    def __init__(
        self,
        *,
        vector_records: dict[str, dict[str, Any]],
        enabled: bool = True,
        k1: float = 1.5,
        b: float = 0.75,
        lowercase: bool = True,
    ):
        self._enabled = bool(enabled)
        self._k1 = float(k1)
        self._b = float(b)
        self._lowercase = bool(lowercase)

        self._vector_records = vector_records or {}
        self._index: BM25Index | None = None

        if self._enabled:
            self._build_index()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _build_index(self) -> None:
        # token_freqs aligned with doc_ids
        doc_ids = []
        token_freqs: list[dict[str, int]] = []
        doc_lens: list[int] = []
        doc_freq: dict[str, int] = {}

        for embedding_id, record in self._vector_records.items():
            chunk_text = record.get("chunk_text") or ""
            text = chunk_text.lower() if self._lowercase else chunk_text
            toks = _tokenize(text)
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            token_freqs.append(tf)
            doc_lens.append(len(toks))
            doc_ids.append(str(embedding_id))

            for term in tf.keys():
                doc_freq[term] = doc_freq.get(term, 0) + 1

        n_docs = max(1, len(doc_ids))
        avgdl = sum(doc_lens) / n_docs if n_docs else 0.0
        avgdl = float(avgdl) if avgdl > 0 else 1.0

        self._index = BM25Index(
            doc_freq=doc_freq,
            token_freqs=token_freqs,
            doc_lens=doc_lens,
            avgdl=avgdl,
            doc_ids=doc_ids,
        )

    def retrieve(
        self,
        query_text: str,
        *,
        top_k: int,
        filters: RetrievalFilters | None,
        base_request: RetrievalRequest,
    ) -> list[RetrievalChunkResult]:
        if not self._enabled:
            return []

        if not query_text or not query_text.strip():
            return []

        if self._index is None:
            raise RetrievalError("BM25 index is not built")

        t0 = time.perf_counter()

        query = query_text.lower() if self._lowercase else query_text
        q_toks = _tokenize(query)
        if not q_toks:
            return []

        # Precompute term set
        q_terms = set(q_toks)

        n_docs = len(self._index.doc_ids)
        # BM25 params
        k1 = self._k1
        b = self._b

        scores = [0.0] * n_docs

        # For each term, update scores
        for term in q_terms:
            df = self._index.doc_freq.get(term, 0)
            if df == 0:
                continue

            # IDF (Okapi BM25)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

            for i in range(n_docs):
                tf = self._index.token_freqs[i].get(term, 0)
                if tf == 0:
                    continue
                dl = self._index.doc_lens[i]
                denom = tf + k1 * (1.0 - b + b * (dl / self._index.avgdl))
                score_i = idf * (tf * (k1 + 1.0) / denom)
                scores[i] += score_i

        # Select top_k indices by score
        # Note: stable ordering by index for ties.
        top_k = int(top_k)
        top_k = max(0, min(top_k, n_docs))
        ranked_idx = sorted(range(n_docs), key=lambda i: (-scores[i], i))[:top_k]

        # Construct results applying filters + similarity_threshold (if any)
        threshold = base_request.similarity_threshold
        results: list[RetrievalChunkResult] = []
        for rank0, i in enumerate(ranked_idx, start=1):
            embedding_id = self._index.doc_ids[i]
            record = self._vector_records.get(embedding_id)
            if not record:
                continue

            # apply filters using FAISSVectorStore private logic? We can't access.
            # We implement minimal matching for document_ids/source_filenames/languages/custom exact.
            # For sprint 3: filter matching is best-effort.
            if not self._record_matches_filters(record, base_request):
                continue

            # BM25 score is not naturally bounded; convert to a pseudo [0,1] similarity.
            # Lightweight normalization: divide by (max_score or 1).
            # We'll do lazy normalization using max score from ranked subset.
            bm25_score = float(scores[i])
            # Normalize later after we collect? We'll compute max over ranked.
            results.append(
                RetrievalChunkResult(
                    chunk_id=record["chunk_id"],
                    document_id=record["document_id"],
                    chunk_text=record.get("chunk_text") or "",
                    similarity_score=0.0,  # fill below
                    rank=rank0,
                    source_filename=record.get("source_filename") or None,
                    metadata=record.get("metadata") or record.get("custom") or {},
                    embedding_model=record.get("embedding_model") or None,
                    retrieval_timestamp=base_request.retrieval_timestamp,
                )
            )

        # similarity threshold: apply using normalized BM25
        if results:
            max_score = max(scores[i] for i in ranked_idx) if ranked_idx else 1.0
            denom = float(max_score) if max_score != 0 else 1.0
            for r, i in zip(results, ranked_idx[: len(results)], strict=False):
                sim = max(0.0, float(scores[i]) / denom)
                # apply threshold if set
                if threshold is not None and sim < float(threshold):
                    continue
                # mutate by re-creating
            out: list[RetrievalChunkResult] = []
            for r, i in zip(results, ranked_idx[: len(results)], strict=False):
                sim = max(0.0, float(scores[i]) / denom)
                if threshold is not None and sim < float(threshold):
                    continue
                out.append(
                    RetrievalChunkResult(
                        **r.model_dump(exclude={"similarity_score"}),
                        similarity_score=sim,
                    )
                )
            results = out

        _ = int((time.perf_counter() - t0) * 1000)
        return results

    def _record_matches_filters(self, record: dict[str, Any], request: RetrievalRequest) -> bool:
        filters = request.filters
        if not filters and not any(
            [request.document_ids, request.source_filenames, request.languages]
        ):
            return True

        document_ids = request.document_ids or (filters.document_ids if filters else None)
        source_filenames = request.source_filenames or (
            filters.source_filenames if filters else None
        )
        languages = request.languages or (filters.languages if filters else None)
        custom_filters = (filters.custom if filters else {}) or {}

        if document_ids:
            doc_id = record.get("document_id")
            if doc_id is None or str(doc_id) not in {str(d) for d in document_ids}:
                return False

        if source_filenames:
            sf = record.get("source_filename") or record.get("source_file")
            if sf not in set(source_filenames):
                return False

        if languages:
            lang = record.get("language")
            if lang not in set(languages):
                return False

        record_custom = record.get("custom") or {}
        record_metadata = record.get("metadata") or {}
        for k, v in custom_filters.items():
            if k.startswith("custom."):
                kk = k.split("custom.", 1)[1]
                if record_custom.get(kk) != v:
                    return False
            else:
                if record_metadata.get(k) == v:
                    continue
                if record_custom.get(k) == v:
                    continue
                return False

        return True
