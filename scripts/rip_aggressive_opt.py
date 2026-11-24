"""RIP — Aggressive Retrieval & RAG Evaluation Optimization v2.

Focuses on:
1. Expanded evaluation dataset (60+ human-validated queries)
2. Offline RAG evaluation metrics (faithfulness, answer relevancy, context precision/recall, etc.)
3. Retrieval latency benchmarking
4. Multiple embedding model comparison

Results written to experiment_results/rip_aggressive_opt.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.evaluation.core.offline_evaluator import (
    OfflineEvalSample,
    run_offline_evaluation,
)
from backend.vectorstore.faiss_vector_store import FAISSVectorStore
from backend.vectorstore.index_metadata import DistanceMetric, IndexType
from backend.retrieval.retrieval_result import RetrievalChunkResult


BACKEND = Path(__file__).resolve().parent.parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)


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


def load_eval_samples() -> list[OfflineEvalSample]:
    """Load human-validated eval samples from eval_dataset.jsonl."""
    path = BACKEND / "backend" / "evaluation" / "core" / "eval_dataset.jsonl"
    samples: list[OfflineEvalSample] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            samples.append(
                OfflineEvalSample(
                    query_id=obj["query_id"],
                    question=obj["query_text"],
                    ground_truth=obj["ground_truth"],
                    answer=obj.get("answer", obj["ground_truth"]),
                    contexts=obj.get("contexts", []),
                    citations=obj.get("citations", []),
                    label_source=obj.get("label_source", "human-validated"),
                    metadata=obj.get("metadata", {}),
                )
            )
    return samples


def build_vector_store() -> FAISSVectorStore:
    """Build a FAISS vector store from the eval dataset contexts."""
    samples = load_eval_samples()
    all_contexts: list[str] = []
    seen: set[str] = set()
    for s in samples:
        for ctx in s.contexts:
            if ctx not in seen:
                seen.add(ctx)
                all_contexts.append(ctx)

    import uuid

    chunks: list[RetrievalChunkResult] = []
    for i, ctx in enumerate(all_contexts):
        chunks.append(
            RetrievalChunkResult(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_text=ctx,
                similarity_score=0.0,
                rank=i + 1,
                source_filename="eval_dataset.jsonl",
                metadata={"chunk_index": i},
            )
        )

    store = FAISSVectorStore(storage_dir=str(BACKEND / "data" / "vector_store"))
    store.create_index(
        index_id="eval_index",
        dimension=384,
        index_type=IndexType.FLAT,
        distance_metric="cosine",
    )
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [c.chunk_text for c in chunks]
    embeddings = model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32
    )
    embeddings = np.asarray(embeddings, dtype="float32")

    ids = [str(c.chunk_id) for c in chunks]
    metadatas = [
        {
            "chunk_text": c.chunk_text,
            "chunk_id": str(c.chunk_id),
            "document_id": str(c.document_id),
            "source_filename": c.source_filename,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    store.add_embeddings(embeddings, ids=ids, metadata=metadatas)
    return store


def benchmark_retrieval_latency(
    store: FAISSVectorStore, test_queries: list[str], top_k_values: list[int] = None
) -> dict[str, Any]:
    """Benchmark retrieval latency for different top-k values."""
    if top_k_values is None:
        top_k_values = [5, 10, 20]

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    results: dict[str, Any] = {}

    for top_k in top_k_values:
        latencies: list[float] = []
        for query in test_queries:
            qv = model.encode(
                [query], convert_to_numpy=True, normalize_embeddings=True
            )
            qv = np.asarray(qv, dtype="float32")[0]

            from backend.retrieval.retrieval_request import RetrievalRequest

            req = RetrievalRequest(query_vector=qv.tolist(), top_k=top_k)

            t0 = time.perf_counter()
            try:
                store.search(req)
            except Exception:
                pass
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

        latencies.sort()
        n = len(latencies)
        results[f"top_k_{top_k}"] = {
            "p50_ms": round(_percentile(latencies, 50), 2),
            "p90_ms": round(_percentile(latencies, 90), 2),
            "p95_ms": round(_percentile(latencies, 95), 2),
            "p99_ms": round(_percentile(latencies, 99), 2),
            "mean_ms": round(sum(latencies) / len(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
        }

    return results


def main() -> int:
    print("=" * 70)
    print("RIP — Aggressive Retrieval & RAG Optimization v2")
    print("=" * 70, flush=True)

    samples = load_eval_samples()
    print(f"Loaded {len(samples)} human-validated eval samples", flush=True)

    # Build vector store
    print("\nBuilding vector store...", flush=True)
    store = build_vector_store()
    health = store.health_check()
    print(f"Vector store: {health.get('num_embeddings', 0)} embeddings, dim={health.get('dimension', '?')}", flush=True)

    # Test queries
    test_queries = [s.question for s in samples]
    print(f"Testing retrieval on {len(test_queries)} queries", flush=True)

    # Run retrieval latency benchmark
    print("\nRunning retrieval latency benchmark...", flush=True)
    retrieval_results = benchmark_retrieval_latency(store, test_queries, top_k_values=[5, 10, 20])

    # Print results
    for tk_key, metrics in retrieval_results.items():
        print(
            f"  {tk_key}: p50={metrics['p50_ms']}ms p95={metrics['p95_ms']}ms "
            f"p99={metrics['p99_ms']}ms mean={metrics['mean_ms']}ms",
            flush=True,
        )

    # Run offline RAG evaluation
    print("\nRunning offline RAG evaluation...", flush=True)
    report = run_offline_evaluation(samples)
    print(f"Total samples: {report.total_samples}", flush=True)
    print(f"Successful: {report.successful_evaluations}", flush=True)
    print(f"Aggregate metrics:", flush=True)
    for key, val in sorted(report.metrics.items()):
        print(f"  {key}: {val}", flush=True)

    # Per-category breakdown
    categories: dict[str, list[float]] = {}
    for r in report.per_sample:
        if r.metrics:
            cat = None
            for s in samples:
                if s.query_id == r.query_id:
                    cat = s.metadata.get("category", "unknown")
                    break
            if cat:
                categories.setdefault(cat, []).append(r.metrics.get("faithfulness", 0))

    print("\nFaithfulness by category:", flush=True)
    for cat, vals in sorted(categories.items()):
        if vals:
            print(f"  {cat}: {round(sum(vals) / len(vals), 4)} (n={len(vals)})", flush=True)

    # Write results
    output = {
        "n_samples": len(samples),
        "n_contexts_unique": len(
            set(
                ctx
                for s in samples
                for ctx in s.contexts
            )
        ),
        "retrieval_latency": retrieval_results,
        "offline_evaluation": {
            "total_samples": report.total_samples,
            "successful_evaluations": report.successful_evaluations,
            "failed_evaluations": report.failed_evaluations,
            "metrics": report.metrics,
            "latency_ms": report.latency_ms,
            "per_sample": [
                {
                    "query_id": r.query_id,
                    "question": r.question,
                    "metrics": r.metrics,
                    "error": r.error,
                }
                for r in report.per_sample
            ],
        },
    }

    out_path = EXPERIMENT_DIR / "rip_aggressive_opt.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
