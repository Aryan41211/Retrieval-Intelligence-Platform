"""
API dependencies and service injection setup.

This module exposes dependency-injection helpers used by routers. It is kept
import-safe: heavy provider wiring is performed lazily inside the helpers so a
missing/incomplete service cannot prevent the application from booting. Routers
that depend on services not yet wired in a given build receive a clear 501.
"""

from typing import Any, Optional

from fastapi import Header, HTTPException

from backend.generation.generation_pipeline import GenerationPipeline


class APIServices:
    """API service container for dependency injection."""

    def get_generation_pipeline(self) -> GenerationPipeline:
        """Return a configured generation pipeline instance."""
        return GenerationPipeline.from_config()

    def get_retrieval_pipeline(self) -> Any:
        """Retrieve the retrieval pipeline (not wired in this build)."""
        raise HTTPException(
            status_code=501, detail="Retrieval pipeline is not wired in this build"
        )

    def get_evaluation_engine(self) -> Any:
        """Retrieve the evaluation engine (not wired in this build)."""
        raise HTTPException(
            status_code=501, detail="Evaluation engine is not available in this build"
        )


def get_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """API key authentication dependency.

    Reject requests that do not present an ``X-API-Key`` header. Endpoints opt
    in by declaring this dependency.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key


def get_rate_limit(request: Any) -> None:
    """Rate limiting dependency placeholder.

    Active rate limiting is enforced by :class:`RateLimitMiddleware`; this hook
    remains for per-route overrides if needed.
    """
    return None


def get_generation_pipeline() -> GenerationPipeline:
    """FastAPI dependency returning a configured generation pipeline."""
    return services.get_generation_pipeline()


# Default service instance.
services = APIServices()
