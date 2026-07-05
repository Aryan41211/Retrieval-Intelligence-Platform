from __future__ import annotations

from backend.generation.exceptions import (
    GenerationError,
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)
from backend.generation.providers.base_provider import LLMProvider


class NIMProvider(LLMProvider):
    """HTTP client for NVIDIA NIM API."""

    def __init__(self, *, model: str, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "nim"

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
            raise LLMProviderUnavailableError("httpx is required for NIMProvider") from exc

        headers = {"Content-Type": "application/json"}
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        try:
            with httpx.Client(timeout=timeout_s) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except TimeoutError as exc:
            raise GenerationTimeoutError(f"Request timed out after {timeout_s}s") from exc
        except LLMProviderUnavailableError:
            raise
        except GenerationError:
            raise
        except Exception as exc:
            raise LLMProviderUnavailableError(str(exc)) from exc
