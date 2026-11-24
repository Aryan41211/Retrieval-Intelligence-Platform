"""RIP Phase 2 — Offline RAG Evaluation.

Runs offline RAG evaluation (faithfulness, answer relevancy, context precision,
context recall, citation precision/coverage, unsupported claim rate) on the
human-validated eval dataset using only local computation (no API keys).

Results written to experiment_results/rip_phase2_evaluation.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.evaluation.core.offline_evaluator import (
    OfflineEvalSample,
    run_offline_evaluation,
)


BACKEND = Path(__file__).resolve().parent.parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)


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


def main() -> int:
    print("=== RIP Offline RAG Evaluation ===", flush=True)
    samples = load_eval_samples()
    print(f"Loaded {len(samples)} human-validated eval samples", flush=True)

    t0 = time.perf_counter()
    report = run_offline_evaluation(samples)
    total_latency = int((time.perf_counter() - t0) * 1000)

    print(f"Total samples: {report.total_samples}", flush=True)
    print(f"Successful: {report.successful_evaluations}", flush=True)
    print(f"Failed: {report.failed_evaluations}", flush=True)
    print(f"Aggregate metrics:", flush=True)
    for key, val in sorted(report.metrics.items()):
        print(f"  {key}: {val}", flush=True)
    print(f"Evaluation latency: {report.latency_ms}ms", flush=True)
    print(f"Total script latency: {total_latency}ms", flush=True)

    print("\nPer-sample results:", flush=True)
    for r in report.per_sample:
        if r.metrics:
            print(
                f"  {r.query_id}: "
                f"faithfulness={r.metrics.get('faithfulness', 0):.2f} "
                f"answer_relevancy={r.metrics.get('answer_relevancy', 0):.2f} "
                f"context_precision={r.metrics.get('context_precision', 0):.2f} "
                f"context_recall={r.metrics.get('context_recall', 0):.2f} "
                f"citation_precision={r.metrics.get('citation_precision', 0):.2f} "
                f"citation_coverage={r.metrics.get('citation_coverage', 0):.2f} "
                f"unsupported_claim_rate={r.metrics.get('unsupported_claim_rate', 0):.2f}",
                flush=True,
            )
        else:
            print(f"  {r.query_id}: ERROR - {r.error}", flush=True)

    # Write results
    output = {
        "evaluation": {
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

    out_path = EXPERIMENT_DIR / "rip_phase2_evaluation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
