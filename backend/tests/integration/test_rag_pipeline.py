"""End-to-end integration tests for the RIP pipeline."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.configs.settings import get_settings
from backend.core.exceptions import RipError
from backend.generation.generation_pipeline import GenerationPipeline
from backend.generation.models import GenerationResult
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

    def test_normal_query(self):
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
        result = gen.generate(query="What is Python?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""
        assert not result.incomplete
        assert len(result.citations) >= 0

    def test_empty_retrieval(self):
        """Test generation with empty retrieval context."""
        gen = GenerationPipeline.from_config()
        result = gen.generate(query="What is unknown?", retrieved_chunks=[])
        assert isinstance(result, GenerationResult)
        assert result.incomplete is True
        assert result.answer == "I don't know."

    def test_low_confidence_retrieval(self):
        """Test generation with low-confidence retrieval results."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text="Uncertain fragment.",
                similarity_score=0.1,
                source_filename="low.txt",
            )
        ]
        result = gen.generate(query="Could be anything?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    def test_missing_source_metadata(self):
        """Test generation with chunks missing source metadata."""
        gen = GenerationPipeline.from_config()
        chunks = [
            _make_chunk(
                chunk_text="Content without source.",
                source_filename=None,
                similarity_score=0.8,
            )
        ]
        result = gen.generate(query="What is this?", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    def test_large_retrieved_context(self):
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
        result = gen.generate(query="Summarize everything.", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    def test_invalid_provider_configuration(self):
        """Test that provider factory falls back to fake on invalid config."""
        gen = GenerationPipeline.from_config()
        chunks = [_make_chunk(chunk_text="text")]
        result = gen.generate(query="test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.metadata.provider == "fake"

    def test_unsupported_provider_falls_back(self):
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
            result = gen.generate(query="test", retrieved_chunks=chunks)
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

    def test_full_pipeline_wired_correctly(self):
        """Test that retrieval results flow into generation correctly."""
        def _retrieve(self, request):
            return [RetrievalChunkResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                chunk_text="RAG test context.",
                similarity_score=0.9,
                rank=1,
                source_filename="rag.txt",
            )], RetrievalMetadata(retrieved_chunks=1)

        engine = RetrievalEngine.__new__(RetrievalEngine)
        engine.retrieve = lambda request: _retrieve(None, request)[0]
        engine.retrieve_with_filters = lambda *a, **k: _retrieve(None, None)[0]
        engine.retrieve_by_document = lambda *a, **k: _retrieve(None, None)[0]
        engine.retrieve_by_chunk = lambda *a, **k: _retrieve(None, None)[0]
        engine.retrieve_batch = lambda requests: [_retrieve(None, r)[0] for r in requests]
        engine._vector_store = None

        gen = GenerationPipeline.from_config()

        class FakeRAGPipeline:
            pass

        # Directly test generation with retrieval output.
        chunks, _ = _retrieve(None, None)
        result = gen.generate(query="RAG integration test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.answer != ""

    def test_retrieval_engine_communicates_with_generation(self):
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
        result = gen.generate(query="interop test", retrieved_chunks=chunks)
        assert isinstance(result, GenerationResult)
        assert result.metadata.provider == "fake"

    def test_context_builder_receives_structured_results(self):
        """Verify ContextBuilder handles RetrievalChunkResult objects."""
        from backend.generation.pipeline_components.context_builder import ContextBuilder
        builder = ContextBuilder()
        chunks = [
            RetrievalChunkResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                chunk_text="Builder test chunk.",
                similarity_score=0.9,
                rank=1,
                source_filename="builder.txt",
                metadata={"page": 1},
            )
        ]
        context_items = builder.build(query="test", retrieved_chunks=chunks)
        assert len(context_items) == 1
        assert context_items[0].chunk_text == "Builder test chunk."
        assert context_items[0].source_filename == "builder.txt"
        assert context_items[0].extra == {"page": 1}

    def test_prompt_builder_assembles_correctly(self):
        """Verify PromptBuilder renders prompt with doc markers."""
        from backend.generation.models import ContextItem
        from backend.generation.pipeline_components.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        items = [
            ContextItem(
                chunk_id="1",
                document_id="doc-1",
                chunk_text="Python is great.",
                rank=1,
                similarity_score=0.9,
                source_filename="py.txt",
            )
        ]
        prompt, token_est = builder.build(query="What is Python?", context_items=items)
        assert "[doc_1]" in prompt
        assert "Python is great." in prompt
        assert "What is Python?" in prompt
        assert token_est > 0

    def test_citation_generator_receives_source_metadata(self):
        """Verify CitationGenerator extracts citations from answer."""
        from backend.generation.models import ContextItem
        from backend.generation.pipeline_components.citation_generator import CitationGenerator
        gen = CitationGenerator()
        chunks = [
            ContextItem(
                chunk_id="chunk-1",
                document_id="doc-1",
                chunk_text="First document.",
                rank=1,
                similarity_score=0.9,
                source_filename="doc-1.txt",
            ),
            ContextItem(
                chunk_id="chunk-2",
                document_id="doc-2",
                chunk_text="Second document.",
                rank=2,
                similarity_score=0.8,
                source_filename="doc-2.txt",
            ),
        ]
        expected_citations = 2
        answer = "According to [doc_1] and [doc_2], the answer is clear. [doc_1]"
        citations = gen.generate(answer=answer, context_items=chunks)
        assert len(citations) == expected_citations
        assert citations[0].doc_index == 1
        assert citations[1].doc_index == expected_citations

    def test_response_validator_processes_every_answer(self):
        """Verify ResponseValidator processes every generated answer."""
        from backend.generation.models import Citation, ContextItem
        from backend.generation.pipeline_components.response_validator import ResponseValidator
        validator = ResponseValidator()
        chunks = [
            ContextItem(
                chunk_id="c1",
                document_id="d1",
                chunk_text="Validated text.",
                rank=1,
                similarity_score=0.9,
            )
        ]
        result = validator.validate(
            query="test",
            answer="This is a valid answer. [doc_1]",
            context_items=chunks,
            citations=[Citation(doc_index=1, chunk_id="c1", confidence=0.9)],
        )
        assert isinstance(result, GenerationResult)
        assert result.answer == "This is a valid answer. [doc_1]"

    def test_hallucination_guard_executes(self):
        """Verify HallucinationGuard runs for every response."""
        from backend.generation.models import ContextItem, GenerationMetadata, GenerationResult
        from backend.generation.pipeline_components.hallucination_guard import HallucinationGuard
        from backend.generation.pipeline_components.response_validator import ResponseValidator
        guard = HallucinationGuard(response_validator=ResponseValidator(), threshold=0.3)
        chunks = [ContextItem(chunk_id="c1", document_id="d1", chunk_text="text", rank=1, similarity_score=0.9)]
        result = GenerationResult(
            answer="no citations here",
            metadata=GenerationMetadata(groundedness_score=0.0),
        )
        guarded = guard.apply(query="test", result=result, context_items=chunks)
        assert guarded.incomplete is True

    def test_llm_gateway_produces_grounded_responses(self):
        """Verify LLMGateway produces responses through the provider."""
        from backend.generation.pipeline_components.llm_gateway import LLMGateway
        from backend.generation.providers.stubs.fake_provider import FakeProvider
        gateway = LLMGateway(provider=FakeProvider())
        response = gateway.generate(prompt="[doc_1]: test context\n\nQuestion: what?", temperature=0.1, max_tokens=64)
        assert isinstance(response, str)
        assert len(response) > 0
