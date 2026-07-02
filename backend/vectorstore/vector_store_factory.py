"""Factory for creating vector store instances."""

from pathlib import Path
from typing import Any

from backend.vectorstore.base_vector_store import BaseVectorStore
from backend.vectorstore.exceptions import VectorStoreError
from backend.vectorstore.faiss_vector_store import FAISSVectorStore


class VectorStoreFactory:
    """Factory for creating vector store provider instances.

    Provides a centralized way to create vector store instances based on
    provider name. Supports extensibility for future vector database providers.
    """

    _providers: dict[str, type[BaseVectorStore]] = {
        "faiss": FAISSVectorStore,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseVectorStore]) -> None:
        """Register a new vector store provider.

        Args:
            name: Provider name (e.g., 'chromadb', 'pinecone').
            provider_class: Provider class implementing BaseVectorStore.
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(cls, provider: str, storage_dir: str | Path, **kwargs: Any) -> BaseVectorStore:
        """Create a vector store instance.

        Args:
            provider: Provider name ('faiss', 'chromadb', etc.).
            storage_dir: Directory for storing index files.
            **kwargs: Additional provider-specific options.

        Returns:
            Vector store instance.

        Raises:
            VectorStoreError: If provider is not supported.
        """
        provider_name = provider.lower()
        if provider_name not in cls._providers:
            raise VectorStoreError(
                f"Unsupported vector store provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(storage_dir, **kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered vector store providers.

        Returns:
            List of provider names.
        """
        return list(cls._providers.keys())