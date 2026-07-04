from __future__ import annotations

from backend.generation.providers.base_provider import LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic provider for unit testing.

    Returns a canned grounded answer that includes [doc_N] citations
    derived from prompt context if present.
    """

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        stream: bool = False,
    ) -> str:
        # Simple heuristic: if the prompt contains doc markers, cite first two.
        if "[doc_1]:" in prompt and "[doc_2]:" in prompt:
            return "This answer is grounded in the provided context. [doc_1] [doc_2]"
        if "[doc_1]:" in prompt:
            return "This answer is grounded in the provided context. [doc_1]"
        return "I don't know."
