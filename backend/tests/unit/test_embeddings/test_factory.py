"""Tests for embedding factory."""

import pytest

from backend.data.embeddings.embedding_factory import (
    EmbeddingFactory,
    EmbeddingProviderType,
)
from backend.data.embeddings.sentence_transformer_provider import SentenceTransformerProvider


class TestEmbeddingFactory:
    """Tests for EmbeddingFactory class."""

    def test_create_sentence_transformer_provider(self):
        provider = EmbeddingFactory.create_sentence_transformer(
            model_name="all-MiniLM-L6-v2"
        )
        assert isinstance(provider, SentenceTransformerProvider)
        assert provider.name == "all-MiniLM-L6-v2"

    def test_create_with_config(self):
        config = {"device": "cpu", "batch_size": 64}
        provider = EmbeddingFactory.create(
            provider_type=EmbeddingProviderType.SENTENCE_TRANSFORMERS,
            model_name="all-MiniLM-L6-v2",
            config=config,
        )
        assert isinstance(provider, SentenceTransformerProvider)
        assert provider.get_device() == "cpu"

    def test_available_providers(self):
        providers = EmbeddingFactory.available_providers()
        assert "sentence_transformers" in providers

    def test_get_default_model(self):
        model = EmbeddingFactory.get_default_model(
            EmbeddingProviderType.SENTENCE_TRANSFORMERS
        )
        assert model == "all-MiniLM-L6-v2"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            EmbeddingFactory.create(provider_type="unknown")

    def test_register_provider(self):
        class MockProvider:
            def __init__(self, model_name, config):
                self.model_name = model_name

        EmbeddingFactory.register_provider("mock", MockProvider)
        assert "mock" in EmbeddingFactory.available_providers()