"""
FastAPI application configuration and setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.documents import router as documents_router
from .routers.chat import router as chat_router
from .routers.retrieval import router as retrieval_router
from .routers.evaluation import router as evaluation_router
from .routers.experiments import router as experiments_router
from .routers.settings import router as settings_router
from .config import get_settings


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    
    app = FastAPI(
        title="Retrieval Intelligence Platform API",
        description="End-to-end Retrieval-Augmented Generation (RAG) platform with modular architecture for document processing, intelligent retrieval, and AI-powered question answering.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(retrieval_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        pass
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup application on shutdown."""
        pass
    
    return app


app = create_application()
