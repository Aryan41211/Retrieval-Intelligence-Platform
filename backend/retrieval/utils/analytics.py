from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalAnalytics:
    """Lightweight analytics collector used by IntelligentRetrievalPipeline."""

    # Store arbitrary numeric metrics.
    metrics: dict[str, int] = field(default_factory=dict)

    def add(self, key: str, value: int) -> None:
        self.metrics[key] = int(value)

    def to_dict(self) -> dict[str, int]:
        return dict(self.metrics)
