"""Summarize RIP Phase 3 end-to-end RAG evaluation results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS_PATH = Path(__file__).resolve().parent.parent / "experiment_results" / "rip_phase3_e2e_rag_eval.json"


def main() -> int:
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        r = json.load(f)

    print(f"N documents: {r.get('n_documents')}")
    print(f"N queries: {r.get('n_queries')}")
    print(f"Embedding model: {r.get('embedding_model')}")
    print()

    for name, method in r.get("methods", {}).items():
        m = method.get("metrics", {})
        lat = method.get("latency_ms", {})
        print(
            f"{name}: "
            f"Faithfulness={m.get('faithfulness', 0):.4f} "
            f"AnsRel={m.get('answer_relevancy', 0):.4f} "
            f"CtxPrec={m.get('context_precision', 0):.4f} "
            f"CtxRecall={m.get('context_recall', 0):.4f} "
            f"UnsuppRate={m.get('unsupported_claim_rate', 0):.4f} "
            f"p50={lat.get('p50_ms', 0)}ms "
            f"p95={lat.get('p95_ms', 0)}ms"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())