from __future__ import annotations

from backend.configs.settings import SUPPORTED_GENERATION_PROVIDERS, get_settings
from backend.generation.exceptions import GenerationError
from backend.generation.providers.anthropic_provider import AnthropicProvider
from backend.generation.providers.base_provider import LLMProvider
from backend.generation.providers.nim_provider import NIMProvider
from backend.generation.providers.ollama_provider import OllamaProvider
from backend.generation.providers.openai_provider import OpenAICompatibleProvider


class ProviderFactory:
    """Factory for creating LLM providers based on configuration."""

    @staticmethod
    def create() -> LLMProvider:
        """Build the configured LLM provider with its credentials and endpoint.

        Returns:
            A ready-to-use provider instance.

        Raises:
            GenerationError: If the configured provider is not supported. It is
                deliberately *not* silently replaced by the stub provider, which
                previously caused a typo in GENERATION_PROVIDER to serve
                fabricated answers with a 200 response.
        """
        settings = get_settings()
        gen = settings.generation
        provider = (gen.provider or "fake").strip().lower()

        if provider == "fake":
            return FakeProvider()

        # Options shared by every HTTP-backed provider. Previously none of these
        # were passed, so providers ran with no API key and a localhost base URL.
        common: dict[str, object] = {
            "model": gen.model_name,
            "timeout_s": gen.timeout_s,
            "max_retries": gen.max_retries,
        }
        base_url = gen.resolved_base_url()
        if base_url:
            common["base_url"] = base_url
        if gen.api_key:
            common["api_key"] = gen.api_key

        if provider in {"openai", "openai_compatible", "openai-compatible"}:
            return OpenAICompatibleProvider(
                organization=gen.organization,
                project=gen.project,
                **common,
            )

        if provider == "ollama":
            return OllamaProvider(**common)

        if provider == "nim":
            return NIMProvider(**common)

        if provider == "anthropic":
            return AnthropicProvider(
                anthropic_version=gen.anthropic_version,
                **common,
            )

        supported = ", ".join(sorted(SUPPORTED_GENERATION_PROVIDERS))
        raise GenerationError(
            f"Unsupported GENERATION_PROVIDER {gen.provider!r}. Supported providers: {supported}."
        )


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
