from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Provider interface for LLM calls."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    def token_usage(self) -> dict[str, Any] | None:
        """Token usage from the most recent generation, if the provider reports it.

        Non-streaming chat completions carry a ``usage`` object; streaming
        responses may not. Providers that cannot report usage return ``None``.
        """
        return None

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        stream: bool = False,
    ) -> str:
        raise NotImplementedError
