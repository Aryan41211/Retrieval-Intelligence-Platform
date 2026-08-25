"""
FastAPI application factory and entry point.

Builds the production-grade ASGI application: configures structured logging,
CORS, security/correlation/rate-limit middleware, health probes and all
versioned routers. Import ``app`` (or run ``python -m backend.api.app``).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.enterprise.database import init_db
from backend.enterprise.routers import (
    admin_router,
    auth_router,
    conversations_router,
    users_router,
    workspaces_router,
)

from .config import get_settings
from .middleware import HealthProbeExemptTrustedHostMiddleware, setup_middleware
from .observability import configure_logging, get_logger
from .routers.chat import router as chat_router
from .routers.documents import router as documents_router
from .routers.evaluation import router as evaluation_router
from .routers.experiments import router as experiments_router
from .routers.health import router as health_router
from .routers.retrieval import router as retrieval_router
from .routers.settings import router as settings_router

logger = get_logger(__name__)


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    """Attach the API version to every response for explicit versioning."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "v1"
        return response


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Validate configuration, initialise the database and warm caches."""
    settings = app.state.api_settings
    settings.validate_for_environment()

    # Provider configuration is validated here too: a stub provider or a missing
    # API key must stop the process at boot rather than surface as fabricated or
    # 401-failing answers once traffic arrives.
    from backend.configs.settings import get_settings as get_app_settings

    get_app_settings().generation.validate_for_environment(settings.environment)

    logger.info(
        "Starting %s in %s environment",
        settings.app_name,
        settings.environment,
    )
    await init_db()

    # Build the expensive singletons before serving traffic. Loading the
    # sentence-transformers model lazily meant the first real request paid a
    # multi-second stall and readiness reported OK before the model existed.
    from starlette.concurrency import run_in_threadpool

    from backend.api.dependencies import warm_up_caches

    await run_in_threadpool(warm_up_caches)
    logger.info("Startup complete: caches warmed")

    yield
    logger.info("Shutting down %s", settings.app_name)
    try:
        from backend.generation.providers.common.http_client import (
            close_provider_clients,
        )

        await close_provider_clients()
    except Exception:  # pragma: no cover - best-effort cleanup
        logger.warning("Failed to close provider HTTP clients during shutdown")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Retrieval Intelligence Platform API",
        description=(
            "End-to-end Retrieval-Augmented Generation (RAG) platform with modular "
            "architecture for document processing, intelligent retrieval, and "
            "AI-powered question answering."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=_lifespan,
    )

    app.state.api_settings = settings
    app.state.correlation_header = settings.correlation_header

    setup_middleware(app)
    app.add_middleware(VersionHeaderMiddleware)

    # CORS is registered LAST so it becomes the outermost layer. Registering it
    # first made it innermost, which meant rate-limit 429s and body-size 413s
    # were returned without CORS headers and surfaced in browsers as opaque
    # network errors instead of the real status.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    prefix = settings.api_prefix

    # Host validation guards against Host-header poisoning; wildcard is rejected
    # in production by APISettings.validate_for_environment. Health probes are
    # exempt: an orchestrator reaches the container by address (127.0.0.1 for the
    # image HEALTHCHECK, the pod IP for a kubelet), which cannot be enumerated in
    # API_TRUSTED_HOSTS, and those endpoints reflect no Host anywhere.
    if settings.trusted_hosts and settings.trusted_hosts != ["*"]:
        app.add_middleware(
            HealthProbeExemptTrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts,
            exempt_paths=(f"{prefix}/health",),
        )

    app.include_router(health_router, prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(chat_router, prefix=prefix)
    app.include_router(retrieval_router, prefix=prefix)
    app.include_router(evaluation_router, prefix=prefix)
    app.include_router(experiments_router, prefix=prefix)
    app.include_router(settings_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(workspaces_router, prefix=prefix)
    app.include_router(conversations_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)

    @app.get("/api/version", tags=["meta"])
    async def api_version():
        """Report the current API version and prefix."""
        return {"version": "1.0.0", "api_prefix": prefix, "api": "v1"}

    return app


app = create_application()
