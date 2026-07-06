from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, HTTPStatusError, Response, TimeoutException

from backend.generation.exceptions import (
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for HTTP retry strategy."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    backoff_factor: float = 2.0


def _parse_url(url: str) -> str:
    """Normalize URL by removing trailing slash."""
    return url.rstrip("/")


class HTTPProviderClient:
    """Base HTTP client for LLM providers with common functionality.

    Provides health checks, retry logic, timeout handling, and streaming support.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: float = 60.0,
        retry_config: RetryConfig | None = None,
    ):
        self._base_url = _parse_url(base_url)
        self._model = model
        self._timeout_s = timeout_s
        self._retry_config = retry_config or RetryConfig()

    def _build_headers(self, additional: dict[str, str] | None = None) -> dict[str, str]:
        """Build standard HTTP headers for the provider."""
        headers = {"Content-Type": "application/json"}
        if additional:
            headers.update(additional)
        return headers

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Execute HTTP request with retry logic."""
        url = f"{self._base_url}/{path.lstrip('/')}"

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                async with AsyncClient(timeout=self._timeout_s) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=body,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return response
            except (TimeoutError, TimeoutException) as exc:
                if attempt == self._retry_config.max_retries:
                    raise GenerationTimeoutError(f"Request timed out after {self._timeout_s}s") from exc
                delay = min(
                    self._retry_config.initial_delay * (self._retry_config.backoff_factor ** attempt),
                    self._retry_config.max_delay,
                )
                await time.sleep(delay)
            except HTTPStatusError as exc:
                if 500 <= exc.response.status_code <= 599 and attempt < self._retry_config.max_retries:
                    delay = min(
                        self._retry_config.initial_delay * (self._retry_config.backoff_factor ** attempt),
                        self._retry_config.max_delay,
                    )
                    await time.sleep(delay)
                    continue
                raise LLMProviderUnavailableError(f"HTTP {exc.response.status_code}: {exc.response.text}") from exc
            except Exception as exc:
                raise LLMProviderUnavailableError(f"Request failed: {exc}") from exc

        raise LLMProviderUnavailableError("Max retries reached")

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the provider.

        Returns:
            Health check result with status and metrics.
        """
        start_time = time.perf_counter()

        try:
            response = await self._request_with_retry("GET", "health")
            status_code = response.status_code
            data = await response.json()

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if 200 <= status_code < 300:
                return {
                    "status": "healthy",
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "data": data,
                }
            else:
                return {
                    "status": "unhealthy",
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "data": data,
                }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Health check failed: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
                "latency_ms": latency_ms,
            }


@dataclass(frozen=True)
class GenerationSettings:
    """LLM generation settings."""

    provider: str = "fake"
    model_name: str = "fake-model"
    temperature: float = 0.2
    max_tokens: int = 512
    timeout_s: float = 60.0


from typing import Protocol


class StructuredResponse(Protocol):
    """Protocol for structured generation responses."""

    def __init__(self, data: Any, usage: dict[str, Any] | None = None, model: str | None = None, finish_reason: str | None = None): ...


class TokenUsageReporter(Protocol):
    """Protocol for extracting token usage from responses."""

    def extract_usage(self, response: Any) -> dict[str, Any] | None: ...

