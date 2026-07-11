from __future__ import annotations

import time
from dataclasses import dataclass

from backend.generation.models import ContextItem


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class PromptBuildConfig:
    system_prompt: str = (
        "You are a helpful assistant that answers questions using only the provided context. "
        "Always cite your sources using [doc_N] format. "
        'If unsure, say "I don\'t know."'
    )
    developer_prompt: str | None = None
    output_format_instructions: str = "Answer with citations."
    safety_instructions: str | None = None


class PromptBuilder:
    """Builds a grounded prompt from query + context items."""

    def __init__(self, config: PromptBuildConfig | None = None):
        self._config = config or PromptBuildConfig()

    def build(self, *, query: str, context_items: list[ContextItem]) -> tuple[str, int]:
        t0 = time.perf_counter()

        context_lines: list[str] = []
        for i, item in enumerate(context_items, start=1):
            context_lines.append(f"[doc_{i}]: {item.chunk_text}")

        dev = (self._config.developer_prompt or "").strip()
        safety = (self._config.safety_instructions or "").strip()

        parts: list[str] = [
            self._config.system_prompt.strip(),
        ]
        if dev:
            parts.append(dev)
        if safety:
            parts.append(safety)

        parts.extend(
            [
                "Context:\n" + "\n".join(context_lines),
                f"User question: {query}",
                self._config.output_format_instructions.strip(),
            ]
        )

        prompt = "\n\n".join(parts).strip()

        token_est = _estimate_tokens(prompt)

        _ = int((time.perf_counter() - t0) * 1000)  # prompt latency exists for logging later
        return prompt, token_est
