"""Settings API router for FastAPI.

Exposes a read-only, non-sensitive view of the active configuration. Runtime settings are
environment-driven (per project conventions), so mutation endpoints are not implemented.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_current_user
from backend.configs.settings import get_settings

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/settings")
async def get_settings_view() -> dict[str, object]:
    """Return a non-sensitive summary of the active configuration."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "generation_provider": settings.generation.provider,
        "generation_model": settings.generation.model_name,
        "embedding_provider": "sentence_transformers",
        "vector_store_provider": settings.vector_store.provider,
        "retrieval_top_k": settings.retrieval.top_k,
        "retrieval_strategy": "dense",
        "docs_enabled": settings.docs_enabled,
    }


@router.put("/settings")
async def update_settings() -> None:
    """Configuration is environment-driven; runtime mutation is not supported."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings are environment-driven and cannot be mutated at runtime.",
    )
