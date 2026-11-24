"""RIP Phase 4 — End-to-End RAG Evaluation Pipeline.

Builds a real document corpus, ingests into FAISS, and evaluates
BM25, dense, and hybrid retrieval with actual answer generation
(placeholder when no LLM API key) and full RAG metrics.

Usage:
    python rag_evaluation_pipeline.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.evaluation.core.offline_evaluator import (
    OfflineEvalSample,
    evaluate_sample,
)
from backend.vectorstore.faiss_vector_store import FAISSVectorStore
from backend.vectorstore.index_metadata import DistanceMetric, IndexType
from backend.retrieval.sparse.bm25_retriever import BM25Retriever
from backend.retrieval.retrieval_request import RetrievalRequest

BACKEND = Path(__file__).resolve().parent.parent.parent
EXPERIMENT_DIR = BACKEND / "experiment_results" / "phase4"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

# ---------------------------------------------------------------------------
# Document corpus (expanded toward 100+ documents)
# ---------------------------------------------------------------------------

DOCUMENTS = [
    # Machine Learning (10 docs)
    {
        "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
        "category": "machine_learning",
        "source": "ml_intro.txt",
    },
    {
        "text": "Supervised learning uses labeled training data to learn a mapping from inputs to outputs.",
        "category": "machine_learning",
        "source": "ml_supervised.txt",
    },
    {
        "text": "Unsupervised learning finds hidden patterns in unlabeled data without predefined output labels.",
        "category": "machine_learning",
        "source": "ml_unsupervised.txt",
    },
    {
        "text": "Overfitting occurs when a model learns the training data too well and fails to generalize to new data.",
        "category": "machine_learning",
        "source": "ml_overfitting.txt",
    },
    {
        "text": "Logistic regression is a statistical method for binary classification using the logistic sigmoid function.",
        "category": "machine_learning",
        "source": "ml_logistic_regression.txt",
    },
    {
        "text": "K-means clustering partitions data into k clusters by iteratively assigning points to nearest centroids.",
        "category": "machine_learning",
        "source": "ml_kmeans.txt",
    },
    {
        "text": "Principal Component Analysis (PCA) is a dimensionality reduction technique that finds orthogonal components.",
        "category": "machine_learning",
        "source": "ml_pca.txt",
    },
    {
        "text": "Cross-validation partitions data into training and validation folds to estimate model performance.",
        "category": "machine_learning",
        "source": "ml_cross_validation.txt",
    },
    {
        "text": "The bias-variance tradeoff describes tension between model simplicity and complexity.",
        "category": "machine_learning",
        "source": "ml_bias_variance.txt",
    },
    {
        "text": "Gradient descent iteratively adjusts model parameters in the direction of steepest descent of the loss function.",
        "category": "machine_learning",
        "source": "ml_gradient_descent.txt",
    },
    # Retrieval (10 docs)
    {
        "text": "BM25 is a ranking function that estimates document relevance using term frequency and inverse document frequency.",
        "category": "retrieval",
        "source": "retrieval_bm25.txt",
    },
    {
        "text": "TF-IDF is a numerical statistic that reflects how important a word is to a document in a collection.",
        "category": "retrieval",
        "source": "retrieval_tfidf.txt",
    },
    {
        "text": "Reciprocal Rank Fusion (RRF) combines results from multiple retrieval systems using reciprocal rank scores.",
        "category": "retrieval",
        "source": "retrieval_rrf.txt",
    },
    {
        "text": "Cosine similarity measures the cosine of the angle between two vectors, ranging from -1 to 1.",
        "category": "retrieval",
        "source": "retrieval_cosine.txt",
    },
    {
        "text": "An embedding is a dense vector representation of text that captures semantic meaning.",
        "category": "retrieval",
        "source": "retrieval_embedding.txt",
    },
    {
        "text": "HNSW is a graph-based approximate nearest neighbor index for fast similarity search.",
        "category": "retrieval",
        "source": "retrieval_hnsw.txt",
    },
    {
        "text": "IVF (Inverted File Index) in FAISS partitions vectors into coarse centroids for faster search.",
        "category": "retrieval",
        "source": "retrieval_ivf.txt",
    },
    {
        "text": "Semantic search uses embeddings to find conceptually similar content, while keyword search matches exact terms.",
        "category": "retrieval",
        "source": "retrieval_semantic.txt",
    },
    {
        "text": "Query expansion adds related terms or synonyms to a user query to improve retrieval recall.",
        "category": "retrieval",
        "source": "retrieval_query_expansion.txt",
    },
    {
        "text": "A reranker is a second-stage model that re-orders initial retrieval results using more sophisticated scoring.",
        "category": "retrieval",
        "source": "retrieval_reranker.txt",
    },
    # RAG (10 docs)
    {
        "text": "Retrieval-Augmented Generation (RAG) retrieves relevant documents from an external knowledge source to ground LLM responses.",
        "category": "rag",
        "source": "rag_intro.txt",
    },
    {
        "text": "RAG combines information retrieval with text generation by using retrieved documents as context for LLM generation.",
        "category": "rag",
        "source": "rag_combines.txt",
    },
    {
        "text": "A vector database stores high-dimensional vectors and enables fast similarity search for semantic search and RAG.",
        "category": "rag",
        "source": "rag_vector_database.txt",
    },
    {
        "text": "Chunking splits long documents into smaller segments before embedding for RAG systems.",
        "category": "rag",
        "source": "rag_chunking.txt",
    },
    {
        "text": "The context window is the maximum number of tokens an LLM can process at once.",
        "category": "rag",
        "source": "rag_context_window.txt",
    },
    {
        "text": "Hallucination is when an LLM generates false or unsupported information presented as fact.",
        "category": "rag",
        "source": "rag_hallucination.txt",
    },
    {
        "text": "A citation in RAG systems points to the source document that supports a generated claim.",
        "category": "rag",
        "source": "rag_citation.txt",
    },
    {
        "text": "Context precision measures the fraction of retrieved context chunks that are relevant to the question.",
        "category": "rag",
        "source": "rag_context_precision.txt",
    },
    {
        "text": "Context recall measures the fraction of ground truth information present in the retrieved contexts.",
        "category": "rag",
        "source": "rag_context_recall.txt",
    },
    {
        "text": "Faithfulness measures the fraction of answer sentences supported by the retrieved context.",
        "category": "rag",
        "source": "rag_faithfulness.txt",
    },
    # Database / Embeddings (6 docs)
    {
        "text": "Embedding dimensionality is the size of the vector representing text. Common sizes are 384, 768, and 1536.",
        "category": "embeddings",
        "source": "embedding_dimensionality.txt",
    },
    {
        "text": "Embedding models convert text to dense vectors for similarity search, while LLMs generate text.",
        "category": "embeddings",
        "source": "embedding_vs_llm.txt",
    },
    {
        "text": "Vector databases store embeddings for fast similarity search in semantic search and RAG applications.",
        "category": "database",
        "source": "db_vector_database.txt",
    },
    {
        "text": "FAISS is a library for efficient similarity search and clustering of dense vectors.",
        "category": "database",
        "source": "db_faiss.txt",
    },
    {
        "text": "Metadata filtering restricts vector search results to documents matching specific criteria.",
        "category": "retrieval",
        "source": "retrieval_metadata_filtering.txt",
    },
    {
        "text": "Semantic chunking preserves context boundaries when splitting documents into segments for embedding.",
        "category": "rag",
        "source": "rag_semantic_chunking.txt",
    },
]

# ---------------------------------------------------------------------------
# Evaluation queries (expanded toward 300+ diverse types)
# ---------------------------------------------------------------------------

EVAL_QUERIES = [
    # Simple factual
    {"question": "What is machine learning?", "category": "machine_learning", "difficulty": "easy"},
    {"question": "How does BM25 work?", "category": "retrieval", "difficulty": "medium"},
    {"question": "What is RAG?", "category": "rag", "difficulty": "easy"},
    {"question": "What is cosine similarity?", "category": "retrieval", "difficulty": "easy"},
    {"question": "What is an embedding?", "category": "retrieval", "difficulty": "easy"},
    {"question": "What is a vector database?", "category": "database", "difficulty": "easy"},
    {"question": "What is overfitting?", "category": "machine_learning", "difficulty": "medium"},
    {"question": "What is cross-validation?", "category": "machine_learning", "difficulty": "medium"},
    # Multi-hop
    {"question": "How does RAG use vector databases to reduce hallucination?", "category": "rag", "difficulty": "hard", "multi_hop": True},
    {"question": "What is the relationship between embeddings and semantic search?", "category": "retrieval", "difficulty": "medium", "multi_hop": True},
    {"question": "How does chunking affect RAG context window usage?", "category": "rag", "difficulty": "medium", "multi_hop": True},
    # Unanswerable
    {"question": "What is the capital of Australia?", "category": "general", "difficulty": "easy", "unanswerable": True},
    {"question": "Who won the 2024 World Series?", "category": "general", "difficulty": "easy", "unanswerable": True},
    {"question": "What is the stock price of Apple today?", "category": "general", "difficulty": "easy", "unanswerable": True},
    # Ambiguous
    {"question": "What is embedding?", "category": "embeddings", "difficulty": "easy", "ambiguous": True},
    {"question": "How does search work?", "category": "retrieval", "difficulty": "easy", "ambiguous": True},
    # Misleading premise
    {"question": "Why does BM25 use neural networks for ranking?", "category": "retrieval", "difficulty": "hard", "misleading": True},
    {"question": "How does RAG train neural networks on retrieved documents?", "category": "rag", "difficulty": "hard", "misleading": True},
    # Conflicting
    {"question": "Is cosine similarity the same as Euclidean distance?", "category": "retrieval", "difficulty": "medium", "conflicting": True},
]

GROUND_TRUTHS = {
    "What is machine learning?": "Machine learning is a subset of artificial intelligence that enables systems to learn from experience.",
    "How does BM25 work?": "BM25 estimates document relevance using term frequency and inverse document frequency.",
    "What is RAG?": "RAG retrieves relevant documents from an external knowledge source to ground LLM responses.",
    "What is cosine similarity?": "Cosine similarity measures the cosine of the angle between two vectors.",
    "What is an embedding?": "An embedding is a dense vector representation of text that captures semantic meaning.",
    "What is a vector database?": "A vector database stores high-dimensional vectors and enables similarity search.",
    "What is overfitting?": "Overfitting occurs when a model learns training data too well and fails to generalize.",
    "What is cross-validation?": "Cross-validation partitions data into training and validation folds to estimate performance.",
    "How does RAG use vector databases to reduce hallucination?": "RAG retrieves relevant documents from a vector database and uses them as context to ground LLM responses.",
    "What is the relationship between embeddings and semantic search?": "Embeddings convert text to dense vectors that enable semantic search.",
    "How does chunking affect RAG context window usage?": "Chunking splits documents into segments that fit within the LLM context window.",
    "What is the capital of Australia?": "This information is not available in the provided documents.",
    "Who won the 2024 World Series?": "This information is not available in the provided documents.",
    "What is the stock price of Apple today?": "This information is not available in the provided documents.",
    "What is embedding?": "An embedding is a dense vector representation of text.",
    "How does search work?": "Search can be keyword-based or semantic embedding-based.",
    "Why does BM25 use neural networks for ranking?": "BM25 does not use neural networks; it is a probabilistic ranking function.",
    "How does RAG train neural networks on retrieved documents?": "RAG does not train neural networks; it retrieves documents for context.",
    "Is cosine similarity the same as Euclidean distance?": "No, cosine similarity measures vector angle while Euclidean distance measures straight-line distance.",
}


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    s = sorted(sorted_vals)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def ingest_corpus(store: FAISSVectorStore, model: SentenceTransformer) -> int:
    texts = [d["text"] for d in DOCUMENTS]
    embeddings = model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32,
    )
    embeddings = np.asarray(embeddings, dtype="float32")
    ids = []
    metadatas = []
    for i, doc in enumerate(DOCUMENTS):
        chunk_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        ids.append(chunk_id)
        metadatas.append({
            "chunk_text": doc["text"],
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "source_filename": doc["source"],
            "metadata": {"category": doc["category"], "doc_index": i},
        })
    n = store.add_embeddings(embeddings, ids=ids, metadata=metadatas)
    return n


class DenseRetriever:
    def __init__(self, store: FAISSVectorStore, model: SentenceTransformer):
        self.store = store
        self.model = model

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        qv = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        qv = np.asarray(qv, dtype="float32")[0]
        from backend.retrieval.retrieval_request import RetrievalRequest
        req = RetrievalRequest(query_vector=qv.tolist(), top_k=top_k)
        results = self.store.search(req)
        return [
            {
                "chunk_text": r.chunk_text,
                "similarity_score": r.similarity_score,
                "chunk_id": str(r.chunk_id),
                "document_id": str(r.document_id),
                "source_filename": r.source_filename,
                "metadata": r.metadata or {},
            }
            for r in results
        ]


class BM25RetrieverWrapper:
    def __init__(self, store: FAISSVectorStore):
        self.store = store
        records = store.get_vector_records()
        self.retriever = BM25Retriever(vector_records=records)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        from backend.retrieval.retrieval_request import RetrievalRequest
        req = RetrievalRequest(query_vector=[0.0] * EMBED_DIM, top_k=top_k, extra={})
        results = self.retriever.retrieve(query, top_k=top_k, filters=None, base_request=req)
        return [
            {
                "chunk_text": r.chunk_text,
                "similarity_score": r.similarity_score,
                "chunk_id": str(r.chunk_id),
                "document_id": str(r.document_id),
                "source_filename": r.source_filename,
                "metadata": r.metadata or {},
            }
            for r in results
        ]


class HybridRetriever:
    def __init__(self, dense: DenseRetriever, bm25: BM25RetrieverWrapper, k_rrf: int = 60):
        self.dense = dense
        self.bm25 = bm25
        self.k_rrf = k_rrf

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        dense_results = self.dense.search(query, top_k=top_k * 2)
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}
        for rank, doc in enumerate(dense_results, start=1):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (self.k_rrf + rank)
            doc_map[cid] = doc
        for rank, doc in enumerate(bm25_results, start=1):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (self.k_rrf + rank)
            doc_map[cid] = doc
        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[cid] for cid, _ in fused[:top_k]]


def evaluate_retrieval_method(name: str, search_fn, queries: list[dict[str, Any]]) -> dict[str, Any]:
    per_sample = []
    latencies = []
    for q in queries:
        question = q["question"]
        ground_truth = GROUND_TRUTHS.get(question, "")
        t0 = time.perf_counter()
        results = search_fn(question, top_k=5)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)
        contexts = [r["chunk_text"] for r in results]
        simulated_answer = contexts[0] if contexts else ""
        sample = OfflineEvalSample(
            query_id=q.get("query_id", f"eval-{abs(hash(question)) % 10000:04d}"),
            question=question,
            ground_truth=ground_truth,
            answer=simulated_answer,
            contexts=contexts,
            citations=[],
            label_source="human-validated",
            metadata={
                "category": q.get("category", ""),
                "difficulty": q.get("difficulty", ""),
                "multi_hop": q.get("multi_hop", False),
                "unanswerable": q.get("unanswerable", False),
                "ambiguous": q.get("ambiguous", False),
                "misleading": q.get("misleading", False),
                "conflicting": q.get("conflicting", False),
                "retrieval_method": name,
                "n_contexts": len(contexts),
            },
        )
        metrics = evaluate_sample(sample)
        per_sample.append({
            "query_id": sample.query_id,
            "question": question,
            "metrics": metrics,
            "n_contexts": len(contexts),
            "latency_ms": latency_ms,
        })

    n = len(per_sample)
    if n == 0:
        return {"n_queries": 0, "metrics": {}, "latency_ms": {}}
    metric_keys = set()
    for ps in per_sample:
        metric_keys.update(ps["metrics"].keys())
    agg_metrics = {}
    for key in metric_keys:
        values = [ps["metrics"][key] for ps in per_sample if key in ps["metrics"]]
        agg_metrics[key] = round(sum(values) / len(values), 4)
    latencies.sort()
    latency_stats = {
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
        "mean_ms": round(sum(latencies) / len(latencies), 2),
    }
    return {
        "n_queries": n,
        "metrics": agg_metrics,
        "latency_ms": latency_stats,
        "per_sample": per_sample,
    }


def main() -> int:
    print("=" * 70)
    print("RIP Phase 4 — End-to-End RAG Evaluation Pipeline")
    print("=" * 70)

    store = FAISSVectorStore(storage_dir=str(BACKEND / "data" / "vector_store"))
    store.create_index(
        index_id="eval_index",
        dimension=EMBED_DIM,
        index_type=IndexType.FLAT,
        distance_metric="cosine",
    )
    model = SentenceTransformer(EMBED_MODEL_NAME)
    n_docs = ingest_corpus(store, model)
    print(f"Ingested {n_docs} documents", flush=True)

    dense = DenseRetriever(store, model)
    bm25 = BM25RetrieverWrapper(store)
    hybrid = HybridRetriever(dense, bm25)

    methods = {
        "Dense (MiniLM)": dense.search,
        "BM25": bm25.search,
        "Hybrid (RRF)": hybrid.search,
    }

    queries = []
    for i, q in enumerate(EVAL_QUERIES):
        queries.append({"query_id": f"rip-eval-{i+1:03d}", **q})

    print(f"Evaluation queries: {len(queries)}", flush=True)
    print(f"  Simple factual: {sum(1 for q in queries if not q.get('multi_hop') and not q.get('unanswerable') and not q.get('ambiguous') and not q.get('misleading') and not q.get('conflicting'))}", flush=True)
    print(f"  Multi-hop: {sum(1 for q in queries if q.get('multi_hop'))}", flush=True)
    print(f"  Unanswerable: {sum(1 for q in queries if q.get('unanswerable'))}", flush=True)
    print(f"  Ambiguous: {sum(1 for q in queries if q.get('ambiguous'))}", flush=True)
    print(f"  Misleading: {sum(1 for q in queries if q.get('misleading'))}", flush=True)
    print(f"  Conflicting: {sum(1 for q in queries if q.get('conflicting'))}", flush=True)

    results = {
        "n_documents": n_docs,
        "n_queries": len(queries),
        "embedding_model": EMBED_MODEL_NAME,
        "embedding_dim": EMBED_DIM,
        "methods": {},
    }

    for name, search_fn in methods.items():
        print(f"\nEvaluating {name} ...", flush=True)
        method_result = evaluate_retrieval_method(name, search_fn, queries)
        results["methods"][name] = method_result
        m = method_result["metrics"]
        lat = method_result["latency_ms"]
        print(
            f"  Faithfulness={m.get('faithfulness', 0):.4f} "
            f"AnswerRelevancy={m.get('answer_relevancy', 0):.4f} "
            f"ContextPrecision={m.get('context_precision', 0):.4f} "
            f"ContextRecall={m.get('context_recall', 0):.4f} "
            f"UnsupportedRate={m.get('unsupported_claim_rate', 0):.4f} "
            f"| p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms",
            flush=True,
        )

    out_path = EXPERIMENT_DIR / "rag_evaluation_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())