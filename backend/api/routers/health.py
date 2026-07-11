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

from backend.configs.settings import get_settings as get_app_settings

from ..config import get_settings
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
    settings = get_settings()
    return HealthStatus(
        status="ok",
        service=settings.app_name,
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/health/ready", response_model=HealthStatus, tags=["health"])
async def readiness() -> HealthStatus:
    """Readiness probe: required runtime dependencies are available."""
    settings = get_settings()
    app_settings = get_app_settings()
    vector_store_dir = app_settings.vector_store.storage_dir or "./data/vectorstore"

    # Vector store persistence directory must be reachable/writable.
    store_dir = vector_store_dir
    parent = os.path.dirname(store_dir) or "."
    is_ready = True
    if parent and not (os.path.isdir(parent) and os.access(parent, os.W_OK | os.R_OK)):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError:
            is_ready = False

    return HealthStatus(
        status="ok" if is_ready else "unavailable",
        service=settings.app_name,
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/health", response_model=ServiceInfo, tags=["health"])
async def health() -> ServiceInfo:
    """Aggregate service information."""
    settings = get_settings()
    return ServiceInfo(
        service=settings.app_name,
        environment=settings.environment,
        version="1.0.0",
        uptime_seconds=round(_uptime(), 2),
    )


@router.get("/metrics", tags=["observability"])
async def metrics() -> Response:
    """Prometheus metrics exposition endpoint."""
    settings = get_settings()
    if not settings.prometheus_enabled:
        return Response(status_code=404, content="metrics disabled")
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
