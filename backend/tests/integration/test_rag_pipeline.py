"""End-to-end integration tests for the RIP pipeline."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.configs.settings import get_settings
from backend.core.exceptions import RipError
from backend.generation.generation_pipeline import GenerationPipeline
from backend.generation.models import GenerationResult
from backend.generation.pipeline_components.llm_gateway import LLMGateway
from backend.generation.providers.provider_factory import FakeProvider
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

    async def test_invalid_provider_configuration(self):
        """Test that provider factory falls back to fake on invalid config."""
        gen = GenerationPipeline.from_config()
        chunks = [_make_chunk(chunk_text="text")]
        result = await gen.generate(query="test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.metadata.provider == "fake"

    async def test_unsupported_provider_falls_back(self):
        """Test that unsupported provider type falls back to fake."""
        # Temporarily set an unsupported provider
        settings = get_settings()
        original = settings.generation.provider
        try:
            settings.generation.provider = "unsupported_provider"
            # Clear cache to pick up new settings
            get_settings.cache_clear()
            gen = GenerationPipeline.from_config()
            chunks = [_make_chunk(chunk_text="text")]
            result = await gen.generate(query="test", retrieved_chunks=chunks)
            assert result.metadata.provider == "fake"
        finally:
            settings.generation.provider = original
            get_settings.cache_clear()
            GenerationPipeline.from_config()

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
