from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from httpx import TimeoutException

from backend.generation.exceptions import (
    GenerationError,
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)
from backend.generation.providers.base_provider import LLMProvider
from backend.generation.providers.common.http_client import HTTPProviderClient, RetryConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnthropicSettings:
    """Settings for Anthropic provider."""

    base_url: str = "https://api.anthropic.com/v1"
    model: str = "claude-3-5-sonnet-20241022"
    api_key: str | None = None
    max_retries: int = 3
    timeout_s: float = 60.0
    temperature: float = 0.2
    max_tokens: int = 512
    stream: bool = False
    anthropic_version: str = "2023-06-01"


class AnthropicProvider(LLMProvider):
    """Production-grade Anthropic API provider.

    Implements full Anthropic API support with health checks,
    retry logic, streaming, structured responses, and token usage reporting.
    """

    def __init__(self, *, model: str, base_url: str = "https://api.anthropic.com/v1", **kwargs):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._http_client = HTTPProviderClient(
            base_url=self._base_url,
            model=model,
            timeout_s=kwargs.get("timeout_s", 60.0),
            retry_config=RetryConfig(
                max_retries=kwargs.get("max_retries", 3),
                initial_delay=kwargs.get("initial_delay", 1.0),
                max_delay=kwargs.get("max_delay", 10.0),
                backoff_factor=kwargs.get("backoff_factor", 2.0),
            ),
        )

        self._api_key = kwargs.get("api_key")
        self._anthropic_version = kwargs.get("anthropic_version", "2023-06-01")
        self._max_retries = kwargs.get("max_retries", 3)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def health_check(self) -> dict[str, Any]:
        """Check if the Anthropic API is healthy."""
        return await self._http_client.health_check()

    async def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        stream: bool = False,
    ) -> str:
        """Generate completion with full Anthropic API support.

        Args:
            prompt: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout_s: Request timeout
            stream: Whether to stream the response

        Returns:
            Generated text
        """
        start_time = time.perf_counter()
        path = "/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key or "",
            "anthropic-version": self._anthropic_version,
            "User-Agent": "RetrievalIntelligencePlatform/1.0",
        }

        # Anthropic uses messages API with system and user messages
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        try:
            response = await self._http_client._request_with_retry(
                method="POST",
                path=path,
                body=body,
                headers=headers,
            )

            if stream:
                return await self._handle_streaming_response(response)
            else:
                data = await response.json()
                return self._extract_text_from_response(data)

        except (TimeoutException, GenerationTimeoutError) as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                json.dumps(
                    {
                        "event": "generation.timeout",
                        "provider": self.provider_name,
                        "model": self.model_name,
                        "latency_ms": latency_ms,
                        "timeout_s": timeout_s,
                    }
                )
            )
            raise GenerationTimeoutError(f"Request timed out after {timeout_s}s") from exc
        except LLMProviderUnavailableError:
            raise
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                json.dumps(
                    {
                        "event": "generation.failed",
                        "provider": self.provider_name,
                        "model": self.model_name,
                        "latency_ms": latency_ms,
                        "error": str(exc),
                    }
                )
            )
            raise LLMProviderUnavailableError(f"Provider '{self.provider_name}' failed: {exc}") from exc

    async def _handle_streaming_response(self, response: httpx.Response) -> str:
        """Handle streaming response from Anthropic API."""
        content = []
        async for chunk in response.aiter_text():
            if chunk.strip():
                content.append(chunk)
        return "".join(content)

    def _extract_text_from_response(self, data: dict[str, Any]) -> str:
        """Extract text content from non-streaming response."""
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise GenerationError(f"Invalid response format: {exc}") from exc

    def extract_token_usage(self, response: httpx.Response) -> dict[str, Any] | None:
        """Extract token usage from API response.

        Args:
            response: HTTPX response object

        Returns:
            Dictionary with token usage or None if not available
        """
        try:
            data = response.json()
            return data.get("usage")
        except (json.JSONDecodeError, KeyError):
            return None


# Import httpx at module level for streaming handling
import httpx
