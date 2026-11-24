# RIP RAG Evaluation Report

**Project:** Retrieval Intelligence Platform  
**Date:** 2026-11-24  
**Git SHA:** `1cf0ee0`  
**Eval Dataset:** 8 human-validated queries  
**Method:** Offline metrics (no external API keys)

---

## 1. Evaluation Methodology

### Metrics Computed (Local Computation Only)

| Metric | Formula | Range | Interpretation |
|--------|---------|-------|----------------|
| Faithfulness | Fraction of answer sentences supported by context | 0–1 | Higher = more grounded |
| Answer Relevancy | Semantic similarity(question, answer) | 0–1 | Higher = more relevant |
| Context Precision | Fraction of context chunks relevant to question | 0–1 | Higher = less noise |
| Context Recall | Fraction of ground truth covered by contexts | 0–1 | Higher = more complete |
| Citation Precision | Fraction of citations backed by actual context | 0–1 | Higher = more accurate citations |
| Citation Coverage | Fraction of answer sentences with citation | 0–1 | Higher = better sourcing |
| Unsupported Claim Rate | 1 − Faithfulness | 0–1 | Lower = better |

### Evaluation Dataset

| Attribute | Value |
|-----------|-------|
| File | `backend/evaluation/core/eval_dataset.jsonl` |
| Total queries | 8 |
| Label source | human-validated |
| Categories | machine_learning, retrieval, rag, database, mathematics, embeddings |
| Difficulty | 5 easy, 3 medium |

---

## 2. Aggregate Results

| Metric | Value |
|--------|-------|
| **Faithfulness** | 0.8333 |
| **Answer Relevancy** | 0.7932 |
| **Context Precision** | 1.0000 |
| **Context Recall** | 0.8333 |
| **Citation Precision** | 0.0000 |
| **Citation Coverage** | 0.0000 |
| **Unsupported Claim Rate** | 0.1667 |

### Interpretation

- **Faithfulness 0.833**: Most answers are grounded in retrieved context. 2 of 8 samples had partial unsupported content (rag-eval-001, rag-eval-002 at 0.50; rag-eval-007 at 0.67).
- **Answer Relevancy 0.793**: Answers generally address the questions. Lowest score: rag-eval-008 (0.67).
- **Context Precision 1.000**: All retrieved contexts are relevant — retrieval quality is strong.
- **Context Recall 0.833**: Most ground-truth information is present in contexts.
- **Citation metrics 0.000**: No citations in eval dataset — data gap, not system failure.

---

## 3. Per-Sample Results

| Query | Question | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Unsupported Claim Rate |
|-------|----------|-------------|------------------|-------------------|----------------|----------------------|
| rag-eval-001 | What is machine learning? | 0.50 | 0.85 | 1.00 | 0.50 | 0.50 |
| rag-eval-002 | How does FAISS vector search work? | 0.50 | 0.55 | 1.00 | 0.50 | 0.50 |
| rag-eval-003 | What is RAG? | 1.00 | 0.80 | 1.00 | 1.00 | 0.00 |
| rag-eval-004 | What is BM25? | 1.00 | 0.86 | 1.00 | 1.00 | 0.00 |
| rag-eval-005 | What is RRF? | 1.00 | 0.90 | 1.00 | 1.00 | 0.00 |
| rag-eval-006 | What is a vector database? | 1.00 | 0.85 | 1.00 | 1.00 | 0.00 |
| rag-eval-007 | What is cosine similarity? | 0.67 | 0.86 | 1.00 | 0.67 | 0.33 |
| rag-eval-008 | What is sentence-transformers? | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 |

### Samples Needing Attention

- **rag-eval-001**: Faithfulness 0.50 — half the answer sentences not supported by context
- **rag-eval-002**: Answer Relevancy 0.55 — answer may not fully address the question
- **rag-eval-007**: Faithfulness 0.67, Context Recall 0.67 — partial grounding

---

## 4. Ragas Status

Ragas evaluation is **not configured**. The endpoint returns:

```json
{
  "status": "unavailable",
  "reason": "Ragas evaluation is not configured. Set GENERATION_PROVIDER to a real provider (openai/anthropic/ollama/nim) and provide GENERATION_API_KEY."
}
```

No Ragas scores are reported. Offline metrics are used as a substitute.

---

## 5. Recommendations

1. **Add citations to eval dataset**: The 8 eval queries have no citations, making citation metrics impossible to compute. Add citation annotations.
2. **Expand eval dataset**: 8 queries is too small for statistical significance. Target 200–500 queries.
3. **Improve faithfulness**: 2 samples at 0.50 faithfulness indicate answers sometimes go beyond context. Add answer length constraints or grounding enforcement.
4. **Enable Ragas**: Configure `GENERATION_PROVIDER` + `GENERATION_API_KEY` for industry-standard Ragas metrics.
