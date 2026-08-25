"""
Health, readiness, liveness and metrics endpoints.

These endpoints are consumed by container orchestrators and monitoring systems:
- ``/health/live``  : liveness probe (process is up).
- ``/health/ready`` : readiness probe (dependencies are available).
- ``/health``       : aggregate service information.
- ``/metrics``      : Prometheus exposition format (when enabled).
"""

import logging
import os
import secrets
import time
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.configs.settings import get_settings as get_app_settings
from backend.enterprise.security import decode_token

from ..config import get_settings
from ..observability import render_metrics

logger = logging.getLogger(__name__)

router = APIRouter()

_metrics_bearer = HTTPBearer(auto_error=False)

_START_TIME = time.time()


class HealthStatus(BaseModel):
    """Basic liveness/readiness payload."""

    status: Literal["ok", "degraded", "unavailable"]
    service: str
    uptime_seconds: float


class ReadinessStatus(HealthStatus):
    """Readiness payload including per-dependency results."""

    checks: dict[str, str] = {}


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


@router.get("/health/ready", response_model=ReadinessStatus, tags=["health"])
async def readiness(response: Response) -> ReadinessStatus:
    """Readiness probe: required runtime dependencies are available.

    Checks the database and the vector-store directory. The previous version
    only tested a directory and *created* it as a side effect, reporting ready
    while the database was unreachable.
    """
    settings = get_settings()
    app_settings = get_app_settings()
    checks: dict[str, str] = {}

    # --- Database round-trip.
    try:
        from sqlalchemy import text

        from backend.enterprise.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - exercised via failure injection
        logger.warning("Readiness: database check failed: %s", exc)
        checks["database"] = "unavailable"

    # --- Vector store directory must be readable and writable (no creation here).
    store_dir = app_settings.vector_store.storage_dir or "./data/vectorstore"
    if os.path.isdir(store_dir) and os.access(store_dir, os.W_OK | os.R_OK):
        checks["vector_store"] = "ok"
    else:
        checks["vector_store"] = "unavailable"

    is_ready = all(value == "ok" for value in checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        status="ok" if is_ready else "unavailable",
        service=settings.app_name,
        uptime_seconds=round(_uptime(), 2),
        checks=checks,
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


async def _authorize_metrics(
    credentials: HTTPAuthorizationCredentials | None = Depends(_metrics_bearer),
) -> None:
    """Authorize a /metrics scrape.

    The endpoint was previously unauthenticated, publishing the full endpoint
    inventory plus traffic, latency and error counts to anyone who asked.

    Accepts either the dedicated ``API_METRICS_TOKEN`` (for Prometheus, which
    cannot perform a login) or a valid user access token.

    Raises:
        HTTPException: 401 when the caller presents no acceptable credential.
    """
    settings = get_settings()
    if not settings.metrics_require_auth:
        return

    presented = credentials.credentials if credentials else None
    if not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Metrics require authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if settings.metrics_token and secrets.compare_digest(presented, settings.metrics_token):
        return

    try:
        decode_token(presented, "access")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid metrics credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.get("/metrics", tags=["observability"], dependencies=[Depends(_authorize_metrics)])
async def metrics() -> Response:
    """Prometheus metrics exposition endpoint."""
    settings = get_settings()
    if not settings.prometheus_enabled:
        return Response(status_code=404, content="metrics disabled")
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
