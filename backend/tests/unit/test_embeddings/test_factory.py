"""Tests for embedding factory."""

import pytest

from backend.data.embeddings.base_embedding_provider import BaseEmbeddingProvider
from backend.data.embeddings.embedding_factory import (
    EmbeddingFactory,
    EmbeddingProviderType,
)


class MockProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "mock", config=None):
        super().__init__(config)
        self._model_info = type("Info", (), {"name": model_name, "version": "1.0", "dimension": 100})()

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_info(self):
        return self._model_info

    @property
    def dimension(self) -> int:
        return 100

    def embed_text(self, text: str):
        return type(
            "Embedding",
            (),
            {
                "chunk_id": None,
                "document_id": None,
                "model_name": self.name,
                "model_version": "1.0",
                "embedding_dimension": 100,
                "embedding_vector": [0.1] * 100,
                "checksum": "abc",
            },
        )()

    def embed_texts(self, texts: list[str]):
        return [self.embed_text(t) for t in texts]

    def embed_chunks(self, chunks):
        from backend.data.models.embedding import EmbeddingBatchResult

        return EmbeddingBatchResult(results=[])


class TestEmbeddingFactory:
    """Tests for EmbeddingFactory class."""

    def test_create_custom_provider(self):
        EmbeddingFactory.register_provider("mock", MockProvider)
        provider = EmbeddingFactory.create(
            provider_type="mock",
            model_name="test-model",
            config={"device": "cpu"},
        )
        assert isinstance(provider, MockProvider)

    def test_create_with_config(self):
        config = {"device": "cpu", "batch_size": 64}
        provider = EmbeddingFactory.create(
            provider_type="mock",
            model_name="test-model",
            config=config,
        )
        assert isinstance(provider, MockProvider)

    def test_register_provider(self):
        EmbeddingFactory.register_provider("mock2", MockProvider)
        assert "mock2" in EmbeddingFactory.available_providers()

    def test_get_default_model(self):
        model = EmbeddingFactory.get_default_model(EmbeddingProviderType.SENTENCE_TRANSFORMERS)
        assert model == "all-MiniLM-L6-v2"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            EmbeddingFactory.create(provider_type="unknown")
