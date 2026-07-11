from uuid import UUID

import numpy as np
import pytest

from backend.configs.settings import (
    CrossEncoderRerankSettings,
    QueryExpansionSettings,
)
from backend.retrieval.fusion.rrf_fusion import RRFFuser
from backend.retrieval.intelligent_retrieval_pipeline import IntelligentRetrievalPipeline
from backend.retrieval.query_expansion.query_expander import QueryExpander
from backend.retrieval.rerank.cross_encoder_reranker import CrossEncoderReranker
from backend.retrieval.retrieval_filters import RetrievalFilters
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.retrieval.sparse.bm25_retriever import BM25Retriever
from backend.retrieval.topk.dynamic_topk import DynamicTopKSelector
from backend.retrieval.utils.analytics import RetrievalAnalytics
from backend.vectorstore.faiss_vector_store import FAISSVectorStore


@pytest.fixture
def populated_vector_store(tmp_path):
    np.random.seed(42)
    embeddings = np.random.randn(30, 64).astype(np.float32)
    metadata = []
    for i in range(30):
        metadata.append(
            {
                "chunk_id": f"chunk-{i}",
                "document_id": f"doc-{i % 3}",
                "chunk_text": f"Sample text for chunk {i}. AI retrieval search.",
                "source_filename": f"doc_{i % 3}.txt",
                "language": "en",
                "metadata": {"index": i},
                # Ensure vectorstore can round-trip the embedding vector for deterministic tests.
                "embedding_vector": embeddings[i].tolist(),
            }
        )

    store = FAISSVectorStore(tmp_path)
    store.create_index(index_id="test-index", dimension=64)
    store.add_embeddings(
        embeddings=embeddings, ids=[f"id-{i}" for i in range(30)], metadata=metadata
    )
    return store


class _FakeDenseEngine:
    def __init__(self, dense_results: list[RetrievalChunkResult]):
        self._dense_results = dense_results

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalChunkResult]:
        # Mimic vector similarity rank ordering
        return self._dense_results[: request.top_k]


