"""
HTTP middleware for the FastAPI application.

Implements request correlation, structured request/response logging,
exception logging, baseline security headers, and in-memory rate limiting.
Registered by :func:`backend.api.app.create_application` in the correct order.
"""

import time
from collections import OrderedDict
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from .observability import (
    CORRELATION_ID,
    EXCEPTION_COUNT,
    REQUESTS_IN_PROGRESS,
    get_logger,
    new_correlation_id,
    observe_request,
)

logger = get_logger(__name__)


def resolve_endpoint_label(request: Request) -> str:
    """Return a low-cardinality metrics label for the request's route.

    Uses the matched route *template* (``/api/v1/conversations/{conversation_id}``)
    rather than ``request.url.path``. The raw path mints a new Prometheus label
    set per path parameter value, so every distinct conversation id permanently
    allocated four new time series and grew memory without bound.
    """
    route = request.scope.get("route")
    path_format = getattr(route, "path_format", None) or getattr(route, "path", None)
    if path_format:
        return str(path_format)
    return "__unmatched__"


def resolve_client_ip(request: Request) -> str:
    """Determine the client IP, honouring proxy headers only when configured.

    ``X-Forwarded-For`` is attacker-controlled unless every request traverses a
    proxy that overwrites it. When trusted, the address is read
    ``trusted_proxy_count`` hops from the right, which a spoofed prefix cannot
    influence.
    """
    settings = getattr(request.app.state, "api_settings", None)
    direct = request.client.host if request.client else "unknown"
    if settings is None or not getattr(settings, "trust_proxy_headers", False):
        return direct

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return direct
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not hops:
        return direct
    index = len(hops) - settings.trusted_proxy_count
    if index < 0:
        # Fewer hops than expected: the chain is not what we were told to trust.
        return direct
    return hops[index]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign/propagate a correlation ID and log each request with latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_header = request.app.state.correlation_header
        incoming = request.headers.get(correlation_header)
        correlation_id = incoming or new_correlation_id()
        token = CORRELATION_ID.set(correlation_id)

        request.state.correlation_id = correlation_id
        # In-flight is tracked against the raw method only until the route is
        # matched; the labelled metrics below use the route template.
        start = time.perf_counter()
        in_progress_label = request.method
        REQUESTS_IN_PROGRESS.labels(method=in_progress_label, endpoint="__all__").inc()
        try:
            try:
                response = await call_next(request)
            except Exception:
                duration = time.perf_counter() - start
                endpoint = resolve_endpoint_label(request)
                observe_request(request.method, endpoint, 500, duration)
                EXCEPTION_COUNT.labels(endpoint=endpoint).inc()
                logger.exception(
                    "Unhandled exception during request",
                    extra={"method": request.method, "path": endpoint},
                )
                raise
            finally:
                REQUESTS_IN_PROGRESS.labels(method=in_progress_label, endpoint="__all__").dec()

            duration = time.perf_counter() - start
            endpoint = resolve_endpoint_label(request)
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
            return response
        finally:
            # Reset in finally: previously an exception propagated before the
            # reset, leaking the correlation id into the surrounding context.
            CORRELATION_ID.reset(token)


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


