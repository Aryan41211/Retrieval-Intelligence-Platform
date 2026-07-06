"""
API dependencies and service injection setup.
"""

from typing import Callable, Any, Optional
from fastapi import Depends, Header, HTTPException

from backend.data.loaders.loader_factory import create_loader, LoaderConfig
from backend.data.preprocessing.text_cleaner import TextPreprocessor
from backend.data.chunking.chunking_factory import create_chunker, ChunkerConfig
from backend.data.embeddings.embedding_factory import create_embedder, EmbedderConfig
from backend.vectorstore.vector_store_factory import create_vector_store, VectorStoreConfig
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_pipeline import RetrievalPipeline
from backend.retrieval.retrieval_request import RetrievalRequest
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.generation.generation_pipeline import GenerationPipeline
from backend.evaluation.evaluation_engine import EvaluationEngine


class APIServices:
    """API service container for dependency injection."""
    
    def __init__(self):
        self._loader_config = LoaderConfig()
        self._chunker_config = ChunkerConfig()
        self._embedding_config = EmbedderConfig()
        self._vector_store_config = VectorStoreConfig()
        self._retrieval_config = None
        self._generation_config = None
        self._evaluation_config = None
    
    def get_ingestion_service(self) -> Callable:
        """Get ingestion service factory."""
        return create_loader(self._loader_config)
    
    def get_preprocessing_service(self) -> TextPreprocessor:
        """Get preprocessing service."""
        return TextPreprocessor()
    
    def get_chunking_service(self) -> Callable:
        """Get chunking service factory."""
        return create_chunker(self._chunker_config)
    
    def get_embedding_service(self) -> Callable:
        """Get embedding service factory."""
        return create_embedder(self._embedding_config)
    
    def get_vector_store_service(self) -> Callable:
        """Get vector store service factory."""
        return create_vector_store(self._vector_store_config)
    
    def get_retrieval_engine(self) -> RetrievalEngine:
        """Get retrieval engine instance."""
        if self._retrieval_config is None:
            # Create retrieval engine with default vector store
            vector_store = self.get_vector_store_service()
            # In real implementation, we would create a proper vector store instance
            # and pass it to RetrievalEngine constructor
            raise HTTPException(status_code=500, detail="Retrieval configuration not initialized")
        # In real implementation, this would create a VectorStore instance
        # and pass it to RetrievalEngine constructor
        raise NotImplementedError("RetrievalEngine initialization requires VectorStore instance")
    
    def get_retrieval_pipeline(self) -> RetrievalPipeline:
        """Get retrieval pipeline instance."""
        if self._retrieval_config is None:
            raise HTTPException(status_code=500, detail="Retrieval configuration not initialized")
        # Create a simple retrieval pipeline with default engine
        # This is a placeholder for real implementation
        raise NotImplementedError("RetrievalPipeline initialization requires RetrievalEngine instance")
    
    def get_generation_pipeline(self) -> GenerationPipeline:
        """Get generation pipeline instance."""
        if self._generation_config is None:
            raise HTTPException(status_code=500, detail="Generation configuration not initialized")
        return GenerationPipeline.from_config()
    
    def get_evaluation_engine(self) -> EvaluationEngine:
        """Get evaluation engine instance."""
        if self._evaluation_config is None:
            raise HTTPException(status_code=500, detail="Evaluation configuration not initialized")
        return EvaluationEngine(self._evaluation_config)


def get_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """API key authentication dependency."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key


def get_rate_limit(request: Any, limit: Callable) -> None:
    """Rate limiting dependency."""
    # In real implementation, this would enforce rate limits
    pass


# Default service instance
services = APIServices()
