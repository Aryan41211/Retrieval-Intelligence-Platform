from __future__ import annotations

from backend.configs.settings import get_settings
from backend.generation.providers.anthropic_provider import AnthropicProvider
from backend.generation.providers.base_provider import LLMProvider
from backend.generation.providers.openai_provider import OpenAIProvider
from backend.generation.providers.stubs.fake_provider import FakeProvider
from backend.generation.providers.stubs.nim_provider import NIMProvider
from backend.generation.providers.stubs.ollama_provider import OllamaProvider
from backend.generation.providers.stubs.openai_compatible_provider import OpenAICompatibleProvider


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

        if provider == "openai":
            return OpenAIProvider(
                model=gen.model_name,
            )

        if provider == "anthropic":
            return AnthropicProvider(
                model=gen.model_name,
            )

        return FakeProvider()
