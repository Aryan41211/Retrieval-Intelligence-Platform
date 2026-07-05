from __future__ import annotations

import logging
import time

from backend.generation.exceptions import (
    GenerationError,
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)
from backend.generation.providers.base_provider import LLMProvider

logger = logging.getLogger(__name__)


class LLMGateway:
    """Provider-agnostic gateway for LLM calls with timeout handling."""

    def __init__(self, *, provider: LLMProvider, timeout_s: float = 60.0):
        self._provider = provider
        self._timeout_s = timeout_s

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def generate(self, *, prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> str:
        t0 = time.perf_counter()
        try:
            raw = self._provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_s=self._timeout_s,
                stream=False,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "LLM generation completed",
                extra={"provider": self.provider_name, "model": self.model_name, "latency_ms": latency_ms},
            )
            return raw
        except LLMProviderUnavailableError:
            raise
        except GenerationTimeoutError:
            raise
        except GenerationError:
            raise
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error(
                "LLM generation failed: %s",
                str(exc),
                extra={"provider": self.provider_name, "model": self.model_name, "latency_ms": latency_ms},
            )
            raise LLMProviderUnavailableError(
                f"Provider '{self.provider_name}' failed: {exc}"
            ) from exc
