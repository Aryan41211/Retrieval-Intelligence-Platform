"""Factory for creating embedding providers."""

from typing import Any

from backend.data.embeddings.base_embedding_provider import BaseEmbeddingProvider


class EmbeddingProviderType(str):
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    COHERE = "cohere"
    VOYAGE = "voyage"
    JINA = "jina"
    INSTRUCTOR = "instructor"
    E5 = "e5"


class EmbeddingFactory:
    """Factory for creating embedding providers."""

    _providers: dict[str, type[BaseEmbeddingProvider]] = {}

    @classmethod
    def _get_provider_class(cls, provider_type: str) -> type[BaseEmbeddingProvider]:
        if provider_type not in cls._providers:
            if provider_type == EmbeddingProviderType.SENTENCE_TRANSFORMERS:
                try:
                    from backend.data.embeddings.sentence_transformer_provider import (
                        SentenceTransformerProvider,
                    )

                    cls._providers[provider_type] = SentenceTransformerProvider
                except ImportError as e:
                    raise ImportError(
                        f"SentenceTransformerProvider requires sentence-transformers: {e}"
                    ) from e
            else:
                available = ", ".join(cls._providers.keys())
                raise ValueError(f"Unknown provider type: {provider_type}. Available: {available}")
        return cls._providers[provider_type]

    @classmethod
    def create(
        cls,
        provider_type: str = EmbeddingProviderType.SENTENCE_TRANSFORMERS,
        model_name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> BaseEmbeddingProvider:
        provider_class = cls._get_provider_class(provider_type)
        merged_config = {**(config or {})}
        return provider_class(model_name=model_name, config=merged_config)

    @classmethod
    def create_sentence_transformer(
        cls,
        model_name: str = "all-MiniLM-L6-v2",
        config: dict[str, Any] | None = None,
    ) -> BaseEmbeddingProvider:
        return cls.create(
            provider_type=EmbeddingProviderType.SENTENCE_TRANSFORMERS,
            model_name=model_name,
            config=config,
        )

    @classmethod
    def register_provider(
        cls,
        provider_type: str,
        provider_class: type[BaseEmbeddingProvider],
    ) -> None:
        cls._providers[provider_type] = provider_class

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get_default_model(cls, provider_type: str) -> str:
        defaults = {
            EmbeddingProviderType.SENTENCE_TRANSFORMERS: "all-MiniLM-L6-v2",
            EmbeddingProviderType.OPENAI: "text-embedding-3-small",
            EmbeddingProviderType.COHERE: "embed-english-v3.0",
            EmbeddingProviderType.VOYAGE: "voyage-3",
            EmbeddingProviderType.JINA: "jina-embeddings-v3",
            EmbeddingProviderType.INSTRUCTOR: "instructor-xl",
            EmbeddingProviderType.E5: "intfloat/e5-base-v2",
        }
        return defaults.get(provider_type, "all-MiniLM-L6-v2")
