"""
Observability primitives: structured logging, correlation IDs and metrics.

Provides a single place to configure JSON or text logging, thread/async-safe
correlation IDs that are attached to every log record, and Prometheus metrics
for request volume, latency and in-flight requests.
"""

import logging
import sys
import uuid
from contextvars import ContextVar

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

try:  # pydantic-settings is always present; keep import local to limit coupling.
    from .config import APISettings, get_settings
except ImportError:  # pragma: no cover - allows standalone import in tests
    APISettings = None  # type: ignore
    get_settings = None  # type: ignore


# ---------------------------------------------------------------------------
# Correlation IDs
# ---------------------------------------------------------------------------
CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    """Generate a fresh correlation ID."""
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    """Return the active correlation ID (if any)."""
    return CORRELATION_ID.get()


def set_correlation_id(value: str | None) -> None:
    """Set the active correlation ID for the current context."""
    CORRELATION_ID.set(value)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class CorrelationFilter(logging.Filter):
    """Attach the active correlation ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = CORRELATION_ID.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON suitable for log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload.setdefault(key, value)
        return json.dumps(payload, default=str)


_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


def configure_logging(api_settings: APISettings | None = None) -> None:
    """Configure the root logger based on settings.

    Args:
        api_settings: Resolved API settings. Defaults to :func:`get_settings`.
    """
    if api_settings is None and get_settings is not None:
        api_settings = get_settings()

    level = (api_settings.log_level if api_settings else "INFO").upper()
    use_json = (api_settings.log_format == "json") if api_settings else True
    log_file = api_settings.log_file if api_settings else None

    handler: logging.Handler
    if log_file:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.addFilter(CorrelationFilter())
    if use_json:
        handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z"))
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s"
            )
        )

    root = logging.getLogger()
    root.setLevel(level)
    # Replace handlers to avoid duplicate logs when called more than once.
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with correlation-ID support already configured."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "rip_http_requests_total",
    "Total HTTP requests.",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "rip_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
)
REQUESTS_IN_PROGRESS = Counter(
    "rip_http_requests_in_progress",
    "In-flight HTTP requests.",
    ["method", "endpoint"],
)
EXCEPTION_COUNT = Counter(
    "rip_http_exceptions_total",
    "Unhandled exceptions surfaced by the API.",
    ["endpoint"],
)


def observe_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record metrics for a completed request."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_exception(endpoint: str) -> None:
    """Record an unhandled exception for an endpoint."""
    EXCEPTION_COUNT.labels(endpoint=endpoint).inc()


def render_metrics() -> tuple[bytes, str]:
    """Return the Prometheus exposition payload and content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
