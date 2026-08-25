"""Unit tests for API middleware.

These cover the middleware layer directly because the API test fixtures run with
rate limiting disabled, so the limiter, the proxy-aware client resolver and the
metrics label helper were previously untested.
"""

import time
from types import SimpleNamespace

import pytest

from backend.api.middleware import (
    RateLimitMiddleware,
    resolve_client_ip,
    resolve_endpoint_label,
)


def _request(
    *,
    client_host: str = "10.0.0.1",
    headers: dict[str, str] | None = None,
    trust_proxy: bool = False,
    proxy_count: int = 1,
    route_path: str | None = None,
    path: str = "/api/v1/chat",
) -> SimpleNamespace:
    """Build a minimal stand-in for a Starlette Request."""
    settings = SimpleNamespace(
        trust_proxy_headers=trust_proxy,
        trusted_proxy_count=proxy_count,
    )
    scope: dict[str, object] = {}
    if route_path is not None:
        scope["route"] = SimpleNamespace(path_format=route_path, path=route_path)
    return SimpleNamespace(
        client=SimpleNamespace(host=client_host) if client_host else None,
        headers={k.lower(): v for k, v in (headers or {}).items()},
        app=SimpleNamespace(state=SimpleNamespace(api_settings=settings)),
        scope=scope,
        url=SimpleNamespace(path=path),
        method="POST",
    )


class TestResolveEndpointLabel:
    """C9: raw paths made Prometheus label cardinality unbounded."""

    def test_uses_route_template_not_raw_path(self) -> None:
        request = _request(route_path="/api/v1/conversations/{conversation_id}")
        assert resolve_endpoint_label(request) == "/api/v1/conversations/{conversation_id}"

    def test_distinct_ids_collapse_to_one_label(self) -> None:
        """Two different path parameter values must share a single label."""
        labels = {
            resolve_endpoint_label(_request(route_path="/api/v1/conversations/{id}"))
            for _ in range(2)
        }
        assert len(labels) == 1

    def test_unmatched_route_gets_a_constant_label(self) -> None:
        assert resolve_endpoint_label(_request(route_path=None)) == "__unmatched__"


class TestResolveClientIp:
    """H5: X-Forwarded-For was honoured implicitly and could be spoofed."""

    def test_ignores_forwarded_header_by_default(self) -> None:
        request = _request(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "1.2.3.4"},
            trust_proxy=False,
        )
        assert resolve_client_ip(request) == "10.0.0.1"

    def test_uses_forwarded_header_when_trusted(self) -> None:
        request = _request(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.7"},
            trust_proxy=True,
            proxy_count=1,
        )
        assert resolve_client_ip(request) == "203.0.113.7"

    def test_spoofed_prefix_cannot_reach_the_trusted_hop(self) -> None:
        """A client-supplied prefix must not become the resolved address."""
        request = _request(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "666.spoof, 203.0.113.7"},
            trust_proxy=True,
            proxy_count=1,
        )
        assert resolve_client_ip(request) == "203.0.113.7"

    def test_short_chain_falls_back_to_direct_peer(self) -> None:
        request = _request(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.7"},
            trust_proxy=True,
            proxy_count=3,
        )
        assert resolve_client_ip(request) == "10.0.0.1"

    def test_missing_client_is_unknown(self) -> None:
        request = _request(client_host="")
        assert resolve_client_ip(request) == "unknown"


