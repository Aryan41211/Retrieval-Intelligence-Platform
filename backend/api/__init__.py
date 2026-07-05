"""
Main FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.documents import router as documents_router
from .routers.chat import router as chat_router
from .routers.retrieval import router as retreval_router
from .routers.evaluation import router as evaluation_router
from .routers.experiments import router as experiments_router
from .routers.settings import router as settings_router

# Create FastAPI app
app = FastAPI(
    title="Retrieval Intelligence Platform API",
    description="End-to-end Retrieval-Augmented Generation (RAG) platform API with modular endpoints for document ingestion, intelligent retrieval, AI-powered chat, evaluation, experiments, and settings.",
    version="1.0.0",
    docs_url="/docs" if True else None,
    redoc_url="/redoc" if True else None,
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(documents_router, prefix="/v1")
app.include_router(chat_router, prefix="/v1")
app.include_router(retreval_router, prefix="/v1")
app.include_router(evaluation_router, prefix="/v1")
app.include_router(experiments_router, prefix="/v1")
app.include_router(settings_router, prefix="/v1")

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application."""
    pass

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application."""
    pass