# Paths that gate credentials and therefore get a much stricter budget than
# ordinary API traffic.
_AUTH_PATH_MARKERS = (
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/password-reset",
    "/auth/email/verify",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter keyed by client IP (in-memory, single process).

    Bucket storage is bounded and evicts least-recently-used clients, so a flood
    of distinct (or spoofed) source addresses cannot grow memory without limit.
    Authentication endpoints get their own, stricter bucket.

    For multi-instance deployments exchange this for a shared store (Redis);
    per-process buckets otherwise multiply the effective limit by the replica
    count.
    """

    def __init__(
        self,
        app: FastAPI,
        per_minute: int,
        burst: int,
        auth_per_minute: int = 10,
        max_tracked_clients: int = 10000,
    ) -> None:
        super().__init__(app)
        self._rate = per_minute / 60.0
        self._burst = burst
        self._auth_rate = auth_per_minute / 60.0
        self._auth_burst = max(1, min(burst, auth_per_minute))
        self._max_tracked = max_tracked_clients
        # OrderedDict as a bounded LRU: the previous defaultdict never evicted,
        # so every distinct client IP allocated a bucket forever.
        self._buckets: OrderedDict[tuple[str, str], dict[str, float]] = OrderedDict()

    def _evict_if_needed(self) -> None:
        while len(self._buckets) > self._max_tracked:
            self._buckets.popitem(last=False)

    def _allow(self, key: tuple[str, str], rate: float, burst: int) -> bool:
        now = time.time()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = {"tokens": float(burst), "ts": now}
            self._buckets[key] = bucket
            self._evict_if_needed()
        else:
            self._buckets.move_to_end(key)
        elapsed = now - bucket["ts"]
        bucket["tokens"] = min(float(burst), bucket["tokens"] + elapsed * rate)
        bucket["ts"] = now
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False

    @staticmethod
    def _is_auth_path(path: str) -> bool:
        return any(marker in path for marker in _AUTH_PATH_MARKERS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = resolve_client_ip(request)
        if self._is_auth_path(request.url.path):
            scope, rate, burst = "auth", self._auth_rate, self._auth_burst
        else:
            scope, rate, burst = "api", self._rate, self._burst

        if not self._allow((scope, client), rate, burst):
            logger.warning("Rate limit exceeded for %s on %s scope", client, scope)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds the configured maximum size.

    Note:
        This checks the declared ``Content-Length``. A chunked request without
        that header is not caught here and must be bounded by the reverse proxy
        (e.g. nginx ``client_max_body_size``).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = request.app.state.api_settings
        max_bytes = settings.max_request_size_mb * 1024 * 1024
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Request body exceeds the maximum allowed size of "
                                f"{settings.max_request_size_mb} MB."
                            )
                        },
                    )
            except (ValueError, TypeError):
                pass
        return await call_next(request)


class HealthProbeExemptTrustedHostMiddleware(TrustedHostMiddleware):
    """``TrustedHostMiddleware`` that lets infrastructure probes through.

    Host validation exists to stop Host-header poisoning: an attacker-supplied
    ``Host`` reflected into a cache key or into an absolute URL such as a
    password-reset link. The health and metrics endpoints do neither - they
    return a fixed body and build no URLs - so the check protects nothing on
    those paths while reliably breaking deployment.

    It breaks deployment because infrastructure addresses the app by *address or
    service name*, never by the public hostname. The image's ``HEALTHCHECK``
    sends ``Host: 127.0.0.1:8000``, a Kubernetes kubelet sends the pod IP, and
    the Prometheus scrape sends ``Host: api:8000``. None can be listed in
    ``API_TRUSTED_HOSTS`` up front - the pod IP does not exist until the pod is
    scheduled. Under the stock middleware every probe was answered 400, so a
    production container never became healthy (compose held the frontend at
    ``depends_on: service_healthy`` indefinitely, Kubernetes crash-looped the pod
    against a failing liveness probe) and every metrics scrape failed.

    Access control is not what is being relaxed here: ``/metrics`` keeps its own
    bearer token, and a ``Host`` header is attacker-chosen in any case, so it was
    never a gate.

    Args:
        app: The wrapped ASGI application.
        allowed_hosts: Permitted ``Host`` values, as for the base class.
        www_redirect: Redirect ``www.`` hosts, as for the base class.
        exempt_paths: Path prefixes served without Host validation.
    """

    #: Cap on distinct rejected hosts remembered for log suppression. The Host
    #: header is attacker-controlled, so this set must not grow without bound.
    _MAX_LOGGED_REJECTIONS: int = 64

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: list[str] | None = None,
        www_redirect: bool = True,
        exempt_paths: tuple[str, ...] = (),
    ) -> None:
        super().__init__(app, allowed_hosts=allowed_hosts, www_redirect=www_redirect)
        self.exempt_paths = tuple(exempt_paths)
        self._logged_rejections: set[str] = set()

    def _is_allowed(self, host: str) -> bool:
        """Mirror the base class's host match, for logging only.

        Args:
            host: The ``Host`` header with any port stripped.

        Returns:
            ``True`` when the base middleware would admit this host.
        """
        if self.allow_any:
            return True
        return any(
            host == pattern or (pattern.startswith("*") and host.endswith(pattern[1:]))
            for pattern in self.allowed_hosts
        )

    def _log_rejection(self, host: str) -> None:
        """Warn once per host that a request was rejected on Host validation.

        A rejected request returns a bare ``400 Invalid host header`` with
        nothing written to the log, which is the least diagnosable failure in
        the stack: the usual cause is that ``API_TRUSTED_HOSTS`` lists the API's
        own hostname while the bundled nginx forwards the *browser's* Host, so
        every request 400s while the health probes look fine. Naming the
        rejected host next to the configured list turns that into a one-line
        fix.

        Repeats are suppressed because the header is attacker-controlled and an
        unbounded log line per request is a denial-of-service vector in itself.

        Args:
            host: The rejected ``Host`` header value.
        """
        if host in self._logged_rejections:
            return
        if len(self._logged_rejections) < self._MAX_LOGGED_REJECTIONS:
            self._logged_rejections.add(host)
        logger.warning(
            "Rejected request: Host %r is not in API_TRUSTED_HOSTS %s. "
            "This must list the hostnames browsers use to reach the app - behind the "
            "bundled nginx that is the frontend's hostname, not the API's.",
            host,
            self.allowed_hosts,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bypass Host validation for probe paths; otherwise defer to the base."""
        if scope["type"] == "http" and self.exempt_paths:
            if str(scope.get("path", "")).startswith(self.exempt_paths):
                await self.app(scope, receive, send)
                return
        if scope["type"] in ("http", "websocket") and not self.allow_any:
            host = Headers(scope=scope).get("host", "").split(":")[0]
            if not self._is_allowed(host):
                self._log_rejection(host)
        await super().__call__(scope, receive, send)


def setup_middleware(app: FastAPI) -> None:
    """Register all API middleware.

    ``add_middleware`` *prepends*, so the last registration is the outermost
    layer. Registrations below therefore run inner-to-outer, which is the
    reverse of the previous ordering: rate limiting used to be added first and
    so executed last, after every request had already been logged and measured.

    Effective order, outermost first:
    correlation/logging -> security headers -> rate limit -> body size -> route.
    """
    settings = app.state.api_settings

    # Innermost: reject oversized bodies immediately before the route parses them.
    app.add_middleware(MaxBodySizeMiddleware)

    # Rate limiting sits outside body-size so abusive traffic is shed early.
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            per_minute=settings.rate_limit_per_minute,
            burst=settings.rate_limit_burst,
            auth_per_minute=settings.rate_limit_auth_per_minute,
            max_tracked_clients=settings.rate_limit_max_tracked_clients,
        )

    # Security headers wrap everything the application returns, including 429s.
    app.add_middleware(SecurityHeadersMiddleware)

    # Outermost: every response, including rejections above, is logged once and
    # carries a correlation id.
    app.add_middleware(CorrelationIdMiddleware)
