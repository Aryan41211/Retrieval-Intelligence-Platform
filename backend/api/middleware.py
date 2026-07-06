"""
HTTP middleware for the FastAPI application.

Implements request correlation, structured request/response logging,
exception logging, baseline security headers, and in-memory rate limiting.
Registered by :func:`backend.api.app.create_application` in the correct order.
"""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .observability import (
    CORRELATION_ID,
    EXCEPTION_COUNT,
    REQUESTS_IN_PROGRESS,
    get_logger,
    new_correlation_id,
    observe_request,
)

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign/propagate a correlation ID and log each request with latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_header = request.app.state.correlation_header
        incoming = request.headers.get(correlation_header)
        correlation_id = incoming or new_correlation_id()
        token = CORRELATION_ID.set(correlation_id)

        request.state.correlation_id = correlation_id
        endpoint = request.url.path
        REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            observe_request(request.method, endpoint, 500, duration)
            EXCEPTION_COUNT.labels(endpoint=endpoint).inc()
            logger.exception(
                "Unhandled exception during request",
                extra={"method": request.method, "path": endpoint},
            )
            raise
        finally:
            REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).dec()

        duration = time.perf_counter() - start
        status = response.status_code
        observe_request(request.method, endpoint, status, duration)
        response.headers[correlation_header] = correlation_id
        response.headers["X-Process-Time"] = f"{duration * 1000:.1f}ms"
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": endpoint,
                "status": status,
                "duration_ms": round(duration * 1000, 1),
            },
        )
        CORRELATION_ID.reset(token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        settings = request.app.state.api_settings
        if not settings.security_headers_enabled:
            return response

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault("Content-Security-Policy", settings.csp_policy)
        if settings.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter keyed by client IP (in-memory, single process).

    For multi-instance deployments exchange this for a shared store (Redis).
    """

    def __init__(self, app: FastAPI, per_minute: int, burst: int) -> None:
        super().__init__(app)
        self._rate = per_minute / 60.0
        self._burst = burst
        self._buckets: dict[str, dict[str, float]] = defaultdict(
            lambda: {"tokens": float(burst), "ts": time.time()}
        )

    def _allow(self, key: str) -> bool:
        bucket = self._buckets[key]
        now = time.time()
        elapsed = now - bucket["ts"]
        bucket["tokens"] = min(self._burst, bucket["tokens"] + elapsed * self._rate)
        bucket["ts"] = now
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = request.client.host if request.client else "unknown"
        if not self._allow(client):
            logger.warning("Rate limit exceeded for %s", client)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    """Register all API middleware in the correct (outer-to-inner) order."""
    settings = app.state.api_settings
    # Outermost: rate limiting rejects abusive traffic early.
    app.add_middleware(
        RateLimitMiddleware,
        per_minute=settings.rate_limit_per_minute,
        burst=settings.rate_limit_burst,
    )
    # Security headers wrap application responses.
    app.add_middleware(SecurityHeadersMiddleware)
    # Innermost: correlation ID and request logging around the route handler.
    app.add_middleware(CorrelationIdMiddleware)
