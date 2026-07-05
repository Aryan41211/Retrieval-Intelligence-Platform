"""
FastAPI application configuration and setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers.documents import router as documents_router
from .api.routers.chat import router as chat_router
from .api.routers.retrieval import router as retreval_router
from .api.routers.evaluation import router as evaluation_router
from .api.routers.experiments import router as experiments_router
from .api.routers.settings import router as settings_router
from .dependencies import get_ingestion_service, get_retrieval_service, get_generation_service
from .exceptions import setup_exception_handlers
from .middleware import setup_middleware
from .config import get_settings


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    
    # Initialize FastAPI app with metadata
    app = FastAPI(
        title="Retrieval Intelligence Platform API",
        description="End-to-end Retrieval-Augmented Generation (RAG) platform with modular architecture for document processing, intelligent retrieval, and AI-powered question answering.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Setup exception handling
    setup_exception_handlers(app)
    
    # Include all routers
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(retreval_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=settings.api.cors_credentials,
        allow_methods=settings.api.cors_methods,
        allow_headers=settings.api.cors_headers,
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


# Create the application instance
app = create_application()
