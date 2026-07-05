from __future__ import annotations

from backend.generation.exceptions import (
    GenerationError,
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)
from backend.generation.providers.base_provider import LLMProvider


class OllamaProvider(LLMProvider):
    """HTTP client for Ollama local API."""

    def __init__(self, *, model: str, base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        stream: bool = False,
    ) -> str:
        try:
            import httpx  # type: ignore[import-untyped]
        except ImportError as exc:
            raise LLMProviderUnavailableError("httpx is required for OllamaProvider") from exc

        body = {
            "model": self._model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": stream,
        }

        try:
            with httpx.Client(timeout=timeout_s) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except TimeoutError as exc:
            raise GenerationTimeoutError(f"Request timed out after {timeout_s}s") from exc
        except LLMProviderUnavailableError:
            raise
        except GenerationError:
            raise
        except Exception as exc:
            raise LLMProviderUnavailableError(str(exc)) from exc
