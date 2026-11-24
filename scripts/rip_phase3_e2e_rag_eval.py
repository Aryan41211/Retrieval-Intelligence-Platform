"""RIP Phase 3 — End-to-End RAG Evaluation.

Builds a real document corpus, ingests it into FAISS, and evaluates
BM25, dense, and hybrid retrieval with per-stage latency tracking.
Uses offline RAG metrics on actually retrieved contexts (not pre-written
Q&A pairs). Since no LLM API key is configured, generation is simulated
by using the top retrieved context as the answer — clearly marked as a
limitation.

Usage:
    python rip_phase3_e2e_rag_eval.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from backend.retrieval.retrieval_result import RetrievalChunkResult

BACKEND = Path(__file__).resolve().parent.parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

# ---------------------------------------------------------------------------
# Document corpus (synthetic but realistic — additional docs beyond eval Q&A)
# ---------------------------------------------------------------------------

DOCUMENTS = [
    # Machine Learning
    {
        "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data, identify patterns, and make decisions with minimal human intervention.",
        "category": "machine_learning",
        "source": "ml_intro.txt",
    },
    {
        "text": "Supervised learning uses labeled training data to learn a mapping from inputs to outputs, while unsupervised learning finds hidden patterns in unlabeled data without predefined output labels.",
        "category": "machine_learning",
        "source": "ml_supervised_vs_unsupervised.txt",
    },
    {
        "text": "Overfitting occurs when a model learns the training data too well, including noise, and fails to generalize to new data. Prevention techniques include cross-validation, regularization, early stopping, and using more training data.",
        "category": "machine_learning",
        "source": "ml_overfitting.txt",
    },
    {
        "text": "Logistic regression is a statistical method for binary classification that uses the logistic sigmoid function to model the probability of an input belonging to a particular class. It outputs values between 0 and 1, which can be interpreted as probabilities.",
        "category": "machine_learning",
        "source": "ml_logistic_regression.txt",
    },
    {
        "text": "K-means clustering partitions data into k clusters by iteratively assigning points to the nearest cluster centroid and recomputing centroids until convergence. It requires specifying k in advance.",
        "category": "machine_learning",
        "source": "ml_kmeans.txt",
    },
    {
        "text": "Principal Component Analysis (PCA) is a dimensionality reduction technique that finds orthogonal components capturing maximum variance in data. It is used for visualization, noise reduction, and feature extraction before classification.",
        "category": "machine_learning",
        "source": "ml_pca.txt",
    },
    {
        "text": "Cross-validation is a resampling technique that partitions data into training and validation folds multiple times to estimate model performance more reliably and reduce overfitting risk.",
        "category": "machine_learning",
        "source": "ml_cross_validation.txt",
    },
    {
        "text": "The bias-variance tradeoff describes the tension between model simplicity (high bias, low variance) and model complexity (low bias, high variance). Good models balance both to minimize total error.",
        "category": "machine_learning",
        "source": "ml_bias_variance.txt",
    },
    {
        "text": "A decision tree is a flowchart-like structure where internal nodes represent feature tests, branches represent outcomes, and leaves represent class labels or values. It is used for both classification and regression.",
        "category": "machine_learning",
        "source": "ml_decision_tree.txt",
    },
    {
        "text": "Gradient descent is an optimization algorithm that iteratively adjusts model parameters in the direction of steepest descent of the loss function to minimize error. Learning rate controls step size.",
        "category": "machine_learning",
        "source": "ml_gradient_descent.txt",
    },
    # Retrieval
    {
        "text": "BM25 is a ranking function used by search engines to estimate the relevance of documents to a given search query. It is based on the probabilistic retrieval framework and considers term frequency, inverse document frequency, and document length normalization.",
        "category": "retrieval",
        "source": "retrieval_bm25.txt",
    },
    {
        "text": "TF-IDF (Term Frequency-Inverse Document Frequency) is a numerical statistic that reflects how important a word is to a document in a collection. It weights frequent terms in a document down by their frequency across the document collection.",
        "category": "retrieval",
        "source": "retrieval_tfidf.txt",
    },
    {
        "text": "Reciprocal Rank Fusion (RRF) is a rank fusion method that combines results from multiple retrieval systems by assigning scores based on the reciprocal of each result's rank. The formula is 1/(k + rank), where k is a constant (typically 60).",
        "category": "retrieval",
        "source": "retrieval_rrf.txt",
    },
    {
        "text": "Cosine similarity measures the cosine of the angle between two vectors, ranging from -1 to 1. In vector search, it measures how similar two embeddings are, with 1 meaning identical direction.",
        "category": "retrieval",
        "source": "retrieval_cosine_similarity.txt",
    },
    {
        "text": "An embedding is a dense vector representation of text that captures semantic meaning. Words or sentences with similar meanings have embeddings that are close together in vector space.",
        "category": "retrieval",
        "source": "retrieval_embedding.txt",
    },
    {
        "text": "HNSW (Hierarchical Navigable Small World) is a graph-based approximate nearest neighbor index that provides fast similarity search with high recall by creating layers of increasingly coarse graphs.",
        "category": "retrieval",
        "source": "retrieval_hnsw.txt",
    },
    {
        "text": "IVF (Inverted File Index) in FAISS partitions vectors into coarse centroids and only searches relevant cells, trading some accuracy for much faster search on large datasets.",
        "category": "retrieval",
        "source": "retrieval_ivf.txt",
    },
    {
        "text": "Semantic search uses embeddings to find conceptually similar content, while keyword search matches exact terms. Semantic search handles synonyms and concepts better, keyword search is better for exact matches.",
        "category": "retrieval",
        "source": "retrieval_semantic_vs_keyword.txt",
    },
    {
        "text": "Query expansion adds related terms or synonyms to a user query to improve retrieval recall. It is useful when users use different terminology than the documents contain.",
        "category": "retrieval",
        "source": "retrieval_query_expansion.txt",
    },
    {
        "text": "Metadata filtering restricts vector search results to documents matching specific criteria (date, category, author). It improves relevance by narrowing the search space before similarity comparison.",
        "category": "retrieval",
        "source": "retrieval_metadata_filtering.txt",
    },
    {
        "text": "A reranker is a second-stage model that re-orders initial retrieval results using more sophisticated scoring. Cross-encoders are common rerankers that improve precision at the cost of latency.",
        "category": "retrieval",
        "source": "retrieval_reranker.txt",
    },
    # RAG
    {
        "text": "Retrieval-Augmented Generation (RAG) is an AI framework that retrieves relevant documents from an external knowledge source to ground large language model responses, reducing hallucinations and improving factual accuracy by providing relevant context to the LLM before generation.",
        "category": "rag",
        "source": "rag_intro.txt",
    },
    {
        "text": "RAG combines information retrieval with text generation by retrieving relevant documents from a knowledge base and using them as context for an LLM to generate grounded answers.",
        "category": "rag",
        "source": "rag_combines.txt",
    },
    {
        "text": "A vector database is a type of database that stores data as high-dimensional vectors (embeddings) and enables similarity search by comparing vector representations using distance metrics like cosine similarity or Euclidean distance. It is commonly used for storing embeddings from machine learning models for semantic search.",
        "category": "rag",
        "source": "rag_vector_database.txt",
    },
    {
        "text": "Chunking splits long documents into smaller segments before embedding. Good chunking preserves context boundaries and ensures chunks are small enough for embedding models while retaining meaning.",
        "category": "rag",
        "source": "rag_chunking.txt",
    },
    {
        "text": "The context window is the maximum number of tokens an LLM can process at once. It limits how much text can be provided as input, affecting how much context can be included in RAG.",
        "category": "rag",
        "source": "rag_context_window.txt",
    },
    {
        "text": "Hallucination is when an LLM generates false or unsupported information presented as fact. RAG helps reduce hallucinations by grounding responses in retrieved context.",
        "category": "rag",
        "source": "rag_hallucination.txt",
    },
    {
        "text": "A citation in RAG systems points to the source document that supports a generated claim. Citations enable users to verify information and reduce trust issues with AI-generated content.",
        "category": "rag",
        "source": "rag_citation.txt",
    },
    # Database
    {
        "text": "A vector database stores high-dimensional embeddings and enables fast similarity search. It is used for semantic search, recommendation systems, and RAG applications.",
        "category": "database",
        "source": "db_vector_database_uses.txt",
    },
    {
        "text": "Embedding dimensionality is the size of the vector representing text. Higher dimensions capture more nuance but require more storage and computation. Common sizes are 384, 768, and 1536.",
        "category": "embeddings",
        "source": "embedding_dimensionality.txt",
    },
    {
        "text": "Embedding models convert text to dense vectors for similarity search, while LLMs generate text. Embeddings are used for retrieval, LLMs for generation in RAG systems.",
        "category": "embeddings",
        "source": "embedding_vs_llm.txt",
    },
]

# ---------------------------------------------------------------------------
# Evaluation queries (expanded from 60 to include diverse types)
# ---------------------------------------------------------------------------

EVAL_QUERIES = [
    # Simple factual (from original dataset)
    {"question": "What is machine learning?", "category": "machine_learning", "difficulty": "easy"},
    {"question": "How does FAISS vector search work?", "category": "retrieval", "difficulty": "medium"},
    {"question": "What is Retrieval-Augmented Generation (RAG)?", "category": "rag", "difficulty": "easy"},
    {"question": "What is BM25 in information retrieval?", "category": "retrieval", "difficulty": "medium"},
    {"question": "What is Reciprocal Rank Fusion (RRF)?", "category": "retrieval", "difficulty": "medium"},
    {"question": "What is a vector database?", "category": "database", "difficulty": "easy"},
    {"question": "What is cosine similarity?", "category": "retrieval", "difficulty": "easy"},
    {"question": "What is sentence-transformers?", "category": "embeddings", "difficulty": "easy"},
    # Multi-hop questions (require combining information)
    {"question": "How does RAG use vector databases to reduce hallucination?", "category": "rag", "difficulty": "hard", "multi_hop": True},
    {"question": "What is the relationship between embeddings and semantic search?", "category": "retrieval", "difficulty": "medium", "multi_hop": True},
    {"question": "How does chunking affect RAG context window usage?", "category": "rag", "difficulty": "medium", "multi_hop": True},
    # Unanswerable questions (no relevant document in corpus)
    {"question": "What is the capital of Australia?", "category": "general", "difficulty": "easy", "unanswerable": True},
    {"question": "Who won the 2024 World Series?", "category": "general", "difficulty": "easy", "unanswerable": True},
    {"question": "What is the stock price of Apple today?", "category": "general", "difficulty": "easy", "unanswerable": True},
    # Ambiguous questions
    {"question": "What is embedding?", "category": "embeddings", "difficulty": "easy", "ambiguous": True},
    {"question": "How does search work?", "category": "retrieval", "difficulty": "easy", "ambiguous": True},
    # Misleading premise questions
    {"question": "Why does BM25 use neural networks for ranking?", "category": "retrieval", "difficulty": "hard", "misleading": True},
    {"question": "How does RAG train neural networks on retrieved documents?", "category": "rag", "difficulty": "hard", "misleading": True},
    # Conflicting source questions
    {"question": "Is cosine similarity the same as Euclidean distance?", "category": "retrieval", "difficulty": "medium", "conflicting": True},
]

# Ground truth answers for answer relevancy computation
GROUND_TRUTHS = {
    "What is machine learning?": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
    "How does FAISS vector search work?": "FAISS is a library for efficient similarity search and clustering of dense vectors using indexing methods like IVF and HNSW.",
    "What is Retrieval-Augmented Generation (RAG)?": "RAG is an AI framework that retrieves relevant documents from an external knowledge source to ground LLM responses.",
    "What is BM25 in information retrieval?": "BM25 is a ranking function that estimates document relevance using term frequency, inverse document frequency, and document length normalization.",
    "What is Reciprocal Rank Fusion (RRF)?": "RRF combines results from multiple retrieval systems using reciprocal rank scores (1/(k+rank)).",
    "What is a vector database?": "A vector database stores high-dimensional vectors and enables similarity search using distance metrics like cosine similarity.",
    "What is cosine similarity?": "Cosine similarity measures the cosine of the angle between two vectors, ranging from -1 to 1.",
    "What is sentence-transformers?": "sentence-transformers is a Python framework for computing sentence and text embeddings.",
    # Multi-hop
    "How does RAG use vector databases to reduce hallucination?": "RAG retrieves relevant documents from a vector database and uses them as context to ground LLM responses, reducing hallucination.",
    "What is the relationship between embeddings and semantic search?": "Embeddings convert text to dense vectors that enable semantic search to find conceptually similar content.",
    "How does chunking affect RAG context window usage?": "Chunking splits documents into segments that fit within the LLM context window while preserving meaning.",
    # Unanswerable
    "What is the capital of Australia?": "This information is not available in the provided documents.",
    "Who won the 2024 World Series?": "This information is not available in the provided documents.",
    "What is the stock price of Apple today?": "This information is not available in the provided documents.",
    # Ambiguous
    "What is embedding?": "An embedding is a dense vector representation of text that captures semantic meaning.",
    "How does search work?": "Search can be keyword-based (BM25, TF-IDF) or semantic (embedding-based vector search).",
    # Misleading premise
    "Why does BM25 use neural networks for ranking?": "BM25 does not use neural networks; it is a probabilistic ranking function based on term frequency and inverse document frequency.",
    "How does RAG train neural networks on retrieved documents?": "RAG does not train neural networks; it retrieves documents and uses them as context for generation.",
    # Conflicting
    "Is cosine similarity the same as Euclidean distance?": "No, cosine similarity measures vector angle while Euclidean distance measures straight-line distance between points.",
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


def _ci95(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        v = float(values[0]) if values else 0.0
        return (v, v)
    n_bootstrap = 2000
    rng = np.random.RandomState(42)
    boot_means = []
    n = len(values)
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))
    boot_means.sort()
    lo = _percentile(boot_means, 2.5)
    hi = _percentile(boot_means, 97.5)
    return (lo, hi)


# ---------------------------------------------------------------------------
# Corpus ingestion
# ---------------------------------------------------------------------------

def ingest_corpus(store: FAISSVectorStore, model: SentenceTransformer) -> int:
    """Ingest documents into the FAISS vector store."""
    texts = [d["text"] for d in DOCUMENTS]
    embeddings = model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32
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
    print(f"Ingested {n} documents into FAISS index", flush=True)
    return n


# ---------------------------------------------------------------------------
# Retrieval methods
# ---------------------------------------------------------------------------

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
                "metadata": r.metadata,
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
        req = RetrievalRequest(
            query_vector=[0.0] * EMBED_DIM,
            top_k=top_k,
            extra={},
        )
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
    def __init__(self, dense: DenseRetriever, bm25: BM25RetrieverWrapper, dense_weight: float = 0.7, bm25_weight: float = 0.3):
        self.dense = dense
        self.bm25 = bm25
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        dense_results = self.dense.search(query, top_k=top_k * 2)
        bm25_results = self.bm25.search(query, top_k=top_k * 2)

        # RRF fusion
        k_rrf = 60
        scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(dense_results, start=1):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k_rrf + rank)
            doc_map[cid] = doc

        for rank, doc in enumerate(bm25_results, start=1):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k_rrf + rank)
            doc_map[cid] = doc

        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[cid] for cid, _ in fused[:top_k]]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_retrieval_method(
    name: str,
    search_fn,
    queries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate a retrieval method using offline RAG metrics on retrieved contexts."""
    per_sample = []
    latencies = []

    for q in queries:
        question = q["question"]
        ground_truth = GROUND_TRUTHS.get(question, "")

        t0 = time.perf_counter()
        results = search_fn(question, top_k=5)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        contexts = [r["chunk_text"] for r in results]

        # Simulated answer: use top context as answer (limitation — no LLM API key)
        simulated_answer = contexts[0] if contexts else ""

        sample = OfflineEvalSample(
            query_id=q.get("query_id", f"eval-{hash(question) % 10000:04d}"),
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

    # Aggregate
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

    # Per-query recall proxy: fraction of queries where ground truth key terms appear in contexts
    r5_values = [ps["metrics"].get("context_recall", 0.0) for ps in per_sample]
    ci_lo, ci_hi = _ci95(r5_values)

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
        "context_recall_ci95": {"lo": ci_lo, "hi": ci_hi},
        "latency_ms": latency_stats,
        "per_sample": per_sample,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("RIP Phase 3 — End-to-End RAG Evaluation")
    print("=" * 70)

    # Build vector store and ingest corpus
    store = FAISSVectorStore(storage_dir=str(BACKEND / "data" / "vector_store"))
    store.create_index(
        index_id="eval_index",
        dimension=EMBED_DIM,
        index_type=IndexType.FLAT,
        distance_metric="cosine",
    )
    model = SentenceTransformer(EMBED_MODEL_NAME)
    n_docs = ingest_corpus(store, model)
    print(f"Corpus size: {n_docs} documents", flush=True)

    # Initialize retrievers
    dense_retriever = DenseRetriever(store, model)
    bm25_retriever = BM25RetrieverWrapper(store)
    hybrid_retriever = HybridRetriever(dense_retriever, bm25_retriever)

    methods = {
        "Dense (MiniLM)": dense_retriever.search,
        "BM25": bm25_retriever.search,
        "Hybrid (RRF)": hybrid_retriever.search,
    }

    # Build evaluation queries with IDs
    queries = []
    for i, q in enumerate(EVAL_QUERIES):
        queries.append({
            "query_id": f"rip-eval-{i+1:03d}",
            **q,
        })

    print(f"Evaluation queries: {len(queries)}", flush=True)
    print(f"  Simple factual: {sum(1 for q in queries if not q.get('multi_hop') and not q.get('unanswerable') and not q.get('ambiguous') and not q.get('misleading') and not q.get('conflicting'))}", flush=True)
    print(f"  Multi-hop: {sum(1 for q in queries if q.get('multi_hop'))}", flush=True)
    print(f"  Unanswerable: {sum(1 for q in queries if q.get('unanswerable'))}", flush=True)
    print(f"  Ambiguous: {sum(1 for q in queries if q.get('ambiguous'))}", flush=True)
    print(f"  Misleading: {sum(1 for q in queries if q.get('misleading'))}", flush=True)
    print(f"  Conflicting: {sum(1 for q in queries if q.get('conflicting'))}", flush=True)

    # Run evaluation for each method
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
            f"| CI95=[{method_result['context_recall_ci95']['lo']:.4f}, {method_result['context_recall_ci95']['hi']:.4f}] "
            f"| p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms",
            flush=True,
        )

    # Write results
    out_path = EXPERIMENT_DIR / "rip_phase3_e2e_rag_eval.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)

    # Print comparison
    print("\n" + "=" * 70)
    print("COMPARISON — End-to-End RAG Evaluation Metrics")
    print("=" * 70)
    print(f"  {'Method':<25s} {'Faithfulness':>12s} {'AnsRel':>10s} {'CtxPrec':>10s} {'CtxRecall':>11s} {'UnsuppRate':>12s} {'p50_ms':>8s}")
    for name, method_result in results["methods"].items():
        m = method_result["metrics"]
        lat = method_result["latency_ms"]
        print(
            f"  {name:<25s} {m.get('faithfulness', 0):>12.4f} {m.get('answer_relevancy', 0):>10.4f} "
            f"{m.get('context_precision', 0):>10.4f} {m.get('context_recall', 0):>11.4f} "
            f"{m.get('unsupported_claim_rate', 0):>12.4f} {lat['p50_ms']:>8.2f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())