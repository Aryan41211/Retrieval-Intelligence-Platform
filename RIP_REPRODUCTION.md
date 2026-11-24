# RIP Phase 2 — Reproduction Guide

**Project:** Retrieval Intelligence Platform  
**Git SHA:** `1cf0ee0`  
**Branch:** `main`  
**Date:** 2026-11-24  
**Environment:** 16 CPU cores, 15.65 GB RAM, CPU-only

---

## 1. Environment Setup

```bash
cd "C:\projects\Retrieval Intelligence Platform\backend"

# Verify Python version
python --version  # 3.12

# Install dependencies
pip install -r requirements.txt

# Key dependencies:
# - FastAPI, Pydantic v2
# - SQLAlchemy 2.0 async
# - sentence-transformers
# - faiss-cpu
# - rank-bm25
# - pytest, httpx
```

---

## 2. Backend Tests

```bash
cd "C:\projects\Retrieval Intelligence Platform\backend"

# Run all tests
python -m pytest tests -q -p no:cacheprovider

# Expected: 547 passed, 4 failed (pre-existing integration test failures)
# The 4 failures require a running database and are unrelated to Phase 2
```

---

## 3. Server Startup

```bash
cd "C:\projects\Retrieval Intelligence Platform\backend"

# Bootstrap deployment (generates .env with JWT secret key)
python scripts/bootstrap_deployment.py

# Start server
uvicorn backend.api:app --reload

# Server runs at http://127.0.0.1:8000
# API docs at http://127.0.0.1:8000/docs
```

**Required environment variables:**
- `ENTERPRISE_JWT_SECRET_KEY` (≥32 characters, required for import)
- `API_RATE_LIMIT_ENABLED=true` (production default)
- `GENERATION_PROVIDER=fake` (default, Ragas unavailable)

---

## 4. Offline RAG Evaluation

```bash
cd "C:\projects\Retrieval Intelligence Platform\scripts"

python rip_phase2_evaluation.py

# Output: experiment_results/rip_phase2_evaluation.json
# Evaluates 8 human-validated queries using offline metrics:
# - faithfulness, answer_relevancy, context_precision, context_recall
# - citation_precision, citation_coverage, unsupported_claim_rate
# Runtime: ~10 seconds
```

### Expected Results

| Metric | Value |
|--------|-------|
| Faithfulness | 0.8333 |
| Answer Relevancy | 0.7932 |
| Context Precision | 1.0000 |
| Context Recall | 0.8333 |
| Citation Precision | 0.0000 |
| Citation Coverage | 0.0000 |
| Unsupported Claim Rate | 0.1667 |

---

## 5. Load Testing

```bash
cd "C:\projects\Retrieval Intelligence Platform\scripts"

# Server must be running on port 8000 first
python rip_load_test.py

# Output: experiment_results/rip_load_test.json
# Tests concurrency C=1/5/10/25/50/100 with rate limiting ENABLED
# Runtime: ~2-3 minutes
```

### Expected Results (Rate Limiting ON)

| Concurrency | Error Rate | p95 ms | Meets Criteria |
|-------------|------------|--------|----------------|
| C=1 | 0.0% | 270.1 | ✅ Yes |
| C=5 | 4.0% | 6457.8 | ❌ No |
| C≥10 | >68% | >353ms | ❌ No |

**Only C=1 meets err<1% & p95<500ms with rate limiting enabled.**

---

## 6. Ragas Evaluation (Requires API Key)

Ragas evaluation is intentionally not configured. To enable:

```bash
# Set environment variables
export GENERATION_PROVIDER=openai
export GENERATION_API_KEY=sk-...

# Restart server
uvicorn backend.api:app --reload

# Check evaluation status
curl http://127.0.0.1:8000/api/v1/evaluation
# Should return: {"status": "available", "provider": "openai"}

# Run evaluation
curl -X POST http://127.0.0.1:8000/api/v1/evaluation/run \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"question": "...", "ground_truth": "...", "answer": "...", "contexts": ["..."]}]'
```

**No API key = no Ragas scores.** The system honestly reports "unavailable" rather than fabricating metrics.

---

## 7. Rate Limiting (Isolated Capacity Test)

To test raw server capacity without rate limiting:

```bash
# Temporarily disable rate limiting (isolated test only)
export API_RATE_LIMIT_ENABLED=false

# Restart server
uvicorn backend.api:app --reload

# Run load test again
python rip_load_test.py

# Re-enable for production
export API_RATE_LIMIT_ENABLED=true
```

**Warning:** This is an isolated capacity test. Rate limiting must be ENABLED in production.

---

## 8. Key Files

| File | Purpose |
|------|---------|
| `backend/evaluation/core/offline_evaluator.py` | Offline RAG metrics |
| `backend/evaluation/core/evaluator.py` | Ragas evaluator |
| `backend/evaluation/core/eval_dataset.jsonl` | 8 human-validated eval queries |
| `backend/api/routers/evaluation.py` | Evaluation API router |
| `backend/api/routers/chat.py` | Chat/RAG API (SSE streaming) |
| `backend/api/config.py` | Settings (rate limiting, providers) |
| `backend/api/middleware.py` | Rate limiter middleware |
| `scripts/rip_phase2_evaluation.py` | Offline evaluation runner |
| `scripts/rip_load_test.py` | Load and concurrency test |
| `experiment_results/rip_phase2_evaluation.json` | Raw evaluation results |
| `experiment_results/rip_load_test.json` | Raw load test results |
| `experiment_results/baseline_snapshot.json` | Baseline snapshot |

---

## 9. Git Status

- All changes committed to `main` (SHA: `1cf0ee0`)
- `backend/evaluation/core/eval_dataset.jsonl` — untracked (needs `git add`)
- No branches created or switched
- No commits pushed (pending approval)
