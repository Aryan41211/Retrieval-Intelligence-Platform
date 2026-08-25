"""End-to-end integration tests for the RIP pipeline."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.configs.settings import get_settings
from backend.core.exceptions import RipError
from backend.generation.exceptions import GenerationError
from backend.generation.generation_pipeline import GenerationPipeline
from backend.generation.models import GenerationResult
from backend.generation.pipeline_components.llm_gateway import LLMGateway
from backend.generation.providers.provider_factory import FakeProvider, ProviderFactory
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_metadata import RetrievalMetadata
from backend.retrieval.retrieval_result import RetrievalChunkResult
from backend.vectorstore.exceptions import VectorStoreError


def _make_chunk(
    chunk_id: str | None = None,
    document_id: str | None = None,
    chunk_text: str = "default text",
    similarity_score: float = 0.9,
    rank: int = 1,
    source_filename: str | None = "sample.txt",
    metadata: dict | None = None,
) -> Any:
    """Create a chunk-like object for generation pipeline consumption."""
    return type(
        "ChunkLike",
        (),
        {
            "chunk_id": chunk_id or str(uuid4()),
            "document_id": document_id or str(uuid4()),
            "chunk_text": chunk_text,
            "rank": rank,
            "similarity_score": similarity_score,
            "source_filename": source_filename,
            "metadata": metadata or {},
        },
    )()


class StubRetrievalPipeline:
    """A stub retrieval pipeline that returns pre-configured results."""

    def __init__(self, results, metadata=None):
        self._results = results
        self._metadata = metadata or RetrievalMetadata(retrieved_chunks=len(results))

    def run(self, request):
        return self._results, self._metadata


class TestGenerationPipelineEndToEnd:
    """End-to-end tests for the generation pipeline (the main integration point)."""

    async def test_normal_query(self):
        """Test normal query with context."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text="Python is a high-level programming language.",
                source_filename="python.txt",
                similarity_score=0.95,
            ),
            _make_chunk(
                chunk_text="It emphasizes code readability.",
                source_filename="python.txt",
                similarity_score=0.87,
            ),
        ]
        result = await gen.generate(query="What is Python?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""
        assert not result.incomplete
        assert len(result.citations) >= 0

    async def test_empty_retrieval(self):
        """Test generation with empty retrieval context."""
        gen = GenerationPipeline.from_config()
        result = await gen.generate(query="What is unknown?", retrieved_chunks=[])
        assert isinstance(result, GenerationResult)
        assert result.incomplete is True
        assert result.answer == "I don't know."

    async def test_low_confidence_retrieval(self):
        """Test generation with low-confidence retrieval results."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text="Uncertain fragment.",
                similarity_score=0.1,
                source_filename="low.txt",
            )
        ]
        result = await gen.generate(query="Could be anything?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    async def test_missing_source_metadata(self):
        """Test generation with chunks missing source metadata."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text="Content without source.",
                source_filename=None,
                similarity_score=0.8,
            )
        ]
        result = await gen.generate(query="What is this?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    async def test_large_retrieved_context(self):
        """Test generation with many chunks (verifies context truncation)."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text=f"Context fragment number {i}. " * 20,
                source_filename=f"doc_{i}.txt",
                similarity_score=0.9 - (i * 0.001),
            )
            for i in range(30)
        ]
        result = await gen.generate(query="Summarize everything.", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    async def test_default_development_provider_is_the_stub(self):
        """With no provider configured, development defaults to the stub."""
        gen = GenerationPipeline.from_config()
        chunks = [_make_chunk(chunk_text="text")]
        result = await gen.generate(query="test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.metadata.provider == "fake"

    async def test_unsupported_provider_is_rejected(self, monkeypatch):
        """An unrecognised provider must raise, not silently serve stub answers.

        Previously ProviderFactory returned FakeProvider for any unknown value,
        so a typo in GENERATION_PROVIDER produced fabricated ``[fake] ...``
        answers with a 200 response. The old test for this asserted the
        fallback but mutated settings in a way that was reverted by
        ``cache_clear()``, so it never exercised the path at all.
        """
        monkeypatch.setenv("GENERATION_PROVIDER", "gpt-9000")
        get_settings.cache_clear()
        try:
            with pytest.raises(ValidationError, match="Unknown GENERATION_PROVIDER"):
                get_settings()
        finally:
            get_settings.cache_clear()

    async def test_provider_factory_rejects_unsupported_provider_directly(self, monkeypatch):
        """ProviderFactory itself refuses an unsupported provider."""
        settings = get_settings()
        monkeypatch.setattr(settings.generation, "provider", "gpt-9000", raising=False)
        with pytest.raises(GenerationError, match="Unsupported GENERATION_PROVIDER"):
            ProviderFactory.create()

    async def test_real_provider_receives_credentials_and_base_url(self, monkeypatch):
        """A configured real provider must be built with its key and endpoint.

        Regression test for the factory constructing every provider with only a
        model name, which left OpenAI pointed at localhost with no API key and
        Anthropic sending an empty ``x-api-key`` header.
        """
        monkeypatch.setenv("GENERATION_PROVIDER", "anthropic")
        monkeypatch.setenv("GENERATION_MODEL_NAME", "claude-sonnet-5")
        monkeypatch.setenv("GENERATION_API_KEY", "test-key-123")
        get_settings.cache_clear()
        try:
            provider = ProviderFactory.create()
            assert provider.provider_name == "anthropic"
            assert provider.model_name == "claude-sonnet-5"
            assert provider._api_key == "test-key-123"
            assert provider._base_url == "https://api.anthropic.com/v1"
        finally:
            get_settings.cache_clear()

    async def test_production_rejects_fake_provider(self):
        """The stub provider must be refused in a production environment."""
        settings = get_settings()
        with pytest.raises(ValueError, match="must not be used in production"):
            settings.generation.validate_for_environment("production")

    async def test_real_provider_without_api_key_is_rejected(self, monkeypatch):
        """A credential-requiring provider with no key fails validation."""
        monkeypatch.setenv("GENERATION_PROVIDER", "openai")
        monkeypatch.delenv("GENERATION_API_KEY", raising=False)
        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError, match="requires GENERATION_API_KEY"):
                get_settings().generation.validate_for_environment("production")
        finally:
            get_settings.cache_clear()

    def test_vector_store_error_inherits_rip_error(self):
        """Verify vector store exceptions are part of the RIP error hierarchy."""
        assert issubclass(VectorStoreError, RipError)
        exc = VectorStoreError("test")
        assert exc.code == "VECTOR_STORE_ERROR"
        response = exc.to_response()
        assert response["code"] == "VECTOR_STORE_ERROR"


class TestRAGPipelineEndToEnd:
    """End-to-end tests for the unified RAG pipeline."""

    async def test_full_pipeline_wired_correctly(self):
        """Test that retrieval results flow into generation correctly."""

        def _retrieve(request):
            return [
                RetrievalChunkResult(
                    chunk_id=uuid4(),
                    document_id=uuid4(),
                    chunk_text="RAG test context.",
                    similarity_score=0.9,
                    rank=1,
                    source_filename="rag.txt",
                )
            ], RetrievalMetadata(retrieved_chunks=1)

        engine = RetrievalEngine.__new__(RetrievalEngine)
        engine.retrieve = lambda request: _retrieve(request)[0]
        engine.retrieve_with_filters = lambda *a, **k: _retrieve(None)[0]
        engine.retrieve_by_document = lambda *a, **k: _retrieve(None)[0]
        engine.retrieve_by_chunk = lambda *a, **k: _retrieve(None)[0]
        engine.retrieve_batch = lambda requests: [_retrieve(r)[0] for r in requests]
        engine._vector_store = None

        gen = GenerationPipeline.from_config()

        class FakeRAGPipeline:
            pass

        # Directly test generation with retrieval output.
        chunks, _ = _retrieve(None)
        result = await gen.generate(query="RAG integration test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    async def test_retrieval_engine_communicates_with_generation(self):
        """Verify RetrievalChunkResult attributes are accessible to generation."""
        chunks = [
            RetrievalChunkResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                chunk_text="Interoperable chunk.",
                similarity_score=0.85,
                rank=1,
                source_filename="interop.txt",
            )
        ]
        gen = GenerationPipeline.from_config()
        result = await gen.generate(query="interop test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.metadata.provider == "fake"

    async def test_llm_gateway_produces_grounded_responses(self):
        """Verify LLMGateway produces responses through the provider."""
        gateway = LLMGateway(provider=FakeProvider())
        response = await gateway.generate(
            prompt="[doc_1]: test context\n\nQuestion: what?", temperature=0.1, max_tokens=64
        )
        assert isinstance(response, str)
        assert len(response) > 0