class TestRateLimitBuckets:
    """H6: the bucket store never evicted, so memory grew without bound."""

    @pytest.fixture()
    def limiter(self) -> RateLimitMiddleware:
        return RateLimitMiddleware.__new__(RateLimitMiddleware)

    def _configure(
        self,
        limiter: RateLimitMiddleware,
        *,
        per_minute: int = 60,
        burst: int = 5,
        max_tracked: int = 3,
    ) -> RateLimitMiddleware:
        from collections import OrderedDict

        limiter._rate = per_minute / 60.0
        limiter._burst = burst
        limiter._auth_rate = 10 / 60.0
        limiter._auth_burst = 2
        limiter._max_tracked = max_tracked
        limiter._buckets = OrderedDict()
        return limiter

    def test_burst_is_allowed_then_exhausted(self, limiter: RateLimitMiddleware) -> None:
        self._configure(limiter, burst=3)
        key = ("api", "1.1.1.1")
        assert [limiter._allow(key, limiter._rate, 3) for _ in range(3)] == [True] * 3
        assert limiter._allow(key, limiter._rate, 3) is False

    def test_bucket_store_is_bounded(self, limiter: RateLimitMiddleware) -> None:
        self._configure(limiter, max_tracked=3)
        for i in range(50):
            limiter._allow(("api", f"10.0.0.{i}"), limiter._rate, 5)
        assert len(limiter._buckets) <= 3

    def test_eviction_is_least_recently_used(self, limiter: RateLimitMiddleware) -> None:
        self._configure(limiter, max_tracked=2)
        limiter._allow(("api", "a"), limiter._rate, 5)
        limiter._allow(("api", "b"), limiter._rate, 5)
        # Touch "a" so "b" becomes the least recently used entry.
        limiter._allow(("api", "a"), limiter._rate, 5)
        limiter._allow(("api", "c"), limiter._rate, 5)
        assert ("api", "b") not in limiter._buckets
        assert ("api", "a") in limiter._buckets

    def test_tokens_refill_over_time(self, limiter: RateLimitMiddleware) -> None:
        self._configure(limiter, per_minute=600, burst=1)
        key = ("api", "2.2.2.2")
        assert limiter._allow(key, limiter._rate, 1) is True
        assert limiter._allow(key, limiter._rate, 1) is False
        # Rewind the bucket timestamp to simulate elapsed time.
        limiter._buckets[key]["ts"] = time.time() - 5
        assert limiter._allow(key, limiter._rate, 1) is True

    def test_auth_and_api_scopes_are_independent(self, limiter: RateLimitMiddleware) -> None:
        self._configure(limiter, burst=1)
        assert limiter._allow(("api", "3.3.3.3"), limiter._rate, 1) is True
        # The same client still has its separate auth budget.
        assert limiter._allow(("auth", "3.3.3.3"), limiter._auth_rate, 1) is True

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/api/v1/auth/login", True),
            ("/api/v1/auth/register", True),
            ("/api/v1/auth/password-reset/request", True),
            ("/api/v1/chat", False),
            ("/api/v1/health", False),
        ],
    )
    def test_auth_paths_are_detected(self, path: str, expected: bool) -> None:
        assert RateLimitMiddleware._is_auth_path(path) is expected


@pytest.mark.unit
class TestHealthProbeExemptTrustedHost:
    """Host validation must not lock out container/orchestrator health probes.

    Regression cover for a production-only deployment failure: with
    ``API_TRUSTED_HOSTS`` set (which production *requires*), the stock
    ``TrustedHostMiddleware`` answered every probe 400, because the image
    HEALTHCHECK addresses the app as ``127.0.0.1:8000`` and a kubelet uses the
    pod IP. The container therefore never reported healthy.
    """

    @staticmethod
    def _client(trusted_hosts: list[str]):
        """Build a test client for an app with the given trusted hosts."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.middleware import HealthProbeExemptTrustedHostMiddleware

        app = FastAPI()

        @app.get("/api/v1/health/live")
        async def live() -> dict[str, str]:
            return {"status": "ok"}

        @app.get("/api/v1/chat")
        async def chat() -> dict[str, str]:
            return {"status": "ok"}

        app.add_middleware(
            HealthProbeExemptTrustedHostMiddleware,
            allowed_hosts=trusted_hosts,
            exempt_paths=("/api/v1/health",),
        )
        return TestClient(app)

    @pytest.mark.parametrize("host", ["127.0.0.1:8000", "10.42.0.7:8000", "evil.example"])
    def test_probe_paths_ignore_the_host_header(self, host: str) -> None:
        client = self._client(["api.example.com"])
        response = client.get("/api/v1/health/live", headers={"host": host})
        assert response.status_code == 200

    def test_non_probe_paths_still_reject_untrusted_hosts(self) -> None:
        client = self._client(["api.example.com"])
        assert client.get("/api/v1/chat", headers={"host": "evil.example"}).status_code == 400

    def test_non_probe_paths_accept_trusted_hosts(self) -> None:
        client = self._client(["api.example.com"])
        assert client.get("/api/v1/chat", headers={"host": "api.example.com"}).status_code == 200


@pytest.mark.unit
class TestHostRejectionIsDiagnosable:
    """A rejected Host must leave a log line naming the host and the config.

    Starlette answers a bad Host with a bare ``400 Invalid host header`` and logs
    nothing, which made the most common production misconfiguration - listing the
    API's hostname while nginx forwards the browser's - effectively undebuggable.
    """

    def test_rejection_names_the_host_and_the_allowed_list(self, caplog) -> None:
        client = TestHealthProbeExemptTrustedHost._client(["api.example.com"])
        with caplog.at_level("WARNING"):
            client.get("/api/v1/chat", headers={"host": "app.example.com"})
        assert "app.example.com" in caplog.text
        assert "api.example.com" in caplog.text

    def test_repeat_rejections_are_suppressed(self, caplog) -> None:
        client = TestHealthProbeExemptTrustedHost._client(["api.example.com"])
        with caplog.at_level("WARNING"):
            for _ in range(5):
                client.get("/api/v1/chat", headers={"host": "app.example.com"})
        assert caplog.text.count("is not in API_TRUSTED_HOSTS") == 1

    def test_allowed_requests_log_nothing(self, caplog) -> None:
        client = TestHealthProbeExemptTrustedHost._client(["api.example.com"])
        with caplog.at_level("WARNING"):
            client.get("/api/v1/chat", headers={"host": "api.example.com"})
        assert "is not in API_TRUSTED_HOSTS" not in caplog.text
