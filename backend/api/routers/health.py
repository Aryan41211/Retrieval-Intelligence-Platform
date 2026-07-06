"""
Health, readiness, liveness and metrics endpoints.

These endpoints are consumed by container orchestrators and monitoring systems:
- ``/health/live``  : liveness probe (process is up).
- ``/health/ready`` : readiness probe (dependencies are available).
- ``/health``       : aggregate service information.
- ``/metrics``      : Prometheus exposition format (when enabled).
"""

import os
import time
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ..observability import render_metrics

router = APIRouter()

_START_TIME = time.time()


class HealthStatus(BaseModel):
    """Basic liveness/readiness payload."""

    status: Literal["ok", "degraded", "unavailable"]
    service: str
    uptime_seconds: float


class ServiceInfo(BaseModel):
    """Aggregate service information."""

    service: str
    environment: str
    version: str
    uptime_seconds: float


def _uptime() -> float:
    return time.time() - _START_TIME


@router.get("/health/live", response_model=HealthStatus, tags=["health"])
async def liveness() -> HealthStatus:
    """Liveness probe: the process is running and able to serve."""
    settings = router.app.state.api_settings
    return HealthStatus(
        status="ok",
        service=settings.app_name,
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/health/ready", response_model=HealthStatus, tags=["health"])
async def readiness() -> HealthStatus:
    """Readiness probe: required runtime dependencies are available."""
    settings = router.app.state.api_settings
    checks: list[str] = []

    # Configuration validity (fail-fast settings already validated at startup).
    try:
        settings.validate_for_environment()
    except Exception as exc:  # pragma: no cover - defensive
        return HealthStatus(
            status="unavailable",
            service=settings.app_name,
            uptime_seconds=round(_uptime(), 2),
        )

    # Vector store persistence directory must be writable/reachable.
    store_dir = os.environ.get("VECTOR_STORE_PATH", "backend/data/vectorstore")
    parent = os.path.dirname(store_dir) or "."
    checks.append(parent)

    status = "ok"
    for path in checks:
        if path and not os.access(path, os.W_OK | os.R_OK) and not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                status = "unavailable"

    return HealthStatus(
        status="ok" if status == "ok" else "degraded",
        service=settings.app_name,
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/health", response_model=ServiceInfo, tags=["health"])
async def health() -> ServiceInfo:
    """Aggregate service information."""
    settings = router.app.state.api_settings
    return ServiceInfo(
        service=settings.app_name,
        environment=settings.environment,
        version="1.0.0",
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/metrics", tags=["observability"])
async def metrics() -> Response:
    """Prometheus metrics exposition endpoint."""
    settings = router.app.state.api_settings
    if not settings.prometheus_enabled:
        return Response(status_code=404, content="metrics disabled")
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
