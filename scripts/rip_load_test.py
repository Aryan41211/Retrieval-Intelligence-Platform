"""RIP Phase 2 — Load and Concurrency Testing.

Tests the Retrieval Intelligence Platform server at multiple concurrency levels:
1, 5, 10, 25, 50, 100 concurrent users.

Endpoints tested:
- Health (no auth)
- Auth login (no auth)
- Chat / RAG (JWT auth required)

Tests run with rate limiting ENABLED (production config).

Results written to experiment_results/rip_load_test.json
"""

from __future__ import annotations

import concurrent.futures
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path(__file__).resolve().parent.parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8000"

# Test credentials
TEST_EMAIL = "loadtest@test.com"
TEST_PASSWORD = "loadtestpass123"


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


def register_user() -> str | None:
    """Register a test user. Returns token on success, None on failure."""
    data = json.dumps({
        "email": TEST_EMAIL,
        "username": "loadtestuser",
        "password": TEST_PASSWORD,
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/register",
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return body.get("access_token")
    except urllib.error.HTTPError as e:
        # User may already exist - try login instead
        return login_user()
    except Exception:
        return None


def login_user() -> str | None:
    """Login and return JWT token."""
    data = json.dumps({
        "identifier": "loadtestuser",
        "password": TEST_PASSWORD,
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return body.get("access_token")
    except Exception:
        return None


def make_request(method: str, path: str, token: str | None = None,
                 body: dict | None = None, timeout: int = 30) -> dict[str, Any]:
    """Make a single HTTP request and return result dict."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "status": resp.status,
                "latency_ms": latency_ms,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "status": e.code,
            "latency_ms": latency_ms,
            "error": e.read().decode()[:100] if e.fp else None,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "status": 0,
            "latency_ms": latency_ms,
            "error": str(e)[:100],
        }


def run_concurrency_test(concurrency: int, requests_per_user: int = 10,
                         token: str | None = None) -> dict[str, Any]:
    """Run load test at given concurrency level."""
    results: list[dict[str, Any]] = []

    def worker() -> list[dict[str, Any]]:
        worker_results = []
        for _ in range(requests_per_user):
            # Mix of endpoints: 50% health, 30% chat, 20% auth
            import random
            r = random.random()
            if r < 0.5:
                worker_results.append(make_request("GET", "/api/v1/health/ready"))
            elif r < 0.8:
                worker_results.append(make_request("POST", "/api/v1/chat",
                    token=token,
                    body={"query": "What is machine learning?", "conversation_id": None}))
            else:
                worker_results.append(make_request("POST", "/api/v1/auth/login",
                    body={"identifier": "loadtestuser", "password": TEST_PASSWORD}))
        return worker_results

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for future in concurrent.futures.as_completed(futures):
            results.extend(future.result())
    total_time = time.perf_counter() - t0

    # Aggregate
    total_requests = len(results)
    successful = sum(1 for r in results if r["status"] == 200)
    errors = total_requests - successful
    error_rate = errors / total_requests if total_requests > 0 else 0

    status_counts: dict[str, int] = {}
    for r in results:
        s = str(r["status"])
        status_counts[s] = status_counts.get(s, 0) + 1

    latencies = sorted([r["latency_ms"] for r in results])
    rps = total_requests / total_time if total_time > 0 else 0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successful": successful,
        "errors": errors,
        "error_rate": round(error_rate, 4),
        "rps": round(rps, 2),
        "total_time_sec": round(total_time, 2),
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p90_ms": round(_percentile(latencies, 90), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "status_counts": status_counts,
    }


def main() -> int:
    # Register/login to get a token
    print("Authenticating...", flush=True)
    token = register_user()
    if token:
        print(f"  Token obtained: {token[:20]}...", flush=True)
    else:
        print("  WARNING: No token - chat tests will fail with 401", flush=True)

    concurrency_levels = [1, 5, 10, 25, 50, 100]
    all_results: list[dict[str, Any]] = []

    for c in concurrency_levels:
        print(f"\nTesting concurrency C={c} ...", flush=True)
        result = run_concurrency_test(c, requests_per_user=5, token=token)
        all_results.append(result)
        print(f"  Requests: {result['total_requests']}, "
              f"Successful: {result['successful']}, "
              f"Errors: {result['errors']} ({result['error_rate']*100:.1f}%)", flush=True)
        print(f"  RPS: {result['rps']}, p50: {result['p50_ms']}ms, "
              f"p95: {result['p95_ms']}ms, p99: {result['p99_ms']}ms", flush=True)
        print(f"  Status counts: {result['status_counts']}", flush=True)

    # Summary: highest concurrency meeting err<1% and p95<500ms
    best_c = None
    for r in all_results:
        if r["error_rate"] < 0.01 and r["p95_ms"] < 500:
            if best_c is None or r["concurrency"] > best_c:
                best_c = r["concurrency"]

    output = {
        "server_url": BASE_URL,
        "rate_limiting": "enabled",
        "concurrency_results": all_results,
        "highest_concurrency_err_lt_1_p95_lt_500ms": best_c,
        "test_timestamp": time.time(),
    }

    out_path = EXPERIMENT_DIR / "rip_load_test.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    if best_c:
        print(f"Highest concurrency meeting err<1% & p95<500ms: C={best_c}", flush=True)
    else:
        print("No concurrency level meets err<1% & p95<500ms", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
