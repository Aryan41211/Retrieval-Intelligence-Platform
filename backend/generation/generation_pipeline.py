from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from backend.generation.exceptions import (
    EmptyContextError,
    GenerationError,
    LLMProviderUnavailableError,
)
from backend.generation.models import ContextItem, GenerationResult
from backend.generation.pipeline_components.citation_generator import CitationGenerator
from backend.generation.pipeline_components.context_builder import ContextBuilder
from backend.generation.pipeline_components.hallucination_guard import HallucinationGuard
from backend.generation.pipeline_components.llm_gateway import LLMGateway
from backend.generation.pipeline_components.prompt_builder import PromptBuilder
from backend.generation.pipeline_components.response_validator import ResponseValidator
from backend.generation.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationInput:
    query: str
    context_items: list[ContextItem]
    correlation_id: str | None = None
    extra: dict[str, Any] | None = None


class GenerationPipeline:
    """Provider-agnostic grounded generation orchestrator.

    This pipeline remains independent of retrieval implementation. It consumes
    structured context items (derived from retrieved chunks) and produces a
    grounded GenerationResult with citations and validation metadata.
    """

    def __init__(
        self,
        *,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        llm_gateway: LLMGateway,
        citation_generator: CitationGenerator,
        response_validator: ResponseValidator,
        hallucination_guard: HallucinationGuard,
    ):
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._llm_gateway = llm_gateway
        self._citation_generator = citation_generator
        self._response_validator = response_validator
        self._hallucination_guard = hallucination_guard

    @classmethod
    def from_config(cls) -> GenerationPipeline:
        provider = ProviderFactory.create()

        # Lazy imports avoid circulars in test environments.
        context_builder = ContextBuilder()
        prompt_builder = PromptBuilder()
        llm_gateway = LLMGateway(provider=provider)
        citation_generator = CitationGenerator()
        response_validator = ResponseValidator()
        hallucination_guard = HallucinationGuard(response_validator=response_validator)

        return cls(
            context_builder=context_builder,
            prompt_builder=prompt_builder,
            llm_gateway=llm_gateway,
            citation_generator=citation_generator,
            response_validator=response_validator,
            hallucination_guard=hallucination_guard,
        )

    async def generate(
        self, query: str, retrieved_chunks: list[Any], *, correlation_id: str | None = None
    ) -> GenerationResult:
        """Asynchronous generation entry point.

        Args:
            query: User query.
            retrieved_chunks: RetrievalChunk-like objects; must expose chunk_id, document_id, chunk_text,
                rank/similarity_score/source_filename and optional metadata.
            correlation_id: Optional correlation id for logs.

        Returns:
            Grounded GenerationResult.
        """
        t0 = time.perf_counter()
        correlation_id = correlation_id or None

        # 1) Context
        try:
            context_items = self._context_builder.build(
                query=query, retrieved_chunks=retrieved_chunks
            )
        except EmptyContextError:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return GenerationResult(
                answer="I don't know.",
                incomplete=True,
                metadata=self._empty_metadata(
                    correlation_id=correlation_id, total_latency_ms=latency_ms
                ),
            )

        # 2) Prompt
        prompt, token_est_prompt = self._prompt_builder.build(
            query=query, context_items=context_items
        )

        # 3) LLM call
        try:
            llm_start = time.perf_counter()
            raw_answer = await self._llm_gateway.generate(prompt=prompt)
            llm_latency_ms = int((time.perf_counter() - llm_start) * 1000)
        except LLMProviderUnavailableError as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error(
                json.dumps(
                    {
                        "event": "generation.provider_unavailable",
                        "correlation_id": correlation_id,
                        "error": str(e),
                    }
                )
            )
            return GenerationResult(
                answer="I don't know.",
                incomplete=True,
                metadata=self._empty_metadata(
                    correlation_id=correlation_id,
                    total_latency_ms=latency_ms,
                    llm_latency_ms=llm_latency_ms,
                ),
            )
        except GenerationError:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return GenerationResult(
                answer="I don't know.",
                incomplete=True,
                metadata=self._empty_metadata(
                    correlation_id=correlation_id, total_latency_ms=latency_ms
                ),
            )

        # 4) Citations
        citations = self._citation_generator.generate(
            answer=raw_answer, context_items=context_items
        )

        # 5) Validate + guard
        grounded_result = self._response_validator.validate(
            query=query,
            answer=raw_answer,
            context_items=context_items,
            citations=citations,
        )
        final_result = self._hallucination_guard.apply(
            query=query, result=grounded_result, context_items=context_items
        )

        total_latency_ms = int((time.perf_counter() - t0) * 1000)
        final_result.metadata.total_latency_ms = total_latency_ms
        final_result.metadata.token_estimate_prompt = token_est_prompt
        final_result.metadata.llm_latency_ms = llm_latency_ms
        final_result.metadata.citations_generated = len(citations)
        final_result.metadata.provider = self._llm_gateway.provider_name
        final_result.metadata.model = self._llm_gateway.model_name

        return final_result

    def _empty_metadata(
        self,
        *,
        correlation_id: str | None,
        total_latency_ms: int,
        llm_latency_ms: int | None = None,
    ):
        md = GenerationMetadataPlaceholder(
            correlation_id=correlation_id,
            total_latency_ms=total_latency_ms,
            llm_latency_ms=llm_latency_ms,
        )
        return md.to_generation_metadata()


class GenerationMetadataPlaceholder:
    def __init__(
        self, correlation_id: str | None, total_latency_ms: int, llm_latency_ms: int | None
    ):
        self._correlation_id = correlation_id
        self._total_latency_ms = total_latency_ms
        self._llm_latency_ms = llm_latency_ms

    def to_generation_metadata(self):
        from backend.generation.models import GenerationMetadata

        return GenerationMetadata(
            total_latency_ms=self._total_latency_ms,
            llm_latency_ms=self._llm_latency_ms or 0,
            extra={"correlation_id": self._correlation_id},
        )
