from __future__ import annotations

from backend.configs.settings import get_settings
from backend.generation.exceptions import GenerationError, LLMProviderUnavailableError
from backend.generation.providers.anthropic_provider import AnthropicProvider
from backend.generation.providers.base_provider import LLMProvider
from backend.generation.providers.nim_provider import NIMProvider
from backend.generation.providers.ollama_provider import OllamaProvider
from backend.generation.providers.openai_provider import OpenAICompatibleProvider


class ProviderFactory:
    """Factory for creating LLM providers based on configuration."""

    @staticmethod
    def create() -> LLMProvider:
        settings = get_settings()
        gen = settings.generation
        provider = (gen.provider or "fake").lower()

        if provider == "fake":
            return FakeProvider()

        if provider in {"openai", "openai_compatible", "openai-compatible"}:
            return OpenAICompatibleProvider(
                model=gen.model_name,
            )

        if provider == "ollama":
            return OllamaProvider(
                model=gen.model_name,
            )

        if provider == "nim":
            return NIMProvider(
                model=gen.model_name,
            )

        if provider == "anthropic":
            return AnthropicProvider(
                model=gen.model_name,
            )

        return FakeProvider()


class FakeProvider(LLMProvider):
    """Deterministic fake provider for testing and development."""

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def health_check(self) -> dict[str, object]:
        return {"status": "healthy", "provider": self.provider_name}

    async def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        stream: bool = False,
    ) -> str:
        if not prompt or not prompt.strip():
            raise GenerationError("Empty prompt is not allowed")
        prefix = "[fake] "
        text = prefix + prompt.strip()
        if len(text) > max_tokens:
            text = text[:max_tokens]
        return text

    def extract_token_usage(self, response: object) -> dict[str, int] | None:
        return None