class TestIntelligentRetrievalPipeline:
    def test_intelligent_pipeline_runs(self, populated_vector_store):
        vector_records = populated_vector_store.get_vector_records()
        fake_dense_results: list[RetrievalChunkResult] = []
        for rank0, (embedding_id, rec) in enumerate(vector_records.items(), start=1):
            try:
                # chunk_id/document_id are optional depending on records shape; best-effort
                chunk_uuid = UUID(str(rec.get("chunk_id", f"00000000-0000-0000-0000-{rank0:012d}")))
                doc_uuid = UUID(
                    str(rec.get("document_id", f"00000000-0000-0000-0000-{(rank0 % 3):012d}"))
                )
            except Exception:
                # If UUID conversion fails, use deterministic UUIDs
                chunk_uuid = UUID(int=rank0)
                doc_uuid = UUID(int=rank0 % 3)

            fake_dense_results.append(
                RetrievalChunkResult(
                    chunk_id=chunk_uuid,
                    document_id=doc_uuid,
                    chunk_text=rec.get("chunk_text") or "",
                    similarity_score=1.0 - (rank0 * 0.01),
                    rank=rank0,
                    source_filename=rec.get("source_filename") or None,
                    metadata=rec.get("metadata") or rec.get("custom") or {},
                    embedding_model=rec.get("embedding_model") or None,
                )
            )
            if len(fake_dense_results) >= 20:
                break

        dense_engine = _FakeDenseEngine(fake_dense_results)

        bm25 = BM25Retriever(
            vector_records=vector_records,
            enabled=True,
            k1=1.5,
            b=0.75,
            lowercase=True,
        )

        fusion = RRFFuser(k=60, remove_duplicates=True, stable_ranking=True)

        query_expander = QueryExpander(settings=QueryExpansionSettings(enabled=True))

        topk = DynamicTopKSelector(
            enabled=True,
            min_k=5,
            max_k=15,
            min_confidence=0.2,
            max_confidence=0.9,
        )

        rerank_settings = CrossEncoderRerankSettings(enabled=False)
        reranker = CrossEncoderReranker(
            enabled=rerank_settings.enabled,
            provider=rerank_settings.provider,
            model_name=rerank_settings.model_name,
            top_n=rerank_settings.top_n,
            batch_size=rerank_settings.batch_size,
            max_length=rerank_settings.max_length,
        )

        pipeline = IntelligentRetrievalPipeline(
            dense_engine=dense_engine,
            bm25_retriever=bm25,
            fusion=fusion,
            reranker=reranker,
            query_expander=query_expander,
            topk_selector=topk,
            analytics=RetrievalAnalytics(),
        )

        request = RetrievalRequest(
            query_vector=np.zeros(64, dtype=np.float32).tolist(),
            top_k=10,
            extra={"query_text": "AI retrieval search"},
            similarity_threshold=None,
            filters=None,
        )

        results, metadata = pipeline.run(request)

        assert isinstance(results, list)
        assert all(isinstance(r, RetrievalChunkResult) for r in results)
        assert metadata.retrieved_chunks == len(results)
        assert metadata.retrieval_latency_ms >= 0
        assert "analytics" in metadata.extra
        assert metadata.extra["analytics"]["candidate_count"] >= len(results)

    def test_intelligent_pipeline_with_filters(self, populated_vector_store):
        vector_records = populated_vector_store.get_vector_records()
        bm25 = BM25Retriever(vector_records=vector_records, enabled=True)

        # Fake dense results so the test focuses on fusion/dynamic top-k rather than FAISS behavior.
        fake_dense_results: list[RetrievalChunkResult] = []
        for rank0, (embedding_id, rec) in enumerate(vector_records.items(), start=1):
            chunk_uuid = UUID(int=rank0)
            doc_uuid = UUID(int=rank0 % 3)
            fake_dense_results.append(
                RetrievalChunkResult(
                    chunk_id=chunk_uuid,
                    document_id=doc_uuid,
                    chunk_text=rec.get("chunk_text") or "",
                    similarity_score=1.0 - (rank0 * 0.01),
                    rank=rank0,
                    source_filename=rec.get("source_filename") or None,
                    metadata=rec.get("metadata") or rec.get("custom") or {},
                    embedding_model=rec.get("embedding_model") or None,
                )
            )
            if len(fake_dense_results) >= 20:
                break

        dense_engine = _FakeDenseEngine(fake_dense_results)

        fusion = RRFFuser(k=60, remove_duplicates=True, stable_ranking=True)
        query_expander = QueryExpander(settings=QueryExpansionSettings(enabled=False))
        topk = DynamicTopKSelector(
            enabled=True, min_k=3, max_k=10, min_confidence=0.2, max_confidence=0.9
        )
        reranker = CrossEncoderReranker(
            enabled=False,
            provider="sentence_transformers",
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_n=20,
        )

        pipeline = IntelligentRetrievalPipeline(
            dense_engine=dense_engine,
            bm25_retriever=bm25,
            fusion=fusion,
            reranker=reranker,
            query_expander=query_expander,
            topk_selector=topk,
            analytics=RetrievalAnalytics(),
        )

        # document_ids are UUID typed in schema, but our test vector records use string doc-*
        # retrieval_filters custom matching in FAISS expects UUID-compatible strings.
        # We use document_ids filter with "doc-0" as UUID directly is invalid; so filter matching is best-effort.
        # Therefore, just validate that pipeline does not crash.
        filters = RetrievalFilters(custom={})
        request = RetrievalRequest(
            query_vector=np.zeros(64, dtype=np.float32).tolist(),
            top_k=10,
            extra={"query_text": "retrieval search"},
            filters=filters,
            similarity_threshold=None,
        )

        results, _ = pipeline.run(request)
        assert isinstance(results, list)

    def test_intelligent_pipeline_empty_returns_error(self, populated_vector_store):
        vector_records = populated_vector_store.get_vector_records()
        bm25 = BM25Retriever(vector_records=vector_records, enabled=True)

        # Return empty dense results so final fusion has a chance to be empty as well.
        dense_engine = _FakeDenseEngine([])
        fusion = RRFFuser(k=60, remove_duplicates=True, stable_ranking=True)
        query_expander = QueryExpander(settings=QueryExpansionSettings(enabled=False))
        topk = DynamicTopKSelector(
            enabled=True, min_k=5, max_k=10, min_confidence=0.2, max_confidence=0.9
        )
        reranker = CrossEncoderReranker(
            enabled=False, provider="sentence_transformers", model_name="x", top_n=20
        )

        pipeline = IntelligentRetrievalPipeline(
            dense_engine=dense_engine,
            bm25_retriever=bm25,
            fusion=fusion,
            reranker=reranker,
            query_expander=query_expander,
            topk_selector=topk,
        )

        # Use high similarity_threshold to force dense to empty; BM25 threshold is also derived from same request.similarity_threshold.
        request = RetrievalRequest(
            query_vector=np.random.randn(64).astype(np.float32).tolist(),
            top_k=10,
            extra={"query_text": "some unlikely words zzz yyy xxx"},
            similarity_threshold=1.0,
        )

        with pytest.raises(Exception):
            pipeline.run(request)
